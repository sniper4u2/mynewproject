import asyncio
import logging
from typing import Dict, List
from datetime import datetime
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger('C2Server')

class AlertManager:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.alert_rules = self._load_alert_rules()
        self.alert_history: List[Dict] = []
        
    def _load_alert_rules(self) -> Dict:
        """Load alert rules from configuration"""
        try:
            rules = {
                'cpu_usage': {
                    'threshold': 90,
                    'severity': 'critical',
                    'description': 'High CPU usage'
                },
                'memory_usage': {
                    'threshold': 95,
                    'severity': 'critical',
                    'description': 'High memory usage'
                },
                'network_latency': {
                    'threshold': 100,
                    'unit': 'ms',
                    'severity': 'warning',
                    'description': 'High network latency'
                },
                'connection_loss': {
                    'threshold': 3,
                    'unit': 'attempts',
                    'severity': 'critical',
                    'description': 'Multiple connection failures'
                }
            }
            return rules
        except Exception as e:
            logger.error(f"Failed to load alert rules: {str(e)}")
            return {}
    
    async def check_metrics(self, device_id: str, metrics: Dict):
        """Check metrics against alert rules"""
        try:
            for metric, value in metrics.items():
                if metric in self.alert_rules:
                    rule = self.alert_rules[metric]
                    if isinstance(value, (int, float)) and value >= rule['threshold']:
                        await self._create_alert(
                            device_id=device_id,
                            type=metric,
                            severity=rule['severity'],
                            message=f"{rule['description']}: {value} {rule.get('unit', '')}"
                        )
        except Exception as e:
            logger.error(f"Failed to check metrics for alerts: {str(e)}")
            raise
    
    async def _create_alert(self, device_id: str, type: str, severity: str, message: str):
        """Create and store an alert"""
        try:
            alert = {
                'device_id': device_id,
                'type': type,
                'severity': severity,
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Store in alert history
            self.alert_history.append(alert)
            
            # Send notification
            await self._send_notification(alert)
            
            logger.warning(f"Alert created: {severity} - {type}")
            return alert
        except Exception as e:
            logger.error(f"Failed to create alert: {str(e)}")
            raise
    
    async def _send_notification(self, alert: Dict):
        """Send alert notification"""
        try:
            # Email notification
            if self.config.get('email_enabled', False):
                message = MIMEMultipart()
                message['From'] = self.config.get('email_from', 'no-reply@c2server.com')
                message['To'] = self.config.get('email_to', 'admin@c2server.com')
                message['Subject'] = f"C2 Server Alert: {alert['severity'].upper()} - {alert['type']}"
                
                body = f"""
                Device ID: {alert['device_id']}
                Type: {alert['type']}
                Severity: {alert['severity']}
                Message: {alert['message']}
                Timestamp: {alert['timestamp']}
                """
                
                message.attach(MIMEText(body, 'plain'))
                
                with smtplib.SMTP(self.config.get('smtp_host', 'localhost'), 
                                self.config.get('smtp_port', 25)) as server:
                    server.send_message(message)
            
            # Slack notification
            if self.config.get('slack_enabled', False):
                # TODO: Implement Slack notification
                pass
            
            # Webhook notification
            if self.config.get('webhook_enabled', False):
                # TODO: Implement webhook notification
                pass
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            raise
    
    async def get_alerts(self, device_id: str = None, severity: str = None):
        """Get stored alerts"""
        try:
            alerts = self.alert_history.copy()
            
            if device_id:
                alerts = [a for a in alerts if a['device_id'] == device_id]
            
            if severity:
                alerts = [a for a in alerts if a['severity'] == severity]
            
            return alerts
        except Exception as e:
            logger.error(f"Failed to get alerts: {str(e)}")
            raise
    
    async def clear_alerts(self, device_id: str = None):
        """Clear stored alerts"""
        try:
            if device_id:
                self.alert_history = [a for a in self.alert_history if a['device_id'] != device_id]
            else:
                self.alert_history.clear()
            
            logger.info("Alerts cleared")
        except Exception as e:
            logger.error(f"Failed to clear alerts: {str(e)}")
            raise
