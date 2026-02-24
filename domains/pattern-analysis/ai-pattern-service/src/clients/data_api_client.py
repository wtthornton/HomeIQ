"""
Data API Client for Pattern Service (cross-group: core-platform)

Epic 39, Story 39.6: Daily Scheduler Migration
Resilient client for fetching events, devices, and entities from data-api.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pandas as pd

from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

logger = logging.getLogger(__name__)

# Module-level shared breaker — all DataAPIClient instances share one circuit.
_core_platform_breaker = CircuitBreaker(name="core-platform")


class DataAPIClient:
    """Resilient client for fetching historical data from Data API (core-platform group)."""

    def __init__(
        self,
        base_url: str = "http://data-api:8006",
        influxdb_url: str | None = None,
        influxdb_token: str | None = None,
        influxdb_org: str | None = None,
        influxdb_bucket: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        api_key = (
            os.getenv("DATA_API_API_KEY")
            or os.getenv("DATA_API_KEY")
            or os.getenv("API_KEY")
        )
        self._cross_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="core-platform",
            timeout=30.0,
            max_retries=3,
            auth_token=api_key,
            circuit_breaker=_core_platform_breaker,
        )

        # Store InfluxDB config for optional direct queries
        self.influxdb_url = influxdb_url
        self.influxdb_token = influxdb_token
        self.influxdb_org = influxdb_org
        self.influxdb_bucket = influxdb_bucket
        self.influxdb_client = None

        logger.info("Data API client initialized with base_url=%s", self.base_url)

    async def fetch_events(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        entity_id: str | None = None,
        device_id: str | None = None,
        event_type: str | None = None,
        limit: int = 10000,
    ) -> pd.DataFrame:
        """Fetch historical events from Data API."""
        try:
            if start_time is None:
                start_time = datetime.now(timezone.utc) - timedelta(days=7)
            if end_time is None:
                end_time = datetime.now(timezone.utc)

            params: dict[str, Any] = {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "limit": limit,
            }
            if entity_id:
                params["entity_id"] = entity_id
            if device_id:
                params["device_id"] = device_id
            if event_type:
                params["event_type"] = event_type

            logger.info(
                "Fetching events from Data API: start=%s, end=%s, limit=%s",
                start_time, end_time, limit,
            )

            response = await self._cross_client.call(
                "GET", "/api/v1/events", params=params,
            )
            response.raise_for_status()
            events_data = response.json()

            if isinstance(events_data, list):
                events = events_data
            elif isinstance(events_data, dict) and "events" in events_data:
                events = events_data["events"]
            else:
                events = []

            if not events:
                logger.warning(
                    "No events returned from Data API for period %s to %s",
                    start_time, end_time,
                )
                return pd.DataFrame()

            df_data = []
            for event in events:
                timestamp_str = event.get("timestamp", event.get("time_fired"))
                if isinstance(timestamp_str, str):
                    timestamp = pd.to_datetime(timestamp_str)
                else:
                    timestamp = pd.to_datetime(
                        event.get("_time", datetime.now(timezone.utc))
                    )

                entity_id_val = event.get("entity_id", "")
                new_state = event.get("new_state")
                if isinstance(new_state, dict):
                    state = new_state.get("state", "")
                else:
                    state = event.get("state", event.get("state_value", ""))

                df_data.append({
                    "timestamp": timestamp,
                    "_time": timestamp,
                    "last_changed": timestamp,
                    "entity_id": entity_id_val,
                    "device_id": event.get("device_id", entity_id_val),
                    "state": state,
                    "event_type": event.get("event_type", "state_changed"),
                    "domain": entity_id_val.split(".")[0] if "." in entity_id_val else "",
                    "friendly_name": event.get("friendly_name", entity_id_val),
                })

            df = pd.DataFrame(df_data)
            logger.info("Fetched %d events from Data API", len(df))
            return df

        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty DataFrame")
            return pd.DataFrame()
        except httpx.HTTPError as e:
            logger.error("Failed to fetch events from Data API: %s", e)
            raise
        except Exception as e:
            logger.error("Unexpected error fetching events: %s", e)
            raise

    async def fetch_devices(
        self,
        manufacturer: str | None = None,
        model: str | None = None,
        area_id: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Fetch all devices from Data API."""
        try:
            params: dict[str, Any] = {"limit": limit}
            if manufacturer:
                params["manufacturer"] = manufacturer
            if model:
                params["model"] = model
            if area_id:
                params["area_id"] = area_id

            logger.info("Fetching devices from Data API (limit=%d)", limit)
            response = await self._cross_client.call(
                "GET", "/api/devices", params=params,
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "devices" in data:
                devices = data["devices"]
            elif isinstance(data, list):
                devices = data
            else:
                logger.warning("Unexpected devices response format: %s", type(data))
                devices = []

            logger.info("Fetched %d devices from Data API", len(devices))
            return devices

        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty devices")
            return []
        except httpx.HTTPError as e:
            logger.error("Failed to fetch devices from Data API: %s", e)
            raise
        except Exception as e:
            logger.error("Unexpected error fetching devices: %s", e)
            raise

    async def fetch_entities(
        self,
        device_id: str | None = None,
        domain: str | None = None,
        platform: str | None = None,
        area_id: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Fetch all entities from Data API."""
        try:
            params: dict[str, Any] = {"limit": limit}
            if device_id:
                params["device_id"] = device_id
            if domain:
                params["domain"] = domain
            if platform:
                params["platform"] = platform
            if area_id:
                params["area_id"] = area_id

            logger.info("Fetching entities from Data API (limit=%d)", limit)
            response = await self._cross_client.call(
                "GET", "/api/entities", params=params,
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "entities" in data:
                entities = data["entities"]
            elif isinstance(data, list):
                entities = data
            else:
                logger.warning("Unexpected entities response format: %s", type(data))
                entities = []

            logger.info("Fetched %d entities from Data API", len(entities))
            return entities

        except CircuitOpenError:
            logger.warning("Data API circuit open — returning empty entities")
            return []
        except httpx.HTTPError as e:
            logger.error("Failed to fetch entities from Data API: %s", e)
            raise
        except Exception as e:
            logger.error("Unexpected error fetching entities: %s", e)
            raise

    async def fetch_activity_history(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Fetch activity history from Data API (Epic Activity Recognition Story 3.1).

        Returns list of {activity, activity_id, confidence, timestamp}.
        Graceful degradation: on failure returns [].
        """
        try:
            params: dict[str, Any] = {"hours": hours, "limit": limit}
            response = await self._cross_client.call(
                "GET", "/api/v1/activity/history", params=params,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            logger.warning("Unexpected activity history response format: %s", type(data))
            return []
        except CircuitOpenError:
            logger.warning("Data API circuit open — activity history returning empty")
            return []
        except httpx.HTTPError as e:
            logger.warning("Failed to fetch activity history: %s", e)
            return []
        except Exception as e:
            logger.warning("Unexpected error fetching activity history: %s", e)
            return []

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Generic GET request to the Data API."""
        try:
            response = await self._cross_client.call("GET", path, params=params)
            response.raise_for_status()
            return response.json()
        except CircuitOpenError:
            logger.warning("Data API circuit open — GET %s returning empty", path)
            return {}
        except httpx.HTTPError as e:
            logger.error("GET %s failed: %s", path, e)
            raise

    async def close(self):
        """No-op — CrossGroupClient uses per-request clients."""
        logger.debug("Data API client close (no-op with CrossGroupClient)")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
