from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime, timezone # Added timezone

@dataclass(frozen=True) # Makes instances immutable and auto-generates __eq__, etc.
class ArxivPaper:
    """Represents a parsed paper from the arXiv API."""
    id_str: str
    title: str
    summary: str
    # Non-default fields first, type hints updated
    published_date: Optional[datetime] = None 
    updated_date: Optional[datetime] = None   
    # Fields with defaults
    authors: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    primary_category: Optional[str] = None
    pdf_link: Optional[str] = None
    doi: Optional[str] = None

    def __post_init__(self):
        # Basic validation: Ensure essential fields are not empty or None.
        # frozen=True means we can't modify fields here, but we can raise errors.
        if not self.id_str:
            raise ValueError("Paper ID (id_str) cannot be empty or None.")
        if not self.title:
            raise ValueError("Paper title cannot be empty or None.")
        if self.summary is None: # Explicitly checking for None, empty summary might be valid
             raise ValueError("Paper summary cannot be None.")

        # Date parsing logic
        for date_field_name in ['published_date', 'updated_date']:
            # The value from the constructor (still a string or None at this point)
            # needs to be accessed before it's potentially overwritten by a previous iteration
            # if we were to use a single variable for `date_val_from_constructor`.
            # However, __setattr__ in dataclasses' __post_init__ for frozen=True
            # is tricky. The initial values passed to __init__ are what need parsing.
            # We need to access the initial string value that was passed.
            # A common pattern is to accept string, parse, and store as datetime.
            # For frozen dataclasses, this usually means a custom __init__ or a factory method,
            # or doing the conversion before calling the dataclass constructor.
            # Given the current structure, the easiest is to change the input type annotation
            # in arxiv_api.py when preparing paper_data, or here, by assuming the __init__
            # received strings and we're converting them.
            # Let's assume the strings are passed to __init__ and we convert them.

            date_val_str = getattr(self, date_field_name) # This will be the string from init
            parsed_dt = None

            if isinstance(date_val_str, str):
                try:
                    # Handle 'Z' for UTC, making it compatible with fromisoformat
                    processed_date_str = date_val_str.replace('Z', '+00:00') if date_val_str.endswith('Z') else date_val_str
                    parsed_dt = datetime.fromisoformat(processed_date_str)
                except ValueError:
                    # Fallback for YYYY-MM-DD if full ISO parse fails
                    try:
                        parsed_dt = datetime.strptime(date_val_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    except ValueError:
                        # If all parsing attempts fail, parsed_dt remains None
                        # Optionally log this failure: print(f"Warning: Could not parse date string '{date_val_str}' for {date_field_name}")
                        pass 
            elif isinstance(date_val_str, datetime): # If it's already a datetime
                parsed_dt = date_val_str
            
            # Use object.__setattr__ to assign to the field in a frozen dataclass
            object.__setattr__(self, date_field_name, parsed_dt)

        # Validations after attempting to parse/set the dates
        if self.published_date is None: # Now checks the (potentially None) datetime object
            raise ValueError("Published date could not be parsed or was None.")
        if self.updated_date is None: # Now checks the (potentially None) datetime object
            raise ValueError("Updated date could not be parsed or was None.")
        # Note: pdf_link can be None if ID is missing, handled during construction.

    def to_dict(self) -> dict:
        """Converts the ArxivPaper instance to a dictionary."""
        # Custom handling for datetime might be needed if asdict doesn't convert to ISO string
        data = asdict(self)
        for date_field in ['published_date', 'updated_date']:
            if isinstance(data[date_field], datetime):
                data[date_field] = data[date_field].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ArxivPaper":
        """Creates an ArxivPaper instance from a dictionary.
        Assumes keys in the dictionary match the dataclass field names,
        and date strings are ISO format.
        """
        # Convert date strings back to datetime objects before instantiation if necessary
        # For simplicity here, this factory assumes ArxivPaper's __init__ (via __post_init__) handles parsing
        # if strings are passed for dates. But if we were strictly constructing from a dict
        # that already had datetime objects, this would be simpler.
        # The current setup is: arxiv_api creates dict with date strings, ArxivPaper parses them.
        
        # If date fields in `data` are strings, they will be parsed by __post_init__
        try:
            return cls(**data)
        except TypeError as e:
            # This can happen if `data` is missing fields required by __init__
            # or has extra fields not defined in the dataclass (if not using ignore_extra_fields with a lib like Pydantic)
            # For standard dataclasses, it's mostly about missing required fields without defaults.
            raise ValueError(f"Error creating ArxivPaper from dict: {e}. Data: {data}") from e 