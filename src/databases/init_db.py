import os
import pymongo
from cryptography.fernet import Fernet
import yaml
from dotenv import load_dotenv
from datetime import datetime
import bcrypt
import aiozmq

# Load environment variables
load_dotenv()

# Load configuration
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize MongoDB client
client = pymongo.MongoClient(
    config['database']['uri'],
    serverSelectionTimeoutMS=5000
)

db = client[config['database']['name']]

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

# Create collections and indexes
collections = {
    'agents': {
        'indexes': [
            {'key': [('agent_id', 1)], 'unique': True},
            {'key': [('last_seen', -1)]}
        ]
    },
    'mobile_sessions': {
        'indexes': [
            {'key': [('session_id', 1)], 'unique': True},
            {'key': [('device_id', 1), ('timestamp', -1)]}
        ]
    },
    'commands': {
        'indexes': [
            {'key': [('command_id', 1)], 'unique': True},
            {'key': [('status', 1), ('timestamp', -1)]}
        ]
    },
    'users': {
        'indexes': [
            {'key': [('username', 1)], 'unique': True},
            {'key': [('email', 1)], 'unique': True}
        ]
    }
}

# Create collections and indexes
for collection_name, config in collections.items():
    if collection_name not in db.list_collection_names():
        print(f"Creating collection: {collection_name}")
        db.create_collection(collection_name)
        
        # Create indexes
        for index_config in config['indexes']:
            db[collection_name].create_index(
                index_config['key'],
                unique=index_config.get('unique', False)
            )

# Create default user
users = db['users']
if users.count_documents({}) == 0:
    print("Creating default user...")
    default_user = {
        'username': 'spaypeur',
        'password': bcrypt.hashpw('31101986'.encode(), bcrypt.gensalt()),
        'email': 'spaypeur@example.com',
        'role': 'admin',
        'created_at': datetime.utcnow(),
        'last_login': None
    }
    users.insert_one(default_user)
    print("Default user created successfully")

def init_db():
    """Initialize the database with required collections and default user"""
    # Initialize collections
    collections = ['agents', 'mobile_sessions', 'commands', 'users']
    
    for collection in collections:
        if collection not in db.list_collection_names():
            print(f"Creating collection: {collection}")
            db.create_collection(collection)
    
    # Create default user if none exists
    users = db['users']
    if users.count_documents({}) == 0:
        print("Creating default user...")
        default_user = {
            'username': 'spaypeur',
            'password': bcrypt.hashpw('31101986'.encode(), bcrypt.gensalt()),
            'email': 'spaypeur@example.com',
            'role': 'admin',
            'created_at': datetime.utcnow(),
            'last_login': None
        }
        users.insert_one(default_user)
        print("Default user created successfully")
    
    print("Database initialization complete")

if __name__ == '__main__':
    init_db()
