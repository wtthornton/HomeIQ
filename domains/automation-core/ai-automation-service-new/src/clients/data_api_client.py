"""
Data API Client for AI Automation Service (cross-group: core-platform)

Epic 39, Story 39.10: Automation Service Foundation
Provides resilient async access to historical Home Assistant data via Data API service.

Architecture Notes (Epic 31):
- Events are queried via data-api, which reads from InfluxDB
- Devices/Entities are queried via data-api, which reads from PostgreSQL
- This client follows the Epic 31 pattern: Query via data-api, NOT direct writes

API Endpoint Paths:
- Events: /api/v1/events (with v1 prefix)
- Devices: /api/devices (no v1 prefix)
- Entities: /api/entities (no v1 prefix)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

from ..config import settings

logger = logging.getLogger(__name__)

# Module-level shared breaker — all DataAPIClient instances share one circuit.
_core_platform_breaker = CircuitBreaker(name="core-platform")


class DataAPIClient:
    """Resilient client for Data API service (core-platform group)."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or settings.data_api_url).rstrip("/")
        _key = api_key or settings.api_key
        self._cross_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="core-platform",
            timeout=30.0,
            max_retries=3,
            auth_token=_key,
            circuit_breaker=_core_platform_breaker,
        )
        logger.info("Data API client initialized with base_url=%s", self.base_url)

    async def fetch_events(
        self,
        entity_id: str | None = None,
        device_id: str | None = None,
        event_type: str | None = None,
        limit: int = 10000,
        **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Fetch historical events from Data API."""
        params: dict[str, Any] = {"limit": limit}
        if entity_id:
            params["entity_id"] = entity_id
        if device_id:
            params["device_id"] = device_id
        if event_type:
            params["event_type"] = event_type

        try:
            logger.debug("Fetching events from %s/api/v1/events with params: %s", self.base_url, params)
            response = await self._cross_client.call(
                "GET", "/api/v1/events", params=params,
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                logger.info("Fetched %d events from Data API", len(data))
                return data

            events = data.get("events", []) if isinstance(data, dict) else []
            logger.info("Fetched %d events from Data API", len(events))
            return events

        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty events")
            return []
        except httpx.HTTPStatusError as e:
            logger.error("Data API returned %d: %s", e.response.status_code, e.response.text[:200])
            raise
        except httpx.HTTPError as e:
            logger.error("Failed to fetch events from Data API: %s", e)
            raise

    async def fetch_devices(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Fetch devices from Data API."""
        try:
            logger.debug("Fetching devices from %s/api/devices", self.base_url)
            response = await self._cross_client.call(
                "GET", "/api/devices", params={"limit": limit},
            )
            response.raise_for_status()
            data = response.json()
            devices = data.get("devices", [])
            logger.info("Fetched %d devices from Data API", len(devices))
            return devices
        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty devices")
            return []
        except httpx.HTTPStatusError as e:
            logger.error("Data API returned %d: %s", e.response.status_code, e.response.text[:200])
            raise
        except httpx.HTTPError as e:
            logger.error("Failed to fetch devices from Data API: %s", e)
            raise

    async def fetch_entities(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Fetch entities from Data API."""
        try:
            logger.debug("Fetching entities from %s/api/entities", self.base_url)
            response = await self._cross_client.call(
                "GET", "/api/entities", params={"limit": limit},
            )
            response.raise_for_status()
            data = response.json()
            entities = data.get("entities", [])
            logger.info("Fetched %d entities from Data API", len(entities))
            return entities
        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty entities")
            return []
        except httpx.HTTPStatusError as e:
            logger.error("Data API returned %d: %s", e.response.status_code, e.response.text[:200])
            raise
        except httpx.HTTPError as e:
            logger.error("Failed to fetch entities from Data API: %s", e)
            raise

    async def get_entity_by_id(self, entity_id: str) -> dict[str, Any] | None:
        """Get specific entity by ID."""
        try:
            response = await self._cross_client.call(
                "GET", f"/api/entities/{entity_id}",
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except CircuitOpenError:
            logger.warning("Data API circuit open — returning None for entity %s", entity_id)
            return None
        except httpx.HTTPError as e:
            logger.error("Failed to fetch entity %s from Data API: %s", entity_id, e)
            raise

    async def fetch_areas(self) -> list[dict[str, Any]]:
        """Fetch distinct areas from Data API."""
        try:
            response = await self._cross_client.call("GET", "/api/areas")
            response.raise_for_status()
            data = response.json()
            return data.get("areas", [])
        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty areas")
            return []
        except Exception as e:
            logger.warning("Failed to fetch areas from Data API: %s", e)
            return []

    async def fetch_entities_in_area(self, area_id: str) -> list[dict[str, Any]]:
        """Fetch entities in a specific area from Data API."""
        try:
            response = await self._cross_client.call(
                "GET", f"/api/entities/by-area/{area_id}",
            )
            response.raise_for_status()
            data = response.json()
            return data.get("entities", [])
        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty entities for area %s", area_id)
            return []
        except Exception as e:
            logger.warning("Failed to fetch entities in area %s: %s", area_id, e)
            return []

    async def health_check(self) -> bool:
        """Check if Data API service is healthy."""
        try:
            response = await self._cross_client.call("GET", "/health")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """No-op — CrossGroupClient uses per-request clients."""
        logger.debug("Data API client close (no-op with CrossGroupClient)")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
