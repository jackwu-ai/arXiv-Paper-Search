from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
# import uuid # For generating unique tokens if not using itsdangerous's features directly for storage
from cryptography.fernet import Fernet
import hashlib
from flask import current_app # For accessing app config for Fernet key

db = SQLAlchemy()

# Global Fernet instance
_fernet = None

def initialize_fernet(key):
    """Initializes the Fernet instance with a key."""
    global _fernet
    if not key:
        raise ValueError("FERNET_KEY cannot be empty. Please set it in your Flask app configuration.")
    _fernet = Fernet(key)

def get_fernet():
    """Returns the initialized Fernet instance."""
    if _fernet is None:
        # Attempt to initialize from current_app if available and not already initialized
        # This is a fallback, ideally initialize_fernet is called during app setup
        if current_app and 'FERNET_KEY' in current_app.config:
            initialize_fernet(current_app.config['FERNET_KEY'])
        else:
            raise RuntimeError("Fernet encryption has not been initialized. Call initialize_fernet() during app setup or ensure FERNET_KEY is in app.config.")
    return _fernet

def _generate_email_hash(email_address: str) -> str:
    """Generates a SHA-256 hash of the lowercase email address."""
    if not email_address:
        raise ValueError("Email address cannot be empty for hashing.")
    return hashlib.sha256(email_address.lower().encode('utf-8')).hexdigest()

class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    
    # Store encrypted email as bytes
    _encrypted_email = db.Column(db.LargeBinary, nullable=False) 
    
    # Store a searchable hash of the email
    # Made unique=True, nullable=False, and indexed for performance
    email_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)

    confirmation_token = db.Column(db.String(100), unique=True, nullable=True) 
    is_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    subscribed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    unsubscribed_at = db.Column(db.DateTime, nullable=True)

    @property
    def email(self) -> str:
        try:
            fernet = get_fernet()
            decrypted_email_bytes = fernet.decrypt(self._encrypted_email)
            return decrypted_email_bytes.decode('utf-8')
        except Exception as e:
            # Log error or handle appropriately
            # Returning a placeholder or raising an error might be options
            current_app.logger.error(f"Failed to decrypt email for subscription ID {self.id}: {e}")
            return "[Decryption Failed]"

    @email.setter
    def email(self, email_address: str):
        if not email_address:
            raise ValueError("Email address cannot be empty.")
        # Basic email format validation (can be expanded)
        if "@" not in email_address or "." not in email_address.split("@")[-1]:
            raise ValueError("Invalid email format.")

        self.email_hash = _generate_email_hash(email_address)
        
        fernet = get_fernet()
        self._encrypted_email = fernet.encrypt(email_address.encode('utf-8'))

    def __repr__(self):
        # Avoid decrypting email for repr if possible, or handle potential errors
        return f"<Subscription hash: {self.email_hash}>"

# Example of another model if you have users, for context
# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(80), unique=True, nullable=False)
#     email = db.Column(db.String(120), unique=True, nullable=False)

#     def __repr__(self):
#         return f"<User {self.username}>"

def init_app(app):
    """Initialize the database with the Flask app."""
    db.init_app(app)
    # Initialize Fernet here as well, ensuring it's done after app config is loaded
    # and before any db operations that might need encryption if not called earlier.
    if 'FERNET_KEY' in app.config and not _fernet:
        initialize_fernet(app.config['FERNET_KEY'])
    # You might want to create tables if they don't exist,
    # but typically Flask-Migrate is used for migrations.
    # with app.app_context():
    #     db.create_all() 