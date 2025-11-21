"""
Device Context Service

Enriches entities with real-time device context.
Provides comprehensive device information for automation generation.

Created: Phase 4 - Function Calling & Device Context
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ...clients.ha_client import HomeAssistantClient

logger = logging.getLogger(__name__)


@dataclass
class DeviceContext:
    """Device context information"""
    entity_id: str
    current_state: dict[str, Any]
    typical_on_time: str | None = None
    last_changed: datetime | None = None
    responsive: bool = True
    usage_patterns: dict[str, Any] | None = None


class DeviceContextService:
    """
    Enriches entities with real-time device context.

    Provides:
    - Current state
    - 24h usage history
    - Typical patterns
    - Response rate
    - Last seen
    """

    def __init__(self, ha_client: HomeAssistantClient):
        """
        Initialize device context service.

        Args:
            ha_client: Home Assistant client
        """
        self.ha_client = ha_client
        logger.info("DeviceContextService initialized")

    async def enrich_with_context(
        self,
        entity_ids: list[str],
        ha_client: HomeAssistantClient | None = None,
    ) -> dict[str, DeviceContext]:
        """
        Get comprehensive device context.

        Args:
            entity_ids: List of entity IDs to enrich
            ha_client: Optional HA client (uses self.ha_client if not provided)

        Returns:
            Dictionary mapping entity_id to DeviceContext
        """
        client = ha_client or self.ha_client
        if not client:
            logger.warning("No HA client available for device context")
            return {}

        contexts = {}

        for entity_id in entity_ids:
            try:
                # Get current state
                state = await client.get_entity_state(entity_id)

                # Get state history (last 24h) - placeholder for now
                # Full implementation would query InfluxDB or HA history API
                history = []  # await self._get_entity_history(entity_id, hours=24)

                # Calculate usage patterns
                patterns = self._analyze_usage_patterns(history)

                # Calculate response rate
                response_rate = self._calculate_response_rate(history)

                contexts[entity_id] = DeviceContext(
                    entity_id=entity_id,
                    current_state=state or {},
                    typical_on_time=patterns.get("typical_on_time"),
                    last_changed=datetime.utcnow(),  # Would extract from state
                    responsive=response_rate > 0.9,
                    usage_patterns=patterns,
                )

            except Exception as e:
                logger.warning(f"Failed to enrich context for {entity_id}: {e}")
                # Continue with other entities

        logger.info(f"✅ Enriched context for {len(contexts)}/{len(entity_ids)} entities")
        return contexts

    def _analyze_usage_patterns(self, history: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze usage patterns from history"""
        # Placeholder - full implementation would analyze history
        return {
            "typical_on_time": None,
            "frequency": "unknown",
            "patterns": [],
        }

    def _calculate_response_rate(self, history: list[dict[str, Any]]) -> float:
        """Calculate device response rate"""
        # Placeholder - full implementation would calculate from history
        return 1.0  # Assume responsive by default

