"""
Areas/Rooms List Service

Fetches all areas from Home Assistant and formats them for context injection.
Epic AI-19: Story AI19.3
Enhanced: Added friendly names, aliases, icons, and labels mapping
"""

import logging

from ..clients.ha_client import HomeAssistantClient
from ..config import Settings
from ..services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class AreasService:
    """
    Service for fetching and formatting areas/rooms list.

    Formats areas with friendly names, aliases, icons, and labels for context injection.
    Provides area_id to friendly_name mapping for automation target usage.
    """

    def __init__(self, settings: Settings, context_builder: ContextBuilder):
        """
        Initialize areas service.

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
        self._cache_key = "areas_list"
        self._cache_ttl = 600  # 10 minutes

    async def get_areas_list(self) -> str:
        """
        Get formatted areas list with enhanced metadata.

        Returns:
            Formatted areas list with friendly names, area_ids, aliases, and icons
            Format: "Office (area_id: office, aliases: workspace, study), Kitchen (area_id: kitchen, icon: mdi:chef-hat)"

        Raises:
            Exception: If unable to fetch areas
        """
        # Check cache first
        cached = await self.context_builder._get_cached_value(self._cache_key)
        if cached:
            logger.debug("✅ Using cached areas list")
            return cached

        try:
            # Fetch areas from Home Assistant
            logger.info("🏠 Fetching areas from Home Assistant...")
            areas = await self.ha_client.get_area_registry()

            if not areas:
                areas_str = "No areas found"
                await self.context_builder._set_cached_value(
                    self._cache_key, areas_str, self._cache_ttl
                )
                return areas_str

            # Format areas with enhanced information
            area_parts = []
            area_mapping_parts = []

            for area in areas:
                area_id = area.get("area_id", "")
                name = area.get("name") or area_id
                aliases = area.get("aliases", [])
                icon = area.get("icon")
                labels = area.get("labels", [])

                if not area_id:
                    continue

                # Build area description
                area_desc = name
                metadata_parts = [f"area_id: {area_id}"]

                if aliases:
                    metadata_parts.append(f"aliases: {', '.join(aliases[:3])}")  # Limit to 3 aliases
                if icon:
                    metadata_parts.append(f"icon: {icon}")
                if labels:
                    metadata_parts.append(f"labels: {', '.join(labels[:3])}")  # Limit to 3 labels

                area_info = f"{area_desc} ({', '.join(metadata_parts)})"
                area_parts.append(area_info)

                # Also build mapping for quick reference
                area_mapping_parts.append(f"{area_id} → {name}")

            # Combine: list format + mapping
            areas_str = ", ".join(sorted(area_parts))
            if area_mapping_parts:
                areas_str += f"\nArea ID Mapping: {', '.join(sorted(area_mapping_parts))}"

            # Cache the result
            await self.context_builder._set_cached_value(
                self._cache_key, areas_str, self._cache_ttl
            )

            logger.info(f"✅ Generated enhanced areas list: {len(areas)} areas")
            return areas_str

        except Exception as e:
            logger.error(f"❌ Error fetching areas: {e}", exc_info=True)
            # Return fallback
            return "Areas unavailable. Please check Home Assistant connection."

    async def close(self):
        """Close service resources"""
        await self.ha_client.close()

