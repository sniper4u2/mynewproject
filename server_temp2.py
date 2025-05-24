import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from src.databases.init_db import init_db
from src.adapters.protocol_adapter import ProtocolAdapterManager
from pymongo import MongoClient
import aiozmq
import yaml
from src.utils.rate_limiter import RateLimiter
from pathlib import Path

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/c2_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('C2Server')

# Load configuration
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize Flask app
app = Flask(__name__)
app.template_folder = str(Path('/home/b13/Desktop/mynewproject/templates').resolve())
CORS(app)  # Enable CORS for API endpoints

# Configure JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = config['security']['jwt']['token_expires']
app.config['JWT_COOKIE_NAME'] = 'jwt-token'
jwt = JWTManager(app)

# Root route
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

# Dashboard route
@app.route('/dashboard')
def dashboard():
    # Get stats from MongoDB
    stats = {
        'total_agents': db.agents.count_documents({}),
        'active_agents': db.agents.count_documents({'status': 'active'}),
        'mobile_sessions': db.mobile_sessions.count_documents({}),
        'total_commands': db.commands.count_documents({})
    }
    
    # Get recent activity (last 10 activities)
    recent_activity = list(db.activity.find().sort('timestamp', -1).limit(10))
    
    return render_template('dashboard.html', stats=stats, recent_activity=recent_activity)

# Agents route
@app.route('/agents')
def agents():
    return render_template('agents.html')

# Connections route
@app.route('/connections')
def connections():
    return render_template('connections.html')

# OSINT route
@app.route('/osint')
def osint():
    return render_template('osint.html')

# Mobile route
@app.route('/mobile')
def mobile():
    return render_template('mobile.html')

# Monitoring route
@app.route('/monitoring')
def monitoring():
    return render_template('monitoring.html')

# Settings route
@app.route('/settings')
def settings():
    return render_template('settings.html')

# Initialize MongoDB client
try:
    client = MongoClient(
        config['database']['uri'],
        serverSelectionTimeoutMS=5000
    )
    db = client[config['database']['name']]
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    sys.exit(1)

# Initialize encryption
try:
    with open('encryption.key', 'r') as f:
        encryption_key = f.read().strip()
        fernet = Fernet(encryption_key.encode())
except Exception as e:
    print(f"Error reading encryption key: {e}")
    print("Generating new encryption key...")
    encryption_key = Fernet.generate_key()
    with open('encryption.key', 'w') as f:
        f.write(encryption_key.decode())
    fernet = Fernet(encryption_key)

# Initialize rate limiter
api_rate_limiter = RateLimiter(
    calls_per_minute=config['security']['api_rate_limit']['calls_per_minute'],
    max_attempts=config['security']['api_rate_limit']['max_attempts'],
    backoff_factor=config['security']['api_rate_limit']['backoff_factor'],
    max_delay=config['security']['api_rate_limit']['max_delay']
)

# Initialize protocol adapters
from src.adapters.protocol_adapter import ProtocolAdapterManager
adapter_manager = ProtocolAdapterManager(db, encryption_key, config)

# Initialize handlers
from src.handlers.gsm_ss7_handler import GsmSs7Handler
from src.handlers.osint_handler import OSINTHandler
gsm_handler = GsmSs7Handler(db, encryption_key)
osint_handler = OSINTHandler(db, encryption_key)

# Initialize web interface routes
from src.web.routes import init_web_routes
osint_bp, gsm_bp = init_web_routes(app, db, encryption_key)

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Add your authentication logic here
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Add your logout logic here
    return redirect(url_for('login'))

# Initialize API routes
from src.api.routes import init_api_routes
init_api_routes(app, db, encryption_key, adapter_manager)

if __name__ == '__main__':
    app.run(
        host=config['server']['host'],
        port=config['server']['port'],
        debug=config['server']['debug']
    )
