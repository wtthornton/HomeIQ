"""
Entity Context Cache

Caches enriched entity data to reduce redundant API calls and token usage.
Uses in-memory cache with TTL (Time To Live) for efficient entity context reuse.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class EntityContextCache:
    """
    Cache for enriched entity context data.

    Reduces token usage by caching entity enrichment results for a configurable TTL.
    Entity data rarely changes during a session, making caching highly effective.
    """

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize entity context cache.

        Args:
            ttl_seconds: Time to live for cached entries in seconds (default: 5 minutes)
        """
        self.cache: dict[str, tuple[Any, datetime]] = {}
        self.ttl_seconds = ttl_seconds
        logger.info(f"EntityContextCache initialized with TTL={ttl_seconds}s")

    def _generate_key(self, entity_ids: set[str]) -> str:
        """
        Generate cache key from entity IDs.

        Args:
            entity_ids: Set of entity IDs

        Returns:
            Cache key string
        """
        # Sort entity IDs for consistent key generation
        sorted_ids = sorted(entity_ids)
        key_string = json.dumps(sorted_ids, sort_keys=True)
        # Use hash for shorter keys
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, entity_ids: set[str]) -> dict[str, Any] | None:
        """
        Get cached entity context for given entity IDs.

        Args:
            entity_ids: Set of entity IDs to look up

        Returns:
            Cached entity data dictionary or None if not found/expired
        """
        if not entity_ids:
            return None

        key = self._generate_key(entity_ids)

        if key not in self.cache:
            return None

        value, timestamp = self.cache[key]

        # Check if expired
        if datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds):
            logger.debug(f"Cache entry expired for key: {key[:8]}...")
            del self.cache[key]
            return None

        logger.debug(f"Cache hit for {len(entity_ids)} entities (key: {key[:8]}...)")
        return value

    def set(self, entity_ids: set[str], entity_data: dict[str, Any]) -> None:
        """
        Store entity context in cache.

        Args:
            entity_ids: Set of entity IDs being cached
            entity_data: Enriched entity data dictionary
        """
        if not entity_ids or not entity_data:
            return

        key = self._generate_key(entity_ids)
        self.cache[key] = (entity_data, datetime.now())

        logger.debug(f"Cached {len(entity_ids)} entities (key: {key[:8]}...)")

    def clear(self) -> None:
        """Clear all cached entries."""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cleared {count} cache entries")

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (size, hit rate, etc.)
        """
        total_entries = len(self.cache)
        expired_entries = 0
        valid_entries = 0

        now = datetime.now()
        for _key, (_value, timestamp) in self.cache.items():
            if now - timestamp > timedelta(seconds=self.ttl_seconds):
                expired_entries += 1
            else:
                valid_entries += 1

        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "ttl_seconds": self.ttl_seconds,
        }

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        now = datetime.now()
        expired_keys = [
            key for key, (value, timestamp) in self.cache.items()
            if now - timestamp > timedelta(seconds=self.ttl_seconds)
        ]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)


# Global cache instance
_entity_cache: EntityContextCache | None = None


def get_entity_cache(ttl_seconds: int = 300) -> EntityContextCache:
    """
    Get or create global entity context cache instance.

    Args:
        ttl_seconds: Time to live for cached entries

    Returns:
        EntityContextCache instance
    """
    global _entity_cache
    if _entity_cache is None:
        _entity_cache = EntityContextCache(ttl_seconds=ttl_seconds)
    return _entity_cache

