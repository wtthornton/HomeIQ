"""
Simple in-memory cache for device mappings with TTL support.

Cache key format: device_mapping_{device_id}_{endpoint_type}
Cache TTL: 300 seconds (5 minutes)
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DeviceMappingCache:
    """
    Simple in-memory cache for device mappings with TTL.
    
    Cache entries expire after 5 minutes (300 seconds).
    """
    
    def __init__(self, ttl: int = 300):
        """
        Initialize the cache.
        
        Args:
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl
        logger.debug(f"Device mapping cache initialized with TTL={ttl}s")
    
    def get(self, key: str) -> Any | None:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key not in self._cache:
            return None
        
        value, timestamp = self._cache[key]
        current_time = time.time()
        
        # Check if entry has expired
        if current_time - timestamp > self._ttl:
            logger.debug(f"Cache entry expired: {key}")
            del self._cache[key]
            return None
        
        logger.debug(f"Cache hit: {key}")
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        current_time = time.time()
        self._cache[key] = (value, current_time)
        logger.debug(f"Cache set: {key}")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared: {count} entries removed")
    
    def invalidate(self, pattern: str | None = None) -> None:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Optional pattern to match keys (if None, clears all)
        """
        if pattern is None:
            self.clear()
            return
        
        keys_to_remove = [key for key in self._cache.keys() if pattern in key]
        for key in keys_to_remove:
            del self._cache[key]
        
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching pattern: {pattern}")
    
    def size(self) -> int:
        """Get the number of entries in the cache."""
        return len(self._cache)
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from the cache.
        
        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp > self._ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)


# Global cache instance
_cache: DeviceMappingCache | None = None


def get_cache() -> DeviceMappingCache:
    """Get or create the global device mapping cache."""
    global _cache
    if _cache is None:
        _cache = DeviceMappingCache(ttl=300)  # 5 minutes
    return _cache


def clear_cache() -> None:
    """Clear the global device mapping cache."""
    global _cache
    if _cache is not None:
        _cache.clear()

