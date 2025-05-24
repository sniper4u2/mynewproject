import requests
import logging
from typing import Dict, Optional
from datetime import datetime
from protocol_adapter import ProtocolAdapter

class HTTPAdapter(ProtocolAdapter):
    def __init__(self, db, key, config):
        super().__init__(db, key, config)
        self.logger = logging.getLogger('C2Server')
        self.endpoints = config['endpoints']
        self.heartbeat_interval = config['heartbeat']['interval_seconds']
        self.timeout = config['heartbeat']['timeout_seconds']

    def send_data(self, data: Dict, device_id: str) -> bool:
        try:
            for endpoint in self.endpoints:
                url = f"https://{endpoint['domain']}{endpoint['path']}"
                headers = endpoint.get('headers', {})
                
                # Encrypt data
                encrypted_data = self.encrypt_data(data)
                
                # Send request
                response = requests.post(
                    url,
                    json=encrypted_data,
                    headers=headers,
                    timeout=self.timeout,
                    verify=True  # Verify SSL certificates
                )
                
                if response.status_code == 200:
                    self.logger.info(f"Successfully sent data to {url} for device {device_id}")
                    return True
                else:
                    self.logger.error(f"Failed to send data to {url}: {response.status_code}")
            
            return False
        except Exception as e:
            self.logger.error(f"Error sending HTTP data: {str(e)}")
            return False

    def receive_data(self, device_id: str) -> Optional[Dict]:
        # HTTP protocol doesn't have a dedicated receive method
        # Data is received through webhooks or polling
        return None

    def heartbeat(self, device_id: str) -> bool:
        try:
            for endpoint in self.endpoints:
                url = f"https://{endpoint['domain']}{endpoint['path']}"
                headers = endpoint.get('headers', {})
                
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    verify=True
                )
                
                if response.status_code == 200:
                    self.logger.info(f"Heartbeat successful for device {device_id}")
                    return True
            
            return False
        except Exception as e:
            self.logger.error(f"Heartbeat failed: {str(e)}")
            return False
