from flask import Blueprint, jsonify, render_template, current_app, request, flash, url_for, redirect
from app.arxiv_api import search_papers
# Updated custom exception imports
from app.exceptions import (
    ArxivAPIException,
    NetworkException,
    ParsingException,
    ValidationException
)
import math
import os # Added for OpenAI API Key
import datetime # Added for subscription confirmation
from openai import OpenAI, RateLimitError, APIError # Added for summarization
from threading import Thread

# Imports for subscription routes
from app.models import db, Subscription, _generate_email_hash
from app.utils import send_email, generate_confirmation_token, verify_confirmation_token
from app import limiter # Import limiter from app/__init__.py
from app.scheduler import send_weekly_newsletter_job, summarize_abstracts_for_newsletter # Import the newsletter job and summarize_abstracts_for_newsletter

main = Blueprint('main', __name__)

@main.route('/ping')
def ping():
    """A simple ping endpoint to check if the blueprint is registered and working."""
    return jsonify(message="pong"), 200

# The actual index and search routes will be defined in later subtasks (e.g., 5.2, 5.3)
# For example:
# from flask import render_template
@main.route('/')
@main.route('/index')
def index():
    current_app.logger.info('Homepage accessed')
    # Check for flashed messages from a previous redirect if an empty query was submitted
    # This part is tricky if we want to show a message specifically for an empty search attempt.
    # For now, the template handles display based on query presence.
    return render_template('index.html', title='Homepage') # Simplified from root app.py, can be enhanced later

@main.route('/search')
def search():
    query = request.args.get('query', '').strip()
    papers = []
    error_message = None
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    total_pages = 0
    total_results_count = 0
    results_per_page = current_app.config.get('RESULTS_PER_PAGE', 10)

    if not query:
        return render_template('index.html', title='Search', query=query, error_message="Please enter a search query.",
                               page=page, total_pages=0, total_results=0, papers=[]) # Pass all expected args

    try:
        start_index = (page - 1) * results_per_page
        current_app.logger.info(f'Searching for query: "{query}", page: {page}, start_index: {start_index}, count: {results_per_page}')
        
        api_result = search_papers(query=query, start_index=start_index, count=results_per_page)
        
        papers = api_result['papers']
        total_results_count = api_result['total_results']
        
        if total_results_count > 0 and results_per_page > 0:
            total_pages = math.ceil(total_results_count / results_per_page)
        else:
            total_pages = 0 

        if not papers and total_results_count > 0 and page > total_pages and total_pages > 0:
             current_app.logger.warning(f"Requested page {page} is out of bounds ({total_pages} total pages).")
        if not papers and total_results_count == 0 and query:
            error_message = f"No results found for '{query}'."

        current_app.logger.info(f'Query "{query}" yielded {len(papers)} papers on page {page}. Total results: {total_results_count}, Total pages: {total_pages}')

    except ValidationException as e:
        current_app.logger.warning(f'Validation error for query "{query}": {e}', exc_info=True)
        error_message = str(e) # Simpler error message from root app.py
    except ArxivAPIException as e:
        current_app.logger.error(f"arXiv API error for query '{query}': {e} (Status: {e.status_code if hasattr(e, 'status_code') else 'N/A'})")
        error_message = str(e) # Simpler error message from root app.py
    except NetworkException as e: # Added from root app.py logic
        current_app.logger.error(f'Network error for query "{query}": {e}', exc_info=True)
        error_message = "Could not connect to the arXiv service. Please check your internet connection or try again later."
        if hasattr(e, 'status_code') and e.status_code:
             error_message += f" (Server responded with status: {e.status_code})"
    except ParsingException as e: # Added from root app.py logic
        current_app.logger.error(f'Parsing error for query "{query}": {e}', exc_info=True)
        error_message = "There was an issue processing the data received from arXiv. Please try again. If the problem persists, the arXiv service might be temporarily unavailable."
    except Exception as e: 
        current_app.logger.error(f'Unexpected error during search for query "{query}": {e}', exc_info=True)
        error_message = "An unexpected error occurred. Please try again later."
    
    return render_template('index.html', 
                           title=f'Search Results for "{query}"' if query and not error_message and papers else 'Search', 
                           query=query, 
                           papers=papers, 
                           error_message=error_message,
                           page=page,
                           total_pages=total_pages,
                           total_results=total_results_count,
                           results_per_page=results_per_page,
                           start_index=start_index if papers else 0, # Corrected start_index and end_index from root app.py
                           end_index=start_index + len(papers) -1 if papers else (start_index if query else 0)
                           ) 

# --- Routes moved from root app.py ---

@main.route('/api/summarize_papers', methods=['POST'])
def summarize_abstracts():
    current_app.logger.info("Received request to /api/summarize_papers")
    try:
        data = request.get_json()
        if not data or 'papers' not in data or not isinstance(data['papers'], list):
            current_app.logger.warning("Invalid request format: 'papers' field missing or not a list of objects.")
            return jsonify({"error": "Invalid request format. 'papers' field (list of objects with id, title, abstract_text) is required."}), 400

        input_papers = data['papers']
        if not input_papers:
            current_app.logger.warning("No papers provided for summarization.")
            return jsonify({"error": "No papers provided."}), 400

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            current_app.logger.error("OPENAI_API_KEY not found in environment variables.")
            return jsonify({"error": "OpenAI API key not configured on the server."}), 500
        
        client = OpenAI(api_key=api_key)
        
        summarized_papers_data = []
        max_retries_per_paper = 2

        for paper_data in input_papers:
            if not isinstance(paper_data, dict) or not all(key in paper_data for key in ['id', 'title', 'abstract_text']):
                current_app.logger.warning(f"Skipping invalid paper object: {paper_data}")
                summarized_papers_data.append({
                    "id": paper_data.get("id", "unknown"), 
                    "title": paper_data.get("title", "Unknown Title"), 
                    "takeaways_text": "Error: Invalid paper data provided."
                })
                continue

            paper_id = paper_data['id']
            title = paper_data['title']
            abstract = paper_data['abstract_text']

            if not abstract or not abstract.strip():
                current_app.logger.warning(f"Empty abstract for paper ID {paper_id} ('{title}'). Skipping summarization for this paper.")
                summarized_papers_data.append({
                    "id": paper_id, 
                    "title": title, 
                    "takeaways_text": "Abstract was empty, no takeaways generated."
                })
                continue
            
            # Truncate individual abstract if too long (though less likely for single abstracts)
            max_words_per_abstract = 3000 
            if len(abstract.split()) > max_words_per_abstract:
                current_app.logger.warning(f"Abstract for paper '{title}' (ID: {paper_id}) exceeds {max_words_per_abstract} words. Truncating.")
                abstract = ' '.join(abstract.split()[:max_words_per_abstract])

            prompt = (
                f"Extract exactly 3 key takeaways from the following research paper abstract. Present these takeaways as a numbered list. "
                f"Each takeaway should be concise and highlight a main contribution, finding, or methodology.\n\n"
                f"Title: {title}\n"
                f"Abstract:\n{abstract}"
            )
            current_app.logger.info(f"Attempting to generate 3 key takeaways for paper: '{title}' (ID: {paper_id}).")
            
            takeaways_text = "Error: Could not generate takeaways."
            for attempt in range(max_retries_per_paper):
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant skilled in extracting key takeaways from academic research papers."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.5,
                        max_tokens=300 # Max tokens for 3 takeaways from one abstract
                    )
                    takeaways_text = response.choices[0].message.content.strip()
                    current_app.logger.info(f"Successfully generated takeaways for paper '{title}' (ID: {paper_id}).")
                    break 
                except RateLimitError as e:
                    current_app.logger.warning(f"OpenAI RateLimitError for paper '{title}' (attempt {attempt + 1}/{max_retries_per_paper}): {e}")
                    if attempt + 1 == max_retries_per_paper:
                        takeaways_text = "Error: OpenAI API rate limit exceeded."
                except APIError as e:
                    current_app.logger.error(f"OpenAI API error for paper '{title}' (attempt {attempt + 1}/{max_retries_per_paper}): {e}")
                    if attempt + 1 == max_retries_per_paper:
                        takeaways_text = f"Error: OpenAI API error ({str(e)})."
                except Exception as e:
                    current_app.logger.error(f"Unexpected error for paper '{title}' (attempt {attempt + 1}/{max_retries_per_paper}): {e}")
                    if attempt + 1 == max_retries_per_paper:
                        takeaways_text = "Error: Unexpected error during takeaway generation."
            
            summarized_papers_data.append({"id": paper_id, "title": title, "takeaways_text": takeaways_text})

        current_app.logger.info(f"Finished processing {len(input_papers)} papers for key takeaways.")
        return jsonify({"papers_with_takeaways": summarized_papers_data})

    except Exception as e:
        current_app.logger.error(f"Error in /api/summarize_papers: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred processing paper takeaways."}), 500

@main.route('/api/summarize_single_paper', methods=['POST'])
def summarize_single_paper():
    current_app.logger.info("Received request to /api/summarize_single_paper")
    try:
        data = request.get_json()
        if not data or not all(key in data for key in ['paper_id', 'title', 'abstract_text']):
            current_app.logger.warning("Invalid request format for single paper summary.")
            return jsonify({"error": "Invalid request. 'paper_id', 'title', and 'abstract_text' are required."}), 400

        paper_id = data['paper_id']
        title = data['title']
        abstract = data['abstract_text']

        if not abstract or not abstract.strip():
            current_app.logger.warning(f"Empty abstract provided for paper {paper_id} ({title}).")
            return jsonify({"error": "Cannot summarize an empty abstract."}), 400

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            current_app.logger.error("OPENAI_API_KEY not found.")
            return jsonify({"error": "OpenAI API key not configured."}), 500
        
        client = OpenAI(api_key=api_key)
        prompt = (
            f"Please provide a detailed, structured summary of the research paper titled '{title}'. "
            f"The summary should be suitable for a single page (approximately 300-500 words). "
            f"Focus on clearly articulating the paper's core problem, objectives, key methodologies, main findings/results, and primary conclusions or contributions. "
            f"Organize the summary logically, perhaps with subheadings for clarity if appropriate (e.g., Introduction/Background, Methods, Results, Discussion/Conclusion). "
            f"Avoid overly technical jargon where possible, or briefly explain it. Ensure the summary is comprehensive yet concise.\\n\\n"
            f"Abstract of the paper:\n{abstract}"
        )
        current_app.logger.info(f"Attempting to generate detailed summary for paper: {paper_id} - '{title}'")
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert research assistant, skilled at creating detailed and structured summaries of academic papers."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4,
                    max_tokens=1200
                )
                single_summary = response.choices[0].message.content.strip()
                current_app.logger.info(f"Successfully generated single paper summary for {paper_id}.")
                return jsonify({"single_paper_summary": single_summary, "paper_id": paper_id, "title": title})
            except RateLimitError as e:
                current_app.logger.warning(f"OpenAI RateLimitError (single paper summary, attempt {attempt + 1}/{max_retries}): {e}")
                if attempt + 1 == max_retries:
                    return jsonify({"error": "OpenAI API rate limit exceeded. Please try again later.", "paper_id": paper_id}), 429
            except APIError as e:
                current_app.logger.error(f"OpenAI API error (single paper summary, attempt {attempt + 1}/{max_retries}): {e}")
                if attempt + 1 == max_retries:
                    return jsonify({"error": f"An error occurred with the OpenAI API: {str(e)}", "paper_id": paper_id}), 500
            except Exception as e:
                current_app.logger.error(f"Unexpected error during OpenAI API call (single paper summary, attempt {attempt + 1}/{max_retries}): {e}")
                if attempt + 1 == max_retries:
                    return jsonify({"error": "An unexpected error occurred while generating the single paper summary.", "paper_id": paper_id}), 500
        return jsonify({"error": "Failed to generate single paper summary after multiple attempts.", "paper_id": paper_id}), 500
    except Exception as e:
        current_app.logger.error(f"Error in /api/summarize_single_paper: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500

@main.route('/health')
def health_check():
    return jsonify({"status": "ok", "message": "Application is healthy"}), 200

# --- Subscription Routes ---
@main.route('/subscribe', methods=['POST'])
@limiter.limit(lambda: current_app.config.get('RATELIMIT_SUBSCRIBE', "10 per minute")) # Uncommented and using imported limiter
def subscribe():
    data = request.get_json()
    email = data.get('email')
    keywords = data.get('keywords') # Get keywords from the request
    if not email:
        return jsonify({'message': 'Email is required.'}), 400
    if '@' not in email or '.' not in email.split('@')[-1]:
        return jsonify({'message': 'Invalid email format.'}), 400
    try:
        hashed_email = _generate_email_hash(email)
        existing_subscription = Subscription.query.filter_by(email_hash=hashed_email).first()

        if existing_subscription:
            if existing_subscription.is_confirmed and not existing_subscription.unsubscribed_at:
                return jsonify({'message': 'This email is already subscribed and confirmed.'}), 409
            elif existing_subscription.unsubscribed_at:
                # User is re-subscribing after having unsubscribed
                token = generate_confirmation_token(email)
                existing_subscription.confirmation_token = token
                existing_subscription.is_confirmed = False # Require re-confirmation
                existing_subscription.unsubscribed_at = None # Clear unsubscription timestamp
                existing_subscription.subscribed_at = datetime.datetime.utcnow() # Update subscription time
                existing_subscription.keywords = keywords # Update keywords if provided
                db.session.commit()
                confirmation_url = url_for('.confirm_subscription', token=token, _external=True)
                send_email(
                    to_email=email, 
                    subject='Confirm Your Re-Subscription', 
                    template_name_or_html='emails/confirmation_email.html',
                    confirmation_url=confirmation_url,
                    name_or_email=email,
                    expiration_hours=current_app.config.get('SECURITY_TOKEN_MAX_AGE_HOURS', 1)
                )
                current_app.logger.info(f"Re-subscription initiated for {email}. Confirmation email sent.")
                return jsonify({'message': 'Re-subscription successful! Please check your email to confirm.'}), 201
            elif not existing_subscription.is_confirmed and not existing_subscription.unsubscribed_at:
                # Subscription was initiated but never confirmed
                token = generate_confirmation_token(email)
                existing_subscription.confirmation_token = token
                existing_subscription.is_confirmed = False # Require re-confirmation
                existing_subscription.unsubscribed_at = None # Clear unsubscription timestamp
                existing_subscription.subscribed_at = datetime.datetime.utcnow() # Update subscription time
                existing_subscription.keywords = keywords # Update keywords if provided
                db.session.commit()
                confirmation_url = url_for('.confirm_subscription', token=token, _external=True)
                send_email(
                    to_email=email, 
                    subject='Confirm Your Subscription', 
                    template_name_or_html='emails/confirmation_email.html',
                    confirmation_url=confirmation_url,
                    name_or_email=email,
                    expiration_hours=current_app.config.get('SECURITY_TOKEN_MAX_AGE_HOURS', 1)
                )
                current_app.logger.info(f"Subscription initiated for {email}. Confirmation email sent.")
                return jsonify({'message': 'Subscription successful! Please check your email to confirm.'}), 201
        else: # No existing subscription, create a new one
            token = generate_confirmation_token(email)
            new_subscription = Subscription(email=email, confirmation_token=token, keywords=keywords)
            db.session.add(new_subscription)
            db.session.commit()
            confirmation_url = url_for('.confirm_subscription', token=token, _external=True)
            send_email(
                to_email=email,
                subject='Confirm Your Subscription',
                template_name_or_html='emails/confirmation_email.html',
                confirmation_url=confirmation_url,
                name_or_email=email,
                expiration_hours=current_app.config.get('SECURITY_TOKEN_MAX_AGE_HOURS', 1)
            )
            current_app.logger.info(f"New subscription created for {email}. Confirmation email sent.")
            return jsonify({'message': 'Subscription successful! Please check your email to confirm.'}), 201
    except ValueError as ve:
        current_app.logger.warning(f"ValueError during subscription for {email}: {ve}")
        return jsonify({'message': str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Error during subscription for {email}: {e}", exc_info=True)
        return jsonify({'message': 'An internal error occurred. Please try again later.'}), 500

@main.route('/confirm_subscription', methods=['GET'])
def confirm_subscription():
    token = request.args.get('token')
    if not token:
        flash('Confirmation token is missing or invalid.', 'danger')
        return redirect(url_for('.index')) # Use . for blueprint route
    try:
        email_from_token = verify_confirmation_token(token)
        if not email_from_token:
            flash('The confirmation link is invalid or has expired.', 'danger')
            return redirect(url_for('.index'))
        hashed_email = _generate_email_hash(email_from_token)
        subscription = Subscription.query.filter_by(email_hash=hashed_email).first()
        if not subscription:
            flash('Subscription record not found. The confirmation link may be outdated or invalid.', 'danger')
            return redirect(url_for('.index'))
        if subscription.is_confirmed:
            flash('This email address has already been confirmed.', 'info')
            return redirect(url_for('.index'))
        if subscription.confirmation_token != token:
             flash('This confirmation link is outdated as a newer one may have been issued. Please use the latest confirmation email.', 'warning')
             return redirect(url_for('.index'))
        subscription.is_confirmed = True
        subscription.confirmed_at = datetime.datetime.utcnow()
        subscription.confirmation_token = None
        db.session.commit()
        send_email(
            to_email=subscription.email,
            subject='Subscription Confirmed!',
            template_name_or_html='emails/subscription_confirmed_email.html', # Ensure this template exists
            name_or_email=subscription.email
        )
        current_app.logger.info(f"Email {subscription.email} confirmed successfully.")
        flash('Your subscription has been confirmed successfully! Thank you.', 'success')
        return redirect(url_for('.index'))
    except Exception as e:
        current_app.logger.error(f"Error during email confirmation: {e}", exc_info=True)
        flash('An error occurred during confirmation. Please try again or contact support.', 'danger')
        return redirect(url_for('.index'))

@main.route('/unsubscribe-request', methods=['GET'])
def unsubscribe_request():
    """Serves the page where users can enter their email to unsubscribe."""
    return render_template('unsubscribe_page.html')

@main.route('/unsubscribe', methods=['POST'])
@limiter.limit(lambda: current_app.config.get('RATELIMIT_DEFAULT', "10 per minute")) # Uncommented and using imported limiter
def unsubscribe():
    data = request.get_json()
    if not data or not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400
    email = data['email'].lower().strip()
    # IMPORTANT: Query by email_hash for unsubscribing if email itself is encrypted and not directly queryable
    # This assumes the email passed to unsubscribe is the plain one, so we hash it for lookup.
    hashed_email = _generate_email_hash(email)
    subscription = Subscription.query.filter_by(email_hash=hashed_email).first()

    if not subscription or subscription.unsubscribed_at is not None:
        return jsonify({'message': 'Email not found or already unsubscribed.'}), 200

    subscription.is_confirmed = False
    subscription.unsubscribed_at = datetime.datetime.utcnow()
    db.session.commit()
    try:
        send_email(
            to_email=email, # Send to plain email for unsubscription confirmation
            subject="You Have Unsubscribed",
            template_name_or_html='emails/unsubscribed_email.html', # Ensure this template exists
            name_or_email=email
        )
    except Exception as e:
        current_app.logger.error(f"Error sending unsubscription confirmation email to {email}: {e}")
    return jsonify({'message': 'Successfully unsubscribed.'}), 200
    
@main.route('/admin/send_test_email', methods=['POST'])
@limiter.limit("10 per hour") # Adjusted rate limit, was "5 per hour"
def send_test_email_route():
    current_app.logger.info("Admin: Test newsletter send requested.")
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is missing.'}), 400

    target_email = data.get('email')
    keywords = data.get('keywords')
    # subject = data.get('subject', f"Test Newsletter - {datetime.datetime.now().strftime('%Y-%m-%d')}")
    # body_html_content = data.get('body') # This was for a generic email, we want to generate a newsletter

    if not target_email:
        return jsonify({'error': 'Target email is required for test send.'}), 400
    
    # Use provided keywords, or default if empty, similar to the main scheduler job
    test_query = keywords if keywords and keywords.strip() else "cat:cs.AI"
    current_app.logger.info(f"Admin: Generating test newsletter for {target_email} with query: '{test_query}'")

    try:
        # --- Simplified single-user newsletter generation logic (adapted from scheduler.py) ---
        # 1. Fetch papers based on test_query
        arxiv_results = search_papers(query=test_query, count=20, sort_by='submittedDate', sort_order='descending')
        raw_papers = arxiv_results.get('papers', [])
        one_week_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
        filtered_papers = []
        for paper_obj in raw_papers:
            published_dt = paper_obj.published_date
            if published_dt and published_dt >= one_week_ago:
                filtered_papers.append({
                    'id': paper_obj.id_str,
                    'title': paper_obj.title,
                    'summary': paper_obj.summary,
                    'pdf_link': paper_obj.pdf_link,
                    'published_date': published_dt.isoformat(),
                    'authors': paper_obj.authors,
                    'primary_category': paper_obj.primary_category
                })
        
        if not filtered_papers:
            current_app.logger.info(f"Admin Test: No recent papers found for query '{test_query}'.")
            # Still send an email, but it will say no papers found.
            # return jsonify({'message': f'No recent papers found for query "{test_query}". Test email not sent.'}), 200

        # 2. Generate AI Summaries (for a subset)
        # Using the same summarization utility from scheduler
        papers_with_summaries = summarize_abstracts_for_newsletter(filtered_papers, max_papers_to_summarize=5)

        # 3. Compile and Send Newsletter
        newsletter_subject = f"[TEST] Your Personalized AI Research Newsletter - {datetime.datetime.now().strftime('%Y-%m-%d')}"
        site_url = current_app.config.get('SITE_URL', url_for('main.index', _external=True))
        # For a test email, the unsubscribe link might point to the main page or a test unsubscribe page
        # For simplicity, using the actual unsubscribe request page URL
        unsubscribe_url = url_for('main.unsubscribe_request', _external=True) 

        html_content = render_template(
            'emails/newsletter_email.html',
            papers=papers_with_summaries, # This might be empty if no papers were found
            subscriber_email=target_email, # For display in the email if needed
            unsubscribe_url=unsubscribe_url, 
            site_url=site_url,
            current_year=datetime.datetime.now().year
        )
        
        success = send_email(
            to_email=target_email,
            subject=newsletter_subject,
            template_name_or_html=html_content
        )

        if success:
            current_app.logger.info(f"Admin: Test newsletter successfully sent to {target_email} with query '{test_query}'.")
            return jsonify({'message': f'Test newsletter sent to {target_email} with query "{test_query}".'}), 200
        else:
            current_app.logger.warning(f"Admin: Failed to send test newsletter to {target_email}.")
            return jsonify({'error': f'Failed to send test newsletter to {target_email}.'}), 500

    except (ArxivAPIException, NetworkException, ParsingException, ValidationException) as e:
        current_app.logger.error(f"Admin Test: Error fetching/processing papers from arXiv (query: '{test_query}'): {e}", exc_info=True)
        return jsonify({'error': f'Error fetching papers for test newsletter: {str(e)}'}), 500
    except Exception as e:
        current_app.logger.error(f"Admin: Error sending test newsletter: {e}", exc_info=True)
        return jsonify({'error': 'Could not send test newsletter due to an unexpected error.'}), 500 