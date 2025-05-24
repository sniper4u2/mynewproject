from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.handlers.gsm_ss7_handler import GsmSs7Handler
from src.core.auth import requires_role

api_bp = Blueprint('api', __name__)

def init_api_routes(app, db, encryption_key, adapter_manager):
    # Initialize handlers
    gsm_handler = GsmSs7Handler(db, encryption_key)

    # GSM/SS7 API routes
    @api_bp.route('/api/gsm/monitor/start', methods=['POST'])
    @jwt_required()
    @requires_role('admin')
    def start_gsm_monitor():
        try:
            result = gsm_handler.start_monitor()
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @api_bp.route('/api/gsm/monitor/stop', methods=['POST'])
    @jwt_required()
    @requires_role('admin')
    def stop_gsm_monitor():
        try:
            result = gsm_handler.stop_monitor()
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Register the blueprint
    app.register_blueprint(api_bp)
