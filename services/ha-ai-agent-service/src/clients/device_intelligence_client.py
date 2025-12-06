"""
Device Intelligence Service Client

Client for interacting with the Device Intelligence Service device mapping API (Epic AI-24).
"""

import logging
from typing import Any

import httpx

from ..config import Settings

logger = logging.getLogger(__name__)


class DeviceIntelligenceClient:
    """
    Client for Device Intelligence Service device mapping API.
    
    Provides methods to query device types, relationships, and context
    from the device mapping library.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the client.
        
        Args:
            settings: Application settings
        """
        self.base_url = settings.device_intelligence_url.rstrip("/")
        self.enabled = settings.device_intelligence_enabled
        self.timeout = 10.0
        logger.debug(f"Device Intelligence Client initialized: {self.base_url} (enabled: {self.enabled})")
    
    async def get_device_type(
        self,
        device_id: str,
        device_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Get device type for a device.
        
        Args:
            device_id: Device ID
            device_data: Device data dictionary (manufacturer, model, etc.)
            
        Returns:
            Dictionary with device type information, or None if service unavailable
        """
        if not self.enabled:
            return None
        
        try:
            url = f"{self.base_url}/api/device-mappings/{device_id}/type"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=device_data)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.warning(f"⚠️ Device Intelligence Service unavailable for device type: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"⚠️ Device Intelligence Service error for device type: {e.response.status_code}")
            return None
        except Exception as e:
            logger.warning(f"⚠️ Error getting device type from Device Intelligence Service: {e}")
            return None
    
    async def get_device_relationships(
        self,
        device_id: str,
        device_data: dict[str, Any],
        all_devices: list[dict[str, Any]] | None = None
    ) -> dict[str, Any] | None:
        """
        Get device relationships for a device.
        
        Args:
            device_id: Device ID
            device_data: Device data dictionary
            all_devices: Optional list of all devices for relationship discovery
            
        Returns:
            Dictionary with device relationships, or None if service unavailable
        """
        if not self.enabled:
            return None
        
        try:
            url = f"{self.base_url}/api/device-mappings/{device_id}/relationships"
            payload = device_data
            if all_devices:
                # Note: The API endpoint accepts all_devices as a query parameter or in body
                # For now, we'll send it in the body if provided
                payload = {**device_data, "all_devices": all_devices}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.warning(f"⚠️ Device Intelligence Service unavailable for device relationships: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"⚠️ Device Intelligence Service error for device relationships: {e.response.status_code}")
            return None
        except Exception as e:
            logger.warning(f"⚠️ Error getting device relationships from Device Intelligence Service: {e}")
            return None
    
    async def get_device_context(
        self,
        device_id: str,
        device_data: dict[str, Any],
        entities: list[dict[str, Any]] | None = None
    ) -> dict[str, Any] | None:
        """
        Get enriched context for a device.
        
        Args:
            device_id: Device ID
            device_data: Device data dictionary
            entities: Optional list of entities associated with the device
            
        Returns:
            Dictionary with enriched device context, or None if service unavailable
        """
        if not self.enabled:
            return None
        
        try:
            url = f"{self.base_url}/api/device-mappings/{device_id}/context"
            payload = device_data
            if entities:
                payload = {**device_data, "entities": entities}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.warning(f"⚠️ Device Intelligence Service unavailable for device context: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"⚠️ Device Intelligence Service error for device context: {e.response.status_code}")
            return None
        except Exception as e:
            logger.warning(f"⚠️ Error getting device context from Device Intelligence Service: {e}")
            return None
