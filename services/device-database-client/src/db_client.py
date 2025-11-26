"""
Device Database API Client
Phase 3.1: Client for querying external Device Database
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class DeviceDatabaseClient:
    """Client for Device Database API"""

    def __init__(self):
        """Initialize Device Database client"""
        self.api_url = os.getenv("DEVICE_DATABASE_API_URL")
        self.api_key = os.getenv("DEVICE_DATABASE_API_KEY")
        self.timeout = 10
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create client session"""
        if self._session is None or self._session.closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
                raise_for_status=False
            )
        return self._session

    def is_available(self) -> bool:
        """Check if Device Database API is available"""
        return self.api_url is not None

    async def get_device_info(
        self,
        manufacturer: str,
        model: str
    ) -> dict[str, Any] | None:
        """
        Get device information from Device Database.
        
        Args:
            manufacturer: Device manufacturer
            model: Device model
            
        Returns:
            Device information dictionary or None if not available
        """
        if not self.is_available():
            return None
        
        try:
            session = await self._get_session()
            
            # Query Device Database API
            # Note: Actual endpoint structure will depend on Device Database API design
            url = f"{self.api_url}/devices/search"
            params = {
                "manufacturer": manufacturer,
                "model": model
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                elif response.status == 404:
                    logger.debug(f"Device not found in Device Database: {manufacturer} {model}")
                    return None
                else:
                    logger.warning(f"Device Database API error: HTTP {response.status}")
                    return None
                    
        except aiohttp.ClientError as e:
            logger.warning(f"Device Database API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error querying Device Database: {e}")
            return None

    async def search_devices(
        self,
        device_type: str | None = None,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Search devices in Device Database.
        
        Args:
            device_type: Device type filter
            filters: Additional filters
            
        Returns:
            List of device information dictionaries
        """
        if not self.is_available():
            return []
        
        try:
            session = await self._get_session()
            
            url = f"{self.api_url}/devices"
            params = {}
            if device_type:
                params["device_type"] = device_type
            if filters:
                params.update(filters)
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    # Handle both list and dict with 'devices' key
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and "devices" in data:
                        return data["devices"]
                    return []
                else:
                    logger.warning(f"Device Database search failed: HTTP {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching Device Database: {e}")
            return []

    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()

