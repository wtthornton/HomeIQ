"""
Data API Client for Device Intelligence Service

Simple client for querying entities from the data-api service.
"""

import logging
import os
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class DataAPIClient:
    """Simple client for fetching entities from Data API."""

    def __init__(self, base_url: str | None = None):
        """
        Initialize Data API client.
        
        Args:
            base_url: Base URL for Data API (default: from env or http://data-api:8006)
        """
        self.base_url = (base_url or os.getenv("DATA_API_URL") or "http://data-api:8006").rstrip('/')
        
        # Optional API key for authenticated Data API access
        api_key = os.getenv("DATA_API_API_KEY") or os.getenv("DATA_API_KEY") or os.getenv("API_KEY")
        default_headers = {}
        if api_key:
            default_headers["Authorization"] = f"Bearer {api_key}"
            default_headers["X-HomeIQ-API-Key"] = api_key

        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers=default_headers
        )

        logger.info(f"Data API client initialized with base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def fetch_entities(
        self,
        device_id: str | None = None,
        domain: str | None = None,
        platform: str | None = None,
        area_id: str | None = None,
        limit: int = 10000
    ) -> list[dict[str, Any]]:
        """
        Fetch entities from Data API.
        
        Args:
            device_id: Optional filter by device ID
            domain: Optional filter by domain (light, sensor, switch, etc)
            platform: Optional filter by integration platform
            area_id: Optional filter by area/room
            limit: Maximum number of entities to return
        
        Returns:
            List of entity dictionaries with keys: entity_id, device_id, domain, platform, area_id, etc.
        
        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            params: dict[str, Any] = {"limit": limit}

            if device_id:
                params["device_id"] = device_id
            if domain:
                params["domain"] = domain
            if platform:
                params["platform"] = platform
            if area_id:
                params["area_id"] = area_id

            logger.debug(f"Fetching entities from Data API: {params}")

            response = await self.client.get(
                f"{self.base_url}/api/entities",
                params=params
            )
            response.raise_for_status()

            data = response.json()

            # Handle response format
            if isinstance(data, dict) and "entities" in data:
                entities = data["entities"]
            elif isinstance(data, list):
                entities = data
            else:
                logger.warning(f"Unexpected entities response format: {type(data)}")
                entities = []

            logger.info(f"✅ Fetched {len(entities)} entities from Data API")
            return entities

        except httpx.HTTPStatusError as e:
            error_msg = f"Data API returned {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"❌ HTTP error fetching entities from Data API: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.ConnectError as e:
            error_msg = f"Could not connect to Data API at {self.base_url}. Is the service running?"
            logger.error(f"❌ Connection error: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.TimeoutException as e:
            error_msg = f"Data API request timed out after 30 seconds"
            logger.error(f"❌ Timeout error: {error_msg}")
            raise Exception(error_msg) from e
        except httpx.HTTPError as e:
            error_msg = f"HTTP error fetching entities from Data API: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error fetching entities: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

