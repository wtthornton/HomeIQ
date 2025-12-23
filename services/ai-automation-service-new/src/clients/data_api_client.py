"""
Data API Client for AI Automation Service (2025 Patterns)

Epic 39, Story 39.10: Automation Service Foundation
Provides async access to historical Home Assistant data via Data API service.
"""

import logging
from datetime import datetime, timedelta, timezone
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
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        entity_id: str | None = None,
        device_id: str | None = None,
        event_type: str | None = None,
        limit: int = 10000,
        days: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Fetch historical events from Data API.
        
        Args:
            start_time: Start datetime (default: 30 days ago or days parameter)
            end_time: End datetime (default: now)
            entity_id: Optional filter for specific entity
            device_id: Optional filter for specific device
            event_type: Optional filter for event type (e.g., 'state_changed')
            limit: Maximum number of events to return
            days: Number of days to look back (alternative to start_time)
        
        Returns:
            List of event dictionaries
        
        Raises:
            httpx.HTTPError: If API request fails
        """
        # Calculate time range
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        
        if start_time is None:
            if days:
                start_time = end_time - timedelta(days=days)
            else:
                start_time = end_time - timedelta(days=30)
        
        # Build query parameters
        params: dict[str, Any] = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "limit": limit
        }
        
        if entity_id:
            params["entity_id"] = entity_id
        if device_id:
            params["device_id"] = device_id
        if event_type:
            params["event_type"] = event_type
        
        # Make request
        url = f"{self.base_url}/api/events"
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("events", [])
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch events from Data API: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def fetch_devices(self) -> list[dict[str, Any]]:
        """
        Fetch all devices from Data API.
        
        Returns:
            List of device dictionaries
        
        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/api/devices"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("devices", [])
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch devices from Data API: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def fetch_entities(self) -> list[dict[str, Any]]:
        """
        Fetch all entities from Data API.
        
        Returns:
            List of entity dictionaries
        
        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/api/entities"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("entities", [])
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
        try:
            response = await self.client.get(url)
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
            response = await self.client.get(url, timeout=5.0)
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

