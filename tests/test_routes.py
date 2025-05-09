import pytest
from flask import url_for, get_flashed_messages
from app import create_app, cache
import unittest.mock as mock # For mocking
import math
import requests

# Fixture to create and configure a new app instance for each test
@pytest.fixture
def app_instance():
    app = create_app(config_name='testing') # Use a 'testing' configuration
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False, # Disable CSRF for simpler form testing if needed
        "SERVER_NAME": "localhost.localdomain" # For url_for to work without active request context
    })

    # Clear cache before each test to ensure isolation
    with app.app_context():
        cache.clear()
        
    yield app

# Fixture for the test client
@pytest.fixture
def client(app_instance):
    with app_instance.app_context(): # Ensure operations like url_for are within app context
        yield app_instance.test_client()

# Fixture to automatically push an application context for tests that need it
@pytest.fixture
def app_context(app_instance):
    with app_instance.app_context():
        yield

# Mock the search_papers function for all tests in this file
@pytest.fixture(autouse=True)
def mock_search_papers(mocker):
    # This mock will be used for all tests unless a specific test re-mocks it.
    # It returns a default successful response with some papers and total results.
    mocked_search = mocker.patch('app.arxiv_api.search_papers')
    mocked_search.return_value = {
        'papers': [
            mock.MagicMock(title='Test Paper 1', authors=['Author A'], summary='Summary 1', published_date='2023-01-01T00:00:00Z', pdf_link='http://example.com/1.pdf'),
            mock.MagicMock(title='Test Paper 2', authors=['Author B'], summary='Summary 2', published_date='2023-01-02T00:00:00Z', pdf_link='http://example.com/2.pdf')
        ],
        'total_results': 2,
        'results_per_page': 10 # Assuming a default or common value
    }
    return mocked_search

def test_home_page(client, app_context):
    with app_context: # Add app_context for url_for
        response = client.get(url_for('main.index'))
    assert response.status_code == 200
    assert b"arXiv Paper Search" in response.data

# Tests for Search Route Query Edge Cases

@pytest.mark.parametrize(
    "query_string, expected_flash_message, expect_api_call",
    [
        ("", "Please enter a search query.", False),
        ("   ", "Please enter a search query.", False),
        ("a" * 1001, None, True),  # Test with a very long query
        ("!@#$%^&*()_+-={}|[]\\:\";'<>,.?/", None, True),  # Test with special characters
        ("量子コンピューティング", None, True),  # Test with Non-ASCII characters
        ("quantum'; DROP TABLE papers;--", None, True),  # Test with SQL injection attempt
        ("<script>alert('XSS')</script>", None, True)  # Test with HTML/script injection
    ]
)
def test_search_query_edge_cases(client, app_context, mock_search_papers, query_string, expected_flash_message, expect_api_call):
    """Test search route with various query string edge cases."""
    # Reset call count for each parametrized test run if the mock is autouse=True and shared
    mock_search_papers.reset_mock()

    with app_context:
        response = client.get(url_for('main.search', query=query_string))
    
    assert response.status_code == 200

    if expected_flash_message:
        # Check for flashed messages only if one is expected
        with client.session_transaction() as session:
            flashed = session.get('_flashes', [])
        assert flashed  # Ensure there are messages
        assert any(expected_flash_message in message_tuple[1] for message_tuple in flashed)
        assert not mock_search_papers.called  # API should not be called
    else:
        # If no flash message is expected, the API call should match expect_api_call
        assert mock_search_papers.called == expect_api_call
        if expect_api_call:
            # Ensure that the data check is safe for an empty paper list
            # The mock currently returns 2 papers, so this is fine.
            # If the mock could return 0 papers, this might need adjustment or a check for papers.
            assert b"Test Paper 1" in response.data 
            mock_search_papers.assert_called_once_with(query=query_string, start=0, count=10) # Assuming default page & count

def test_search_valid_query(client, app_context, mock_search_papers):
    """Test a normal, valid search query."""
    mock_search_papers.reset_mock() # Reset mock before this specific test
    with app_context: # Add app_context for url_for
        response = client.get(url_for('main.search', query='valid_query'))
    assert response.status_code == 200
    mock_search_papers.assert_called_once_with(query='valid_query', start=0, count=10)
    assert b"Test Paper 1" in response.data
    # Adjust pagination check based on mock and app config for results_per_page
    # The mock provides 2 total_results, and results_per_page is often 10 by default.
    # If total_results < results_per_page, it shows all on one page.
    assert b"Showing results 1 - 2 of 2" in response.data 

# More tests will be added here for pagination and other edge cases 

@pytest.mark.parametrize(
    "page_param_value, query_string, expected_api_start_index, expected_page_in_header, expected_results_str, expect_papers_present",
    [
        (0, 'test_pagination', 0, "Page 1 of 1", "Showing results 1 - 2 of 2", True),   # page=0 defaults to 1
        (-1, 'test_pagination', 0, "Page 1 of 1", "Showing results 1 - 2 of 2", True),  # page=-1 defaults to 1
        ('abc', 'test_pagination', 0, "Page 1 of 1", "Showing results 1 - 2 of 2", True), # non-integer page defaults to 1
        (2, 'test_pagination_many_results', 10, "Page 2 of 10", "Showing results 11 - 20 of 95", True), # Valid page with multiple results
        (10, 'test_pagination_many_results', 90, "Page 10 of 10", "Showing results 91 - 95 of 95", True), # Last valid page
        (11, 'test_pagination_many_results', 100, "Page 11 of 10", "No search results found for this query and page.", False), # Page just beyond total
        (100, 'test_pagination_many_results', 990, "Page 100 of 10", "No search results found for this query and page.", False), # Page far beyond total
        (1, 'test_very_large_total', 0, "Page 1 of 1000", "Showing results 1 - 10 of 10000", True) # Very large total_results
    ]
)
def test_search_pagination_edge_cases(client, app_context, mock_search_papers, page_param_value, query_string, expected_api_start_index, expected_page_in_header, expected_results_str, expect_papers_present):
    """Test search route with various pagination edge cases."""
    mock_search_papers.reset_mock()
    results_per_page_config = 10 # Assuming app.config['RESULTS_PER_PAGE'] is 10

    if query_string == 'test_pagination_many_results':
        mock_papers_list = [mock.MagicMock(title=f'Test Paper {i+1}') for i in range(results_per_page_config)]
        # Simulate API returning papers only if start_index is within range of total_results
        # total_results = 95. Max start_index that yields papers is 90 (for page 10).
        if expected_api_start_index <= 90: # Max start for 95 results, 10 per page
            actual_papers_for_mock = mock_papers_list[:max(0, 95 - expected_api_start_index)]
            if expected_api_start_index == 90: # last page has 5 papers
                 actual_papers_for_mock = mock_papers_list[:5]
        else:
            actual_papers_for_mock = [] # No papers if start_index is too high
        
        mock_search_papers.return_value = {
            'papers': actual_papers_for_mock,
            'total_results': 95,
            'results_per_page': results_per_page_config
        }
    elif query_string == 'test_pagination':
        mock_search_papers.return_value = {
            'papers': [mock.MagicMock(title='Test Paper 1'), mock.MagicMock(title='Test Paper 2')],
            'total_results': 2,
            'results_per_page': results_per_page_config
        }
    elif query_string == 'test_very_large_total':
        mock_search_papers.return_value = {
            'papers': [mock.MagicMock(title=f'Test Paper {i+1}') for i in range(results_per_page_config)],
            'total_results': 10000, # Large number of total results
            'results_per_page': results_per_page_config
        }

    query_params = {'query': query_string, 'page': page_param_value}
    with app_context:
        response = client.get(url_for('main.search', **query_params))
    
    assert response.status_code == 200
    mock_search_papers.assert_called_once_with(query=query_string, start=expected_api_start_index, count=results_per_page_config)

    assert expected_page_in_header.encode() in response.data
    assert expected_results_str.encode() in response.data

    if expect_papers_present:
        assert b"Test Paper 1" in response.data # A generic check if papers are listed
    else:
        # Check that no individual paper items are present if expect_papers_present is False
        # This assumes paper items have a certain structure, e.g., <article class="paper-item"> or similar
        # For now, we rely on the "No search results found..." message for this check.
        # A more robust check would be `assert b"Test Paper 1" not in response.data` if the mock guarantees unique paper titles per page.
        pass 

@pytest.mark.parametrize(
    "error_to_raise, expected_flash_message",
    [
        (Exception("Simulated API 500 Error"), "An error occurred while fetching results from arXiv. Please try again later."),
        (requests.exceptions.RequestException("Simulated Network Error"), "An error occurred while fetching results from arXiv. Please try again later."),
        (ValueError("Simulated XML Parsing Error"), "An error occurred while processing data from arXiv. Please try again later.") 
        # Add more specific exceptions if arxiv_api.py raises them for 429, etc.
    ]
)
def test_search_api_errors(client, app_context, mock_search_papers, error_to_raise, expected_flash_message):
    """Test how the search route handles various API errors."""
    mock_search_papers.reset_mock()
    mock_search_papers.side_effect = error_to_raise

    with app_context:
        response = client.get(url_for('main.search', query='api_error_test'))
    
    assert response.status_code == 200 # Route should still render gracefully
    # Check for the flashed error message
    # Option 1: Check flashed messages if your app uses them for this
    # with client.session_transaction() as session:
    #     flashed_messages = dict(session.get('_flashes', []))
    # assert expected_flash_message in flashed_messages.get('error', []) # Or whatever category you use

    # Option 2: Check if error message is rendered in the page content (more common for this type of error)
    assert expected_flash_message.encode() in response.data
    assert b"Test Paper 1" not in response.data # No results should be displayed


# Test malformed API responses (e.g., missing totalResults)
@pytest.mark.parametrize(
    "malformed_return_value, expected_error_message_snippet",
    [
        ({'papers': [], 'total_results': None}, "Error processing search results"), # Missing total_results
        ({'papers': None, 'total_results': 0}, "Error processing search results"), # Missing papers list
        ("some string instead of dict", "Error processing search results") # Completely wrong type
    ]
)
def test_search_malformed_api_responses(client, app_context, mock_search_papers, malformed_return_value, expected_error_message_snippet):
    """Test search route with malformed data from arxiv_api.search_papers."""
    mock_search_papers.reset_mock()
    mock_search_papers.side_effect = None # Ensure it returns a value, not raise exception
    mock_search_papers.return_value = malformed_return_value

    with app_context:
        response = client.get(url_for('main.search', query='malformed_test'))

    assert response.status_code == 200 # Should render gracefully
    assert expected_error_message_snippet.encode() in response.data
    assert b"Test Paper 1" not in response.data # No proper results displayed 

def test_search_query_yields_zero_results(client, app_context, mock_search_papers):
    """Test a query that legitimately returns zero total results from the API."""
    mock_search_papers.reset_mock()
    mock_search_papers.return_value = {
        'papers': [],
        'total_results': 0,
        'results_per_page': 10
    }

    with app_context:
        response = client.get(url_for('main.search', query='zero_results_query'))
    
    assert response.status_code == 200
    assert b"No search results found for this query." in response.data
    assert b"Page 1 of 0" not in response.data # Or check for sensible page display like "Page 1 of 1" or no page info
    assert b"Showing results 1 - 0 of 0" in response.data # Or similar based on template logic for 0 results
    assert b"Test Paper 1" not in response.data