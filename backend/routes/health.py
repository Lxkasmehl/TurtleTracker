"""
Health check endpoints
"""

from flask import jsonify
from services.manager_service import manager


def register_health_routes(app):
    """Register health check routes"""
    
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
