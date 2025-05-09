"""
Custom Jinja2 template filters.
"""
from datetime import datetime
import markupsafe # For escaping in highlight_terms later
import bleach
from typing import List # Added import

def format_date(value, fmt='%b %d, %Y'):
    """Formats a datetime object or an ISO date string into a user-friendly string.
    Example: Jan 15, 2023
    """
    if not value:
        return "N/A"
    if isinstance(value, str):
        try:
            # Attempt to parse common ISO formats, especially if 'Z' is present
            if value.endswith('Z'):
                value = value[:-1] + '+00:00' # Make it explicit UTC for fromisoformat
            dt_obj = datetime.fromisoformat(value)
        except ValueError:
            return "Invalid Date"
    elif isinstance(value, datetime):
        dt_obj = value
    else:
        return "Invalid Date Type"
    
    return dt_obj.strftime(fmt)

def truncate_text(text, max_length=255, suffix='...'):
    """Truncates text to a maximum length and appends a suffix.
    If text is shorter than max_length, it's returned unchanged.
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def highlight_terms(text, search_terms_str):
    """Highlights search terms within a given text by wrapping them in <mark> tags.
    Search is case-insensitive.
    Args:
        text (str): The text to highlight terms in.
        search_terms_str (str): A string of search terms, space-separated.
    Returns:
        markupsafe.Markup: Text with search terms highlighted, marked as safe HTML.
    """
    if not text or not search_terms_str or not isinstance(text, str) or not isinstance(search_terms_str, str):
        return markupsafe.Markup(text) if text else ""

    # Split search terms and filter out empty strings
    terms = [term for term in search_terms_str.lower().split() if term]
    if not terms:
        return markupsafe.Markup(text)

    # To avoid issues with overlapping matches or modifying string during iteration,
    # we build a new string with replacements.
    # This is a simplified approach. For complex HTML content or overlapping terms,
    # a more robust regex or parsing approach might be needed.
    # This approach prioritizes whole word matching where possible by checking boundaries.
    
    # For simplicity and to avoid regex complexity with HTML, we'll do a simpler replacement.
    # This might not perfectly handle terms within HTML tags or attributes.
    highlighted_text = text
    for term in terms:
        # Attempt to do a case-insensitive replacement
        # This is still tricky because `replace` is case-sensitive.
        # A common way is to iterate using `re.finditer` and build the string.
        import re
        try:
            # Find all occurrences of the term, case-insensitive
            # We use a placeholder to mark found terms, then replace placeholders to avoid re-processing marked terms.
            # This also helps in not breaking HTML structure if term itself contains special chars for regex.
            escaped_term = re.escape(term)
            # Placeholder that is unlikely to be in the text naturally
            placeholder_start = "___MARK_START___"
            placeholder_end = "___MARK_END___"
            
            # First, find all matches and temporarily replace them with placeholders
            # We use a regex to find the term as a whole word (if possible) or as part of a word.
            # (?i) for case-insensitive. \b for word boundaries (optional, can make it stricter).
            # Using a simpler find for now to avoid over-complication with existing HTML in text.
            # We'll replace the original casing of the found term.

            # Simpler approach: find and replace iteratively. This is imperfect for overlapping terms or terms that are substrings of others.
            # For this context (highlighting in summaries), it might be acceptable.
            # A more robust solution would involve building the output string part by part.
            
            # Let's refine this. Iterate through parts of the string.
            parts = []
            last_end = 0
            for match in re.finditer(escaped_term, highlighted_text, re.IGNORECASE):
                start, end = match.span()
                parts.append(markupsafe.escape(highlighted_text[last_end:start])) # Escape text before match
                parts.append(markupsafe.Markup(f"<mark>{markupsafe.escape(highlighted_text[start:end])}</mark>")) # Mark and escape matched term
                last_end = end
            parts.append(markupsafe.escape(highlighted_text[last_end:])) # Escape text after last match
            highlighted_text = markupsafe.Markup("".join(parts))

        except re.error:
            # If term creates a bad regex, skip highlighting for this term
            pass # Keep highlighted_text as is from previous terms
            
    return highlighted_text

# More filters (sanitize_html) will be added later.

ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
    'em', 'i', 'li', 'ol', 'strong', 'ul', 'p', 'br',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'pre', 'hr',
    'sub', 'sup' # Added sub and sup for scientific papers
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'abbr': ['title'],
    'acronym': ['title'],
}

def sanitize_html(html_content):
    """Cleans potentially unsafe HTML using bleach.
    Allows a safe list of tags and attributes suitable for arXiv summaries.
    """
    if not html_content or not isinstance(html_content, str):
        return ""
    
    cleaned_text = bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True  # Strip disallowed tags instead of escaping them
    )
    return markupsafe.Markup(cleaned_text)

def format_authors(authors: List[str], max_authors_to_display: int) -> str:
    """Formats a list of author names for display, with sanitization and truncation.

    Args:
        authors: A list of author names (strings).
        max_authors_to_display: The maximum number of authors to display before truncating.

    Returns:
        A formatted string representing the author list.
    """
    if not authors:
        return "Unknown"

    # Sanitize and filter out empty or None author names
    sanitized_authors = [str(sanitize_html(author)).strip() for author in authors if author and str(author).strip()]

    if not sanitized_authors:
        return "Unknown"

    num_authors = len(sanitized_authors)

    if max_authors_to_display < 0:
        max_authors_to_display = 0 # Treat negative as 0

    if max_authors_to_display == 0:
        return f"+{num_authors} more"

    if num_authors == 1:
        return sanitized_authors[0]

    if num_authors <= max_authors_to_display:
        if num_authors == 2:
            return f"{sanitized_authors[0]} and {sanitized_authors[1]}"
        else:
            # Format: "A, B, and C"
            return f"{', '.join(sanitized_authors[:-1])}, and {sanitized_authors[-1]}"
    else: # num_authors > max_authors_to_display
        # Truncation needed
        if max_authors_to_display == 1:
            # Format: "A, ... +X more"
            return f"{sanitized_authors[0]}, ... +{num_authors - 1} more"
        else:
            # Format: "A, B, ... +X more" (where X is num_authors - (max_authors_to_display - 1))
            # Display (max_authors_to_display - 1) authors
            authors_to_show = sanitized_authors[:max_authors_to_display - 1]
            num_hidden = num_authors - (max_authors_to_display - 1)
            return f"{', '.join(authors_to_show)}, ... +{num_hidden} more" 