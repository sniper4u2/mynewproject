import os
import sys
import json
import bcrypt
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def initialize_database():
    try:
        # Connect to MongoDB
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client[os.getenv('MONGODB_NAME')]
        
        # Create indexes
        db.users.create_index([('username', 1)], unique=True)
        db.users.create_index([('email', 1)], unique=True)
        db.users.create_index([('roles', 1)])
        
        # Create default admin user
        admin_user = {
            'username': 'admin',
            'password': bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt()),
            'email': 'admin@example.com',
            'roles': ['admin'],
            'created_at': datetime.utcnow(),
            'last_login': None,
            'active': True
        }
        
        # Insert admin user if it doesn't exist
        if not db.users.find_one({'username': 'admin'}):
            db.users.insert_one(admin_user)
            print("Admin user created successfully!")
        else:
            print("Admin user already exists!")
        
        # Create default settings
        settings = {
            'server': {
                'version': '1.0.0',
                'status': 'running',
                'last_update': datetime.utcnow()
            },
            'security': {
                'jwt_secret': os.getenv('JWT_SECRET'),
                'encryption_key': os.getenv('ENCRYPTION_KEY'),
                'password_salt_rounds': 12
            },
            'api': {
                'rate_limit': {
                    'calls_per_minute': 100,
                    'max_attempts': 3,
                    'backoff_factor': 1,
                    'max_delay': 30
                }
            },
            'cache': {
                'ttl_seconds': 3600,
                'max_entries': 1000
            }
        }
        
        # Insert settings if they don't exist
        if not db.settings.find_one({'_id': 'default'}):
            db.settings.insert_one({'_id': 'default', **settings})
            print("Default settings created successfully!")
        else:
            print("Default settings already exist!")
        
        print("Database initialization completed successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        sys.exit(1)
    # Connect to MongoDB
    client = MongoClient(config['database']['uri'])
    db = client[config['database']['name']]
    
    # Create admin user
    create_admin_user(db, password)
    
    # Create default settings
    create_default_settings(db)
    
    print("Database initialization completed successfully!")

if __name__ == '__main__':
    main()
