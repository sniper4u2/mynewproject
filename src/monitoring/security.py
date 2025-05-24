import asyncio
import logging
from typing import Dict, List
import nmap
import pyshark
import socket
import ssl
import json
from datetime import datetime
import hashlib

logger = logging.getLogger('C2Server')

class SecurityMonitor:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.nm = nmap.PortScanner()
        self.active_scans: Dict[str, Dict] = {}
        self.security_events: List[Dict] = []
        
    async def start(self):
        """Start security monitoring"""
        try:
            # Start periodic security checks
            await asyncio.gather(
                self._monitor_network_security(),
                self._monitor_ssl_tls(),
                self._monitor_packet_capture()
            )
            logger.info("Security monitoring started")
        except Exception as e:
            logger.error(f"Failed to start security monitoring: {str(e)}")
            raise
    
    async def stop(self):
        """Stop security monitoring"""
        try:
            # Cleanup
            self.active_scans.clear()
            self.security_events.clear()
            logger.info("Security monitoring stopped")
        except Exception as e:
            logger.error(f"Failed to stop security monitoring: {str(e)}")
            raise
    
    async def _monitor_network_security(self):
        """Monitor network security"""
        while True:
            try:
                # Scan network for vulnerabilities
                targets = self.config.get('network_scan_targets', ['127.0.0.1'])
                
                for target in targets:
                    try:
                        # Perform scan
                        self.nm.scan(target, arguments='-sV -O')
                        
                        # Check for vulnerabilities
                        for host in self.nm.all_hosts():
                            if self.nm[host].state() == 'up':
                                for proto in self.nm[host].all_protocols():
                                    ports = self.nm[host][proto].keys()
                                    for port in ports:
                                        port_info = self.nm[host][proto][port]
                                        if port_info['state'] == 'open':
                                            await self._check_vulnerability(host, port, port_info)
                    except Exception as e:
                        logger.error(f"Scan failed for {target}: {str(e)}")
                
                await asyncio.sleep(self.config.get('network_scan_interval', 3600))
            except Exception as e:
                logger.error(f"Failed to monitor network security: {str(e)}")
                await asyncio.sleep(1)
    
    async def _check_vulnerability(self, host: str, port: int, port_info: Dict):
        """Check for known vulnerabilities"""
        try:
            # Check for common vulnerabilities
            vulnerabilities = {
                'http': {
                    '80': ['HTTP Basic Auth Bypass', 'Directory Traversal'],
                    '443': ['SSL/TLS Weak Ciphers', 'Heartbleed']
                },
                'ssh': {
                    '22': ['SSH Weak Key', 'SSH Protocol Version']
                }
            }
            
            if port_info['name'] in vulnerabilities:
                if str(port) in vulnerabilities[port_info['name']]:
                    for vuln in vulnerabilities[port_info['name']][str(port)]:
                        await self._create_security_event(
                            host=host,
                            port=port,
                            vulnerability=vuln,
                            severity='medium'
                        )
        except Exception as e:
            logger.error(f"Failed to check vulnerability: {str(e)}")
            raise
    
    async def _monitor_ssl_tls(self):
        """Monitor SSL/TLS security"""
        while True:
            try:
                # Check SSL/TLS configurations
                targets = self.config.get('ssl_scan_targets', ['localhost'])
                
                for target in targets:
                    try:
                        # Check SSL/TLS version
                        context = ssl.create_default_context()
                        with socket.create_connection((target, 443)) as sock:
                            with context.wrap_socket(sock, server_hostname=target) as ssock:
                                version = ssock.version()
                                
                                # Check for weak ciphers
                                cipher = ssock.cipher()
                                if cipher[0] in ['RC4', 'DES', '3DES']:
                                    await self._create_security_event(
                                        host=target,
                                        port=443,
                                        vulnerability='Weak Cipher Suite',
                                        severity='high'
                                    )
                                
                                # Check for SSL/TLS version
                                if version not in ['TLSv1.2', 'TLSv1.3']:
                                    await self._create_security_event(
                                        host=target,
                                        port=443,
                                        vulnerability='Outdated SSL/TLS Version',
                                        severity='high'
                                    )
                    except Exception as e:
                        logger.error(f"SSL check failed for {target}: {str(e)}")
                        await self._create_security_event(
                            host=target,
                            port=443,
                            vulnerability='SSL/TLS Check Failed',
                            severity='warning'
                        )
                
                await asyncio.sleep(self.config.get('ssl_check_interval', 3600))
            except Exception as e:
                logger.error(f"Failed to monitor SSL/TLS: {str(e)}")
                await asyncio.sleep(1)
    
    async def _monitor_packet_capture(self):
        """Monitor network packets for security events"""
        while True:
            try:
                # Capture packets
                capture = pyshark.LiveCapture(interface=self.config.get('capture_interface', 'any'))
                
                for packet in capture.sniff_continuously():
                    try:
                        # Analyze packet
                        await self._analyze_packet(packet)
                    except Exception as e:
                        logger.error(f"Packet analysis failed: {str(e)}")
                        continue
                
                await asyncio.sleep(self.config.get('packet_capture_interval', 60))
            except Exception as e:
                logger.error(f"Failed to monitor packets: {str(e)}")
                await asyncio.sleep(1)
    
    async def _analyze_packet(self, packet):
        """Analyze packet for security events"""
        try:
            # Check for suspicious patterns
            if 'IP' in packet:
                src_ip = packet.ip.src
                dst_ip = packet.ip.dst
                
                # Check for port scanning
                if 'TCP' in packet:
                    flags = packet.tcp.flags
                    if flags == 'S':  # SYN packet
                        await self._check_port_scan(src_ip, dst_ip)
                
                # Check for large data transfers
                if int(packet.length) > self.config.get('large_transfer_threshold', 1000000):
                    await self._create_security_event(
                        host=src_ip,
                        port=int(packet.tcp.srcport),
                        vulnerability='Large Data Transfer',
                        severity='medium'
                    )
        except Exception as e:
            logger.error(f"Failed to analyze packet: {str(e)}")
            raise
    
    async def _check_port_scan(self, src_ip: str, dst_ip: str):
        """Check for port scanning activity"""
        try:
            # Track SYN packets
            if src_ip not in self.active_scans:
                self.active_scans[src_ip] = {
                    'count': 1,
                    'last_time': datetime.utcnow()
                }
            else:
                self.active_scans[src_ip]['count'] += 1
                
                # Check for rapid SYN packets
                if self.active_scans[src_ip]['count'] > self.config.get('syn_threshold', 100):
                    time_diff = (datetime.utcnow() - self.active_scans[src_ip]['last_time']).total_seconds()
                    if time_diff < self.config.get('syn_time_window', 60):
                        await self._create_security_event(
                            host=src_ip,
                            port=None,
                            vulnerability='Potential Port Scan',
                            severity='high'
                        )
            
            self.active_scans[src_ip]['last_time'] = datetime.utcnow()
        except Exception as e:
            logger.error(f"Failed to check port scan: {str(e)}")
            raise
    
    async def _create_security_event(self, host: str, port: Optional[int], 
                                   vulnerability: str, severity: str):
        """Create and store a security event"""
        try:
            event = {
                'timestamp': datetime.utcnow().isoformat(),
                'host': host,
                'port': port,
                'vulnerability': vulnerability,
                'severity': severity,
                'event_id': hashlib.sha256(
                    json.dumps({
                        'host': host,
                        'port': port,
                        'vulnerability': vulnerability,
                        'timestamp': datetime.utcnow().isoformat()
                    }).encode()
                ).hexdigest()
            }
            
            # Store event
            self.security_events.append(event)
            
            # Alert if high severity
            if severity in ['high', 'critical']:
                logger.warning(f"Security event: {severity.upper()} - {vulnerability}")
            
            return event
        except Exception as e:
            logger.error(f"Failed to create security event: {str(e)}")
            raise
    
    async def get_security_events(self, host: str = None, severity: str = None):
        """Get stored security events"""
        try:
            events = self.security_events.copy()
            
            if host:
                events = [e for e in events if e['host'] == host]
            
            if severity:
                events = [e for e in events if e['severity'] == severity]
            
            return events
        except Exception as e:
            logger.error(f"Failed to get security events: {str(e)}")
            raise
    
    async def clear_security_events(self, host: str = None):
        """Clear stored security events"""
        try:
            if host:
                self.security_events = [e for e in self.security_events if e['host'] != host]
            else:
                self.security_events.clear()
            
            logger.info("Security events cleared")
        except Exception as e:
            logger.error(f"Failed to clear security events: {str(e)}")
            raise
