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
        bucket: str = "home_assistant_events"
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
        limit: int = 10000
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
            flux_query = f'''
                from(bucket: "{self.bucket}")
                  |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                  |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
                  |> filter(fn: (r) => r["_field"] == "context_id")
                  |> filter(fn: (r) => r["event_type"] == "state_changed")
            '''

            # Add entity_id filter
            if entity_id:
                flux_query += f'''
                  |> filter(fn: (r) => r["entity_id"] == "{entity_id}")
                '''

            # Add domain filter (if entity_id contains domain)
            if domain:
                flux_query += f'''
                  |> filter(fn: (r) => contains(value: "{domain}.", set: r["entity_id"]))
                '''

            # Sort and limit
            flux_query += f'''
                  |> sort(columns: ["_time"])
                  |> limit(n: {limit})
            '''

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
                    entity_id = record.values.get('entity_id', '')
                    domain = entity_id.split('.')[0] if '.' in entity_id else ''

                    # When querying context_id, state is not available
                    # Pattern detectors will need entity_id and timestamp
                    event = {
                        '_time': record.get_time(),
                        'entity_id': entity_id,
                        'state': '',  # Not available when querying context_id - would need separate query for state_value
                        'domain': domain,
                        'friendly_name': record.values.get('attr_friendly_name', entity_id),
                        'device_id': record.values.get('device_id', entity_id),
                        'event_type': record.values.get('event_type', 'state_changed'),
                        'context_id': record.get_value()  # This is the context_id from _value
                    }
                    events.append(event)

            if not events:
                logger.warning(f"No events found in InfluxDB for period {start_time} to {end_time}")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(events)

            # Ensure _time is datetime and create required columns for pattern detectors
            if '_time' in df.columns:
                df['_time'] = pd.to_datetime(df['_time'])
                # Pattern detectors expect 'timestamp', 'device_id', and 'last_changed'
                df['timestamp'] = df['_time']
                df['last_changed'] = df['_time']

            # Pattern detectors expect 'device_id' but we have 'entity_id'
            # In Home Assistant, entity_id is essentially the device identifier
            if 'entity_id' in df.columns and 'device_id' not in df.columns:
                df['device_id'] = df['entity_id']

            logger.info(f"✅ Fetched {len(df)} events from InfluxDB (columns: {list(df.columns)})")

            return df

        except Exception as e:
            logger.error(f"❌ Failed to fetch events from InfluxDB: {e}", exc_info=True)
            raise

    async def fetch_entity_attributes(
        self,
        entity_id: str,
        attributes: list[str],
        start_time: datetime | None = None,
        end_time: datetime | None = None
    ) -> dict[str, bool]:
        """
        Check which attributes have been set/changed for an entity in the last 30 days.
        
        Phase 4.1 Enhancement: InfluxDB Attribute Querying
        Queries InfluxDB for attribute fields (attr_brightness, attr_color_temp, etc.)
        to detect feature usage patterns.
        
        Args:
            entity_id: Entity ID to check (e.g., "light.office")
            attributes: List of attribute names to check (e.g., ["brightness", "color_temp", "led_effect"])
            start_time: Start of time range (default: 30 days ago)
            end_time: End of time range (default: now)
        
        Returns:
            Dictionary mapping attribute names to boolean (True if attribute was used):
            {"brightness": True, "color_temp": False, "led_effect": True}
        
        Example:
            >>> usage = await client.fetch_entity_attributes(
            ...     "light.office",
            ...     ["brightness", "color_temp", "led_effect"]
            ... )
            >>> print(usage)
            {"brightness": True, "color_temp": False, "led_effect": True}
        """
        try:
            # Default time range: last 30 days
            if start_time is None:
                start_time = datetime.now(timezone.utc) - timedelta(days=30)
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            
            # Build attribute usage map (default False)
            attribute_usage = {attr: False for attr in attributes}
            
            if not attributes:
                return attribute_usage
            
            # Build Flux query for each attribute field
            # Attributes are stored as fields with "attr_" prefix in InfluxDB
            attribute_fields = [f"attr_{attr}" for attr in attributes]
            
            # Query multiple fields using union approach
            flux_query = f'''
                from(bucket: "{self.bucket}")
                  |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                  |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
                  |> filter(fn: (r) => r["entity_id"] == "{entity_id}")
                  |> filter(fn: (r) => r["_field"] == "state_value" or {self._build_field_filter(attribute_fields)})
                  |> filter(fn: (r) => exists r["_value"] and r["_value"] != null)
                  |> limit(n: 1000)
            '''
            
            logger.debug(f"Querying InfluxDB for entity attributes: {entity_id}, attributes={attributes}")
            
            # Execute query
            tables = self.query_api.query(flux_query, org=self.org)
            
            # Process results - check which attribute fields have values
            found_fields = set()
            for table in tables:
                for record in table.records:
                    field_name = record.get_field()
                    # Remove "attr_" prefix if present
                    if field_name.startswith("attr_"):
                        attr_name = field_name[5:]  # Remove "attr_" prefix
                        if attr_name in attributes:
                            found_fields.add(attr_name)
                            attribute_usage[attr_name] = True
                    elif field_name == "state_value":
                        # State value changes indicate basic usage
                        continue
            
            logger.debug(f"Entity {entity_id} attribute usage: {dict(attribute_usage)}")
            
            return attribute_usage
            
        except Exception as e:
            logger.warning(f"Failed to fetch entity attributes for {entity_id}: {e}")
            # Return default (all False) on error
            return {attr: False for attr in attributes}
    
    def _build_field_filter(self, field_names: list[str]) -> str:
        """Build Flux filter expression for multiple field names."""
        if not field_names:
            return 'false'
        
        conditions = ' or '.join([f'r["_field"] == "{field}"' for field in field_names])
        return f'({conditions})'
    
    def close(self):
        """Close the InfluxDB client connection"""
        if self.client:
            self.client.close()
            logger.info("InfluxDB client closed")

