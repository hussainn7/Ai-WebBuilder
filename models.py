from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'  # explicitly set table name
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    chats = db.relationship('Chat', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Chat(db.Model):
    __tablename__ = 'chats'  # explicitly set table name
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, default="New Chat")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    messages = db.relationship('Message', backref='chat', lazy=True)

class Message(db.Model):
    __tablename__ = 'messages'  # explicitly set table name
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    is_user = db.Column(db.Boolean, nullable=False)  # True if user message, False if AI
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id'), nullable=False) 