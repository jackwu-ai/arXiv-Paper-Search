import logging
import os
from flask import Flask, render_template, jsonify, request
from config import config
from flask_caching import Cache

# Import custom template filters
from . import template_filters

cache = Cache()

# Import blueprints and error handlers if they are defined in separate modules
from .routes import main as main_blueprint
# from .errors import page_not_found_error, internal_server_error_handler # Assuming you might have these

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions here
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

    return app 