"""
Device Intelligence Client for Device Health Monitor (cross-group: ml-engine)

Fetches device capabilities and type classifications from device-intelligence-service.
Uses CrossGroupClient with shared circuit breaker for resilience.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

logger = logging.getLogger(__name__)

# Module-level shared breaker for ml-engine group
_ml_engine_breaker = CircuitBreaker(name="ml-engine")


class DeviceIntelligenceClient:
    """Resilient client for device-intelligence-service (ml-engine group)."""

    def __init__(self, base_url: str = "http://device-intelligence-service:8019"):
        self.base_url = base_url.rstrip("/")
        api_key = os.getenv("DEVICE_INTELLIGENCE_API_KEY") or os.getenv("API_KEY")
        self._cross_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="ml-engine",
            timeout=30.0,
            max_retries=3,
            auth_token=api_key,
            circuit_breaker=_ml_engine_breaker,
        )
        logger.info(
            "Device Intelligence client initialized with base_url=%s", self.base_url,
        )

    async def get_device_capabilities(
        self, device_id: str,
    ) -> dict[str, Any] | None:
        """Get device capabilities. Returns None on failure."""
        try:
            response = await self._cross_client.call(
                "GET", f"/api/v1/devices/{device_id}/capabilities",
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except CircuitOpenError:
            logger.warning("Device Intelligence circuit open — capabilities unavailable")
            return None
        except httpx.HTTPError as e:
            logger.warning("HTTP error fetching capabilities for %s: %s", device_id, e)
            return None
        except Exception:
            logger.warning("Error fetching device capabilities", exc_info=True)
            return None

    async def get_device_type(self, device_id: str) -> str | None:
        """Get device type classification. Returns None on failure."""
        try:
            response = await self._cross_client.call(
                "GET", f"/api/v1/devices/{device_id}/type",
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            return data.get("type") if isinstance(data, dict) else None
        except CircuitOpenError:
            logger.warning("Device Intelligence circuit open — type unavailable")
            return None
        except httpx.HTTPError as e:
            logger.warning("HTTP error fetching device type for %s: %s", device_id, e)
            return None
        except Exception:
            logger.warning("Error fetching device type", exc_info=True)
            return None

    async def close(self):
        """No-op — CrossGroupClient uses per-request clients."""
        logger.debug("Device Intelligence client close (no-op with CrossGroupClient)")
