"""
Turtle data endpoints (e.g. list images for a turtle folder)
"""

import os
import json
from flask import request, jsonify
from auth import require_admin
from services import manager_service


def register_turtle_routes(app):
    """Register turtle-related routes"""

    @app.route('/api/turtles/images', methods=['GET'])
    @require_admin
    def get_turtle_images():
        """
        Get image paths for a turtle: primary (ref_data), additional (microhabitat/condition), loose.
        Query: turtle_id (required), sheet_name (optional, for disambiguation).
        Returns: { primary: path | null, additional: [ { path, type } ], loose: [ path ] }
        """
        if not manager_service.manager_ready.wait(timeout=5):
            return jsonify({'error': 'TurtleManager is still initializing'}), 503
        if manager_service.manager is None:
            return jsonify({'error': 'TurtleManager not available'}), 500

        turtle_id = (request.args.get('turtle_id') or '').strip()
        sheet_name = (request.args.get('sheet_name') or '').strip() or None
        if not turtle_id:
            return jsonify({'error': 'turtle_id required'}), 400

        manager = manager_service.manager
        location_hint = sheet_name
        turtle_dir = manager._get_turtle_folder(turtle_id, location_hint)
        if not turtle_dir or not os.path.isdir(turtle_dir):
            return jsonify({
                'primary': None,
                'additional': [],
                'loose': [],
            })

        primary_path = None
        ref_dir = os.path.join(turtle_dir, 'ref_data')
        if os.path.isdir(ref_dir):
            for f in sorted(os.listdir(ref_dir)):
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    primary_path = os.path.join(ref_dir, f)
                    break

        additional = []
        additional_dir = os.path.join(turtle_dir, 'additional_images')
        if os.path.isdir(additional_dir):
            manifest_path = os.path.join(additional_dir, 'manifest.json')
            if os.path.isfile(manifest_path):
                try:
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                    for entry in manifest:
                        fn = entry.get('filename')
                        kind = entry.get('type', 'other')
                        if fn:
                            p = os.path.join(additional_dir, fn)
                            if os.path.isfile(p):
                                additional.append({
                                    'path': p,
                                    'type': kind,
                                    'timestamp': entry.get('timestamp'),
                                    'uploaded_by': entry.get('uploaded_by'),
                                })
                except (json.JSONDecodeError, OSError):
                    pass
            # Fallback: list images in folder if no manifest
            if not additional:
                for f in sorted(os.listdir(additional_dir)):
                    if f != 'manifest.json' and f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                        additional.append({
                            'path': os.path.join(additional_dir, f),
                            'type': 'other',
                            'timestamp': None,
                            'uploaded_by': None,
                        })

        loose = []
        loose_dir = os.path.join(turtle_dir, 'loose_images')
        if os.path.isdir(loose_dir):
            for f in sorted(os.listdir(loose_dir)):
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    loose.append(os.path.join(loose_dir, f))

        return jsonify({
            'primary': primary_path,
            'additional': additional,
            'loose': loose,
        })

    @app.route('/api/turtles/images/additional', methods=['DELETE'])
    @require_admin
    def delete_turtle_additional_image():
        """
        Delete one additional image from a turtle's folder (Admin only).
        Query: turtle_id (required), filename (required), sheet_name (optional).
        """
        if not manager_service.manager_ready.wait(timeout=5):
            return jsonify({'error': 'TurtleManager is still initializing'}), 503
        if manager_service.manager is None:
            return jsonify({'error': 'TurtleManager not available'}), 500
        turtle_id = (request.args.get('turtle_id') or '').strip()
        filename = (request.args.get('filename') or '').strip()
        sheet_name = (request.args.get('sheet_name') or '').strip() or None
        if not turtle_id:
            return jsonify({'error': 'turtle_id required'}), 400
        if not filename:
            return jsonify({'error': 'filename required'}), 400
        success, err = manager_service.manager.remove_additional_image_from_turtle(
            turtle_id, filename, sheet_name
        )
        if not success:
            return jsonify({'error': err or 'Failed to delete image'}), 400
        return jsonify({'success': True})
