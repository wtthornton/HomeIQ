"""
Simple in-memory cache for frequently accessed data
Provides TTL-based caching to reduce database queries
"""

import logging
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with TTL"""
    value: Any
    expires_at: datetime


class SimpleCache:
    """
    Simple in-memory cache with TTL support

    Features:
    - TTL-based expiration
    - Automatic cleanup of expired entries
    - Thread-safe operations
    - LRU eviction when max size reached
    """

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Initialize cache

        Args:
            default_ttl: Default TTL in seconds (default: 5 minutes)
            max_size: Maximum cache entries before eviction
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        logger.info(f"Cache initialized: TTL={default_ttl}s, max_size={max_size}")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None

            entry = self._cache[key]

            # Check if expired
            if datetime.now() >= entry.expires_at:
                del self._cache[key]
                self.misses += 1
                return None

            self.hits += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override (seconds)
        """
        async with self._lock:
            # Evict oldest entry if at max size
            if len(self._cache) >= self.max_size:
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].expires_at
                )
                del self._cache[oldest_key]
                self.evictions += 1

            expires_at = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    async def delete(self, key: str):
        """Delete key from cache"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]

    async def clear(self):
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    async def cleanup_expired(self):
        """Remove all expired entries"""
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now >= entry.expires_at
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_percent": round(hit_rate, 2),
            "evictions": self.evictions,
            "default_ttl_seconds": self.default_ttl
        }


# Global cache instance (5 minute TTL, 1000 entries max)
cache = SimpleCache(default_ttl=300, max_size=1000)
