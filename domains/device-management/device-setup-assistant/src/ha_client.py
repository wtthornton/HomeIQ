"""
Home Assistant API Client for Setup Assistant
Phase 2.3: Query HA API for device and entity information

Two transports, deliberately. The device and entity registries are WebSocket-only
commands — `GET /api/config/{device,entity}_registry/list` has never existed, so
those reads go through the shared HAWebSocketClient (TAP-5424). The states API
(`/api/states/...`), which SetupIssueDetector uses, is a genuine REST endpoint and
keeps its aiohttp session.
"""

import logging
import os
from typing import Any

import aiohttp
from homeiq_ha.client import HAClient as SharedHAClient
from homeiq_ha.client import HAWebSocketClient

logger = logging.getLogger("device-setup-assistant")


class HAClient:
    """Client for the Home Assistant states REST API and the WebSocket registries"""

    def __init__(self):
        """Initialize HA client"""
        self.ha_url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
        if self.ha_url:
            self.ha_url = self.ha_url.rstrip("/")
        else:
            raise ValueError("HA_URL or HA_HTTP_URL environment variable must be set")
        self.ha_token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
        self.headers = (
            {"Authorization": f"Bearer {self.ha_token}", "Content-Type": "application/json"}
            if self.ha_token
            else {}
        )
        self._session: aiohttp.ClientSession | None = None
        self._ws: HAWebSocketClient | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create client session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(
                headers=self.headers, timeout=timeout, raise_for_status=False
            )
        return self._session

    async def _connection(self) -> HAWebSocketClient:
        """Return a live WebSocket connection, opening one on first use.

        Cached so repeated registry reads do not repeat the auth handshake, and
        dropped by the callers below on failure so the next call reconnects
        rather than reusing a socket the server has closed.
        """
        if self._ws is None:
            # The facade derives the ws:// URL from the HTTP base URL.
            self._ws = SharedHAClient(self.ha_url, self.ha_token).ws
            await self._ws.connect()
        return self._ws

    async def get_device_registry(self) -> dict[str, dict[str, Any]]:
        """Get device registry from HA, keyed by device id"""
        try:
            connection = await self._connection()
            devices = await connection.list_devices()
            return {d["id"]: d for d in devices if d.get("id")}
        except Exception as e:
            logger.error(f"Error getting device registry: {e}")
            await self._close_ws()
            return {}

    async def get_entity_registry(self) -> dict[str, dict[str, Any]]:
        """Get entity registry from HA, keyed by entity id"""
        try:
            connection = await self._connection()
            entities = await connection.list_entities()
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
