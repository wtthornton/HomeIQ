"""
Mock Data API Client

Direct DataFrame returns from synthetic data.
Maintains same interface as production DataAPIClient.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class MockDataAPIClient:
    """
    Mock Data API client for simulation.
    
    Returns DataFrames directly from synthetic data.
    Maintains same interface as production DataAPIClient.
    """

    def __init__(
        self,
        base_url: str = "http://mock-data-api:8006",
        influxdb_url: str | None = None,
        influxdb_token: str | None = None,
        influxdb_org: str | None = None,
        influxdb_bucket: str | None = None
    ):
        """
        Initialize mock Data API client.
        
        Args:
            base_url: Mock base URL (not used)
            influxdb_url: Mock InfluxDB URL (not used)
            influxdb_token: Mock token (not used)
            influxdb_org: Mock org (not used)
            influxdb_bucket: Mock bucket (not used)
        """
        self.base_url = base_url
        self._events_data: pd.DataFrame = pd.DataFrame()
        
        logger.info(f"MockDataAPIClient initialized: base_url={base_url}")

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
        Fetch events from synthetic data.
        
        Args:
            start_time: Start of time range (default: 30 days ago)
            end_time: End of time range (default: now)
            entity_id: Filter by specific entity ID
            device_id: Filter by device ID
            event_type: Filter by event type
            limit: Maximum number of events to return
            
        Returns:
            DataFrame with event data
        """
        # Default time range: last 7 days
        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(days=7)
        if end_time is None:
            end_time = datetime.now(timezone.utc)

        # Get events from storage
        df = self._events_data.copy()

        if df.empty:
            logger.warning("No events in mock Data API storage")
            return pd.DataFrame()

        # Filter by time range
        if 'timestamp' in df.columns:
            df = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
        elif '_time' in df.columns:
            df = df[(df['_time'] >= start_time) & (df['_time'] <= end_time)]

        # Filter by entity_id
        if entity_id:
            if 'entity_id' in df.columns:
                df = df[df['entity_id'] == entity_id]

        # Filter by device_id
        if device_id:
            if 'device_id' in df.columns:
                df = df[df['device_id'] == device_id]

        # Filter by event_type
        if event_type:
            if 'event_type' in df.columns:
                df = df[df['event_type'] == event_type]

        # Limit results
        if len(df) > limit:
            df = df.head(limit)

        logger.debug(f"Fetched {len(df)} events from mock Data API")
        return df

    def load_events(self, events: pd.DataFrame) -> None:
        """
        Load events into mock storage.
        
        Args:
            events: DataFrame with event data
        """
        self._events_data = pd.concat([
            self._events_data,
            events
        ], ignore_index=True)
        
        logger.info(f"Loaded {len(events)} events into mock Data API storage")

    def clear_storage(self) -> None:
        """Clear mock storage."""
        self._events_data = pd.DataFrame()
        logger.info("Cleared mock Data API storage")

    async def close(self) -> None:
        """Close the mock client (no-op)."""
        logger.debug("MockDataAPIClient closed")

