import time
from datetime import datetime, timedelta
from typing import Optional

class RateLimiter:
    def __init__(self, calls_per_minute: int, max_attempts: int = 3, backoff_factor: float = 1, max_delay: int = 30):
        """
        Initialize the rate limiter.
        
        Args:
            calls_per_minute: Maximum number of calls allowed per minute
            max_attempts: Maximum number of retry attempts
            backoff_factor: Factor to multiply delay by for each retry
            max_delay: Maximum delay between retries in seconds
        """
        self.calls_per_minute = calls_per_minute
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        
        self.calls = 0
        self.last_call_time = datetime.now()
        self.current_delay = 0
        
    def check_limit(self) -> None:
        """
        Check if rate limit has been exceeded and sleep if necessary.
        
        Raises:
            RateLimitExceeded: If rate limit is exceeded and max attempts reached
        """
        current_time = datetime.now()
        time_since_last_call = (current_time - self.last_call_time).total_seconds()
        
        # Reset counter if we've passed a minute
        if time_since_last_call > 60:
            self.calls = 0
        
        # If we've reached our limit, calculate delay
        if self.calls >= self.calls_per_minute:
            delay = 60 - time_since_last_call
            if delay > 0:
                time.sleep(delay)
        
        # Update call count and timestamp
        self.calls += 1
        self.last_call_time = current_time
        
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for exponential backoff.
        
        Args:
            attempt: Current retry attempt number
            
        Returns:
            float: Delay in seconds
        """
        delay = min(
            self.backoff_factor * (2 ** attempt),
            self.max_delay
        )
        return delay
        
    def reset(self) -> None:
        """Reset the rate limiter state"""
        self.calls = 0
        self.last_call_time = datetime.now()
        self.current_delay = 0
