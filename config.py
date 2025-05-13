import os
from dotenv import load_dotenv
import logging

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '..', '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_hard_to_guess_string'
    # Add other global config settings here, e.g.
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db'
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
    RESULTS_PER_PAGE = 10 # Default number of results per search page
    LOG_TO_STDOUT = False # Default to False, can be overridden by env or specific configs
    LOG_LEVEL = logging.INFO # Default log level

    # Cache settings
    CACHE_TYPE = 'SimpleCache'  # In-memory cache
    CACHE_DEFAULT_TIMEOUT = 300   # 5 minutes
    CACHE_THRESHOLD = 500         # Max number of items in cache

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