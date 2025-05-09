from flask import Blueprint, jsonify, render_template, current_app, request, flash
from app.arxiv_api import search_papers
# Updated custom exception imports
from app.exceptions import (
    ArxivAPIException,
    NetworkException,
    ParsingException,
    ValidationException
)
import math

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
    return render_template('index.html', title='Homepage')

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
        # Instead of just rendering, flash a message and redirect or render with specific error context
        # For simplicity, we'll pass an error_message directly for the template to handle.
        # The template already has logic for: 
        # {% elif not query and request.args.get('query') is not none %} <p>Please enter a search term.</p>
        # This is fine for now.
        return render_template('index.html', title='Search', query=query, error_message="Please enter a search query.")

    try:
        start_index = (page - 1) * results_per_page
        current_app.logger.info(f'Searching for query: "{query}", page: {page}, start_index: {start_index}, count: {results_per_page}')
        # Removed cache stats logging from here for brevity, can be added back if needed for debugging
        
        api_result = search_papers(query=query, start_index=start_index, count=results_per_page)
        
        papers = api_result['papers']
        total_results_count = api_result['total_results']
        
        if total_results_count > 0 and results_per_page > 0:
            total_pages = math.ceil(total_results_count / results_per_page)
        else:
            total_pages = 0 

        if not papers and total_results_count > 0 and page > total_pages and total_pages > 0:
             current_app.logger.warning(f"Requested page {page} is out of bounds ({total_pages} total pages).")

        current_app.logger.info(f'Query "{query}" yielded {len(papers)} papers on page {page}. Total results: {total_results_count}, Total pages: {total_pages}')

    except ValidationException as e:
        current_app.logger.warning(f'Validation error for query "{query}": {e}', exc_info=True)
        error_message = "There was a problem with your search query or parameters. Please check your input and try again."
    except NetworkException as e:
        current_app.logger.error(f'Network error for query "{query}": {e}', exc_info=True)
        error_message = "Could not connect to the arXiv service. Please check your internet connection or try again later."
        if e.status_code:
             error_message += f" (Server responded with status: {e.status_code})"
    except ParsingException as e:
        current_app.logger.error(f'Parsing error for query "{query}": {e}', exc_info=True)
        error_message = "There was an issue processing the data received from arXiv. Please try again. If the problem persists, the arXiv service might be temporarily unavailable."
    except ArxivAPIException as e: 
        current_app.logger.error(f'arXiv API error for query "{query}": {e}', exc_info=True)
        error_message = "An unexpected issue occurred while communicating with the arXiv service. Please try again."
        if e.status_code:
            error_message += f" (Received API status: {e.status_code})"
    except Exception as e: 
        current_app.logger.error(f'Unexpected error during search for query "{query}": {e}', exc_info=True)
        error_message = "An unexpected error occurred. Please try again later."
    
    if error_message:
        papers = [] 
        total_results_count = 0
        total_pages = 0

    return render_template('index.html', 
                           title=f'Search Results for "{query}"' if query and not error_message else 'Search', 
                           query=query, 
                           papers=papers, 
                           error_message=error_message,
                           page=page,
                           total_pages=total_pages,
                           total_results=total_results_count,
                           results_per_page=results_per_page
                           ) 