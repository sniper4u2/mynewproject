import asyncio
import logging
from typing import Dict, List
import psutil
import time
import json
from datetime import datetime
import platform
import os
import subprocess

logger = logging.getLogger('C2Server')

class PerformanceMonitor:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.metrics_history: List[Dict] = []
        self.system_info = self._get_system_info()
        
    def _get_system_info(self) -> Dict:
        """Get system information"""
        try:
            return {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'cpu_count': psutil.cpu_count(),
                'total_memory': psutil.virtual_memory().total,
                'disk_partitions': [
                    {
                        'device': part.device,
                        'mount_point': part.mountpoint,
                        'fstype': part.fstype
                    }
                    for part in psutil.disk_partitions()
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {str(e)}")
            return {}
    
    async def start(self):
        """Start performance monitoring"""
        try:
            # Start periodic checks
            await asyncio.gather(
                self._monitor_cpu(),
                self._monitor_memory(),
                self._monitor_disk(),
                self._monitor_process()
            )
            logger.info("Performance monitoring started")
        except Exception as e:
            logger.error(f"Failed to start performance monitoring: {str(e)}")
            raise
    
    async def stop(self):
        """Stop performance monitoring"""
        try:
            # Cleanup
            self.metrics_history.clear()
            logger.info("Performance monitoring stopped")
        except Exception as e:
            logger.error(f"Failed to stop performance monitoring: {str(e)}")
            raise
    
    async def _monitor_cpu(self):
        """Monitor CPU usage"""
        while True:
            try:
                # Get CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                per_cpu = psutil.cpu_percent(interval=1, percpu=True)
                cpu_times = psutil.cpu_times_percent(interval=1)
                
                # Store metrics
                metrics = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'type': 'cpu',
                    'total_usage': cpu_percent,
                    'per_cpu': per_cpu,
                    'times': {
                        'user': cpu_times.user,
                        'system': cpu_times.system,
                        'idle': cpu_times.idle,
                        'iowait': getattr(cpu_times, 'iowait', 0)
                    }
                }
                
                await self._store_metrics(metrics)
                
                await asyncio.sleep(self.config.get('cpu_check_interval', 5))
            except Exception as e:
                logger.error(f"Failed to monitor CPU: {str(e)}")
                await asyncio.sleep(1)
    
    async def _monitor_memory(self):
        """Monitor memory usage"""
        while True:
            try:
                # Get memory metrics
                mem = psutil.virtual_memory()
                swap = psutil.swap_memory()
                
                # Store metrics
                metrics = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'type': 'memory',
                    'total': mem.total,
                    'available': mem.available,
                    'used': mem.used,
                    'percent': mem.percent,
                    'swap_total': swap.total,
                    'swap_used': swap.used,
                    'swap_percent': swap.percent
                }
                
                await self._store_metrics(metrics)
                
                await asyncio.sleep(self.config.get('memory_check_interval', 5))
            except Exception as e:
                logger.error(f"Failed to monitor memory: {str(e)}")
                await asyncio.sleep(1)
    
    async def _monitor_disk(self):
        """Monitor disk usage"""
        while True:
            try:
                # Get disk metrics
                partitions = psutil.disk_partitions()
                disk_metrics = {}
                
                for partition in partitions:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_metrics[partition.mountpoint] = {
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': usage.percent
                    }
                
                # Store metrics
                metrics = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'type': 'disk',
                    'partitions': disk_metrics
                }
                
                await self._store_metrics(metrics)
                
                await asyncio.sleep(self.config.get('disk_check_interval', 30))
            except Exception as e:
                logger.error(f"Failed to monitor disk: {str(e)}")
                await asyncio.sleep(1)
    
    async def _monitor_process(self):
        """Monitor process activity"""
        while True:
            try:
                # Get process metrics
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
                    try:
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'username': proc.info['username'],
                            'memory_percent': proc.info['memory_percent'],
                            'cpu_percent': proc.info['cpu_percent']
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                
                # Store metrics
                metrics = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'type': 'process',
                    'processes': processes
                }
                
                await self._store_metrics(metrics)
                
                await asyncio.sleep(self.config.get('process_check_interval', 10))
            except Exception as e:
                logger.error(f"Failed to monitor processes: {str(e)}")
                await asyncio.sleep(1)
    
    async def _store_metrics(self, metrics: Dict):
        """Store performance metrics"""
        try:
            # Add to history
            self.metrics_history.append(metrics)
            
            # Keep only last N entries
            max_history = self.config.get('max_history', 1000)
            if len(self.metrics_history) > max_history:
                self.metrics_history = self.metrics_history[-max_history:]
            
            # Alert if thresholds are exceeded
            await self._check_thresholds(metrics)
        except Exception as e:
            logger.error(f"Failed to store metrics: {str(e)}")
            raise
    
    async def _check_thresholds(self, metrics: Dict):
        """Check if any metrics exceed configured thresholds"""
        try:
            thresholds = {
                'cpu': self.config.get('cpu_threshold', 90),
                'memory': self.config.get('memory_threshold', 95),
                'disk': self.config.get('disk_threshold', 90)
            }
            
            if metrics['type'] == 'cpu' and metrics['total_usage'] > thresholds['cpu']:
                await self._create_alert(
                    'cpu_usage',
                    f"High CPU usage: {metrics['total_usage']}%",
                    'warning'
                )
            
            if metrics['type'] == 'memory' and metrics['percent'] > thresholds['memory']:
                await self._create_alert(
                    'memory_usage',
                    f"High memory usage: {metrics['percent']}%",
                    'warning'
                )
            
            if metrics['type'] == 'disk':
                for mount, usage in metrics['partitions'].items():
                    if usage['percent'] > thresholds['disk']:
                        await self._create_alert(
                            'disk_usage',
                            f"High disk usage on {mount}: {usage['percent']}%",
                            'warning'
                        )
        except Exception as e:
            logger.error(f"Failed to check thresholds: {str(e)}")
            raise
    
    async def _create_alert(self, type: str, message: str, severity: str):
        """Create a performance alert"""
        try:
            alert = {
                'timestamp': datetime.utcnow().isoformat(),
                'type': type,
                'message': message,
                'severity': severity
            }
            
            # Log the alert
            logger.warning(f"Performance alert: {severity.upper()} - {type}")
            
            # TODO: Implement alert notification
            pass
        except Exception as e:
            logger.error(f"Failed to create alert: {str(e)}")
            raise
    
    async def get_metrics(self, metric_type: str = None, start_time: datetime = None, 
                        end_time: datetime = None) -> List[Dict]:
        """Get stored metrics"""
        try:
            metrics = self.metrics_history.copy()
            
            if metric_type:
                metrics = [m for m in metrics if m['type'] == metric_type]
            
            if start_time:
                metrics = [m for m in metrics 
                          if datetime.fromisoformat(m['timestamp']) >= start_time]
            
            if end_time:
                metrics = [m for m in metrics 
                          if datetime.fromisoformat(m['timestamp']) <= end_time]
            
            return metrics
        except Exception as e:
            logger.error(f"Failed to get metrics: {str(e)}")
            raise
    
    async def get_system_info(self) -> Dict:
        """Get current system information"""
        try:
            return self.system_info.copy()
        except Exception as e:
            logger.error(f"Failed to get system info: {str(e)}")
            raise
    
    async def get_process_list(self) -> List[Dict]:
        """Get current process list"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
                try:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'username': proc.info['username'],
                        'memory_percent': proc.info['memory_percent'],
                        'cpu_percent': proc.info['cpu_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            return processes
        except Exception as e:
            logger.error(f"Failed to get process list: {str(e)}")
            raise
