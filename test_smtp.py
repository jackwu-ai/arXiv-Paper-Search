import smtplib
import os
from dotenv import load_dotenv

# Load environment variables from .env file in the current directory
load_dotenv()

# Get credentials from environment variables
# IMPORTANT: Ensure these EXACT variable names are in your .env file
# and that your NEW App Password is set for MAIL_PASSWORD
smtp_server = os.environ.get('MAIL_SERVER')
smtp_port = os.environ.get('MAIL_PORT')
login_user = os.environ.get('MAIL_USERNAME')
login_password = os.environ.get('MAIL_PASSWORD') # This should be your NEW App Password
sender_email = os.environ.get('MAIL_DEFAULT_SENDER_EMAIL')
receiver_email = "jackwuvancouver@gmail.com" # CHANGE THIS to an email you can check

print(f"Attempting to send email...")
print(f"SMTP Server: {smtp_server}")
print(f"SMTP Port: {smtp_port}")
print(f"Login User: {login_user}")
# Be careful about printing the password, even in a test script.
# For this test, we'll assume it's loaded. If it fails, we know it's an issue.
# print(f"Login Password: {'*' * len(login_password) if login_password else 'Not set'}")
print(f"Sender Email: {sender_email}")
print(f"Receiver Email: {receiver_email}")


if not all([smtp_server, smtp_port, login_user, login_password, sender_email]):
    print("Error: One or more email configuration variables are missing from .env")
    exit()

try:
    smtp_port = int(smtp_port) # Ensure port is an integer
    
    message = f"""\
Subject: SMTP Test Email from Python Script
To: {receiver_email}
From: {sender_email}

This is a test email sent directly via Python's smtplib."""

    # Try to connect and send
    print("\nConnecting to server...")
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.set_debuglevel(1)  # Show detailed SMTP conversation
        print("Starting TLS...")
        server.starttls()
        print("Logging in...")
        server.login(login_user, login_password)
        print("Sending email...")
        server.sendmail(sender_email, receiver_email, message)
        print("Email sent successfully!")

except smtplib.SMTPAuthenticationError as e:
    print(f"\nSMTP Authentication Error: {e}")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")
