"""
Device Intelligence Service Client

Client for interacting with the Device Intelligence Service device mapping API (Epic AI-24).
Uses CrossGroupClient for circuit-breaker protection and automatic retries.
"""

import logging
from typing import Any

import httpx

from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

from ..config import Settings

logger = logging.getLogger(__name__)

_ml_engine_breaker = CircuitBreaker(name="ml-engine")


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
            self.api_key = settings.device_intelligence_api_key.get_secret_value() if settings.device_intelligence_api_key else None
        else:
            if base_url is None:
                raise ValueError("Either settings or base_url must be provided")
            self.base_url = base_url.rstrip("/")
            self.enabled = enabled
            self.api_key = None

        self.timeout = 10.0
        # X-API-Key header for device-intelligence-service auth (not Bearer)
        self._auth_headers: dict[str, str] = {"X-API-Key": self.api_key} if self.api_key else {}
        self._cross_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="ml-engine",
            timeout=self.timeout,
            max_retries=3,
            circuit_breaker=_ml_engine_breaker,
        )
        logger.debug(f"Device Intelligence Client initialized: {self.base_url} (enabled: {self.enabled}, auth={'yes' if self.api_key else 'no'})")

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
            response = await self._cross_client.call(
                "GET", "/api/devices", params=params, headers=self._auth_headers,
            )
            response.raise_for_status()

            data = response.json()
            if isinstance(data, dict) and "devices" in data:
                devices = data["devices"]
            elif isinstance(data, list):
                devices = data
            else:
                logger.warning(f"Unexpected devices response format: {type(data)}")
                devices = []

            return devices
        except CircuitOpenError:
            logger.warning("Device Intelligence circuit breaker open — returning empty")
            return []
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            error_text = getattr(e.response, 'text', str(e))[:200] if hasattr(e.response, 'text') else str(e)[:200]
            error_msg = f"Device Intelligence API returned {e.response.status_code}: {error_text}"
            logger.error(f"HTTP error fetching devices: {error_msg}")
            raise Exception(error_msg) from e
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as e:
            error_msg = f"Error fetching devices from Device Intelligence: {e}"
            logger.error(error_msg)
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
            response = await self._cross_client.call(
                "GET", f"/api/devices/{device_id}/capabilities", headers=self._auth_headers,
            )
            response.raise_for_status()

            data = response.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "capabilities" in data:
                return data["capabilities"]
            logger.warning(f"Unexpected capabilities response format: {type(data)}")
            return []
        except (CircuitOpenError, httpx.HTTPStatusError, httpx.RequestError, Exception) as e:
            logger.warning(f"Device Intelligence unavailable for capabilities: {e}")
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
            response = await self._cross_client.call(
                "POST", f"/api/device-mappings/{device_id}/type",
                json=device_data, headers=self._auth_headers,
            )
            response.raise_for_status()
            return response.json()
        except (CircuitOpenError, httpx.RequestError, httpx.HTTPStatusError, Exception) as e:
            logger.warning(f"Device Intelligence unavailable for device type: {e}")
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
            payload = device_data
            if all_devices:
                payload = {**device_data, "all_devices": all_devices}

            response = await self._cross_client.call(
                "POST", f"/api/device-mappings/{device_id}/relationships",
                json=payload, headers=self._auth_headers,
            )
            response.raise_for_status()
            return response.json()
        except (CircuitOpenError, httpx.RequestError, httpx.HTTPStatusError, Exception) as e:
            logger.warning(f"Device Intelligence unavailable for device relationships: {e}")
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
            payload = device_data
            if entities:
                payload = {**device_data, "entities": entities}

            response = await self._cross_client.call(
                "POST", f"/api/device-mappings/{device_id}/context",
                json=payload, headers=self._auth_headers,
            )
            response.raise_for_status()
            return response.json()
        except (CircuitOpenError, httpx.RequestError, httpx.HTTPStatusError, Exception) as e:
            logger.warning(f"Device Intelligence unavailable for device context: {e}")
            return None

    async def close(self):
        """No-op — CrossGroupClient uses per-request clients."""
        logger.debug("Device Intelligence client close called (no-op with CrossGroupClient)")
