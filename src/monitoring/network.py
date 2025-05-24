import asyncio
import logging
from typing import Dict, List
import netifaces
import psutil
import scapy.all as scapy
from datetime import datetime
import socket

logger = logging.getLogger('C2Server')

class NetworkMonitor:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.active_connections: Dict[str, Dict] = {}
        self.network_interfaces = self._get_network_interfaces()
        
    def _get_network_interfaces(self) -> Dict:
        """Get available network interfaces"""
        try:
            interfaces = {}
            for interface in netifaces.interfaces():
                addresses = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addresses:
                    interfaces[interface] = {
                        'ip': addresses[netifaces.AF_INET][0]['addr'],
                        'netmask': addresses[netifaces.AF_INET][0]['netmask']
                    }
            return interfaces
        except Exception as e:
            logger.error(f"Failed to get network interfaces: {str(e)}")
            return {}
    
    async def start(self):
        """Start network monitoring"""
        try:
            # Start periodic checks
            await asyncio.gather(
                self._monitor_connections(),
                self._monitor_bandwidth(),
                self._monitor_latency()
            )
            logger.info("Network monitoring started")
        except Exception as e:
            logger.error(f"Failed to start network monitoring: {str(e)}")
            raise
    
    async def stop(self):
        """Stop network monitoring"""
        try:
            # Cleanup
            self.active_connections.clear()
            logger.info("Network monitoring stopped")
        except Exception as e:
            logger.error(f"Failed to stop network monitoring: {str(e)}")
            raise
    
    async def _monitor_connections(self):
        """Monitor active connections"""
        while True:
            try:
                # Get current connections
                connections = psutil.net_connections()
                current_connections = {}
                
                for conn in connections:
                    if conn.status == 'ESTABLISHED':
                        local_addr = f"{conn.laddr.ip}:{conn.laddr.port}"
                        remote_addr = f"{conn.raddr.ip}:{conn.raddr.port}"
                        current_connections[local_addr] = {
                            'remote': remote_addr,
                            'status': conn.status,
                            'pid': conn.pid,
                            'last_seen': datetime.utcnow().isoformat()
                        }
                
                # Update active connections
                self.active_connections = current_connections
                
                # Check for new connections
                for conn in current_connections:
                    if conn not in self.active_connections:
                        logger.info(f"New connection: {conn} -> {current_connections[conn]['remote']}")
                
                await asyncio.sleep(self.config.get('connection_check_interval', 5))
            except Exception as e:
                logger.error(f"Failed to monitor connections: {str(e)}")
                await asyncio.sleep(1)
    
    async def _monitor_bandwidth(self):
        """Monitor network bandwidth"""
        while True:
            try:
                # Get current bandwidth
                stats = psutil.net_io_counters(pernic=True)
                metrics = {}
                
                for interface, stat in stats.items():
                    metrics[interface] = {
                        'bytes_sent': stat.bytes_sent,
                        'bytes_recv': stat.bytes_recv,
                        'packets_sent': stat.packets_sent,
                        'packets_recv': stat.packets_recv
                    }
                
                # Store metrics
                await self._store_metrics('bandwidth', metrics)
                
                await asyncio.sleep(self.config.get('bandwidth_check_interval', 10))
            except Exception as e:
                logger.error(f"Failed to monitor bandwidth: {str(e)}")
                await asyncio.sleep(1)
    
    async def _monitor_latency(self):
        """Monitor network latency"""
        while True:
            try:
                # Get latency to important targets
                targets = self.config.get('latency_targets', ['8.8.8.8', '1.1.1.1'])
                metrics = {}
                
                for target in targets:
                    try:
                        # Send ping
                        packet = scapy.IP(dst=target)/scapy.ICMP()
                        response = scapy.sr1(packet, timeout=2, verbose=0)
                        
                        if response:
                            metrics[target] = {
                                'latency': response.time,
                                'status': 'up'
                            }
                        else:
                            metrics[target] = {
                                'latency': None,
                                'status': 'down'
                            }
                    except Exception as e:
                        logger.error(f"Ping failed for {target}: {str(e)}")
                        metrics[target] = {
                            'latency': None,
                            'status': 'error'
                        }
                
                # Store metrics
                await self._store_metrics('latency', metrics)
                
                await asyncio.sleep(self.config.get('latency_check_interval', 30))
            except Exception as e:
                logger.error(f"Failed to monitor latency: {str(e)}")
                await asyncio.sleep(1)
    
    async def _store_metrics(self, metric_type: str, metrics: Dict):
        """Store network metrics"""
        try:
            # TODO: Implement metric storage (e.g., InfluxDB)
            pass
        except Exception as e:
            logger.error(f"Failed to store metrics: {str(e)}")
            raise
    
    async def get_active_connections(self) -> Dict:
        """Get current active connections"""
        try:
            return self.active_connections.copy()
        except Exception as e:
            logger.error(f"Failed to get active connections: {str(e)}")
            raise
    
    async def get_bandwidth_stats(self) -> Dict:
        """Get bandwidth statistics"""
        try:
            # Get current stats
            stats = psutil.net_io_counters(pernic=True)
            return stats
        except Exception as e:
            logger.error(f"Failed to get bandwidth stats: {str(e)}")
            raise
    
    async def get_latency_stats(self) -> Dict:
        """Get latency statistics"""
        try:
            # Get current latency
            targets = self.config.get('latency_targets', ['8.8.8.8', '1.1.1.1'])
            metrics = {}
            
            for target in targets:
                try:
                    # Send ping
                    packet = scapy.IP(dst=target)/scapy.ICMP()
                    response = scapy.sr1(packet, timeout=2, verbose=0)
                    
                    if response:
                        metrics[target] = {
                            'latency': response.time,
                            'status': 'up'
                        }
                    else:
                        metrics[target] = {
                            'latency': None,
                            'status': 'down'
                        }
                except Exception as e:
                    logger.error(f"Ping failed for {target}: {str(e)}")
                    metrics[target] = {
                        'latency': None,
                        'status': 'error'
                    }
            
            return metrics
        except Exception as e:
            logger.error(f"Failed to get latency stats: {str(e)}")
            raise
