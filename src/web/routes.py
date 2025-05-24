from flask import Blueprint, jsonify, request
from flask_login import login_required
from src.core.auth import requires_role
from src.handlers.osint_handler import OSINTHandler
from src.handlers.gsm_ss7_handler import GsmSs7Handler

def init_web_routes(app, db, encryption_key):
    # Create blueprints
    osint_bp = Blueprint('osint', __name__)
    gsm_bp = Blueprint('gsm', __name__)

    # Initialize handlers
    osint_handler = OSINTHandler(db, encryption_key)
    gsm_handler = GsmSs7Handler(db, encryption_key)

    # OSINT routes
    @osint_bp.route('/capture/start', methods=['POST'])
    @login_required
    @requires_role('admin')
    def start_capture():
        interface = request.json.get('interface')
        filter = request.json.get('filter')
        return osint_handler.start_capture(interface, filter)

    @osint_bp.route('/capture/stop', methods=['POST'])
    @login_required
    @requires_role('admin')
    def stop_capture():
        return osint_handler.stop_capture()

    @osint_bp.route('/captures', methods=['GET'])
    @login_required
    @requires_role('admin')
    def list_captures():
        return osint_handler.list_captures()

    # GSM/SS7 routes
    @gsm_bp.route('/monitor', methods=['POST'])
    @login_required
    @requires_role('admin')
    def start_gsm_monitor():
        return gsm_handler.start_monitor()

    @gsm_bp.route('/stop', methods=['POST'])
    @login_required
    @requires_role('admin')
    def stop_gsm_monitor():
        return gsm_handler.stop_monitor()

    # Register blueprints with API prefix
    app.register_blueprint(osint_bp, url_prefix="/api/osint")
    app.register_blueprint(gsm_bp, url_prefix="/api/gsm")

    return osint_bp, gsm_bp
