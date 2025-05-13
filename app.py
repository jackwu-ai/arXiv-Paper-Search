print(f"Executing app.py from: {__file__}") # Print the path of the executing file
import sys
sys.path.insert(0, '.') # Ensure current directory is prioritized for imports

import logging
from flask import Flask, render_template, request, jsonify
from app.arxiv_api import search_papers
from app.exceptions import ArxivAPIException, ValidationException
from openai import OpenAI, RateLimitError, APIError # Import new classes
import os
import datetime

# Import custom template filters
from app import template_filters # Assuming this import works from the top-level app.py
from app import cache # Import the cache object

# Initialize Flask app
app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
cache.init_app(app) # Initialize cache with this app instance

# Register custom template filters directly onto this app instance
app.jinja_env.filters['format_date'] = template_filters.format_date
app.jinja_env.filters['truncate_text'] = template_filters.truncate_text
app.jinja_env.filters['highlight'] = template_filters.highlight_terms
app.jinja_env.filters['sanitize_html'] = template_filters.sanitize_html
app.jinja_env.filters['format_authors'] = template_filters.format_authors

# Add Python built-ins to Jinja environment if needed (from app/__init__.py)
app.jinja_env.globals['min'] = min
app.jinja_env.globals['max'] = max 

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure that the logger for 'app' is also configured if it's different
app_logger = logging.getLogger('app')
if not app_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    handler.setFormatter(formatter)
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)

@app.context_processor
def inject_now():
    return {'now': datetime.datetime.utcnow}

@app.route('/')
def index():
    app_logger.info("Homepage accessed")
    query = request.args.get('query')
    if query:
        return render_template('index.html', query=query, title=f"Search Results for '{query}'")
    return render_template('index.html', title='arXiv Paper Search')

@app.route('/search')
def search():
    app_logger.info("Search route accessed")
    query = request.args.get('query')
    page = int(request.args.get('page', 1))
    start_index = (page - 1) * 10
    papers = []
    total_results = 0
    total_pages = 0
    error_message = None

    if not query:
        error_message = "Please enter a search term."
        return render_template('index.html', 
                               error_message=error_message, 
                               query=query, 
                               current_page=page, 
                               papers=papers, 
                               total_pages=total_pages, 
                               total_results=total_results, 
                               start_index=start_index, 
                               end_index=start_index) 

    try:
        app_logger.info(f"Searching for query: '{query}', page: {page}")
        results_per_page = 10 
        search_results_data = search_papers(query=query, start_index=start_index, count=results_per_page)
        
        papers = search_results_data.get('papers', [])
        total_results = search_results_data.get('total_results', 0)
        if total_results > 0 and results_per_page > 0:
            total_pages = (total_results + results_per_page - 1) // results_per_page
        else:
            total_pages = 0
        
        app_logger.info(f"Query '{query}' yielded {len(papers)} papers on page {page}. Total results: {total_results}, Total pages: {total_pages}")
        if not papers and total_results == 0:
            error_message = f"No results found for '{query}'."

    except ValidationException as e:
        app_logger.error(f"Validation error during search: {e}")
        error_message = str(e)
    except ArxivAPIException as e:
        app_logger.error(f"arXiv API error during search: {e} (Status: {e.status_code if hasattr(e, 'status_code') else 'N/A'})")
        error_message = str(e)
    except Exception as e:
        app_logger.error(f"An unexpected error occurred during search: {e}", exc_info=True)
        error_message = "An unexpected error occurred. Please try again."
    
    return render_template('index.html', 
                           papers=papers, 
                           query=query, 
                           page=page,
                           total_pages=total_pages, 
                           total_results=total_results, 
                           start_index=start_index, 
                           end_index=start_index + len(papers) -1 if papers else start_index,
                           error_message=error_message,
                           results_per_page=results_per_page)

@app.route('/api/summarize', methods=['POST'])
def summarize_abstracts():
    app_logger.info("Received request to /api/summarize")
    try:
        data = request.get_json()
        if not data or 'abstracts' not in data or not isinstance(data['abstracts'], list):
            app_logger.warning("Invalid request format: 'abstracts' field missing or not a list.")
            return jsonify({"error": "Invalid request format. 'abstracts' field (list of strings) is required."}), 400

        abstracts = data['abstracts']
        if not abstracts:
            app_logger.warning("No abstracts provided for summarization.")
            return jsonify({"error": "No abstracts provided."}), 400

        # Configure OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            app_logger.error("OPENAI_API_KEY not found in environment variables.")
            return jsonify({"error": "OpenAI API key not configured on the server."}), 500
        
        client = OpenAI(api_key=api_key) # Initialize the client

        combined_abstracts = "\\n\\n---\\n\\n".join(abstracts)
        
        # Limit the length of the combined abstracts to avoid exceeding token limits (approx. 3000 words for a buffer)
        # A more robust solution would involve token counting.
        max_words = 3000 
        if len(combined_abstracts.split()) > max_words:
            app_logger.warning(f"Combined abstracts exceed {max_words} words. Truncating.")
            combined_abstracts = ' '.join(combined_abstracts.split()[:max_words])

        prompt = f"Please summarize the key findings, methodologies, and conclusions from the following research paper abstracts. Provide a concise overview that highlights the main contributions of each paper if possible, and then a brief overall synthesis if themes emerge. Abstracts:\\n\\n{combined_abstracts}"

        app_logger.info(f"Attempting to summarize {len(abstracts)} abstracts.")

        # Simple retry mechanism
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant skilled in summarizing academic research papers."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=1000  # Adjust as needed, ensure it's reasonable for summaries
                )
                summary = response.choices[0].message.content.strip()
                app_logger.info(f"Successfully generated summary for {len(abstracts)} abstracts.")
                return jsonify({"summary": summary})
            except RateLimitError as e:
                app_logger.warning(f"OpenAI RateLimitError (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt + 1 == max_retries:
                    return jsonify({"error": "OpenAI API rate limit exceeded. Please try again later."}), 429
            except APIError as e:
                app_logger.error(f"OpenAI API error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt + 1 == max_retries:
                    return jsonify({"error": f"An error occurred with the OpenAI API: {str(e)}"}), 500
            except Exception as e:
                app_logger.error(f"Unexpected error during OpenAI API call (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt + 1 == max_retries:
                    return jsonify({"error": "An unexpected error occurred while generating the summary."}), 500

        # Fallback if all retries fail (though specific errors should have returned earlier)
        return jsonify({"error": "Failed to generate summary after multiple attempts."}), 500

    except Exception as e:
        app_logger.error(f"Error in /api/summarize: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500

# Health check endpoint
@app.route('/health')
def health_check():
    pass

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)