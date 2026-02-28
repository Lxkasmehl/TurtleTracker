"""
Review queue endpoints
"""

import os
import json
import time
import traceback
from flask import request, jsonify
from werkzeug.utils import secure_filename
from auth import require_admin
from services import manager_service
from services.manager_service import get_sheets_service
from config import UPLOAD_FOLDER, MAX_FILE_SIZE, allowed_file


def register_review_routes(app):
    """Register review queue routes"""
    
    @app.route('/api/review-queue', methods=['GET'])
    @require_admin
    def get_review_queue():
        """
        Get all pending review queue items (Admin only)
        Returns list of community uploads waiting for review
        """
        # Wait for manager to be ready (use module ref so we see current value after background init)
        if not manager_service.manager_ready.wait(timeout=30):
            return jsonify({'error': 'TurtleManager is still initializing. Please try again in a moment.'}), 503
        if manager_service.manager is None:
            return jsonify({'error': 'TurtleManager failed to initialize'}), 500
        
        try:
            queue_items = manager_service.manager.get_review_queue()
            formatted_items = [_format_packet_item(item['path'], item['request_id']) for item in queue_items]
            return jsonify({'success': True, 'items': formatted_items})
        
        except Exception as e:
            return jsonify({'error': f'Failed to load review queue: {str(e)}'}), 500

    @app.route('/api/review-queue/<request_id>/additional-images', methods=['POST'])
    @require_admin
    def add_review_packet_additional_images(request_id):
        """Add microhabitat/condition images to an existing review packet (Admin only)."""
        if not manager_service.manager_ready.wait(timeout=30):
            return jsonify({'error': 'TurtleManager is still initializing.'}), 503
        if manager_service.manager is None:
            return jsonify({'error': 'TurtleManager failed to initialize'}), 500
        files_with_types = []
        try:
            for key in list(request.files.keys()):
                if not key.startswith('file_'):
                    continue
                f = request.files[key]
                if not f or not f.filename:
                    continue
                idx = key.replace('file_', '')
                typ = request.form.get(f'type_{idx}', 'other').strip().lower()
                if typ not in ('microhabitat', 'condition', 'other'):
                    typ = 'other'
                if not allowed_file(f.filename):
                    continue
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(0)
                if size > MAX_FILE_SIZE:
                    continue
                ext = os.path.splitext(secure_filename(f.filename))[1] or '.jpg'
                temp_path = os.path.join(UPLOAD_FOLDER, f"review_extra_{request_id}_{idx}_{int(time.time())}{ext}")
                f.save(temp_path)
                files_with_types.append({'path': temp_path, 'type': typ, 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
            if not files_with_types:
                return jsonify({'error': 'No valid image files provided'}), 400
            success, msg = manager_service.manager.add_additional_images_to_packet(request_id, files_with_types)
            for item in files_with_types:
                p = item.get('path')
                if p and os.path.isfile(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            if not success:
                return jsonify({'error': msg}), 400
            return jsonify({'success': True, 'message': f'Added {len(files_with_types)} image(s).'})
        except Exception as e:
            for item in files_with_types:
                p = item.get('path')
                if p and os.path.isfile(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            return jsonify({'error': str(e)}), 500

    @app.route('/api/review-queue/<request_id>/additional-images', methods=['DELETE'])
    @require_admin
    def remove_review_packet_additional_image(request_id):
        """Remove one microhabitat/condition image from a packet (Admin only). Body: { "filename": "..." }."""
        if not manager_service.manager_ready.wait(timeout=30):
            return jsonify({'error': 'TurtleManager is still initializing.'}), 503
        if manager_service.manager is None:
            return jsonify({'error': 'TurtleManager failed to initialize'}), 500
        data = request.get_json(silent=True) or {}
        filename = (data.get('filename') or '').strip()
        if not filename:
            return jsonify({'error': 'filename required'}), 400
        success, err = manager_service.manager.remove_additional_image_from_packet(request_id, filename)
        if not success:
            return jsonify({'error': err or 'Failed to remove image'}), 400
        return jsonify({'success': True})

    def _format_packet_item(packet_dir, request_id):
        """Build one queue item dict from packet_dir (used by get_review_queue and get_review_packet)."""
        metadata_path = os.path.join(packet_dir, 'metadata.json')
        metadata = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

        additional_images = []
        additional_dir = os.path.join(packet_dir, 'additional_images')

        # --- NEW LOGIC: Helper to parse manifest or folder ---
        def parse_manifest_or_folder(target_dir):
            results = []
            manifest_path = os.path.join(target_dir, 'manifest.json')
            processed_files = set()

            if os.path.isfile(manifest_path):
                try:
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                    for entry in manifest:
                        fn = entry.get('filename')
                        kind = entry.get('type', 'other')
                        if fn:
                            p = os.path.join(target_dir, fn)
                            if os.path.isfile(p):
                                results.append({
                                    'filename': fn,
                                    'type': kind,
                                    'timestamp': entry.get('timestamp'),
                                    'image_path': p,
                                })
                                processed_files.add(fn)
                except (json.JSONDecodeError, OSError):
                    pass

            # Fallback: catch images not in manifest (e.g., from tests or legacy uploads)
            if os.path.isdir(target_dir):
                for f in sorted(os.listdir(target_dir)):
                    if f != 'manifest.json' and f not in processed_files and f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                        results.append({
                            'filename': f,
                            'type': 'other',
                            'timestamp': None,
                            'image_path': os.path.join(target_dir, f),
                        })
            return results

        # Execute our folder scanning
        if os.path.isdir(additional_dir):
            # 1. Process legacy root folder
            additional_images.extend(parse_manifest_or_folder(additional_dir))

            # 2. Process our new Date-Stamped subfolders
            for item in sorted(os.listdir(additional_dir)):
                item_path = os.path.join(additional_dir, item)
                if os.path.isdir(item_path):
                    additional_images.extend(parse_manifest_or_folder(item_path))

        uploaded_image = None
        for f in os.listdir(packet_dir):
            if f.lower().endswith(('.jpg', '.png', '.jpeg')) and f != 'metadata.json' and not f.startswith('.'):
                uploaded_image = os.path.join(packet_dir, f)
                break

        candidates_dir = os.path.join(packet_dir, 'candidate_matches')
        candidates = []
        if os.path.exists(candidates_dir):
            for candidate_file in sorted(os.listdir(candidates_dir)):
                if candidate_file.lower().endswith(('.jpg', '.png', '.jpeg')):
                    parts = candidate_file.replace('.jpg', '').replace('.png', '').replace('.jpeg', '').split('_')
                    rank, turtle_id, score = 0, 'Unknown', 0
                    for part in parts:
                        if part.startswith('Rank'):
                            rank = int(part.replace('Rank', ''))
                        elif part.startswith('ID'):
                            turtle_id = part.replace('ID', '')
                        elif part.startswith('Score'):
                            score = int(part.replace('Score', ''))
                    candidates.append({'rank': rank, 'turtle_id': turtle_id, 'score': score, 'image_path': os.path.join(candidates_dir, candidate_file)})

        return {
            'request_id': request_id,
            'uploaded_image': uploaded_image,
            'metadata': metadata,
            'additional_images': additional_images,
            'candidates': sorted(candidates, key=lambda x: x['rank']),
            'status': 'pending',
        }

    @app.route('/api/review-queue/<request_id>', methods=['GET'])
    @require_admin
    def get_review_packet(request_id):
        """Get a single review packet by request_id (Admin only)."""
        if not manager_service.manager_ready.wait(timeout=30):
            return jsonify({'error': 'TurtleManager is still initializing.'}), 503
        if manager_service.manager is None:
            return jsonify({'error': 'TurtleManager failed to initialize'}), 500
        packet_dir = os.path.join(manager_service.manager.review_queue_dir, request_id)
        if not os.path.isdir(packet_dir):
            return jsonify({'error': 'Request not found'}), 404
        item = _format_packet_item(packet_dir, request_id)
        return jsonify({'success': True, 'item': item})

    @app.route('/api/flags', methods=['GET'])
    @require_admin
    def get_turtles_with_flags():
        """List turtles that have find_metadata (e.g. digital flag / collected to lab) for release page."""
        if not manager_service.manager_ready.wait(timeout=30):
            return jsonify({'error': 'TurtleManager is still initializing. Please try again in a moment.'}), 503
        if manager_service.manager is None:
            return jsonify({'error': 'TurtleManager failed to initialize'}), 500
        try:
            items = manager_service.manager.get_turtles_with_flags()
            return jsonify({'success': True, 'items': items})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/flags/release', methods=['POST'])
    @require_admin
    def clear_release_flag():
        """Mark turtle as released back to nature: clear digital flag, set released_at (Admin only)."""
        if not manager_service.manager_ready.wait(timeout=5):
            return jsonify({'error': 'TurtleManager is still initializing'}), 503
        if manager_service.manager is None:
            return jsonify({'error': 'TurtleManager not available'}), 500
        data = request.json or {}
        turtle_id = (data.get('turtle_id') or '').strip()
        location = (data.get('location') or '').strip() or None
        if not turtle_id:
            return jsonify({'error': 'turtle_id required'}), 400
        success, err = manager_service.manager.clear_release_flag(turtle_id, location)
        if not success:
            return jsonify({'error': err or 'Failed to clear release flag'}), 400
        return jsonify({'success': True})

    @app.route('/api/review/<request_id>', methods=['DELETE'])
    @require_admin
    def delete_review(request_id):
        """
        Delete a review queue item without processing (Admin only).
        Use for junk/spam. Requires confirmation in the frontend.
        """
        if not manager_service.manager_ready.wait(timeout=30):
            return jsonify({'error': 'TurtleManager is still initializing. Please try again in a moment.'}), 503
        if manager_service.manager is None:
            return jsonify({'error': 'TurtleManager failed to initialize'}), 500
        try:
            success, message = manager_service.manager.reject_review_packet(request_id)
            if success:
                return jsonify({'success': True, 'message': message})
            return jsonify({'error': message}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/review/<request_id>/approve', methods=['POST'])
    @require_admin
    def approve_review(request_id):
        """
        Approve a review queue item (Admin only)
        Admin selects which of the 5 matches is the correct one, OR creates a new turtle
        """
        # Wait for manager to be ready
        if not manager_service.manager_ready.wait(timeout=30):
            return jsonify({'error': 'TurtleManager is still initializing. Please try again in a moment.'}), 503
        if manager_service.manager is None:
            return jsonify({'error': 'TurtleManager failed to initialize'}), 500

        data = request.json or {}
        match_turtle_id = data.get('match_turtle_id')  # The turtle ID that was selected
        new_location = data.get('new_location')  # Optional: if creating new turtle (format: "State/Location")
        new_turtle_id = data.get('new_turtle_id')  # Optional: Turtle ID for new turtle (e.g., "T101")
        uploaded_image_path = data.get('uploaded_image_path')  # Optional: direct path for admin uploads
        sheets_data = data.get('sheets_data')  # Optional: Google Sheets data to create/update
        find_metadata = data.get('find_metadata')  # Optional: microhabitat_uploaded, physical_flag, digital_flag_*, etc.

        try:
            success, message = manager_service.manager.approve_review_packet(
                request_id,
                match_turtle_id=match_turtle_id,
                new_location=new_location,
                new_turtle_id=new_turtle_id,
                uploaded_image_path=uploaded_image_path,
                find_metadata=find_metadata
            )

            if success:
                # Ensure Google Sheets consistency: Create/update Sheets entry for this turtle
                service = get_sheets_service()
                if service:
                    try:
                        if new_location and new_turtle_id:
                            # New turtle created - create Sheets entry
                            # new_location is the sheet name (backend path); row content uses sheets_data
                            sheet_name = (isinstance(sheets_data, dict) and sheets_data.get('sheet_name')) or new_location
                            state = (isinstance(sheets_data, dict) and sheets_data.get('general_location')) or ''
                            location = (isinstance(sheets_data, dict) and sheets_data.get('location')) or ''

                            # Check if frontend already created the entry (indicated by primary_id and sheet_name in sheets_data)
                            # IMPORTANT: Only skip if primary_id is present - if createTurtleSheetsData failed,
                            # primary_id won't be set, and we should create it in fallback mode
                            if isinstance(sheets_data, dict) and sheets_data.get('primary_id') and sheets_data.get('sheet_name'):
                                # Frontend already created the entry via createTurtleSheetsData
                                # Skip creation here to avoid duplicates
                                primary_id = sheets_data.get('primary_id')
                                print(f"✅ Google Sheets entry already created by frontend for new turtle {new_turtle_id} with Primary ID {primary_id}")
                                print(f"   Frontend data fields: {list(sheets_data.keys())}")
                            elif isinstance(sheets_data, dict) and sheets_data.get('sheet_name') and not sheets_data.get('primary_id'):
                                # Frontend tried to create but failed (no primary_id means createTurtleSheetsData failed)
                                # Create it in fallback mode with all the form data
                                print(f"⚠️ Frontend createTurtleSheetsData failed (no primary_id in sheets_data), creating in fallback mode")
                            else:
                                # Fallback: create Sheets entry if frontend didn't (for backwards compatibility)

                                # Use primary_id from sheets_data if provided, otherwise generate new one
                                if isinstance(sheets_data, dict) and sheets_data.get('primary_id'):
                                    primary_id = sheets_data.get('primary_id')
                                else:
                                    primary_id = service.generate_primary_id(state, location)

                                # Create Sheets entry with ALL data from sheets_data (preserve user input)
                                turtle_data = sheets_data.copy() if isinstance(sheets_data, dict) else {}
                                # Remove sheet_name from turtle_data (it's metadata, not data)
                                turtle_data.pop('sheet_name', None)

                                # Set primary_id in the Primary ID column (globally unique)
                                turtle_data['primary_id'] = primary_id
                                # Determine sheet_name from the turtle data or use a default
                                sheet_name = sheets_data.get('sheet_name') if isinstance(sheets_data, dict) else 'Location A'
                                # Auto-generate biology ID (ID column) from sex if not present (scoped to this sheet)
                                if not turtle_data.get('id'):
                                    sex = (turtle_data.get('sex') or '').strip().upper()
                                    gender = sex if sex in ('M', 'F', 'J') else 'U'
                                    turtle_data['id'] = service.generate_biology_id(gender, sheet_name)
                                # Do not set general_location or location from state/location – leave empty if admin did not fill them; community location is for display only

                                service.create_turtle_data(turtle_data, sheet_name, state, location)
                                print(f"✅ Created Google Sheets entry for new turtle {new_turtle_id} with Primary ID {primary_id} (fallback)")
                        elif match_turtle_id:
                            pass
                    except Exception as sheets_error:
                        # Log but don't fail - Sheets is optional but should be created
                        print(f"⚠️ Warning: Failed to create Google Sheets entry: {sheets_error}")

                return jsonify({
                    'success': True,
                    'message': message
                })
            else:
                return jsonify({'error': message}), 400

        except Exception as e:
            error_trace = traceback.format_exc()
            try:
                print(f"❌ Error approving review: {str(e)}")
            except UnicodeEncodeError:
                print(f"[ERROR] Error approving review: {str(e)}")
            print(f"Traceback:\n{error_trace}")
            return jsonify({'error': f'Failed to approve review: {str(e)}'}), 500