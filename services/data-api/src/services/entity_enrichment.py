"""
Entity Enrichment Service
Populates entity capabilities and available services from Home Assistant API

Phase 1.1: Fetches entity state from HA to extract capabilities
Phase 1.1: Maps available services from Service table to entity domains
"""

import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class EntityEnrichmentService:
    """Service for enriching entities with capabilities and available services"""

    def __init__(self):
        """Initialize entity enrichment service"""
        self.ha_url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
        self.ha_token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HA API session"""
        if self._session is None or self._session.closed:
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
                raise_for_status=False
            )
        return self._session

    async def enrich_entity_capabilities(
        self,
        entity_id: str,
        domain: str
    ) -> dict[str, Any]:
        """
        Enrich entity with capabilities from HA state API.
        
        Args:
            entity_id: Entity identifier (e.g., "light.kitchen")
            domain: Entity domain (e.g., "light")
            
        Returns:
            Dictionary with:
            - supported_features: int | None
            - capabilities: list[str] | None
        """
        if not self.ha_url or not self.ha_token:
            logger.debug(f"HA_URL or HA_TOKEN not configured, skipping capability enrichment for {entity_id}")
            return {
                "supported_features": None,
                "capabilities": None
            }

        try:
            session = await self._get_session()
            url = f"{self.ha_url}/api/states/{entity_id}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    state = await response.json()
                    attributes = state.get("attributes", {})
                    
                    # Extract supported_features (bitmask)
                    supported_features = attributes.get("supported_features")
                    if supported_features is not None and not isinstance(supported_features, int):
                        try:
                            supported_features = int(supported_features)
                        except (ValueError, TypeError):
                            supported_features = None
                    
                    # Extract capabilities list from attributes
                    capabilities = self._extract_capabilities(domain, attributes, supported_features)
                    
                    return {
                        "supported_features": supported_features,
                        "capabilities": capabilities
                    }
                else:
                    logger.debug(f"Failed to fetch state for {entity_id}: {response.status}")
                    return {
                        "supported_features": None,
                        "capabilities": None
                    }
                    
        except Exception as e:
            logger.warning(f"Error enriching capabilities for {entity_id}: {e}")
            return {
                "supported_features": None,
                "capabilities": None
            }

    def _extract_capabilities(
        self,
        domain: str,
        attributes: dict[str, Any],
        supported_features: int | None
    ) -> list[str]:
        """
        Extract capabilities list from entity attributes and supported_features.
        
        Args:
            domain: Entity domain (e.g., "light", "switch")
            attributes: Entity attributes from HA state
            supported_features: Supported features bitmask
            
        Returns:
            List of capability strings (e.g., ["brightness", "color", "effect"])
        """
        capabilities = []
        
        # Domain-specific capability extraction
        if domain == "light":
            # Light capabilities from supported_features bitmask
            if supported_features is not None:
                if supported_features & 1:  # SUPPORT_BRIGHTNESS
                    capabilities.append("brightness")
                if supported_features & 2:  # SUPPORT_COLOR_TEMP
                    capabilities.append("color_temp")
                if supported_features & 4:  # SUPPORT_EFFECT
                    capabilities.append("effect")
                if supported_features & 16:  # SUPPORT_TRANSITION
                    capabilities.append("transition")
                if supported_features & 128:  # SUPPORT_COLOR
                    capabilities.append("color")
                if supported_features & 256:  # SUPPORT_WHITE_VALUE
                    capabilities.append("white_value")
            
            # Check attributes for additional capabilities
            if attributes.get("brightness") is not None:
                if "brightness" not in capabilities:
                    capabilities.append("brightness")
            if attributes.get("rgb_color") or attributes.get("hs_color") or attributes.get("xy_color"):
                if "color" not in capabilities:
                    capabilities.append("color")
            if attributes.get("color_temp") is not None:
                if "color_temp" not in capabilities:
                    capabilities.append("color_temp")
            if attributes.get("effect_list"):
                if "effect" not in capabilities:
                    capabilities.append("effect")
                    
        elif domain == "switch":
            # Switch capabilities
            capabilities.append("on_off")
            
        elif domain == "sensor":
            # Sensor capabilities from device_class
            device_class = attributes.get("device_class")
            if device_class:
                capabilities.append(f"measure_{device_class}")
            
            # State class capabilities
            state_class = attributes.get("state_class")
            if state_class:
                capabilities.append(f"state_{state_class}")
                
        elif domain == "cover":
            # Cover capabilities from supported_features
            if supported_features is not None:
                if supported_features & 1:  # SUPPORT_OPEN
                    capabilities.append("open")
                if supported_features & 2:  # SUPPORT_CLOSE
                    capabilities.append("close")
                if supported_features & 4:  # SUPPORT_SET_POSITION
                    capabilities.append("position")
                if supported_features & 8:  # SUPPORT_STOP
                    capabilities.append("stop")
                    
        elif domain == "fan":
            # Fan capabilities
            if supported_features is not None:
                if supported_features & 1:  # SUPPORT_SET_SPEED
                    capabilities.append("speed")
                if supported_features & 2:  # SUPPORT_OSCILLATE
                    capabilities.append("oscillate")
                if supported_features & 4:  # SUPPORT_DIRECTION
                    capabilities.append("direction")
        
        # Add capabilities from attributes that indicate features
        if attributes.get("volume_level") is not None:
            capabilities.append("volume")
        if attributes.get("media_content_type"):
            capabilities.append("media")
        if attributes.get("temperature"):
            capabilities.append("temperature_control")
        if attributes.get("humidity"):
            capabilities.append("humidity_control")
            
        return sorted(list(set(capabilities))) if capabilities else None

    async def get_available_services_for_domain(
        self,
        domain: str,
        db
    ) -> list[str]:
        """
        Get available services for an entity domain from Service table.
        
        Args:
            domain: Entity domain (e.g., "light")
            db: Database session (AsyncSession)
            
        Returns:
            List of service call strings (e.g., ["light.turn_on", "light.turn_off"])
        """
        try:
            from sqlalchemy import select
            from ..models import Service
            
            # Query services for this domain
            result = await db.execute(
                select(Service.service_name).where(Service.domain == domain)
            )
            service_names = result.scalars().all()
            
            # Format as domain.service_name
            available_services = [f"{domain}.{name}" for name in service_names]
            
            return available_services if available_services else None
            
        except Exception as e:
            logger.warning(f"Error fetching available services for domain {domain}: {e}")
            return None

    async def enrich_entity(
        self,
        entity_id: str,
        domain: str,
        db
    ) -> dict[str, Any]:
        """
        Enrich entity with both capabilities and available services.
        
        Args:
            entity_id: Entity identifier
            domain: Entity domain
            db: Database session (AsyncSession)
            
        Returns:
            Dictionary with:
            - supported_features: int | None
            - capabilities: list[str] | None
            - available_services: list[str] | None
        """
        # Fetch capabilities from HA state API
        capabilities_data = await self.enrich_entity_capabilities(entity_id, domain)
        
        # Fetch available services from Service table
        available_services = await self.get_available_services_for_domain(domain, db)
        
        return {
            "supported_features": capabilities_data.get("supported_features"),
            "capabilities": capabilities_data.get("capabilities"),
            "available_services": available_services
        }

    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()


# Singleton instance
_enrichment_service: EntityEnrichmentService | None = None


def get_entity_enrichment_service() -> EntityEnrichmentService:
    """Get singleton entity enrichment service instance"""
    global _enrichment_service
    if _enrichment_service is None:
        _enrichment_service = EntityEnrichmentService()
    return _enrichment_service
