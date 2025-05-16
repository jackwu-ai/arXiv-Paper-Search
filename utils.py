from flask import current_app, render_template, url_for
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from threading import Thread

# This should be initialized in your app factory (e.g., in app.py or create_app() function)
# from flask_mail import Mail
# mail = Mail()

# Placeholder for mail instance, assuming it's initialized in app.py and passed or accessed via current_app

def send_async_email(app, msg):
    with app.app_context():
        current_app.extensions['mail'].send(msg)

def send_email(to_email, subject, template_name_or_html, **kwargs):
    """Sends an email.

    Args:
        to_email (str): The recipient's email address.
        subject (str): The subject of the email.
        template_name_or_html (str): The name of the HTML template file (e.g., 'emails/confirmation.html')
                                     OR the raw HTML content of the email.
        **kwargs: Keyword arguments to pass to the template.
    """
    app = current_app._get_current_object()
    
    # Construct the sender tuple from config if it's a tuple, otherwise use it as is
    sender_config = app.config.get('MAIL_DEFAULT_SENDER')
    if isinstance(sender_config, tuple):
        sender = sender_config
    else: # Assume it's a simple string email address
        sender = (app.config.get('APP_NAME', 'Your App'), sender_config) # Use a default app name if not set

    msg = Message(subject, sender=sender, recipients=[to_email])

    try:
        # Check if it's a template file or raw HTML
        if '.html' in template_name_or_html and not '<' in template_name_or_html: # Basic check for template file
            msg.html = render_template(template_name_or_html, **kwargs)
        else:
            msg.html = template_name_or_html # Assume it's raw HTML
    except Exception as e:
        app.logger.error(f"Error rendering email template {template_name_or_html}: {e}", exc_info=True)
        # Fallback to a plain text message or handle error appropriately
        msg.body = f"Could not render HTML template. Subject: {subject}. Details: {kwargs.get('details', '')}"
        # Or, re-raise the error if email sending is critical and should fail loudly
        # raise

    # Send email asynchronously
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    app.logger.info(f"Email sending thread started for {to_email} with subject '{subject}'.")
    return thr

def generate_confirmation_token(email):
    """Generates a confirmation token for the given email."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=current_app.config['SECURITY_PASSWORD_SALT'])

def verify_confirmation_token(token, max_age_seconds=None):
    """Verifies a confirmation token.

    Args:
        token (str): The token to verify.
        max_age_seconds (int, optional): The maximum age of the token in seconds.
                                         Defaults to app.config['CONFIRMATION_TOKEN_EXPIRATION'].

    Returns:
        str or bool: The email address if the token is valid, False otherwise.
    """
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    if max_age_seconds is None:
        max_age_seconds = current_app.config.get('CONFIRMATION_TOKEN_EXPIRATION', 3600)
    
    try:
        email = serializer.loads(
            token,
            salt=current_app.config['SECURITY_PASSWORD_SALT'],
            max_age=max_age_seconds
        )
        return email
    except SignatureExpired:
        current_app.logger.warning(f"Confirmation token expired: {token}")
        return False
    except BadTimeSignature:
        current_app.logger.warning(f"Confirmation token has bad signature: {token}")
        return False
    except Exception as e: # Catch any other itsdangerous errors or general errors
        current_app.logger.error(f"Error verifying confirmation token {token}: {e}")
        return False 