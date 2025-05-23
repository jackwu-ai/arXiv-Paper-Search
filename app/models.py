from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime, timezone # Added timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash # For hashing, though not directly passwords here
import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import current_app # For accessing app config

# Initialize SQLAlchemy
db = SQLAlchemy()

# Placeholder for encryption key - In a real app, this should be securely managed
# and loaded from app.config, e.g., app.config['APPLICATION_SECRET_KEY']
# For AESGCM, the key should be 32 bytes.
# Example: ENCRYPTION_KEY = os.urandom(32) # Generate a new key
# Store it securely, don't regenerate it every time unless for specific key rotation strategy.

def encrypt_data(data: str) -> bytes:
    """Encrypts data using AESGCM."""
    if not data:
        return b''
    key = current_app.config.get('ENCRYPTION_KEY')
    if not key:
        raise ValueError("ENCRYPTION_KEY not configured in Flask app.")
    aesgcm = AESGCM(key.encode('utf-8') if isinstance(key, str) else key) # Ensure key is bytes
    nonce = os.urandom(12)  # AES-GCM nonce, 12 bytes is common
    encoded_data = data.encode('utf-8')
    encrypted_payload = aesgcm.encrypt(nonce, encoded_data, None)
    return nonce + encrypted_payload # Prepend nonce to the ciphertext

def decrypt_data(encrypted_payload_with_nonce: bytes) -> str:
    """Decrypts data using AESGCM."""
    if not encrypted_payload_with_nonce:
        return ""
    key = current_app.config.get('ENCRYPTION_KEY')
    if not key:
        raise ValueError("ENCRYPTION_KEY not configured in Flask app.")
    aesgcm = AESGCM(key.encode('utf-8') if isinstance(key, str) else key) # Ensure key is bytes
    nonce = encrypted_payload_with_nonce[:12]
    encrypted_payload = encrypted_payload_with_nonce[12:]
    try:
        decrypted_data = aesgcm.decrypt(nonce, encrypted_payload, None)
        return decrypted_data.decode('utf-8')
    except Exception as e: # Catch potential decryption errors (e.g., InvalidTag)
        # Log this error appropriately in a real application
        current_app.logger.error(f"Decryption failed: {e}")
        # Depending on policy, either raise an error or return a specific value
        # For GDPR data access, failing to decrypt might mean data is corrupted.
        raise ValueError(f"Failed to decrypt data. It might be corrupted or the key is incorrect. {e}")

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

def _generate_email_hash(email: str) -> str:
    """Generates a SHA-256 hash of the email address for non-reversible storage and lookup."""
    if not email:
        raise ValueError("Email cannot be empty for hashing.")
    return hashlib.sha256(email.lower().strip().encode('utf-8')).hexdigest()

class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    
    # For querying/checking existence without exposing plain email
    email_hash = db.Column(db.String(64), unique=True, nullable=False, index=True) 
    
    # Store encrypted email
    encrypted_email = db.Column(db.LargeBinary, nullable=False) # Changed from email to encrypted_email

    confirmation_token = db.Column(db.String(128), unique=True, nullable=True)
    is_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    unsubscribed_at = db.Column(db.DateTime, nullable=True)
    # GDPR related fields / preferences
    preferences = db.Column(db.Text, nullable=True) # For storing subscription preferences as JSON string or similar
    keywords = db.Column(db.Text, nullable=True) # For storing user-defined keywords for paper search

    def __init__(self, email: str, confirmation_token: Optional[str] = None, preferences: Optional[str] = None, keywords: Optional[str] = None):
        if not email:
            raise ValueError("Email address is required for subscription.")
        
        plain_email = email.lower().strip()
        self.email_hash = _generate_email_hash(plain_email)
        self.encrypted_email = encrypt_data(plain_email) # Encrypt the email
        
        self.confirmation_token = confirmation_token
        self.is_confirmed = False
        self.preferences = preferences
        self.keywords = keywords
        # Ensure subscribed_at is set if not defaulted by db.Column directly in all cases
        if not self.subscribed_at:
             self.subscribed_at = datetime.utcnow()

    @property
    def email(self) -> str:
        """Returns the decrypted email address."""
        try:
            return decrypt_data(self.encrypted_email)
        except ValueError as e:
            # Log error and handle appropriately, e.g. return placeholder or raise
            current_app.logger.error(f"Could not decrypt email for subscription id {self.id}: {e}")
            return "[email decryption failed]" # Or raise a custom error

    def export_data(self) -> dict:
        """Exports subscriber data in a dictionary format for GDPR."""
        return {
            "email": self.email, # Uses the property to decrypt
            "email_hash": self.email_hash,
            "is_confirmed": self.is_confirmed,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "subscribed_at": self.subscribed_at.isoformat() if self.subscribed_at else None,
            "unsubscribed_at": self.unsubscribed_at.isoformat() if self.unsubscribed_at else None,
            "preferences": self.preferences,
            "keywords": self.keywords
        }

    def anonymize_data(self):
        """Anonymizes subscriber data for GDPR 'right to be forgotten'.
        This might involve nullifying fields or replacing them with placeholder values.
        Actual deletion might be handled by a separate process or directly via db.session.delete(self).
        """
        self.encrypted_email = encrypt_data(f"anonymized_{self.id}@example.com") # Anonymize email
        self.email_hash = _generate_email_hash(f"anonymized_{self.id}@example.com") # Update hash
        self.confirmation_token = None
        self.preferences = None # Or '{"anonymized": true}'
        self.keywords = None # Or '{"anonymized": true}'
        # Keep is_confirmed, confirmed_at, subscribed_at, unsubscribed_at for audit/stats if needed,
        # or nullify them as well based on policy.
        # For complete removal, one would typically use: db.session.delete(self)
        # Here we are "anonymizing" by altering sensitive data.

    def __repr__(self):
        return f'<Subscription {self.email_hash} (Confirmed: {self.is_confirmed})>'

def init_app(app):
    """Initializes the database with the Flask app."""
    db.init_app(app)
    # You might want to add a check here for app.testing or specific configs
    # to conditionally call db.create_all() or recommend migrations.
    # For simplicity in this context, create_all is often called directly in dev.
    # with app.app_context():
    #     db.create_all() # Creates tables if they don't exist. For prod, use migrations. 