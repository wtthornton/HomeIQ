"""Data API client for entity/area queries"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class DataAPIClient:
    """Client for Data API service."""

    def __init__(self, base_url: str = "http://data-api:8006", api_key: str | None = None):
        """
        Initialize Data API client.

        Args:
            base_url: Base URL for Data API service
            api_key: Optional Bearer token for data-api authentication
        """
        self.base_url = base_url.rstrip("/")
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.client = httpx.AsyncClient(timeout=10.0, headers=headers)
    
    async def fetch_entities(self) -> list[dict[str, Any]]:
        """
        Fetch all entities from Data API.
        
        Returns:
            List of entity dictionaries
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/entities")
            response.raise_for_status()
            data = response.json()
            return data.get("entities", [])
        except Exception as e:
            logger.error(f"Failed to fetch entities: {e}")
            return []
    
    async def fetch_areas(self) -> list[dict[str, Any]]:
        """
        Fetch all areas from Data API.
        
        Returns:
            List of area dictionaries
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/areas")
            response.raise_for_status()
            data = response.json()
            return data.get("areas", [])
        except Exception as e:
            logger.error(f"Failed to fetch areas: {e}")
            return []
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

