"""
Data API Client for HA AI Agent Service

Provides access to entities and devices via Data API service.
"""

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class DataAPIClient:
    """Client for fetching entities and devices from Data API"""

    def __init__(self, base_url: str = "http://data-api:8006"):
        """
        Initialize Data API client.

        Args:
            base_url: Base URL for Data API (default: http://data-api:8006)
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.info(f"Data API client initialized with base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
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
            httpx.HTTPError: If API request fails
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

            response = await self.client.get(
                f"{self.base_url}/api/entities",
                params=params
            )
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

            logger.info(f"✅ Fetched {len(entities)} entities from Data API")
            return entities

        except httpx.HTTPStatusError as e:
            error_msg = f"Data API returned {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"❌ HTTP error fetching entities from Data API: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.ConnectError as e:
            error_msg = f"Could not connect to Data API at {self.base_url}. Is the service running?"
            logger.error(f"❌ Connection error: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.TimeoutException as e:
            error_msg = "Data API request timed out after 30 seconds"
            logger.error(f"❌ Timeout error: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.HTTPError as e:
            error_msg = f"HTTP error fetching entities: {str(e)}"
            logger.error(f"❌ {error_msg}")
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

            logger.info(f"✅ Fetched {len(devices)} devices from Data API")
            return devices

        except httpx.HTTPStatusError as e:
            error_msg = f"Data API returned {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"❌ HTTP error fetching devices from Data API: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.ConnectError as e:
            error_msg = f"Could not connect to Data API at {self.base_url}. Is the service running?"
            logger.error(f"❌ Connection error: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.TimeoutException as e:
            error_msg = "Data API request timed out after 30 seconds"
            logger.error(f"❌ Timeout error: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.HTTPError as e:
            error_msg = f"HTTP error fetching devices: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    async def get_areas(self) -> list[dict[str, Any]]:
        """
        Extract areas from devices and entities (local/cached).

        Returns:
            List of area dictionaries with keys: area_id, name

        Raises:
            Exception: If API request fails
        """
        try:
            # Fetch devices to extract unique areas
            devices = await self.get_devices(limit=1000)
            
            # Extract unique area_ids from devices
            area_map: dict[str, str] = {}
            for device in devices:
                area_id = device.get("area_id")
                if area_id and area_id not in area_map:
                    # Use area_id as name (can be improved with actual area names if available)
                    area_map[area_id] = area_id.replace("_", " ").title()
            
            # Also check entities for any additional areas
            entities = await self.fetch_entities(limit=1000)
            for entity in entities:
                area_id = entity.get("area_id")
                if area_id and area_id not in area_map:
                    area_map[area_id] = area_id.replace("_", " ").title()
            
            # Convert to list format
            areas = [
                {"area_id": area_id, "name": name}
                for area_id, name in sorted(area_map.items())
            ]
            
            logger.info(f"✅ Extracted {len(areas)} areas from Data API")
            return areas

        except Exception as e:
            error_msg = f"Error extracting areas: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    async def close(self):
        """Close HTTP client connection pool"""
        await self.client.aclose()
        logger.debug("Data API client closed")

