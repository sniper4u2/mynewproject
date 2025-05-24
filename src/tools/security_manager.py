import logging
from typing import Dict, Any, Optional
import hashlib
import hmac
import base64
import time
from datetime import datetime
import json
from aiohttp import web
from cryptography.fernet import Fernet

logger = logging.getLogger('C2Server')

class SecurityManager:
    def __init__(self, config: Dict[str, Any]):
        """Initialize security manager"""
        self.config = config
        self.api_keys = config.get('api_keys', {})
        self.ip_whitelist = config.get('ip_whitelist', [])
        self.rate_limit = config.get('rate_limit', 60)
        self.burst_limit = config.get('burst_limit', 10)
        self.key = Fernet.generate_key()
        self.fernet = Fernet(self.key)
        self.request_log = []
        self.failed_attempts = {}
        
    def _generate_token(self, api_key: str) -> str:
        """Generate a secure token for API authentication"""
        try:
            timestamp = str(int(time.time()))
            message = f"{api_key}:{timestamp}"
            signature = hmac.new(
                self.key,
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            return f"{timestamp}:{signature}"
        except Exception as e:
            logger.error(f"Failed to generate token: {str(e)}")
            raise
    
    def _validate_token(self, token: str, api_key: str) -> bool:
        """Validate an API token"""
        try:
            parts = token.split(':')
            if len(parts) != 2:
                return False
            
            timestamp, signature = parts
            message = f"{api_key}:{timestamp}"
            expected_signature = hmac.new(
                self.key,
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Check if signature matches
            if signature != expected_signature:
                return False
            
            # Check if token is expired (15 minute timeout)
            current_time = time.time()
            token_time = int(timestamp)
            if current_time - token_time > 900:
                return False
            
            return True
        except Exception as e:
            logger.error(f"Failed to validate token: {str(e)}")
            return False
    
    def _encrypt_data(self, data: Dict[str, Any]) -> str:
        """Encrypt sensitive data"""
        try:
            return self.fernet.encrypt(json.dumps(data).encode()).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt data: {str(e)}")
            raise
    
    def _decrypt_data(self, encrypted: str) -> Dict[str, Any]:
        """Decrypt sensitive data"""
        try:
            return json.loads(self.fernet.decrypt(encrypted.encode()).decode())
        except Exception as e:
            logger.error(f"Failed to decrypt data: {str(e)}")
            raise
    
    async def validate_request(self, request: web.Request) -> bool:
        """Validate incoming request"""
        try:
            # Check IP whitelist
            if self.ip_whitelist:
                client_ip = request.remote
                if client_ip not in self.ip_whitelist:
                    logger.warning(f"Access denied from IP: {client_ip}")
                    return False
            
            # Check rate limiting
            if not await self._check_rate_limit(request):
                return False
            
            # Check API key
            if self.config.get('api_key_required', True):
                api_key = request.headers.get('X-API-Key')
                if not api_key or api_key not in self.api_keys:
                    logger.warning("Invalid API key")
                    return False
            
            # Check authentication token
            auth_token = request.headers.get('Authorization')
            if auth_token:
                if not self._validate_token(auth_token, api_key):
                    logger.warning("Invalid authentication token")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Request validation failed: {str(e)}")
            return False
    
    async def _check_rate_limit(self, request: web.Request) -> bool:
        """Check rate limiting"""
        try:
            client_ip = request.remote
            current_time = time.time()
            
            # Check burst limit
            if client_ip in self.request_log:
                recent_requests = [r for r in self.request_log[client_ip] 
                                 if current_time - r < 60]
                if len(recent_requests) >= self.burst_limit:
                    logger.warning(f"Burst limit exceeded for IP: {client_ip}")
                    return False
            
            # Check rate limit
            if client_ip in self.request_log:
                request_count = len([r for r in self.request_log[client_ip] 
                                   if current_time - r < 3600])
                if request_count >= self.rate_limit:
                    logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                    return False
            
            # Add request to log
            if client_ip not in self.request_log:
                self.request_log[client_ip] = []
            self.request_log[client_ip].append(current_time)
            
            return True
        except Exception as e:
            logger.error(f"Rate limiting failed: {str(e)}")
            return False
    
    def validate_phone(self, phone: str) -> bool:
        """Validate phone number format"""
        try:
            # Basic phone number validation
            if not phone.isdigit() or len(phone) < 10:
                return False
            
            # Check against known patterns
            patterns = [
                r'^\+?[1-9]\d{1,14}$',  # E.164 format
                r'^\d{10,15}$'         # Basic numeric format
            ]
            
            for pattern in patterns:
                if re.match(pattern, phone):
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Phone validation failed: {str(e)}")
            return False
    
    def validate_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        try:
            # Basic IP validation using socket
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        try:
            # Basic email validation
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return False
            
            # Check against known disposable email providers
            disposable_domains = [
                'mailinator.com', 'guerrillamail.com', '10minutemail.com'
            ]
            
            domain = email.split('@')[-1]
            if domain.lower() in disposable_domains:
                return False
            
            return True
        except Exception as e:
            logger.error(f"Email validation failed: {str(e)}")
            return False
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security events"""
        try:
            event = {
                'timestamp': datetime.utcnow().isoformat(),
                'type': event_type,
                'details': details,
                'severity': self._determine_severity(event_type)
            }
            
            # Log to database/file
            self._store_security_event(event)
            
            # Alert if high severity
            if event['severity'] in ['high', 'critical']:
                self._send_security_alert(event)
        except Exception as e:
            logger.error(f"Failed to log security event: {str(e)}")
    
    def _determine_severity(self, event_type: str) -> str:
        """Determine severity level of security event"""
        severity_map = {
            'login_failure': 'medium',
            'rate_limit_exceeded': 'medium',
            'ip_blacklist': 'high',
            'malicious_payload': 'critical',
            'unauthorized_access': 'critical'
        }
        return severity_map.get(event_type, 'low')
    
    def _store_security_event(self, event: Dict[str, Any]):
        """Store security event in persistent storage"""
        try:
            # TODO: Implement storage mechanism
            pass
        except Exception as e:
            logger.error(f"Failed to store security event: {str(e)}")
    
    def _send_security_alert(self, event: Dict[str, Any]):
        """Send security alert notification"""
        try:
            # TODO: Implement alert notification
            pass
        except Exception as e:
            logger.error(f"Failed to send security alert: {str(e)}")
