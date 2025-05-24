import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from src.databases.database_manager import DatabaseManager
from src.config.config_loader import config_loader

logger = logging.getLogger('C2Server')

class SessionManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.config = config_loader.get_section('agent')
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._cleanup_interval = 60  # seconds
        self._cleanup_thread = None
        self._start_cleanup()

    def _start_cleanup(self) -> None:
        """Start session cleanup thread"""
        import threading
        def cleanup():
            while True:
                self._cleanup_expired_sessions()
                import time
                time.sleep(self._cleanup_interval)
        
        self._cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        self._cleanup_thread.start()

    def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions"""
        now = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session in list(self.sessions.items()):
            if now - session['last_seen'] > timedelta(seconds=self.config['timeout']):
                expired_sessions.append(session_id)
                
        for session_id in expired_sessions:
            self._end_session(session_id)

    def start_session(self, device_id: str, device_info: Dict[str, Any]) -> str:
        """Start a new session for a device"""
        session_id = self._generate_session_id()
        session = {
            'session_id': session_id,
            'device_id': device_id,
            'device_info': device_info,
            'status': 'active',
            'last_seen': datetime.utcnow(),
            'commands': [],
            'results': {}
        }
        
        self.sessions[session_id] = session
        self._save_session(session)
        return session_id

    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        import uuid
        return str(uuid.uuid4())

    def _save_session(self, session: Dict[str, Any]) -> None:
        """Save session to database"""
        try:
            self.db_manager.insert('sessions', session)
        except Exception as e:
            logger.error(f"Failed to save session: {str(e)}")

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        return self.sessions.get(session_id)

    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update session information"""
        session = self.sessions.get(session_id)
        if not session:
            return False
            
        session.update(data)
        session['last_seen'] = datetime.utcnow()
        self._save_session(session)
        return True

    def _end_session(self, session_id: str) -> None:
        """End a session"""
        session = self.sessions.pop(session_id, None)
        if session:
            session['status'] = 'ended'
            session['end_time'] = datetime.utcnow()
            self._save_session(session)

    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get device status across all sessions"""
        status = {
            'device_id': device_id,
            'active_sessions': 0,
            'last_seen': None,
            'status': 'offline',
            'protocols': set()
        }
        
        for session in self.sessions.values():
            if session['device_id'] == device_id:
                status['active_sessions'] += 1
                if not status['last_seen'] or session['last_seen'] > status['last_seen']:
                    status['last_seen'] = session['last_seen']
                status['protocols'].update(session['device_info'].get('protocols', []))
        
        if status['active_sessions'] > 0:
            status['status'] = 'online'
        
        return status
