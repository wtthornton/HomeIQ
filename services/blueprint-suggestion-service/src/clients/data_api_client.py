"""HTTP client for Data API Service."""

import logging
from typing import Any, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class DataApiClient:
    """Client for interacting with Data API Service."""
    
    def __init__(self, base_url: Optional[str] = None):
        """Initialize data API client."""
        self.base_url = (base_url or settings.data_api_url).rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        timeout = httpx.Timeout(
            connect=settings.http_timeout_connect,
            read=settings.http_timeout_read,
            write=settings.http_timeout_write,
            pool=settings.http_timeout_pool,
        )
        self._client = httpx.AsyncClient(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get_all_entities(self, limit: int = 1000) -> list[dict[str, Any]]:
        """
        Get all entities from data-api service.
        
        Args:
            limit: Maximum number of entities to return
            
        Returns:
            List of entity dictionaries
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/api/entities",
                params={
                    "limit": limit,
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("entities", [])
        except Exception as e:
            logger.error(f"Failed to fetch entities: {e}")
            return []
    
    async def get_all_devices(self, limit: int = 500) -> list[dict[str, Any]]:
        """
        Get all devices from data-api service.
        
        Args:
            limit: Maximum number of devices to return
            
        Returns:
            List of device dictionaries
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/api/devices",
                params={
                    "limit": limit,
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("devices", [])
        except Exception as e:
            logger.error(f"Failed to fetch devices: {e}")
            return []
