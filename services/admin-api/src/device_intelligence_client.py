"""
Device Intelligence Service Client for Admin API

This client allows the admin-api to query device data from the Device Intelligence Service
instead of querying InfluxDB directly.
"""

import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DeviceIntelligenceClient:
    """Client for interacting with Device Intelligence Service from admin-api."""
    
    def __init__(self, base_url: str = "http://device-intelligence-service:8019"):
        """Initialize the client with Device Intelligence Service URL."""
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"Device Intelligence Client initialized with URL: {base_url}")
    
    async def get_devices(
        self, 
        limit: int = 100, 
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        area_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get devices from Device Intelligence Service.
        
        Args:
            limit: Maximum number of devices to return
            manufacturer: Filter by manufacturer
            model: Filter by model
            area_id: Filter by area/room
            
        Returns:
            Dictionary with devices, count, and limit
        """
        try:
            params = {"limit": limit}
            if manufacturer:
                params["manufacturer"] = manufacturer
            if model:
                params["model"] = model
            if area_id:
                params["area_id"] = area_id
            
            response = await self.client.get(f"{self.base_url}/api/devices", params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Retrieved {data.get('count', 0)} devices from Device Intelligence Service")
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting devices: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error getting devices: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting devices: {e}")
            raise
    
    async def get_device_by_id(self, device_id: str) -> Dict[str, Any]:
        """
        Get a specific device by ID.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Device data dictionary
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/devices/{device_id}")
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Retrieved device {device_id} from Device Intelligence Service")
            return data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Device {device_id} not found in Device Intelligence Service")
                return None
            logger.error(f"HTTP error getting device {device_id}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error getting device {device_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting device {device_id}: {e}")
            raise
    
    async def get_device_stats(self) -> Dict[str, Any]:
        """
        Get device statistics from Device Intelligence Service.
        
        Returns:
            Device statistics dictionary
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/stats")
            response.raise_for_status()
            
            data = response.json()
            logger.debug("Retrieved device statistics from Device Intelligence Service")
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting device stats: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error getting device stats: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting device stats: {e}")
            raise
    
    async def get_device_capabilities(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Get device capabilities from Device Intelligence Service.
        
        Args:
            device_id: Device identifier
            
        Returns:
            List of device capabilities
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/devices/{device_id}/capabilities")
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Retrieved {len(data)} capabilities for device {device_id}")
            return data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Device {device_id} not found for capabilities")
                return []
            logger.error(f"HTTP error getting capabilities for device {device_id}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error getting capabilities for device {device_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting capabilities for device {device_id}: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        try:
            await self.client.aclose()
            logger.info("Device Intelligence Client closed")
        except Exception as e:
            logger.error(f"Error closing Device Intelligence Client: {e}")

# Global client instance
_device_intelligence_client = None

def get_device_intelligence_client() -> DeviceIntelligenceClient:
    """Get or create the global Device Intelligence Service client."""
    global _device_intelligence_client
    if _device_intelligence_client is None:
        _device_intelligence_client = DeviceIntelligenceClient()
    return _device_intelligence_client

async def close_device_intelligence_client():
    """Close the global Device Intelligence Service client."""
    global _device_intelligence_client
    if _device_intelligence_client:
        await _device_intelligence_client.close()
        _device_intelligence_client = None
