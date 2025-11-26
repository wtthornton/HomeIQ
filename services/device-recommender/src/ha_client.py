"""
Home Assistant API Client for Device Recommender
Phase 3.3: Query HA API for user's devices
"""

import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class HAClient:
    """Client for Home Assistant REST API"""

    def __init__(self):
        """Initialize HA client"""
        self.ha_url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
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

    async def get_user_devices(self) -> list[dict[str, Any]]:
        """Get user's devices from HA API"""
        try:
            session = await self._get_session()
            
            # Get device registry
            url = f"{self.ha_url}/api/config/device_registry/list"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("devices", [])
                elif response.status == 404:
                    # Fallback: get from entity registry
                    return await self._get_devices_from_entities(session)
                else:
                    logger.warning(f"Failed to get devices: HTTP {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting user devices: {e}")
            return []

    async def _get_devices_from_entities(self, session: aiohttp.ClientSession) -> list[dict[str, Any]]:
        """Get devices from entity registry as fallback"""
        try:
            url = f"{self.ha_url}/api/config/entity_registry/list"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    entities = data.get("entities", [])
                    
                    # Extract unique devices
                    devices = {}
                    for entity in entities:
                        device_id = entity.get("device_id")
                        if device_id and device_id not in devices:
                            devices[device_id] = {
                                "id": device_id,
                                "name": entity.get("name", "Unknown"),
                                "manufacturer": entity.get("manufacturer"),
                                "model": entity.get("model")
                            }
                    return list(devices.values())
        except Exception:
            pass
        return []

    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()

