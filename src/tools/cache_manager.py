import asyncio
import logging
from typing import Dict, Any, Optional
import time
from datetime import datetime
import json
from functools import lru_cache
from threading import Lock

class CacheManager:
    def __init__(self, config: Dict[str, Any]):
        """Initialize cache manager"""
        self.config = config
        self.ttl = config.get('ttl', 3600)  # Default 1 hour
        self.max_size = config.get('max_size', 1000)
        self.cache = {}
        self.lock = Lock()
        self.cleanup_interval = 300  # 5 minutes
        self.cleanup_task = None
        
        # Start cleanup task
        self._start_cleanup()
    
    def _start_cleanup(self):
        """Start periodic cache cleanup"""
        async def cleanup():
            while True:
                await self._cleanup_expired()
                await asyncio.sleep(self.cleanup_interval)
        
        self.cleanup_task = asyncio.create_task(cleanup())
    
    async def _cleanup_expired(self):
        """Remove expired cache entries"""
        try:
            current_time = time.time()
            expired_keys = []
            
            with self.lock:
                for key, (value, timestamp) in self.cache.items():
                    if current_time - timestamp > self.ttl:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.cache[key]
                    
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        except Exception as e:
            logger.error(f"Cache cleanup failed: {str(e)}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            with self.lock:
                if key in self.cache:
                    value, timestamp = self.cache[key]
                    current_time = time.time()
                    
                    # Check if expired
                    if current_time - timestamp > self.ttl:
                        del self.cache[key]
                        return None
                    
                    return value
            return None
        except Exception as e:
            logger.error(f"Failed to get from cache: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        try:
            with self.lock:
                # Check cache size
                if len(self.cache) >= self.max_size:
                    self._evict_oldest()
                
                # Store with timestamp
                self.cache[key] = (value, time.time())
                logger.info(f"Cached value for key: {key}")
        except Exception as e:
            logger.error(f"Failed to set cache: {str(e)}")
    
    def _evict_oldest(self):
        """Evict oldest cache entry"""
        try:
            with self.lock:
                if not self.cache:
                    return
                
                # Find oldest entry
                oldest_key = min(
                    self.cache,
                    key=lambda k: self.cache[k][1]
                )
                del self.cache[oldest_key]
                logger.info(f"Evicted oldest cache entry: {oldest_key}")
        except Exception as e:
            logger.error(f"Failed to evict oldest cache entry: {str(e)}")
    
    async def delete(self, key: str):
        """Delete value from cache"""
        try:
            with self.lock:
                if key in self.cache:
                    del self.cache[key]
                    logger.info(f"Deleted cache entry: {key}")
        except Exception as e:
            logger.error(f"Failed to delete from cache: {str(e)}")
    
    async def clear(self):
        """Clear entire cache"""
        try:
            with self.lock:
                self.cache.clear()
                logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")
    
    def cache_decorator(self, ttl: Optional[int] = None):
        """Decorator for caching function results"""
        def decorator(func):
            @lru_cache(maxsize=self.max_size)
            async def wrapper(*args, **kwargs):
                # Generate cache key based on function arguments
                key = self._generate_cache_key(func.__name__, args, kwargs)
                
                # Check cache
                cached_result = await self.get(key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self.set(key, result, ttl)
                return result
            
            return wrapper
        return decorator
    
    def _generate_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate unique cache key for function arguments"""
        try:
            # Convert arguments to string
            args_str = json.dumps(args)
            kwargs_str = json.dumps(kwargs, sort_keys=True)
            
            # Create key using function name and arguments
            return f"{func_name}:{args_str}:{kwargs_str}"
        except Exception as e:
            logger.error(f"Failed to generate cache key: {str(e)}")
            return f"{func_name}:error"
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            with self.lock:
                return {
                    'size': len(self.cache),
                    'max_size': self.max_size,
                    'ttl': self.ttl,
                    'cleanup_interval': self.cleanup_interval,
                    'last_cleanup': datetime.fromtimestamp(
                        max(entry[1] for entry in self.cache.values())
                    ).isoformat() if self.cache else None
                }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {'error': str(e)}
    
    async def set_config(self, config: Dict[str, Any]):
        """Update cache configuration"""
        try:
            with self.lock:
                self.ttl = config.get('ttl', self.ttl)
                self.max_size = config.get('max_size', self.max_size)
                self.cleanup_interval = config.get('cleanup_interval', self.cleanup_interval)
                
                # Clear cache if size changed
                if 'max_size' in config:
                    await self.clear()
                
                logger.info(f"Cache config updated: {config}")
        except Exception as e:
            logger.error(f"Failed to update cache config: {str(e)}")
            raise
