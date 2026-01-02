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
    
    def __init__(self, settings: Settings | None = None, base_url: str | None = None, enabled: bool = True):
        """
        Initialize the client.
        
        Args:
            settings: Application settings (optional, if provided base_url and enabled are ignored)
            base_url: Base URL for Device Intelligence Service (optional, required if settings not provided)
            enabled: Whether the service is enabled (default: True, only used if settings not provided)
        """
        if settings:
            self.base_url = settings.device_intelligence_url.rstrip("/")
            self.enabled = settings.device_intelligence_enabled
        else:
            if base_url is None:
                raise ValueError("Either settings or base_url must be provided")
            self.base_url = base_url.rstrip("/")
            self.enabled = enabled
        
        self.timeout = 10.0
        # Create persistent HTTP client (like DataAPIClient pattern)
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.debug(f"Device Intelligence Client initialized: {self.base_url} (enabled: {self.enabled})")
    
    async def get_devices(self, limit: int = 1000) -> list[dict[str, Any]]:
        """
        Fetch devices from Device Intelligence Service.
        
        Args:
            limit: Maximum number of devices to return
            
        Returns:
            List of device dictionaries
            
        Raises:
            Exception: If API request fails
        """
        if not self.enabled:
            return []
        
        try:
            params = {"limit": limit}
            response = await self.client.get(
                f"{self.base_url}/api/devices",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            # Handle response format
            if isinstance(data, dict) and "devices" in data:
                devices = data["devices"]
            elif isinstance(data, list):
                devices = data
            else:
                logger.warning(f"Unexpected devices response format: {type(data)}")
                devices = []
            
            return devices
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Device not found - return empty list
                return []
            error_text = getattr(e.response, 'text', str(e))[:200] if hasattr(e.response, 'text') else str(e)[:200]
            error_msg = f"Device Intelligence API returned {e.response.status_code}: {error_text}"
            logger.error(f"❌ HTTP error fetching devices: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.ConnectError as e:
            error_msg = f"Could not connect to Device Intelligence Service at {self.base_url}"
            logger.error(f"❌ Connection error: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.TimeoutException as e:
            error_msg = f"Device Intelligence Service request timed out"
            logger.error(f"❌ Timeout error: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.HTTPError as e:
            error_msg = f"HTTP error fetching devices: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e
    
    async def get_device_capabilities(self, device_id: str) -> list[dict[str, Any]]:
        """
        Get device capabilities for a device.
        
        Args:
            device_id: Device ID
            
        Returns:
            List of capability dictionaries, or empty list if device not found or service unavailable
        """
        if not self.enabled:
            return []
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/devices/{device_id}/capabilities"
            )
            response.raise_for_status()
            
            data = response.json()
            # Handle response format
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "capabilities" in data:
                return data["capabilities"]
            else:
                logger.warning(f"Unexpected capabilities response format: {type(data)}")
                return []
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Device not found - return empty list
                return []
            logger.warning(f"⚠️ Device Intelligence Service error for capabilities: {e.response.status_code}")
            return []
        except httpx.RequestError as e:
            logger.warning(f"⚠️ Device Intelligence Service unavailable for capabilities: {e}")
            return []
        except Exception as e:
            logger.warning(f"⚠️ Error getting device capabilities: {e}")
            return []
    
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
            response = await self.client.post(url, json=device_data)
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
            
            response = await self.client.post(url, json=payload)
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
            
            response = await self.client.post(url, json=payload)
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
    
    async def close(self):
        """Close HTTP client connection pool"""
        await self.client.aclose()
        logger.debug("Device Intelligence client closed")
