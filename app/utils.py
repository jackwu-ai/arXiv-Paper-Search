import os
from flask import current_app, url_for, render_template
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from threading import Thread

# Mail object needs to be imported from the app initialization (app.py or app/__init__.py)
# For now, we assume it will be available via current_app.extensions['mail']
# or passed directly if this util is refactored.

def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    salt = current_app.config.get('SECURITY_CONFIRMATION_SALT', 'email-confirmation-salt')
    return serializer.dumps(email, salt=salt)

def verify_confirmation_token(token, max_age_seconds=None):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    salt = current_app.config.get('SECURITY_CONFIRMATION_SALT', 'email-confirmation-salt')
    
    if max_age_seconds is None:
        # Use config value (in hours), convert to seconds. Default 1 hour.
        max_age_hours = current_app.config.get('SECURITY_TOKEN_MAX_AGE_HOURS', 1)
        max_age_seconds = max_age_hours * 3600

    try:
        email = serializer.loads(
            token,
            salt=salt,
            max_age=max_age_seconds
        )
        return email
    except SignatureExpired:
        current_app.logger.warning(f"Confirmation token expired: {token}")
        return False # Or raise custom exception
    except BadSignature:
        current_app.logger.warning(f"Bad signature for confirmation token: {token}")
        return False # Or raise custom exception
    except Exception as e:
        current_app.logger.error(f"Error verifying confirmation token {token}: {e}")
        return False

def _send_async_email(app, msg):
    with app.app_context():
        try:
            mail_ext = current_app.extensions.get('mail')
            if mail_ext:
                mail_ext.send(msg)
                current_app.logger.info(f"Async email sent to {msg.recipients} with subject '{msg.subject}'")
            else:
                current_app.logger.error("Flask-Mail extension not found on current_app.")
        except Exception as e:
            current_app.logger.error(f"Failed to send async email to {msg.recipients}: {e}", exc_info=True)

def send_email(to_email, subject, template_name_or_html, **kwargs):
    # Ensure we have an app context if called outside of a request context (e.g. by a celery task)
    # However, for Threading, app_context() from the caller is better.
    app = current_app._get_current_object() # Get the actual app instance
    mail_ext = app.extensions.get('mail')

    if not mail_ext:
        app.logger.error("Flask-Mail extension not properly initialized or found.")
        # Depending on desired behavior, either raise an error or silently fail/log.
        # For now, let's log and prevent an exception that might break a larger process.
        return False # Indicate failure

    msg = Message(
        subject,
        sender=app.config.get('MAIL_DEFAULT_SENDER', 'noreply@example.com'),
        recipients=[to_email]
    )

    # Determine if template_name_or_html is a template file or direct HTML content
    if '.html' in template_name_or_html or '.txt' in template_name_or_html:
        # Assumed to be a template file path (e.g., 'emails/confirmation_email.html')
        try:
            msg.html = render_template(template_name_or_html, **kwargs)
            # If you have a .txt version for the same email for clients that don't render HTML:
            # try:
            #     text_template_name = template_name_or_html.replace('.html', '.txt')
            #     msg.body = render_template(text_template_name, **kwargs)
            # except Exception:
            #     msg.body = "Please enable HTML to view this email correctly." # Fallback text part
        except Exception as e:
            app.logger.error(f"Error rendering email template {template_name_or_html}: {e}", exc_info=True)
            return False # Indicate failure
    else:
        # Assumed to be direct HTML string
        msg.html = template_name_or_html
        # msg.body = "Please enable HTML to view this email correctly." # Fallback text part if sending raw HTML

    # Send email asynchronously to avoid blocking the request
    # Note: Flask's app context handling with threads needs care.
    # It's better if the calling code (like a route) handles the app context if needed for the thread.
    # For simplicity here, _send_async_email will try to create its own context.
    # However, it's more robust to pass the app object as shown in Flask docs for async tasks.
    thread = Thread(target=_send_async_email, args=[app, msg])
    thread.start()
    app.logger.info(f"Email sending thread started for recipient {to_email}, subject '{subject}'.")
    return True # Indicate email sending process was initiated 