"""
Weather cache implementation used by websocket-ingestion tests.

The cache provides:
* Size-bounded storage with LRU eviction
* Per-entry TTL support
* Periodic cleanup task when started
* Basic statistics for observability
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any


class WeatherCache:
    """In-memory weather cache with TTL semantics and LRU eviction."""

    def __init__(self, max_size: int = 100, default_ttl: int = 300, cleanup_interval: int | None = None) -> None:
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval or default_ttl

        self.cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.total_requests = 0

        self.is_running = False
        self.cleanup_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the background cleanup task."""
        if self.is_running:
            return

        self.is_running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop the background cleanup task."""
        if not self.is_running:
            return

        self.is_running = False

        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            finally:
                self.cleanup_task = None

    async def put(self, key: str, data: Any, ttl: int | None = None) -> bool:
        """Insert or update a cache entry."""
        ttl_value = ttl if ttl is not None else self.default_ttl
        async with self._lock:
            if key in self.cache:
                # Update existing entry and move to the end
                self.cache.pop(key)
            elif len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
                self.evictions += 1

            self.cache[key] = {
                "data": data,
                "timestamp": self._utcnow().isoformat(),
                "ttl": ttl_value,
            }
            self.cache.move_to_end(key, last=True)
        return True

    async def get(self, key: str) -> Any | None:
        """Fetch data from cache if present and not expired."""
        self.total_requests += 1
        async with self._lock:
            entry = self.cache.get(key)
            if not entry:
                self.misses += 1
                return None

            if self._is_expired(entry):
                self.cache.pop(key, None)
                self.misses += 1
                return None

            self.cache.move_to_end(key, last=True)
            self.hits += 1
            return entry["data"]

    async def clear(self) -> None:
        """Remove all cache entries."""
        async with self._lock:
            self.cache.clear()

    async def clear_expired(self) -> None:
        """Remove only expired cache entries."""
        async with self._lock:
            expired_keys = [key for key, entry in self.cache.items() if self._is_expired(entry)]
            for key in expired_keys:
                self.cache.pop(key, None)

    def get_cache_keys(self) -> list[str]:
        """Return current cache keys."""
        return list(self.cache.keys())

    def get_cache_statistics(self) -> dict[str, Any]:
        """Return cache statistics."""
        hit_rate = 0.0
        if self.total_requests:
            hit_rate = round((self.hits / self.total_requests) * 100, 2)

        return {
            "max_size": self.max_size,
            "current_size": len(self.cache),
            "default_ttl": self.default_ttl,
            "cleanup_interval": self.cleanup_interval,
            "total_requests": self.total_requests,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": hit_rate,
        }

    def configure_max_size(self, max_size: int) -> None:
        """Update the maximum cache size and evict if necessary."""
        if max_size <= 0:
            msg = "max_size must be greater than zero"
            raise ValueError(msg)
        self.max_size = max_size
        while len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
            self.evictions += 1

    def configure_ttl(self, ttl_seconds: int) -> None:
        """Set the default TTL for new entries."""
        if ttl_seconds <= 0:
            msg = "ttl_seconds must be greater than zero"
            raise ValueError(msg)
        self.default_ttl = ttl_seconds

    def configure_cleanup_interval(self, interval_seconds: int) -> None:
        """Set the cleanup interval for background task."""
        if interval_seconds <= 0:
            msg = "interval_seconds must be greater than zero"
            raise ValueError(msg)
        self.cleanup_interval = interval_seconds

    def reset_statistics(self) -> None:
        """Reset cache statistics counters."""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.total_requests = 0

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup loop."""
        try:
            while self.is_running:
                await asyncio.sleep(self.cleanup_interval)
                await self.clear_expired()
        except asyncio.CancelledError:
            # Task cancelled during shutdown
            pass

    def _is_expired(self, entry: dict[str, Any]) -> bool:
        """Determine if an entry has expired."""
        timestamp = self._parse_timestamp(entry["timestamp"])
        ttl = entry.get("ttl", self.default_ttl)
        return timestamp + timedelta(seconds=ttl) <= self._utcnow()

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        """Parse ISO timestamp values saved in the cache."""
        return datetime.fromisoformat(value)

    @staticmethod
    def _utcnow() -> datetime:
        """Return timezone-aware UTC now."""
        return datetime.now(timezone.utc)


