from .base_tool import ToolInterface
from typing import Dict, Any, Optional
import asyncio
import logging
import subprocess
import json
from datetime import datetime
import os

logger = logging.getLogger('C2Server')

class SilentSMS(ToolInterface):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.path = config.get('path', 'silentsms')
        self.supported_features = ['SMS', 'USSD', 'Call']
        self.supported_protocols = ['SS7', 'GSM']
    
    async def initialize(self) -> bool:
        """Initialize SilentSMS"""
        try:
            # Check if SilentSMS is installed
            if not os.path.exists(self.path):
                logger.error("SilentSMS not found at specified path")
                return False
            
            # Check dependencies
            dependencies = ['python3', 'scapy', 'pyasn1']
            for dep in dependencies:
                if not self._check_dependency(dep):
                    logger.error(f"Missing dependency: {dep}")
                    return False
            
            logger.info("SilentSMS initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize SilentSMS: {str(e)}")
            return False
    
    def _check_dependency(self, dep: str) -> bool:
        """Check if a dependency is installed"""
        try:
            result = subprocess.run(['which', dep], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False
    
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run SilentSMS operation"""
        try:
            # Validate parameters
            if not await self.validate_params(params):
                return {'status': 'error', 'message': 'Invalid parameters'}
            
            feature = params.get('feature')
            target = params.get('target')
            message = params.get('message')
            
            # Construct command
            cmd = [
                os.path.join(self.path, 'silentsms'),
                feature,
                target
            ]
            
            # Add message for SMS/USSD
            if feature in ['SMS', 'USSD'] and message:
                cmd.extend(['-m', message])
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return {
                    'status': 'error',
                    'message': stderr.decode() if stderr else 'Unknown error'
                }
            
            # Parse output
            try:
                result = json.loads(stdout.decode())
                return {'status': 'success', 'data': result}
            except json.JSONDecodeError:
                return {
                    'status': 'success',
                    'data': stdout.decode()
                }
        except Exception as e:
            logger.error(f"SilentSMS execution failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    async def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate SilentSMS parameters"""
        try:
            # Required parameters
            required = ['feature', 'target']
            if not all(param in params for param in required):
                return False
            
            feature = params['feature'].upper()
            
            # Validate feature
            if feature not in self.supported_features:
                return False
            
            # Validate target
            if not self._validate_phone(params['target']):
                return False
            
            # Validate message for SMS/USSD
            if feature in ['SMS', 'USSD']:
                if not params.get('message'):
                    return False
                if len(params['message']) > 160:
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Parameter validation failed: {str(e)}")
            return False
    
    def _validate_phone(self, phone: str) -> bool:
        """Validate phone number format"""
        try:
            # Basic phone number validation
            if not phone.isdigit() or len(phone) < 10:
                return False
            return True
        except Exception:
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """Get SilentSMS information"""
        return {
            'name': 'SilentSMS',
            'version': '1.0',
            'description': 'SS7/GSM silent SMS/USSD/Call tool',
            'features': self.supported_features,
            'protocols': self.supported_protocols,
            'status': 'ready' if self.enabled else 'disabled'
        }
