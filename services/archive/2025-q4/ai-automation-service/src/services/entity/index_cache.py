"""
Index Cache

Epic AI-12, Story AI12.10: Performance Optimization & Caching
Caches built personalized entity indexes to avoid rebuilding on every request.
Uses singleton pattern with optional persistence.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
import threading

from .personalized_index import PersonalizedEntityIndex

logger = logging.getLogger(__name__)


class IndexCache:
    """
    Cache for built personalized entity indexes.
    
    Features:
    - Singleton pattern (one index per user/system)
    - Thread-safe
    - Optional TTL (time-to-live) for cache entries
    - Incremental updates (no full rebuild)
    """
    
    _instance: Optional['IndexCache'] = None
    _lock = threading.Lock()
    
    def __init__(self, ttl_seconds: Optional[int] = None):
        """
        Initialize index cache.
        
        Args:
            ttl_seconds: Optional TTL in seconds (None = no expiration)
        """
        self.ttl_seconds = ttl_seconds
        
        # Cached index: user_id -> (index, timestamp)
        self._cache: dict[str, tuple[PersonalizedEntityIndex, datetime]] = {}
        
        # Lock for thread safety
        self._cache_lock = threading.Lock()
        
        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "builds": 0,
            "updates": 0
        }
        
        logger.info(f"IndexCache initialized (ttl={ttl_seconds})")
    
    @classmethod
    def get_instance(cls, ttl_seconds: Optional[int] = None) -> 'IndexCache':
        """
        Get singleton instance.
        
        Args:
            ttl_seconds: Optional TTL in seconds (only used on first creation)
        
        Returns:
            IndexCache singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(ttl_seconds=ttl_seconds)
        return cls._instance
    
    def get(
        self,
        user_id: str = "default",
        force_rebuild: bool = False
    ) -> Optional[PersonalizedEntityIndex]:
        """
        Get cached index for user.
        
        Args:
            user_id: User ID (default: "default" for single-home)
            force_rebuild: If True, force rebuild (ignore cache)
        
        Returns:
            Cached index if found and valid, None otherwise
        """
        with self._cache_lock:
            if force_rebuild or user_id not in self._cache:
                self._stats["misses"] += 1
                return None
            
            index, timestamp = self._cache[user_id]
            
            # Check TTL
            if self.ttl_seconds:
                age = (datetime.now() - timestamp).total_seconds()
                if age > self.ttl_seconds:
                    # Expired - remove from cache
                    del self._cache[user_id]
                    self._stats["misses"] += 1
                    return None
            
            self._stats["hits"] += 1
            return index
    
    def put(
        self,
        index: PersonalizedEntityIndex,
        user_id: str = "default"
    ) -> None:
        """
        Cache index for user.
        
        Args:
            index: PersonalizedEntityIndex to cache
            user_id: User ID (default: "default" for single-home)
        """
        if not index:
            return
        
        with self._cache_lock:
            was_update = user_id in self._cache
            self._cache[user_id] = (index, datetime.now())
            
            if was_update:
                self._stats["updates"] += 1
            else:
                self._stats["builds"] += 1
            
            logger.debug(f"Index cached for user '{user_id}' (update={was_update})")
    
    def invalidate(self, user_id: str = "default") -> None:
        """
        Invalidate cached index for user.
        
        Args:
            user_id: User ID (default: "default" for single-home)
        """
        with self._cache_lock:
            if user_id in self._cache:
                del self._cache[user_id]
                logger.debug(f"Index cache invalidated for user '{user_id}'")
    
    def clear(self) -> None:
        """Clear all cached indexes"""
        with self._cache_lock:
            self._cache.clear()
            self._stats["hits"] = 0
            self._stats["misses"] = 0
            self._stats["builds"] = 0
            self._stats["updates"] = 0
            logger.info("IndexCache cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        with self._cache_lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0.0
            
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "builds": self._stats["builds"],
                "updates": self._stats["updates"],
                "cached_users": len(self._cache),
                "hit_rate": round(hit_rate, 2),
                "total_requests": total_requests
            }
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries (if TTL enabled).
        
        Returns:
            Number of entries removed
        """
        if not self.ttl_seconds:
            return 0
        
        removed = 0
        now = datetime.now()
        expired_keys = []
        
        with self._cache_lock:
            for key, (_, timestamp) in self._cache.items():
                age = (now - timestamp).total_seconds()
                if age > self.ttl_seconds:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                removed += 1
        
        if removed > 0:
            logger.debug(f"Removed {removed} expired entries from index cache")
        
        return removed

