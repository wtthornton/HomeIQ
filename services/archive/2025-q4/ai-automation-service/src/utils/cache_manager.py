"""
Cache Management Utilities

Epic 39, Story 39.15: Performance Optimization
Centralized cache management for consistent cache usage across services.
"""

import logging
from typing import Any, Optional
from functools import wraps

from shared.correlation_cache import CorrelationCache
from ..utils.performance import get_performance_monitor

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Centralized cache manager for consistent cache usage.
    
    Provides a unified interface for caching across services.
    """
    
    def __init__(
        self,
        correlation_cache: Optional[CorrelationCache] = None,
        default_ttl: int = 3600
    ):
        """
        Initialize cache manager.
        
        Args:
            correlation_cache: Optional CorrelationCache instance
            default_ttl: Default TTL in seconds
        """
        self.correlation_cache = correlation_cache
        self.default_ttl = default_ttl
        self._caches: dict[str, Any] = {}
        
        # In-memory cache for general use
        self._memory_cache: dict[str, dict[str, Any]] = {}
    
    def get_correlation_cache(self) -> Optional[CorrelationCache]:
        """Get correlation cache instance."""
        return self.correlation_cache
    
    def get_from_cache(
        self,
        cache_key: str,
        cache_type: str = "memory"
    ) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            cache_key: Cache key
            cache_type: Cache type ("memory" or "correlation")
        
        Returns:
            Cached value or None
        """
        monitor = get_performance_monitor()
        
        if cache_type == "correlation" and self.correlation_cache:
            # Parse correlation cache key (entity1_id:entity2_id)
            if ":" in cache_key:
                entity1_id, entity2_id = cache_key.split(":", 1)
                result = self.correlation_cache.get(entity1_id, entity2_id, self.default_ttl)
                if result is not None:
                    monitor.record_cache_hit("correlation")
                    return result
                else:
                    monitor.record_cache_miss("correlation")
            return None
        
        # Memory cache
        if cache_key in self._memory_cache:
            cached = self._memory_cache[cache_key]
            # Check TTL
            import time
            if time.time() < cached.get("expires_at", 0):
                monitor.record_cache_hit("memory")
                return cached["value"]
            else:
                del self._memory_cache[cache_key]
        
        monitor.record_cache_miss("memory")
        return None
    
    def set_in_cache(
        self,
        cache_key: str,
        value: Any,
        ttl: Optional[int] = None,
        cache_type: str = "memory"
    ):
        """
        Set value in cache.
        
        Args:
            cache_key: Cache key
            value: Value to cache
            ttl: TTL in seconds (default: self.default_ttl)
            cache_type: Cache type ("memory" or "correlation")
        """
        if ttl is None:
            ttl = self.default_ttl
        
        if cache_type == "correlation" and self.correlation_cache:
            # Parse correlation cache key (entity1_id:entity2_id)
            if ":" in cache_key:
                entity1_id, entity2_id = cache_key.split(":", 1)
                self.correlation_cache.set(entity1_id, entity2_id, value, ttl)
            return
        
        # Memory cache
        import time
        self._memory_cache[cache_key] = {
            "value": value,
            "expires_at": time.time() + ttl
        }
    
    def clear_cache(self, cache_type: Optional[str] = None):
        """
        Clear cache.
        
        Args:
            cache_type: Cache type to clear (None = all)
        """
        if cache_type == "correlation" and self.correlation_cache:
            self.correlation_cache.clear()
        elif cache_type == "memory":
            self._memory_cache.clear()
        elif cache_type is None:
            # Clear all
            if self.correlation_cache:
                self.correlation_cache.clear()
            self._memory_cache.clear()
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "memory_cache_size": len(self._memory_cache),
            "correlation_cache": None
        }
        
        if self.correlation_cache:
            stats["correlation_cache"] = self.correlation_cache.get_stats()
        
        return stats


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(ttl: int = 3600, cache_key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Usage:
        @cached(ttl=3600, cache_key_prefix="query")
        async def expensive_query(param):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            import hashlib
            import json
            
            # Generate cache key
            key_data = {
                "prefix": cache_key_prefix or func.__name__,
                "args": str(args),
                "kwargs": json.dumps(kwargs, sort_keys=True, default=str)
            }
            cache_key = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
            
            # Try cache
            cache_manager = get_cache_manager()
            cached_result = cache_manager.get_from_cache(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}: {cache_key[:8]}")
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache_manager.set_in_cache(cache_key, result, ttl)
            logger.debug(f"Cached result for {func.__name__}: {cache_key[:8]}")
            
            return result
        
        return async_wrapper
    
    return decorator

