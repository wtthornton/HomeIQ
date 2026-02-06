"""
Areas/Rooms List Service

Fetches all areas from Home Assistant and formats them for context injection.
Epic AI-19: Story AI19.3
Enhanced: Added friendly names, aliases, icons, and labels mapping
"""

import logging

from ..clients.data_api_client import DataAPIClient
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
            access_token=settings.ha_token.get_secret_value()
        )
        self.data_api_client = DataAPIClient(base_url=settings.data_api_url)
        self._cache_key = "areas_list"
        self._cache_ttl = 1800  # 30 minutes (P1: Increased TTL for static data - areas rarely change)

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
            # 2025 Optimization: Fetch areas from Data API (local/cached) instead of HA API
            logger.info("🏠 Fetching areas from Data API (local/cached)...")
            areas = await self.data_api_client.get_areas()

            if not areas:
                # Fallback to entity-based extraction
                logger.info("🔄 No areas from Data API, falling back to entity extraction...")
                return await self._extract_areas_from_entities()

            # Format areas (optimized: simple area_id → name mapping)
            area_parts = []

            for area in areas:
                area_id = area.get("area_id", "")
                name = area.get("name") or area_id

                if not area_id:
                    continue

                # Simple format: area_id: name (token-efficient)
                area_parts.append(f"{area_id}: {name}")

            # Simple comma-separated list
            areas_str = ", ".join(sorted(area_parts))

            # Cache the result
            await self.context_builder._set_cached_value(
                self._cache_key, areas_str, self._cache_ttl
            )

            logger.info(f"✅ Generated optimized areas list: {len(areas)} areas ({len(areas_str)} chars)")
            return areas_str

        except Exception as e:
            logger.warning(f"⚠️ Error fetching areas from area registry: {e}")
            logger.info("🔄 Falling back to entity-based area extraction...")
            
            # Fallback: Extract areas from entity area_id
            try:
                return await self._extract_areas_from_entities()
            except Exception as fallback_error:
                logger.error(f"❌ Fallback area extraction also failed: {fallback_error}", exc_info=True)
                return "Areas unavailable. Please check Home Assistant connection."
    
    async def _extract_areas_from_entities(self) -> str:
        """
        Fallback: Extract areas from entity area_id values.
        
        Returns:
            Formatted areas list string
        """
        try:
            # Fetch entities from data-api
            entities = await self.data_api_client.fetch_entities(limit=1000)
            
            if not entities:
                return "No areas found"
            
            # Collect unique area_ids from entities
            area_ids = set()
            for entity in entities:
                area_id = entity.get("area_id")
                if area_id and area_id != "unassigned":
                    area_ids.add(area_id)
            
            if not area_ids:
                return "No areas found"
            
            # Format areas (use area_id as name if no friendly name available)
            area_parts = []
            for area_id in sorted(area_ids):
                # Convert area_id to friendly name (replace underscores with spaces, title case)
                friendly_name = area_id.replace("_", " ").title()
                area_parts.append(f"{friendly_name} (area_id: {area_id})")
            
            areas_str = ", ".join(area_parts)
            
            # Cache the result
            await self.context_builder._set_cached_value(
                self._cache_key, areas_str, self._cache_ttl
            )
            
            logger.info(f"✅ Extracted {len(area_ids)} areas from entities")
            return areas_str
            
        except Exception as e:
            logger.error(f"❌ Error extracting areas from entities: {e}", exc_info=True)
            return "Areas unavailable."

    async def close(self):
        """Close service resources"""
        await self.ha_client.close()

