"""
Weather API Client for Proactive Agent Service

Fetches current weather and forecast data from weather-api service.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class WeatherAPIClient:
    """Client for fetching weather data from Weather API service"""

    def __init__(self, base_url: str = "http://weather-api:8009"):
        """
        Initialize Weather API client.

        Args:
            base_url: Base URL for Weather API (default: http://weather-api:8009)
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.info(f"Weather API client initialized with base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False  # Don't reraise - return None for graceful degradation
    )
    async def get_current_weather(self) -> dict[str, Any] | None:
        """
        Get current weather conditions.

        Returns:
            Dictionary with weather data (temperature, condition, etc.) or None if unavailable

        Note:
            Returns None on any error for graceful degradation.
            Errors are logged but not raised to allow service to continue.
        """
        try:
            logger.debug("Fetching current weather from Weather API")
            response = await self.client.get(f"{self.base_url}/current-weather")
            response.raise_for_status()
            data = response.json()
            logger.info("Fetched current weather from Weather API")
            return data
        except httpx.HTTPStatusError as e:
            error_msg = f"Weather API returned {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"HTTP error fetching weather: {error_msg}")
            return None  # Graceful degradation
        except httpx.ConnectError as e:
            error_msg = f"Could not connect to Weather API at {self.base_url}"
            logger.warning(f"Connection error: {error_msg}")
            return None  # Graceful degradation
        except httpx.TimeoutException as e:
            error_msg = "Weather API request timed out after 30 seconds"
            logger.warning(f"Timeout error: {error_msg}")
            return None  # Graceful degradation
        except Exception as e:
            logger.error(f"Unexpected error fetching weather: {str(e)}", exc_info=True)
            return None  # Graceful degradation

    async def close(self):
        """Close HTTP client connection pool"""
        await self.client.aclose()
        logger.debug("Weather API client closed")

