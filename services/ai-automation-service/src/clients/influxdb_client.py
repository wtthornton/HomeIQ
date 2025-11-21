"""
InfluxDB Client for fetching Home Assistant events
Direct query to InfluxDB for historical event data
"""

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd
from influxdb_client import InfluxDBClient as InfluxClient

logger = logging.getLogger(__name__)


class InfluxDBEventClient:
    """Client for querying Home Assistant events from InfluxDB"""

    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        bucket: str = "home_assistant_events",
    ):
        """
        Initialize InfluxDB client.

        Args:
            url: InfluxDB URL (e.g., http://influxdb:8086)
            token: InfluxDB authentication token
            org: InfluxDB organization
            bucket: Bucket name (default: home_assistant_events)
        """
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket

        self.client = InfluxClient(url=url, token=token, org=org)
        self.query_api = self.client.query_api()

        logger.info(f"InfluxDB client initialized: {url}, org={org}, bucket={bucket}")

    async def fetch_events(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        entity_id: str | None = None,
        domain: str | None = None,
        limit: int = 10000,
    ) -> pd.DataFrame:
        """
        Fetch Home Assistant events from InfluxDB.

        Args:
            start_time: Start of time range (default: 30 days ago)
            end_time: End of time range (default: now)
            entity_id: Filter by specific entity ID
            domain: Filter by domain (e.g., 'light', 'switch')
            limit: Maximum number of events to return

        Returns:
            DataFrame with columns: _time, entity_id, state, domain, friendly_name
        """
        try:
            # Default time range: last 30 days
            if start_time is None:
                start_time = datetime.now(timezone.utc) - timedelta(days=30)
            if end_time is None:
                end_time = datetime.now(timezone.utc)

            # Build Flux query
            # Query the home_assistant_events measurement
            # Use context_id field (like data-api) to get one record per event
            # Tags (entity_id, event_type, domain) are automatically included
            flux_query = f"""
                from(bucket: "{self.bucket}")
                  |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                  |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
                  |> filter(fn: (r) => r["_field"] == "context_id")
            """

            # Add event_type filter if needed (it's a tag)
            if not event_type:
                # Default to state_changed for pattern detection
                flux_query += """
                  |> filter(fn: (r) => r["event_type"] == "state_changed")
                """
            else:
                flux_query += f"""
                  |> filter(fn: (r) => r["event_type"] == "{event_type}")
                """

            # Add entity_id filter
            if entity_id:
                flux_query += f"""
                  |> filter(fn: (r) => r["entity_id"] == "{entity_id}")
                """

            # Add domain filter (if entity_id contains domain)
            if domain:
                flux_query += f"""
                  |> filter(fn: (r) => contains(value: "{domain}.", set: r["entity_id"]))
                """

            # Sort and limit
            flux_query += f"""
                  |> sort(columns: ["_time"])
                  |> limit(n: {limit})
            """

            logger.info(f"Querying InfluxDB for events: {start_time} to {end_time}, limit={limit}")

            # Execute query (sync - InfluxDB client doesn't have true async)
            tables = self.query_api.query(flux_query, org=self.org)

            # Convert to list of dicts
            # Note: When querying context_id field, _value contains context_id, not state
            # We need to query state_value field to get the actual state
            # For now, use entity_id and timestamp for pattern detection
            events = []
            for table in tables:
                for record in table.records:
                    # Extract entity_id to determine domain
                    entity_id = record.values.get("entity_id", "")
                    domain = entity_id.split(".")[0] if "." in entity_id else ""

                    # When querying context_id, state is not available
                    # Pattern detectors will need entity_id and timestamp
                    event = {
                        "_time": record.get_time(),
                        "entity_id": entity_id,
                        "state": "",  # Not available when querying context_id - would need separate query for state_value
                        "domain": domain,
                        "friendly_name": record.values.get("attr_friendly_name", entity_id),
                        "device_id": record.values.get("device_id", entity_id),
                        "event_type": record.values.get("event_type", "state_changed"),
                        "context_id": record.get_value(),  # This is the context_id from _value
                    }
                    events.append(event)

            if not events:
                logger.warning(f"No events found in InfluxDB for period {start_time} to {end_time}")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(events)

            # Ensure _time is datetime and create required columns for pattern detectors
            if "_time" in df.columns:
                df["_time"] = pd.to_datetime(df["_time"])
                # Pattern detectors expect 'timestamp', 'device_id', and 'last_changed'
                df["timestamp"] = df["_time"]
                df["last_changed"] = df["_time"]

            # Pattern detectors expect 'device_id' but we have 'entity_id'
            # In Home Assistant, entity_id is essentially the device identifier
            if "entity_id" in df.columns and "device_id" not in df.columns:
                df["device_id"] = df["entity_id"]

            logger.info(f"✅ Fetched {len(df)} events from InfluxDB (columns: {list(df.columns)})")

            return df

        except Exception as e:
            logger.error(f"❌ Failed to fetch events from InfluxDB: {e}", exc_info=True)
            raise

    def close(self):
        """Close the InfluxDB client connection"""
        if self.client:
            self.client.close()
            logger.info("InfluxDB client closed")

