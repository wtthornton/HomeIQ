"""
Data API Client for Proactive Agent Service (cross-group: core-platform)

Fetches historical patterns and event data from data-api service.
Uses CrossGroupClient with shared circuit breaker for resilience.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from homeiq_resilience import CircuitOpenError, CrossGroupClient

from .breakers import core_platform_breaker

logger = logging.getLogger(__name__)


class DataAPIClient:
    """Resilient client for fetching data from Data API (core-platform group)."""

    def __init__(self, base_url: str = "http://data-api:8006"):
        self.base_url = base_url.rstrip("/")
        api_key = os.getenv("DATA_API_API_KEY") or os.getenv("API_KEY")
        self._cross_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="core-platform",
            timeout=30.0,
            max_retries=3,
            auth_token=api_key,
            circuit_breaker=core_platform_breaker,
        )
        # Shorter-timeout client for activity endpoints
        self._activity_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="core-platform",
            timeout=5.0,
            max_retries=1,
            auth_token=api_key,
            circuit_breaker=core_platform_breaker,
        )
        logger.info("Data API client initialized with base_url=%s", self.base_url)

    async def get_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch historical events. Returns [] on failure."""
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

            logger.debug("Fetching events from Data API: %s", params)
            response = await self._cross_client.call(
                "GET", "/api/v1/events", params=params,
            )
            response.raise_for_status()
            data = response.json()
            events = data if isinstance(data, list) else data.get("events", [])
            logger.info("Fetched %d events from Data API", len(events))
            return events
        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty events")
            return []
        except httpx.HTTPError as e:
            logger.warning("HTTP error fetching events: %s", e)
            return []
        except Exception:
            logger.warning("Error fetching events", exc_info=True)
            return []

    async def get_activity(self) -> dict[str, Any] | None:
        """Get current activity. Returns None on failure (5s timeout)."""
        try:
            response = await self._activity_client.call(
                "GET", "/api/v1/activity",
            )
            if response.status_code in (404, 503):
                return None
            if response.status_code != 200:
                return None
            return response.json()
        except CircuitOpenError:
            logger.debug("Data API circuit open — activity unavailable")
            return None
        except Exception as e:
            logger.debug("Activity fetch failed: %s", e)
            return None

    async def get_activity_history(self, hours: int = 1) -> list[dict[str, Any]]:
        """Get activity history. Returns [] on failure (5s timeout)."""
        try:
            response = await self._activity_client.call(
                "GET", "/api/v1/activity/history", params={"hours": hours},
            )
            if response.status_code != 200:
                return []
            data = response.json()
            return data if isinstance(data, list) else []
        except CircuitOpenError:
            logger.debug("Data API circuit open — activity history unavailable")
            return []
        except Exception as e:
            logger.debug("Activity history fetch failed: %s", e)
            return []

    async def get_patterns(
        self,
        pattern_type: str | None = None,  # noqa: ARG002
        limit: int = 100,  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        """Get historical patterns (placeholder for future integration)."""
        logger.debug("Pattern data may be in ai-automation-service, not data-api")
        return []

    async def close(self):
        """No-op — CrossGroupClient uses per-request clients."""
        logger.debug("Data API client close (no-op with CrossGroupClient)")
