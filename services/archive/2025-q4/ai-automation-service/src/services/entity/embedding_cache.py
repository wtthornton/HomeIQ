"""
Embedding Cache

Epic AI-12, Story AI12.10: Performance Optimization & Caching
Caches semantic embeddings to avoid regenerating for same names.
Uses LRU cache with configurable size limit.
"""

import logging
from typing import Optional
from functools import lru_cache
from collections import OrderedDict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    LRU cache for semantic embeddings.
    
    Features:
    - LRU eviction (least recently used)
    - Configurable size limit
    - Optional TTL (time-to-live) for cache entries
    - Memory efficient
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: Optional[int] = None
    ):
        """
        Initialize embedding cache.
        
        Args:
            max_size: Maximum number of cached embeddings (default: 1000)
            ttl_seconds: Optional TTL in seconds (None = no expiration)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        # LRU cache: text -> (embedding, timestamp)
        self._cache: OrderedDict[str, tuple[list[float], datetime]] = OrderedDict()
        
        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "size": 0
        }
        
        logger.info(f"EmbeddingCache initialized (max_size={max_size}, ttl={ttl_seconds})")
    
    def get(self, text: str) -> Optional[list[float]]:
        """
        Get cached embedding for text.
        
        Args:
            text: Text to get embedding for
        
        Returns:
            Cached embedding if found and valid, None otherwise
        """
        if not text or not text.strip():
            return None
        
        text_key = text.strip().lower()
        
        # Check if in cache
        if text_key not in self._cache:
            self._stats["misses"] += 1
            return None
        
        # Get entry
        embedding, timestamp = self._cache[text_key]
        
        # Check TTL
        if self.ttl_seconds:
            age = (datetime.now() - timestamp).total_seconds()
            if age > self.ttl_seconds:
                # Expired - remove from cache
                del self._cache[text_key]
                self._stats["misses"] += 1
                self._stats["size"] = len(self._cache)
                return None
        
        # Move to end (most recently used)
        self._cache.move_to_end(text_key)
        self._stats["hits"] += 1
        return embedding
    
    def put(self, text: str, embedding: list[float]) -> None:
        """
        Cache embedding for text.
        
        Args:
            text: Text to cache embedding for
            embedding: Embedding vector to cache
        """
        if not text or not text.strip() or not embedding:
            return
        
        text_key = text.strip().lower()
        
        # Remove if already exists (will be re-added at end)
        if text_key in self._cache:
            del self._cache[text_key]
        
        # Add to cache
        self._cache[text_key] = (embedding, datetime.now())
        
        # Evict if over limit
        if len(self._cache) > self.max_size:
            # Remove oldest (first) entry
            self._cache.popitem(last=False)
            self._stats["evictions"] += 1
        
        self._stats["size"] = len(self._cache)
    
    def clear(self) -> None:
        """Clear all cached embeddings"""
        self._cache.clear()
        self._stats["size"] = 0
        self._stats["hits"] = 0
        self._stats["misses"] = 0
        self._stats["evictions"] = 0
        logger.info("EmbeddingCache cleared")
    
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
            logger.debug(f"Removed {removed} expired entries from embedding cache")
        
        return removed

