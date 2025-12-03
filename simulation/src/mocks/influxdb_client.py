"""
Mock InfluxDB Client

In-memory event storage using pandas DataFrames for simulation.
Maintains same interface as production InfluxDBEventClient.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class MockInfluxDBClient:
    """
    Mock InfluxDB client for simulation.
    
    Stores events in-memory using pandas DataFrames.
    Maintains same interface as InfluxDBEventClient.
    """

    def __init__(
        self,
        url: str = "http://mock-influxdb:8086",
        token: str = "mock-token",
        org: str = "mock-org",
        bucket: str = "home_assistant_events"
    ):
        """
        Initialize mock InfluxDB client.
        
        Args:
            url: Mock URL (not used)
            token: Mock token (not used)
            org: Mock org (not used)
            bucket: Bucket name (for organization)
        """
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        
        # In-memory storage: dict[bucket_name, DataFrame]
        self._storage: dict[str, pd.DataFrame] = {}
        
        logger.info(f"MockInfluxDBClient initialized: bucket={bucket}")

    async def fetch_events(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        entity_id: str | None = None,
        domain: str | None = None,
        limit: int = 10000
    ) -> pd.DataFrame:
        """
        Fetch events from in-memory storage.
        
        Args:
            start_time: Start of time range (default: 30 days ago)
            end_time: End of time range (default: now)
            entity_id: Filter by specific entity ID
            domain: Filter by domain (e.g., 'light', 'switch')
            limit: Maximum number of events to return
            
        Returns:
            DataFrame with columns: _time, entity_id, state, domain, friendly_name, device_id
        """
        # Default time range: last 30 days
        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(days=30)
        if end_time is None:
            end_time = datetime.now(timezone.utc)

        # Get events from storage
        if self.bucket not in self._storage:
            logger.warning(f"No events in bucket {self.bucket}")
            return pd.DataFrame()

        df = self._storage[self.bucket].copy()

        # Filter by time range
        if '_time' in df.columns:
            df = df[(df['_time'] >= start_time) & (df['_time'] <= end_time)]

        # Filter by entity_id
        if entity_id:
            df = df[df['entity_id'] == entity_id]

        # Filter by domain
        if domain:
            df = df[df['domain'] == domain]

        # Limit results
        if len(df) > limit:
            df = df.head(limit)

        logger.debug(f"Fetched {len(df)} events from mock InfluxDB")
        return df

    async def fetch_entity_attributes(
        self,
        entity_id: str,
        attributes: list[str],
        start_time: datetime | None = None,
        end_time: datetime | None = None
    ) -> dict[str, bool]:
        """
        Check which attributes have been set for an entity.
        
        Args:
            entity_id: Entity ID to check
            attributes: List of attribute names to check
            start_time: Start of time range (default: 30 days ago)
            end_time: End of time range (default: now)
            
        Returns:
            Dictionary mapping attribute names to boolean (True if attribute was used)
        """
        # Default time range: last 30 days
        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(days=30)
        if end_time is None:
            end_time = datetime.now(timezone.utc)

        # Build attribute usage map (default False)
        attribute_usage = {attr: False for attr in attributes}

        if self.bucket not in self._storage:
            return attribute_usage

        df = self._storage[self.bucket].copy()

        # Filter by entity and time
        df = df[(df['entity_id'] == entity_id) & 
                (df['_time'] >= start_time) & 
                (df['_time'] <= end_time)]

        # Check for attribute columns (attr_*)
        for attr in attributes:
            attr_col = f"attr_{attr}"
            if attr_col in df.columns:
                # Check if any non-null values exist
                if df[attr_col].notna().any():
                    attribute_usage[attr] = True

        logger.debug(f"Entity {entity_id} attribute usage: {attribute_usage}")
        return attribute_usage

    def load_events(self, events: pd.DataFrame, bucket: str | None = None) -> None:
        """
        Load events into in-memory storage.
        
        Args:
            events: DataFrame with event data
            bucket: Bucket name (default: self.bucket)
        """
        bucket_name = bucket or self.bucket
        
        if bucket_name not in self._storage:
            self._storage[bucket_name] = pd.DataFrame()
        
        # Append events
        self._storage[bucket_name] = pd.concat([
            self._storage[bucket_name],
            events
        ], ignore_index=True)
        
        logger.info(f"Loaded {len(events)} events into bucket {bucket_name}")

    def clear_storage(self, bucket: str | None = None) -> None:
        """Clear in-memory storage."""
        bucket_name = bucket or self.bucket
        if bucket_name in self._storage:
            del self._storage[bucket_name]
            logger.info(f"Cleared storage for bucket {bucket_name}")

    def close(self) -> None:
        """Close the mock client (no-op)."""
        logger.debug("MockInfluxDBClient closed")

