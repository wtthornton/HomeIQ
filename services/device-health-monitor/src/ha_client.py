"""
Home Assistant API Client for Device Health Monitor
Phase 1.2: Query HA API for device states and history
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp

logger = logging.getLogger("device-health-monitor")


class HAClient:
    """Client for Home Assistant REST API"""

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
                end_time = datetime.now(timezone.utc)
            
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
            session = await self._get_session()
            url = f"{self.ha_url}/api/config/entity_registry/list"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # HA returns a flat list, not {"entities": [...]}
                    entities = data if isinstance(data, list) else data.get('entities', [])
                    registry_dict = {}
                    for entity in entities:
                        entity_id = entity.get('entity_id')
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

