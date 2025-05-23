import os
from dotenv import load_dotenv
import logging

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here' # IMPORTANT: Change this and set as environment variable
    SITE_URL = os.environ.get('SITE_URL') or 'http://localhost:5000' # Base URL for the site
    SERVER_NAME = os.environ.get('SERVER_NAME') or 'localhost:5000' # For URL generation outside request context
    PREFERRED_URL_SCHEME = os.environ.get('PREFERRED_URL_SCHEME') or 'http' # For URL generation
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db' # Example for SQLite
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RESULTS_PER_PAGE = 10 # Default number of results per search page
    LOG_TO_STDOUT = False # Default to False, can be overridden by env or specific configs
    LOG_LEVEL = logging.INFO # Default log level

    # Encryption key for AESGCM (must be 32 bytes)
    # For production, this MUST be set via an environment variable and kept secret.
    # For development, we can generate one if not set, but it will change on each app restart.
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or os.urandom(32)
    if isinstance(ENCRYPTION_KEY, str):
        ENCRYPTION_KEY = ENCRYPTION_KEY.encode('utf-8') # Ensure it's bytes if from env

    if len(ENCRYPTION_KEY) != 32:
        # In development, if a generated key from os.urandom() somehow wasn't 32 bytes (highly unlikely)
        # or if an env var was set incorrectly.
        if os.environ.get('ENCRYPTION_KEY'):
            logging.warning(
                f"ENCRYPTION_KEY from environment variable is not 32 bytes long (got {len(ENCRYPTION_KEY)} bytes). "
                f"This can lead to errors. Please ensure it is a 32-byte (256-bit) key."
            )
            # Fallback to a generated key if the env var is invalid, or raise an error.
            # Forcing a correct key in dev, but in prod this should be a hard failure.
            if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('FLASK_DEBUG') == '1':
                logging.warning("Falling back to a newly generated 32-byte key for development.")
                ENCRYPTION_KEY = os.urandom(32)
            else:
                raise ValueError("ENCRYPTION_KEY must be 32 bytes long. Invalid key provided.")
        else: # Should not happen with os.urandom(32)
            ENCRYPTION_KEY = os.urandom(32)

    # Cache settings
    CACHE_TYPE = 'SimpleCache'  # In-memory cache
    CACHE_DEFAULT_TIMEOUT = 300   # 5 minutes
    CACHE_THRESHOLD = 500         # Max number of items in cache

    # --- Email Configuration ---
    # The MAIL_DEFAULT_SENDER_NAME and MAIL_DEFAULT_SENDER_EMAIL might still be useful for display purposes
    # or if some parts of Flask-Mail are kept for other reasons, but sending will be via Gmail API.
    MAIL_DEFAULT_SENDER_NAME = os.environ.get('MAIL_DEFAULT_SENDER_NAME') or 'Your App Name'
    MAIL_DEFAULT_SENDER_EMAIL = os.environ.get('MAIL_DEFAULT_SENDER_EMAIL') or 'your-app-sender-email@example.com' # This should match GOOGLE_SENDER_EMAIL
    MAIL_DEFAULT_SENDER = (MAIL_DEFAULT_SENDER_NAME, MAIL_DEFAULT_SENDER_EMAIL)

    # Gmail API Configuration (replaces SMTP for sending)
    # These MUST be set in your environment variables for production.
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    # This refresh token is obtained after a one-time OAuth2 flow authorizing your app
    # to send emails on behalf of GOOGLE_SENDER_EMAIL.
    GOOGLE_REFRESH_TOKEN = os.environ.get('GOOGLE_REFRESH_TOKEN')
    GOOGLE_SENDER_EMAIL = os.environ.get('GOOGLE_SENDER_EMAIL') # The email address authorized to send

    # Commenting out old SMTP specific Flask-Mail configurations as they will be replaced by Gmail API for sending.
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't'] # Defaults to True for Gmail
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() in ['true', '1', 't'] # Defaults to False if using TLS
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') # e.g., your.email@gmail.com
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') # Your Gmail App Password or regular password

    # For itsdangerous token generation (used for confirmation links)
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT') or 'your-very-secure-salt' # IMPORTANT: Change this and set as environment variable
    CONFIRMATION_TOKEN_EXPIRATION = 3600  # Token valid for 1 hour (in seconds)

    # Rate Limiting (example, adjust as needed)
    RATELIMIT_DEFAULT = "200 per day, 50 per hour" # Default for most routes
    RATELIMIT_STRATEGIES = "fixed-window"
    RATELIMIT_STORAGE_URI = "memory://" # Use Redis in production: "redis://localhost:6379/1"

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    # Add development-specific settings, e.g.
    # SQLALCHEMY_ECHO = True

class TestingConfig(Config):
    TESTING = True
    # Testing-specific settings (e.g., different database)

class ProductionConfig(Config):
    DEBUG = False
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    # Add production-specific settings, e.g.
    # Consider more robust logging, mail server for errors, etc.
    # Example: os.environ.get('DATABASE_URL') or \
    #          'sqlite:///' + os.path.join(basedir, 'data.sqlite')

# You can add other configurations like TestingConfig if needed
# class TestingConfig(Config):
#     TESTING = True
#     SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 