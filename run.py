import os
from app import create_app
from config import config

# Determine the configuration to use
# You can set FLASK_CONFIG in your environment, e.g., 'production' or 'development'
config_name = os.getenv('FLASK_CONFIG', 'default')

app = create_app(config_name)

if __name__ == '__main__':
    # Flask's development server is not suitable for production.
    # Use a production WSGI server like Gunicorn or uWSGI for deployment.
    # Example: gunicorn -w 4 -b 0.0.0.0:5000 run:app
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 