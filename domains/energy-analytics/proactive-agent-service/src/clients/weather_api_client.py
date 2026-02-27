"""
Weather API Client for Proactive Agent Service (cross-group: data-collectors)

Fetches current weather and forecast data from weather-api service.
Uses CrossGroupClient with shared circuit breaker for resilience.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from homeiq_resilience import CircuitOpenError, CrossGroupClient

from .breakers import data_collectors_breaker

logger = logging.getLogger(__name__)


class WeatherAPIClient:
    """Resilient client for fetching weather data (data-collectors group)."""

    def __init__(self, base_url: str = "http://weather-api:8009"):
        self.base_url = base_url.rstrip("/")
        api_key = os.getenv("DATA_COLLECTORS_API_KEY") or os.getenv("API_KEY")
        self._cross_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="data-collectors",
            timeout=30.0,
            max_retries=3,
            auth_token=api_key,
            circuit_breaker=data_collectors_breaker,
        )
        logger.info("Weather API client initialized with base_url=%s", self.base_url)

    async def get_current_weather(self) -> dict[str, Any] | None:
        """Get current weather. Returns None on failure."""
        try:
            logger.debug("Fetching current weather from Weather API")
            response = await self._cross_client.call(
                "GET", "/current-weather",
            )
            response.raise_for_status()
            data = response.json()
            logger.info("Fetched current weather from Weather API")
            return data
        except CircuitOpenError:
            logger.warning("Weather API circuit open — returning None")
            return None
        except httpx.HTTPError as e:
            logger.warning("HTTP error fetching weather: %s", e)
            return None
        except Exception as e:
            logger.warning("Unexpected error fetching weather: %s", e, exc_info=True)
            return None

    async def close(self):
        """No-op — CrossGroupClient uses per-request clients."""
        logger.debug("Weather API client close (no-op with CrossGroupClient)")
