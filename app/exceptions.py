# app/exceptions.py

"""
Custom exception classes for the arXiv Paper Search application.
"""

class ApplicationException(Exception):
    """Base class for all application-specific exceptions."""
    def __init__(self, message="An application error occurred", original_exception=None):
        super().__init__(message)
        self.original_exception = original_exception
        self.message = message

    def __str__(self):
        if self.original_exception:
            return f"{self.message}: {str(self.original_exception)}"
        return self.message

class ArxivAPIException(ApplicationException):
    """Base class for exceptions related to the arXiv API interactions."""
    def __init__(self, message="An error occurred with the arXiv API", original_exception=None, status_code=None):
        super().__init__(message, original_exception)
        self.status_code = status_code

class NetworkException(ArxivAPIException):
    """Raised for network errors during arXiv API requests (e.g., connection timeout)."""
    def __init__(self, message="A network error occurred while contacting the arXiv API", original_exception=None, status_code=None):
        super().__init__(message, original_exception, status_code)

class ParsingException(ArxivAPIException):
    """Raised for errors during parsing of arXiv API responses (e.g., malformed XML)."""
    def __init__(self, message="Error parsing data from the arXiv API", original_exception=None):
        super().__init__(message, original_exception)

class ValidationException(ApplicationException):
    """Raised for application-level input validation errors."""
    def __init__(self, message="Input validation failed", errors=None, original_exception=None):
        super().__init__(message, original_exception)
        self.errors = errors # Can be a dict of field-specific errors or a simple message

    def __str__(self):
        if self.errors:
            return f"{self.message}: {str(self.errors)}"
        return super().__str__()

# Example Usage (for documentation purposes, not to be run here):
# if __name__ == '__main__':
#     try:
#         raise NetworkException("Could not connect to server.", status_code=503)
#     except ArxivAPIException as e:
#         print(f"Caught ArxivAPIException: {e}, Status Code: {e.status_code}")
#     
#     try:
#         raise ParsingException("Invalid XML tag found.")
#     except ApplicationException as e:
#         print(f"Caught ApplicationException: {e}")

#     try:
#         form_errors = {'query': 'Query cannot be empty', 'max_results': 'Must be a positive integer'}
#         raise ValidationException("Search form validation failed", errors=form_errors)
#     except ValidationException as e:
#         print(f"Caught ValidationException: {e}, Errors: {e.errors}")

class ArxivAPIError(Exception):
    """Base class for exceptions related to the arXiv API interactions."""
    def __init__(self, message="An error occurred with the arXiv API.", status_code=None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message

    def __str__(self):
        if self.status_code:
            return f'{self.message} (Status Code: {self.status_code})'
        return self.message

class ArxivAPITimeoutError(ArxivAPIError):
    """Raised when a request to the arXiv API times out."""
    def __init__(self, message="The request to the arXiv API timed out."):
        super().__init__(message)

class ArxivAPIRateLimitError(ArxivAPIError):
    """Raised when the arXiv API rate limit is exceeded (e.g., HTTP 429)."""
    def __init__(self, message="arXiv API rate limit exceeded. Please try again later.", status_code=429):
        super().__init__(message, status_code=status_code)

class ArxivAPIServerError(ArxivAPIError):
    """Raised for server-side errors from the arXiv API (e.g., HTTP 5xx)."""
    def __init__(self, message="The arXiv API encountered a server error.", status_code=None):
        super().__init__(message, status_code=status_code)

class ArxivAPIClientError(ArxivAPIError):
    """Raised for client-side errors from the arXiv API (e.g., HTTP 4xx, excluding 429)."""
    def __init__(self, message="There was a client-side error with the arXiv API request.", status_code=None):
        super().__init__(message, status_code=status_code)

class ArxivParsingError(ArxivAPIError):
    """Raised when there is an error parsing the XML response from the arXiv API."""
    def __init__(self, message="Failed to parse the XML response from arXiv API."):
        super().__init__(message)

class ArxivInvalidQueryError(ArxivAPIError):
    """Raised when the query parameters for arXiv API are invalid."""
    def __init__(self, message="Invalid query parameters for arXiv API."):
        super().__init__(message) 