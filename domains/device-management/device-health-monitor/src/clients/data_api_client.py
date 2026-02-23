"""
Data API Client for Device Health Monitor (cross-group: core-platform)

Fetches entity metadata and device information from data-api.
Uses CrossGroupClient with shared circuit breaker for resilience.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

logger = logging.getLogger(__name__)

# Module-level shared breaker — all DataAPIClient instances share one circuit.
_core_platform_breaker = CircuitBreaker(name="core-platform")


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
            circuit_breaker=_core_platform_breaker,
        )
        logger.info("Data API client initialized with base_url=%s", self.base_url)

    async def fetch_entities(
        self,
        device_id: str | None = None,
        domain: str | None = None,
        area_id: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Fetch entities from Data API. Returns [] on failure."""
        try:
            params: dict[str, Any] = {"limit": limit}
            if device_id:
                params["device_id"] = device_id
            if domain:
                params["domain"] = domain
            if area_id:
                params["area_id"] = area_id

            response = await self._cross_client.call(
                "GET", "/api/entities", params=params,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and "entities" in data:
                return data["entities"]
            if isinstance(data, list):
                return data
            return []
        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty entities")
            return []
        except httpx.HTTPError as e:
            logger.warning("HTTP error fetching entities: %s", e)
            return []
        except Exception:
            logger.warning("Error fetching entities", exc_info=True)
            return []

    async def get_devices(
        self,
        manufacturer: str | None = None,
        area_id: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Fetch devices from Data API. Returns [] on failure."""
        try:
            params: dict[str, Any] = {"limit": limit}
            if manufacturer:
                params["manufacturer"] = manufacturer
            if area_id:
                params["area_id"] = area_id

            response = await self._cross_client.call(
                "GET", "/api/devices", params=params,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and "devices" in data:
                return data["devices"]
            if isinstance(data, list):
                return data
            return []
        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty devices")
            return []
        except httpx.HTTPError as e:
            logger.warning("HTTP error fetching devices: %s", e)
            return []
        except Exception:
            logger.warning("Error fetching devices", exc_info=True)
            return []

    async def close(self):
        """No-op — CrossGroupClient uses per-request clients."""
        logger.debug("Data API client close (no-op with CrossGroupClient)")
