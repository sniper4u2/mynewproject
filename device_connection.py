import asyncio
import aiohttp
import phonenumbers
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Device:
    device_id: str
    phone_number: Optional[str] = None
    ip_address: Optional[str] = None
    last_seen: datetime = datetime.now()
    status: str = "offline"
    platform: Optional[str] = None
    version: Optional[str] = None

class DeviceConnectionManager:
    def __init__(self):
        self.devices: Dict[str, Device] = {}
        self.logger = logging.getLogger(__name__)
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def initialize_device(self, device_id: str, 
                              phone_number: Optional[str] = None, 
                              ip_address: Optional[str] = None) -> Device:
        """Initialize a new device connection."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        if device_id in self.devices:
            raise ValueError(f"Device {device_id} already exists")

        device = Device(
            device_id=device_id,
            phone_number=phone_number,
            ip_address=ip_address
        )
        self.devices[device_id] = device
        return device

    async def connect_device(self, device_id: str) -> bool:
        """Connect to a device using its phone number or IP address."""
        if device_id not in self.devices:
            self.logger.error(f"Device {device_id} not found")
            return False

        device = self.devices[device_id]
        
        try:
            if device.phone_number:
                # TODO: Implement GSM connection
                self.logger.info(f"Connecting to device {device_id} via phone number")
                device.status = "connected"
                await self.db_manager.update_device_status(device_id, "connected")
            elif device.ip_address:
                # Test connection
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((device.ip_address, 22))  # Test SSH port
                sock.close()
                
                if result == 0:
                    device.status = "connected"
                    await self.db_manager.update_device_status(device_id, "connected")
                    self.logger.info(f"Device {device_id} connected via IP")
                else:
                    device.status = "offline"
                    await self.db_manager.update_device_status(device_id, "offline")
                    self.logger.error(f"Failed to connect to device {device_id} via IP")
            
            device.last_seen = datetime.now()
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to device {device_id}: {str(e)}")
            device.status = "offline"
            await self.db_manager.update_device_status(device_id, "offline")
            return False

    async def scan_network(self, subnet: str = "192.168.1.0/24") -> Dict[str, Device]:
        """Scan network for devices."""
        if self.scanning:
            return self.devices

        self.scanning = True
        try:
            # TODO: Implement network scanning
            self.logger.info(f"Scanning network: {subnet}")
            # Placeholder - implement actual scanning
            return self.devices

        finally:
            self.scanning = False

    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get device status."""
        if device_id not in self.devices:
            return {"error": "Device not found"}

        device = self.devices[device_id]
        
        # Get locations from database
        locations = await self.db_manager.get_device_locations(device_id)
        
        return {
            "device_id": device.device_id,
            "phone_number": device.phone_number,
            "ip_address": device.ip_address,
            "status": device.status,
            "last_seen": device.last_seen.isoformat(),
            "ports": device.ports,
            "services": device.services,
            "locations": locations
        }

    async def monitor_device(self, device_id: str, interval: int = 60):
        """Monitor device status and track location."""
        while True:
            try:
                if device_id in self.devices:
                    # Update connection status
                    await self.connect_device(device_id)
                    
                    # Track location
                    location_task = asyncio.create_task(
                        self.db_manager.track_device_movement(device_id)
                    )
                    
                    await asyncio.sleep(interval)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring device {device_id}: {str(e)}")
                await asyncio.sleep(interval)

    async def add_location(self, device_id: str, latitude: float, longitude: float, accuracy: float):
        """Add a new location for a device."""
        location_data = {
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy,
            "source": "gsm"
        }
        await self.db_manager.add_location(device_id, location_data)

    async def add_connection(self, device_id: str, connection_type: str, ip_address: str, port: int):
        """Add a new device connection record."""
        connection_data = {
            "connection_type": connection_type,
            "ip_address": ip_address,
            "port": port,
            "status": "connected"
        }
        await self.db_manager.add_connection(device_id, connection_data)

    async def add_sms(self, device_id: str, sender: str, recipient: str, content: str):
        """Add a new SMS message record."""
        sms_data = {
            "sender": sender,
            "recipient": recipient,
            "content": content,
            "direction": "in" if sender == self.devices[device_id].phone_number else "out",
            "status": "delivered"
        }
        await self.db_manager.add_sms(device_id, sms_data)

    async def add_call(self, device_id: str, caller: str, callee: str, duration: int):
        """Add a new call record."""
        call_data = {
            "caller": caller,
            "callee": callee,
            "duration": duration,
            "status": "completed"
        }
        await self.db_manager.add_call(device_id, call_data)

    async def add_gprs_session(self, device_id: str, session_id: str, ip_address: str):
        """Add a new GPRS session record."""
        session_data = {
            "session_id": session_id,
            "ip_address": ip_address,
            "status": "active",
            "data_usage": 0
        }
        await self.db_manager.add_gprs_session(device_id, session_data)

# Example usage
async def main():
    manager = DeviceConnectionManager()
    
    try:
        # Initialize device with phone number
        phone_device = await manager.initialize_device("device1", phone_number="+1234567890")
        print(f"Phone device: {phone_device}")
        
        # Initialize device with IP address
        ip_device = await manager.initialize_device("device2", ip_address="192.168.1.100")
        print(f"IP device: {ip_device}")
        
        # Connect devices
        await manager.connect_device("device1")
        await manager.connect_device("device2")
        
        # Add location
        await manager.add_location("device1", 37.7749, -122.4194, 50.0)
        
        # Add connection
        await manager.add_connection("device2", "ssh", "192.168.1.100", 22)
        
        # Get device status
        status = await manager.get_device_status("device1")
        print(f"Device status: {status}")
        
        # Start monitoring
        task = asyncio.create_task(
            manager.monitor_device("device1")
        )
        
    finally:
        task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
