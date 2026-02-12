"""
JWT Authentication utilities and decorators
"""

import jwt
from functools import wraps
from flask import request, jsonify
from config import JWT_SECRET


def verify_jwt_token(token):
    """
    Verify JWT token and return decoded payload.
    Returns (success: bool, payload: dict or None, error: str or None)
    """
    if not token:
        return False, None, 'No token provided'
    
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return True, decoded, None
    except jwt.ExpiredSignatureError:
        return False, None, 'Token has expired'
    except jwt.InvalidTokenError as e:
        return False, None, f'Invalid token: {str(e)}'


def get_user_from_request():
    """
    Extract and verify user information from Authorization header.
    Returns (success: bool, user_data: dict or None, error: str or None)
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return False, None, 'Authorization header required'
    
    success, payload, error = verify_jwt_token(auth_header)
    if not success:
        return False, None, error
    
    return True, payload, None


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        success, user_data, error = get_user_from_request()
        if not success:
            return jsonify({'error': error or 'Authentication required'}), 401
        
        # Attach user data to request for use in route
        request.user = user_data
        return f(*args, **kwargs)
    return decorated_function


def optional_auth(f):
    """Decorator to make authentication optional"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        request.user = None
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                success, user_data, error = verify_jwt_token(auth_header)
                if success and user_data is not None:
                    request.user = user_data
            except Exception:
                # Any token error: treat as anonymous
                request.user = None
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Allow OPTIONS requests for CORS preflight
        if request.method == 'OPTIONS':
            return jsonify({}), 200
        
        success, user_data, error = get_user_from_request()
        if not success:
            return jsonify({'error': error or 'Authentication required'}), 401
        
        if user_data.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        # Attach user data to request for use in route
        request.user = user_data
        return f(*args, **kwargs)
    return decorated_function
