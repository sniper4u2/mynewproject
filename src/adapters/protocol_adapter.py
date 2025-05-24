import abc
import asyncio
import logging
from cryptography.fernet import Fernet
import json
from datetime import datetime
import pymongo
import ssl
import random
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('protocol_adapter.log'),
        logging.StreamHandler()
    ]
)

class ProtocolAdapter(abc.ABC):
    """Base class for all protocol adapters"""
    
    def __init__(self, db_client: pymongo.MongoClient, encryption_key: bytes, config: Dict[str, Any]):
        self.db = db_client
        self.fernet = Fernet(encryption_key)
        self.config = config
        self.active_connections = {}
        self.heartbeat_interval = config.get('heartbeat_interval', 30)
        self.retry_delays = [1, 2, 4, 8, 16, 32]  # Exponential backoff
        self.current_retry = 0
        
    @abc.abstractmethod
    async def connect(self, device_id: str, connection_info: Dict[str, Any]) -> bool:
        """Establish a connection to the device
        
        Args:
            device_id: Unique identifier for the device
            connection_info: Dictionary containing connection parameters
            
        Returns:
            bool: True if connection was successful, False otherwise
            
        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abc.abstractmethod
    async def disconnect(self, device_id: str) -> bool:
        """Disconnect from the device
        
        Args:
            device_id: Unique identifier for the device
            
        Returns:
            bool: True if disconnection was successful, False otherwise
        """
        pass

    @abc.abstractmethod
    async def send(self, device_id: str, data: bytes) -> bool:
        """Send data to the device
        
        Args:
            device_id: Unique identifier for the device
            data: Data to send
            
        Returns:
            bool: True if send was successful, False otherwise
        """
        pass

    @abc.abstractmethod
    async def receive(self, device_id: str) -> bytes:
        """Receive data from the device
        
        Args:
            device_id: Unique identifier for the device
            
        Returns:
            bytes: Received data
            
        Raises:
            ConnectionError: If no data is available
        """
        pass

    async def handle_heartbeat(self, device_id: str):
        """Handle connection heartbeat"""
        while True:
            try:
                if device_id in self.active_connections:
                    await self.send(device_id, b'HEARTBEAT')
                    await asyncio.sleep(self.heartbeat_interval)
                else:
                    break
            except Exception as e:
                logging.error(f"Heartbeat error for {device_id}: {str(e)}")
                break

    def get_retry_delay(self):
        """Get current retry delay with exponential backoff"""
        delay = self.retry_delays[self.current_retry % len(self.retry_delays)]
        self.current_retry += 1
        return delay

class ProtocolAdapterManager:
    """Manager for protocol adapters"""
    
    def __init__(self, db_client: pymongo.MongoClient, encryption_key: bytes, config: Dict[str, Any]):
        self.adapters = {}
        self.db = db_client
        self.fernet = Fernet(encryption_key)
        self.config = config
        
    def register_adapter(self, protocol: str, adapter_class):
        """Register a new protocol adapter"""
        if protocol not in self.adapters:
            self.adapters[protocol] = adapter_class(self.db, self.fernet, self.config)
            logging.info(f"Registered adapter for protocol: {protocol}")
        else:
            logging.warning(f"Adapter for protocol {protocol} already registered")
            
    def get_adapter(self, protocol: str):
        """Get adapter for a specific protocol"""
        return self.adapters.get(protocol)
        
    async def initialize_all_adapters(self):
        """Initialize all registered adapters"""
        for protocol, adapter in self.adapters.items():
            try:
                await adapter.initialize()
                logging.info(f"Successfully initialized adapter for protocol: {protocol}")
            except Exception as e:
                logging.error(f"Failed to initialize adapter for protocol {protocol}: {str(e)}")
                
    async def shutdown_all_adapters(self):
        """Shutdown all registered adapters"""
        for protocol, adapter in self.adapters.items():
            try:
                await adapter.shutdown()
                logging.info(f"Successfully shutdown adapter for protocol: {protocol}")
            except Exception as e:
                logging.error(f"Failed to shutdown adapter for protocol {protocol}: {str(e)}")

    async def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using Fernet"""
        try:
            return self.fernet.encrypt(data)
        except Exception as e:
            logging.error(f"Encryption error: {str(e)}")
            return None
            
    async def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using Fernet"""
        try:
            return self.fernet.decrypt(encrypted_data)
        except Exception as e:
            logging.error(f"Decryption error: {str(e)}")
            return None
            
    async def handle_heartbeat(self, device_id: str) -> bool:
        """Handle connection heartbeats"""
        try:
            if device_id in self.active_connections:
                await self.send(device_id, b'HEARTBEAT')
                response = await self.receive(device_id)
                if response == b'HEARTBEAT_ACK':
                    return True
            return False
        except Exception as e:
            logging.error(f"Heartbeat error for {device_id}: {str(e)}")
            return False
            
    async def handle_reconnection(self, device_id: str) -> bool:
        """Handle connection retries with exponential backoff"""
        try:
            if self.current_retry < len(self.retry_delays):
                await asyncio.sleep(self.retry_delays[self.current_retry])
                success = await self.connect(device_id, self.active_connections[device_id])
                if success:
                    self.current_retry = 0
                    return True
                self.current_retry += 1
            return False
        except Exception as e:
            logging.error(f"Reconnection error for {device_id}: {str(e)}")
            return False
            
    async def switch_protocol(self, device_id: str, new_protocol: str) -> bool:
        """Switch to a different protocol"""
        try:
            # Disconnect current protocol
            await self.disconnect(device_id)
            
            # Initialize new protocol
            protocol_class = PROTOCOL_CLASSES.get(new_protocol)
            if protocol_class:
                new_adapter = protocol_class(self.db, self.fernet, self.config)
                success = await new_adapter.connect(device_id, self.active_connections[device_id])
                if success:
                    self.active_connections[device_id]['protocol'] = new_protocol
                    return True
            return False
        except Exception as e:
            logging.error(f"Protocol switch error for {device_id}: {str(e)}")
            return False
            
    def get_protocol_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections"""
        stats = {
            'total_connections': len(self.active_connections),
            'active_protocols': {},
            'last_heartbeat': {}
        }
        
        for device_id, conn in self.active_connections.items():
            protocol = conn.get('protocol', 'unknown')
            stats['active_protocols'][protocol] = stats['active_protocols'].get(protocol, 0) + 1
            stats['last_heartbeat'][device_id] = conn.get('last_heartbeat', 'never')
            
        return stats

# Protocol adapter classes will be registered here
PROTOCOL_CLASSES: Dict[str, type] = {}
