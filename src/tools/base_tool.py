from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger('C2Server')

class ToolInterface(ABC):
    """Base interface for all tools"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__
        self.enabled = config.get('enabled', True)
        self.timeout = config.get('timeout', 30)
        self.retries = config.get('retries', 3)
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the tool"""
        pass
    
    @abstractmethod
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run the tool with given parameters"""
        pass
    
    @abstractmethod
    async def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate input parameters"""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get tool information"""
        pass
    
    async def _make_request(self, url: str, params: Dict[str, Any] = None, 
                           headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Make a network request with error handling"""
        try:
            # TODO: Implement request with proper error handling
            return {'status': 'success', 'data': {}}
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def _validate_phone(self, phone: str) -> bool:
        """Validate phone number format"""
        try:
            # TODO: Implement phone validation
            return True
        except Exception as e:
            logger.error(f"Phone validation failed: {str(e)}")
            return False
    
    def _validate_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        try:
            # TODO: Implement IP validation
            return True
        except Exception as e:
            logger.error(f"IP validation failed: {str(e)}")
            return False
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.utcnow().isoformat()
    
    def _log(self, level: str, message: str):
        """Log messages with tool name"""
        logger.log(logging.getLevelName(level.upper()), 
                 f"[{self.name}] {message}")
