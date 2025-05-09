import unittest
from unittest.mock import patch, MagicMock, call
import xml.etree.ElementTree as ET
from dataclasses import asdict
import requests
from datetime import datetime
import logging

# Assuming your project structure allows this import path
# If run from project root: python -m unittest discover tests
from app.arxiv_api import (
    construct_query_url,
    make_api_request,
    parse_arxiv_xml,
    search_papers,
    ARXIV_API_URL, 
    REQUEST_THROTTLE_SECONDS,
    MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS
)
from app.models import ArxivPaper
# Import new custom exceptions
from app.exceptions import (
    ValidationException,
    NetworkException,
    ArxivAPIException, # Base for specific client errors if not Network
    ParsingException
)

# Configure logging for tests if necessary, or rely on caplog if using pytest features later
# For unittest, we can check logs using self.assertLogs
logging.basicConfig(level=logging.DEBUG) # Or use a more specific logger

# --- Test Fixtures (Sample Data) ---
# For simplicity, defined here. Could be moved to tests/fixtures/ for larger XMLs.
SAMPLE_XML_VALID_SINGLE_ENTRY = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/1234.5678</id>
    <updated>2023-01-01T00:00:00Z</updated>
    <published>2023-01-01T00:00:00Z</published>
    <title>Test Paper Title</title>
    <summary>This is a test summary.</summary>
    <author><name>Author One</name></author>
    <author><name>Author Two</name></author>
    <arxiv:doi>10.1234/arxiv.1234.5678</arxiv:doi>
    <link href="http://arxiv.org/abs/1234.5678" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/1234.5678" rel="related" type="application/pdf"/>
    <arxiv:primary_category term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>'''

EXPECTED_PAPER_DICT_SINGLE_ENTRY = {
    "id_str": "1234.5678",
    "title": "Test Paper Title",
    "summary": "This is a test summary.",
    "authors": ["Author One", "Author Two"],
    "categories": ["cs.AI", "cs.LG"],
    "primary_category": "cs.AI",
    "published_date": "2023-01-01T00:00:00Z",
    "updated_date": "2023-01-01T00:00:00Z",
    "pdf_link": "http://arxiv.org/pdf/1234.5678.pdf", # Constructed by parser
    "doi": "10.1234/arxiv.1234.5678"
}

EXPECTED_PAPER_OBJ_SINGLE_ENTRY = ArxivPaper(**EXPECTED_PAPER_DICT_SINGLE_ENTRY)

MALFORMED_XML = "<feed><entry></malformed>"

SAMPLE_XML_EMPTY_FEED_WITH_TOTAL = '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"><opensearch:totalResults>0</opensearch:totalResults></feed>'

SAMPLE_XML_VALID_MULTIPLE_ENTRIES_WITH_TOTAL = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>2</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/1234.5678</id>
    <updated>2023-01-01T00:00:00Z</updated>
    <published>2023-01-01T00:00:00Z</published>
    <title>Test Paper Title 1</title>
    <summary>Summary 1.</summary>
    <author><name>Author One</name></author>
    <arxiv:primary_category term="cs.AI"/>
    <category term="cs.AI"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/9876.5432</id>
    <updated>2023-02-01T00:00:00Z</updated>
    <published>2023-02-01T00:00:00Z</published>
    <title>Test Paper Title 2</title>
    <summary>Summary 2.</summary>
    <author><name>Author Two</name></author>
    <category term="cs.LG"/>
  </entry>
</feed>'''

EXPECTED_PAPERS_MULTIPLE_ENTRIES = [
    ArxivPaper(id_str="1234.5678", title="Test Paper Title 1", summary="Summary 1.", authors=["Author One"], categories=["cs.AI"], primary_category="cs.AI", published_date="2023-01-01T00:00:00Z", updated_date="2023-01-01T00:00:00Z", pdf_link="http://arxiv.org/pdf/1234.5678.pdf", doi=None),
    ArxivPaper(id_str="9876.5432", title="Test Paper Title 2", summary="Summary 2.", authors=["Author Two"], categories=["cs.LG"], primary_category=None, published_date="2023-02-01T00:00:00Z", updated_date="2023-02-01T00:00:00Z", pdf_link="http://arxiv.org/pdf/9876.5432.pdf", doi=None),
]

SAMPLE_XML_MISSING_OPTIONAL_DOI_WITH_TOTAL = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/1111.2222</id>
    <updated>2023-03-01T00:00:00Z</updated>
    <published>2023-03-01T00:00:00Z</published>
    <title>Paper Missing DOI</title>
    <summary>Summary for paper missing DOI.</summary>
    <author><name>Author Three</name></author>
    <arxiv:primary_category term="math.CO"/>
    <category term="math.CO"/>
  </entry>
</feed>'''

EXPECTED_PAPER_MISSING_OPTIONAL_DOI = ArxivPaper(
    id_str="1111.2222", title="Paper Missing DOI", summary="Summary for paper missing DOI.",
    authors=["Author Three"], categories=["math.CO"], primary_category="math.CO",
    published_date="2023-03-01T00:00:00Z", updated_date="2023-03-01T00:00:00Z",
    pdf_link="http://arxiv.org/pdf/1111.2222.pdf", doi=None
)

SAMPLE_XML_INVALID_ENTRY_MISSING_TITLE_WITH_TOTAL = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>1</opensearch:totalResults> <!-- Count only valid entries -->
  <entry> <!-- This entry is valid and should be parsed -->
    <id>http://arxiv.org/abs/valid.0001</id>
    <updated>2023-04-01T00:00:00Z</updated>
    <published>2023-04-01T00:00:00Z</published>
    <title>Valid Paper Title</title>
    <summary>Valid summary.</summary>
    <author><name>Valid Author</name></author>
    <category term="stat.ML"/>
  </entry>
  <entry> <!-- This entry is invalid (missing title), should be skipped -->
    <id>http://arxiv.org/abs/invalid.0002</id>
    <updated>2023-04-02T00:00:00Z</updated>
    <published>2023-04-02T00:00:00Z</published>
    <summary>Summary for paper missing title.</summary>
    <author><name>Invalid Author</name></author>
  </entry>
</feed>'''
EXPECTED_PAPER_FROM_VALID_ENTRY_IN_MIXED_XML = ArxivPaper(
    id_str="valid.0001", title="Valid Paper Title", summary="Valid summary.",
    authors=["Valid Author"], categories=["stat.ML"], primary_category=None,
    published_date="2023-04-01T00:00:00Z", updated_date="2023-04-01T00:00:00Z",
    pdf_link="http://arxiv.org/pdf/valid.0001.pdf", doi=None
)

class TestArxivPaperModel(unittest.TestCase):
    def test_creation_valid(self):
        paper = ArxivPaper(**EXPECTED_PAPER_DICT_SINGLE_ENTRY)
        self.assertEqual(paper.id_str, EXPECTED_PAPER_DICT_SINGLE_ENTRY["id_str"])
        self.assertEqual(paper.title, EXPECTED_PAPER_DICT_SINGLE_ENTRY["title"])
        self.assertEqual(paper.summary, EXPECTED_PAPER_DICT_SINGLE_ENTRY["summary"])
        # For frozen dataclasses, direct attribute comparison is fine.
        # Using asdict to compare the whole structure can also be an option.
        self.assertEqual(asdict(paper), asdict(EXPECTED_PAPER_OBJ_SINGLE_ENTRY))

    def test_creation_invalid_missing_required(self):
        invalid_data = EXPECTED_PAPER_DICT_SINGLE_ENTRY.copy()
        del invalid_data["id_str"] # id_str is required
        with self.assertRaises(TypeError): # Dataclass __init__ raises TypeError for missing args
            ArxivPaper(**invalid_data)

    def test_post_init_validation_empty_id(self):
        invalid_data = EXPECTED_PAPER_DICT_SINGLE_ENTRY.copy()
        invalid_data["id_str"] = ""
        with self.assertRaisesRegex(ValueError, "Paper ID \\(id_str\\) cannot be empty or None."):
            ArxivPaper(**invalid_data)

    def test_post_init_validation_empty_title(self):
        invalid_data = EXPECTED_PAPER_DICT_SINGLE_ENTRY.copy()
        invalid_data["title"] = ""
        with self.assertRaisesRegex(ValueError, "Paper title cannot be empty or None."):
            ArxivPaper(**invalid_data)
    
    def test_post_init_validation_none_summary(self):
        invalid_data = EXPECTED_PAPER_DICT_SINGLE_ENTRY.copy()
        invalid_data["summary"] = None
        with self.assertRaisesRegex(ValueError, "Paper summary cannot be None."):
            ArxivPaper(**invalid_data)

    def test_post_init_validation_valid_empty_summary(self):
        valid_data = EXPECTED_PAPER_DICT_SINGLE_ENTRY.copy()
        valid_data["summary"] = ""
        try:
            paper = ArxivPaper(**valid_data)
            self.assertEqual(paper.summary, "")
        except ValueError:
            self.fail("ArxivPaper raised ValueError for empty summary, but should be valid.")

    def test_post_init_validation_none_published_date(self):
        invalid_data = EXPECTED_PAPER_DICT_SINGLE_ENTRY.copy()
        invalid_data["published_date"] = None
        with self.assertRaisesRegex(ValueError, "Published date cannot be None."):
            ArxivPaper(**invalid_data)
            
    def test_post_init_validation_none_updated_date(self):
        invalid_data = EXPECTED_PAPER_DICT_SINGLE_ENTRY.copy()
        invalid_data["updated_date"] = None
        with self.assertRaisesRegex(ValueError, "Updated date cannot be None."):
            ArxivPaper(**invalid_data)

    def test_to_dict(self):
        paper = EXPECTED_PAPER_OBJ_SINGLE_ENTRY
        self.assertEqual(paper.to_dict(), EXPECTED_PAPER_DICT_SINGLE_ENTRY)

    def test_from_dict_valid(self):
        paper = ArxivPaper.from_dict(EXPECTED_PAPER_DICT_SINGLE_ENTRY)
        self.assertIsInstance(paper, ArxivPaper)
        self.assertEqual(asdict(paper), EXPECTED_PAPER_DICT_SINGLE_ENTRY)

    def test_from_dict_missing_field_handled_by_value_error(self):
        invalid_data = EXPECTED_PAPER_DICT_SINGLE_ENTRY.copy()
        del invalid_data["title"] # title is required by __init__
        # Adjusted regex to be more general and expect trailing data
        with self.assertRaisesRegex(ValueError, "Error creating ArxivPaper from dict: __init__\\(\\) missing 1 required positional argument: 'title'.*Data: {.*}"):
            ArxivPaper.from_dict(invalid_data)
            
    def test_from_dict_extra_field(self):
        data_with_extra = EXPECTED_PAPER_DICT_SINGLE_ENTRY.copy()
        data_with_extra["extra_field"] = "some_value"
        # Adjusted regex to be more general and expect trailing data
        with self.assertRaisesRegex(ValueError, "Error creating ArxivPaper from dict: __init__\\(\\) got an unexpected keyword argument 'extra_field'.*Data: {.*}"):
            ArxivPaper.from_dict(data_with_extra)

class TestConstructQueryUrl(unittest.TestCase):
    def test_basic_search_query(self):
        url = construct_query_url(search_query="ti:electron")
        self.assertIn(f"{ARXIV_API_URL}?", url)
        self.assertIn("search_query=ti%3Aelectron", url)
        self.assertIn("start=0", url)
        self.assertIn("max_results=10", url)
        self.assertIn("sortBy=relevance", url)
        self.assertIn("sortOrder=descending", url)

    def test_search_query_with_pagination_and_sorting(self):
        url = construct_query_url(
            search_query="au:bohr",
            start=5,
            max_results=25,
            sortBy="submittedDate",
            sortOrder="ascending"
        )
        self.assertIn("search_query=au%3Abohr", url)
        self.assertIn("start=5", url)
        self.assertIn("max_results=25", url)
        self.assertIn("sortBy=submittedDate", url)
        self.assertIn("sortOrder=ascending", url)

    def test_id_list_query(self):
        url = construct_query_url(id_list=["1234.5678", "abcd.1234"])
        self.assertIn("id_list=1234.5678%2Cabcd.1234", url)
        self.assertNotIn("search_query=", url)
        self.assertIn("start=0", url)
        self.assertIn("max_results=10", url)

    def test_id_list_with_pagination_and_sorting(self):
        url = construct_query_url(
            id_list=["1234.5678"],
            start=2,
            max_results=5,
            sortBy="lastUpdatedDate",
            sortOrder="ascending"
        )
        self.assertIn("id_list=1234.5678", url)
        self.assertIn("start=2", url)
        self.assertIn("max_results=5", url)
        self.assertIn("sortBy=lastUpdatedDate", url)
        self.assertIn("sortOrder=ascending", url)

    def test_special_characters_in_search_query(self):
        url = construct_query_url(search_query='ti:"complex query" AND au:O\'Malley')
        self.assertIn("search_query=ti%3A%22complex+query%22+AND+au%3AO%27Malley", url)
        
    @patch('app.arxiv_api.logger.error')
    def test_invalid_both_search_query_and_id_list(self, mock_logger_error):
        with self.assertRaisesRegex(ValidationException, "Cannot use both search_query and id_list simultaneously."):
            construct_query_url(search_query="ti:test", id_list=["1234.5678"])
        mock_logger_error.assert_called_with("Cannot use both search_query and id_list simultaneously.")

    @patch('app.arxiv_api.logger.error')
    def test_invalid_neither_search_query_nor_id_list(self, mock_logger_error):
        with self.assertRaisesRegex(ValidationException, "Either search_query or id_list must be provided."):
            construct_query_url()
        mock_logger_error.assert_called_with("Either search_query or id_list must be provided.")

class TestMakeApiRequest(unittest.TestCase):
    @patch('app.arxiv_api.time.sleep', return_value=None)
    @patch('app.arxiv_api.requests.get')
    def test_successful_request(self, mock_requests_get, mock_time_sleep):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<feed>success</feed>"
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        result = make_api_request("http://fakeurl.com/query")

        self.assertEqual(result, "<feed>success</feed>")
        mock_requests_get.assert_called_once_with("http://fakeurl.com/query", timeout=DEFAULT_TIMEOUT_SECONDS)
        mock_time_sleep.assert_called_once_with(REQUEST_THROTTLE_SECONDS)

    @patch('app.arxiv_api.time.sleep', return_value=None)
    @patch('app.arxiv_api.requests.get')
    def test_http_error_client_404_no_retry(self, mock_requests_get, mock_time_sleep):
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error
        mock_requests_get.return_value = mock_response

        with self.assertRaises(ArxivAPIException) as cm:
            make_api_request("http://fakeurl.com/query")
        self.assertEqual(cm.exception.status_code, 404)
        self.assertIn("Client error with arXiv API request.", str(cm.exception))
        mock_requests_get.assert_called_once()
        mock_time_sleep.assert_called_once_with(REQUEST_THROTTLE_SECONDS)

    @patch('app.arxiv_api.time.sleep', return_value=None)
    @patch('app.arxiv_api.requests.get')
    def test_http_error_server_500_with_retries(self, mock_requests_get, mock_time_sleep):
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error 
        mock_requests_get.return_value = mock_response

        with self.assertRaises(NetworkException) as cm:
            make_api_request("http://fakeurl.com/query")
        self.assertEqual(cm.exception.status_code, 500)
        self.assertIn("arXiv API server error.", str(cm.exception))
        self.assertEqual(mock_requests_get.call_count, MAX_RETRIES)

    @patch('app.arxiv_api.time.sleep', return_value=None)
    @patch('app.arxiv_api.requests.get')
    def test_http_error_rate_limit_429_with_retries_and_backoff(self, mock_requests_get, mock_time_sleep):
        mock_response = MagicMock()
        mock_response.status_code = 429
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error
        mock_requests_get.return_value = mock_response

        with self.assertRaises(NetworkException) as cm:
            make_api_request("http://fakeurl.com/query")
        self.assertEqual(cm.exception.status_code, 429)
        self.assertIn("arXiv API rate limit exceeded.", str(cm.exception))
        self.assertEqual(mock_requests_get.call_count, MAX_RETRIES)

    @patch('app.arxiv_api.time.sleep', return_value=None)
    @patch('app.arxiv_api.requests.get')
    def test_timeout_error_with_retries(self, mock_requests_get, mock_time_sleep):
        mock_requests_get.side_effect = requests.exceptions.Timeout("Timeout test")
        with self.assertRaisesRegex(NetworkException, "Request to arXiv API timed out."):
            make_api_request("http://fakeurl.com/query")
        self.assertEqual(mock_requests_get.call_count, MAX_RETRIES)

    @patch('app.arxiv_api.time.sleep', return_value=None)
    @patch('app.arxiv_api.requests.get')
    def test_request_exception_with_retries(self, mock_requests_get, mock_time_sleep):
        mock_requests_get.side_effect = requests.exceptions.RequestException("Some generic network error")
        with self.assertRaisesRegex(NetworkException, "A general network or request error occurred: Some generic network error"):
            make_api_request("http://fakeurl.com/query")
        self.assertEqual(mock_requests_get.call_count, MAX_RETRIES)

    @patch('app.arxiv_api.logger.error')
    @patch('app.arxiv_api.time.sleep', return_value=None)
    @patch('app.arxiv_api.requests.get')
    def test_final_retry_failure_logs_error(self, mock_requests_get, mock_time_sleep, mock_logger_error):
        mock_requests_get.side_effect = requests.exceptions.Timeout() 
        with self.assertRaises(NetworkException): # Expect NetworkException on final timeout
            make_api_request("http://fakeurl.com/query")
        # Check if the specific log message for all retries failed is present
        # This requires inspecting all calls to mock_logger_error
        all_log_calls = [call_args[0][0] for call_args in mock_logger_error.call_args_list] # Get the first arg of each call
        self.assertTrue(any(f"All {MAX_RETRIES} retries failed for URL: http://fakeurl.com/query" in log_msg for log_msg in all_log_calls))

class TestParseArxivXml(unittest.TestCase):
    def test_valid_single_entry(self):
        result = parse_arxiv_xml(SAMPLE_XML_VALID_SINGLE_ENTRY)
        self.assertIsNotNone(result)
        self.assertEqual(len(result['papers']), 1)
        self.assertEqual(result['papers'][0], EXPECTED_PAPER_OBJ_SINGLE_ENTRY)
        self.assertEqual(result['total_results'], 1)

    def test_valid_multiple_entries(self):
        result = parse_arxiv_xml(SAMPLE_XML_VALID_MULTIPLE_ENTRIES_WITH_TOTAL)
        self.assertIsNotNone(result)
        self.assertEqual(len(result['papers']), 2)
        self.assertEqual(result['papers'], EXPECTED_PAPERS_MULTIPLE_ENTRIES)
        self.assertEqual(result['total_results'], 2)

    def test_entry_missing_optional_doi(self):
        result = parse_arxiv_xml(SAMPLE_XML_MISSING_OPTIONAL_DOI_WITH_TOTAL)
        self.assertIsNotNone(result)
        self.assertEqual(len(result['papers']), 1)
        self.assertEqual(result['papers'][0], EXPECTED_PAPER_MISSING_OPTIONAL_DOI)
        self.assertIsNone(result['papers'][0].doi)
        self.assertEqual(result['total_results'], 1)

    @patch('app.arxiv_api.logger.warning')
    def test_entry_invalid_missing_title_is_skipped(self, mock_logger_warning):
        result = parse_arxiv_xml(SAMPLE_XML_INVALID_ENTRY_MISSING_TITLE_WITH_TOTAL)
        self.assertIsNotNone(result)
        self.assertEqual(len(result['papers']), 1) 
        self.assertEqual(result['papers'][0], EXPECTED_PAPER_FROM_VALID_ENTRY_IN_MIXED_XML)
        self.assertEqual(result['total_results'], 1) # totalResults in XML was 1
        self.assertTrue(any("Skipping entry due to validation error: Paper title cannot be empty or None." in call[0][0] for call in mock_logger_warning.call_args_list))

    def test_malformed_xml_raises_parsing_exception(self):
        with self.assertRaisesRegex(ParsingException, "Failed to parse XML response from arXiv."):
            parse_arxiv_xml(MALFORMED_XML)

    def test_empty_feed_xml(self):
        result = parse_arxiv_xml(SAMPLE_XML_EMPTY_FEED_WITH_TOTAL)
        self.assertIsNotNone(result)
        self.assertEqual(len(result['papers']), 0)
        self.assertEqual(result['total_results'], 0)

    @patch('app.arxiv_api.logger.warning')
    def test_xml_with_only_invalid_entry(self, mock_logger_warning):
        xml_only_invalid_with_total = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>0</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/invalid.only</id>
    <summary>No title here.</summary>
  </entry>
</feed>'''
        result = parse_arxiv_xml(xml_only_invalid_with_total)
        self.assertIsNotNone(result)
        self.assertEqual(len(result['papers']), 0)
        self.assertEqual(result['total_results'], 0)
        self.assertTrue(any("Skipping entry due to validation error" in call[0][0] for call in mock_logger_warning.call_args_list))

    @patch('app.arxiv_api.logger.warning')
    def test_missing_total_results_tag(self, mock_logger_warning):
        xml_missing_total = SAMPLE_XML_VALID_SINGLE_ENTRY.replace("<opensearch:totalResults>1</opensearch:totalResults>", "")
        result = parse_arxiv_xml(xml_missing_total)
        self.assertIsNotNone(result)
        self.assertEqual(len(result['papers']), 1) # Should still parse papers
        self.assertEqual(result['total_results'], 0) # Defaults to 0 if tag missing
        mock_logger_warning.assert_any_call("opensearch:totalResults tag not found or empty. Defaulting to 0.")

    @patch('app.arxiv_api.logger.warning')
    def test_malformed_total_results_value(self, mock_logger_warning):
        xml_malformed_total = SAMPLE_XML_VALID_SINGLE_ENTRY.replace("<opensearch:totalResults>1</opensearch:totalResults>", "<opensearch:totalResults>not-a-number</opensearch:totalResults>")
        result = parse_arxiv_xml(xml_malformed_total)
        self.assertIsNotNone(result)
        self.assertEqual(len(result['papers']), 1)
        self.assertEqual(result['total_results'], 0) # Defaults to 0 if value is unparseable
        mock_logger_warning.assert_any_call("Could not parse totalResults value: 'not-a-number'. Defaulting to 0.")

class TestSearchPapersIntegration(unittest.TestCase):
    @patch('app.arxiv_api.parse_arxiv_xml')
    @patch('app.arxiv_api.make_api_request')
    @patch('app.arxiv_api.construct_query_url')
    def test_successful_flow(self, mock_construct_url, mock_make_request, mock_parse_xml):
        test_query = "ti:test_query"
        fake_url = "http://fakeurl.com/api?search_query=ti:test_query"
        mock_construct_url.return_value = fake_url
        mock_make_request.return_value = SAMPLE_XML_VALID_SINGLE_ENTRY
        # Mock parse_arxiv_xml to return the dict structure
        mock_parse_xml.return_value = {'papers': [EXPECTED_PAPER_OBJ_SINGLE_ENTRY], 'total_results': 1}

        result = search_papers(query=test_query)

        self.assertEqual(result['papers'], [EXPECTED_PAPER_OBJ_SINGLE_ENTRY])
        self.assertEqual(result['total_results'], 1)
        mock_construct_url.assert_called_once_with(
            search_query=test_query, id_list=None, start=0, max_results=10, 
            sortBy="relevance", sortOrder="descending"
        )
        mock_make_request.assert_called_once_with(fake_url)
        mock_parse_xml.assert_called_once_with(SAMPLE_XML_VALID_SINGLE_ENTRY)

    def test_failure_in_construct_query_url(self):
        with self.assertRaises(ValidationException):
            search_papers(query=None, ids=None) # This will fail in construct_query_url

    @patch('app.arxiv_api.construct_query_url') 
    @patch('app.arxiv_api.make_api_request')
    def test_failure_in_make_api_request(self, mock_make_request, mock_construct_url):
        mock_construct_url.return_value = "http://fakeurl.com/api"
        mock_make_request.side_effect = NetworkException("Simulated network failure")
        with self.assertRaises(NetworkException):
            search_papers(query="ti:test")

    @patch('app.arxiv_api.construct_query_url')
    @patch('app.arxiv_api.make_api_request')
    @patch('app.arxiv_api.parse_arxiv_xml')
    def test_failure_in_parse_arxiv_xml(self, mock_parse_xml, mock_make_request, mock_construct_url):
        mock_construct_url.return_value = "http://fakeurl.com/api"
        mock_make_request.return_value = MALFORMED_XML 
        mock_parse_xml.side_effect = ParsingException("Simulated parsing failure")
        with self.assertRaises(ParsingException):
            search_papers(query="ti:test")

if __name__ == '__main__':
    unittest.main() 