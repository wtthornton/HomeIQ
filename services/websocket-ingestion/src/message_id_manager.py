"""
Centralized Message ID Manager for WebSocket Messages

Ensures all WebSocket messages use strictly increasing IDs to prevent
Home Assistant 'id_reuse' errors.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MessageIDManager:
    """
    Centralized message ID manager for WebSocket messages.
    
    Home Assistant requires message IDs to be strictly increasing across
    all WebSocket messages. This singleton ensures all components use
    the same counter.
    """
    _instance: Optional['MessageIDManager'] = None
    _lock: Optional[asyncio.Lock] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the message ID manager (only once)"""
        if self._initialized:
            return
        
        # Start at 1 to avoid conflicts with Home Assistant internal IDs
        # Use a higher starting point to avoid conflicts with other services
        self._counter = 1
        self._lock = asyncio.Lock()
        self._initialized = True
        logger.info("MessageIDManager initialized with counter starting at 1")
    
    async def get_next_id(self) -> int:
        """
        Get the next message ID (thread-safe).
        
        Returns:
            Next available message ID (strictly increasing)
        """
        async with self._lock:
            self._counter += 1
            message_id = self._counter
            logger.debug(f"Generated message ID: {message_id}")
            return message_id
    
    def get_next_id_sync(self) -> int:
        """
        Get the next message ID synchronously (for non-async contexts).
        
        Note: This should only be used when async is not available.
        Prefer get_next_id() for async code.
        
        Returns:
            Next available message ID (strictly increasing)
        """
        # Create lock if it doesn't exist (for sync contexts)
        if self._lock is None:
            self._lock = asyncio.Lock()
        
        # Use asyncio.run if we're in a sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we need to use a different approach
                # For now, just increment (not thread-safe in sync context)
                # This is a fallback - prefer async usage
                self._counter += 1
                return self._counter
            else:
                return loop.run_until_complete(self.get_next_id())
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self.get_next_id())
    
    def reset(self, start_value: int = 1):
        """
        Reset the counter (use with caution).
        
        Args:
            start_value: Starting value for the counter (default: 1)
        """
        self._counter = start_value
        logger.warning(f"MessageIDManager counter reset to {start_value}")
    
    def get_current_id(self) -> int:
        """
        Get the current counter value (without incrementing).
        
        Returns:
            Current counter value
        """
        return self._counter


# Global singleton instance
_message_id_manager: Optional[MessageIDManager] = None


def get_message_id_manager() -> MessageIDManager:
    """
    Get the global MessageIDManager instance.
    
    Returns:
        MessageIDManager singleton instance
    """
    global _message_id_manager
    if _message_id_manager is None:
        _message_id_manager = MessageIDManager()
    return _message_id_manager

