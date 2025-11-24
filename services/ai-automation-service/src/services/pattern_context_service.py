"""
Pattern Context Service

Provides pattern context for Ask AI queries by querying patterns
matching detected entities. Optimized for single home NUC deployment
with efficient SQLite queries and caching.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Pattern

logger = logging.getLogger(__name__)

# Metrics tracking
class PatternMetrics:
    """Track pattern query metrics for monitoring."""
    def __init__(self):
        self.query_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.query_latencies = []  # List of latencies in milliseconds
        self.errors = 0
        self.patterns_retrieved = []  # List of pattern counts per query
    
    def record_query(self, latency_ms: float, patterns_count: int, cache_hit: bool):
        """Record a query metric."""
        self.query_count += 1
        self.query_latencies.append(latency_ms)
        self.patterns_retrieved.append(patterns_count)
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def record_error(self):
        """Record a query error."""
        self.errors += 1
    
    def get_stats(self) -> dict[str, Any]:
        """Get current statistics."""
        if not self.query_latencies:
            return {
                "query_count": self.query_count,
                "cache_hit_rate": 0.0,
                "avg_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "avg_patterns_retrieved": 0.0,
                "errors": self.errors
            }
        
        sorted_latencies = sorted(self.query_latencies)
        total_queries = self.cache_hits + self.cache_misses
        
        return {
            "query_count": self.query_count,
            "cache_hit_rate": (self.cache_hits / total_queries * 100) if total_queries > 0 else 0.0,
            "avg_latency_ms": sum(self.query_latencies) / len(self.query_latencies),
            "p50_latency_ms": sorted_latencies[len(sorted_latencies) // 2],
            "p95_latency_ms": sorted_latencies[int(len(sorted_latencies) * 0.95)] if len(sorted_latencies) > 1 else sorted_latencies[0],
            "p99_latency_ms": sorted_latencies[int(len(sorted_latencies) * 0.99)] if len(sorted_latencies) > 1 else sorted_latencies[0],
            "avg_patterns_retrieved": sum(self.patterns_retrieved) / len(self.patterns_retrieved) if self.patterns_retrieved else 0.0,
            "errors": self.errors
        }

# Global metrics instance
_pattern_metrics = PatternMetrics()


class PatternContextService:
    """
    Service to query and format patterns for prompt context.
    
    Optimized for single home NUC:
    - Efficient SQLite queries with IN clause
    - Result caching (5-minute TTL)
    - Pattern relevance scoring (confidence + recency)
    """

    def __init__(self):
        """Initialize pattern context service."""
        self._cache: dict[str, tuple[list[dict], datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)

    def _calculate_relevance_score(self, pattern: Pattern) -> float:
        """
        Calculate relevance score combining confidence and recency.
        
        Args:
            pattern: Pattern database model
            
        Returns:
            Relevance score (0.0-1.0)
        """
        confidence = pattern.confidence or 0.0
        
        # Recency score: patterns seen in last 7 days get full score
        # Older patterns get diminishing score
        if pattern.last_seen:
            days_old = (datetime.now(timezone.utc) - pattern.last_seen).days
            if days_old <= 7:
                recency = 1.0
            elif days_old <= 30:
                recency = 0.8
            elif days_old <= 90:
                recency = 0.6
            else:
                recency = 0.4
        else:
            recency = 0.5  # Default if no last_seen
        
        # Weighted combination: 70% confidence, 30% recency
        relevance = (confidence * 0.7) + (recency * 0.3)
        
        return relevance

    async def get_patterns_for_entities(
        self,
        db: AsyncSession,
        entity_ids: set[str],
        min_confidence: float = 0.6,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Query patterns matching any of the provided entities.
        
        Args:
            db: Database session
            entity_ids: Set of entity IDs to match against
            min_confidence: Minimum confidence threshold
            limit: Maximum number of patterns to return
            
        Returns:
            List of pattern dictionaries with metadata
        """
        if not entity_ids:
            return []

        # Start timing
        start_time = time.time()
        cache_hit = False
        
        # Check cache
        cache_key = self._get_cache_key(entity_ids, min_confidence, limit)
        if cache_key in self._cache:
            cached_patterns, cache_time = self._cache[cache_key]
            if datetime.now(timezone.utc) - cache_time < self._cache_ttl:
                cache_hit = True
                latency_ms = (time.time() - start_time) * 1000
                _pattern_metrics.record_query(latency_ms, len(cached_patterns), cache_hit)
                logger.debug(f"✅ Pattern cache hit for {len(entity_ids)} entities (latency: {latency_ms:.1f}ms)")
                return cached_patterns

        try:
            # Query patterns where device_id matches any entity
            # SQLite handles small IN clauses efficiently (single home deployment)
            query = select(Pattern).where(
                Pattern.device_id.in_(entity_ids),
                Pattern.confidence >= min_confidence
            ).order_by(Pattern.confidence.desc())

            result = await db.execute(query)
            patterns = result.scalars().all()

            # Calculate relevance scores and sort
            patterns_with_scores = []
            for pattern in patterns:
                relevance = self._calculate_relevance_score(pattern)
                patterns_with_scores.append((pattern, relevance))

            # Sort by relevance (descending)
            patterns_with_scores.sort(key=lambda x: x[1], reverse=True)

            # Format patterns for prompt context
            formatted_patterns = []
            for pattern, relevance in patterns_with_scores[:limit]:
                formatted_pattern = {
                    'pattern_id': pattern.id,
                    'pattern_type': pattern.pattern_type,
                    'device_id': pattern.device_id,
                    'confidence': pattern.confidence,
                    'occurrences': pattern.occurrences,
                    'relevance_score': relevance,
                    'last_seen': pattern.last_seen.isoformat() if pattern.last_seen else None,
                    'metadata': pattern.pattern_metadata or {}
                }
                formatted_patterns.append(formatted_pattern)

            # Cache results
            self._cache[cache_key] = (formatted_patterns, datetime.now(timezone.utc))
            
            # Clean old cache entries (keep max 100)
            if len(self._cache) > 100:
                self._clean_cache()

            # Record metrics
            latency_ms = (time.time() - start_time) * 1000
            _pattern_metrics.record_query(latency_ms, len(formatted_patterns), cache_hit)
            
            logger.info(
                f"✅ Retrieved {len(formatted_patterns)} patterns for {len(entity_ids)} entities "
                f"(latency: {latency_ms:.1f}ms, cache: {'hit' if cache_hit else 'miss'})"
            )
            return formatted_patterns

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            _pattern_metrics.record_error()
            logger.error(
                f"❌ Failed to query patterns: {e} (latency: {latency_ms:.1f}ms)",
                exc_info=True
            )
            return []  # Fail gracefully - return empty list

    def _get_cache_key(self, entity_ids: set[str], min_confidence: float, limit: int) -> str:
        """Generate cache key from parameters."""
        # Sort entity IDs for consistent key
        sorted_entities = sorted(entity_ids)
        return f"patterns:{','.join(sorted_entities)}:conf{min_confidence}:lim{limit}"

    def _clean_cache(self):
        """Remove old cache entries (keep most recent 50)."""
        # Sort by cache time (newest first)
        sorted_cache = sorted(
            self._cache.items(),
            key=lambda x: x[1][1],
            reverse=True
        )
        # Keep top 50
        self._cache = dict(sorted_cache[:50])
        logger.debug(f"🧹 Cleaned pattern cache: kept 50 entries")

    def clear_cache(self):
        """Clear all cached patterns (for testing or manual refresh)."""
        self._cache.clear()
        logger.debug("🧹 Cleared pattern cache")
    
    @staticmethod
    def get_metrics() -> dict[str, Any]:
        """Get pattern query metrics for monitoring."""
        return _pattern_metrics.get_stats()

