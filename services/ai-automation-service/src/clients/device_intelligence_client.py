"""
Device Intelligence Service Client

Client for communicating with the Device Intelligence Service API.
Used by ai-automation-service to replace its internal device discovery.
"""

import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class DeviceIntelligenceClient:
    """
    Client for Device Intelligence Service API.
    
    Provides methods to query device data, capabilities, and health metrics
    from the centralized Device Intelligence Service.
    """
    
    def __init__(self, base_url: str = "http://device-intelligence-service:8019"):
        """
        Initialize Device Intelligence Service client.
        
        Args:
            base_url: Base URL of the Device Intelligence Service
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={"Content-Type": "application/json"}
        )
        logger.info(f"🔌 Device Intelligence Client initialized: {self.base_url}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check Device Intelligence Service health.
        
        Returns:
            Health status dictionary
        """
        try:
            response = await self.client.get(f"{self.base_url}/health/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Device Intelligence Service health check failed: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def get_devices(
        self,
        limit: int = 100,
        area_id: Optional[str] = None,
        integration: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all devices from Device Intelligence Service.
        
        Args:
            limit: Maximum number of devices to return
            area_id: Filter by area ID
            integration: Filter by integration
            
        Returns:
            List of device dictionaries
        """
        try:
            params: Dict[str, Any] = {"limit": limit}
            
            if area_id:
                params["area_id"] = area_id
            if integration:
                params["integration"] = integration
            
            logger.info(f"📡 Fetching devices from Device Intelligence Service (limit={limit})")
            
            response = await self.client.get(
                f"{self.base_url}/api/devices",
                params=params
            )
            response.raise_for_status()
            
            devices = response.json()
            logger.info(f"✅ Fetched {len(devices)} devices from Device Intelligence Service")
            return devices
            
        except httpx.HTTPError as e:
            logger.error(f"❌ Failed to fetch devices from Device Intelligence Service: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching devices: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def get_device_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific device by ID.
        
        Args:
            device_id: Device ID to fetch
            
        Returns:
            Device dictionary or None if not found
        """
        try:
            logger.info(f"📡 Fetching device {device_id} from Device Intelligence Service")
            
            response = await self.client.get(f"{self.base_url}/api/devices/{device_id}")
            
            if response.status_code == 404:
                logger.debug(f"Device {device_id} not found in Device Intelligence Service")
                return None
            
            response.raise_for_status()
            device = response.json()
            logger.info(f"✅ Fetched device {device_id} from Device Intelligence Service")
            return device
            
        except httpx.HTTPError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"❌ Failed to fetch device {device_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching device {device_id}: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def get_device_capabilities(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Get device capabilities.
        
        Args:
            device_id: Device ID to get capabilities for
            
        Returns:
            List of capability dictionaries
        """
        try:
            logger.info(f"📡 Fetching capabilities for device {device_id}")
            
            response = await self.client.get(f"{self.base_url}/api/devices/{device_id}/capabilities")
            response.raise_for_status()
            
            capabilities = response.json()
            logger.info(f"✅ Fetched {len(capabilities)} capabilities for device {device_id}")
            return capabilities
            
        except httpx.HTTPError as e:
            logger.error(f"❌ Failed to fetch capabilities for device {device_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching capabilities for device {device_id}: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def get_device_health(self, device_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get device health metrics.
        
        Args:
            device_id: Device ID to get health metrics for
            limit: Maximum number of metrics to return
            
        Returns:
            List of health metric dictionaries
        """
        try:
            logger.info(f"📡 Fetching health metrics for device {device_id}")
            
            response = await self.client.get(
                f"{self.base_url}/api/devices/{device_id}/health",
                params={"limit": limit}
            )
            response.raise_for_status()
            
            metrics = response.json()
            logger.info(f"✅ Fetched {len(metrics)} health metrics for device {device_id}")
            return metrics
            
        except httpx.HTTPError as e:
            logger.error(f"❌ Failed to fetch health metrics for device {device_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching health metrics for device {device_id}: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def get_device_stats(self) -> Dict[str, Any]:
        """
        Get device statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            logger.info("📡 Fetching device statistics from Device Intelligence Service")
            
            response = await self.client.get(f"{self.base_url}/api/stats")
            response.raise_for_status()
            
            stats = response.json()
            logger.info("✅ Fetched device statistics from Device Intelligence Service")
            return stats
            
        except httpx.HTTPError as e:
            logger.error(f"❌ Failed to fetch device statistics: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching device statistics: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("🔌 Device Intelligence Client closed")
