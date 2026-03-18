"""
General location catalog endpoints.
"""

from flask import jsonify, request

from auth import require_admin
from general_locations_catalog import add_general_location, get_general_location_catalog
from services.manager_service import get_sheets_service
from sheets import sheet_management


def _serialize_catalog(catalog):
    states = [
        {'state': state, 'locations': locations}
        for state, locations in catalog.get('states', {}).items()
    ]
    sheet_defaults = [
        {'sheet_name': sheet_name, **rule}
        for sheet_name, rule in catalog.get('sheet_defaults', {}).items()
    ]
    return {
        'catalog': catalog,
        'states': states,
        'sheet_defaults': sheet_defaults,
    }


def register_general_location_routes(app):
    """Register general location catalog endpoints."""

    @app.route('/api/general-locations', methods=['GET', 'POST'])
    @require_admin
    def general_locations():
        if request.method == 'GET':
            catalog = get_general_location_catalog()
            return jsonify({'success': True, **_serialize_catalog(catalog)})

        data = request.get_json(silent=True) or {}
        state = (data.get('state') or '').strip()
        general_location = (data.get('general_location') or '').strip()
        if not state:
            return jsonify({'success': False, 'error': 'state is required'}), 400
        if not general_location:
            return jsonify({'success': False, 'error': 'general_location is required'}), 400

        try:
            catalog = add_general_location(state, general_location)
        except ValueError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400

        synced = False
        sync_error = None
        try:
            service = get_sheets_service()
            if service:
                sheet_management.sync_general_location_validations(service)
                synced = True
        except Exception as exc:  # pragma: no cover - best effort sync
            sync_error = str(exc)

        response = {'success': True, **_serialize_catalog(catalog), 'synced': synced}
        if sync_error:
            response['sync_error'] = sync_error
        return jsonify(response)

