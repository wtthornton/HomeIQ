"""
Data API Client for AI Automation Service (2025 Patterns)

Epic 39, Story 39.10: Automation Service Foundation
Provides async access to historical Home Assistant data via Data API service.

Architecture Notes (Epic 31):
- Events are queried via data-api, which reads from InfluxDB
- Devices/Entities are queried via data-api, which reads from SQLite
- This client follows the Epic 31 pattern: Query via data-api, NOT direct writes
- See .cursor/rules/epic-31-architecture.mdc for architecture details

API Endpoint Paths:
- Events: /api/v1/events (with v1 prefix)
- Devices: /api/devices (no v1 prefix)  
- Entities: /api/entities (no v1 prefix)
"""

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import settings

logger = logging.getLogger(__name__)


class DataAPIClient:
    """
    Async client for fetching data from Data API service.
    
    Features:
    - Async HTTP requests with httpx
    - Automatic retry logic
    - Proper error handling
    - Type hints throughout
    """

    def __init__(self, base_url: str | None = None):
        """
        Initialize Data API client.
        
        Args:
            base_url: Base URL for Data API (defaults to settings.data_api_url)
        """
        self.base_url = (base_url or settings.data_api_url).rstrip('/')
        
        # Create async HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10
            ),
        )
        
        logger.info(f"Data API client initialized with base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def fetch_events(
        self,
        entity_id: str | None = None,
        device_id: str | None = None,
        event_type: str | None = None,
        limit: int = 10000,
        **kwargs: Any  # Accept but ignore unused params for backward compatibility
    ) -> list[dict[str, Any]]:
        """
        Fetch historical events from Data API.
        
        Note: Data-api returns events from its default time window (typically 24h).
        Time filtering parameters are not currently supported due to a bug in the
        data-api InfluxDB query builder. The default window is sufficient for
        pattern detection and suggestion generation.
        
        Args:
            entity_id: Optional filter for specific entity
            device_id: Optional filter for specific device  
            event_type: Optional filter for event type (e.g., 'state_changed')
            limit: Maximum number of events to return (default: 10000)
            **kwargs: Ignored parameters for backward compatibility (start_time, end_time, days)
        
        Returns:
            List of event dictionaries
        
        Raises:
            httpx.HTTPError: If API request fails after retries
        """
        # Build query parameters
        params: dict[str, Any] = {"limit": limit}
        
        if entity_id:
            params["entity_id"] = entity_id
        if device_id:
            params["device_id"] = device_id
        if event_type:
            params["event_type"] = event_type
        
        # Events endpoint uses /api/v1/events (with v1 prefix)
        url = f"{self.base_url}/api/v1/events"
        headers = {"X-Internal-Service": "true"}
        
        try:
            logger.debug(f"Fetching events from {url} with params: {params}")
            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Handle both list response (direct) and dict response (wrapped)
            if isinstance(data, list):
                logger.info(f"Fetched {len(data)} events from Data API")
                return data
            
            events = data.get("events", []) if isinstance(data, dict) else []
            logger.info(f"Fetched {len(events)} events from Data API")
            return events
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Data API returned {e.response.status_code}: {e.response.text[:200]}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch events from Data API: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def fetch_devices(self, limit: int = 1000) -> list[dict[str, Any]]:
        """
        Fetch devices from Data API (SQLite).
        
        Args:
            limit: Maximum number of devices to return (default: 1000)
        
        Returns:
            List of device dictionaries
        
        Raises:
            httpx.HTTPError: If API request fails after retries
        """
        # Devices endpoint uses /api/devices (no v1 prefix)
        url = f"{self.base_url}/api/devices"
        headers = {"X-Internal-Service": "true"}
        params = {"limit": limit}
        
        try:
            logger.debug(f"Fetching devices from {url}")
            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            devices = data.get("devices", [])
            logger.info(f"Fetched {len(devices)} devices from Data API")
            return devices
        except httpx.HTTPStatusError as e:
            logger.error(f"Data API returned {e.response.status_code}: {e.response.text[:200]}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch devices from Data API: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def fetch_entities(self, limit: int = 1000) -> list[dict[str, Any]]:
        """
        Fetch entities from Data API (SQLite).
        
        Args:
            limit: Maximum number of entities to return (default: 1000)
        
        Returns:
            List of entity dictionaries
        
        Raises:
            httpx.HTTPError: If API request fails after retries
        """
        # Entities endpoint uses /api/entities (no v1 prefix)
        url = f"{self.base_url}/api/entities"
        headers = {"X-Internal-Service": "true"}
        params = {"limit": limit}
        
        try:
            logger.debug(f"Fetching entities from {url}")
            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            entities = data.get("entities", [])
            logger.info(f"Fetched {len(entities)} entities from Data API")
            return entities
        except httpx.HTTPStatusError as e:
            logger.error(f"Data API returned {e.response.status_code}: {e.response.text[:200]}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch entities from Data API: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def get_entity_by_id(self, entity_id: str) -> dict[str, Any] | None:
        """
        Get specific entity by ID.
        
        Args:
            entity_id: Entity ID to fetch
        
        Returns:
            Entity dictionary or None if not found
        
        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/api/entities/{entity_id}"
        headers = {"X-Internal-Service": "true"}
        try:
            response = await self.client.get(url, headers=headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch entity {entity_id} from Data API: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if Data API service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            url = f"{self.base_url}/health"
            headers = {"X-Internal-Service": "true"}
            response = await self.client.get(url, headers=headers, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Data API health check failed: {e}")
            return False

    async def close(self):
        """Close HTTP client connection."""
        await self.client.aclose()
        logger.debug("Data API client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

