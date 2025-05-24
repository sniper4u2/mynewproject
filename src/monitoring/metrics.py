import asyncio
import logging
from typing import Dict, List
from datetime import datetime
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from .models import Metric

logger = logging.getLogger('C2Server')

class MetricsCollector:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.influx_client = None
        self.write_api = None
        self.metrics: List[Metric] = []
        
        # Initialize InfluxDB client
        self._initialize_influxdb()
    
    def _initialize_influxdb(self):
        """Initialize InfluxDB client"""
        try:
            self.influx_client = influxdb_client.InfluxDBClient(
                url=self.config.get('influxdb_url', 'http://localhost:8086'),
                token=self.config.get('influxdb_token'),
                org=self.config.get('influxdb_org', 'c2')
            )
            self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            logger.info("InfluxDB client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB client: {str(e)}")
            raise
    
    async def store_metrics(self, device_id: str, metrics: Dict):
        """Store metrics in InfluxDB"""
        try:
            # Create metric point
            point = influxdb_client.Point("device_metrics")
            point.tag("device_id", device_id)
            
            # Add fields from metrics
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    point.field(key, value)
            
            # Write to InfluxDB
            self.write_api.write(
                bucket=self.config.get('influxdb_bucket', 'c2_metrics'),
                org=self.config.get('influxdb_org', 'c2'),
                record=point
            )
            
            logger.debug(f"Stored metrics for device {device_id}")
        except Exception as e:
            logger.error(f"Failed to store metrics for device {device_id}: {str(e)}")
            raise
    
    async def get_metrics(self, device_id: str, start_time: datetime, end_time: datetime):
        """Get metrics for a device"""
        try:
            # Construct query
            bucket = self.config.get('influxdb_bucket', 'c2_metrics')
            query = f'from(bucket: "{bucket}")'
            query += f' |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})'
            query += f' |> filter(fn: (r) => r["device_id"] == "{device_id}")'
            
            tables = self.influx_client.query_api().query(query)
            
            # Convert to list of dictionaries
            metrics = []
            for table in tables:
                for record in table.records:
                    metrics.append({
                        "time": record.get_time(),
                        **record.values
                    })
            
            return metrics
        except Exception as e:
            logger.error(f"Failed to get metrics for device {device_id}: {str(e)}")
            raise
    
    async def get_alerts(self, device_id: str, start_time: datetime, end_time: datetime):
        """Get alerts for a device"""
        try:
            # Construct query
            bucket = self.config.get('influxdb_bucket', 'c2_metrics')
            query = f'from(bucket: "{bucket}")'
            query += f' |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})'
            query += f' |> filter(fn: (r) => r["device_id"] == "{device_id}" and r["_measurement"] == "alerts")'
            
            tables = self.influx_client.query_api().query(query)
            
            # Convert to list of dictionaries
            alerts = []
            for table in tables:
                for record in table.records:
                    alerts.append({
                        "time": record.get_time(),
                        "severity": record.get_field("severity"),
                        "type": record.get_field("type"),
                        "message": record.get_field("message")
                    })
            
            return alerts
        except Exception as e:
            logger.error(f"Failed to get alerts for device {device_id}: {str(e)}")
            raise
