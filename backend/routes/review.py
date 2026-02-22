"""
Review queue endpoints
"""

import os
import json
import traceback
from flask import request, jsonify
from auth import require_admin
from services import manager_service
from services.manager_service import get_sheets_service, get_community_sheets_service

# Metadata keys to strip when syncing turtle data to community spreadsheet
_COMMUNITY_SYNC_STRIP_KEYS = ('sheet_name', 'row_index')


def _sync_confirmed_to_community(data, sheets_data, service, new_location, new_turtle_id, match_turtle_id):
    """
    After a successful approval, push the confirmed turtle record to the community-facing
    spreadsheet. Community uploads always sync here (required; separate from research).
    Raises if community spreadsheet is not configured or sync fails.
    """
    comm = get_community_sheets_service()
    if not comm:
        raise RuntimeError(
            "Community spreadsheet is required for confirmations. "
            "Set GOOGLE_SHEETS_COMMUNITY_SPREADSHEET_ID in backend .env and share the sheet with the service account."
        )
    if not isinstance(data, dict):
        data = {}
    if not isinstance(sheets_data, dict):
        sheets_data = {}
    primary_id = data.get('primary_id') or sheets_data.get('primary_id')
    raw_sheet = (data.get('sheet_name') or sheets_data.get('sheet_name') or new_location or '').strip()
    # Community sheet tab = first path segment (State); new_location can be "State/Location"
    sheet_name = raw_sheet.split("/")[0].strip() if raw_sheet else ''
    if not primary_id or not sheet_name:
        raise ValueError("Cannot sync to community spreadsheet: missing primary_id or sheet_name")
    # Resolve full turtle data: for new turtle use sheets_data; for match read from research
    turtle_data = None
    if new_location and new_turtle_id and sheets_data:
        turtle_data = dict(sheets_data)
    elif match_turtle_id and service:
        turtle_data = service.get_turtle_data(primary_id, sheet_name)
    if not turtle_data:
        raise ValueError("Cannot sync to community spreadsheet: could not resolve turtle data")
    for key in _COMMUNITY_SYNC_STRIP_KEYS:
        turtle_data.pop(key, None)
    turtle_data['primary_id'] = primary_id
    # For new turtles, ensure primary_id and biology ID exist (community sheet only)
    if new_location and new_turtle_id:
        if not turtle_data.get('primary_id'):
            raise ValueError("Cannot sync to community spreadsheet: missing primary_id for new turtle")
        if not turtle_data.get('id'):
            sex = (turtle_data.get('sex') or '').strip().upper()
            gender = sex if sex in ('M', 'F', 'J') else 'U'
            turtle_data['id'] = comm.generate_biology_id(gender, sheet_name)
    comm.create_sheet_with_headers(sheet_name)
    existing_row = comm.get_turtle_data(primary_id, sheet_name)
    state = turtle_data.get('general_location') or ''
    location = turtle_data.get('location') or ''
    if existing_row:
        comm.update_turtle_data(primary_id, turtle_data, sheet_name, state, location)
        print(f"✅ Community spreadsheet: updated turtle {primary_id} on sheet '{sheet_name}'")
    else:
        comm.create_turtle_data(turtle_data, sheet_name, state, location)
        print(f"✅ Community spreadsheet: added turtle {primary_id} to sheet '{sheet_name}'")


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
        
        data = request.json
        match_turtle_id = data.get('match_turtle_id')  # The turtle ID that was selected
        new_location = data.get('new_location')  # Optional: if creating new turtle (format: "State/Location")
        new_turtle_id = data.get('new_turtle_id')  # Optional: Turtle ID for new turtle (e.g., "T101")
        uploaded_image_path = data.get('uploaded_image_path')  # Optional: direct path for admin uploads
        sheets_data = data.get('sheets_data')  # Optional: Google Sheets data to create/update
        
        try:
            success, message = manager_service.manager.approve_review_packet(
                request_id,
                match_turtle_id=match_turtle_id,
                new_location=new_location,
                new_turtle_id=new_turtle_id,
                uploaded_image_path=uploaded_image_path
            )
            
            if success:
                # Admin uploads use request_id starting with "admin_"; only those go to research sheet.
                # Community uploads (review queue) go to community spreadsheet only (new turtles) or sync match from research.
                is_community_upload = not (request_id.startswith('admin_') if request_id else False)

                # Research spreadsheet: only update for *matches* (existing turtle). New turtles from
                # community uploads are created only in the community spreadsheet, not in research.
                service = get_sheets_service()
                if service and match_turtle_id:
                    try:
                        # Match to existing turtle: research sheet is updated by frontend before approve.
                        # No backend action needed here.
                        pass
                    except Exception as sheets_error:
                        print(f"⚠️ Warning: Research Sheets: {sheets_error}")

                # Sync to community spreadsheet only for community uploads (review queue).
                # Admin uploads (match or new turtle) use the research/admin sheet only; no community sync.
                if is_community_upload:
                    try:
                        _sync_confirmed_to_community(
                            data=data,
                            sheets_data=sheets_data,
                            service=get_sheets_service() if success else None,
                            new_location=new_location,
                            new_turtle_id=new_turtle_id,
                            match_turtle_id=match_turtle_id,
                        )
                    except (ValueError, RuntimeError) as sync_err:
                        return jsonify({'error': str(sync_err)}), 503
                    except Exception as sync_err:
                        print(f"⚠️ Community spreadsheet sync failed: {sync_err}")
                        return jsonify({
                            'error': f"Community spreadsheet sync failed: {sync_err}. Check GOOGLE_SHEETS_COMMUNITY_SPREADSHEET_ID and service account access."
                        }), 503

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
