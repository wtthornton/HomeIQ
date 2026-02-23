"""HTTP client for Data API Service (cross-group: core-platform)."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

try:
    _project_root = str(Path(__file__).resolve().parents[5])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass  # Docker: PYTHONPATH already includes /app

from shared.resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

from ..config import settings

logger = logging.getLogger(__name__)

# Module-level shared breaker — all DataApiClient instances share one circuit.
_core_platform_breaker = CircuitBreaker(name="core-platform")


class DataApiClient:
    """Resilient client for Data API Service (core-platform group)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        """Initialize data API client with CrossGroupClient."""
        _base = (base_url or settings.data_api_url).rstrip("/")
        _key = api_key or os.getenv("API_KEY")
        self._cross_client = CrossGroupClient(
            base_url=_base,
            group_name="core-platform",
            timeout=30.0,
            max_retries=3,
            auth_token=_key,
            circuit_breaker=_core_platform_breaker,
        )

    async def get_all_entities(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Get all entities from data-api service."""
        try:
            response = await self._cross_client.call(
                "GET", "/api/entities", params={"limit": limit}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("entities", [])
        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty entities")
            return []
        except Exception as e:
            logger.error("Failed to fetch entities: %s", e)
            return []

    async def get_all_devices(self, limit: int = 500) -> list[dict[str, Any]]:
        """Get all devices from data-api service."""
        try:
            response = await self._cross_client.call(
                "GET", "/api/devices", params={"limit": limit}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("devices", [])
        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty devices")
            return []
        except Exception as e:
            logger.error("Failed to fetch devices: %s", e)
            return []
