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
        self._cache_ttl = 600  # 10 minutes

    async def get_summary(self) -> str:
        """
        Get helpers and scenes summary.

        Returns:
            Formatted summary like "input_boolean: morning_routine, night_mode (2 helpers); Scenes: Morning Scene, Evening Scene (2 scenes)"

        Raises:
            Exception: If unable to fetch helpers/scenes
        """
        # Check cache first
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

                # Format helpers by type with enhanced info
                helper_parts = []
                for helper_type in sorted(helpers_by_type.keys()):
                    helper_list = sorted(helpers_by_type[helper_type], key=lambda x: x["id"])
                    count = len(helper_list)

                    # Format helper descriptions
                    helper_descriptions = []
                    for helper in helper_list[:10]:  # Limit to 10 per type
                        helper_desc = f"{helper['friendly_name']} ({helper['id']}"
                        if helper.get("entity_id"):
                            helper_desc += f", entity_id: {helper['entity_id']}"
                        if helper.get("state") and helper["state"] != "unknown":
                            helper_desc += f", state: {helper['state']}"
                        helper_desc += ")"
                        helper_descriptions.append(helper_desc)

                    names_str = ", ".join(helper_descriptions)
                    helper_parts.append(f"{helper_type}: {names_str} ({count} helpers)")

                if helper_parts:
                    summary_parts.append("\n".join(helper_parts))
            else:
                summary_parts.append("No helpers found")

            # Format scenes with enhanced information
            if scenes:
                scene_descriptions = []
                for scene in scenes:
                    # Prefer friendly_name, fallback to entity_id name part, then id
                    scene_name = (
                        scene.get("name") or
                        scene.get("entity_id", "").split(".", 1)[1] if "." in scene.get("entity_id", "") else
                        scene.get("id", "")
                    )
                    entity_id = scene.get("entity_id", "")
                    state = scene.get("state", "unknown")

                    if scene_name:
                        scene_desc = scene_name
                        if entity_id:
                            scene_desc += f" (entity_id: {entity_id}"
                            if state != "unknown":
                                scene_desc += f", state: {state}"
                            scene_desc += ")"
                        scene_descriptions.append(scene_desc)

                if scene_descriptions:
                    # Limit to 20 scenes to avoid overwhelming context
                    if len(scene_descriptions) > 20:
                        scene_descriptions = sorted(scene_descriptions)[:20]
                        scenes_str = ", ".join(scene_descriptions) + f" ... ({len(scenes)} total scenes)"
                    else:
                        scenes_str = ", ".join(sorted(scene_descriptions))
                        count = len(scene_descriptions)
                        scenes_str += f" ({count} scenes)"
                    summary_parts.append(f"Scenes: {scenes_str}")
                else:
                    summary_parts.append("No scenes found")
            else:
                summary_parts.append("No scenes found")

            summary = "\n".join(summary_parts)

            # Truncate if too long (max 2000 chars for enhanced version)
            if len(summary) > 2000:
                summary = summary[:2000] + "... (truncated)"

            # Cache the result
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

