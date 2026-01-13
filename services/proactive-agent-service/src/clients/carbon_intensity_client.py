"""
Carbon Intensity Client for Proactive Agent Service

Fetches carbon intensity data. Carbon intensity data is stored in InfluxDB
and accessed via data-api service or directly from carbon-intensity service.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class CarbonIntensityClient:
    """Client for fetching carbon intensity data from data-api (InfluxDB)"""

    def __init__(
        self,
        base_url: str = "http://carbon-intensity:8010",
        data_api_url: str = "http://data-api:8006",
    ):
        """
        Initialize Carbon Intensity client.

        Args:
            base_url: Base URL for Carbon Intensity service (default: http://carbon-intensity:8010)
            data_api_url: Base URL for Data API service (default: http://data-api:8006)
        """
        self.base_url = base_url.rstrip('/')
        self.data_api_url = data_api_url.rstrip('/')
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.info(f"Carbon Intensity client initialized (data-api: {self.data_api_url})")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False  # Don't reraise - return None for graceful degradation
    )
    async def get_current_intensity(self) -> dict[str, Any] | None:
        """
        Get current carbon intensity from data-api (InfluxDB).

        Returns:
            Dictionary with carbon intensity data or None if unavailable
        """
        try:
            logger.debug("Fetching current carbon intensity from data-api")
            response = await self.client.get(
                f"{self.data_api_url}/api/v1/energy/carbon-intensity/current"
            )
            response.raise_for_status()
            data = response.json()
            
            # Transform to expected format
            return {
                "intensity": data.get("intensity", 0),
                "renewable_percentage": data.get("renewable_percentage", 0),
                "fossil_percentage": data.get("fossil_percentage", 0),
                "forecast_1h": data.get("forecast_1h", 0),
                "forecast_24h": data.get("forecast_24h", 0),
                "timestamp": data.get("timestamp"),
                "region": data.get("region"),
                "grid_operator": data.get("grid_operator"),
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug("No carbon intensity data found in InfluxDB")
            else:
                error_msg = f"Data API returned {e.response.status_code}: {e.response.text[:200]}"
                logger.warning(f"HTTP error fetching carbon intensity: {error_msg}")
            return None  # Graceful degradation
        except httpx.ConnectError as e:
            error_msg = f"Could not connect to Data API at {self.data_api_url}"
            logger.warning(f"Connection error: {error_msg}")
            return None  # Graceful degradation
        except Exception as e:
            logger.warning(f"Error fetching carbon intensity: {str(e)}", exc_info=True)
            return None  # Graceful degradation

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False  # Don't reraise - return None for graceful degradation
    )
    async def get_trends(self) -> dict[str, Any] | None:
        """
        Get carbon intensity trends over the last 24 hours.

        Returns:
            Dictionary with trends data or None if unavailable
        """
        try:
            logger.debug("Fetching carbon intensity trends from data-api")
            response = await self.client.get(
                f"{self.data_api_url}/api/v1/energy/carbon-intensity/trends"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug("No carbon intensity trends data found")
            else:
                error_msg = f"Data API returned {e.response.status_code}: {e.response.text[:200]}"
                logger.warning(f"HTTP error fetching carbon intensity trends: {error_msg}")
            return None  # Graceful degradation
        except httpx.ConnectError as e:
            error_msg = f"Could not connect to Data API at {self.data_api_url}"
            logger.warning(f"Connection error: {error_msg}")
            return None  # Graceful degradation
        except Exception as e:
            logger.warning(f"Error fetching carbon intensity trends: {str(e)}", exc_info=True)
            return None  # Graceful degradation

    async def close(self):
        """Close HTTP client connection pool"""
        await self.client.aclose()
        logger.debug("Carbon Intensity client closed")

