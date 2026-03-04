"""
Shared Correlation Cache

Epic 39, Story 39.11: Shared Infrastructure Setup
File-backed cache shared across all microservices.

Single-home NUC optimized:
- Database-backed persistent cache (<20MB)
- In-memory LRU cache (fast lookups)
- Automatic cache invalidation
- Thread-safe for async usage
"""

from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Optional

from .logging_config import get_logger

logger = get_logger(__name__)


class CorrelationCache:
    """
    Caches correlation computations for fast lookups.

    Two-tier caching:
    1. In-memory LRU cache (fast, limited size)
    2. Persistent PostgreSQL database (larger capacity)

    Single-home optimization:
    - Database-backed (PostgreSQL)
    - Cache size: ~1000-5000 pairs (single home scale)
    - TTL: 1 hour (correlations change slowly)
    - Thread-safe for use across async services
    """

    def __init__(self, cache_db_url: Optional[str] = None, max_memory_size: int = 1000):
        """
        Initialize correlation cache.

        Args:
            cache_db_url: PostgreSQL connection URL (default: in-memory only)
            max_memory_size: Maximum size of in-memory LRU cache
        """
        self.max_memory_size = max_memory_size

        # In-memory LRU cache
        self.memory_cache: OrderedDict[tuple[str, str], dict] = OrderedDict()

        # Persistent cache (if URL provided)
        self.cache_db_url = cache_db_url
        self.db_conn = None

        # Statistics tracking
        self._total_requests = 0
        self._cache_hits = 0
        self._cache_misses = 0

        if cache_db_url:
            self._init_database()

        logger.info("CorrelationCache initialized (db=%s, memory_size=%d)",
                   cache_db_url or "in-memory only", max_memory_size)

    def _init_database(self) -> None:
        """Initialize cache database."""
        if not self.cache_db_url:
            return

        try:
            import psycopg2
            self.db_conn = psycopg2.connect(self.cache_db_url)
            self.db_conn.autocommit = False
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS correlation_cache (
                        entity1_id TEXT NOT NULL,
                        entity2_id TEXT NOT NULL,
                        correlation REAL NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        PRIMARY KEY (entity1_id, entity2_id)
                    )
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_expires_at ON correlation_cache(expires_at)
                """)
            self.db_conn.commit()

            logger.debug("Cache database initialized: %s", self.cache_db_url)
        except Exception as e:
            logger.warning("Failed to initialize cache database: %s", e)
            self.db_conn = None

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

        # Check persistent cache
        if self.db_conn:
            try:
                with self.db_conn.cursor() as cur:
                    cur.execute("""
                        SELECT correlation, timestamp, expires_at
                        FROM correlation_cache
                        WHERE entity1_id = %s AND entity2_id = %s
                    """, pair_key)

                    row = cur.fetchone()
                    if row:
                        correlation, timestamp_val, expires_at_val = row

                        if datetime.now() < expires_at_val:
                            # Valid cache entry
                            correlation_val = float(correlation)

                            # Also add to memory cache
                            self._set_memory(pair_key, correlation_val, ttl_seconds)

                            self._cache_hits += 1
                            return correlation_val
                        else:
                            # Expired, remove from database
                            cur.execute("""
                                DELETE FROM correlation_cache
                                WHERE entity1_id = %s AND entity2_id = %s
                            """, pair_key)
                            self.db_conn.commit()
            except Exception as e:
                logger.debug("Error reading from cache database: %s", e)

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

        # Set in persistent cache
        if self.db_conn:
            try:
                now = datetime.now()
                expires_at = now + timedelta(seconds=ttl_seconds)

                with self.db_conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO correlation_cache
                        (entity1_id, entity2_id, correlation, timestamp, expires_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (entity1_id, entity2_id) DO UPDATE SET
                            correlation = EXCLUDED.correlation,
                            timestamp = EXCLUDED.timestamp,
                            expires_at = EXCLUDED.expires_at
                    """, (
                        pair_key[0],
                        pair_key[1],
                        correlation,
                        now.isoformat(),
                        expires_at.isoformat()
                    ))
                self.db_conn.commit()
            except Exception as e:
                logger.debug("Error writing to cache database: %s", e)

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

    def _is_valid(self, cached: dict, _ttl_seconds: int) -> bool:
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

        # Remove from persistent cache
        if self.db_conn:
            try:
                with self.db_conn.cursor() as cur:
                    cur.execute("""
                        DELETE FROM correlation_cache
                        WHERE entity1_id = %s AND entity2_id = %s
                    """, pair_key)
                self.db_conn.commit()
            except Exception as e:
                logger.debug("Error invalidating cache entry: %s", e)

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

        # Clear expired from persistent cache
        if self.db_conn:
            try:
                with self.db_conn.cursor() as cur:
                    cur.execute("""
                        DELETE FROM correlation_cache
                        WHERE expires_at < %s
                    """, (now.isoformat(),))
                    count += cur.rowcount
                self.db_conn.commit()
            except Exception as e:
                logger.debug("Error clearing expired cache entries: %s", e)

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
                with self.db_conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM correlation_cache")
                    db_size = cur.fetchone()[0]
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


def get_correlation_cache(cache_db_url: Optional[str] = None, max_memory_size: int = 1000) -> CorrelationCache:
    """
    Get or create global correlation cache instance.

    Args:
        cache_db_url: PostgreSQL connection URL
        max_memory_size: Maximum size of in-memory LRU cache

    Returns:
        CorrelationCache instance (singleton)
    """
    global _global_cache

    if _global_cache is None:
        _global_cache = CorrelationCache(cache_db_url, max_memory_size)

    return _global_cache
