"""
Device Intelligence Service - In-Memory Cache Service

Simple in-memory cache with TTL support for device data.
Uses shared cache base class from shared/cache.py
"""

import os
import sys
from pathlib import Path
from typing import Any

# Add shared directory to path for imports
shared_path_override = os.getenv('HOMEIQ_SHARED_PATH')
try:
    app_root = Path(__file__).resolve().parents[4]  # Go up to project root
except Exception:
    app_root = Path("/app")

candidate_paths = []
if shared_path_override:
    candidate_paths.append(Path(shared_path_override).expanduser())
candidate_paths.extend([
    app_root / "shared",
    Path("/app/shared"),
    Path.cwd() / "shared",
    Path(__file__).parent.parent.parent.parent.parent / "shared",  # Fallback for local dev
])

shared_path = None
for p in candidate_paths:
    if p.exists():
        shared_path = p.resolve()
        break

if shared_path and str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

import logging

from cache import BaseCache

logger = logging.getLogger(__name__)


class DeviceCache(BaseCache):
    """Simple in-memory cache with TTL support for device data."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize device cache.
        
        Args:
            max_size: Maximum cache entries
            default_ttl: Default TTL in seconds
        """
        # Note: BaseCache expects (default_ttl, max_size) but DeviceCache uses (max_size, default_ttl)
        super().__init__(default_ttl=default_ttl, max_size=max_size)

        # Backward compatibility: expose stats as instance variables
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

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in cache (overrides to sync instance variables)"""
        result = await super().set(key, value, ttl)
        # Sync instance variables for backward compatibility
        self.evictions = self.stats.evictions
        return result

    def is_connected(self) -> bool:
        """Check if cache is available (always true for in-memory)."""
        return True

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics (extended version with device-specific fields)."""
        base_stats = super().get_stats()
        total_requests = self.stats.hits + self.stats.misses

        return {
            "cache_type": "in_memory",
            "hit_count": self.stats.hits,
            "miss_count": self.stats.misses,
            "total_requests": total_requests,
            "hit_rate": round(self.stats.hit_rate * 100, 2),
            "current_size": self.stats.size,
            "max_size": self.stats.max_size,
            "evictions": self.stats.evictions,
            "memory_usage": f"{self.stats.size} entries",
            "connected": True,
            **base_stats  # Include base stats for compatibility
        }

    async def get_device(self, device_id: str) -> dict[str, Any] | None:
        """Get device from cache."""
        key = f"device:{device_id}"
        return await self.get(key)

    async def set_device(self, device_id: str, device_data: dict[str, Any], ttl: int | None = None) -> bool:
        """Set device in cache."""
        key = f"device:{device_id}"
        return await self.set(key, device_data, ttl)

    async def invalidate_device(self, device_id: str) -> bool:
        """Invalidate device cache."""
        key = f"device:{device_id}"
        return await self.delete(key)

    async def get_devices_by_area(self, area_id: str) -> list[dict[str, Any]] | None:
        """Get devices by area from cache."""
        key = f"devices:area:{area_id}"
        return await self.get(key)

    async def set_devices_by_area(self, area_id: str, devices: list[dict[str, Any]], ttl: int | None = None) -> bool:
        """Set devices by area in cache."""
        key = f"devices:area:{area_id}"
        return await self.set(key, devices, ttl)

    async def get_devices_by_integration(self, integration: str) -> list[dict[str, Any]] | None:
        """Get devices by integration from cache."""
        key = f"devices:integration:{integration}"
        return await self.get(key)

    async def set_devices_by_integration(self, integration: str, devices: list[dict[str, Any]], ttl: int | None = None) -> bool:
        """Set devices by integration in cache."""
        key = f"devices:integration:{integration}"
        return await self.set(key, devices, ttl)

    async def invalidate_area_cache(self, area_id: str) -> bool:
        """Invalidate area-related cache."""
        key = f"devices:area:{area_id}"
        return await self.delete(key)

    async def invalidate_integration_cache(self, integration: str) -> bool:
        """Invalidate integration-related cache."""
        key = f"devices:integration:{integration}"
        return await self.delete(key)

    async def invalidate_all_device_cache(self):
        """Invalidate all device-related cache entries."""
        async with self._lock:
            keys_to_delete = []
            for key in self.cache.keys():
                if key.startswith("device:") or key.startswith("devices:"):
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self.cache[key]


# Global cache instance
_device_cache: DeviceCache | None = None


def get_device_cache() -> DeviceCache:
    """Get the global device cache instance."""
    global _device_cache

    if _device_cache is None:
        # For single-home deployment: 6-hour TTL with max 500 devices
        _device_cache = DeviceCache(max_size=500, default_ttl=21600)  # 6 hours
        logger.info("📦 Device cache initialized with 6-hour TTL")

    return _device_cache


async def start_cache_cleanup_task():
    """Start background task to clean up expired cache entries."""
    cache = get_device_cache()

    async def cleanup_loop():
        while True:
            try:
                await asyncio.sleep(60)  # Clean up every minute
                expired_count = await cache.cleanup_expired()
                if expired_count > 0:
                    logger.debug(f"🧹 Cleaned up {expired_count} expired cache entries")
            except Exception as e:
                logger.error(f"❌ Cache cleanup error: {e}")

    # Start cleanup task
    asyncio.create_task(cleanup_loop())
    logger.info("🧹 Cache cleanup task started")
