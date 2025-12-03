"""
Home Assistant API Client for HA AI Agent Service

Simplified client for fetching areas, services, and config from Home Assistant.
"""

import asyncio
import logging
from typing import Any

import aiohttp
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """Client for interacting with Home Assistant REST API"""

    def __init__(
        self,
        ha_url: str,
        access_token: str,
        timeout: int = 10
    ):
        """
        Initialize HA client.

        Args:
            ha_url: Home Assistant URL (e.g., "http://homeassistant:8123")
            access_token: Long-lived access token from HA
            timeout: Request timeout in seconds
        """
        self.ha_url = ha_url.rstrip('/')
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create a reusable client session"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                keepalive_timeout=30
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                headers=self.headers,
                timeout=self.timeout
            )
        return self._session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True
    )
    async def get_area_registry(self) -> list[dict[str, Any]]:
        """
        Get area registry from Home Assistant.

        Uses endpoint: GET /api/config/area_registry/list
        Note: This endpoint may not be in basic REST API docs but is used in HA codebase.
        Falls back gracefully if endpoint not available (404).

        Returns:
            List of area dictionaries with keys: area_id, name, aliases, etc.

        Raises:
            Exception: If API request fails (except 404 which returns empty list)
        """
        try:
            session = await self._get_session()
            url = f"{self.ha_url}/api/config/area_registry/list"

            async with session.get(url) as response:
                if response.status == 404:
                    # Some HA versions/configurations don't expose this endpoint
                    logger.info("ℹ️ Area Registry API not available (404) - returning empty list")
                    return []
                response.raise_for_status()
                data = await response.json()
                # Handle both list format and dict with 'areas' key
                if isinstance(data, dict) and "areas" in data:
                    areas = data["areas"]
                elif isinstance(data, list):
                    areas = data
                else:
                    areas = []
                logger.info(f"✅ Fetched {len(areas)} areas from Home Assistant")
                return areas
        except aiohttp.ClientError as e:
            error_msg = f"Failed to fetch area registry: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True
    )
    async def get_services(self) -> dict[str, Any]:
        """
        Get available services from Home Assistant.

        Returns:
            Dictionary of services grouped by domain

        Raises:
            Exception: If API request fails
        """
        try:
            session = await self._get_session()
            url = f"{self.ha_url}/api/services"

            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                logger.info("✅ Fetched services from Home Assistant")
                return data
        except aiohttp.ClientError as e:
            error_msg = f"Failed to fetch services: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True
    )
    async def get_states(self) -> list[dict[str, Any]]:
        """
        Get all entity states from Home Assistant.

        Uses REST API endpoint: GET /api/states
        Reference: https://developers.home-assistant.io/docs/api/rest/

        Returns:
            List of state dictionaries with entity_id, state, attributes, etc.

        Raises:
            Exception: If API request fails
        """
        try:
            session = await self._get_session()
            url = f"{self.ha_url}/api/states"

            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                logger.debug(f"✅ Fetched {len(data)} entity states from Home Assistant")
                return data
        except aiohttp.ClientError as e:
            error_msg = f"Failed to fetch states: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    async def get_helpers(self) -> list[dict[str, Any]]:
        """
        Get helpers (input_boolean, input_number, input_select, etc.) from Home Assistant.

        Filters states by helper domains. Helpers are entities with domains:
        - input_boolean
        - input_number
        - input_select
        - input_text
        - input_datetime
        - input_button
        - counter
        - timer

        Returns:
            List of helper state dictionaries with entity_id, state, attributes

        Raises:
            Exception: If API request fails
        """
        try:
            all_states = await self.get_states()
            helper_domains = {
                "input_boolean", "input_number", "input_select", "input_text",
                "input_datetime", "input_button", "counter", "timer"
            }

            helpers = []
            for state in all_states:
                entity_id = state.get("entity_id", "")
                if entity_id:
                    domain = entity_id.split(".")[0]
                    if domain in helper_domains:
                        helpers.append({
                            "id": entity_id.split(".", 1)[1] if "." in entity_id else entity_id,
                            "type": domain,
                            "entity_id": entity_id,
                            "name": state.get("attributes", {}).get("friendly_name", entity_id),
                            "state": state.get("state")
                        })

            logger.info(f"✅ Found {len(helpers)} helpers from Home Assistant")
            return helpers
        except Exception as e:
            error_msg = f"Failed to fetch helpers: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    async def get_scenes(self) -> list[dict[str, Any]]:
        """
        Get scenes from Home Assistant.

        Filters states by scene domain. Scenes are entities with domain "scene".

        Returns:
            List of scene state dictionaries with entity_id, state, attributes

        Raises:
            Exception: If API request fails
        """
        try:
            all_states = await self.get_states()

            scenes = []
            for state in all_states:
                entity_id = state.get("entity_id", "")
                if entity_id and entity_id.startswith("scene."):
                    scenes.append({
                        "id": entity_id.split(".", 1)[1] if "." in entity_id else entity_id,
                        "entity_id": entity_id,
                        "name": state.get("attributes", {}).get("friendly_name", entity_id),
                        "state": state.get("state")
                    })

            logger.info(f"✅ Found {len(scenes)} scenes from Home Assistant")
            return scenes
        except Exception as e:
            error_msg = f"Failed to fetch scenes: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    async def close(self):
        """Close HTTP client connection pool"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("✅ Home Assistant client closed")

