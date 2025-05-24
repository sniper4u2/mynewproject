import logging
from typing import Dict, Optional, List
import pymongo
from datetime import datetime
import requests
from dataclasses import dataclass
import asyncio

logger = logging.getLogger('C2Server')

@dataclass
class MccMncEntry:
    mcc: str
    mnc: str
    country: str
    operator: str
    technologies: List[str]
    last_updated: datetime

class MccMncDatabase:
    def __init__(self, db_client):
        self.db = db_client
        self.cache: Dict[str, MccMncEntry] = {}
        self.cache_ttl = 3600  # 1 hour
        self.online_sources = [
            'https://raw.githubusercontent.com/mcc-mnc/mcc-mnc/master/mcc-mnc.json',
            'https://mcc-mnc.com/api/v1/mcc-mnc'
        ]
        
        # Initialize database collection
        self.collection = self.db.mcc_mnc
        
        # Create indexes
        self._create_indexes()
        
        # Load initial data
        asyncio.create_task(self._load_initial_data())

    def _create_indexes(self):
        """Create necessary database indexes"""
        try:
            self.collection.create_index([('mcc', pymongo.ASCENDING)])
            self.collection.create_index([('mcc', pymongo.ASCENDING), ('mnc', pymongo.ASCENDING)])
            self.collection.create_index([('country', pymongo.ASCENDING)])
            self.collection.create_index([('operator', pymongo.ASCENDING)])
            self.collection.create_index([('last_updated', pymongo.DESCENDING)])
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")

    async def _load_initial_data(self):
        """Load initial data from online sources"""
        try:
            for source in self.online_sources:
                try:
                    response = requests.get(source, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        await self._update_database(data)
                        break
                except Exception as e:
                    logger.warning(f"Failed to load from {source}: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading initial data: {str(e)}")

    async def _update_database(self, data: Dict):
        """Update database with new MCC-MNC data"""
        try:
            bulk_operations = []
            for entry in data:
                mcc = str(entry['mcc'])
                mnc = str(entry['mnc'])
                
                # Create update operation
                bulk_operations.append(pymongo.UpdateOne(
                    {'mcc': mcc, 'mnc': mnc},
                    {
                        '$set': {
                            'mcc': mcc,
                            'mnc': mnc,
                            'country': entry.get('country', ''),
                            'operator': entry.get('operator', ''),
                            'technologies': entry.get('technologies', []),
                            'last_updated': datetime.utcnow()
                        }
                    },
                    upsert=True
                ))
            
            if bulk_operations:
                result = await self.collection.bulk_write(bulk_operations)
                logger.info(f"Updated {result.modified_count} MCC-MNC entries")
        except Exception as e:
            logger.error(f"Error updating database: {str(e)}")

    async def get_operator_info(self, mcc: str, mnc: str) -> Optional[MccMncEntry]:
        """Get operator information for given MCC and MNC"""
        # Check cache first
        cache_key = f"{mcc}-{mnc}"
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if (datetime.utcnow() - entry.last_updated).total_seconds() < self.cache_ttl:
                return entry

        try:
            # Query database
            result = await self.collection.find_one(
                {'mcc': mcc, 'mnc': mnc},
                {'_id': False}
            )
            
            if result:
                entry = MccMncEntry(**result)
                self.cache[cache_key] = entry
                return entry
            
            return None
        except Exception as e:
            logger.error(f"Error getting operator info: {str(e)}")
            return None

    async def get_country_operators(self, country: str) -> List[MccMncEntry]:
        """Get all operators in a country"""
        try:
            results = await self.collection.find(
                {'country': country},
                {'_id': False}
            ).to_list(None)
            
            return [MccMncEntry(**entry) for entry in results]
        except Exception as e:
            logger.error(f"Error getting country operators: {str(e)}")
            return []

    async def get_technologies(self, mcc: str, mnc: str) -> List[str]:
        """Get supported technologies for an operator"""
        entry = await self.get_operator_info(mcc, mnc)
        return entry.technologies if entry else []

    async def update_entry(self, mcc: str, mnc: str, data: Dict):
        """Update an MCC-MNC entry"""
        try:
            result = await self.collection.update_one(
                {'mcc': mcc, 'mnc': mnc},
                {
                    '$set': {
                        **data,
                        'last_updated': datetime.utcnow()
                    }
                },
                upsert=True
            )
            
            if result.modified_count > 0:
                # Clear cache
                cache_key = f"{mcc}-{mnc}"
                if cache_key in self.cache:
                    del self.cache[cache_key]
                
                logger.info(f"Updated entry for MCC {mcc} MNC {mnc}")
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating entry: {str(e)}")
            return False

    async def add_entry(self, mcc: str, mnc: str, data: Dict):
        """Add a new MCC-MNC entry"""
        try:
            result = await self.collection.insert_one({
                'mcc': mcc,
                'mnc': mnc,
                **data,
                'last_updated': datetime.utcnow()
            })
            
            # Clear cache
            cache_key = f"{mcc}-{mnc}"
            if cache_key in self.cache:
                del self.cache[cache_key]
            
            return result.inserted_id is not None
        except Exception as e:
            logger.error(f"Error adding entry: {str(e)}")
            return False

    async def delete_entry(self, mcc: str, mnc: str):
        """Delete an MCC-MNC entry"""
        try:
            result = await self.collection.delete_one({'mcc': mcc, 'mnc': mnc})
            
            # Clear cache
            cache_key = f"{mcc}-{mnc}"
            if cache_key in self.cache:
                del self.cache[cache_key]
            
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting entry: {str(e)}")
            return False

    async def refresh_database(self):
        """Refresh the entire database from online sources"""
        try:
            # Clear cache
            self.cache = {}
            
            # Clear database
            result = await self.collection.delete_many({})
            if result.deleted_count > 0:
                logger.info(f"Deleted {result.deleted_count} entries")
            
            # Load fresh data
            await self._load_initial_data()
            
            logger.info("Database refreshed successfully")
            return True
        except Exception as e:
            logger.error(f"Error refreshing database: {str(e)}")
            return False
