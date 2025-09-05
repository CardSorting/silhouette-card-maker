"""
Authentication routes for user registration, login, and token management.
"""

import re
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    jwt_required, get_jwt_identity, get_jwt, create_access_token
)
from marshmallow import Schema, fields, validate, ValidationError
from app.auth import auth_manager
from app.models import User, db

# Create auth blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


# Validation schemas
class UserRegistrationSchema(Schema):
    username = fields.Str(required=True, validate=[
        validate.Length(min=3, max=20),
        validate.Regexp(r'^[a-zA-Z0-9_]+$', error='Username can only contain letters, numbers, and underscores')
    ])
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=[
        validate.Length(min=8, max=128),
        validate.Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]', 
                       error='Password must contain at least one lowercase letter, one uppercase letter, one digit, and one special character')
    ])


class UserLoginSchema(Schema):
    username_or_email = fields.Str(required=True)
    password = fields.Str(required=True)


class PasswordChangeSchema(Schema):
    current_password = fields.Str(required=True)
    new_password = fields.Str(required=True, validate=[
        validate.Length(min=8, max=128),
        validate.Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]', 
                       error='Password must contain at least one lowercase letter, one uppercase letter, one digit, and one special character')
    ])


# Initialize schemas
registration_schema = UserRegistrationSchema()
login_schema = UserLoginSchema()
password_change_schema = PasswordChangeSchema()


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        # Validate input
        data = registration_schema.load(request.json)
        
        # Create user
        user = auth_manager.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password']
        )
        
        # Create tokens
        access_token, refresh_token = auth_manager.create_tokens(user)
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 201
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation failed',
            'code': 'VALIDATION_ERROR',
            'details': e.messages
        }), 400
        
    except ValueError as e:
        return jsonify({
            'error': str(e),
            'code': 'USER_EXISTS'
        }), 409
        
    except Exception as e:
        current_app.logger.error(f'Registration failed: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Registration failed',
            'code': 'REGISTRATION_ERROR'
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return tokens"""
    try:
        # Validate input
        data = login_schema.load(request.json)
        
        # Authenticate user
        user = auth_manager.authenticate_user(
            data['username_or_email'],
            data['password']
        )
        
        if not user:
            return jsonify({
                'error': 'Invalid credentials',
                'code': 'INVALID_CREDENTIALS'
            }), 401
        
        # Create tokens
        access_token, refresh_token = auth_manager.create_tokens(user)
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation failed',
            'code': 'VALIDATION_ERROR',
            'details': e.messages
        }), 400
        
    except Exception as e:
        current_app.logger.error(f'Login failed: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Login failed',
            'code': 'LOGIN_ERROR'
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({
                'error': 'User not found or inactive',
                'code': 'USER_NOT_FOUND'
            }), 401
        
        # Create new access token
        additional_claims = {
            'username': user.username,
            'email': user.email,
            'is_admin': user.is_admin
        }
        
        new_access_token = create_access_token(
            identity=user.id,
            additional_claims=additional_claims
        )
        
        return jsonify({
            'access_token': new_access_token
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Token refresh failed: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Token refresh failed',
            'code': 'REFRESH_ERROR'
        }), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user by revoking tokens"""
    try:
        jti = get_jwt()['jti']
        token_type = get_jwt()['type']
        expires_at = datetime.fromtimestamp(get_jwt()['exp'])
        user_id = get_jwt_identity()
        
        # Revoke current token
        auth_manager.revoke_token(jti, token_type, expires_at, user_id)
        
        return jsonify({
            'message': 'Logout successful'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Logout failed: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Logout failed',
            'code': 'LOGOUT_ERROR'
        }), 500


@auth_bp.route('/logout-all', methods=['POST'])
@jwt_required()
def logout_all():
    """Logout user from all devices by revoking all tokens"""
    try:
        user_id = get_jwt_identity()
        auth_manager.revoke_all_user_tokens(user_id)
        
        return jsonify({
            'message': 'Logged out from all devices'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Logout all failed: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Logout all failed',
            'code': 'LOGOUT_ALL_ERROR'
        }), 500


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'error': 'User not found',
                'code': 'USER_NOT_FOUND'
            }), 404
        
        return jsonify({
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Get profile failed: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Failed to get profile',
            'code': 'PROFILE_ERROR'
        }), 500


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'error': 'User not found',
                'code': 'USER_NOT_FOUND'
            }), 404
        
        data = request.json
        if not data:
            return jsonify({
                'error': 'No data provided',
                'code': 'NO_DATA'
            }), 400
        
        # Update allowed fields
        if 'email' in data:
            # Check if email is already taken
            existing_user = User.query.filter(
                User.email == data['email'],
                User.id != user_id
            ).first()
            if existing_user:
                return jsonify({
                    'error': 'Email already in use',
                    'code': 'EMAIL_EXISTS'
                }), 409
            user.email = data['email']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Update profile failed: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Failed to update profile',
            'code': 'UPDATE_PROFILE_ERROR'
        }), 500


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        # Validate input
        data = password_change_schema.load(request.json)
        
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'error': 'User not found',
                'code': 'USER_NOT_FOUND'
            }), 404
        
        # Verify current password
        if not user.check_password(data['current_password']):
            return jsonify({
                'error': 'Current password is incorrect',
                'code': 'INVALID_CURRENT_PASSWORD'
            }), 400
        
        # Set new password
        user.set_password(data['new_password'])
        db.session.commit()
        
        # Revoke all tokens to force re-login
        auth_manager.revoke_all_user_tokens(user_id)
        
        return jsonify({
            'message': 'Password changed successfully. Please log in again.'
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation failed',
            'code': 'VALIDATION_ERROR',
            'details': e.messages
        }), 400
        
    except Exception as e:
        current_app.logger.error(f'Change password failed: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Failed to change password',
            'code': 'CHANGE_PASSWORD_ERROR'
        }), 500


@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    """List all users (admin only)"""
    try:
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({
                'error': 'Admin access required',
                'code': 'ADMIN_REQUIRED'
            }), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        users = User.query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'pagination': {
                'page': users.page,
                'pages': users.pages,
                'per_page': users.per_page,
                'total': users.total,
                'has_next': users.has_next,
                'has_prev': users.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'List users failed: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Failed to list users',
            'code': 'LIST_USERS_ERROR'
        }), 500


@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """Update user (admin only)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({
                'error': 'Admin access required',
                'code': 'ADMIN_REQUIRED'
            }), 403
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'error': 'User not found',
                'code': 'USER_NOT_FOUND'
            }), 404
        
        data = request.json
        if not data:
            return jsonify({
                'error': 'No data provided',
                'code': 'NO_DATA'
            }), 400
        
        # Update allowed fields
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
        
        if 'is_admin' in data:
            user.is_admin = bool(data['is_admin'])
        
        if 'rate_limit_multiplier' in data:
            user.rate_limit_multiplier = float(data['rate_limit_multiplier'])
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Update user failed: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Failed to update user',
            'code': 'UPDATE_USER_ERROR'
        }), 500
