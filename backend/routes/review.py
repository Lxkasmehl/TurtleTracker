"""
Review queue endpoints
"""

import os
import json
import traceback
from flask import request, jsonify
from auth import require_admin
from services import manager_service
from services.manager_service import get_sheets_service


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
                                # Keep user-provided 'id' if present, otherwise use primary_id as fallback
                                if 'id' not in turtle_data or not turtle_data.get('id'):
                                    turtle_data['id'] = primary_id
                                # Do not set general_location or location from state/location – leave empty if admin did not fill them; community location is for display only
                                
                                # sheet_name already set above (sheet tab name)
                                service.create_turtle_data(turtle_data, sheet_name, state, location)
                                print(f"✅ Created Google Sheets entry for new turtle {new_turtle_id} with Primary ID {primary_id} (fallback)")
                        elif match_turtle_id:
                            # Existing turtle - ensure Sheets entry exists
                            # Try to find location from turtle folder structure
                            # For now, we'll handle this in the frontend when Sheets data is saved
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
