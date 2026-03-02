"""
Flask API Server for Turtle Project
Handles photo uploads, matching, and review queue
"""

import os
import sys
import threading # ARCHITECT FIX: Restored missing threading import
import time      # ARCHITECT FIX: Restored missing time import
import json      # ARCHITECT FIX: Restored missing json import
import jwt       # ARCHITECT FIX: Restored missing jwt import
from functools import wraps # ARCHITECT FIX: Restored missing wraps import

# Import configuration first (sets up environment)
import config

# Import Flask and CORS
from flask import Flask, request, jsonify, send_file # ARCHITECT FIX: Restored missing Flask utilities
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.serving import make_server
import tempfile
from turtle_manager import TurtleManager

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    # Set stdout/stderr encoding to UTF-8 on Windows
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError, OSError):
        # If reconfigure fails, try to set encoding via environment
        # This won't affect current process but helps with subprocesses
        pass

# Import services
from services import manager_service

# Import routes
from routes.health import register_health_routes
from routes.upload import register_upload_routes
from routes.review import register_review_routes
from routes.images import register_image_routes
from routes.sheets import register_sheets_routes
from routes.turtles import register_turtle_routes

# Create Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})  # Enable CORS for frontend

# Add after_request handler to ensure CORS headers are always set
@app.after_request
def after_request(response):
    # Add CORS headers to all responses
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

# Register all routes
register_health_routes(app)
register_upload_routes(app)
register_review_routes(app)
register_image_routes(app)
register_sheets_routes(app)
register_turtle_routes(app)

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# JWT Configuration - must match auth-backend JWT_SECRET
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')

if JWT_SECRET == 'your-secret-key-change-in-production':
    try:
        print("⚠️  WARNING: Using default JWT_SECRET. This should match auth-backend JWT_SECRET!")
    except UnicodeEncodeError:
        print("[WARN] WARNING: Using default JWT_SECRET. This should match auth-backend JWT_SECRET!")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        auth_header = request.headers.get('Authorization')
        if auth_header:
            success, user_data, error = verify_jwt_token(auth_header)
            if success:
                request.user = user_data
            else:
                # Invalid token, treat as anonymous
                request.user = None
        else:
            # No token provided, treat as anonymous
            request.user = None
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        success, user_data, error = get_user_from_request()
        if not success:
            return jsonify({'error': error or 'Authentication required'}), 401

        if user_data.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        # Attach user data to request for use in route
        request.user = user_data
        return f(*args, **kwargs)
    return decorated_function

# ARCHITECT NOTE: Renamed and updated to strictly handle PyTorch .pt tensors
def convert_pt_to_image_path(pt_path):
    """
    Convert a .pt file path to the corresponding image file path.
    Tries common image extensions (.jpg, .jpeg, .png).
    Returns the image path if found, otherwise returns the original pt_path.
    """
    if not pt_path or not pt_path.endswith('.pt'):
        return pt_path

    # Try to find the corresponding image file
    base_path = pt_path[:-3]  # Remove .pt extension
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

    for ext in image_extensions:
        image_path = base_path + ext
        if os.path.exists(image_path) and os.path.isfile(image_path):
            return image_path

    # If no image found, return original (might be an error case)
    return pt_path

@app.errorhandler(Exception)
def handle_exception(err):
    """Log unhandled exceptions and return JSON (works in debug mode too)."""
    import traceback
    tb = traceback.format_exc()
    prefix = "[UNHANDLED]"
    sys.stderr.write(f"{prefix} {err}\n{tb}")
    sys.stderr.flush()
    try:
        print(f"{prefix} {err}", flush=True)
    except Exception:
        pass
    return (
        {'error': f'Server error: {str(err)}', 'details': tb if app.debug else None},
        500,
        {'Content-Type': 'application/json'},
    )

if __name__ == '__main__':
    # Determine if debug mode should be enabled
    # Disable debug mode for tests to avoid reload issues
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    port = int(os.environ.get('PORT', '5000'))

    try:
        print("🐢 Starting Turtle API Server...", flush=True)
        print(f"🌐 Server will be available at http://localhost:{port}", flush=True)
        if manager_service.manager is not None:
            print(f"📁 Data directory: {manager_service.manager.base_dir}", flush=True)
        sys.stdout.flush()
    except UnicodeEncodeError:
        print("[TURTLE] Starting Turtle API Server...", flush=True)
        print(f"[NET] Server will be available at http://localhost:{port}", flush=True)
        if manager_service.manager is not None:
            print(f"[DIR] Data directory: {manager_service.manager.base_dir}", flush=True)
        sys.stdout.flush()

    try:
        # Use Werkzeug's development server which prints when ready
        # This ensures we can see when the server actually starts
        app.run(debug=debug_mode, host='0.0.0.0', port=port, use_reloader=False)
    except Exception as e:
        print(f"[ERROR] Exception during app.run(): {str(e)}", flush=True)
        sys.stdout.flush()
        import traceback
        traceback.print_exc()
        sys.stderr.flush()