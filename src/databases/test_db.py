import pymongo
from datetime import datetime

# Test MongoDB connection
try:
    client = pymongo.MongoClient(
        "mongodb://paypeur:31101986@localhost:27017/paypeur",
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000,
        authSource="admin",
        authMechanism="SCRAM-SHA-256"
    )
    
    # Authenticate
    db = client["admin"]
    db.authenticate("paypeur", "31101986")
    
    # Switch to target database
    db = client["paypeur"]
    
    # Test connection
    db.command('ping')
    print("Successfully connected to MongoDB")
    
    # List collections
    print("Collections in database:", db.list_collection_names())
    
    # Try a simple query
    users = db["users"]
    count = users.count_documents({})
    print(f"Number of users: {count}")
    
except Exception as e:
    print(f"Error connecting to MongoDB: {str(e)}")
