"""
Shared Correlation Cache

Epic 39, Story 39.11: Shared Infrastructure Setup
SQLite-based cache shared across all microservices.

Single-home NUC optimized:
- SQLite-backed cache (persistent, <20MB)
- In-memory LRU cache (fast lookups)
- Automatic cache invalidation
- Thread-safe for async usage
"""

import logging
import sqlite3
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path
from collections import OrderedDict

from .logging_config import get_logger

logger = get_logger(__name__)


class CorrelationCache:
    """
    Caches correlation computations for fast lookups.
    
    Two-tier caching:
    1. In-memory LRU cache (fast, limited size)
    2. SQLite database (persistent, larger capacity)
    
    Single-home optimization:
    - SQLite database (no Redis needed for single home)
    - Cache size: ~1000-5000 pairs (single home scale)
    - TTL: 1 hour (correlations change slowly)
    - Thread-safe for use across async services
    """
    
    def __init__(self, cache_db_path: Optional[str] = None, max_memory_size: int = 1000):
        """
        Initialize correlation cache.
        
        Args:
            cache_db_path: Path to SQLite cache database (default: in-memory only)
            max_memory_size: Maximum size of in-memory LRU cache
        """
        self.max_memory_size = max_memory_size
        
        # In-memory LRU cache
        self.memory_cache: OrderedDict[tuple[str, str], dict] = OrderedDict()
        
        # SQLite cache (if path provided)
        self.cache_db_path = cache_db_path
        self.db_conn: Optional[sqlite3.Connection] = None
        
        # Statistics tracking
        self._total_requests = 0
        self._cache_hits = 0
        self._cache_misses = 0
        
        if cache_db_path:
            self._init_database()
        
        logger.info("CorrelationCache initialized (db=%s, memory_size=%d)",
                   cache_db_path or "in-memory only", max_memory_size)
    
    def _init_database(self) -> None:
        """Initialize SQLite cache database"""
        if not self.cache_db_path:
            return
        
        db_path = Path(self.cache_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.db_conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS correlation_cache (
                entity1_id TEXT NOT NULL,
                entity2_id TEXT NOT NULL,
                correlation REAL NOT NULL,
                timestamp DATETIME NOT NULL,
                expires_at DATETIME NOT NULL,
                PRIMARY KEY (entity1_id, entity2_id)
            )
        """)
        self.db_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at ON correlation_cache(expires_at)
        """)
        self.db_conn.commit()
        
        logger.debug("SQLite cache database initialized: %s", self.cache_db_path)
    
    def get(
        self,
        entity1_id: str,
        entity2_id: str,
        ttl_seconds: int = 3600
    ) -> Optional[float]:
        """
        Get cached correlation.
        
        Args:
            entity1_id: Entity 1 ID
            entity2_id: Entity 2 ID
            ttl_seconds: Time-to-live in seconds (default: 1 hour)
        
        Returns:
            Cached correlation value or None if not found/expired
        """
        self._total_requests += 1
        pair_key = self._normalize_pair(entity1_id, entity2_id)
        
        # Check in-memory cache first
        if pair_key in self.memory_cache:
            cached = self.memory_cache[pair_key]
            if self._is_valid(cached, ttl_seconds):
                # Move to end (LRU)
                self.memory_cache.move_to_end(pair_key)
                self._cache_hits += 1
                return cached['correlation']
            else:
                # Expired, remove from memory
                del self.memory_cache[pair_key]
        
        # Check SQLite cache
        if self.db_conn:
            try:
                cursor = self.db_conn.execute("""
                    SELECT correlation, timestamp, expires_at
                    FROM correlation_cache
                    WHERE entity1_id = ? AND entity2_id = ?
                """, pair_key)
                
                row = cursor.fetchone()
                if row:
                    correlation, timestamp_str, expires_at_str = row
                    expires_at = datetime.fromisoformat(expires_at_str)
                    
                    if datetime.now() < expires_at:
                        # Valid cache entry
                        correlation_val = float(correlation)
                        
                        # Also add to memory cache
                        self._set_memory(pair_key, correlation_val, ttl_seconds)
                        
                        self._cache_hits += 1
                        return correlation_val
                    else:
                        # Expired, remove from database
                        self.db_conn.execute("""
                            DELETE FROM correlation_cache
                            WHERE entity1_id = ? AND entity2_id = ?
                        """, pair_key)
                        self.db_conn.commit()
            except Exception as e:
                logger.debug("Error reading from SQLite cache: %s", e)
        
        self._cache_misses += 1
        return None
    
    def set(
        self,
        entity1_id: str,
        entity2_id: str,
        correlation: float,
        ttl_seconds: int = 3600
    ) -> None:
        """
        Cache correlation value.
        
        Args:
            entity1_id: Entity 1 ID
            entity2_id: Entity 2 ID
            correlation: Correlation value (-1.0 to 1.0)
            ttl_seconds: Time-to-live in seconds (default: 1 hour)
        """
        pair_key = self._normalize_pair(entity1_id, entity2_id)
        
        # Set in-memory cache
        self._set_memory(pair_key, correlation, ttl_seconds)
        
        # Set in SQLite cache
        if self.db_conn:
            try:
                now = datetime.now()
                expires_at = now + timedelta(seconds=ttl_seconds)
                
                self.db_conn.execute("""
                    INSERT OR REPLACE INTO correlation_cache
                    (entity1_id, entity2_id, correlation, timestamp, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    pair_key[0],
                    pair_key[1],
                    correlation,
                    now.isoformat(),
                    expires_at.isoformat()
                ))
                self.db_conn.commit()
            except Exception as e:
                logger.debug("Error writing to SQLite cache: %s", e)
    
    def _set_memory(self, pair_key: tuple[str, str], correlation: float, ttl_seconds: int) -> None:
        """Set value in in-memory LRU cache"""
        now = datetime.now()
        expires_at = now + timedelta(seconds=ttl_seconds)
        
        self.memory_cache[pair_key] = {
            'correlation': correlation,
            'timestamp': now,
            'expires_at': expires_at
        }
        
        # Move to end (most recently used)
        self.memory_cache.move_to_end(pair_key)
        
        # Evict oldest if over limit
        if len(self.memory_cache) > self.max_memory_size:
            self.memory_cache.popitem(last=False)  # Remove oldest
    
    def _is_valid(self, cached: dict, ttl_seconds: int) -> bool:
        """Check if cached value is still valid"""
        expires_at = cached.get('expires_at')
        if expires_at is None:
            return False
        
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        return datetime.now() < expires_at
    
    def invalidate(self, entity1_id: str, entity2_id: str) -> None:
        """Invalidate cache entry for a pair"""
        pair_key = self._normalize_pair(entity1_id, entity2_id)
        
        # Remove from memory cache
        if pair_key in self.memory_cache:
            del self.memory_cache[pair_key]
        
        # Remove from SQLite cache
        if self.db_conn:
            try:
                self.db_conn.execute("""
                    DELETE FROM correlation_cache
                    WHERE entity1_id = ? AND entity2_id = ?
                """, pair_key)
                self.db_conn.commit()
            except Exception as e:
                logger.debug("Error invalidating SQLite cache: %s", e)
    
    def clear_expired(self) -> int:
        """
        Clear expired cache entries.
        
        Returns:
            Number of entries cleared
        """
        count = 0
        now = datetime.now()
        
        # Clear expired from memory cache
        expired_keys = [
            key for key, cached in self.memory_cache.items()
            if not self._is_valid(cached, 0)
        ]
        for key in expired_keys:
            del self.memory_cache[key]
            count += 1
        
        # Clear expired from SQLite cache
        if self.db_conn:
            try:
                cursor = self.db_conn.execute("""
                    DELETE FROM correlation_cache
                    WHERE expires_at < ?
                """, (now.isoformat(),))
                self.db_conn.commit()
                count += cursor.rowcount
            except Exception as e:
                logger.debug("Error clearing expired SQLite cache: %s", e)
        
        if count > 0:
            logger.debug("Cleared %d expired cache entries", count)
        
        return count
    
    def _normalize_pair(self, entity1_id: str, entity2_id: str) -> tuple[str, str]:
        """Normalize pair to ensure consistent ordering"""
        if entity1_id < entity2_id:
            return (entity1_id, entity2_id)
        return (entity2_id, entity1_id)
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        memory_size = len(self.memory_cache)
        
        db_size = 0
        if self.db_conn:
            try:
                cursor = self.db_conn.execute("SELECT COUNT(*) FROM correlation_cache")
                db_size = cursor.fetchone()[0]
            except Exception:
                pass
        
        total_requests = getattr(self, '_total_requests', 0)
        hits = getattr(self, '_cache_hits', 0)
        misses = getattr(self, '_cache_misses', 0)
        hit_rate = hits / total_requests if total_requests > 0 else 0.0
        
        return {
            'memory_cache_size': memory_size,
            'db_cache_size': db_size,
            'max_memory_size': self.max_memory_size,
            'total_requests': total_requests,
            'cache_hits': hits,
            'cache_misses': misses,
            'hit_rate': round(hit_rate, 4),
            'hit_rate_percent': round(hit_rate * 100, 2)
        }
    
    def close(self) -> None:
        """Close database connection"""
        if self.db_conn:
            self.db_conn.close()
            self.db_conn = None
            logger.debug("Correlation cache database closed")


# Global cache instance (singleton pattern)
_global_cache: Optional[CorrelationCache] = None


def get_correlation_cache(cache_db_path: Optional[str] = None, max_memory_size: int = 1000) -> CorrelationCache:
    """
    Get or create global correlation cache instance.
    
    Args:
        cache_db_path: Path to SQLite cache database
        max_memory_size: Maximum size of in-memory LRU cache
    
    Returns:
        CorrelationCache instance (singleton)
    """
    global _global_cache
    
    if _global_cache is None:
        _global_cache = CorrelationCache(cache_db_path, max_memory_size)
    
    return _global_cache

