"""
Device Context Classifier
Phase 2.1: Core classification logic
"""

import logging
import os
from typing import Any

import aiohttp

from .patterns import get_device_category, match_device_pattern

logger = logging.getLogger(__name__)


class DeviceContextClassifier:
    """Classifies devices based on entity patterns"""

    def __init__(self):
        """Initialize classifier"""
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

    async def classify_device(
        self,
        device_id: str,
        entity_ids: list[str]
    ) -> dict[str, Any]:
        """
        Classify a device based on its entities.
        
        Args:
            device_id: Device identifier
            entity_ids: List of entity IDs for this device
            
        Returns:
            Classification result with device_type and device_category
        """
        if not self.ha_url or not self.ha_token:
            logger.warning("HA_URL or HA_TOKEN not configured")
            return {
                "device_id": device_id,
                "device_type": None,
                "device_category": None,
                "confidence": 0.0
            }

        try:
            session = await self._get_session()
            
            # Get entity registry
            registry_url = f"{self.ha_url}/api/config/entity_registry/list"
            async with session.get(registry_url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to get entity registry: HTTP {response.status}")
                    return {
                        "device_id": device_id,
                        "device_type": None,
                        "device_category": None,
                        "confidence": 0.0
                    }
                
                registry_data = await response.json()
                entities = registry_data.get("entities", [])
                
                # Build entity info
                entity_domains = []
                entity_attributes = {}
                
                for entity_id in entity_ids:
                    # Find entity in registry
                    entity_info = next(
                        (e for e in entities if e.get("entity_id") == entity_id),
                        None
                    )
                    if entity_info:
                        domain = entity_id.split(".")[0] if "." in entity_id else None
                        if domain:
                            entity_domains.append(domain)
                    
                    # Get state for attributes
                    state_url = f"{self.ha_url}/api/states/{entity_id}"
                    async with session.get(state_url) as state_response:
                        if state_response.status == 200:
                            state_data = await state_response.json()
                            attrs = state_data.get("attributes", {})
                            entity_attributes.update(attrs)
                
                # Match pattern
                device_type = match_device_pattern(entity_domains, entity_attributes)
                device_category = get_device_category(device_type)
                
                # Calculate confidence (simplified)
                confidence = 0.8 if device_type else 0.0
                
                return {
                    "device_id": device_id,
                    "device_type": device_type,
                    "device_category": device_category,
                    "confidence": confidence,
                    "matched_entities": len(entity_ids)
                }
                
        except Exception as e:
            logger.error(f"Error classifying device {device_id}: {e}")
            return {
                "device_id": device_id,
                "device_type": None,
                "device_category": None,
                "confidence": 0.0
            }

    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()

