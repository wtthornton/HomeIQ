"""
Helpers & Scenes Summary Service

Discovers available Home Assistant helpers and scenes for context injection.
Epic AI-19: Story AI19.6
"""

import logging
from collections import defaultdict
from typing import Any

from ..clients.ha_client import HomeAssistantClient
from ..config import Settings
from ..services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class HelpersScenesService:
    """
    Service for generating helpers and scenes summary.

    Provides awareness of reusable Home Assistant components for automation generation.
    """

    def __init__(self, settings: Settings, context_builder: ContextBuilder):
        """
        Initialize helpers and scenes service.

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
        self._cache_key = "helpers_scenes_summary"
        self._cache_ttl = 900  # 15 minutes (P1: Increased TTL - helpers/scenes change occasionally)

    async def get_summary(self, skip_truncation: bool = False) -> str:
        """
        Get helpers and scenes summary.

        Args:
            skip_truncation: If True, skip truncation (for debug display)

        Returns:
            Formatted summary like "input_boolean: morning_routine, night_mode (2 helpers); Scenes: Morning Scene, Evening Scene (2 scenes)"

        Raises:
            Exception: If unable to fetch helpers/scenes
        """
        # Check cache first (only if not skipping truncation, as cache may be truncated)
        if not skip_truncation:
            cached = await self.context_builder._get_cached_value(self._cache_key)
            if cached:
                logger.debug("✅ Using cached helpers/scenes summary")
                return cached

        try:
            # Fetch helpers and scenes from Home Assistant
            logger.info("🔧 Fetching helpers and scenes from Home Assistant...")
            helpers = await self.ha_client.get_helpers()
            scenes = await self.ha_client.get_scenes()

            summary_parts = []

            # Group helpers by type with enhanced information
            if helpers:
                helpers_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for helper in helpers:
                    helper_type = helper.get("type", "unknown")
                    helper_id = helper.get("id", "")
                    entity_id = helper.get("entity_id", "")
                    friendly_name = helper.get("name", helper_id)
                    state = helper.get("state", "unknown")

                    if helper_id:
                        helpers_by_type[helper_type].append({
                            "id": helper_id,
                            "entity_id": entity_id,
                            "friendly_name": friendly_name,
                            "state": state
                        })

                # Format helpers by type (optimized: names only)
                helper_parts = []
                for helper_type in sorted(helpers_by_type.keys()):
                    helper_list = sorted(helpers_by_type[helper_type], key=lambda x: x["id"])
                    count = len(helper_list)

                    # Simple format: just friendly names (token-efficient)
                    # Limit to 10 per type unless skipping truncation
                    limit = len(helper_list) if skip_truncation else min(10, len(helper_list))
                    helper_names = [helper['friendly_name'] for helper in helper_list[:limit]]
                    names_str = ", ".join(helper_names)
                    if not skip_truncation and len(helper_list) > 10:
                        helper_parts.append(f"{helper_type}: {names_str} ... ({count})")
                    else:
                        helper_parts.append(f"{helper_type}: {names_str} ({count})")

                if helper_parts:
                    summary_parts.append("\n".join(helper_parts))
            else:
                summary_parts.append("No helpers found")

            # Format scenes (optimized: names only)
            if scenes:
                scene_names = []
                for scene in scenes:
                    # Prefer friendly_name, fallback to entity_id name part, then id
                    scene_name = (
                        scene.get("name") or
                        scene.get("entity_id", "").split(".", 1)[1] if "." in scene.get("entity_id", "") else
                        scene.get("id", "")
                    )
                    if scene_name:
                        scene_names.append(scene_name)

                if scene_names:
                    # Limit to 15 scenes (token-efficient) unless skipping truncation
                    if not skip_truncation and len(scene_names) > 15:
                        scene_names = sorted(scene_names)[:15]
                        scenes_str = ", ".join(scene_names) + f" ... ({len(scenes)} total)"
                    else:
                        scenes_str = ", ".join(sorted(scene_names))
                    summary_parts.append(f"Scenes: {scenes_str}")
                else:
                    summary_parts.append("No scenes found")
            else:
                summary_parts.append("No scenes found")

            summary = "\n".join(summary_parts)

            # Truncate if too long (optimized: max 1000 chars for token efficiency)
            # Skip truncation for debug display
            if not skip_truncation and len(summary) > 1000:
                summary = summary[:1000] + "... (truncated)"

            # Cache the result (only if not skipping truncation)
            if not skip_truncation:
                await self.context_builder._set_cached_value(
                    self._cache_key, summary, self._cache_ttl
                )

            logger.info(f"✅ Generated helpers/scenes summary ({len(summary)} chars)")
            return summary

        except Exception as e:
            logger.error(f"❌ Error generating helpers/scenes summary: {e}", exc_info=True)
            # Return fallback
            return "Helpers and scenes unavailable. Please check Home Assistant connection."

    async def close(self):
        """Close service resources"""
        await self.ha_client.close()

