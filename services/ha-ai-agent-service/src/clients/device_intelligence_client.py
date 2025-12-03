"""
Device Intelligence Service Client

Provides access to device capabilities from device-intelligence-service.
"""

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class DeviceIntelligenceClient:
    """Client for fetching device capabilities from device-intelligence-service"""

    def __init__(self, base_url: str = "http://device-intelligence-service:8028"):
        """
        Initialize device intelligence client.

        Args:
            base_url: Base URL for device-intelligence-service (default: http://device-intelligence-service:8028)
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.info(f"Device Intelligence client initialized with base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def get_device_capabilities(self, device_id: str) -> list[dict[str, Any]]:
        """
        Get capabilities for a specific device.

        Args:
            device_id: Device identifier

        Returns:
            List of capability dictionaries

        Raises:
            Exception: If API request fails
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/devices/{device_id}/capabilities"
            )
            response.raise_for_status()
            data = response.json()
            logger.debug(f"✅ Fetched capabilities for device {device_id}")
            return data if isinstance(data, list) else []
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(f"Device {device_id} not found")
                return []
            error_msg = f"Device Intelligence API returned {e.response.status_code}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e
        except httpx.ConnectError as e:
            error_msg = f"Could not connect to Device Intelligence Service at {self.base_url}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e
        except httpx.TimeoutException as e:
            error_msg = "Device Intelligence API request timed out"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def get_devices(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get list of devices.

        Args:
            limit: Maximum number of devices to return

        Returns:
            List of device dictionaries

        Raises:
            Exception: If API request fails
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/devices",
                params={"limit": limit}
            )
            response.raise_for_status()
            data = response.json()
            # Handle different response formats
            if isinstance(data, dict) and "devices" in data:
                devices = data["devices"]
            elif isinstance(data, list):
                devices = data
            else:
                devices = []
            logger.debug(f"✅ Fetched {len(devices)} devices")
            return devices
        except httpx.HTTPError as e:
            error_msg = f"Failed to fetch devices: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    async def close(self):
        """Close HTTP client connection pool"""
        await self.client.aclose()
        logger.debug("Device Intelligence client closed")

