"""
Event Injector for Testing

Utilities for injecting synthetic events into InfluxDB for testing pattern
detection and synergy detection systems.

Phase 1: Foundation - Event Injection
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.delete_api import DeleteApi
from influxdb_client.client.write_api import SYNCHRONOUS, WriteApi

logger = logging.getLogger(__name__)


class EventInjector:
    """Inject synthetic events into InfluxDB for testing"""
    
    def __init__(
        self,
        influxdb_url: str = "http://localhost:8086",
        influxdb_token: str = "homeiq-token",
        influxdb_org: str = "homeiq",
        influxdb_bucket: str = "home_assistant_events"
    ):
        """
        Initialize event injector.
        
        Args:
            influxdb_url: InfluxDB URL
            influxdb_token: InfluxDB authentication token
            influxdb_org: InfluxDB organization
            influxdb_bucket: InfluxDB bucket name
        """
        self.influxdb_url = influxdb_url
        self.influxdb_token = influxdb_token
        self.influxdb_org = influxdb_org
        self.influxdb_bucket = influxdb_bucket
        
        self.client: InfluxDBClient | None = None
        self.write_api: WriteApi | None = None
        
        logger.info(f"Event injector initialized: {influxdb_url}/{influxdb_bucket}")
    
    def connect(self):
        """Connect to InfluxDB"""
        try:
            self.client = InfluxDBClient(
                url=self.influxdb_url,
                token=self.influxdb_token,
                org=self.influxdb_org
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            logger.info("✅ Connected to InfluxDB")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from InfluxDB"""
        if self.write_api:
            self.write_api.close()
        if self.client:
            self.client.close()
        logger.info("Disconnected from InfluxDB")
    
    async def inject_events(self, events: list[dict[str, Any]]) -> int:
        """
        Inject a list of events into InfluxDB.
        
        Args:
            events: List of event dictionaries with:
                - entity_id: Entity identifier
                - state: State value
                - timestamp: ISO format timestamp
                - attributes: Optional attributes dict
                - event_type: Event type (default: 'state_changed')
        
        Returns:
            Number of events successfully injected
        """
        if not self.client:
            self.connect()
        
        if not self.write_api:
            raise RuntimeError("InfluxDB write API not initialized")
        
        points = []
        for event in events:
            point = self._create_point_from_event(event)
            if point:
                points.append(point)
        
        if not points:
            logger.warning("No valid points created from events")
            return 0
        
        try:
            self.write_api.write(
                bucket=self.influxdb_bucket,
                record=points
            )
            logger.info(f"✅ Injected {len(points)} events into InfluxDB")
            return len(points)
        except Exception as e:
            logger.error(f"Failed to inject events: {e}")
            raise
    
    def _create_point_from_event(self, event: dict[str, Any]) -> Point | None:
        """
        Create InfluxDB Point from event dictionary.
        
        Args:
            event: Event dictionary
        
        Returns:
            InfluxDB Point or None if invalid
        """
        try:
            entity_id = event.get('entity_id')
            if not entity_id:
                logger.warning("Event missing entity_id, skipping")
                return None
            
            # Parse timestamp
            timestamp_str = event.get('timestamp')
            if timestamp_str:
                if isinstance(timestamp_str, str):
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    dt = timestamp_str
            else:
                dt = datetime.now(timezone.utc)
            
            # Create point
            point = Point("home_assistant_events") \
                .time(dt, WritePrecision.MS)
            
            # Add tags (for efficient querying)
            point = point.tag("entity_id", entity_id)
            
            event_type = event.get('event_type', 'state_changed')
            point = point.tag("event_type", event_type)
            
            # Extract domain from entity_id (e.g., 'light.kitchen' -> 'light')
            if '.' in entity_id:
                domain = entity_id.split('.')[0]
                point = point.tag("domain", domain)
            
            # Add fields
            state = event.get('state', 'unknown')
            point = point.field("state_value", state)
            
            # Add context_id (required field for our schema)
            context_id = event.get('context_id', f"test-{entity_id}-{dt.timestamp()}")
            point = point.field("context_id", context_id)
            
            # Add attributes as JSON field
            attributes = event.get('attributes', {})
            if attributes:
                import json
                point = point.field("attributes", json.dumps(attributes))
            
            return point
            
        except Exception as e:
            logger.error(f"Failed to create point from event: {e}")
            return None
    
    async def clear_test_events(self, entity_prefix: str = "test.") -> int:
        """
        Clear test events from InfluxDB (by entity prefix).
        
        Note: InfluxDB doesn't support DELETE by tag, so this is a placeholder.
        In production, you'd use a test bucket or time-based cleanup.
        
        Args:
            entity_prefix: Prefix of entity IDs to clear (e.g., 'test.')
        
        Returns:
            Number of events cleared (0 for now, as DELETE not implemented)
        """
        logger.warning(
            f"clear_test_events() called for prefix '{entity_prefix}' - "
            "InfluxDB DELETE by tag not supported. "
            "Consider using a separate test bucket or time-based cleanup."
        )
        return 0
    
    async def clear_events_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        predicate: str | None = None
    ) -> int:
        """
        Clear events in time range using InfluxDB delete API.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            predicate: Optional predicate for filtering (e.g., 'entity_id=~/"home_001_.*/"')
        
        Returns:
            Number of events deleted (estimated, as InfluxDB delete doesn't return count)
        
        Raises:
            RuntimeError: If InfluxDB client is not connected
            ValueError: If time range is invalid
        """
        if start_time >= end_time:
            raise ValueError(f"Invalid time range: start_time ({start_time}) must be before end_time ({end_time})")
        
        if not self.client:
            self.connect()
        
        if not self.client:
            raise RuntimeError("Failed to connect to InfluxDB")
        
        try:
            delete_api = DeleteApi(self.client)
            
            # Build predicate string with validation
            predicate_str = predicate or '_measurement="home_assistant_events"'
            
            # Execute delete
            delete_api.delete(
                start=start_time,
                stop=end_time,
                predicate=predicate_str,
                bucket=self.influxdb_bucket,
                org=self.influxdb_org
            )
            
            logger.info(
                f"✅ Deleted events from {start_time.isoformat()} to {end_time.isoformat()}"
                f" (predicate: {predicate_str})"
            )
            
            # InfluxDB delete doesn't return count, so we estimate based on time range
            # Return 1 to indicate success (caller can query to verify)
            return 1
            
        except Exception as e:
            logger.error(f"Failed to delete events by time range: {e}")
            raise
    
    async def clear_events_by_entity_prefix(self, prefix: str) -> int:
        """
        Clear events for entities matching a prefix pattern.
        
        Note: InfluxDB delete API doesn't support regex operators.
        This method uses a simple equality check which may not match all prefixes.
        For exact prefix matching, consider using tag-based isolation instead.
        
        Args:
            prefix: Entity ID prefix (e.g., 'home_001_' or 'test.')
        
        Returns:
            Number of events deleted (estimated)
        
        Raises:
            ValueError: If prefix is empty or invalid
        """
        if not prefix:
            raise ValueError("Prefix cannot be empty")
        
        # Use time range covering all possible test data (last 30 days)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=30)
        
        # Note: InfluxDB delete API doesn't support regex (=~) operators
        # We can only delete by exact matches or use measurement filter
        # For prefix matching, we'd need to query first to get exact entity_ids
        # For now, log a warning and use measurement-only predicate
        logger.warning(
            f"InfluxDB delete API doesn't support regex operators. "
            f"Cannot delete by prefix '{prefix}' directly. "
            f"Consider using tag-based isolation or querying first to get exact entity_ids."
        )
        
        # Use measurement-only predicate (will delete all events in time range)
        # This is a limitation - we can't filter by prefix without regex
        predicate = '_measurement="home_assistant_events"'
        
        return await self.clear_events_by_time_range(start_time, end_time, predicate)
    
    async def clear_home_events(
        self,
        home_id: str,
        time_range: tuple[datetime, datetime] | None = None
    ) -> int:
        """
        Delete all events for a specific home.
        
        Note: InfluxDB delete API doesn't support regex operators.
        This method uses time-based cleanup only. For precise home-based cleanup,
        consider using tag-based isolation (add home_id as a tag when injecting events).
        
        Args:
            home_id: Home identifier (e.g., 'home_001')
            time_range: Optional (start_time, end_time) tuple. If None, uses last 30 days.
        
        Returns:
            Number of events deleted (estimated)
        
        Raises:
            ValueError: If home_id is empty or invalid
        """
        if not home_id:
            raise ValueError("home_id cannot be empty")
        
        if time_range:
            start_time, end_time = time_range
        else:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=30)
        
        # Note: InfluxDB delete API doesn't support regex (=~) operators
        # We can only delete by exact matches or use measurement filter
        # For home-based cleanup, we'd need to:
        # 1. Add home_id as a tag when injecting events (recommended)
        # 2. Query first to get exact entity_ids matching the home
        # 3. Use time-based cleanup (current approach - less precise)
        
        logger.warning(
            f"InfluxDB delete API doesn't support regex operators. "
            f"Using time-based cleanup for home '{home_id}'. "
            f"For precise cleanup, add home_id as a tag when injecting events."
        )
        
        # Use measurement-only predicate with time range
        # This will delete all events in the time range (not just for this home)
        predicate = '_measurement="home_assistant_events"'
        
        return await self.clear_events_by_time_range(start_time, end_time, predicate)

