"""
Home Assistant API Client for Setup Assistant
Phase 2.3: Query HA API for device and entity information
"""

import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger("device-setup-assistant")


class HAClient:
    """Client for Home Assistant REST API"""

    def __init__(self):
        """Initialize HA client"""
        self.ha_url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
        if self.ha_url:
            self.ha_url = self.ha_url.rstrip("/")
        else:
            raise ValueError("HA_URL or HA_HTTP_URL environment variable must be set")
        self.ha_token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {self.ha_token}",
            "Content-Type": "application/json"
        } if self.ha_token else {}
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create client session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout,
                raise_for_status=False
            )
        return self._session

    async def get_device_registry(self) -> dict[str, dict[str, Any]]:
        """Get device registry from HA"""
        try:
            session = await self._get_session()
            url = f"{self.ha_url}/api/config/device_registry/list"

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    devices = data if isinstance(data, list) else data.get("devices", [])
                    registry_dict = {}
                    for device in devices:
                        device_id = device.get("id")
                        if device_id:
                            registry_dict[device_id] = device
                    return registry_dict
                elif response.status == 404:
                    logger.info("Device Registry API not available (404)")
                    return {}
                else:
                    logger.warning(f"Failed to get device registry: HTTP {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error getting device registry: {e}")
            return {}

    async def get_entity_registry(self) -> dict[str, dict[str, Any]]:
        """Get entity registry from HA"""
        try:
            session = await self._get_session()
            url = f"{self.ha_url}/api/config/entity_registry/list"

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    entities = data if isinstance(data, list) else data.get("entities", [])
                    registry_dict = {}
                    for entity in entities:
                        entity_id = entity.get("entity_id")
                        if entity_id:
                            registry_dict[entity_id] = entity
                    return registry_dict
                elif response.status == 404:
                    logger.info("Entity Registry API not available (404)")
                    return {}
                else:
                    logger.warning(f"Failed to get entity registry: HTTP {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error getting entity registry: {e}")
            return {}

    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()
