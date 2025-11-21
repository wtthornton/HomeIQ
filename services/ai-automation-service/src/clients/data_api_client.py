"""
Data API Client for AI Automation Service

Provides access to historical Home Assistant data via InfluxDB and Data API service.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pandas as pd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .capability_parsers import BitmaskCapabilityParser
from .influxdb_client import InfluxDBEventClient

logger = logging.getLogger(__name__)


class DataAPIClient:
    """Client for fetching historical data from InfluxDB and Data API"""

    def __init__(
        self,
        base_url: str = "http://data-api:8006",
        influxdb_url: str = "http://influxdb:8086",
        influxdb_token: str = "homeiq-token",
        influxdb_org: str = "homeiq",
        influxdb_bucket: str = "home_assistant_events",
    ):
        """
        Initialize Data API client.

        Args:
            base_url: Base URL for Data API (default: http://data-api:8006)
            influxdb_url: InfluxDB URL for direct event queries
            influxdb_token: InfluxDB authentication token
            influxdb_org: InfluxDB organization
            influxdb_bucket: InfluxDB bucket name
        """
        self.base_url = base_url.rstrip("/")
        # Optional API key for authenticated Data API access
        api_key = os.getenv("DATA_API_API_KEY") or os.getenv("DATA_API_KEY") or os.getenv("API_KEY")
        default_headers = {}
        if api_key:
            default_headers["Authorization"] = f"Bearer {api_key}"

        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers=default_headers,
        )

        # Initialize InfluxDB client for direct event queries
        self.influxdb_client = InfluxDBEventClient(
            url=influxdb_url,
            token=influxdb_token,
            org=influxdb_org,
            bucket=influxdb_bucket,
        )

        # Initialize capability parser
        self.capability_parser = BitmaskCapabilityParser()

        logger.info(f"Data API client initialized with base_url={self.base_url}")
        logger.info(f"InfluxDB client initialized with url={influxdb_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def fetch_events(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        entity_id: str | None = None,
        device_id: str | None = None,
        event_type: str | None = None,
        limit: int = 10000,
    ) -> pd.DataFrame:
        """
        Fetch historical events from Data API.

        Args:
            start_time: Start datetime (default: 30 days ago)
            end_time: End datetime (default: now)
            entity_id: Optional filter for specific entity
            device_id: Optional filter for specific device
            event_type: Optional filter for event type (e.g., 'state_changed')
            limit: Maximum number of events to return

        Returns:
            pandas DataFrame with columns: timestamp, entity_id, event_type, old_state, new_state, attributes, tags

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            # Default to last 30 days
            if start_time is None:
                start_time = datetime.now(timezone.utc) - timedelta(days=30)
            if end_time is None:
                end_time = datetime.now(timezone.utc)

            # Build query parameters
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

            logger.info(f"Fetching events from Data API: start={start_time}, end={end_time}, limit={limit}")

            # Try Data API first (more reliable, already tested)
            try:
                # Build query params
                # Data API supports start_time and end_time as ISO strings
                params = {
                    "limit": limit,
                }
                if start_time:
                    params["start_time"] = start_time.isoformat()
                if end_time:
                    params["end_time"] = end_time.isoformat()
                if entity_id:
                    params["entity_id"] = entity_id
                if device_id:
                    params["device_id"] = device_id
                if event_type:
                    params["event_type"] = event_type

                # Query Data API endpoint
                response = await self.client.get(
                    f"{self.base_url}/api/v1/events",
                    params=params,
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

                # Convert to DataFrame format expected by pattern detectors
                df_data = []
                for event in events:
                    # Extract timestamp
                    timestamp_str = event.get("timestamp", event.get("time_fired"))
                    if isinstance(timestamp_str, str):
                        timestamp = pd.to_datetime(timestamp_str)
                    else:
                        timestamp = pd.to_datetime(event.get("_time", datetime.now(timezone.utc)))

                    # Extract entity_id and state
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
                logger.info(f"✅ Fetched {len(df)} events from Data API")
                return df

            except Exception as e:
                logger.warning(f"Data API query failed: {e}, falling back to direct InfluxDB query")
                # Fallback to direct InfluxDB query
                df = await self.influxdb_client.fetch_events(
                    start_time=start_time,
                    end_time=end_time,
                    entity_id=entity_id,
                    limit=limit,
                )

                if df.empty:
                    logger.warning(f"No events returned from InfluxDB for period {start_time} to {end_time}")
                    return pd.DataFrame()

                logger.info(f"✅ Fetched {len(df)} events from InfluxDB (fallback)")
                return df

        except httpx.HTTPError as e:
            logger.exception(f"❌ Failed to fetch events from Data API: {e}")
            raise
        except Exception as e:
            logger.exception(f"❌ Unexpected error fetching events: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def fetch_devices(
        self,
        manufacturer: str | None = None,
        model: str | None = None,
        area_id: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Fetch all devices from Data API.

        Args:
            manufacturer: Optional filter by manufacturer
            model: Optional filter by model
            area_id: Optional filter by area/room
            limit: Maximum number of devices to return

        Returns:
            List of device dictionaries with keys: device_id, name, manufacturer, model, area_id, entity_count

        Raises:
            httpx.HTTPError: If API request fails
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
                params=params,
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
            logger.exception(f"❌ Failed to fetch devices from Data API: {e}")
            raise
        except Exception as e:
            logger.exception(f"❌ Unexpected error fetching devices: {e}")
            raise

    async def get_all_devices(self) -> list[dict[str, Any]]:
        """
        Get all devices from Data API (alias for fetch_devices with no filters).

        Returns:
            List of all device dictionaries
        """
        return await self.fetch_devices()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def fetch_entities(
        self,
        device_id: str | None = None,
        domain: str | None = None,
        platform: str | None = None,
        area_id: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Fetch all entities from Data API.

        Args:
            device_id: Optional filter by device ID
            domain: Optional filter by domain (light, sensor, switch, etc)
            platform: Optional filter by integration platform
            area_id: Optional filter by area/room
            limit: Maximum number of entities to return

        Returns:
            List of entity dictionaries with keys: entity_id, device_id, domain, platform, area_id, disabled

        Raises:
            httpx.HTTPError: If API request fails
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
                params=params,
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
            logger.exception(f"❌ Failed to fetch entities from Data API: {e}")
            raise
        except Exception as e:
            logger.exception(f"❌ Unexpected error fetching entities: {e}")
            raise

    async def health_check(self) -> dict[str, Any]:
        """
        Check Data API health status.

        Returns:
            Health status dictionary

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.exception(f"❌ Data API health check failed: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def get_entity_metadata(self, entity_id: str) -> dict[str, Any] | None:
        """
        Fetch entity metadata including friendly name and device info.

        Args:
            entity_id: Entity ID to lookup (e.g., 'light.office_lamp')

        Returns:
            Dictionary with entity metadata including friendly_name, or None if not found
        """
        try:
            # Query data-api for entity metadata
            response = await self.client.get(
                f"{self.base_url}/api/entities/{entity_id}",
            )

            if response.status_code == 200:
                data = response.json()
                logger.debug(f"Retrieved metadata for {entity_id}: {data.get('friendly_name', entity_id)}")
                return data
            if response.status_code == 404:
                logger.warning(f"Entity {entity_id} not found in metadata")
                return None
            logger.warning(f"Unexpected status {response.status_code} fetching entity {entity_id}")
            return None

        except httpx.HTTPError as e:
            logger.exception(f"Failed to fetch entity metadata for {entity_id}: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def get_device_metadata(self, device_id: str) -> dict[str, Any] | None:
        """
        Fetch device metadata including name, manufacturer, model, and area.

        Args:
            device_id: Device ID to lookup

        Returns:
            Dictionary with device metadata, or None if not found
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/devices/{device_id}",
            )

            if response.status_code == 200:
                data = response.json()
                logger.debug(f"Retrieved device metadata for {device_id}: {data.get('name', device_id)}")
                return data
            if response.status_code == 404:
                logger.warning(f"Device {device_id} not found in metadata")
                return None
            logger.warning(f"Unexpected status {response.status_code} fetching device {device_id}")
            return None

        except httpx.HTTPError as e:
            logger.exception(f"Failed to fetch device metadata for {device_id}: {e}")
            return None

    def extract_friendly_name(self, entity_id: str, metadata: dict | None = None) -> str:
        """
        Extract friendly name from entity metadata or generate from entity_id.

        Args:
            entity_id: Entity ID (e.g., 'light.office_lamp')
            metadata: Optional entity metadata dict

        Returns:
            User-friendly name (e.g., 'Office Lamp' instead of 'light.office_lamp')
        """
        # Try to get from metadata first
        if metadata and "friendly_name" in metadata:
            return metadata["friendly_name"]

        if metadata and "name" in metadata:
            return metadata["name"]

        # Fallback: Generate from entity_id
        # Remove domain prefix (e.g., 'light.', 'switch.')
        name = entity_id.split(".", 1)[1] if "." in entity_id else entity_id

        # Replace underscores with spaces and title case
        return name.replace("_", " ").title()


    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False,
    )
    async def fetch_device_capabilities(
        self,
        entity_id: str,
        use_cache: bool = True,
        cache_ttl_seconds: int = 3600,
    ) -> dict:
        """
        Fetch device capabilities for conversational suggestions.

        Story AI1.23 Phase 2: Description-Only Generation

        This method fetches device metadata and parses supported features
        to provide user-friendly capability information for:
        - Showing users what's possible ("This light can also...")
        - Validating refinement requests ("Can change RGB color? Yes/No")
        - Building better prompts for OpenAI

        Args:
            entity_id: Entity ID (e.g., 'light.living_room')
            use_cache: Whether to use cached capabilities (default: True)
            cache_ttl_seconds: Cache TTL in seconds (default: 3600 = 1 hour)

        Returns:
            Dictionary with parsed capabilities:
            {
                "entity_id": "light.living_room",
                "friendly_name": "Living Room Light",
                "domain": "light",
                "area": "Living Room",
                "supported_features": {
                    "brightness": True,
                    "rgb_color": True,
                    "color_temp": True,
                    "transition": True,
                    "effect": False
                },
                "friendly_capabilities": [
                    "Adjust brightness (0-100%)",
                    "Change color (RGB)",
                    "Set color temperature (warm to cool)",
                    "Smooth transitions (fade in/out)"
                ],
                "cached": False
            }
        """
        try:
            logger.debug(f"Fetching capabilities for {entity_id}")

            # Fetch entity metadata from data-api
            response = await self.client.get(
                f"{self.base_url}/api/entities/{entity_id}",
            )

            if response.status_code == 404:
                logger.warning(f"Entity {entity_id} not found")
                return self._empty_capabilities(entity_id)

            if response.status_code != 200:
                logger.warning(f"Failed to fetch entity {entity_id}: HTTP {response.status_code}")
                return self._empty_capabilities(entity_id)

            entity_data = response.json()

            # Parse capabilities from entity data
            capabilities = self._parse_capabilities(entity_id, entity_data)

            logger.info(
                f"✅ Fetched capabilities for {entity_id}: "
                f"{len(capabilities['friendly_capabilities'])} features",
            )

            return capabilities

        except Exception as e:
            logger.exception(f"Error fetching capabilities for {entity_id}: {e}")
            return self._empty_capabilities(entity_id)

    def _parse_capabilities(self, entity_id: str, entity_data: dict) -> dict:
        """
        Parse entity metadata into structured capabilities.

        Uses the new bitmask parser to eliminate hardcoded elif chains.

        Args:
            entity_id: Entity ID
            entity_data: Raw entity metadata from data-api

        Returns:
            Parsed capabilities dictionary
        """
        domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
        attributes = entity_data.get("attributes", {})

        # Extract basic info
        capabilities = {
            "entity_id": entity_id,
            "friendly_name": entity_data.get("friendly_name", entity_data.get("name", entity_id)),
            "domain": domain,
            "area": entity_data.get("area_id", entity_data.get("area", "")),
            "supported_features": {},
            "friendly_capabilities": [],
            "cached": False,
        }

        # Use new bitmask parser (replaces hardcoded elif chains)
        supported_features_bitmask = attributes.get("supported_features", 0)
        parsed_caps = self.capability_parser.parse_capabilities(
            domain=domain,
            supported_features=supported_features_bitmask,
            attributes=attributes,
        )

        # Merge parsed capabilities
        capabilities["supported_features"] = parsed_caps.get("supported_features", {})
        capabilities["friendly_capabilities"] = parsed_caps.get("friendly_capabilities", [])

        return capabilities

    def _empty_capabilities(self, entity_id: str) -> dict:
        """Return empty capabilities structure for unknown/error cases"""
        domain = entity_id.split(".")[0] if "." in entity_id else "unknown"

        return {
            "entity_id": entity_id,
            "friendly_name": self.extract_friendly_name(entity_id),
            "domain": domain,
            "area": "",
            "supported_features": {},
            "friendly_capabilities": [],
            "cached": False,
        }

    async def get_weather_entities(self) -> list[dict[str, Any]]:
        """
        Get all weather-related entities from Home Assistant.

        Returns:
            List of weather entity dictionaries
        """
        try:
            # Get all entities with weather domain
            weather_entities = await self.fetch_entities(domain="weather", limit=100)

            # Also get sensor entities that might be weather-related
            sensor_entities = await self.fetch_entities(domain="sensor", limit=1000)

            # Filter sensor entities for weather-related ones
            weather_sensors = [
                entity for entity in sensor_entities
                if any(keyword in entity.get("entity_id", "").lower()
                      for keyword in ["weather", "temperature", "humidity", "pressure", "wind", "precipitation", "sun"])
            ]

            # Combine weather domain and weather-related sensors
            all_weather_entities = weather_entities + weather_sensors

            logger.info(f"Found {len(all_weather_entities)} weather entities")
            return all_weather_entities

        except Exception as e:
            logger.exception(f"Failed to get weather entities: {e}")
            return []

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

