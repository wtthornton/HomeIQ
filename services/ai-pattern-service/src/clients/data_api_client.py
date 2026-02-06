"""
Data API Client for Pattern Service

Epic 39, Story 39.6: Daily Scheduler Migration
Simplified client for fetching events, devices, and entities from data-api.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pandas as pd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class DataAPIClient:
    """Client for fetching historical data from Data API service"""

    def __init__(
        self,
        base_url: str = "http://data-api:8006",
        influxdb_url: str | None = None,
        influxdb_token: str | None = None,
        influxdb_org: str | None = None,
        influxdb_bucket: str | None = None
    ):
        """
        Initialize Data API client.
        
        Args:
            base_url: Base URL for Data API (default: http://data-api:8006)
            influxdb_url: Optional InfluxDB URL for direct queries
            influxdb_token: Optional InfluxDB token
            influxdb_org: Optional InfluxDB organization
            influxdb_bucket: Optional InfluxDB bucket
        """
        self.base_url = base_url.rstrip('/')
        api_key = os.getenv("DATA_API_API_KEY") or os.getenv("DATA_API_KEY") or os.getenv("API_KEY")
        default_headers = {}
        if api_key:
            default_headers["Authorization"] = f"Bearer {api_key}"

        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers=default_headers
        )

        # Store InfluxDB config for optional direct queries
        self.influxdb_url = influxdb_url
        self.influxdb_token = influxdb_token
        self.influxdb_org = influxdb_org
        self.influxdb_bucket = influxdb_bucket
        self.influxdb_client = None  # Will be initialized if needed

        logger.info(f"Data API client initialized with base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def fetch_events(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        entity_id: str | None = None,
        device_id: str | None = None,
        event_type: str | None = None,
        limit: int = 10000
    ) -> pd.DataFrame:
        """
        Fetch historical events from Data API.
        
        Args:
            start_time: Start datetime (default: 30 days ago)
            end_time: End datetime (default: now)
            entity_id: Optional filter for specific entity
            device_id: Optional filter for specific device
            event_type: Optional filter for event type
            limit: Maximum number of events to return
        
        Returns:
            pandas DataFrame with event data
        """
        try:
            # Default to last 7 days for pattern detection
            if start_time is None:
                start_time = datetime.now(timezone.utc) - timedelta(days=7)
            if end_time is None:
                end_time = datetime.now(timezone.utc)

            params: dict[str, Any] = {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "limit": limit
            }

            if entity_id:
                params["entity_id"] = entity_id
            if device_id:
                params["device_id"] = device_id
            if event_type:
                params["event_type"] = event_type

            logger.info(f"Fetching events from Data API: start={start_time}, end={end_time}, limit={limit}")

            response = await self.client.get(
                f"{self.base_url}/api/v1/events",
                params=params
            )
            response.raise_for_status()

            events_data = response.json()

            # Handle list response format
            if isinstance(events_data, list):
                events = events_data
            elif isinstance(events_data, dict) and "events" in events_data:
                events = events_data["events"]
            else:
                events = []

            if not events:
                logger.warning(f"No events returned from Data API for period {start_time} to {end_time}")
                return pd.DataFrame()

            # Convert to DataFrame
            df_data = []
            for event in events:
                timestamp_str = event.get("timestamp", event.get("time_fired"))
                if isinstance(timestamp_str, str):
                    timestamp = pd.to_datetime(timestamp_str)
                else:
                    timestamp = pd.to_datetime(event.get("_time", datetime.now(timezone.utc)))

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
                    "friendly_name": event.get("friendly_name", entity_id_val)
                })

            df = pd.DataFrame(df_data)
            logger.info(f"✅ Fetched {len(df)} events from Data API")
            return df

        except httpx.HTTPError as e:
            logger.error(f"❌ Failed to fetch events from Data API: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching events: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def fetch_devices(
        self,
        manufacturer: str | None = None,
        model: str | None = None,
        area_id: str | None = None,
        limit: int = 1000
    ) -> list[dict[str, Any]]:
        """
        Fetch all devices from Data API.
        
        Args:
            manufacturer: Optional filter by manufacturer
            model: Optional filter by model
            area_id: Optional filter by area/room
            limit: Maximum number of devices to return
        
        Returns:
            List of device dictionaries
        """
        try:
            params: dict[str, Any] = {"limit": limit}

            if manufacturer:
                params["manufacturer"] = manufacturer
            if model:
                params["model"] = model
            if area_id:
                params["area_id"] = area_id

            logger.info(f"Fetching devices from Data API (limit={limit})")

            response = await self.client.get(
                f"{self.base_url}/api/devices",
                params=params
            )
            response.raise_for_status()

            data = response.json()

            # Handle response format
            if isinstance(data, dict) and "devices" in data:
                devices = data["devices"]
            elif isinstance(data, list):
                devices = data
            else:
                logger.warning(f"Unexpected devices response format: {type(data)}")
                devices = []

            logger.info(f"✅ Fetched {len(devices)} devices from Data API")
            return devices

        except httpx.HTTPError as e:
            logger.error(f"❌ Failed to fetch devices from Data API: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching devices: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def fetch_entities(
        self,
        device_id: str | None = None,
        domain: str | None = None,
        platform: str | None = None,
        area_id: str | None = None,
        limit: int = 1000
    ) -> list[dict[str, Any]]:
        """
        Fetch all entities from Data API.
        
        Args:
            device_id: Optional filter by device ID
            domain: Optional filter by domain
            platform: Optional filter by platform
            area_id: Optional filter by area/room
            limit: Maximum number of entities to return
        
        Returns:
            List of entity dictionaries
        """
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

            logger.info(f"Fetching entities from Data API (limit={limit})")

            response = await self.client.get(
                f"{self.base_url}/api/entities",
                params=params
            )
            response.raise_for_status()

            data = response.json()

            # Handle response format
            if isinstance(data, dict) and "entities" in data:
                entities = data["entities"]
            elif isinstance(data, list):
                entities = data
            else:
                logger.warning(f"Unexpected entities response format: {type(data)}")
                entities = []

            logger.info(f"✅ Fetched {len(entities)} entities from Data API")
            return entities

        except httpx.HTTPError as e:
            logger.error(f"❌ Failed to fetch entities from Data API: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching entities: {e}")
            raise

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Generic GET request to the Data API.

        Args:
            path: API path (e.g., "/api/devices")
            params: Optional query parameters

        Returns:
            Parsed JSON response as a dictionary
        """
        try:
            response = await self.client.get(
                f"{self.base_url}{path}",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"GET {path} failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in GET {path}: {e}")
            raise

    async def close(self):
        """Close HTTP client connection pool"""
        await self.client.aclose()
        logger.info("Data API client closed")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

