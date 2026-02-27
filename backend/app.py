"""
Flask API Server for Turtle Project
Handles photo uploads, matching, and review queue
"""

import os
import sys
import json
import time
import jwt
import threading
import socket
from functools import wraps
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file
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

# Load environment variables from .env file
# Only load backend/.env and root .env - keep auth-backend completely separate
env_paths = [
    Path(__file__).parent / '.env',  # backend/.env (highest priority)
    Path(__file__).parent.parent / '.env',  # root .env (for shared config like JWT_SECRET)
]

# Load .env files in priority order
env_loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path, override=False)  # Don't override if already set
        try:
            print(f"✅ Loaded .env from: {env_path}")
        except UnicodeEncodeError:
            print(f"[OK] Loaded .env from: {env_path}")
        env_loaded = True

if not env_loaded:
    try:
        print("⚠️  No .env file found. Using environment variables or defaults.")
    except UnicodeEncodeError:
        print("[WARN] No .env file found. Using environment variables or defaults.")

# Ensure PORT is set to 5000 for Flask backend (default)
if 'PORT' not in os.environ:
    os.environ['PORT'] = '5000'
    try:
        print("🔧 Using default PORT=5000 for Flask backend")
    except UnicodeEncodeError:
        print("[CFG] Using default PORT=5000 for Flask backend")

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend


# Define health check endpoints BEFORE initializing TurtleManager
# This ensures the server can respond to health checks immediately
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint - available immediately"""
    manager_status = 'ready' if manager is not None else 'loading'
    response = jsonify({
        'status': 'ok', 
        'message': 'Turtle API is running',
        'manager': manager_status
    })
    # Ensure proper headers for health check
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/', methods=['GET'])
def root():
    """Simple root endpoint for health checks"""
    response = jsonify({'status': 'ok'})
    response.headers['Content-Type'] = 'application/json'
    return response

# Initialize Turtle Manager in background thread to avoid blocking server start
# This allows the server to start immediately and respond to health checks
manager = None
manager_ready = threading.Event()

def initialize_manager():
    """Initialize Turtle Manager in background thread"""
    global manager
    try:
        manager = TurtleManager()
        manager_ready.set()
        try:
            print("✅ TurtleManager initialized successfully")
        except UnicodeEncodeError:
            print("[OK] TurtleManager initialized successfully")
    except Exception as e:
        try:
            print(f"❌ Error initializing TurtleManager: {str(e)}")
        except UnicodeEncodeError:
            print(f"[ERROR] Error initializing TurtleManager: {str(e)}")
        manager_ready.set()  # Set even on error so server can continue

# Start manager initialization in background
manager_thread = threading.Thread(target=initialize_manager, daemon=True)
manager_thread.start()

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

@app.route('/api/upload', methods=['POST'])
@optional_auth
def upload_photo():
    """
    Upload photo endpoint
    - Admin: Process immediately and return top 5 matches
    - Community/Anonymous: Save to review queue with top 5 matches

    Authentication is optional. If no token is provided, upload is treated as anonymous.
    """
    # Wait for manager to be ready (with timeout)
    if not manager_ready.wait(timeout=30):
        return jsonify({'error': 'TurtleManager is still initializing. Please try again in a moment.'}), 503

    if manager is None:
        return jsonify({'error': 'TurtleManager failed to initialize'}), 500

    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        # Get user data from verified JWT token (if provided)
        user_data = request.user
        if user_data:
            user_role = user_data.get('role', 'community')
            user_email = user_data.get('email', 'anonymous')
        else:
            # Anonymous upload
            user_role = 'community'
            user_email = 'anonymous'

        file = request.files['file']
        state = request.form.get('state', '')  # Optional: State where turtle was found
        location = request.form.get('location', '')  # Optional: Specific location

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': 'File too large (max 5MB)'}), 400

        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(temp_path)

        if not os.path.exists(temp_path):
            return jsonify({'error': 'Failed to save file'}), 500

        if user_role == 'admin':
            # Admin: Process immediately and return matches
            # search_for_matches now returns (results, time_elapsed) in the new manager
            matches, _ = manager.search_for_matches(temp_path)

            # Format matches for frontend
            formatted_matches = []
            for match in matches:
                # Convert .pt path to image path
                pt_path = match.get('file_path', '')
                image_path = convert_pt_to_image_path(pt_path)

                # ARCHITECT NOTE: Updated to use Deep Learning metrics (score/confidence) instead of distance
                formatted_matches.append({
                    'turtle_id': match.get('site_id', 'Unknown'),
                    'location': match.get('location', 'Unknown'),
                    'score': int(match.get('score', 0)),
                    'confidence': float(match.get('confidence', 0.0)),
                    'file_path': image_path,  # Now contains image path, not .pt path
                    'filename': os.path.basename(image_path) if image_path else ''
                })

            # Create a temporary request ID for this admin upload
            request_id = f"admin_{int(time.time())}_{filename}"

            # Adjust message based on number of matches
            if len(formatted_matches) > 0:
                message = f'Photo processed successfully. {len(formatted_matches)} matches found.'
            else:
                message = 'Photo processed successfully. No matches found. You can create a new turtle.'

            return jsonify({
                'success': True,
                'request_id': request_id,
                'matches': formatted_matches,
                'uploaded_image_path': temp_path,
                'message': message
            })

        else:
            # Community or Anonymous: Save to review queue
            if user_email == 'anonymous':
                finder_name = 'Anonymous User'
            else:
                finder_name = user_email.split('@')[0] if '@' in user_email else 'anonymous'

            user_info = {
                'finder': finder_name,
                'email': user_email,
                'uploaded_at': time.time()
            }
            # Add location data if provided
            if state and location:
                user_info['state'] = state
                user_info['location'] = location

            request_id = manager.create_review_packet(
                temp_path,
                user_info=user_info
            )

            return jsonify({
                'success': True,
                'request_id': request_id,
                'message': 'Photo uploaded successfully. Waiting for admin review.'
            })

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        try:
            print(f"❌ Error processing upload: {str(e)}")
        except UnicodeEncodeError:
            print(f"[ERROR] Error processing upload: {str(e)}")
        print(f"Traceback:\n{error_trace}")
        return jsonify({
            'error': f'Processing failed: {str(e)}',
            'details': error_trace if app.debug else None
        }), 500

    finally:
        # Keep temp file for now (will be cleaned up later)
        pass

@app.route('/api/review-queue', methods=['GET'])
@require_admin
def get_review_queue():
    """
    Get all pending review queue items (Admin only)
    Returns list of community uploads waiting for review
    """
    # Wait for manager to be ready
    if not manager_ready.wait(timeout=30):
        return jsonify({'error': 'TurtleManager is still initializing. Please try again in a moment.'}), 503
    if manager is None:
        return jsonify({'error': 'TurtleManager failed to initialize'}), 500

    try:
        queue_items = manager.get_review_queue()

        # Load metadata and candidate matches for each item
        formatted_items = []
        for item in queue_items:
            request_id = item['request_id']
            packet_dir = item['path']

            # Load metadata
            metadata_path = os.path.join(packet_dir, 'metadata.json')
            metadata = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)

            # Find the uploaded image
            uploaded_image = None
            for f in os.listdir(packet_dir):
                if f.lower().endswith(('.jpg', '.png', '.jpeg')) and f != 'metadata.json':
                    uploaded_image = os.path.join(packet_dir, f)
                    break

            # Get candidate matches
            candidates_dir = os.path.join(packet_dir, 'candidate_matches')
            candidates = []
            if os.path.exists(candidates_dir):
                for candidate_file in sorted(os.listdir(candidates_dir)):
                    if candidate_file.lower().endswith(('.jpg', '.png', '.jpeg')):
                        # Parse rank, ID, and score from filename: Rank1_IDT101_Score85.jpg
                        parts = candidate_file.replace('.jpg', '').replace('.png', '').replace('.jpeg', '').split('_')
                        rank = 0
                        turtle_id = 'Unknown'
                        score = 0

                        for part in parts:
                            if part.startswith('Rank'):
                                rank = int(part.replace('Rank', ''))
                            elif part.startswith('ID'):
                                turtle_id = part.replace('ID', '')
                            elif part.startswith('Score'):
                                score = int(part.replace('Score', ''))

                        candidates.append({
                            'rank': rank,
                            'turtle_id': turtle_id,
                            'score': score,
                            'image_path': os.path.join(candidates_dir, candidate_file)
                        })

            formatted_items.append({
                'request_id': request_id,
                'uploaded_image': uploaded_image,
                'metadata': metadata,
                'candidates': sorted(candidates, key=lambda x: x['rank']),
                'status': 'pending'
            })

        return jsonify({
            'success': True,
            'items': formatted_items
        })

    except Exception as e:
        return jsonify({'error': f'Failed to load review queue: {str(e)}'}), 500

@app.route('/api/review/<request_id>/approve', methods=['POST'])
@require_admin
def approve_review(request_id):
    """
    Approve a review queue item (Admin only)
    Admin selects which of the 5 matches is the correct one, OR creates a new turtle
    """
    # Wait for manager to be ready
    if not manager_ready.wait(timeout=30):
        return jsonify({'error': 'TurtleManager is still initializing. Please try again in a moment.'}), 503
    if manager is None:
        return jsonify({'error': 'TurtleManager failed to initialize'}), 500

    data = request.json
    match_turtle_id = data.get('match_turtle_id')  # The turtle ID that was selected
    new_location = data.get('new_location')  # Optional: if creating new turtle (format: "State/Location")
    new_turtle_id = data.get('new_turtle_id')  # Optional: Turtle ID for new turtle (e.g., "T101")
    uploaded_image_path = data.get('uploaded_image_path')  # Optional: direct path for admin uploads

    try:
        success, message = manager.approve_review_packet(
            request_id,
            match_turtle_id=match_turtle_id,
            new_location=new_location,
            new_turtle_id=new_turtle_id,
            uploaded_image_path=uploaded_image_path
        )

        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        try:
            print(f"❌ Error approving review: {str(e)}")
        except UnicodeEncodeError:
            print(f"[ERROR] Error approving review: {str(e)}")
        print(f"Traceback:\n{error_trace}")
        return jsonify({'error': f'Failed to approve review: {str(e)}'}), 500

@app.route('/api/images', methods=['GET'])
def serve_image():
    """
    Serve images from the file system
    Used to display uploaded images and matches in the frontend
    Query parameter: path=<encoded_image_path>
    """
    image_path = request.args.get('path')
    if not image_path:
        return jsonify({'error': 'No path provided'}), 400

    # Decode the path
    try:
        from urllib.parse import unquote
        decoded_path = unquote(image_path)
    except:
        decoded_path = image_path

    # Security: Only serve images from allowed directories
    safe_path = os.path.normpath(decoded_path)

    # Check if path is within data directory or temp directory
    # Wait for manager to be ready
    if not manager_ready.wait(timeout=5):
        return jsonify({'error': 'TurtleManager is still initializing'}), 503
    if manager is None:
        return jsonify({'error': 'TurtleManager failed to initialize'}), 500

    data_dir = os.path.abspath(os.path.normpath(manager.base_dir))
    temp_dir = os.path.abspath(os.path.normpath(UPLOAD_FOLDER))

    def is_path_within_base(file_path, base_dir):
        """
        Safely check if file_path is within base_dir using os.path.commonpath.
        This prevents path traversal attacks that startswith() would allow.
        """
        try:
            file_abs = os.path.abspath(os.path.normpath(file_path))
            base_abs = os.path.abspath(os.path.normpath(base_dir))
            # Get the common path and verify it equals the base directory
            common = os.path.commonpath([file_abs, base_abs])
            return common == base_abs
        except (ValueError, OSError):
            # ValueError can occur if paths are on different drives (Windows)
            # OSError can occur for invalid paths
            return False

    full_path = None
    # Check if path is absolute and within allowed directories
    if os.path.isabs(safe_path):
        if is_path_within_base(safe_path, data_dir) or is_path_within_base(safe_path, temp_dir):
            if os.path.exists(safe_path) and os.path.isfile(safe_path):
                full_path = safe_path
    else:
        # Relative path - try to resolve it
        for base_dir in [data_dir, temp_dir]:
            potential_path = os.path.normpath(os.path.join(base_dir, safe_path))
            if os.path.exists(potential_path) and os.path.isfile(potential_path):
                # Verify it's still within the base directory using safe check
                if is_path_within_base(potential_path, base_dir):
                    full_path = potential_path
                    break

    if not full_path or not os.path.exists(full_path):
        return jsonify({'error': 'Image not found'}), 404

    return send_file(full_path)

if __name__ == '__main__':
    # Determine if debug mode should be enabled
    # Disable debug mode for tests to avoid reload issues
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    port = int(os.environ.get('PORT', '5000'))

    try:
        print("🐢 Starting Turtle API Server...", flush=True)
        print(f"🌐 Server will be available at http://localhost:{port}", flush=True)
        if manager is not None:
            print(f"📁 Data directory: {manager.base_dir}", flush=True)
        sys.stdout.flush()
    except UnicodeEncodeError:
        print("[TURTLE] Starting Turtle API Server...", flush=True)
        print(f"[NET] Server will be available at http://localhost:{port}", flush=True)
        if manager is not None:
            print(f"[DIR] Data directory: {manager.base_dir}", flush=True)
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