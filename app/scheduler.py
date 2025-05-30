import os
from datetime import datetime, timedelta, timezone
from flask import current_app, render_template, url_for
from openai import OpenAI, RateLimitError, APIError

from .models import db, Subscription # Assuming models.py is in the same directory (app)
from .utils import send_email # Or send_email_via_gmail_api if 12.4 was done
from .arxiv_api import search_papers, ArxivAPIException, NetworkException, ParsingException, ValidationException

# --- Direct AI Summarization Utility ---
def summarize_abstracts_for_newsletter(abstracts_data: list, max_papers_to_summarize=5):
    """
    Generates summaries for a list of paper abstracts using OpenAI.
    abstracts_data: list of dicts, each like {'id': str, 'title': str, 'summary': str (original abstract), 'pdf_link': str, 'published_date': str}
    Returns a list of dicts, each with original paper data + 'ai_summary': str
    """
    if not abstracts_data:
        return []

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        current_app.logger.error("Newsletter: OPENAI_API_KEY not configured.")
        return abstracts_data # Return original data, summarization failed

    summarized_papers_content = []
    papers_to_process = abstracts_data[:max_papers_to_summarize]

    for paper in papers_to_process:
        prompt = (
            f"Extract exactly 3 key takeaways from the following research paper abstract. Present these takeaways as a numbered list. IMPORTANT: Each numbered takeaway MUST start on a new line, ideally separated by an HTML <br> tag.\n"
            f"Each takeaway should be concise and highlight a main contribution, finding, or methodology.\n\n"
            f"Title: {paper.get('title', 'N/A')}\n"
            f"Abstract: {paper.get('summary', 'N/A')}"
        )
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an assistant skilled in summarizing academic research paper abstracts concisely for a newsletter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300 # Increased from 150 for 3 takeaways
            )
            ai_summary = response.choices[0].message.content.strip()
            paper_with_summary = {**paper, 'ai_summary': ai_summary}
            summarized_papers_content.append(paper_with_summary)
            current_app.logger.info(f"Newsletter: Successfully summarized paper ID {paper.get('id')}")
        except RateLimitError:
            current_app.logger.warning(f"Newsletter: OpenAI RateLimitError for paper ID {paper.get('id')}. Skipping summary for this paper.")
            summarized_papers_content.append({**paper, 'ai_summary': "Summary currently unavailable (rate limit)."})
        except APIError as e:
            current_app.logger.error(f"Newsletter: OpenAI APIError for paper ID {paper.get('id')}: {e}. Skipping summary.")
            summarized_papers_content.append({**paper, 'ai_summary': "Summary currently unavailable (API error)."})
        except Exception as e:
            current_app.logger.error(f"Newsletter: Unexpected error summarizing paper ID {paper.get('id')}: {e}", exc_info=True)
            summarized_papers_content.append({**paper, 'ai_summary': "Summary currently unavailable (unexpected error)."})
            
    # Add remaining papers that were not summarized (if any)
    # This block is removed to only include summarized papers in the newsletter
    # if len(abstracts_data) > max_papers_to_summarize:
    #     for paper in abstracts_data[max_papers_to_summarize:]:
    #          summarized_papers_content.append({**paper, 'ai_summary': 'Further papers available. Visit our website for more.'})

    return summarized_papers_content

# --- Scheduled Job ---
def send_weekly_newsletter_job():
    """
    Job to be scheduled weekly. Fetches new papers, summarizes them,
    and sends them out to confirmed subscribers.
    """
    with current_app.app_context(): # Ensure we have app context for db, config, logging
        current_app.logger.info("Starting weekly newsletter generation job.")

        # 1. Fetch Confirmed Subscribers
        try:
            confirmed_subscribers = Subscription.query.filter_by(
                is_confirmed=True, 
                unsubscribed_at=None
            ).all()
        except Exception as e:
            current_app.logger.error(f"Newsletter: Failed to fetch subscribers: {e}", exc_info=True)
            return

        if not confirmed_subscribers:
            current_app.logger.info("Newsletter: No confirmed subscribers to send to. Job ending.")
            return
        
        current_app.logger.info(f"Newsletter: Found {len(confirmed_subscribers)} confirmed subscribers.")

        # --- Start of per-subscriber processing loop ---
        for subscriber in confirmed_subscribers:
            current_app.logger.info(f"Processing newsletter for subscriber: {subscriber.email_hash}")
            
            # 2. Select Relevant Papers (e.g., last 7 days, specific category or keywords)
            subscriber_query = subscriber.keywords if subscriber.keywords and subscriber.keywords.strip() else "cat:cs.AI"
            current_app.logger.info(f"Using query for subscriber {subscriber.email_hash}: '{subscriber_query}'")

            newsletter_papers = [] # Renamed from recent_papers to avoid confusion, reset per subscriber
            try:
                # Fetch more papers than we plan to summarize to have a selection
                arxiv_results = search_papers(query=subscriber_query, count=20, sort_by='submittedDate', sort_order='descending')
                
                raw_papers = arxiv_results.get('papers', [])
                
                one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
                # Filter for papers from the last 7 days (approx)
                # Name changed from recent_papers to filtered_papers to avoid confusion with the outer scope variable
                filtered_papers = [] 
                for paper_obj in raw_papers:
                    published_dt = paper_obj.published_date 
                    if published_dt and published_dt >= one_week_ago:
                        filtered_papers.append({
                            'id': paper_obj.id_str,
                            'title': paper_obj.title,
                            'summary': paper_obj.summary, # original abstract
                            'pdf_link': paper_obj.pdf_link,
                            'published_date': published_dt.isoformat(), # ensure string for template
                            'authors': paper_obj.authors,
                            'primary_category': paper_obj.primary_category
                        })
                
                if not filtered_papers:
                    current_app.logger.info(f"Newsletter: No recent papers found for subscriber {subscriber.email_hash} with query '{subscriber_query}'. Skipping for this subscriber.")
                    continue # Move to the next subscriber
                
                current_app.logger.info(f"Newsletter: Fetched {len(filtered_papers)} recent papers for subscriber {subscriber.email_hash} with query '{subscriber_query}'.")
            
            except (ArxivAPIException, NetworkException, ParsingException, ValidationException) as e:
                current_app.logger.error(f"Newsletter: Error fetching papers from arXiv for subscriber {subscriber.email_hash} (query: '{subscriber_query}'): {e}", exc_info=True)
                continue # Skip this subscriber if paper fetching fails
            except Exception as e:
                current_app.logger.error(f"Newsletter: Unexpected error fetching papers for subscriber {subscriber.email_hash} (query: '{subscriber_query}'): {e}", exc_info=True)
                continue # Skip this subscriber

            # 3. Generate AI Summaries (for a subset)
            papers_with_summaries = summarize_abstracts_for_newsletter(filtered_papers, max_papers_to_summarize=5)

            if not papers_with_summaries:
                current_app.logger.info(f"Newsletter: No papers to include after summarization attempt for subscriber {subscriber.email_hash}. Skipping.")
                continue # Skip this subscriber

            # 4. Compile and Send Newsletter (Moved inside the loop)
            newsletter_subject = f"Your Personalized AI Research Newsletter - {datetime.now().strftime('%Y-%m-%d')}"
            site_url = current_app.config.get('SITE_URL', url_for('main.index', _external=True))
            unsubscribe_url = url_for('main.index', _external=True) # Placeholder

            try:
                recipient_email = subscriber.email 
                if recipient_email == "[email decryption failed]":
                    current_app.logger.error(f"Newsletter: Failed to decrypt email for subscriber ID {subscriber.id}. Skipping.")
                    # failed_count handling will be tricky if we count globally vs per email attempt
                    continue

                html_content = render_template(
                    'emails/newsletter_email.html',
                    papers=papers_with_summaries,
                    subscriber_email=recipient_email, 
                    unsubscribe_url=unsubscribe_url, 
                    site_url=site_url,
                    current_year=datetime.now().year
                )
                
                success = send_email(
                    to_email=recipient_email,
                    subject=newsletter_subject,
                    template_name_or_html=html_content
                )
                if success:
                    current_app.logger.info(f"Newsletter: Successfully sent to {recipient_email} for query '{subscriber_query}'")
                    # sent_count logic needs adjustment if counts are global
                else:
                    current_app.logger.warning(f"Newsletter: Failed to send to {recipient_email} for query '{subscriber_query}'")
                    # failed_count logic needs adjustment
            except Exception as e:
                current_app.logger.error(f"Newsletter: Error sending to subscriber {subscriber.id} (query: '{subscriber_query}'): {e}", exc_info=True)
                # failed_count logic

        # Global sent/failed counts might need to be rethought or accumulated differently
        # For now, the per-subscriber logging provides insight.
        current_app.logger.info(f"Newsletter job finished processing all subscribers.")

def init_scheduler(app):
    """Initializes and starts the APScheduler."""
    from apscheduler.schedulers.background import BackgroundScheduler
    # from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore # For persistent jobs
    
    # For persistent jobs, configure a job store. Example:
    # jobstores = {
    #     'default': SQLAlchemyJobStore(url=app.config['SQLALCHEMY_DATABASE_URI'])
    # }
    # scheduler = BackgroundScheduler(jobstores=jobstores, timezone=app.config.get('TIMEZONE', 'UTC'))
    
    # Using a simple in-memory scheduler for now
    scheduler = BackgroundScheduler(daemon=True, timezone=app.config.get('TIMEZONE', 'UTC'))
    
    # Schedule the job
    # cron trigger: day_of_week='sun', hour=10 for Sunday at 10 AM
    # interval trigger: weeks=1
    scheduler.add_job(
        send_weekly_newsletter_job, 
        trigger='interval', 
        weeks=1, 
        # Or use cron:
        # trigger='cron',
        # day_of_week='sun', # 0-6 or mon,tue,wed,thu,fri,sat,sun
        # hour=9,
        # minute=0,
        id='weekly_newsletter_job', 
        replace_existing=True
    )
    
    try:
        scheduler.start()
        app.logger.info("APScheduler started successfully with weekly newsletter job.")
    except Exception as e:
        app.logger.error(f"Error starting APScheduler: {e}", exc_info=True)

    # It's good practice to shut down the scheduler when the app exits
    import atexit
    atexit.register(lambda: scheduler.shutdown() if scheduler.running else None)
    
    app.scheduler = scheduler # Make it accessible via app object if needed 