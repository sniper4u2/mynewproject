import logging
import asyncio
import json
import socket
import ssl
from typing import Dict, Optional, List
import paramiko
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger('C2Server')

@dataclass
class YateBTSConfig:
    host: str
    port: int
    username: str
    password: str
    max_connections: int = 100
    timeout: int = 30
    retry_delay: int = 5
    max_retries: int = 3
    monitoring_interval: int = 10
    error_retry_delay: int = 5

class YateBTSIntegration:
    def __init__(self, config: YateBTSConfig):
        self.config = config
        self.connections: Dict[str, paramiko.SSHClient] = {}
        self.active_sessions: Dict[str, Dict] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
        # Initialize pool of SSH clients
        self.ssh_pool = self._initialize_ssh_pool()

    def _initialize_ssh_pool(self) -> List[paramiko.SSHClient]:
        """Initialize pool of SSH clients"""
        pool = []
        for _ in range(self.config.max_connections):
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            pool.append(client)
        return pool

    async def connect(self, device_id: str) -> bool:
        """Connect to YateBTS instance"""
        try:
            if device_id in self.connections:
                return True
            
            # Get SSH client from pool
            client = self.ssh_pool.pop()
            
            # Connect with retry mechanism
            attempts = 0
            while attempts < self.config.max_retries:
                try:
                    client.connect(
                        self.config.host,
                        port=self.config.port,
                        username=self.config.username,
                        password=self.config.password,
                        timeout=self.config.timeout
                    )
                    break
                except Exception as e:
                    attempts += 1
                    if attempts < self.config.max_retries:
                        logger.warning(f"Connection attempt {attempts} failed: {str(e)}")
                        await asyncio.sleep(self.config.retry_delay)
                    else:
                        logger.error(f"Failed to connect after {self.config.max_retries} attempts")
                        client.close()
                        self.ssh_pool.append(client)
                        return False
            
            # Store connection
            self.connections[device_id] = client
            
            # Start monitoring
            self.monitoring_tasks[device_id] = asyncio.create_task(
                self._monitor_connection(device_id)
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to YateBTS: {str(e)}")
            return False

    async def disconnect(self, device_id: str) -> bool:
        """Disconnect from YateBTS instance"""
        try:
            if device_id in self.connections:
                # Cancel monitoring task
                if device_id in self.monitoring_tasks:
                    self.monitoring_tasks[device_id].cancel()
                
                # Close connection
                self.connections[device_id].close()
                
                # Return SSH client to pool
                self.ssh_pool.append(self.connections[device_id])
                del self.connections[device_id]
                
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to disconnect: {str(e)}")
            return False

    async def _monitor_connection(self, device_id: str):
        """Monitor YateBTS connection continuously"""
        while True:
            try:
                # Get connection stats
                stats = await self.get_connection_stats(device_id)
                
                # Check for anomalies
                if self._detect_anomalies(stats):
                    await self._handle_anomalies(device_id, stats)
                
                await asyncio.sleep(10)  # Monitor interval
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error for {device_id}: {str(e)}")
                await asyncio.sleep(5)

    async def get_connection_stats(self, device_id: str) -> Dict:
        """Get connection statistics"""
        try:
            if device_id not in self.connections:
                return {}
            
            client = self.connections[device_id]
            stdin, stdout, stderr = client.exec_command('yate -s')
            
            stats = stdout.read().decode()
            return json.loads(stats)
        except Exception as e:
            logger.error(f"Failed to get stats: {str(e)}")
            return {}

    def _detect_anomalies(self, stats: Dict) -> bool:
        """Detect anomalies in connection statistics"""
        if not stats:
            return False
        
        # Check for high error rates
        if stats.get('error_rate', 0) > 0.1:
            return True
        
        # Check for unusual traffic patterns
        if stats.get('traffic_volume', 0) > 1000000:  # 1MB threshold
            return True
        
        # Check for connection issues
        if stats.get('connection_status') != 'connected':
            return True
        
        return False

    async def _handle_anomalies(self, device_id: str, stats: Dict):
        """Handle detected anomalies"""
        try:
            # Log the anomaly
            logger.warning(f"Anomaly detected for {device_id}: {stats}")
            
            # Try to fix the issue
            if stats.get('error_rate', 0) > 0.1:
                await self._restart_connection(device_id)
            
            if stats.get('traffic_volume', 0) > 1000000:
                await self._throttle_traffic(device_id)
            
            if stats.get('connection_status') != 'connected':
                await self._reconnect(device_id)
        except Exception as e:
            logger.error(f"Failed to handle anomaly: {str(e)}")

    async def _restart_connection(self, device_id: str):
        """Restart YateBTS connection"""
        try:
            if device_id in self.connections:
                await self.disconnect(device_id)
                await asyncio.sleep(self.config.retry_delay)
                await self.connect(device_id)
                logger.info(f"Connection restarted for {device_id}")
        except Exception as e:
            logger.error(f"Failed to restart connection: {str(e)}")

    async def _throttle_traffic(self, device_id: str):
        """Throttle traffic for YateBTS instance"""
        try:
            if device_id in self.connections:
                client = self.connections[device_id]
                stdin, stdout, stderr = client.exec_command('yate -t')
                logger.info(f"Traffic throttled for {device_id}")
        except Exception as e:
            logger.error(f"Failed to throttle traffic: {str(e)}")

    async def _reconnect(self, device_id: str):
        """Reconnect to YateBTS instance"""
        try:
            if device_id in self.connections:
                await self.disconnect(device_id)
                await asyncio.sleep(self.config.retry_delay)
                await self.connect(device_id)
                logger.info(f"Reconnected {device_id}")
        except Exception as e:
            logger.error(f"Failed to reconnect: {str(e)}")

    async def start_monitoring(self, device_id: str, interval: int = 10):
        """Start monitoring YateBTS instance"""
        try:
            if device_id not in self.monitoring_tasks:
                self.monitoring_tasks[device_id] = asyncio.create_task(
                    self._monitor_connection(device_id)
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to start monitoring: {str(e)}")
            return False

    async def stop_monitoring(self, device_id: str):
        """Stop monitoring YateBTS instance"""
        try:
            if device_id in self.monitoring_tasks:
                self.monitoring_tasks[device_id].cancel()
                del self.monitoring_tasks[device_id]
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {str(e)}")
            return False

    async def execute_command(self, device_id: str, command: str) -> Dict:
        """Execute command on YateBTS instance"""
        try:
            if device_id not in self.connections:
                return {'error': 'Not connected'}
            
            client = self.connections[device_id]
            stdin, stdout, stderr = client.exec_command(command)
            
            result = {
                'stdout': stdout.read().decode(),
                'stderr': stderr.read().decode(),
                'return_code': stdout.channel.recv_exit_status()
            }
            
            return result
        except Exception as e:
            logger.error(f"Failed to execute command: {str(e)}")
            return {'error': str(e)}
