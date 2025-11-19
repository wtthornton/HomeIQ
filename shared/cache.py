"""
Shared Cache Base Class

Provides base cache implementation with TTL, LRU eviction, and statistics.
All service caches should inherit from this base class for consistency.
"""

import asyncio
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from collections import OrderedDict
from abc import ABC, abstractmethod

import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheStatistics:
    """Cache statistics dataclass"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class BaseCache(ABC):
    """
    Base cache class with TTL and statistics.
    
    Features:
    - TTL-based expiration
    - LRU eviction
    - Statistics tracking
    - Thread-safe operations
    """
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Initialize base cache.
        
        Args:
            default_ttl: Default TTL in seconds (default: 5 minutes)
            max_size: Maximum cache entries before eviction
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self.stats = CacheStatistics(max_size=max_size)
        self._lock = asyncio.Lock()
        
        logger.info(f"Cache initialized: TTL={default_ttl}s, max_size={max_size}")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            if key not in self.cache:
                self.stats.misses += 1
                return None
            
            value, expiry = self.cache[key]
            current_time = time.time()
            
            if expiry > current_time:
                # Move to end (LRU)
                self.cache.move_to_end(key)
                self.stats.hits += 1
                return value
            else:
                # Expired, remove it
                del self.cache[key]
                self.stats.misses += 1
                return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override (seconds)
            
        Returns:
            True if successful
        """
        async with self._lock:
            try:
                ttl = ttl or self.default_ttl
                expiry = time.time() + ttl
                
                # Remove if already exists
                if key in self.cache:
                    del self.cache[key]
                
                # Add new entry
                self.cache[key] = (value, expiry)
                
                # Evict if over max size (LRU - remove oldest)
                while len(self.cache) > self.max_size:
                    self.cache.popitem(last=False)  # Remove oldest
                    self.stats.evictions += 1
                
                self.stats.size = len(self.cache)
                return True
                
            except Exception as e:
                logger.error(f"Cache set error for key {key}: {e}")
                return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted, False if not found
        """
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                self.stats.size = len(self.cache)
                return True
            return False
    
    async def clear(self):
        """Clear all cache entries"""
        async with self._lock:
            self.cache.clear()
            self.stats.size = 0
            self.stats.hits = 0
            self.stats.misses = 0
            self.stats.evictions = 0
            logger.info("Cache cleared")
    
    def get_statistics(self) -> CacheStatistics:
        """
        Get cache statistics.
        
        Returns:
            CacheStatistics object with current stats
        """
        self.stats.size = len(self.cache)
        return self.stats
    
    async def cleanup_expired(self) -> int:
        """
        Remove expired entries, return count removed.
        
        Returns:
            Number of expired entries removed
        """
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, (_, expiry) in self.cache.items()
                if expiry <= current_time
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            self.stats.size = len(self.cache)
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics as dictionary (for backward compatibility).
        
        Returns:
            Dictionary with cache stats
        """
        stats = self.get_statistics()
        total_requests = stats.hits + stats.misses
        hit_rate_percent = stats.hit_rate * 100
        
        return {
            "size": stats.size,
            "max_size": stats.max_size,
            "hits": stats.hits,
            "misses": stats.misses,
            "hit_rate_percent": round(hit_rate_percent, 2),
            "hit_rate": round(stats.hit_rate, 4),
            "evictions": stats.evictions,
            "default_ttl_seconds": self.default_ttl
        }

