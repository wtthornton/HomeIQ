"""
Pattern Aggregate Client for InfluxDB
Stores and retrieves daily pattern aggregates from InfluxDB

Story: AI5.2 - InfluxDB Daily Aggregates Implementation
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger(__name__)


class PatternAggregateClient:
    """
    Client for writing and reading pattern aggregates to/from InfluxDB.

    Supports Layer 2 (Daily Aggregates) storage for all detector types.
    Story: AI5.2 - InfluxDB Daily Aggregates Implementation
    """

    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        bucket_daily: str = "pattern_aggregates_daily",
        bucket_weekly: str = "pattern_aggregates_weekly",
    ):
        """Initialize Pattern Aggregate client."""
        self.url = url
        self.token = token
        self.org = org
        self.bucket_daily = bucket_daily
        self.bucket_weekly = bucket_weekly

        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()

        logger.info(f"PatternAggregateClient initialized: buckets={bucket_daily}, {bucket_weekly}")

    # ==================== GROUP A DETECTORS - DAILY AGGREGATES ====================

    def write_time_based_daily(
        self,
        date: str,
        entity_id: str,
        domain: str,
        hourly_distribution: list[int],
        peak_hours: list[int],
        frequency: float,
        confidence: float,
        occurrences: int,
    ) -> None:
        """
        Write time-based daily aggregate to InfluxDB.

        Args:
            date: Date string (YYYY-MM-DD)
            entity_id: Entity identifier
            domain: Home Assistant domain
            hourly_distribution: Activity count for each hour (24 values)
            peak_hours: Hours with highest activity
            frequency: Average events per hour
            confidence: Pattern confidence score
            occurrences: Total events in the day
        """
        point = Point("time_based_daily") \
            .tag("date", date) \
            .tag("entity_id", entity_id) \
            .tag("domain", domain) \
            .field("hourly_distribution", json.dumps(hourly_distribution)) \
            .field("peak_hours", json.dumps(peak_hours)) \
            .field("frequency", frequency) \
            .field("confidence", confidence) \
            .field("occurrences", occurrences) \
            .time(datetime.fromisoformat(date), WritePrecision.NS)

        self.write_api.write(bucket=self.bucket_daily, record=point)
        logger.debug(f"Wrote time_based_daily aggregate: {entity_id} on {date}")

    def write_co_occurrence_daily(
        self,
        date: str,
        device_pair: str,
        co_occurrence_count: int,
        time_window_seconds: int,
        confidence: float,
        typical_hours: list[int],
    ) -> None:
        """Write co-occurrence daily aggregate."""
        point = Point("co_occurrence_daily") \
            .tag("date", date) \
            .tag("device_pair", device_pair) \
            .field("co_occurrence_count", co_occurrence_count) \
            .field("time_window_seconds", time_window_seconds) \
            .field("confidence", confidence) \
            .field("typical_hours", json.dumps(typical_hours)) \
            .time(datetime.fromisoformat(date), WritePrecision.NS)

        self.write_api.write(bucket=self.bucket_daily, record=point)
        logger.debug(f"Wrote co_occurrence_daily aggregate: {device_pair} on {date}")

    def write_sequence_daily(
        self,
        date: str,
        sequence_id: str,
        sequence: list[str],
        frequency: int,
        avg_duration_seconds: float,
        confidence: float,
    ) -> None:
        """Write sequence daily aggregate."""
        point = Point("sequence_daily") \
            .tag("date", date) \
            .tag("sequence_id", sequence_id) \
            .field("sequence", json.dumps(sequence)) \
            .field("frequency", frequency) \
            .field("avg_duration_seconds", avg_duration_seconds) \
            .field("confidence", confidence) \
            .time(datetime.fromisoformat(date), WritePrecision.NS)

        self.write_api.write(bucket=self.bucket_daily, record=point)
        logger.debug(f"Wrote sequence_daily aggregate: {sequence_id} on {date}")

    def write_room_based_daily(
        self,
        date: str,
        area_id: str,
        activity_level: float,
        device_usage: dict[str, Any],
        transition_patterns: list[dict[str, Any]],
        peak_activity_hours: list[int],
    ) -> None:
        """Write room-based daily aggregate."""
        point = Point("room_based_daily") \
            .tag("date", date) \
            .tag("area_id", area_id) \
            .field("activity_level", activity_level) \
            .field("device_usage", json.dumps(device_usage)) \
            .field("transition_patterns", json.dumps(transition_patterns)) \
            .field("peak_activity_hours", json.dumps(peak_activity_hours)) \
            .time(datetime.fromisoformat(date), WritePrecision.NS)

        self.write_api.write(bucket=self.bucket_daily, record=point)
        logger.debug(f"Wrote room_based_daily aggregate: {area_id} on {date}")

    def write_duration_daily(
        self,
        date: str,
        entity_id: str,
        avg_duration_seconds: float,
        min_duration_seconds: float,
        max_duration_seconds: float,
        duration_variance: float,
        efficiency_score: float,
    ) -> None:
        """Write duration daily aggregate."""
        point = Point("duration_daily") \
            .tag("date", date) \
            .tag("entity_id", entity_id) \
            .field("avg_duration_seconds", avg_duration_seconds) \
            .field("min_duration_seconds", min_duration_seconds) \
            .field("max_duration_seconds", max_duration_seconds) \
            .field("duration_variance", duration_variance) \
            .field("efficiency_score", efficiency_score) \
            .time(datetime.fromisoformat(date), WritePrecision.NS)

        self.write_api.write(bucket=self.bucket_daily, record=point)
        logger.debug(f"Wrote duration_daily aggregate: {entity_id} on {date}")

    def write_anomaly_daily(
        self,
        date: str,
        entity_id: str,
        anomaly_type: str,
        anomaly_score: float,
        baseline_deviation: float,
        occurrences: int,
        severity: str,
    ) -> None:
        """Write anomaly daily aggregate."""
        point = Point("anomaly_daily") \
            .tag("date", date) \
            .tag("entity_id", entity_id) \
            .tag("anomaly_type", anomaly_type) \
            .field("anomaly_score", anomaly_score) \
            .field("baseline_deviation", baseline_deviation) \
            .field("occurrences", occurrences) \
            .field("severity", severity) \
            .time(datetime.fromisoformat(date), WritePrecision.NS)

        self.write_api.write(bucket=self.bucket_daily, record=point)
        logger.debug(f"Wrote anomaly_daily aggregate: {entity_id} on {date}")

    # ==================== GROUP B DETECTORS - WEEKLY AGGREGATES ====================

    def write_session_weekly(
        self,
        week: str,
        session_type: str,
        avg_session_duration: float,
        session_count: int,
        typical_start_times: list[int],
        devices_used: list[str],
        confidence: float = 1.0,
    ) -> None:
        """
        Write session weekly aggregate to InfluxDB.

        Args:
            week: Week identifier (YYYY-WW format, e.g., '2025-W03')
            session_type: Type of session
            avg_session_duration: Average session duration in seconds
            session_count: Number of sessions
            typical_start_times: Typical session start times (hours)
            devices_used: List of devices used in sessions
            confidence: Pattern confidence score
        """
        point = Point("session_weekly") \
            .tag("week", week) \
            .tag("session_type", session_type) \
            .field("avg_session_duration", avg_session_duration) \
            .field("session_count", session_count) \
            .field("typical_start_times", json.dumps(typical_start_times)) \
            .field("devices_used", json.dumps(devices_used)) \
            .field("confidence", confidence) \
            .time(datetime.now(), WritePrecision.NS)

        self.write_api.write(bucket=self.bucket_weekly, record=point)
        logger.debug(f"Wrote session_weekly aggregate: {session_type} for {week}")

    def write_day_type_weekly(
        self,
        week: str,
        day_type: str,
        avg_events: float,
        typical_hours: list[int],
        device_usage: dict[str, Any],
        confidence: float = 1.0,
    ) -> None:
        """
        Write day-type weekly aggregate to InfluxDB.

        Args:
            week: Week identifier (YYYY-WW format)
            day_type: 'weekday' or 'weekend'
            avg_events: Average number of events
            typical_hours: Typical activity hours
            device_usage: Device usage statistics
            confidence: Pattern confidence score
        """
        point = Point("day_type_weekly") \
            .tag("week", week) \
            .tag("day_type", day_type) \
            .field("avg_events", avg_events) \
            .field("typical_hours", json.dumps(typical_hours)) \
            .field("device_usage", json.dumps(device_usage)) \
            .field("confidence", confidence) \
            .time(datetime.now(), WritePrecision.NS)

        self.write_api.write(bucket=self.bucket_weekly, record=point)
        logger.debug(f"Wrote day_type_weekly aggregate: {day_type} for {week}")

    # ==================== GROUP C DETECTORS - MONTHLY AGGREGATES ====================

    def write_contextual_monthly(
        self,
        month: str,
        weather_context: str,
        device_activity: dict[str, Any],
        correlation_score: float,
        occurrences: int,
        confidence: float = 1.0,
    ) -> None:
        """
        Write contextual monthly aggregate to InfluxDB.

        Args:
            month: Month identifier (YYYY-MM format, e.g., '2025-01')
            weather_context: Weather context classification
            device_activity: Device activity patterns
            correlation_score: Weather-device correlation score
            occurrences: Number of occurrences
            confidence: Pattern confidence score
        """
        point = Point("contextual_monthly") \
            .tag("month", month) \
            .tag("weather_context", weather_context) \
            .field("device_activity", json.dumps(device_activity)) \
            .field("correlation_score", correlation_score) \
            .field("occurrences", occurrences) \
            .field("confidence", confidence) \
            .time(datetime.now(), WritePrecision.NS)

        self.write_api.write(bucket=self.bucket_weekly, record=point)  # Store in weekly bucket
        logger.debug(f"Wrote contextual_monthly aggregate: {weather_context} for {month}")

    def write_seasonal_monthly(
        self,
        month: str,
        season: str,
        seasonal_patterns: dict[str, Any],
        trend_direction: str,
        confidence: float = 1.0,
    ) -> None:
        """
        Write seasonal monthly aggregate to InfluxDB.

        Args:
            month: Month identifier (YYYY-MM format)
            season: Season identifier
            seasonal_patterns: Seasonal activity patterns
            trend_direction: Trend direction ('increasing', 'decreasing', 'stable')
            confidence: Pattern confidence score
        """
        point = Point("seasonal_monthly") \
            .tag("month", month) \
            .tag("season", season) \
            .field("seasonal_patterns", json.dumps(seasonal_patterns)) \
            .field("trend_direction", trend_direction) \
            .field("confidence", confidence) \
            .time(datetime.now(), WritePrecision.NS)

        self.write_api.write(bucket=self.bucket_weekly, record=point)  # Store in weekly bucket
        logger.debug(f"Wrote seasonal_monthly aggregate: {season} for {month}")

    # ==================== QUERY METHODS ====================

    def query_daily_aggregates_by_date_range(
        self,
        measurement: str,
        start_date: str,
        end_date: str,
        **tags,
    ) -> list[dict[str, Any]]:
        """
        Query daily aggregates by date range.

        Args:
            measurement: Measurement name (e.g., 'time_based_daily')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            **tags: Additional tag filters (e.g., entity_id='light.living_room')

        Returns:
            List of records as dictionaries
        """
        flux_query = f"""
            from(bucket: "{self.bucket_daily}")
              |> range(start: {start_date}T00:00:00Z, stop: {end_date}T23:59:59Z)
              |> filter(fn: (r) => r["_measurement"] == "{measurement}")
        """

        # Add tag filters
        for tag_key, tag_value in tags.items():
            flux_query += f'\n  |> filter(fn: (r) => r["{tag_key}"] == "{tag_value}")'

        flux_query += """
              |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        """

        logger.debug(f"Querying {measurement} from {start_date} to {end_date}")
        tables = self.query_api.query(flux_query, org=self.org)

        results = []
        for table in tables:
            for record in table.records:
                results.append(dict(record.values))

        return results

    def query_daily_aggregates_by_entity(
        self,
        measurement: str,
        entity_id: str,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Query daily aggregates for a specific entity.

        Args:
            measurement: Measurement name
            entity_id: Entity identifier
            days: Number of days to query (default: 30)

        Returns:
            List of records
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        return self.query_daily_aggregates_by_date_range(
            measurement=measurement,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            entity_id=entity_id,
        )

    # ==================== BATCH OPERATIONS ====================

    def write_batch(self, points: list[Point], bucket: str | None = None) -> None:
        """
        Write multiple points in a single batch operation.

        Args:
            points: List of Point objects to write
            bucket: Bucket name (default: bucket_daily)
        """
        if bucket is None:
            bucket = self.bucket_daily

        self.write_api.write(bucket=bucket, record=points)
        logger.info(f"Wrote {len(points)} points to {bucket}")

    def close(self) -> None:
        """Close the InfluxDB client connection."""
        if self.client:
            self.client.close()
            logger.info("PatternAggregateClient closed")


# Convenience function to create client from settings
def create_pattern_aggregate_client(
    url: str,
    token: str,
    org: str,
    bucket_daily: str = "pattern_aggregates_daily",
    bucket_weekly: str = "pattern_aggregates_weekly",
) -> PatternAggregateClient:
    """
    Create a PatternAggregateClient instance.

    Args:
        url: InfluxDB URL
        token: InfluxDB token
        org: Organization name
        bucket_daily: Daily aggregates bucket name
        bucket_weekly: Weekly aggregates bucket name

    Returns:
        PatternAggregateClient instance
    """
    return PatternAggregateClient(
        url=url,
        token=token,
        org=org,
        bucket_daily=bucket_daily,
        bucket_weekly=bucket_weekly,
    )
