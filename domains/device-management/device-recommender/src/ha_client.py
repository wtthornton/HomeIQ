"""
Home Assistant registry access for Device Recommender
Phase 3.3: Query HA for the user's devices

Home Assistant exposes its device and entity registries as WebSocket commands
only — `GET /api/config/device_registry/list` has never existed. The previous
REST implementation therefore always received a 404 and fell through to an
entity-registry request that 404'd for the same reason, so this client reported
"no devices" rather than reporting a failure. It now reads the registry over the
shared WebSocket client (TAP-5424).
"""

import logging
import os
from typing import Any

from homeiq_ha.client import HAClient as SharedHAClient
from homeiq_ha.client import HAWebSocketClient

logger = logging.getLogger("device-recommender")


class HAClient:
    """Reads the Home Assistant device registry over WebSocket."""

    def __init__(self):
        """Initialize HA client"""
        self.ha_url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
        self.ha_token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
        self._ws: HAWebSocketClient | None = None

        if not self.ha_url:
            logger.warning("HA_URL / HA_HTTP_URL not set - Home Assistant integration disabled")

    async def _connection(self) -> HAWebSocketClient:
        """Return a live connection, opening one on first use.

        The connection is cached across calls so each request does not repeat
        the auth handshake. `get_user_devices` drops it on failure so the next
        call reconnects rather than reusing a socket the server has closed.
        """
        if self._ws is None:
            # The facade derives the ws:// URL from the HTTP base URL.
            self._ws = SharedHAClient(self.ha_url, self.ha_token).ws
            await self._ws.connect()
        return self._ws

    async def get_user_devices(self) -> list[dict[str, Any]]:
        """Get user's devices from the Home Assistant device registry"""
        if not self.ha_url or not self.ha_token:
            logger.warning("Home Assistant is not configured - returning no devices")
            return []

        try:
            connection = await self._connection()
            return await connection.list_devices()
        except Exception as e:
            logger.error(f"Error getting user devices: {e}")
            await self.close()
            return []

    async def close(self):
        """Close the connection"""
        if self._ws is not None:
            try:
                await self._ws.close()
            finally:
                self._ws = None
