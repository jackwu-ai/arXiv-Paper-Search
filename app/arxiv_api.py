import requests
import time
import logging
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
from typing import List, Optional
from .models import ArxivPaper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"
REQUEST_THROTTLE_SECONDS = 3.1  # Slightly more than 3 seconds to be safe
DEFAULT_TIMEOUT_SECONDS = 10 # Default timeout for requests
MAX_RETRIES = 3 # Maximum number of retries for a request

NAMESPACES = {
    'atom': 'http://www.w3.org/2005/Atom',
    'arxiv': 'http://arxiv.org/schemas/atom'
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
        The fully formed query URL or None if parameters are invalid.
    """
    if not search_query and not id_list:
        logger.error("Either search_query or id_list must be provided.")
        return None
    if search_query and id_list:
        logger.error("Cannot use both search_query and id_list simultaneously.") # As per arXiv API docs, these are mutually exclusive in practice for typical use cases
        return None

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

def make_api_request(query_url: str):
    """
    Makes a request to the arXiv API, handling retries and rate limiting.

    Args:
        query_url: The URL to request.

    Returns:
        The API response text (XML) or None if an error occurs.
    """
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Attempting to fetch URL (attempt {attempt + 1}/{MAX_RETRIES}): {query_url}")
            time.sleep(REQUEST_THROTTLE_SECONDS) # Adhere to rate limits before making the request
            response = requests.get(query_url, timeout=DEFAULT_TIMEOUT_SECONDS)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
            logger.info(f"Successfully fetched URL: {query_url}")
            return response.text
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred: {e} - Status code: {e.response.status_code}")
            # Specific handling for rate limiting if arXiv uses a specific status code like 429
            if e.response.status_code == 429: # Too Many Requests
                sleep_time = REQUEST_THROTTLE_SECONDS * (attempt + 2) # Exponential backoff component
                logger.warning(f"Rate limit likely hit. Sleeping for {sleep_time:.2f} seconds.")
                time.sleep(sleep_time)
            elif e.response.status_code >= 500: # Server-side errors, worth retrying
                logger.warning(f"Server error ({e.response.status_code}). Retrying after a short delay...")
            else: # Client-side errors (4xx other than 429) are unlikely to succeed on retry
                logger.error(f"Client error ({e.response.status_code}). Not retrying.")
                return None
        except requests.exceptions.Timeout:
            logger.warning(f"Request timed out for {query_url}. Attempt {attempt + 1} of {MAX_RETRIES}.")
        except requests.exceptions.RequestException as e:
            logger.error(f"An unexpected error occurred: {e}. Attempt {attempt + 1} of {MAX_RETRIES}.")
        
        if attempt < MAX_RETRIES - 1:
            logger.info(f"Waiting before next retry...")
            # General small delay before retrying, specific rate limit delay handled above
            time.sleep(REQUEST_THROTTLE_SECONDS * (attempt +1) ) 
        else:
            logger.error(f"All {MAX_RETRIES} retries failed for URL: {query_url}")
    return None

def search_papers(query: str = None, ids: list = None, start_index: int = 0, count: int = 10, sort_by: str = "relevance", sort_order: str = "descending") -> List[ArxivPaper] | None:
    """
    High-level function to search for papers on arXiv.

    Args:
        query: The search query string.
        ids: A list of arXiv IDs.
        start_index: The starting index for results.
        count: The number of results to fetch.
        sort_by: Sorting criterion.
        sort_order: Sorting order.

    Returns:
        A list of ArxivPaper objects or None on error.
    """
    logger.info(f"Searching papers with query='{query}', ids='{ids}', start={start_index}, count={count}")
    query_url = construct_query_url(
        search_query=query,
        id_list=ids,
        start=start_index,
        max_results=count,
        sortBy=sort_by,
        sortOrder=sort_order
    )

    if not query_url:
        logger.error("Failed to construct query URL in search_papers.")
        return None

    response_xml = make_api_request(query_url)

    if response_xml:
        # Placeholder for parsing logic (Subtask 2.2 and 2.3)
        logger.info("API request successful. XML response received.")
        # For now, just returning the raw XML. Parsing will be implemented later.
        # return response_xml 
        parsed_papers = parse_arxiv_xml(response_xml)
        if parsed_papers is not None:
            logger.info(f"Successfully parsed {len(parsed_papers)} papers from XML.")
            return parsed_papers
        else:
            logger.error("Failed to parse XML response in search_papers.")
            return None # Or an empty list, depending on desired error handling for the caller
    else:
        logger.error("API request failed after multiple retries in search_papers.")
        return None

def parse_arxiv_xml(xml_string: str) -> List[ArxivPaper] | None:
    """
    Parses the XML response from arXiv API into a list of ArxivPaper objects.

    Args:
        xml_string: The raw XML string from the API.

    Returns:
        A list of ArxivPaper objects, or None if parsing fails.
    """
    try:
        root = ET.fromstring(xml_string)
        papers = []
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

        return papers

    except ET.ParseError as e:
        logger.error(f"Failed to parse XML string: {e}")
        logger.error(f"Problematic XML snippet (first 500 chars): {xml_string[:500]}...")
        return None
    except Exception as e: # Catch any other unexpected errors during parsing
        logger.error(f"An unexpected error occurred during XML parsing: {e}")
        logger.error(f"Problematic XML snippet (first 500 chars): {xml_string[:500]}...")
        return None

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