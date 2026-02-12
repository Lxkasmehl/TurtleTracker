"""
Photo upload endpoint
"""

import os
import time
import traceback
from flask import request, jsonify
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER, MAX_FILE_SIZE, allowed_file
from auth import optional_auth
from services import manager_service


def convert_npz_to_image_path(npz_path):
    """
    Convert a .npz file path to the corresponding image file path.
    Tries common image extensions (.jpg, .jpeg, .png).
    Returns the image path if found, otherwise returns the original npz_path.
    """
    if not npz_path or not npz_path.endswith('.npz'):
        return npz_path
    
    # Try to find the corresponding image file
    base_path = npz_path[:-4]  # Remove .npz extension
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    
    for ext in image_extensions:
        image_path = base_path + ext
        if os.path.exists(image_path) and os.path.isfile(image_path):
            return image_path
    
    # If no image found, return original (might be an error case)
    return npz_path


def register_upload_routes(app):
    """Register upload routes"""
    
    @app.route('/api/upload', methods=['POST'])
    @optional_auth
    def upload_photo():
        """
        Upload photo endpoint
        - Admin: Process immediately and return top 5 matches
        - Community/Anonymous: Save to review queue with top 5 matches
        
        Authentication is optional. If no token is provided, upload is treated as anonymous.
        """
        # Wait for manager to be ready (with timeout); use module ref so we see current value after background init
        if not manager_service.manager_ready.wait(timeout=30):
            return jsonify({'error': 'TurtleManager is still initializing. Please try again in a moment.'}), 503
        
        if manager_service.manager is None:
            return jsonify({'error': 'TurtleManager failed to initialize'}), 500
        
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            # Get user data from verified JWT token (if provided)
            user_data = getattr(request, 'user', None)
            if user_data and isinstance(user_data, dict):
                user_role = user_data.get('role', 'community')
                user_email = user_data.get('email', 'anonymous')
            else:
                # Anonymous upload
                user_role = 'community'
                user_email = 'anonymous'
            
            file = request.files['file']
            state = request.form.get('state', '')  # Optional: State where turtle was found
            location = request.form.get('location', '')  # Optional: Specific location
            # Optional: GPS/manual coordinates as hint only (never stored in sheets)
            location_hint_lat = request.form.get('location_hint_lat', type=float)
            location_hint_lon = request.form.get('location_hint_lon', type=float)
            location_hint_source = request.form.get('location_hint_source', '')  # 'gps' or 'manual'
            
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
                # Admin: Process immediately; optionally restrict to one location (sheet/datasheet)
                # match_sheet: sheet name from Google Sheets (e.g. "Location A"); empty = test against all
                match_sheet = (request.form.get('match_sheet') or '').strip() or None
                matches = manager_service.manager.search_for_matches(temp_path, sheet_name=match_sheet)
                if matches is None:
                    matches = []
                # Format matches for frontend
                formatted_matches = []
                for match in matches:
                    # Convert .npz path to image path
                    npz_path = match.get('file_path', '')
                    image_path = convert_npz_to_image_path(npz_path)
                    
                    formatted_matches.append({
                        'turtle_id': match.get('site_id', 'Unknown'),
                        'location': match.get('location', 'Unknown'),
                        'distance': float(match.get('distance', 0)),
                        'file_path': image_path,  # Now contains image path, not .npz path
                        'filename': match.get('filename', '')
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
                # Add location hint (coords) if provided – hint only, never stored in sheets
                if location_hint_lat is not None and location_hint_lon is not None:
                    user_info['location_hint_lat'] = location_hint_lat
                    user_info['location_hint_lon'] = location_hint_lon
                    if location_hint_source in ('gps', 'manual'):
                        user_info['location_hint_source'] = location_hint_source
                
                request_id = manager_service.manager.create_review_packet(
                    temp_path,
                    user_info=user_info
                )
                
                return jsonify({
                    'success': True,
                    'request_id': request_id,
                    'message': 'Photo uploaded successfully. Waiting for admin review.'
                })
        
        except Exception as e:
            error_trace = traceback.format_exc()
            err_msg = str(e)
            import sys
            # Force unbuffered error output so it appears in the terminal
            sys.stderr.write(f"Upload error: {err_msg}\n")
            sys.stderr.write(error_trace)
            sys.stderr.flush()
            try:
                print(f"❌ Error processing upload: {err_msg}", flush=True)
            except Exception:
                pass
            return jsonify({
                'error': f'Processing failed: {err_msg}',
                'details': error_trace if app.debug else None
            }), 500
        
        finally:
            # Keep temp file for now (will be cleaned up later)
            pass
