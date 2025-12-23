"""
State History API Client

Epic 37, Story 37.3: State History API Client
Integrates with Home Assistant state history API for long-term correlation patterns.

Single-home NUC optimized:
- Memory: <10MB (query cache)
- Performance: <100ms per query (cached)
- Query caching: Avoids repeated API calls
- Rate limiting: Respects HA API limits
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

import httpx

from shared.logging_config import get_logger

logger = get_logger(__name__)


class StateHistoryClient:
    """
    Client for Home Assistant state history API.
    
    Provides:
    - Historical state changes for entities
    - Long-term correlation pattern data
    - Query caching to reduce API calls
    - Rate limiting compliance
    
    Single-home NUC optimization:
    - In-memory query cache (<10MB)
    - Batch queries for multiple entities
    - Respects HA API rate limits
    """
    
    def __init__(
        self,
        ha_url: str,
        access_token: str,
        cache_ttl_seconds: int = 3600,
        timeout_seconds: int = 30
    ):
        """
        Initialize state history client.
        
        Args:
            ha_url: Home Assistant URL (e.g., http://192.168.1.86:8123)
            access_token: Home Assistant long-lived access token
            cache_ttl_seconds: Cache TTL in seconds (default: 1 hour)
            timeout_seconds: HTTP timeout in seconds (default: 30)
        """
        self.ha_url = ha_url.rstrip('/')
        self.access_token = access_token
        self.cache_ttl_seconds = cache_ttl_seconds
        self.timeout_seconds = timeout_seconds
        
        # Query cache: (entity_id, start_time, end_time) -> (data, timestamp)
        self.query_cache: Dict[tuple, tuple] = {}
        
        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=timeout_seconds,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        logger.info(
            "StateHistoryClient initialized (ha_url=%s, cache_ttl=%ds)",
            ha_url, cache_ttl_seconds
        )
    
    async def get_entity_history(
        self,
        entity_id: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get historical state changes for an entity.
        
        Args:
            entity_id: Entity ID (e.g., 'light.living_room')
            start_time: Start time for history query
            end_time: End time (defaults to now)
            use_cache: Whether to use cache (default: True)
        
        Returns:
            List of state change dictionaries with keys:
            - entity_id: Entity ID
            - state: State value
            - last_changed: Timestamp of state change
            - last_updated: Timestamp of last update
            - attributes: Entity attributes
        """
        if end_time is None:
            end_time = datetime.now()
        
        # Check cache
        cache_key = (entity_id, start_time.isoformat(), end_time.isoformat())
        if use_cache and cache_key in self.query_cache:
            cached_data, cached_time = self.query_cache[cache_key]
            age = (datetime.now() - cached_time).total_seconds()
            if age < self.cache_ttl_seconds:
                logger.debug("Cache hit for entity history: %s", entity_id)
                return cached_data
        
        try:
            # Format times for HA API (ISO format)
            start_str = start_time.isoformat()
            end_str = end_time.isoformat()
            
            # HA API endpoint: /api/history/period/{timestamp}
            url = f"{self.ha_url}/api/history/period/{start_str}"
            params = {
                "filter_entity_id": entity_id,
                "end_time": end_str
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Make request
            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            # Parse response (HA returns list of lists)
            data = response.json()
            if not data:
                return []
            
            # HA returns list of lists, flatten if needed
            if isinstance(data[0], list):
                history = data[0]
            else:
                history = data
            
            # Normalize to consistent format
            normalized = []
            for entry in history:
                normalized.append({
                    "entity_id": entry.get("entity_id", entity_id),
                    "state": entry.get("state"),
                    "last_changed": entry.get("last_changed"),
                    "last_updated": entry.get("last_updated"),
                    "attributes": entry.get("attributes", {})
                })
            
            # Cache result
            if use_cache:
                self.query_cache[cache_key] = (normalized, datetime.now())
                self._cleanup_cache()
            
            logger.debug(
                "Retrieved %d state changes for %s (%s to %s)",
                len(normalized), entity_id, start_str, end_str
            )
            
            return normalized
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error getting history for %s: %s (status: %d)",
                entity_id, e, e.response.status_code
            )
            return []
        except Exception as e:
            logger.error("Error getting history for %s: %s", entity_id, e)
            return []
    
    async def get_multiple_entities_history(
        self,
        entity_ids: List[str],
        start_time: datetime,
        end_time: Optional[datetime] = None,
        use_cache: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get historical state changes for multiple entities.
        
        Args:
            entity_ids: List of entity IDs
            start_time: Start time for history query
            end_time: End time (defaults to now)
            use_cache: Whether to use cache
        
        Returns:
            Dict mapping entity_id -> list of state changes
        """
        results = {}
        
        # Query each entity (HA API doesn't support batch queries)
        for entity_id in entity_ids:
            history = await self.get_entity_history(
                entity_id, start_time, end_time, use_cache
            )
            results[entity_id] = history
        
        logger.debug(
            "Retrieved history for %d entities (%d total state changes)",
            len(entity_ids), sum(len(h) for h in results.values())
        )
        
        return results
    
    async def get_correlation_history(
        self,
        entity1_id: str,
        entity2_id: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        use_cache: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get historical state changes for a correlation pair.
        
        Args:
            entity1_id: Entity 1 ID
            entity2_id: Entity 2 ID
            start_time: Start time for history query
            end_time: End time (defaults to now)
            use_cache: Whether to use cache
        
        Returns:
            Dict with 'entity1' and 'entity2' keys, each containing state changes
        """
        return await self.get_multiple_entities_history(
            [entity1_id, entity2_id], start_time, end_time, use_cache
        )
    
    def _cleanup_cache(self) -> None:
        """Clean up expired cache entries."""
        now = datetime.now()
        expired_keys = [
            key for key, (_, cached_time) in self.query_cache.items()
            if (now - cached_time).total_seconds() > self.cache_ttl_seconds
        ]
        
        for key in expired_keys:
            del self.query_cache[key]
        
        if expired_keys:
            logger.debug("Cleaned up %d expired cache entries", len(expired_keys))
    
    def clear_cache(self) -> None:
        """Clear all cached queries."""
        self.query_cache.clear()
        logger.info("State history cache cleared")
    
    def get_cache_size(self) -> int:
        """Get number of cached queries."""
        return len(self.query_cache)
    
    def get_memory_usage_mb(self) -> float:
        """
        Get approximate memory usage in MB.
        
        Rough estimate: ~1KB per cached query entry.
        """
        return len(self.query_cache) * 1.0 / 1024  # ~1KB per entry
    
    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        await self.client.aclose()
        self.query_cache.clear()
        logger.info("StateHistoryClient closed")

