from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import HTTPException, status


class RateLimiter:
    """Simple in-memory rate limiter for check-in endpoints."""
    
    def __init__(self):
        self._attempts: Dict[str, list] = {}
        self.max_attempts = 5
        self.window_seconds = 60
    
    def _get_key(self, identifier: str) -> str:
        return identifier
    
    def _clean_old_attempts(self, key: str) -> None:
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        if key in self._attempts:
            self._attempts[key] = [
                attempt for attempt in self._attempts[key]
                if attempt > cutoff
            ]
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed under rate limit."""
        key = self._get_key(identifier)
        self._clean_old_attempts(key)
        
        attempts = self._attempts.get(key, [])
        return len(attempts) < self.max_attempts
    
    def record_attempt(self, identifier: str) -> None:
        """Record an attempt."""
        key = self._get_key(identifier)
        
        if key not in self._attempts:
            self._attempts[key] = []
        
        self._attempts[key].append(datetime.utcnow())
    
    def check_rate_limit(self, identifier: str) -> None:
        """Check rate limit and raise exception if exceeded."""
        if not self.is_allowed(identifier):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please try again later."
            )
        self.record_attempt(identifier)


# Global rate limiter instance
checkin_rate_limiter = RateLimiter()
