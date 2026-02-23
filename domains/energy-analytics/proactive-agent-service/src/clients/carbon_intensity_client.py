"""
Carbon Intensity Client for Proactive Agent Service (cross-group: core-platform)

Fetches carbon intensity data via data-api (InfluxDB).
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


class CarbonIntensityClient:
    """Resilient client for fetching carbon intensity via Data API (core-platform group)."""

    def __init__(
        self,
        base_url: str = "http://carbon-intensity:8010",
        data_api_url: str = "http://data-api:8006",
    ):
        self.base_url = base_url.rstrip("/")
        self.data_api_url = data_api_url.rstrip("/")
        api_key = os.getenv("DATA_API_API_KEY") or os.getenv("API_KEY")
        # Carbon intensity data is fetched through data-api (core-platform)
        self._cross_client = CrossGroupClient(
            base_url=self.data_api_url,
            group_name="core-platform",
            timeout=30.0,
            max_retries=3,
            auth_token=api_key,
            circuit_breaker=core_platform_breaker,
        )
        logger.info("Carbon Intensity client initialized (data-api: %s)", self.data_api_url)

    async def get_current_intensity(self) -> dict[str, Any] | None:
        """Get current carbon intensity. Returns None on failure."""
        try:
            logger.debug("Fetching current carbon intensity from data-api")
            response = await self._cross_client.call(
                "GET", "/api/v1/energy/carbon-intensity/current",
            )
            response.raise_for_status()
            data = response.json()
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
        except CircuitOpenError:
            logger.warning("Data API circuit open — carbon intensity unavailable")
            return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug("No carbon intensity data found in InfluxDB")
            else:
                logger.warning("HTTP error fetching carbon intensity: %s", e)
            return None
        except httpx.HTTPError as e:
            logger.warning("Connection error fetching carbon intensity: %s", e)
            return None
        except Exception:
            logger.warning("Error fetching carbon intensity", exc_info=True)
            return None

    async def get_trends(self) -> dict[str, Any] | None:
        """Get carbon intensity trends over the last 24 hours. Returns None on failure."""
        try:
            logger.debug("Fetching carbon intensity trends from data-api")
            response = await self._cross_client.call(
                "GET", "/api/v1/energy/carbon-intensity/trends",
            )
            response.raise_for_status()
            return response.json()
        except CircuitOpenError:
            logger.warning("Data API circuit open — carbon trends unavailable")
            return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug("No carbon intensity trends data found")
            else:
                logger.warning("HTTP error fetching carbon intensity trends: %s", e)
            return None
        except httpx.HTTPError as e:
            logger.warning("Connection error fetching carbon trends: %s", e)
            return None
        except Exception:
            logger.warning("Error fetching carbon intensity trends", exc_info=True)
            return None

    async def close(self):
        """No-op — CrossGroupClient uses per-request clients."""
        logger.debug("Carbon Intensity client close (no-op with CrossGroupClient)")
