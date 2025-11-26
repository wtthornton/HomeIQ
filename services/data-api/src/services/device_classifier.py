"""
Device Classification Service
Phase 2.1: Classify devices based on entity patterns
"""

import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Import patterns from device-context-classifier
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '../../../device-context-classifier/src'))
    from patterns import get_device_category, match_device_pattern
except ImportError:
    # Fallback if classifier service not available
    logger.warning("Device context classifier patterns not available, using fallback")
    def match_device_pattern(entity_domains, entity_attributes):
        return None
    def get_device_category(device_type):
        return None


class DeviceClassifierService:
    """Service for classifying devices"""

    def __init__(self):
        """Initialize classifier service"""
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
            return {
                "device_id": device_id,
                "device_type": None,
                "device_category": None
            }

        try:
            session = await self._get_session()
            
            # Get entity domains and attributes
            entity_domains = []
            entity_attributes = {}
            
            for entity_id in entity_ids[:10]:  # Limit to avoid too many API calls
                # Extract domain
                if "." in entity_id:
                    domain = entity_id.split(".")[0]
                    entity_domains.append(domain)
                
                # Get state for attributes
                state_url = f"{self.ha_url}/api/states/{entity_id}"
                async with session.get(state_url) as response:
                    if response.status == 200:
                        state_data = await response.json()
                        attrs = state_data.get("attributes", {})
                        entity_attributes.update(attrs)
            
            # Match pattern
            device_type = match_device_pattern(entity_domains, entity_attributes)
            device_category = get_device_category(device_type)
            
            return {
                "device_id": device_id,
                "device_type": device_type,
                "device_category": device_category
            }
            
        except Exception as e:
            logger.error(f"Error classifying device {device_id}: {e}")
            return {
                "device_id": device_id,
                "device_type": None,
                "device_category": None
            }


# Singleton instance
_classifier_service: DeviceClassifierService | None = None


def get_classifier_service() -> DeviceClassifierService:
    """Get singleton classifier service instance"""
    global _classifier_service
    if _classifier_service is None:
        _classifier_service = DeviceClassifierService()
    return _classifier_service

