"""HTTP client for Blueprint Index Service."""

import logging
from typing import Any, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class BlueprintClient:
    """Client for interacting with Blueprint Index Service."""
    
    def __init__(self, base_url: Optional[str] = None):
        """Initialize blueprint client."""
        self.base_url = (base_url or settings.blueprint_index_url).rstrip("/")
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
    
    async def get_all_blueprints(
        self,
        limit: int = 200,
        min_quality_score: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Get all blueprints from blueprint-index service.
        
        Args:
            limit: Maximum number of blueprints to return
            min_quality_score: Minimum quality score filter
            
        Returns:
            List of blueprint dictionaries
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/api/blueprints/search",
                params={
                    "limit": limit,
                    "min_quality_score": min_quality_score,
                    "sort_by": "quality_score",
                    "sort_order": "desc",
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("blueprints", [])
        except Exception as e:
            logger.error(f"Failed to fetch blueprints: {e}")
            return []
    
    async def get_blueprint(self, blueprint_id: str) -> Optional[dict[str, Any]]:
        """
        Get a specific blueprint by ID.
        
        Args:
            blueprint_id: Blueprint ID
            
        Returns:
            Blueprint dictionary or None if not found
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/api/blueprints/{blueprint_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to fetch blueprint {blueprint_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch blueprint {blueprint_id}: {e}")
            return None
