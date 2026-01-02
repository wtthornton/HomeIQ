"""
Device State Context Service

Fetches and formats current entity states for context inclusion in LLM prompts.
Epic AI-20: Context Enhancement - Device State Context

Provides current device states when entities are mentioned in user prompts,
helping the LLM make smarter automation decisions.
"""

import hashlib
import logging
from typing import Any

from ..clients.data_api_client import DataAPIClient
from ..clients.ha_client import HomeAssistantClient
from ..config import Settings
from ..services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class DeviceStateContextService:
    """
    Service for fetching and formatting current entity states for context inclusion.

    Fetches current states of entities mentioned in user prompts to help LLM
    make smarter automation decisions (e.g., knowing if a light is already on
    when user says "turn on the office lights").
    """

    def __init__(self, settings: Settings, context_builder: ContextBuilder):
        """
        Initialize device state context service.

        Args:
            settings: Application settings
            context_builder: Context builder for cache access
        """
        self.settings = settings
        self.context_builder = context_builder
        self.ha_client = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token
        )
        self.data_api_client = DataAPIClient(base_url=settings.data_api_url)
        self._cache_ttl = 45  # 45 seconds (states change frequently)

    def _get_cache_key(self, entity_ids: list[str]) -> str:
        """
        Generate cache key for entity states.

        Args:
            entity_ids: List of entity IDs

        Returns:
            Cache key string
        """
        # Sort entity IDs for consistent hashing
        sorted_ids = sorted(entity_ids)
        ids_str = ",".join(sorted_ids)
        ids_hash = hashlib.md5(ids_str.encode()).hexdigest()[:12]
        return f"device_state_context_{ids_hash}"

    def _format_state_entry(self, state: dict[str, Any]) -> str:
        """
        Format a single entity state entry.

        Args:
            state: Entity state dictionary from HA API

        Returns:
            Formatted string like "light.office_go: on (brightness: 255, color_mode: rgb)"
        """
        entity_id = state.get("entity_id", "unknown")
        state_value = state.get("state", "unknown")
        attributes = state.get("attributes", {})

        # Build attribute string with relevant attributes
        attr_parts = []

        # Domain-specific attribute extraction
        domain = entity_id.split(".")[0] if "." in entity_id else ""

        if domain == "light":
            # Light-specific attributes
            if "brightness" in attributes:
                attr_parts.append(f"brightness: {attributes['brightness']}")
            if "color_mode" in attributes:
                attr_parts.append(f"color_mode: {attributes['color_mode']}")
            if "rgb_color" in attributes:
                rgb = attributes["rgb_color"]
                if isinstance(rgb, list) and len(rgb) >= 3:
                    attr_parts.append(f"rgb: [{rgb[0]},{rgb[1]},{rgb[2]}]")
            if "color_temp" in attributes:
                attr_parts.append(f"color_temp: {attributes['color_temp']}")

        elif domain == "climate":
            # Climate-specific attributes
            if "temperature" in attributes:
                attr_parts.append(f"temperature: {attributes['temperature']}")
            if "current_temperature" in attributes:
                attr_parts.append(f"current: {attributes['current_temperature']}")
            if "hvac_action" in attributes:
                attr_parts.append(f"hvac_action: {attributes['hvac_action']}")

        elif domain == "cover":
            # Cover-specific attributes
            if "position" in attributes:
                attr_parts.append(f"position: {attributes['position']}")
            elif "current_position" in attributes:
                attr_parts.append(f"position: {attributes['current_position']}")

        elif domain == "fan":
            # Fan-specific attributes
            if "percentage" in attributes:
                attr_parts.append(f"percentage: {attributes['percentage']}")
            if "preset_mode" in attributes:
                attr_parts.append(f"preset: {attributes['preset_mode']}")

        elif domain in ("sensor", "binary_sensor"):
            # Sensor-specific: include unit if available
            if "unit_of_measurement" in attributes:
                attr_parts.append(f"unit: {attributes['unit_of_measurement']}")

        # Build formatted string
        if attr_parts:
            attr_str = " (" + ", ".join(attr_parts) + ")"
        else:
            attr_str = ""

        return f"- {entity_id}: {state_value}{attr_str}"

    async def get_state_context(
        self,
        entity_ids: list[str] | None = None,
        user_prompt: str | None = None,
        skip_truncation: bool = False,
    ) -> str:
        """
        Get formatted state context for specified entities.

        Args:
            entity_ids: Optional list of entity IDs to fetch states for
            user_prompt: Optional user prompt (not used in this implementation,
                        entity extraction should happen in caller)
            skip_truncation: If True, skip truncation (for debug display)

        Returns:
            Formatted context string with entity states, or empty string if no entities
            or if unable to fetch states

        Note:
            This service expects entity_ids to be provided. Entity extraction from
            user_prompt should be done by the caller using EntityResolutionService.
        """
        # If no entity IDs provided, return empty
        if not entity_ids:
            logger.debug("No entity IDs provided, returning empty state context")
            return ""

        # Check cache first (only if not skipping truncation)
        cache_key = self._get_cache_key(entity_ids)
        if not skip_truncation:
            cached = await self.context_builder._get_cached_value(cache_key)
            if cached:
                logger.debug(f"✅ Using cached state context for {len(entity_ids)} entities")
                return cached

        try:
            # Fetch all states from Home Assistant
            logger.info(f"📊 Fetching states for {len(entity_ids)} entities...")
            all_states = await self.ha_client.get_states()

            # Create map for fast lookup
            state_map = {state.get("entity_id"): state for state in all_states if state.get("entity_id")}

            # Filter to requested entities
            relevant_states = []
            for entity_id in entity_ids:
                if entity_id in state_map:
                    relevant_states.append(state_map[entity_id])
                else:
                    logger.debug(f"⚠️ Entity {entity_id} not found in states (may be unavailable)")

            if not relevant_states:
                logger.warning(f"⚠️ No states found for {len(entity_ids)} requested entities")
                return ""

            # Format states
            state_lines = [self._format_state_entry(state) for state in relevant_states]
            context = "DEVICE STATES:\n" + "\n".join(state_lines)

            # Truncate if too long (token management - limit to ~1000 tokens ~750 words ~5000 chars)
            max_length = 5000 if skip_truncation else 5000
            if len(context) > max_length:
                # Truncate by keeping first N entities that fit
                truncated_lines = []
                current_length = len("DEVICE STATES:\n")
                for line in state_lines:
                    if current_length + len(line) + 1 <= max_length - 20:  # Reserve space for "..."
                        truncated_lines.append(line)
                        current_length += len(line) + 1
                    else:
                        break
                context = "DEVICE STATES:\n" + "\n".join(truncated_lines)
                if len(state_lines) > len(truncated_lines):
                    context += f"\n... ({len(state_lines) - len(truncated_lines)} more entities)"
                logger.info(f"✅ Truncated state context from {len(state_lines)} to {len(truncated_lines)} entities")

            # Cache the result (only if not skipping truncation)
            if not skip_truncation:
                await self.context_builder._set_cached_value(
                    cache_key, context, self._cache_ttl
                )

            logger.info(f"✅ Generated state context for {len(relevant_states)} entities ({len(context)} chars)")
            return context

        except Exception as e:
            # Graceful degradation: log error but don't fail
            logger.warning(f"⚠️ Failed to fetch device states: {e}. State context will be unavailable.")
            return ""

    async def close(self) -> None:
        """Cleanup resources"""
        # Close clients if needed (they're shared, so just log)
        logger.debug("DeviceStateContextService closed")
