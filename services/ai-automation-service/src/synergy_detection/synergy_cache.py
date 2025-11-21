"""
Synergy Cache Service

Simple cache for synergy queries using DeviceCache pattern.
Reuses existing cache implementation from device-intelligence-service.

Epic AI-3 Enhancement: Simple Synergy Detection Improvements
"""

import asyncio
import logging
import time
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)


class DeviceCache:
    """
    Simple in-memory cache with TTL support.

    Reuses pattern from device-intelligence-service DeviceCache.
    """
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """Get value from cache if not expired."""
        async with self._lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                current_time = time.time()
                if expiry > current_time:
                    # Move to end (LRU)
                    self.cache.move_to_end(key)
                    return value
                # Expired, remove it
                del self.cache[key]
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in cache with TTL."""
        async with self._lock:
            try:
                expiry = time.time() + (ttl or self.default_ttl)
                # Remove if already exists
                if key in self.cache:
                    del self.cache[key]
                # Add new entry
                self.cache[key] = (value, expiry)
                # Evict if over max size
                while len(self.cache) > self.max_size:
                    self.cache.popitem(last=False)  # Remove oldest
                return True
            except Exception as e:
                logger.exception(f"Cache set error for key {key}: {e}")
                return False


class SynergyCache:
    """Simple cache for synergy queries - reuses DeviceCache pattern"""

    def __init__(self):
        """Initialize synergy cache with TTL-based caches."""
        # Reuse existing pattern
        self._pair_cache = DeviceCache(max_size=500, default_ttl=300)  # 5 min
        self._usage_cache = DeviceCache(max_size=1000, default_ttl=600)  # 10 min
        self._chain_cache = DeviceCache(max_size=200, default_ttl=300)  # 5 min

        logger.info("SynergyCache initialized (reusing DeviceCache pattern)")

    async def get_pair_result(self, device1: str, device2: str) -> Any | None:
        """Get cached pair result."""
        key = f"pair:{device1}:{device2}"
        return await self._pair_cache.get(key)

    async def set_pair_result(self, device1: str, device2: str, result: Any):
        """Cache pair result."""
        key = f"pair:{device1}:{device2}"
        await self._pair_cache.set(key, result)

    async def get_chain_result(self, chain_key: str) -> Any | None:
        """Get cached chain result."""
        return await self._chain_cache.get(chain_key)

    async def set_chain_result(self, chain_key: str, result: Any):
        """Cache chain result."""
        await self._chain_cache.set(chain_key, result)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "pair_cache_size": len(self._pair_cache.cache),
            "usage_cache_size": len(self._usage_cache.cache),
            "chain_cache_size": len(self._chain_cache.cache),
        }

    async def clear(self):
        """Clear all caches."""
        # Clear by recreating
        self._pair_cache = DeviceCache(max_size=500, default_ttl=300)
        self._usage_cache = DeviceCache(max_size=1000, default_ttl=600)
        self._chain_cache = DeviceCache(max_size=200, default_ttl=300)
        logger.debug("SynergyCache cleared")

