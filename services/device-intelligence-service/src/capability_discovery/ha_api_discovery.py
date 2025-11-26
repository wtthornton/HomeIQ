"""
HA API-Only Capability Discovery
Phase 3.2: Infer capabilities from HA Entity Registry and State API
"""

import json
import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class HACapabilityDiscoverer:
    """Discovers device capabilities from Home Assistant API only"""

    def __init__(self):
        """Initialize capability discoverer"""
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

    async def discover_capabilities(
        self,
        device_id: str,
        entity_ids: list[str]
    ) -> dict[str, Any]:
        """
        Discover device capabilities from HA API.
        
        Args:
            device_id: Device identifier
            entity_ids: List of entity IDs for this device
            
        Returns:
            Dictionary of discovered capabilities
        """
        if not self.ha_url or not self.ha_token:
            return {"capabilities": [], "features": {}}

        try:
            session = await self._get_session()
            
            # Get entity registry
            registry_url = f"{self.ha_url}/api/config/entity_registry/list"
            async with session.get(registry_url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to get entity registry: HTTP {response.status}")
                    return {"capabilities": [], "features": {}}
                
                registry_data = await response.json()
                entities = registry_data.get("entities", [])
            
            # Build capabilities from entities
            capabilities = []
            features = {}
            
            for entity_id in entity_ids:
                # Find entity in registry
                entity_info = next(
                    (e for e in entities if e.get("entity_id") == entity_id),
                    None
                )
                
                if not entity_info:
                    continue
                
                # Get entity state for attributes
                state_url = f"{self.ha_url}/api/states/{entity_id}"
                async with session.get(state_url) as state_response:
                    if state_response.status == 200:
                        state_data = await state_response.json()
                        attrs = state_data.get("attributes", {})
                        
                        # Infer capabilities from domain
                        domain = entity_id.split(".")[0] if "." in entity_id else None
                        if domain:
                            domain_caps = self._infer_domain_capabilities(domain, attrs)
                            capabilities.extend(domain_caps)
                            
                            # Extract features from attributes
                            entity_features = self._extract_features(domain, attrs)
                            features[entity_id] = entity_features
            
            # Get device class and state class from entities
            device_classes = set()
            state_classes = set()
            for entity_info in entities:
                if entity_info.get("entity_id") in entity_ids:
                    device_class = entity_info.get("device_class")
                    if device_class:
                        device_classes.add(device_class)
                    # State class might be in attributes
                    state_data = await self._get_entity_state(session, entity_info.get("entity_id"))
                    if state_data:
                        state_class = state_data.get("attributes", {}).get("state_class")
                        if state_class:
                            state_classes.add(state_class)
            
            return {
                "capabilities": list(set(capabilities)),  # Remove duplicates
                "features": features,
                "device_classes": list(device_classes),
                "state_classes": list(state_classes)
            }
            
        except Exception as e:
            logger.error(f"Error discovering capabilities for {device_id}: {e}")
            return {"capabilities": [], "features": {}}

    def _infer_domain_capabilities(self, domain: str, attributes: dict[str, Any]) -> list[str]:
        """Infer capabilities from entity domain"""
        capabilities = []
        
        if domain == "light":
            capabilities.append("lighting_control")
            if "brightness" in attributes:
                capabilities.append("dimming")
            if "rgb_color" in attributes or "hs_color" in attributes:
                capabilities.append("color_control")
            if "color_temp" in attributes:
                capabilities.append("color_temperature")
            if "effect" in attributes:
                capabilities.append("effects")
        
        elif domain == "switch":
            capabilities.append("on_off_control")
            if "current_power_w" in attributes or "power" in attributes:
                capabilities.append("power_monitoring")
        
        elif domain == "sensor":
            capabilities.append("sensing")
            device_class = attributes.get("device_class")
            if device_class == "battery":
                capabilities.append("battery_powered")
            elif device_class == "temperature":
                capabilities.append("temperature_sensing")
            elif device_class == "humidity":
                capabilities.append("humidity_sensing")
        
        elif domain == "climate":
            capabilities.append("climate_control")
            if "temperature" in attributes:
                capabilities.append("temperature_control")
            if "humidity" in attributes:
                capabilities.append("humidity_control")
            if "fan_mode" in attributes:
                capabilities.append("fan_control")
        
        elif domain == "cover":
            capabilities.append("cover_control")
            if "current_position" in attributes:
                capabilities.append("position_control")
        
        elif domain == "lock":
            capabilities.append("lock_control")
            if "code_format" in attributes:
                capabilities.append("keypad")
        
        elif domain == "fan":
            capabilities.append("fan_control")
            if "speed" in attributes or "percentage" in attributes:
                capabilities.append("speed_control")
            if "oscillate" in attributes:
                capabilities.append("oscillation")
        
        return capabilities

    def _extract_features(self, domain: str, attributes: dict[str, Any]) -> dict[str, Any]:
        """Extract features from entity attributes"""
        features = {}
        
        # Common features
        if "battery" in attributes or "battery_level" in attributes:
            features["battery"] = True
        
        # Domain-specific features
        if domain == "light":
            if "brightness" in attributes:
                features["brightness"] = True
            if "rgb_color" in attributes:
                features["rgb_color"] = True
            if "color_temp" in attributes:
                features["color_temperature"] = True
        
        elif domain == "climate":
            if "temperature" in attributes:
                features["temperature"] = True
            if "humidity" in attributes:
                features["humidity"] = True
        
        return features

    async def _get_entity_state(self, session: aiohttp.ClientSession, entity_id: str) -> dict[str, Any] | None:
        """Get entity state"""
        try:
            state_url = f"{self.ha_url}/api/states/{entity_id}"
            async with session.get(state_url) as response:
                if response.status == 200:
                    return await response.json()
        except Exception:
            pass
        return None

    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()

