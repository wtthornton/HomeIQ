"""
Synergy Context Service

Provides synergy context for Ask AI queries by querying synergies
involving detected entities. Optimized for single home NUC deployment
with efficient SQLite queries and caching.
"""

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.crud import calculate_synergy_priority_score
from ..database.models import SynergyOpportunity

logger = logging.getLogger(__name__)

# Metrics tracking
class SynergyMetrics:
    """Track synergy query metrics for monitoring."""
    def __init__(self):
        self.query_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.query_latencies = []  # List of latencies in milliseconds
        self.errors = 0
        self.synergies_retrieved = []  # List of synergy counts per query
    
    def record_query(self, latency_ms: float, synergies_count: int, cache_hit: bool):
        """Record a query metric."""
        self.query_count += 1
        self.query_latencies.append(latency_ms)
        self.synergies_retrieved.append(synergies_count)
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
                "avg_synergies_retrieved": 0.0,
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
            "avg_synergies_retrieved": sum(self.synergies_retrieved) / len(self.synergies_retrieved) if self.synergies_retrieved else 0.0,
            "errors": self.errors
        }

# Global metrics instance
_synergy_metrics = SynergyMetrics()


class SynergyContextService:
    """
    Service to query and format synergies for prompt context.
    
    Optimized for single home NUC:
    - Efficient SQLite queries with JSON parsing (acceptable overhead)
    - Result caching (5-minute TTL)
    - Priority-based selection (impact + pattern support + confidence)
    """

    def __init__(self):
        """Initialize synergy context service."""
        self._cache: dict[str, tuple[list[dict], datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)

    def _parse_device_ids(self, device_ids_json: str) -> list[str]:
        """
        Parse device_ids JSON string from SynergyOpportunity.
        
        Args:
            device_ids_json: JSON string containing device IDs
            
        Returns:
            List of device ID strings
        """
        try:
            if isinstance(device_ids_json, str):
                return json.loads(device_ids_json)
            elif isinstance(device_ids_json, list):
                return device_ids_json
            else:
                return []
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse device_ids: {e}")
            return []

    def _matches_entities(self, synergy: SynergyOpportunity, entity_ids: set[str]) -> bool:
        """
        Check if synergy involves any of the provided entities.
        
        Args:
            synergy: SynergyOpportunity database model
            entity_ids: Set of entity IDs to match against
            
        Returns:
            True if synergy matches any entity
        """
        # Parse device_ids JSON
        synergy_devices = self._parse_device_ids(synergy.device_ids)
        
        # Check if any device in synergy matches any entity
        for device_id in synergy_devices:
            if device_id in entity_ids:
                return True
        
        # Also check chain_devices if available (for multi-hop synergies)
        if synergy.chain_devices:
            chain_devices = self._parse_device_ids(synergy.chain_devices)
            for device_id in chain_devices:
                if device_id in entity_ids:
                    return True
        
        return False

    async def get_synergies_for_entities(
        self,
        db: AsyncSession,
        entity_ids: set[str],
        min_confidence: float = 0.7,
        limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Query synergies involving any of the provided entities.
        
        Args:
            db: Database session
            entity_ids: Set of entity IDs to match against
            min_confidence: Minimum confidence threshold
            limit: Maximum number of synergies to return
            
        Returns:
            List of synergy dictionaries with metadata
        """
        if not entity_ids:
            return []

        # Start timing
        start_time = time.time()
        cache_hit = False
        
        # Check cache
        cache_key = self._get_cache_key(entity_ids, min_confidence, limit)
        if cache_key in self._cache:
            cached_synergies, cache_time = self._cache[cache_key]
            if datetime.now(timezone.utc) - cache_time < self._cache_ttl:
                cache_hit = True
                latency_ms = (time.time() - start_time) * 1000
                _synergy_metrics.record_query(latency_ms, len(cached_synergies), cache_hit)
                logger.debug(f"✅ Synergy cache hit for {len(entity_ids)} entities (latency: {latency_ms:.1f}ms)")
                return cached_synergies

        try:
            # Query synergies with minimum confidence
            # Note: We'll filter by entity matching in Python (SQLite JSON limitation)
            query = select(SynergyOpportunity).where(
                SynergyOpportunity.confidence >= min_confidence
            ).order_by(SynergyOpportunity.impact_score.desc()).limit(limit * 3)  # Get more, filter down

            result = await db.execute(query)
            all_synergies = result.scalars().all()

            # Filter synergies that match our entities
            matching_synergies = [
                s for s in all_synergies
                if self._matches_entities(s, entity_ids)
            ]

            # Calculate priority scores and sort
            synergies_with_scores = []
            for synergy in matching_synergies:
                try:
                    priority = calculate_synergy_priority_score(synergy)
                    synergies_with_scores.append((synergy, priority))
                except Exception as e:
                    logger.warning(f"Failed to calculate priority for synergy {synergy.id}: {e}")
                    # Fallback to impact_score
                    priority = synergy.impact_score or 0.0
                    synergies_with_scores.append((synergy, priority))

            # Sort by priority (descending)
            synergies_with_scores.sort(key=lambda x: x[1], reverse=True)

            # Format synergies for prompt context
            formatted_synergies = []
            for synergy, priority in synergies_with_scores[:limit]:
                formatted_synergy = {
                    'synergy_id': synergy.synergy_id,
                    'synergy_type': synergy.synergy_type,
                    'device_ids': self._parse_device_ids(synergy.device_ids),
                    'chain_devices': self._parse_device_ids(synergy.chain_devices) if synergy.chain_devices else None,
                    'impact_score': synergy.impact_score,
                    'confidence': synergy.confidence,
                    'priority_score': priority,
                    'complexity': synergy.complexity,
                    'area': synergy.area,
                    'validated_by_patterns': synergy.validated_by_patterns,
                    'pattern_support_score': synergy.pattern_support_score,
                    'opportunity_metadata': synergy.opportunity_metadata or {}
                }
                formatted_synergies.append(formatted_synergy)

            # Cache results
            self._cache[cache_key] = (formatted_synergies, datetime.now(timezone.utc))
            
            # Clean old cache entries (keep max 100)
            if len(self._cache) > 100:
                self._clean_cache()

            # Record metrics
            latency_ms = (time.time() - start_time) * 1000
            _synergy_metrics.record_query(latency_ms, len(formatted_synergies), cache_hit)
            
            logger.info(
                f"✅ Retrieved {len(formatted_synergies)} synergies for {len(entity_ids)} entities "
                f"(latency: {latency_ms:.1f}ms, cache: {'hit' if cache_hit else 'miss'})"
            )
            return formatted_synergies

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            _synergy_metrics.record_error()
            logger.error(
                f"❌ Failed to query synergies: {e} (latency: {latency_ms:.1f}ms)",
                exc_info=True
            )
            return []  # Fail gracefully - return empty list

    def _get_cache_key(self, entity_ids: set[str], min_confidence: float, limit: int) -> str:
        """Generate cache key from parameters."""
        # Sort entity IDs for consistent key
        sorted_entities = sorted(entity_ids)
        return f"synergies:{','.join(sorted_entities)}:conf{min_confidence}:lim{limit}"

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
        logger.debug(f"🧹 Cleaned synergy cache: kept 50 entries")

    def clear_cache(self):
        """Clear all cached synergies (for testing or manual refresh)."""
        self._cache.clear()
        logger.debug("🧹 Cleared synergy cache")
    
    @staticmethod
    def get_metrics() -> dict[str, Any]:
        """Get synergy query metrics for monitoring."""
        return _synergy_metrics.get_stats()

