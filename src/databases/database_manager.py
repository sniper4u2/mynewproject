import pymongo
from typing import Dict, Any, Optional
from datetime import datetime
from src.config.config_loader import config_loader

class DatabaseManager:
    def __init__(self):
        self.config = config_loader.get_section('database')
        self.client = None
        self.db = None
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Initialize MongoDB connection"""
        try:
            self.client = pymongo.MongoClient(
                self.config['uri'],
                serverSelectionTimeoutMS=self.config.get('connection_timeout', 5000)
            )
            self.db = self.client[self.config['name']]
            self.client.server_info()  # Test connection
            print("Database connection established successfully")
        except Exception as e:
            print(f"Failed to connect to database: {str(e)}")
            raise

    def get_collection(self, collection_name: str) -> pymongo.collection.Collection:
        """Get or create a collection with proper indexes"""
        if collection_name not in self.db.list_collection_names():
            self._create_collection(collection_name)
        return self.db[collection_name]

    def _create_collection(self, collection_name: str) -> None:
        """Create collection with appropriate indexes"""
        collection = self.db.create_collection(collection_name)
        
        # Common indexes
        indexes = [
            {'key': 'created_at', 'expireAfterSeconds': 2592000},  # 30 days
            {'key': 'updated_at'},
            {'key': 'status'}
        ]
        
        # Collection-specific indexes
        if collection_name == 'agents':
            indexes.extend([
                {'key': 'agent_id', 'unique': True},
                {'key': 'last_seen'}
            ])
        elif collection_name == 'sessions':
            indexes.extend([
                {'key': 'session_id', 'unique': True},
                {'key': 'device_id'},
                {'key': 'start_time'},
                {'key': 'end_time'}
            ])
        
        # Create indexes
        for index in indexes:
            if 'expireAfterSeconds' in index:
                collection.create_index(
                    [(index['key'], pymongo.ASCENDING)],
                    expireAfterSeconds=index['expireAfterSeconds']
                )
            else:
                collection.create_index(
                    [(index['key'], pymongo.ASCENDING)],
                    unique=index.get('unique', False)
                )

    def insert(self, collection_name: str, document: Dict[str, Any]) -> str:
        """Insert a document into a collection"""
        collection = self.get_collection(collection_name)
        document['created_at'] = datetime.utcnow()
        document['updated_at'] = datetime.utcnow()
        return str(collection.insert_one(document).inserted_id)

    def update(self, collection_name: str, filter: Dict[str, Any], update: Dict[str, Any]) -> int:
        """Update a document in a collection"""
        collection = self.get_collection(collection_name)
        update['$set'] = {'updated_at': datetime.utcnow()}
        return collection.update_one(filter, update).modified_count

    def find(self, collection_name: str, filter: Dict[str, Any], projection: Optional[Dict[str, Any]] = None) -> list:
        """Find documents in a collection"""
        collection = self.get_collection(collection_name)
        return list(collection.find(filter, projection))

    def delete(self, collection_name: str, filter: Dict[str, Any]) -> int:
        """Delete documents from a collection"""
        collection = self.get_collection(collection_name)
        return collection.delete_many(filter).deleted_count

    def close(self) -> None:
        """Close database connection"""
        if self.client:
            self.client.close()
