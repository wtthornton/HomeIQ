"""
Security Validation Utilities
Epic 50 Story 50.2: Security Hardening

Provides validation functions for WebSocket messages, rate limiting, and SSL configuration.
"""

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Constants
MAX_MESSAGE_SIZE = 64 * 1024  # 64KB
RATE_LIMIT_MESSAGES = 60  # messages per minute
RATE_LIMIT_WINDOW_SECONDS = 60  # 1 minute window


class RateLimiter:
    """
    Rate limiter for WebSocket connections.
    Tracks message count per connection per minute.
    """
    
    def __init__(self, max_messages: int = RATE_LIMIT_MESSAGES, window_seconds: int = RATE_LIMIT_WINDOW_SECONDS):
        """
        Initialize rate limiter.
        
        Args:
            max_messages: Maximum messages allowed per window
            window_seconds: Time window in seconds
        """
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        # Track message timestamps per connection (identified by client IP or connection ID)
        self._message_timestamps: dict[str, list[datetime]] = defaultdict(list)
        self._cleanup_interval = timedelta(minutes=5)  # Clean up old entries every 5 minutes
        self._last_cleanup = datetime.now(timezone.utc)
    
    def _cleanup_old_entries(self):
        """Remove old message timestamps outside the rate limit window"""
        now = datetime.now(timezone.utc)
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff_time = now - timedelta(seconds=self.window_seconds * 2)  # Keep 2x window for safety
        
        # Remove old timestamps
        for connection_id in list(self._message_timestamps.keys()):
            self._message_timestamps[connection_id] = [
                ts for ts in self._message_timestamps[connection_id]
                if ts > cutoff_time
            ]
            # Remove empty entries
            if not self._message_timestamps[connection_id]:
                del self._message_timestamps[connection_id]
        
        self._last_cleanup = now
    
    def check_rate_limit(self, connection_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if connection has exceeded rate limit.
        
        Args:
            connection_id: Unique identifier for the connection (e.g., client IP or correlation ID)
            
        Returns:
            Tuple of (allowed, error_message)
            - allowed: True if within rate limit, False if exceeded
            - error_message: Error message if rate limit exceeded, None otherwise
        """
        self._cleanup_old_entries()
        
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # Get timestamps for this connection
        timestamps = self._message_timestamps[connection_id]
        
        # Remove timestamps outside the window
        timestamps[:] = [ts for ts in timestamps if ts > window_start]
        
        # Check if limit exceeded
        if len(timestamps) >= self.max_messages:
            return False, f"Rate limit exceeded: {self.max_messages} messages per {self.window_seconds} seconds"
        
        # Add current timestamp
        timestamps.append(now)
        
        return True, None
    
    def reset(self, connection_id: str):
        """Reset rate limit for a specific connection"""
        if connection_id in self._message_timestamps:
            del self._message_timestamps[connection_id]


def validate_message_size(message: str) -> tuple[bool, Optional[str]]:
    """
    Validate WebSocket message size.
    
    Args:
        message: The message string to validate
        
    Returns:
        Tuple of (valid, error_message)
        - valid: True if message size is within limits, False otherwise
        - error_message: Error message if invalid, None otherwise
    """
    message_size = len(message.encode('utf-8'))
    
    if message_size > MAX_MESSAGE_SIZE:
        return False, f"Message size ({message_size} bytes) exceeds maximum allowed size ({MAX_MESSAGE_SIZE} bytes)"
    
    return True, None


def validate_message_json(message: str) -> tuple[bool, Optional[dict], Optional[str]]:
    """
    Validate WebSocket message JSON structure.
    
    Args:
        message: The message string to validate
        
    Returns:
        Tuple of (valid, parsed_data, error_message)
        - valid: True if message is valid JSON, False otherwise
        - parsed_data: Parsed JSON data if valid, None otherwise
        - error_message: Error message if invalid, None otherwise
    """
    try:
        parsed_data = json.loads(message)
        
        # Basic structure validation - ensure it's a dict/object
        if not isinstance(parsed_data, dict):
            return False, None, "Message must be a JSON object"
        
        return True, parsed_data, None
    
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON format: {str(e)}"


def get_ssl_config() -> bool:
    """
    Get SSL verification configuration from environment.
    
    Returns:
        True if SSL verification should be enabled, False otherwise
        Defaults to True (secure by default)
    """
    ssl_verify = os.getenv('SSL_VERIFY', 'true').lower()
    return ssl_verify in ('true', '1', 'yes', 'on')


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        max_messages = int(os.getenv('WEBSOCKET_RATE_LIMIT_MESSAGES', str(RATE_LIMIT_MESSAGES)))
        window_seconds = int(os.getenv('WEBSOCKET_RATE_LIMIT_WINDOW', str(RATE_LIMIT_WINDOW_SECONDS)))
        _rate_limiter = RateLimiter(max_messages=max_messages, window_seconds=window_seconds)
    return _rate_limiter

