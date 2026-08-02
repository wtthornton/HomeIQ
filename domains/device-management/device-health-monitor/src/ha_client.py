"""
Home Assistant API Client for Device Health Monitor
Phase 1.2: Query HA API for device states and history

Two transports, deliberately. States and history are genuine REST endpoints and
keep their aiohttp session. The entity registry is a WebSocket-only command —
`GET /api/config/entity_registry/list` has never existed — so it goes through the
shared HAWebSocketClient (TAP-5424).
"""

import logging
from datetime import UTC, datetime
from typing import Any

import aiohttp
from homeiq_ha.client import HAClient as SharedHAClient
from homeiq_ha.client import HAWebSocketClient

logger = logging.getLogger("device-health-monitor")


class HAClient:
    """Client for the Home Assistant states/history REST API and the WebSocket registry"""

    def __init__(self, ha_url: str, access_token: str, timeout: int = 10):
        """
        Initialize HA client.

        Args:
            ha_url: Home Assistant URL (e.g., "http://homeassistant:8123")
            access_token: Long-lived access token
            timeout: Request timeout in seconds
        """
        self.ha_url = ha_url.rstrip('/')
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        self.timeout = timeout
        self._session: aiohttp.ClientSession | None = None
        self._ws: HAWebSocketClient | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create client session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout,
                raise_for_status=False
            )
        return self._session

    async def get_state(self, entity_id: str) -> dict[str, Any] | None:
        """
        Get current state of an entity.

        Args:
            entity_id: Entity ID (e.g., "sensor.temperature")

        Returns:
            State dictionary or None if not found
        """
        try:
            session = await self._get_session()
            url = f"{self.ha_url}/api/states/{entity_id}"

            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    logger.debug(f"Entity {entity_id} not found")
                    return None
                else:
                    logger.warning(f"Failed to get state for {entity_id}: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting state for {entity_id}: {e}")
            return None

    async def get_history(
        self,
        entity_id: str,
        start_time: datetime,
        end_time: datetime | None = None
    ) -> list[dict[str, Any]]:
        """
        Get history for an entity.

        Args:
            entity_id: Entity ID
            start_time: Start time for history query
            end_time: End time (defaults to now)

        Returns:
            List of state changes
        """
        try:
            session = await self._get_session()

            if end_time is None:
                end_time = datetime.now(UTC)

            # Format times for HA API
            start_str = start_time.isoformat()
            end_str = end_time.isoformat()

            url = f"{self.ha_url}/api/history/period/{start_str}"
            params = {"filter_entity_id": entity_id, "end_time": end_str}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    # HA returns list of lists, flatten if needed
                    if data and isinstance(data[0], list):
                        return data[0] if data else []
                    return data
                else:
                    logger.warning(f"Failed to get history for {entity_id}: HTTP {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting history for {entity_id}: {e}")
            return []

    async def get_entity_registry(self) -> dict[str, dict[str, Any]]:
        """
        Get entity registry from HA.

        Returns:
            Dictionary mapping entity_id to entity data
        """
        try:
            if self._ws is None:
                # The facade derives the ws:// URL from the HTTP base URL.
                self._ws = SharedHAClient(self.ha_url, self.access_token).ws
                await self._ws.connect()
            entities = await self._ws.list_entities()
            return {e["entity_id"]: e for e in entities if e.get("entity_id")}
        except Exception as e:
            logger.error(f"Error getting entity registry: {e}")
            await self._close_ws()
            return {}

    async def _close_ws(self):
        """Close and forget the WebSocket connection"""
        if self._ws is not None:
            try:
                await self._ws.close()
            finally:
                self._ws = None

    async def close(self):
        """Close both transports"""
        await self._close_ws()
        if self._session and not self._session.closed:
            await self._session.close()

