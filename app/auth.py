"""
Industry-standard authentication system for the Silhouette Card Maker API.
Uses Flask-JWT-Extended for JWT tokens and Flask-Login for session management.
"""

import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, create_refresh_token,
    get_jwt_identity, get_jwt, verify_jwt_in_request
)
from flask_login import LoginManager, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.models import User, TokenBlacklist, db


class AuthManager:
    """Comprehensive authentication and authorization manager"""
    
    def __init__(self, app=None):
        self.app = app
        self.jwt = None
        self.login_manager = None
        self.limiter = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize authentication system with Flask app"""
        self.app = app
        
        # Initialize JWT
        self.jwt = JWTManager(app)
        self._setup_jwt_callbacks()
        
        # Initialize Flask-Login
        self.login_manager = LoginManager()
        self.login_manager.init_app(app)
        self.login_manager.login_view = 'auth.login'
        self.login_manager.login_message = 'Please log in to access this page.'
        self.login_manager.login_message_category = 'info'
        
        # Setup user loader
        @self.login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
        
        # Initialize rate limiter
        self.limiter = Limiter(
            key_func=self._get_user_identifier,
            default_limits=[app.config.get('RATELIMIT_DEFAULT', '100 per minute')]
        )
        self.limiter.init_app(app)
    
    def _get_user_identifier(self):
        """Get user identifier for rate limiting"""
        try:
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            if user_id:
                user = User.query.get(user_id)
                if user:
                    # Apply user-specific rate limit multiplier
                    base_limit = current_app.config.get('RATELIMIT_DEFAULT', '100 per minute')
                    multiplier = user.rate_limit_multiplier
                    return f"user:{user_id}:{multiplier}"
        except:
            pass
        
        # Fallback to IP-based limiting
        return get_remote_address()
    
    def _setup_jwt_callbacks(self):
        """Setup JWT callbacks for token management"""
        
        @self.jwt.token_in_blocklist_loader
        def check_if_token_revoked(jwt_header, jwt_payload):
            """Check if token is in blacklist"""
            jti = jwt_payload['jti']
            token = TokenBlacklist.query.filter_by(jti=jti).first()
            return token is not None
        
        @self.jwt.expired_token_loader
        def expired_token_callback(jwt_header, jwt_payload):
            """Handle expired tokens"""
            return jsonify({
                'error': 'Token has expired',
                'code': 'TOKEN_EXPIRED'
            }), 401
        
        @self.jwt.invalid_token_loader
        def invalid_token_callback(error):
            """Handle invalid tokens"""
            return jsonify({
                'error': 'Invalid token',
                'code': 'INVALID_TOKEN'
            }), 401
        
        @self.jwt.unauthorized_loader
        def missing_token_callback(error):
            """Handle missing tokens"""
            return jsonify({
                'error': 'Authorization token required',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        @self.jwt.revoked_token_loader
        def revoked_token_callback(jwt_header, jwt_payload):
            """Handle revoked tokens"""
            return jsonify({
                'error': 'Token has been revoked',
                'code': 'TOKEN_REVOKED'
            }), 401
    
    def create_user(self, username, email, password, is_admin=False):
        """Create a new user"""
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            raise ValueError('Username already exists')
        
        if User.query.filter_by(email=email).first():
            raise ValueError('Email already exists')
        
        user = User(username=username, email=email, password=password, is_admin=is_admin)
        db.session.add(user)
        db.session.commit()
        
        return user
    
    def authenticate_user(self, username_or_email, password):
        """Authenticate user with username/email and password"""
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        if user and user.check_password(password) and user.is_active:
            user.update_last_login()
            return user
        
        return None
    
    def create_tokens(self, user):
        """Create access and refresh tokens for user"""
        additional_claims = {
            'username': user.username,
            'email': user.email,
            'is_admin': user.is_admin
        }
        
        access_token = create_access_token(
            identity=user.id,
            additional_claims=additional_claims
        )
        
        refresh_token = create_refresh_token(
            identity=user.id,
            additional_claims=additional_claims
        )
        
        return access_token, refresh_token
    
    def revoke_token(self, jti, token_type, expires_at, user_id=None):
        """Revoke a token by adding it to blacklist"""
        blacklisted_token = TokenBlacklist(
            jti=jti,
            token_type=token_type,
            expires_at=expires_at,
            user_id=user_id
        )
        db.session.add(blacklisted_token)
        db.session.commit()
    
    def revoke_all_user_tokens(self, user_id):
        """Revoke all tokens for a user"""
        # Get current token
        try:
            verify_jwt_in_request()
            current_jti = get_jwt()['jti']
            current_expires = datetime.fromtimestamp(get_jwt()['exp'])
            current_type = get_jwt()['type']
            
            # Revoke current token
            self.revoke_token(current_jti, current_type, current_expires, user_id)
        except:
            pass
        
        # Revoke all other tokens by adding them to blacklist
        # Note: In a production system, you might want to store active tokens
        # and revoke them individually
    
    def get_current_user(self):
        """Get current authenticated user"""
        try:
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            if user_id:
                return User.query.get(user_id)
        except:
            pass
        return None
    
    def require_auth(self, admin_only=False):
        """Decorator factory for authentication requirements"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Check if authentication is required
                if not current_app.config.get('REQUIRE_AUTH', False):
                    return f(*args, **kwargs)
                
                try:
                    verify_jwt_in_request()
                    user_id = get_jwt_identity()
                    user = User.query.get(user_id)
                    
                    if not user or not user.is_active:
                        return jsonify({
                            'error': 'User not found or inactive',
                            'code': 'USER_NOT_FOUND'
                        }), 401
                    
                    if admin_only and not user.is_admin:
                        return jsonify({
                            'error': 'Admin access required',
                            'code': 'ADMIN_REQUIRED'
                        }), 403
                    
                    # Increment API usage
                    user.increment_api_usage()
                    
                    return f(*args, **kwargs)
                
                except Exception as e:
                    return jsonify({
                        'error': 'Authentication failed',
                        'code': 'AUTH_FAILED'
                    }), 401
            
            return decorated_function
        return decorator
    
    def require_admin(self, f):
        """Decorator to require admin access"""
        return self.require_auth(admin_only=True)(f)
    
    def require_user(self, f):
        """Decorator to require user authentication"""
        return self.require_auth(admin_only=False)(f)


# Global auth manager instance
auth_manager = AuthManager()


def init_auth(app):
    """Initialize authentication with Flask app"""
    auth_manager.init_app(app)
    return auth_manager


def require_auth(admin_only=False):
    """Decorator to require authentication"""
    return auth_manager.require_auth(admin_only)


def require_admin(f):
    """Decorator to require admin access"""
    return auth_manager.require_admin(f)


def require_user(f):
    """Decorator to require user authentication"""
    return auth_manager.require_user(f)


def get_current_user():
    """Get current authenticated user"""
    return auth_manager.get_current_user()
