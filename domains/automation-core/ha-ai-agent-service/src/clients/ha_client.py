"""
Home Assistant API Client for HA AI Agent Service

Simplified client for fetching areas, services, and config from Home Assistant.
Supports both REST API and WebSocket API (2025 best practice).
"""

import asyncio
import logging
import ssl
from typing import Any

import aiohttp
from homeiq_ha.client import HAWebSocketClient
from homeiq_ha.client import websocket_url as _websocket_url
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """
    Client for interacting with Home Assistant API.

    Supports both REST API and WebSocket API (2025 best practice).
    WebSocket API is preferred for area registry access.
    """

    def __init__(self, ha_url: str, access_token: str, timeout: int = 10, ssl_context: ssl.SSLContext | None = None):
        """
        Initialize HA client.

        Args:
            ha_url: Home Assistant URL (e.g., "http://homeassistant:8123")
            access_token: Long-lived access token from HA
            timeout: Request timeout in seconds
            ssl_context: Optional SSL context for TLS verification on WebSocket connections
        """
        self.ha_url = ha_url.rstrip("/")
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None
        self._ssl_context = ssl_context
        self._ws: HAWebSocketClient | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create a reusable client session"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, keepalive_timeout=30)
            self._session = aiohttp.ClientSession(connector=connector, headers=self.headers, timeout=self.timeout)
        return self._session

    async def _connection(self) -> HAWebSocketClient:
        """
        Return a live Home Assistant WebSocket connection, opening one on first use.

        This replaces a hand-rolled connect/auth/send/correlate loop that was this
        repo's second WebSocket implementation. The shared client owns the auth
        handshake, id correlation and read loop, and raises max_size so large
        registry listings are not truncated at the 1 MiB default (TAP-5424).

        The connection is cached, so a caller reading several registries pays one
        handshake instead of one per read as the old per-command connect did.
        """
        if self._ws is None:
            # The facade derives the ws:// URL from the HTTP base URL.
            self._ws = HAWebSocketClient(
                _websocket_url(self.ha_url),
                self.access_token,
                ssl_context=self._ssl_context,
            )
            await self._ws.connect()
        return self._ws

    async def _close_ws(self) -> None:
        """Close and forget the WebSocket connection"""
        if self._ws is not None:
            try:
                await self._ws.close()
            finally:
                self._ws = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def get_area_registry(self) -> list[dict[str, Any]]:
        """
        Get area registry from Home Assistant.

        Returns:
            List of area dictionaries with keys: area_id, name, aliases, etc.

        Raises:
            Exception: If the WebSocket command fails
        """
        try:
            connection = await self._connection()
            return await connection.list_areas()
        except Exception:
            await self._close_ws()
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True,
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
        reraise=True,
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
                "input_boolean",
                "input_number",
                "input_select",
                "input_text",
                "input_datetime",
                "input_button",
                "counter",
                "timer",
            }

            helpers = []
            for state in all_states:
                entity_id = state.get("entity_id", "")
                if entity_id:
                    domain = entity_id.split(".")[0]
                    if domain in helper_domains:
                        helpers.append(
                            {
                                "id": entity_id.split(".", 1)[1] if "." in entity_id else entity_id,
                                "type": domain,
                                "entity_id": entity_id,
                                "name": state.get("attributes", {}).get("friendly_name", entity_id),
                                "state": state.get("state"),
                            }
                        )

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
                    scenes.append(
                        {
                            "id": entity_id.split(".", 1)[1] if "." in entity_id else entity_id,
                            "entity_id": entity_id,
                            "name": state.get("attributes", {}).get("friendly_name", entity_id),
                            "state": state.get("state"),
                        }
                    )

            logger.info(f"✅ Found {len(scenes)} scenes from Home Assistant")
            return scenes
        except Exception as e:
            error_msg = f"Failed to fetch scenes: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def get_entity_registry(self) -> list[dict[str, Any]]:
        """
        Get entity registry from Home Assistant.

        Returns:
            List of entity registry dictionaries with keys: entity_id, aliases, category, disabled_by, etc.

        Raises:
            Exception: If the WebSocket command fails
        """
        try:
            connection = await self._connection()
            return await connection.list_entities()
        except Exception:
            await self._close_ws()
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def get_device_registry(self) -> list[dict[str, Any]]:
        """
        Get device registry from Home Assistant.

        Returns:
            List of device dictionaries with keys: id, name, area_id, manufacturer, model, etc.

        Raises:
            Exception: If the WebSocket command fails
        """
        try:
            connection = await self._connection()
            return await connection.list_devices()
        except Exception:
            await self._close_ws()
            raise

    async def close(self):
        """Close HTTP client connection pool"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("✅ Home Assistant client closed")
