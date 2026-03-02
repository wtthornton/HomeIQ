"""Standard Data API client for HomeIQ services.

Consolidates 7+ duplicate DataAPIClient implementations into a single
shared client with circuit breaker protection and Bearer auth.

Usage::

    from homeiq_data import StandardDataAPIClient

    client = StandardDataAPIClient(
        base_url="http://data-api:8006",
        api_key="my-secret-key",
    )

    entities = await client.fetch_entities(domain="light")
    devices = await client.fetch_devices()

    await client.close()
"""

from __future__ import annotations

import logging
from typing import Any

from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

logger = logging.getLogger(__name__)

# Shared circuit breaker for data-api — all client instances share the
# same breaker so an outage is detected once, not per-client.
_data_api_breaker = CircuitBreaker(name="data-api", failure_threshold=5, recovery_timeout=60.0)


class StandardDataAPIClient:
    """Unified client for the Data API service.

    Parameters
    ----------
    base_url:
        Data API base URL.
    api_key:
        Optional Bearer token for authentication.
    timeout:
        Request timeout in seconds.
    max_retries:
        Maximum retry attempts.
    circuit_breaker:
        Optional custom circuit breaker (defaults to shared instance).
    """

    def __init__(
        self,
        base_url: str = "http://data-api:8006",
        api_key: str | None = None,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._cross_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="core-platform",
            timeout=timeout,
            max_retries=max_retries,
            auth_token=api_key,
            circuit_breaker=circuit_breaker or _data_api_breaker,
        )
        logger.debug(
            "StandardDataAPIClient initialized: base_url=%s, auth=%s",
            self.base_url,
            "yes" if api_key else "no",
        )

    async def fetch_entities(
        self,
        *,
        device_id: str | None = None,
        domain: str | None = None,
        platform: str | None = None,
        area_id: str | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        """Fetch entities from Data API.

        Returns an empty list if the circuit breaker is open.
        """
        params: dict[str, Any] = {"limit": limit}
        if device_id:
            params["device_id"] = device_id
        if domain:
            params["domain"] = domain
        if platform:
            params["platform"] = platform
        if area_id:
            params["area_id"] = area_id

        try:
            data = await self._cross_client.get("/api/v1/entities", params=params)
            return data if isinstance(data, list) else data.get("entities", [])
        except CircuitOpenError:
            logger.warning("AI FALLBACK: data-api circuit open, returning empty entities")
            return []
        except Exception:
            logger.warning("Failed to fetch entities from data-api", exc_info=True)
            return []

    async def fetch_devices(self, *, limit: int = 1000) -> list[dict[str, Any]]:
        """Fetch devices from Data API."""
        try:
            data = await self._cross_client.get("/api/v1/devices", params={"limit": limit})
            return data if isinstance(data, list) else data.get("devices", [])
        except CircuitOpenError:
            logger.warning("AI FALLBACK: data-api circuit open, returning empty devices")
            return []
        except Exception:
            logger.warning("Failed to fetch devices from data-api", exc_info=True)
            return []

    async def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        """Generic GET request to Data API."""
        return await self._cross_client.get(path, params=params)

    async def post(self, path: str, *, json: dict[str, Any] | None = None) -> Any:
        """Generic POST request to Data API."""
        return await self._cross_client.post(path, json=json)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._cross_client.close()

    async def __aenter__(self) -> StandardDataAPIClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
