"""
Database models for the Silhouette Card Maker API.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import bcrypt

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication and authorization"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    api_usage_count = db.Column(db.Integer, default=0, nullable=False)
    rate_limit_multiplier = db.Column(db.Float, default=1.0, nullable=False)
    
    # Relationships
    tokens = db.relationship('TokenBlacklist', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, username, email, password, is_admin=False):
        self.username = username
        self.email = email
        self.set_password(password)
        self.is_admin = is_admin
    
    def set_password(self, password):
        """Hash and set password using bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        """Check password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def increment_api_usage(self):
        """Increment API usage counter"""
        self.api_usage_count += 1
        db.session.commit()
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        """Convert user to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'api_usage_count': self.api_usage_count,
            'rate_limit_multiplier': self.rate_limit_multiplier
        }
    
    def __repr__(self):
        return f'<User {self.username}>'


class TokenBlacklist(db.Model):
    """Model for blacklisted JWT tokens"""
    
    __tablename__ = 'token_blacklist'
    
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, nullable=False, index=True)
    token_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    def __init__(self, jti, token_type, expires_at, user_id=None):
        self.jti = jti
        self.token_type = token_type
        self.expires_at = expires_at
        self.user_id = user_id
    
    def is_expired(self):
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f'<TokenBlacklist {self.jti}>'


class APILog(db.Model):
    """Model for logging API usage"""
    
    __tablename__ = 'api_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    endpoint = db.Column(db.String(255), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.Text, nullable=True)
    response_status = db.Column(db.Integer, nullable=False)
    response_time = db.Column(db.Float, nullable=False)
    request_size = db.Column(db.Integer, nullable=True)
    response_size = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='api_logs')
    
    def __init__(self, user_id, endpoint, method, ip_address, response_status, 
                 response_time, user_agent=None, request_size=None, response_size=None):
        self.user_id = user_id
        self.endpoint = endpoint
        self.method = method
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.response_status = response_status
        self.response_time = response_time
        self.request_size = request_size
        self.response_size = response_size
    
    def to_dict(self):
        """Convert log entry to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'endpoint': self.endpoint,
            'method': self.method,
            'ip_address': self.ip_address,
            'response_status': self.response_status,
            'response_time': self.response_time,
            'request_size': self.request_size,
            'response_size': self.response_size,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<APILog {self.method} {self.endpoint} - {self.response_status}>'


def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        
        # Create default admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password='admin123',  # Change this in production!
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Created default admin user: admin/admin123")
    
    return db
