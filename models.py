from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid # For generating unique tokens if not using itsdangerous's features directly for storage

db = SQLAlchemy()

class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    # Using a string for the token. itsdangerous generates tokens that can be stored.
    # Alternatively, you could generate a UUID here and use itsdangerous to sign it.
    confirmation_token = db.Column(db.String(100), unique=True, nullable=True) 
    
    is_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    
    subscribed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    unsubscribed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<Subscription {self.email}>"

# Example of another model if you have users, for context
# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(80), unique=True, nullable=False)
#     email = db.Column(db.String(120), unique=True, nullable=False)

#     def __repr__(self):
#         return f"<User {self.username}>"

def init_app(app):
    """Initialize the database with the Flask app."""
    db.init_app(app)
    # You might want to create tables if they don't exist,
    # but typically Flask-Migrate is used for migrations.
    # with app.app_context():
    #     db.create_all() 