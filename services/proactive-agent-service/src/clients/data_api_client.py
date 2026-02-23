"""
Data API Client for Proactive Agent Service

Fetches historical patterns and event data from data-api service.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class DataAPIClient:
    """Client for fetching historical patterns and event data from Data API"""

    def __init__(self, base_url: str = "http://data-api:8006"):
        """
        Initialize Data API client.

        Args:
            base_url: Base URL for Data API (default: http://data-api:8006)
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.info(f"Data API client initialized with base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False  # Don't reraise - return empty list for graceful degradation
    )
    async def get_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get historical events.

        Args:
            entity_id: Optional filter by entity ID
            event_type: Optional filter by event type
            start_time: Optional start time (ISO format)
            end_time: Optional end time (ISO format)
            limit: Maximum number of events to return

        Returns:
            List of event dictionaries or empty list if unavailable
        """
        try:
            params: dict[str, Any] = {"limit": limit}
            if entity_id:
                params["entity_id"] = entity_id
            if event_type:
                params["event_type"] = event_type
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time

            logger.debug(f"Fetching events from Data API: {params}")
            response = await self.client.get(
                f"{self.base_url}/api/v1/events",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            events = data if isinstance(data, list) else data.get("events", [])
            logger.info(f"Fetched {len(events)} events from Data API")
            return events
        except httpx.HTTPStatusError as e:
            error_msg = f"Data API returned {e.response.status_code}: {e.response.text[:200]}"
            logger.warning(f"HTTP error fetching events: {error_msg}")
            return []  # Graceful degradation
        except httpx.ConnectError:
            error_msg = f"Could not connect to Data API at {self.base_url}"
            logger.warning(f"Connection error: {error_msg}")
            return []  # Graceful degradation
        except Exception:
            logger.warning("Error fetching events", exc_info=True)
            return []  # Graceful degradation

    async def get_activity(self) -> dict[str, Any] | None:
        """
        Get current activity from data-api (GET /api/v1/activity).
        Returns None on timeout, 404, 503, or error (graceful degradation).
        Timeout: 5s to avoid blocking scheduler.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/v1/activity")
                if response.status_code in (404, 503):
                    return None
                if response.status_code != 200:
                    return None
                return response.json()
        except Exception as e:
            logger.debug("Activity fetch failed: %s", e)
            return None

    async def get_activity_history(self, hours: int = 1) -> list[dict[str, Any]]:
        """
        Get activity history (GET /api/v1/activity/history?hours=N).
        Returns [] on failure (graceful degradation).
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/activity/history",
                    params={"hours": hours},
                )
                if response.status_code != 200:
                    return []
                data = response.json()
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.debug("Activity history fetch failed: %s", e)
            return []

    async def get_patterns(
        self,
        pattern_type: str | None = None,  # noqa: ARG002
        limit: int = 100,  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        """
        Get historical patterns (if available via data-api).

        Args:
            pattern_type: Optional filter by pattern type
            limit: Maximum number of patterns to return

        Returns:
            List of pattern dictionaries or empty list if unavailable
        """
        try:
            # Note: Patterns may be stored in ai-automation-service, not data-api
            # This is a placeholder for future integration
            logger.debug("Pattern data may be in ai-automation-service, not data-api")
            return []
        except Exception as e:
            logger.warning(f"Error fetching patterns: {str(e)}", exc_info=True)
            return []  # Graceful degradation

    async def close(self):
        """Close HTTP client connection pool"""
        await self.client.aclose()
        logger.debug("Data API client closed")

