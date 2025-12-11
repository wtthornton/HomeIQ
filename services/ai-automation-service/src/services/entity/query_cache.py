"""
Query Result Cache

Epic AI-12, Story AI12.10: Performance Optimization & Caching
Caches query results to avoid recalculating similarity scores for common queries.
Uses LRU cache with configurable size limit.
"""

import logging
from typing import Optional
from collections import OrderedDict
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger(__name__)


class QueryCache:
    """
    LRU cache for query results.
    
    Features:
    - LRU eviction (least recently used)
    - Configurable size limit
    - Optional TTL (time-to-live) for cache entries
    - Hash-based cache keys (query + filters)
    """
    
    def __init__(
        self,
        max_size: int = 500,
        ttl_seconds: Optional[int] = 300  # 5 minutes default
    ):
        """
        Initialize query cache.
        
        Args:
            max_size: Maximum number of cached queries (default: 500)
            ttl_seconds: Optional TTL in seconds (default: 300 = 5 minutes)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        # LRU cache: cache_key -> (results, timestamp)
        self._cache: OrderedDict[str, tuple[list, datetime]] = OrderedDict()
        
        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "size": 0
        }
        
        logger.info(f"QueryCache initialized (max_size={max_size}, ttl={ttl_seconds})")
    
    def _make_cache_key(
        self,
        query: str,
        domain: Optional[str] = None,
        area_id: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """
        Create cache key from query parameters.
        
        Args:
            query: Search query
            domain: Optional domain filter
            area_id: Optional area filter
            limit: Result limit
        
        Returns:
            Cache key (hash)
        """
        key_data = {
            "query": query.strip().lower() if query else "",
            "domain": domain or "",
            "area_id": area_id or "",
            "limit": limit
        }
        
        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_json.encode()).hexdigest()
    
    def get(
        self,
        query: str,
        domain: Optional[str] = None,
        area_id: Optional[str] = None,
        limit: int = 10
    ) -> Optional[list]:
        """
        Get cached query results.
        
        Args:
            query: Search query
            domain: Optional domain filter
            area_id: Optional area filter
            limit: Result limit
        
        Returns:
            Cached results if found and valid, None otherwise
        """
        cache_key = self._make_cache_key(query, domain, area_id, limit)
        
        # Check if in cache
        if cache_key not in self._cache:
            self._stats["misses"] += 1
            return None
        
        # Get entry
        results, timestamp = self._cache[cache_key]
        
        # Check TTL
        if self.ttl_seconds:
            age = (datetime.now() - timestamp).total_seconds()
            if age > self.ttl_seconds:
                # Expired - remove from cache
                del self._cache[cache_key]
                self._stats["misses"] += 1
                self._stats["size"] = len(self._cache)
                return None
        
        # Move to end (most recently used)
        self._cache.move_to_end(cache_key)
        self._stats["hits"] += 1
        return results
    
    def put(
        self,
        query: str,
        results: list,
        domain: Optional[str] = None,
        area_id: Optional[str] = None,
        limit: int = 10
    ) -> None:
        """
        Cache query results.
        
        Args:
            query: Search query
            results: Query results to cache
            domain: Optional domain filter
            area_id: Optional area filter
            limit: Result limit
        """
        if not query or not results:
            return
        
        cache_key = self._make_cache_key(query, domain, area_id, limit)
        
        # Remove if already exists (will be re-added at end)
        if cache_key in self._cache:
            del self._cache[cache_key]
        
        # Add to cache
        self._cache[cache_key] = (results, datetime.now())
        
        # Evict if over limit
        if len(self._cache) > self.max_size:
            # Remove oldest (first) entry
            self._cache.popitem(last=False)
            self._stats["evictions"] += 1
        
        self._stats["size"] = len(self._cache)
    
    def invalidate(self, query: Optional[str] = None) -> int:
        """
        Invalidate cached queries.
        
        Args:
            query: Optional query to invalidate (None = invalidate all)
        
        Returns:
            Number of entries invalidated
        """
        if query is None:
            # Invalidate all
            count = len(self._cache)
            self._cache.clear()
            self._stats["size"] = 0
            return count
        
        # Invalidate specific query (and variations)
        query_lower = query.strip().lower()
        invalidated = 0
        keys_to_remove = []
        
        for key in self._cache.keys():
            # Check if key matches query (simple check - could be improved)
            if query_lower in key or key in query_lower:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._cache[key]
            invalidated += 1
        
        if invalidated > 0:
            self._stats["size"] = len(self._cache)
            logger.debug(f"Invalidated {invalidated} query cache entries for '{query}'")
        
        return invalidated
    
    def clear(self) -> None:
        """Clear all cached queries"""
        self._cache.clear()
        self._stats["size"] = 0
        self._stats["hits"] = 0
        self._stats["misses"] = 0
        self._stats["evictions"] = 0
        logger.info("QueryCache cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "evictions": self._stats["evictions"],
            "size": self._stats["size"],
            "max_size": self.max_size,
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
        
        for key, (_, timestamp) in self._cache.items():
            age = (now - timestamp).total_seconds()
            if age > self.ttl_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            removed += 1
        
        if removed > 0:
            self._stats["size"] = len(self._cache)
            logger.debug(f"Removed {removed} expired entries from query cache")
        
        return removed

