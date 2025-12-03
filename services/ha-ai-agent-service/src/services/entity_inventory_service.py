"""
Entity Inventory Summary Service

Aggregates entity counts by domain and area for context injection.
Epic AI-19: Story AI19.2
Enhanced: Added friendly names, device_ids, aliases, labels, states, and device metadata
"""

import logging
from collections import defaultdict
from typing import Any

from ..clients.data_api_client import DataAPIClient
from ..clients.ha_client import HomeAssistantClient
from ..config import Settings
from ..services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class EntityInventoryService:
    """
    Service for generating entity inventory summaries.

    Aggregates entity counts by domain and area with enhanced metadata:
    - Entity friendly names for automation descriptions
    - Device IDs for target.device_id usage
    - Entity aliases for entity resolution (2025 feature)
    - Entity labels for organizational filtering
    - Current states for context
    - Device metadata (manufacturer, model)
    """

    def __init__(self, settings: Settings, context_builder: ContextBuilder):
        """
        Initialize entity inventory service.

        Args:
            settings: Application settings
            context_builder: Context builder for cache access
        """
        self.settings = settings
        self.context_builder = context_builder
        self.data_api_client = DataAPIClient(base_url=settings.data_api_url)
        self.ha_client = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token
        )
        self._cache_key = "entity_inventory_summary"
        self._cache_ttl = 300  # 5 minutes

    async def get_summary(self) -> str:
        """
        Get enhanced entity inventory summary with friendly names, device IDs, aliases, labels, and states.

        Returns:
            Formatted summary with entity counts, friendly names, device IDs, and key metadata

        Raises:
            Exception: If unable to fetch or process entities
        """
        # Check cache first
        cached = await self.context_builder._get_cached_value(self._cache_key)
        if cached:
            logger.debug("✅ Using cached entity inventory summary")
            return cached

        try:
            # Fetch all entities from data-api
            logger.info("📊 Fetching entities for inventory summary...")
            entities = await self.data_api_client.fetch_entities(limit=10000)

            if not entities:
                summary = "No entities found in system."
                await self.context_builder._set_cached_value(
                    self._cache_key, summary, self._cache_ttl
                )
                return summary

            # Fetch entity states for current state information
            logger.info("📊 Fetching entity states...")
            try:
                states = await self.ha_client.get_states()
                state_map = {state.get("entity_id"): state for state in states}
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch states: {e}")
                state_map = {}

            # Fetch areas for friendly name mapping
            try:
                areas = await self.ha_client.get_area_registry()
                area_name_map = {
                    area.get("area_id"): area.get("name", area.get("area_id", ""))
                    for area in areas
                    if area.get("area_id")
                }
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch areas: {e}")
                area_name_map = {}

            # Aggregate by domain and area with enhanced metadata
            domain_area_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
            domain_totals: dict[str, int] = defaultdict(int)
            defaultdict(list)

            # Sample entities per domain for detailed examples (max 5 per domain)
            domain_samples: dict[str, list[dict[str, Any]]] = defaultdict(list)

            for entity in entities:
                domain = entity.get("domain", "unknown")
                area_id = entity.get("area_id") or "unassigned"
                domain_area_counts[domain][area_id] += 1
                domain_totals[domain] += 1

                # Collect sample entities for detailed info
                if len(domain_samples[domain]) < 5:
                    entity_state = state_map.get(entity.get("entity_id", ""), {})
                    sample = {
                        "entity_id": entity.get("entity_id", ""),
                        "friendly_name": entity.get("friendly_name") or entity.get("name") or entity.get("entity_id", "").split(".", 1)[1] if "." in entity.get("entity_id", "") else entity.get("entity_id", ""),
                        "device_id": entity.get("device_id"),
                        "area_id": area_id,
                        "state": entity_state.get("state", "unknown"),
                        "aliases": entity.get("aliases", [])[:3],  # Limit to 3 aliases
                        "labels": entity.get("labels", [])[:3],  # Limit to 3 labels
                        "device_class": entity.get("device_class"),
                        "icon": entity.get("icon")
                    }
                    domain_samples[domain].append(sample)

            # Format summary with enhanced information
            summary_parts = []
            for domain in sorted(domain_totals.keys()):
                total = domain_totals[domain]
                area_counts = domain_area_counts[domain]

                # Format area breakdown with friendly names
                area_parts = []
                for area_id in sorted(area_counts.keys()):
                    count = area_counts[area_id]
                    area_name = area_name_map.get(area_id, area_id.replace("_", " ").title() if area_id != "unassigned" else "unassigned")
                    area_parts.append(f"{area_name}: {count}")

                area_str = ", ".join(area_parts)
                domain_display = domain.replace("_", " ").title()

                # Build domain summary line
                domain_line = f"{domain_display}: {total} entities ({area_str})"

                # Add sample entity details for key domains (light, switch, sensor, climate, cover, lock, fan)
                if domain in ["light", "switch", "sensor", "climate", "cover", "lock", "fan"] and domain_samples[domain]:
                    samples = domain_samples[domain][:3]  # Show max 3 examples
                    sample_parts = []
                    for sample in samples:
                        sample_info = f"{sample['friendly_name']} ({sample['entity_id']}"
                        if sample.get("device_id"):
                            sample_info += f", device_id: {sample['device_id']}"
                        if sample.get("state") and sample["state"] != "unknown":
                            sample_info += f", state: {sample['state']}"
                        sample_info += ")"
                        if sample.get("aliases"):
                            sample_info += f" [aliases: {', '.join(sample['aliases'][:2])}]"
                        sample_parts.append(sample_info)
                    if sample_parts:
                        domain_line += f"\n  Examples: {', '.join(sample_parts)}"

                summary_parts.append(domain_line)

            summary = "\n".join(summary_parts)

            # Truncate if too long (max 3000 chars for enhanced version)
            if len(summary) > 3000:
                summary = summary[:3000] + "... (truncated)"

            # Cache the result
            await self.context_builder._set_cached_value(
                self._cache_key, summary, self._cache_ttl
            )

            logger.info(f"✅ Generated enhanced entity inventory summary ({len(summary)} chars)")
            return summary

        except Exception as e:
            logger.error(f"❌ Error generating entity inventory summary: {e}", exc_info=True)
            # Return fallback summary
            return "Entity inventory unavailable. Please check data-api service."

    async def close(self):
        """Close service resources"""
        await self.data_api_client.close()
        await self.ha_client.close()

