"""
Simple in-memory cache for frequently accessed data
Provides TTL-based caching to reduce database queries

Uses shared cache base class from shared/cache.py
"""

import logging
from typing import Any

from homeiq_data.cache import BaseCache

logger = logging.getLogger(__name__)


class SimpleCache(BaseCache):
    """
    Simple in-memory cache with TTL support

    Features:
    - TTL-based expiration
    - Automatic cleanup of expired entries
    - Thread-safe operations
    - LRU eviction when max size reached

    Inherits from shared BaseCache for consistency.
    """

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Initialize cache

        Args:
            default_ttl: Default TTL in seconds (default: 5 minutes)
            max_size: Maximum cache entries before eviction
        """
        super().__init__(default_ttl=default_ttl, max_size=max_size)

        # Backward compatibility: expose stats as instance variables
        # These will be kept in sync with self.stats
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    async def get(self, key: str) -> Any | None:
        """Get value from cache (overrides to sync instance variables)"""
        result = await super().get(key)
        # Sync instance variables for backward compatibility
        self.hits = self.stats.hits
        self.misses = self.stats.misses
        return result

    async def set(self, key: str, value: Any, ttl: int | None = None):
        """Set value in cache (overrides to sync instance variables)"""
        result = await super().set(key, value, ttl)
        # Sync instance variables for backward compatibility
        self.evictions = self.stats.evictions
        return result

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics (backward compatibility method)

        Returns:
            Dictionary with cache stats
        """
        return super().get_stats()


# Global cache instance (5 minute TTL, 1000 entries max)
cache = SimpleCache(default_ttl=300, max_size=1000)
