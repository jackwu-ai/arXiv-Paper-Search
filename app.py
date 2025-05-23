print(f"Executing app.py from: {__file__}") # Print the path of the executing file
import sys
sys.path.insert(0, '.') # Ensure current directory is prioritized for imports

import os
# Remove direct Flask imports and extension initializations that are now handled in app/__init__.py
# from flask import Flask, render_template, request, jsonify, url_for, flash, redirect, current_app
# from app.arxiv_api import search_papers
# from app.exceptions import ArxivAPIException, ValidationException
# from openai import OpenAI, RateLimitError, APIError
# import datetime
# from flask_sqlalchemy import SQLAlchemy
# from flask_mail import Mail
# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address

# Remove template_filters and cache imports if they are only used by create_app (now in app/__init__)
# from app import template_filters 
# from app import cache

# Config import is fine if needed for os.getenv('FLASK_CONFIG')
from config import config # Dictionary of configurations

# Model and util imports are removed as routes are moved to app/routes.py
# from models import db, Subscription, init_app as init_db, _generate_email_hash 
# from utils import send_email, generate_confirmation_token, verify_confirmation_token

# mail and limiter instances are created in app/__init__.py
# mail = Mail()
# limiter = Limiter(
#     key_func=get_remote_address,
#     # default_limits=["200 per day", "50 per hour"] # This will be set from config
# )

# The create_app function and all routes are removed from here.
# They are now in app/__init__.py and app/routes.py respectively.

# Import create_app from the app package
from app import create_app

if __name__ == '__main__':
    # This is for local development testing only.
    # In production, use a WSGI server like Gunicorn or uWSGI.
    app_instance = create_app(os.getenv('FLASK_CONFIG') or 'default')
    
    # The db.create_all() logic is now handled within create_app in app/__init__.py
    # so it does not need to be repeated here.

    app_instance.run(debug=app_instance.config.get('DEBUG', True))