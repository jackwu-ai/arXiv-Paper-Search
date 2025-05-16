import os
from dotenv import load_dotenv
import logging

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here' # IMPORTANT: Change this and set as environment variable
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db' # Example for SQLite
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RESULTS_PER_PAGE = 10 # Default number of results per search page
    LOG_TO_STDOUT = False # Default to False, can be overridden by env or specific configs
    LOG_LEVEL = logging.INFO # Default log level

    # Cache settings
    CACHE_TYPE = 'SimpleCache'  # In-memory cache
    CACHE_DEFAULT_TIMEOUT = 300   # 5 minutes
    CACHE_THRESHOLD = 500         # Max number of items in cache

    # Mail Configuration - Replace with your actual email server details
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.example.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL') is None # TLS is generally preferred over SSL
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'your-email@example.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'your-email-password'
    MAIL_DEFAULT_SENDER_NAME = os.environ.get('MAIL_DEFAULT_SENDER_NAME') or 'Your App Name'
    MAIL_DEFAULT_SENDER_EMAIL = os.environ.get('MAIL_DEFAULT_SENDER_EMAIL') or 'noreply@yourdomain.com'
    MAIL_DEFAULT_SENDER = (MAIL_DEFAULT_SENDER_NAME, MAIL_DEFAULT_SENDER_EMAIL)

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