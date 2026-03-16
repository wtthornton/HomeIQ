"""
Data API Client for HA AI Agent Service

Provides access to entities and devices via Data API service.
Uses CrossGroupClient for circuit-breaker protection and automatic retries.
"""

import logging
from typing import Any

import httpx
from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

logger = logging.getLogger(__name__)

# Shared circuit breaker for core-platform group — all DataAPIClient instances
# share the same breaker so a data-api outage is detected once, not per-client.
_core_platform_breaker = CircuitBreaker(name="core-platform")


class DataAPIClient:
    """Client for fetching entities and devices from Data API"""

    def __init__(self, base_url: str = "http://data-api:8006", api_key: str | None = None):
        """
        Initialize Data API client.

        Args:
            base_url: Base URL for Data API (default: http://data-api:8006)
            api_key: Optional API key for Bearer auth
        """
        self.base_url = base_url.rstrip('/')
        self._cross_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="core-platform",
            timeout=30.0,
            max_retries=3,
            auth_token=api_key,
            circuit_breaker=_core_platform_breaker,
        )
        logger.info(f"Data API client initialized with base_url={self.base_url}, auth={'yes' if api_key else 'no'}")

    async def fetch_entities(
        self,
        device_id: str | None = None,
        domain: str | None = None,
        platform: str | None = None,
        area_id: str | None = None,
        limit: int = 10000
    ) -> list[dict[str, Any]]:
        """
        Fetch entities from Data API.

        Args:
            device_id: Optional filter by device ID
            domain: Optional filter by domain (light, sensor, switch, etc)
            platform: Optional filter by integration platform
            area_id: Optional filter by area/room
            limit: Maximum number of entities to return

        Returns:
            List of entity dictionaries with keys: entity_id, device_id, domain, platform, area_id, etc.

        Raises:
            Exception: If API request fails or circuit breaker is open
        """
        try:
            params: dict[str, Any] = {"limit": limit}

            if device_id:
                params["device_id"] = device_id
            if domain:
                params["domain"] = domain
            if platform:
                params["platform"] = platform
            if area_id:
                params["area_id"] = area_id

            logger.debug(f"Fetching entities from Data API: {params}")

            response = await self._cross_client.call("GET", "/api/entities", params=params)
            response.raise_for_status()

            data = response.json()

            # Handle response format
            if isinstance(data, dict) and "entities" in data:
                entities = data["entities"]
            elif isinstance(data, list):
                entities = data
            else:
                logger.warning(f"Unexpected entities response format: {type(data)}")
                entities = []

            logger.info(f"Fetched {len(entities)} entities from Data API")
            return entities

        except CircuitOpenError as e:
            error_msg = f"Data API circuit breaker open: {e}"
            logger.error(f"Circuit open: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.HTTPStatusError as e:
            error_msg = f"Data API returned {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"HTTP error fetching entities from Data API: {error_msg}")
            raise Exception(error_msg) from e
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as e:
            error_msg = f"Error fetching entities from Data API: {e}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    async def get_devices(
        self,
        limit: int = 1000,
        area_id: str | None = None,
        manufacturer: str | None = None,
        model: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch devices from Data API (local/cached).

        Args:
            limit: Maximum number of devices to return
            area_id: Optional filter by area/room
            manufacturer: Optional filter by manufacturer
            model: Optional filter by model

        Returns:
            List of device dictionaries with keys: device_id, name, manufacturer, model, area_id, etc.

        Raises:
            Exception: If API request fails
        """
        try:
            params: dict[str, Any] = {"limit": limit}

            if area_id:
                params["area_id"] = area_id
            if manufacturer:
                params["manufacturer"] = manufacturer
            if model:
                params["model"] = model

            logger.debug(f"Fetching devices from Data API: {params}")

            response = await self._cross_client.call("GET", "/api/devices", params=params)
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

            logger.info(f"Fetched {len(devices)} devices from Data API")
            return devices

        except CircuitOpenError as e:
            error_msg = f"Data API circuit breaker open: {e}"
            logger.error(f"Circuit open: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.HTTPStatusError as e:
            error_msg = f"Data API returned {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"HTTP error fetching devices from Data API: {error_msg}")
            raise Exception(error_msg) from e
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as e:
            error_msg = f"Error fetching devices from Data API: {e}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    async def fetch_device(self, device_id: str) -> dict[str, Any]:
        """
        Fetch a single device by ID from Data API.

        Args:
            device_id: Device ID to fetch

        Returns:
            Device dictionary with keys: device_id, name, manufacturer, model, area_id, etc.

        Raises:
            Exception: If API request fails
        """
        try:
            logger.debug(f"Fetching device {device_id} from Data API")

            response = await self._cross_client.call("GET", f"/api/devices/{device_id}")
            response.raise_for_status()

            device = response.json()

            logger.info(f"Fetched device {device_id} from Data API")
            return device

        except CircuitOpenError as e:
            error_msg = f"Data API circuit breaker open: {e}"
            logger.error(f"Circuit open: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                error_msg = f"Device {device_id} not found in Data API"
                logger.warning(error_msg)
                raise ValueError(error_msg) from e
            error_msg = f"Data API returned {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"HTTP error fetching device from Data API: {error_msg}")
            raise Exception(error_msg) from e
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as e:
            error_msg = f"Error fetching device from Data API: {e}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    async def get_areas(self) -> list[dict[str, Any]]:
        """
        Fetch areas from Data API /api/areas endpoint (Story 62.1/62.5).

        Returns a list of area dicts with keys: area_id, display_name, entity_count, domains.
        Falls back to extracting areas from devices if the endpoint is unavailable.
        """
        try:
            response = await self._cross_client.call("GET", "/api/areas")
            response.raise_for_status()
            data = response.json()
            areas = data.get("areas", []) if isinstance(data, dict) else data
            logger.info("Fetched %d areas from Data API /api/areas", len(areas))
            return areas
        except Exception as e:
            logger.warning("Failed to fetch /api/areas, falling back to device scan: %s", e)
            # Fallback: extract from devices (pre-62.1 behavior)
            try:
                devices = await self.get_devices(limit=1000)
                area_map: dict[str, str] = {}
                for device in devices:
                    area_id = device.get("area_id")
                    if area_id and area_id not in area_map:
                        area_map[area_id] = area_id.replace("_", " ").title()
                return [
                    {"area_id": aid, "display_name": name, "entity_count": 0, "domains": []}
                    for aid, name in sorted(area_map.items())
                ]
            except Exception as fallback_err:
                logger.error("Area fallback also failed: %s", fallback_err)
                raise Exception(f"Error fetching areas: {e}") from e

    async def close(self):
        """No-op — CrossGroupClient uses per-request clients."""
        logger.debug("Data API client close called (no-op with CrossGroupClient)")

