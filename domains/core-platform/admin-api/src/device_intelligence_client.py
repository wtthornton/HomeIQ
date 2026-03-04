"""
Device Intelligence Service Client for Admin API

This client allows the admin-api to query device data from the Device Intelligence Service
(cross-group call: core-platform -> ml-engine).
Uses CrossGroupClient with circuit breaker for resilience.
"""

import logging
import os
from typing import Any

import httpx
from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

logger = logging.getLogger(__name__)

# Shared circuit breaker for ml-engine group calls
ml_engine_breaker = CircuitBreaker(name="ml-engine")


class DeviceIntelligenceClient:
    """Client for interacting with Device Intelligence Service from admin-api."""

    def __init__(self, base_url: str = "http://device-intelligence-service:8019"):
        """Initialize the client with Device Intelligence Service URL."""
        self.base_url = base_url.rstrip("/")
        api_key = os.getenv("DEVICE_INTELLIGENCE_API_KEY") or os.getenv("API_KEY")
        self._cross_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="ml-engine",
            timeout=30.0,
            max_retries=3,
            auth_token=api_key,
            circuit_breaker=ml_engine_breaker,
        )
        logger.info("Device Intelligence Client initialized with URL: %s", base_url)

    async def get_devices(
        self,
        limit: int = 100,
        manufacturer: str | None = None,
        model: str | None = None,
        area_id: str | None = None
    ) -> dict[str, Any]:
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
            params: dict[str, Any] = {"limit": limit}
            if manufacturer:
                params["manufacturer"] = manufacturer
            if model:
                params["model"] = model
            if area_id:
                params["area_id"] = area_id

            response = await self._cross_client.call(
                "GET", "/api/devices", params=params,
            )
            response.raise_for_status()

            data = response.json()
            logger.debug("Retrieved %s devices from Device Intelligence Service", data.get('count', 0))
            return data

        except CircuitOpenError:
            logger.warning("Device Intelligence circuit open")
            raise
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error getting devices: %s", e)
            raise
        except httpx.HTTPError as e:
            logger.error("Request error getting devices: %s", e)
            raise

    async def get_device_by_id(self, device_id: str) -> dict[str, Any] | None:
        """
        Get a specific device by ID.

        Args:
            device_id: Device identifier

        Returns:
            Device data dictionary
        """
        try:
            response = await self._cross_client.call(
                "GET", f"/api/devices/{device_id}",
            )
            response.raise_for_status()

            data = response.json()
            logger.debug("Retrieved device %s from Device Intelligence Service", device_id)
            return data

        except CircuitOpenError:
            logger.warning("Device Intelligence circuit open for device %s", device_id)
            return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("Device %s not found in Device Intelligence Service", device_id)
                return None
            logger.error("HTTP error getting device %s: %s", device_id, e)
            raise
        except httpx.HTTPError as e:
            logger.error("Request error getting device %s: %s", device_id, e)
            raise

    async def get_device_stats(self) -> dict[str, Any]:
        """
        Get device statistics from Device Intelligence Service.

        Returns:
            Device statistics dictionary
        """
        try:
            response = await self._cross_client.call("GET", "/api/stats")
            response.raise_for_status()

            data = response.json()
            logger.debug("Retrieved device statistics from Device Intelligence Service")
            return data

        except CircuitOpenError:
            logger.warning("Device Intelligence circuit open for stats")
            raise
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error getting device stats: %s", e)
            raise
        except httpx.HTTPError as e:
            logger.error("Request error getting device stats: %s", e)
            raise

    async def get_device_capabilities(self, device_id: str) -> list[dict[str, Any]]:
        """
        Get device capabilities from Device Intelligence Service.

        Args:
            device_id: Device identifier

        Returns:
            List of device capabilities
        """
        try:
            response = await self._cross_client.call(
                "GET", f"/api/devices/{device_id}/capabilities",
            )
            response.raise_for_status()

            data = response.json()
            logger.debug("Retrieved %d capabilities for device %s", len(data), device_id)
            return data

        except CircuitOpenError:
            logger.warning("Device Intelligence circuit open for capabilities %s", device_id)
            return []
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("Device %s not found for capabilities", device_id)
                return []
            logger.error("HTTP error getting capabilities for device %s: %s", device_id, e)
            raise
        except httpx.HTTPError as e:
            logger.error("Request error getting capabilities for device %s: %s", device_id, e)
            raise

    async def close(self):
        """No-op — CrossGroupClient uses per-request clients."""
        logger.debug("Device Intelligence Client close (no-op with CrossGroupClient)")


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
