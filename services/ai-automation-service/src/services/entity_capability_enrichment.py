"""
Entity Capability Enrichment Service

Enriches entities with capabilities from HA State API and determines available services.
Epic 2025: Store entity capabilities and available services in database.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class EntityCapabilityEnrichment:
    """Service for enriching entities with capabilities from HA State API"""

    def __init__(self, ha_client, services_cache: dict[str, dict[str, Any]] | None = None):
        """
        Initialize the capability enrichment service.

        Args:
            ha_client: HomeAssistantClient instance for fetching entity state
            services_cache: Optional cache of available services per domain
        """
        self.ha_client = ha_client
        self.services_cache = services_cache or {}

    def _parse_capabilities_from_supported_features(
        self,
        supported_features: int,
        domain: str,
    ) -> list[str]:
        """
        Parse capabilities from supported_features bitmask.

        Args:
            supported_features: Bitmask of supported features
            domain: Entity domain (light, climate, cover, etc.)

        Returns:
            List of capability strings
        """
        capabilities = []

        if domain == "light":
            if supported_features & 1:  # SUPPORT_BRIGHTNESS
                capabilities.append("brightness")
            if supported_features & 2:  # SUPPORT_COLOR_TEMP
                capabilities.append("color_temp")
            if supported_features & 4:  # SUPPORT_COLOR
                capabilities.append("color")
            if supported_features & 8:  # SUPPORT_WHITE_VALUE
                capabilities.append("white_value")
            if supported_features & 16:  # SUPPORT_TRANSITION
                capabilities.append("transition")
            if supported_features & 32:  # SUPPORT_FLASH
                capabilities.append("flash")
            if supported_features & 64:  # SUPPORT_EFFECT
                capabilities.append("effect")
            if supported_features & 128:  # SUPPORT_COLOR_MODE
                capabilities.append("color_mode")

        elif domain == "climate":
            if supported_features & 1:  # SUPPORT_TARGET_TEMPERATURE
                capabilities.append("target_temperature")
            if supported_features & 2:  # SUPPORT_TARGET_TEMPERATURE_RANGE
                capabilities.append("temperature_range")
            if supported_features & 4:  # SUPPORT_TARGET_HUMIDITY
                capabilities.append("target_humidity")
            if supported_features & 8:  # SUPPORT_FAN_MODE
                capabilities.append("fan_mode")
            if supported_features & 16:  # SUPPORT_PRESET_MODE
                capabilities.append("preset_mode")
            if supported_features & 32:  # SUPPORT_SWING_MODE
                capabilities.append("swing_mode")
            if supported_features & 64:  # SUPPORT_AUX_HEAT
                capabilities.append("aux_heat")

        elif domain in ["cover", "blind", "shutter"]:
            if supported_features & 1:  # SUPPORT_OPEN
                capabilities.append("open")
            if supported_features & 2:  # SUPPORT_CLOSE
                capabilities.append("close")
            if supported_features & 4:  # SUPPORT_SET_POSITION
                capabilities.append("set_position")
            if supported_features & 8:  # SUPPORT_STOP
                capabilities.append("stop")
            if supported_features & 16:  # SUPPORT_OPEN_TILT
                capabilities.append("open_tilt")
            if supported_features & 32:  # SUPPORT_CLOSE_TILT
                capabilities.append("close_tilt")
            if supported_features & 64:  # SUPPORT_SET_TILT_POSITION
                capabilities.append("set_tilt_position")

        return capabilities

    def _determine_available_services(
        self,
        domain: str,
        capabilities: list[str],
        services_cache: dict[str, dict[str, Any]],
    ) -> list[str]:
        """
        Determine available services for an entity based on domain and capabilities.

        Args:
            domain: Entity domain
            capabilities: List of entity capabilities
            services_cache: Cache of available services per domain

        Returns:
            List of available service calls (e.g., ["light.turn_on", "light.turn_off"])
        """
        available_services = []

        # Get services for this domain from cache
        domain_services = services_cache.get(domain, {})

        # Common services for most domains
        if "turn_on" in domain_services:
            available_services.append(f"{domain}.turn_on")
        if "turn_off" in domain_services:
            available_services.append(f"{domain}.turn_off")
        if "toggle" in domain_services:
            available_services.append(f"{domain}.toggle")

        # Domain-specific services
        if domain == "light":
            if "set_brightness" in domain_services:
                available_services.append("light.set_brightness")
            if "set_color" in domain_services:
                available_services.append("light.set_color")
            if "set_color_temp" in domain_services:
                available_services.append("light.set_color_temp")
            if "set_effect" in domain_services:
                available_services.append("light.set_effect")

        elif domain == "climate":
            if "set_temperature" in domain_services:
                available_services.append("climate.set_temperature")
            if "set_humidity" in domain_services:
                available_services.append("climate.set_humidity")
            if "set_fan_mode" in domain_services:
                available_services.append("climate.set_fan_mode")
            if "set_preset_mode" in domain_services:
                available_services.append("climate.set_preset_mode")

        elif domain in ["cover", "blind", "shutter"]:
            if "open_cover" in domain_services:
                available_services.append(f"{domain}.open_cover")
            if "close_cover" in domain_services:
                available_services.append(f"{domain}.close_cover")
            if "set_cover_position" in domain_services:
                available_services.append(f"{domain}.set_cover_position")
            if "stop_cover" in domain_services:
                available_services.append(f"{domain}.stop_cover")

        return available_services

    async def enrich_entity_capabilities(
        self,
        entity_id: str,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Enrich entity with capabilities from State API.

        Fetches:
        - supported_features (bitmask)
        - Parsed capabilities (brightness, color, effect, etc.)
        - Available service calls based on domain + capabilities
        - Icon, device_class, unit_of_measurement

        Args:
            entity_id: Entity ID to enrich
            db_session: Optional database session for updating entity

        Returns:
            Dictionary with enriched capability data
        """
        try:
            # Fetch entity state from HA
            state_data = await self.ha_client.get_entity_state(entity_id)
            if not state_data:
                logger.warning(f"Entity {entity_id} not found in HA State API")
                return {}

            attributes = state_data.get("attributes", {})
            domain = entity_id.split(".")[0]

            # Parse supported_features
            supported_features = attributes.get("supported_features", 0)

            # Parse capabilities from supported_features
            capabilities = self._parse_capabilities_from_supported_features(
                supported_features,
                domain,
            )

            # Also check attributes for additional capabilities
            if attributes.get("brightness") is not None and "brightness" not in capabilities:
                capabilities.append("brightness")
            if attributes.get("color_temp") is not None and "color_temp" not in capabilities:
                capabilities.append("color_temp")
            if attributes.get("rgb_color") is not None and "rgb_color" not in capabilities:
                capabilities.append("rgb_color")
            if attributes.get("effect") is not None and "effect" not in capabilities:
                capabilities.append("effect")
            if attributes.get("effect_list") is not None and "effect" not in capabilities:
                capabilities.append("effect")

            # Determine available services from domain + services cache
            available_services = self._determine_available_services(
                domain,
                capabilities,
                self.services_cache,
            )

            # Extract other attributes
            icon = attributes.get("icon")
            device_class = attributes.get("device_class")
            unit_of_measurement = attributes.get("unit_of_measurement")

            enriched_data = {
                "supported_features": supported_features,
                "capabilities": capabilities,
                "available_services": available_services,
                "icon": icon,
                "device_class": device_class,
                "unit_of_measurement": unit_of_measurement,
            }

            # Update database via data-api HTTP endpoint if needed
            # Note: For now, we'll rely on the discovery service to update capabilities
            # This could be enhanced to call a data-api endpoint for updating entity capabilities
            logger.debug(f"✅ Enriched entity {entity_id} capabilities: {capabilities}, services: {available_services}")

            return enriched_data

        except Exception as e:
            logger.exception(f"Error enriching entity capabilities for {entity_id}: {e}")
            return {}

    async def enrich_multiple_entities(
        self,
        entity_ids: list[str],
        db_session: AsyncSession | None = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Batch enrich multiple entities IN PARALLEL.

        Args:
            entity_ids: List of entity IDs to enrich
            db_session: Optional database session for updating entities

        Returns:
            Dictionary mapping entity_id to enriched capability data
        """
        import asyncio

        enriched = {}

        async def enrich_one(entity_id: str) -> tuple:
            """Enrich a single entity"""
            try:
                enriched_data = await self.enrich_entity_capabilities(entity_id, db_session)
                return (entity_id, enriched_data)
            except Exception as e:
                logger.debug(f"Error enriching {entity_id}: {e}")
                return (entity_id, {})

        # Execute all enrichment tasks in parallel
        if entity_ids:
            tasks = [enrich_one(entity_id) for entity_id in entity_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.debug(f"Entity enrichment error: {result}")
                    continue
                entity_id, enriched_data = result
                if enriched_data:
                    enriched[entity_id] = enriched_data

        logger.info(f"Enriched {len(enriched)} out of {len(entity_ids)} entities (parallel)")

        return enriched

