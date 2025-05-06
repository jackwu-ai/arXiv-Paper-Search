from dataclasses import dataclass, field, asdict
from typing import List, Optional # For older Python versions; Python 3.9+ can use list, str | None

@dataclass(frozen=True) # Makes instances immutable and auto-generates __eq__, etc.
class ArxivPaper:
    """Represents a parsed paper from the arXiv API."""
    id_str: str
    title: str
    summary: str
    authors: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    primary_category: Optional[str] = None
    published_date: str # Keep as string for now; can convert/validate later
    updated_date: str   # Keep as string for now; can convert/validate later
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
        if self.published_date is None:
            raise ValueError("Published date cannot be None.")
        if self.updated_date is None:
            raise ValueError("Updated date cannot be None.")
        # Note: pdf_link can be None if ID is missing, handled during construction.

    def to_dict(self) -> dict:
        """Converts the ArxivPaper instance to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ArxivPaper":
        """Creates an ArxivPaper instance from a dictionary.
        Assumes keys in the dictionary match the dataclass field names.
        """
        # This is a basic factory. More complex validation or field mapping
        # could be added here if the input dictionary structure is inconsistent.
        try:
            return cls(**data)
        except TypeError as e:
            # This can happen if `data` is missing fields required by __init__
            # or has extra fields not defined in the dataclass (if not using ignore_extra_fields with a lib like Pydantic)
            # For standard dataclasses, it's mostly about missing required fields without defaults.
            raise ValueError(f"Error creating ArxivPaper from dict: {e}. Data: {data}") from e 