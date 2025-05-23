import requests
import time
import logging
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
from typing import List, Optional, Union, Dict
from .models import ArxivPaper
from .exceptions import (
    ArxivAPIException,
    NetworkException,
    ParsingException,
    ValidationException
)
from flask import current_app
from .extensions import cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"
REQUEST_THROTTLE_SECONDS = 3.1  # Slightly more than 3 seconds to be safe
DEFAULT_TIMEOUT_SECONDS = 10 # Default timeout for requests
MAX_RETRIES = 3 # Maximum number of retries for a request

NAMESPACES = {
    'atom': 'http://www.w3.org/2005/Atom',
    'arxiv': 'http://arxiv.org/schemas/atom',
    'opensearch': 'http://a9.com/-/spec/opensearch/1.1/'
}

def construct_query_url(search_query: str = None, id_list: list = None, start: int = 0, max_results: int = 10, sortBy: str = "relevance", sortOrder: str = "descending") -> str:
    """
    Constructs the query URL for the arXiv API.

    Args:
        search_query: The query string (e.g., 'ti:"electron" AND au:"bohr"').
        id_list: A list of arXiv IDs.
        start: The index of the first result to return.
        max_results: The maximum number of results to return.
        sortBy: The sorting criteria (e.g., 'relevance', 'lastUpdatedDate', 'submittedDate').
        sortOrder: The sorting order ('ascending' or 'descending').

    Returns:
        The fully formed query URL.
    Raises:
        ValidationException: If parameters are invalid.
    """
    if not search_query and not id_list:
        msg = "Either search_query or id_list must be provided."
        logger.error(msg)
        raise ValidationException(msg)
    if search_query and id_list:
        msg = "Cannot use both search_query and id_list simultaneously."
        logger.error(msg)
        raise ValidationException(msg)

    query_params = {
        "start": start,
        "max_results": max_results,
        "sortBy": sortBy,
        "sortOrder": sortOrder
    }

    if search_query:
        query_params["search_query"] = search_query
    elif id_list:
        query_params["id_list"] = ",".join(id_list)
    
    encoded_params = urlencode(query_params)
    return f"{ARXIV_API_URL}?{encoded_params}"

def make_api_request(query_url: str) -> str:
    """
    Makes a request to the arXiv API, handling retries and rate limiting.

    Args:
        query_url: The URL to request.

    Returns:
        The API response text (XML).
    Raises:
        NetworkException: If the request times out after all retries, or for rate limit errors / server errors.
        ArxivAPIException: If a client error (4xx, not 429) occurs or for other request-related errors.
    """
    last_exception = None
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Attempting to fetch URL (attempt {attempt + 1}/{MAX_RETRIES}): {query_url}")
            time.sleep(REQUEST_THROTTLE_SECONDS) 
            response = requests.get(query_url, timeout=DEFAULT_TIMEOUT_SECONDS)
            response.raise_for_status()  
            logger.info(f"Successfully fetched URL: {query_url}")
            return response.text
        except requests.exceptions.HTTPError as e:
            last_exception = e
            logger.error(f"HTTP error occurred: {e} - Status code: {e.response.status_code}")
            if e.response.status_code == 429:
                if attempt == MAX_RETRIES - 1:
                    raise NetworkException(message="arXiv API rate limit exceeded. Please try again later.", original_exception=e, status_code=429)
                sleep_time = REQUEST_THROTTLE_SECONDS * (attempt + 2) 
                logger.warning(f"Rate limit likely hit. Sleeping for {sleep_time:.2f} seconds.")
                time.sleep(sleep_time)
            elif e.response.status_code >= 500:
                if attempt == MAX_RETRIES - 1:
                    raise NetworkException(message=f"arXiv API server error.", original_exception=e, status_code=e.response.status_code)
                logger.warning(f"Server error ({e.response.status_code}). Retrying after a short delay...")
            else: # Client-side errors (4xx other than 429)
                logger.error(f"Client error ({e.response.status_code}). Not retrying.")
                raise ArxivAPIException(message=f"Client error with arXiv API request.", original_exception=e, status_code=e.response.status_code)
        except requests.exceptions.Timeout as e:
            last_exception = e
            logger.warning(f"Request timed out for {query_url}. Attempt {attempt + 1} of {MAX_RETRIES}.")
            if attempt == MAX_RETRIES - 1:
                raise NetworkException(message="Request to arXiv API timed out.", original_exception=e)
        except requests.exceptions.RequestException as e: # Catch other generic request exceptions
            last_exception = e
            logger.error(f"An unexpected request error occurred: {e}. Attempt {attempt + 1} of {MAX_RETRIES}.")
            if attempt == MAX_RETRIES - 1:
                # Using NetworkException as it seems more fitting for general request failures than a generic ArxivAPIException
                raise NetworkException(f"A general network or request error occurred: {e}", original_exception=e)
        
        if attempt < MAX_RETRIES - 1:
            logger.info(f"Waiting before next retry...")
            time.sleep(REQUEST_THROTTLE_SECONDS * (attempt + 1))
    
    # This block should ideally not be reached if exceptions in the loop are raised correctly on the final attempt.
    # However, it serves as a defensive fallback.
    if last_exception: # Should always be true if loop finishes without returning
        logger.error(f"All {MAX_RETRIES} retries failed for URL: {query_url}. Last error: {type(last_exception).__name__}: {last_exception}")
        # Re-evaluate the type of last_exception to raise the most specific custom error possible
        if isinstance(last_exception, requests.exceptions.Timeout):
            raise NetworkException(message="Request to arXiv API timed out (fallback).", original_exception=last_exception)
        elif isinstance(last_exception, requests.exceptions.HTTPError):
            if last_exception.response.status_code == 429:
                raise NetworkException(message="arXiv API rate limit exceeded (fallback).", original_exception=last_exception, status_code=429)
            elif last_exception.response.status_code >= 500:
                raise NetworkException(message=f"arXiv API server error (fallback).", original_exception=last_exception, status_code=last_exception.response.status_code)
            else:
                raise ArxivAPIException(message=f"Client error with arXiv API request (fallback).", original_exception=last_exception, status_code=last_exception.response.status_code)
        # For other RequestException types or if it's an unknown last_exception type.
        raise NetworkException(f"All retries failed. Last error: {last_exception}", original_exception=last_exception)
    
    # Absolute fallback, should ideally never be reached.
    raise ArxivAPIException(f"All {MAX_RETRIES} retries failed for URL: {query_url} without a specific final exception being categorized.")

@cache.memoize()
def search_papers(query: str = None, ids: list = None, start_index: int = 0, count: int = 10, sort_by: str = "relevance", sort_order: str = "descending") -> Dict[str, Union[List[ArxivPaper], int]]:
    """
    High-level function to search for papers on arXiv.
    Returns a dictionary with 'papers' list and 'total_results' count.
    Raises ArxivAPIException, NetworkException, ParsingException or ValidationException on failure.
    """
    # construct_query_url will raise ValidationException if params are bad
    query_url = construct_query_url(
        search_query=query,
        id_list=ids,
        start=start_index,
        max_results=count,
        sortBy=sort_by,
        sortOrder=sort_order
    )
    # make_api_request will raise appropriate ArxivAPIError subclass on failure
    response_xml = make_api_request(query_url)
    
    # parse_arxiv_xml will raise ArxivParsingError or ArxivAPIError on failure
    parsed_data = parse_arxiv_xml(response_xml) 
    
    logger.info(f"Successfully processed search. Query='{query}', ids='{ids}', Found {len(parsed_data['papers'])} papers. Total results available: {parsed_data['total_results']}")
    return parsed_data

def parse_arxiv_xml(xml_string: str) -> Dict[str, Union[List[ArxivPaper], int]]:
    """
    Parses the XML response from arXiv API into a list of ArxivPaper objects and total results count.
    Raises ParsingException on failure to parse XML or other unexpected errors during parsing.
    """
    try:
        root = ET.fromstring(xml_string)
        papers = []
        total_results = 0

        # Extract total results
        total_results_tag = root.find('opensearch:totalResults', NAMESPACES)
        if total_results_tag is not None and total_results_tag.text is not None:
            try:
                total_results = int(total_results_tag.text)
            except ValueError:
                logger.warning(f"Could not parse totalResults value: '{total_results_tag.text}'. Defaulting to 0.")
                total_results = 0 # Default or handle as critical error
        else:
            logger.warning("opensearch:totalResults tag not found or empty. Defaulting to 0.")

        for entry in root.findall('atom:entry', NAMESPACES):
            paper_data = {}
            # Helper to find text, returning None if element is not found
            def find_text(element, path, namespace_map=NAMESPACES):
                found = element.find(path, namespace_map)
                return found.text.strip() if found is not None and found.text else None

            # Helper to find all texts for a given path (e.g., multiple authors)
            def find_all_texts(element, path, sub_path, namespace_map=NAMESPACES):
                elements = element.findall(path, namespace_map)
                texts = []
                for el in elements:
                    sub_el = el.find(sub_path, namespace_map)
                    if sub_el is not None and sub_el.text:
                        texts.append(sub_el.text.strip())
                return texts
            
            # Helper to find an attribute
            def find_attribute(element, path, attribute_name, namespace_map=NAMESPACES):
                found = element.find(path, namespace_map)
                return found.get(attribute_name) if found is not None else None

            # Extracting common fields into paper_data dictionary
            id_full_url = find_text(entry, 'atom:id')
            paper_data['id_str'] = id_full_url.split('/abs/')[-1] if id_full_url else None
            paper_data['title'] = find_text(entry, 'atom:title')
            paper_data['summary'] = find_text(entry, 'atom:summary')
            paper_data['published_date'] = find_text(entry, 'atom:published')
            paper_data['updated_date'] = find_text(entry, 'atom:updated')
            
            paper_data['authors'] = find_all_texts(entry, 'atom:author', 'atom:name')
            
            categories_elements = entry.findall('atom:category', NAMESPACES)
            paper_data['categories'] = [cat.get('term') for cat in categories_elements if cat.get('term')]

            if paper_data['id_str']:
                paper_data['pdf_link'] = f"http://arxiv.org/pdf/{paper_data['id_str']}.pdf"
            else:
                paper_data['pdf_link'] = None

            # arXiv specific fields
            paper_data['doi'] = find_text(entry, 'arxiv:doi', NAMESPACES)
            paper_data['primary_category'] = find_attribute(entry, 'arxiv:primary_category', 'term', NAMESPACES)
            
            # Instantiate ArxivPaper object
            try:
                # Ensure all required fields for ArxivPaper are present or have defaults
                # The ArxivPaper dataclass might raise ValueError if required fields are missing
                paper_obj = ArxivPaper(**paper_data)
                papers.append(paper_obj)
            except ValueError as ve:
                logger.warning(f"Skipping entry due to validation error: {ve}. Data: {paper_data}")
            except TypeError as te:
                 logger.warning(f"Skipping entry due to TypeError (likely missing field for dataclass): {te}. Data: {paper_data}")

        return {'papers': papers, 'total_results': total_results}

    except ET.ParseError as e:
        logger.error(f"Failed to parse XML string: {e}")
        logger.error(f"Problematic XML snippet (first 500 chars): {xml_string[:500]}...")
        raise ParsingException(f"Failed to parse XML response from arXiv.", original_exception=e)
    except Exception as e: 
        logger.error(f"An unexpected error occurred during XML parsing: {e}")
        logger.error(f"Problematic XML snippet (first 500 chars): {xml_string[:500]}...")
        raise ParsingException(f"An unexpected error occurred during XML parsing of arXiv data.", original_exception=e)

# Example usage (for testing during development)
if __name__ == "__main__":
    # test_url = construct_query_url(search_query="cat:cs.CV AND ti:\"object detection\"", max_results=2)
    # print(f"Constructed URL: {test_url}")
    # if test_url:
    #     response_xml = make_api_request(test_url)
    #     if response_xml:
    #         print("\\nAPI Response XML (first 500 chars):")
    #         print(response_xml[:500] + "...")
    #         # Further parsing will be handled in subtask 2.2
    pass 