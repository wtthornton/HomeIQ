"""
Device Intelligence Service - In-Memory Cache Service

Simple in-memory cache with TTL support for device data.
Follows the same pattern as sports-data service.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List
from collections import OrderedDict

logger = logging.getLogger(__name__)


class DeviceCache:
    """Simple in-memory cache with TTL support for device data."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        async with self._lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                current_time = time.time()
                
                if expiry > current_time:
                    # Move to end (LRU)
                    self.cache.move_to_end(key)
                    self.hits += 1
                    return value
                else:
                    # Expired, remove it
                    del self.cache[key]
                    self.misses += 1
            else:
                self.misses += 1
            
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL in seconds."""
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
                    self.evictions += 1
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Cache set error for key {key}: {e}")
                return False
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    async def clear(self):
        """Clear all cache."""
        async with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed items."""
        async with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, (value, expiry) in self.cache.items():
                if expiry <= current_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
            
            return len(expired_keys)
    
    def is_connected(self) -> bool:
        """Check if cache is available (always true for in-memory)."""
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_type": "in_memory",
            "hit_count": self.hits,
            "miss_count": self.misses,
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 2),
            "current_size": len(self.cache),
            "max_size": self.max_size,
            "evictions": self.evictions,
            "memory_usage": f"{len(self.cache)} entries",
            "connected": True
        }
    
    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device from cache."""
        key = f"device:{device_id}"
        return await self.get(key)
    
    async def set_device(self, device_id: str, device_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set device in cache."""
        key = f"device:{device_id}"
        return await self.set(key, device_data, ttl)
    
    async def invalidate_device(self, device_id: str) -> bool:
        """Invalidate device cache."""
        key = f"device:{device_id}"
        return await self.delete(key)
    
    async def get_devices_by_area(self, area_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get devices by area from cache."""
        key = f"devices:area:{area_id}"
        return await self.get(key)
    
    async def set_devices_by_area(self, area_id: str, devices: List[Dict[str, Any]], ttl: Optional[int] = None) -> bool:
        """Set devices by area in cache."""
        key = f"devices:area:{area_id}"
        return await self.set(key, devices, ttl)
    
    async def get_devices_by_integration(self, integration: str) -> Optional[List[Dict[str, Any]]]:
        """Get devices by integration from cache."""
        key = f"devices:integration:{integration}"
        return await self.get(key)
    
    async def set_devices_by_integration(self, integration: str, devices: List[Dict[str, Any]], ttl: Optional[int] = None) -> bool:
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
_device_cache: Optional[DeviceCache] = None


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
