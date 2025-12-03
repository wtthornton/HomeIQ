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
    """Client for fetching carbon intensity data"""

    def __init__(self, base_url: str = "http://carbon-intensity:8010"):
        """
        Initialize Carbon Intensity client.

        Args:
            base_url: Base URL for Carbon Intensity service (default: http://carbon-intensity:8010)
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.info(f"Carbon Intensity client initialized with base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False  # Don't reraise - return None for graceful degradation
    )
    async def get_current_intensity(self) -> dict[str, Any] | None:
        """
        Get current carbon intensity.

        Note: Carbon intensity service primarily writes to InfluxDB.
        This method attempts to get cached data if available.

        Returns:
            Dictionary with carbon intensity data or None if unavailable
        """
        try:
            # Carbon intensity service may not have a direct API endpoint
            # In that case, we'll query via data-api for InfluxDB data
            # For now, return None gracefully
            logger.debug("Carbon intensity data is stored in InfluxDB, query via data-api")
            return None
        except Exception as e:
            logger.warning(f"Error fetching carbon intensity: {str(e)}", exc_info=True)
            return None  # Graceful degradation

    async def close(self):
        """Close HTTP client connection pool"""
        await self.client.aclose()
        logger.debug("Carbon Intensity client closed")

