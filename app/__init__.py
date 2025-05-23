import logging
import os
import datetime
from flask import Flask, render_template, jsonify, request
from config import config
from .extensions import cache, mail, limiter

# Import custom template filters
from . import template_filters

# For Fernet encryption and db initialization
# from cryptography.fernet import Fernet # REMOVE FERNET
# from models import db as root_db, initialize_fernet as initialize_root_fernet # REMOVE - Assuming models.py is at project root
from .models import db, Subscription, _generate_email_hash, init_app as init_models_db # CORRECTED IMPORT

# Import scheduler initialization function
from .scheduler import init_scheduler

# Import blueprints and error handlers if they are defined in separate modules
from .routes import main as main_blueprint
# from .errors import page_not_found_error, internal_server_error_handler # Assuming you might have these

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Context Processor for datetime
    @app.context_processor
    def inject_now():
        return {'now': datetime.datetime}

    # Initialize Fernet encryption key and system - REMOVE ALL FERNET LOGIC
    # if 'FERNET_KEY' not in app.config or not app.config['FERNET_KEY']:
    #     fernet_key = Fernet.generate_key()
    #     app.config['FERNET_KEY'] = fernet_key
    #     app.logger.critical("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    #     app.logger.critical(f"FERNET_KEY was not found or was empty in config. A new key has been generated.")
    #     app.logger.critical(f"NEW FERNET_KEY: {fernet_key.decode()}")
    #     app.logger.critical("YOU MUST SAVE THIS KEY SECURELY (e.g., as an environment variable or in instance/config.py)")
    #     app.logger.critical("AND ENSURE IT IS LOADED INTO app.config['FERNET_KEY'] FOR ALL FUTURE RUNS.")
    #     app.logger.critical("IF THIS KEY IS LOST OR CHANGES, YOU WILL NOT BE ABLE TO DECRYPT EXISTING DATA.")
    #     app.logger.critical("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    # else:
    #     app.logger.info("FERNET_KEY loaded from configuration.")
    # 
    # initialize_root_fernet(app.config['FERNET_KEY'])
    # app.logger.info("Fernet encryption system initialized.")

    # Initialize SQLAlchemy instance from .models (within app package)
    init_models_db(app) # Use the init_app from app.models
    app.logger.info("SQLAlchemy (db from app.models) initialized with app.")

    # Initialize other extensions here
    mail.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)

    # Add Python built-ins to Jinja environment if needed
    app.jinja_env.globals['min'] = min
    app.jinja_env.globals['max'] = max 

    # Register custom template filters
    app.jinja_env.filters['format_date'] = template_filters.format_date
    app.jinja_env.filters['truncate_text'] = template_filters.truncate_text
    app.jinja_env.filters['highlight'] = template_filters.highlight_terms
    app.jinja_env.filters['sanitize_html'] = template_filters.sanitize_html
    app.jinja_env.filters['format_authors'] = template_filters.format_authors

    # Configure logging (ensure this is robust)
    if app.config.get('LOG_TO_STDOUT'):
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
    # Add else for file logging or other production logging if needed
    
    app.logger.setLevel(app.config.get('LOG_LEVEL', logging.INFO))
    app.logger.info(f'ArXiv App startup in {config_name} mode.')

    # Register blueprints
    app.register_blueprint(main_blueprint)
    # app.register_blueprint(auth_blueprint, url_prefix='/auth') # Example for other blueprints

    # Register error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        app.logger.warning(f'Page not found: {request.path} - {e}')
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        # For 500 errors, e might be an actual exception. Log it carefully.
        app.logger.error(f'Internal server error: {request.path} - {e}', exc_info=True)
        return render_template('500.html'), 500
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify(status="Healthy"), 200

    # Create database tables if they don't exist
    # IMPORTANT: This will not migrate existing tables if their schema changes.
    # For schema changes on existing tables, a migration tool like Flask-Migrate is recommended.
    with app.app_context():
        app.logger.info("Attempting to create database tables if they don't exist...")
        try:
            db.create_all() # Use db imported from .models
            app.logger.info("db.create_all() executed successfully.")
        except Exception as e:
            app.logger.error(f"Error during db.create_all(): {e}", exc_info=True)

    # Initialize and start the scheduler, only if not in testing mode
    # and ensure it runs only once (e.g., not in reloader subprocess)
    if not app.testing and not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        init_scheduler(app)
        app.logger.info("APScheduler initialization called.")
    elif app.testing:
        app.logger.info("APScheduler skipped in testing mode.")
    else: # app.debug is True but WERKZEUG_RUN_MAIN is not 'true'
        app.logger.info("APScheduler skipped in Flask reloader subprocess.")

    return app 