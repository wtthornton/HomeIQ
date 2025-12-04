"""
Entity Attributes Service

Extracts entity state attributes (effect_list, preset_list, themes, etc.) for context injection.
Epic AI-19: Enhancement - Extract entity state attributes
"""

import logging
from collections import defaultdict
from typing import Any

from ..clients.data_api_client import DataAPIClient
from ..clients.ha_client import HomeAssistantClient
from ..config import Settings
from ..services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class EntityAttributesService:
    """
    Service for extracting and formatting entity state attributes.
    
    Extracts dynamic attributes from entity states:
    - effect_list for lights (WLED, Hue effects)
    - preset_list, theme_list if available
    - supported_color_modes
    - Current effect/preset values
    """

    def __init__(self, settings: Settings, context_builder: ContextBuilder):
        """
        Initialize entity attributes service.

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
        self._cache_key = "entity_attributes_summary"
        self._cache_ttl = 300  # 5 minutes (same as entity inventory)

    async def get_summary(self) -> str:
        """
        Get entity attributes summary with effect lists, presets, themes, etc.

        Returns:
            Formatted summary with entity attributes for lights and other devices

        Raises:
            Exception: If unable to fetch or process attributes
        """
        # Check cache first
        cached = await self.context_builder._get_cached_value(self._cache_key)
        if cached:
            logger.debug("✅ Using cached entity attributes summary")
            return cached

        try:
            # Fetch entity states from Home Assistant
            logger.info("📊 Fetching entity states for attributes...")
            states = await self.ha_client.get_states()
            
            if not states:
                summary = "No entity states available."
                await self.context_builder._set_cached_value(
                    self._cache_key, summary, self._cache_ttl
                )
                return summary

            # Group attributes by domain
            domain_attributes: dict[str, list[dict[str, Any]]] = defaultdict(list)

            for state in states:
                entity_id = state.get("entity_id", "")
                if not entity_id:
                    continue
                
                domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
                attributes = state.get("attributes", {})
                
                # Extract relevant attributes based on domain
                entity_attrs = {}
                
                if domain == "light":
                    # Extract light-specific attributes
                    effect_list = attributes.get("effect_list", [])
                    if effect_list:
                        entity_attrs["effect_list"] = effect_list
                        entity_attrs["effect_list_count"] = len(effect_list)
                    
                    current_effect = attributes.get("effect")
                    if current_effect:
                        entity_attrs["current_effect"] = current_effect
                    
                    supported_color_modes = attributes.get("supported_color_modes", [])
                    if supported_color_modes:
                        entity_attrs["supported_color_modes"] = supported_color_modes
                    
                    # Extract preset/theme lists if available
                    preset_list = attributes.get("preset_list", [])
                    if preset_list:
                        entity_attrs["preset_list"] = preset_list
                    
                    theme_list = attributes.get("theme_list", [])
                    if theme_list:
                        entity_attrs["theme_list"] = theme_list
                
                # Only add if we found relevant attributes
                if entity_attrs:
                    entity_attrs["entity_id"] = entity_id
                    entity_attrs["friendly_name"] = attributes.get("friendly_name", entity_id.split(".")[-1] if "." in entity_id else entity_id)
                    domain_attributes[domain].append(entity_attrs)

            # Format summary
            summary_parts = []
            
            # Focus on light domain (most common use case)
            if "light" in domain_attributes:
                light_attrs = domain_attributes["light"]
                summary_parts.append("LIGHT ENTITY ATTRIBUTES:")
                
                # Limit to 10 lights to avoid overwhelming context
                for light_attr in light_attrs[:10]:
                    entity_id = light_attr["entity_id"]
                    friendly_name = light_attr.get("friendly_name", entity_id)
                    attr_parts = [f"{friendly_name} ({entity_id}):"]
                    
                    # Add effect_list
                    if "effect_list" in light_attr:
                        effect_list = light_attr["effect_list"]
                        effect_count = light_attr.get("effect_list_count", len(effect_list))
                        if effect_count <= 10:
                            effects_str = ", ".join(effect_list)
                            attr_parts.append(f"  effect_list: [{effects_str}]")
                        else:
                            effects_preview = ", ".join(effect_list[:8])
                            attr_parts.append(f"  effect_list: [{effects_preview}, ... ({effect_count} total)]")
                    
                    # Add current effect
                    if "current_effect" in light_attr:
                        attr_parts.append(f"  current_effect: {light_attr['current_effect']}")
                    
                    # Add color modes
                    if "supported_color_modes" in light_attr:
                        color_modes = light_attr["supported_color_modes"]
                        attr_parts.append(f"  supported_color_modes: [{', '.join(color_modes)}]")
                    
                    # Add preset/theme lists if available
                    if "preset_list" in light_attr:
                        preset_list = light_attr["preset_list"]
                        if len(preset_list) <= 10:
                            presets_str = ", ".join(preset_list)
                            attr_parts.append(f"  preset_list: [{presets_str}]")
                        else:
                            presets_preview = ", ".join(preset_list[:5])
                            attr_parts.append(f"  preset_list: [{presets_preview}, ... ({len(preset_list)} total)]")
                    
                    if "theme_list" in light_attr:
                        theme_list = light_attr["theme_list"]
                        if len(theme_list) <= 10:
                            themes_str = ", ".join(theme_list)
                            attr_parts.append(f"  theme_list: [{themes_str}]")
                        else:
                            themes_preview = ", ".join(theme_list[:5])
                            attr_parts.append(f"  theme_list: [{themes_preview}, ... ({len(theme_list)} total)]")
                    
                    summary_parts.append("\n".join(attr_parts))
                
                if len(light_attrs) > 10:
                    summary_parts.append(f"... ({len(light_attrs)} total lights with attributes)")

            summary = "\n".join(summary_parts)
            
            # Truncate if too long (max 2500 chars)
            if len(summary) > 2500:
                summary = summary[:2500] + "... (truncated)"

            # Cache the result
            await self.context_builder._set_cached_value(
                self._cache_key, summary, self._cache_ttl
            )

            logger.info(f"✅ Generated entity attributes summary ({len(summary)} chars)")
            return summary

        except Exception as e:
            logger.error(f"❌ Error generating entity attributes summary: {e}", exc_info=True)
            # Return fallback
            return "Entity attributes unavailable. Please check Home Assistant connection."

    async def close(self):
        """Close service resources"""
        await self.data_api_client.close()
        await self.ha_client.close()

