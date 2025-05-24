import asyncio
import logging
from typing import Dict, List, Optional
import prometheus_client
from prometheus_fastapi_instrumentator import Instrumentator
from .metrics import MetricsCollector
from .alerts import AlertManager
from .network import NetworkMonitor
from .security import SecurityMonitor
from .performance import PerformanceMonitor

logger = logging.getLogger('C2Server')

class MonitoringSystem:
    def __init__(self, config: Dict):
        self.config = config
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.network_monitor = NetworkMonitor()
        self.security_monitor = SecurityMonitor()
        self.performance_monitor = PerformanceMonitor()
        
        # Prometheus metrics
        self.device_metrics = prometheus_client.Gauge(
            'c2_device_metrics',
            'Device metrics',
            ['device_id', 'metric_type', 'protocol']
        )
        
        self.connection_metrics = prometheus_client.Gauge(
            'c2_connection_metrics',
            'Connection metrics',
            ['device_id', 'connection_type', 'status']
        )
        
        self.alert_metrics = prometheus_client.Counter(
            'c2_alerts_total',
            'Total number of alerts',
            ['severity', 'type']
        )
        
        # Initialize monitors
        self.monitors = {
            'network': self.network_monitor,
            'security': self.security_monitor,
            'performance': self.performance_monitor
        }
        
    async def start(self):
        """Start all monitoring components"""
        try:
            # Start Prometheus metrics collection
            Instrumentator().instrument(self.config['app']).expose(self.config['app'])
            
            # Start monitoring tasks
            await asyncio.gather(
                self.network_monitor.start(),
                self.security_monitor.start(),
                self.performance_monitor.start()
            )
            
            logger.info("Monitoring system started successfully")
        except Exception as e:
            logger.error(f"Failed to start monitoring system: {str(e)}")
            raise
    
    async def stop(self):
        """Stop all monitoring components"""
        try:
            # Stop all monitors
            await asyncio.gather(
                *[monitor.stop() for monitor in self.monitors.values()]
            )
            
            # Clean up metrics
            prometheus_client.REGISTRY.unregister(self.device_metrics)
            prometheus_client.REGISTRY.unregister(self.connection_metrics)
            prometheus_client.REGISTRY.unregister(self.alert_metrics)
            
            logger.info("Monitoring system stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop monitoring system: {str(e)}")
            raise
    
    async def collect_metrics(self, device_id: str, metrics: Dict):
        """Collect and report metrics for a device"""
        try:
            # Update Prometheus metrics
            for metric_type, value in metrics.items():
                self.device_metrics.labels(
                    device_id=device_id,
                    metric_type=metric_type,
                    protocol=metrics.get('protocol', 'unknown')
                ).set(value)
            
            # Store metrics in database
            await self.metrics_collector.store_metrics(device_id, metrics)
            
            # Check for alerts
            await self.alert_manager.check_metrics(device_id, metrics)
            
            logger.debug(f"Collected metrics for device {device_id}")
        except Exception as e:
            logger.error(f"Failed to collect metrics for device {device_id}: {str(e)}")
            raise
    
    async def handle_alert(self, alert: Dict):
        """Handle and report an alert"""
        try:
            # Update alert metrics
            self.alert_metrics.labels(
                severity=alert['severity'],
                type=alert['type']
            ).inc()
            
            # Process alert
            await self.alert_manager.process_alert(alert)
            
            logger.warning(f"Alert processed: {alert['type']} - {alert['severity']}")
        except Exception as e:
            logger.error(f"Failed to handle alert: {str(e)}")
            raise
