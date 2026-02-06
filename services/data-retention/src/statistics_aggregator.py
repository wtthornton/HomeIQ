"""
Statistics Aggregator (Epic 45.3, 45.4)

Aggregates raw events into short-term (5-minute) and long-term (hourly) statistics.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    InfluxDBClient = None
    Point = None
    SYNCHRONOUS = None

logger = logging.getLogger(__name__)


class StatisticsAggregator:
    """Aggregates raw events into statistics"""

    def __init__(self):
        """Initialize statistics aggregator"""
        self.influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        self.influxdb_token = os.getenv("INFLUXDB_TOKEN")
        self.influxdb_org = os.getenv("INFLUXDB_ORG", "homeiq")
        self.influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
        
        # SQLite metadata database (for statistics_meta table)
        self.sqlite_path = os.getenv("SQLITE_PATH", "data/metadata.db")
        
        self.client: InfluxDBClient | None = None
        self.query_api = None
        self.write_api = None
        
        # Statistics tracking
        self.last_short_term_run: datetime | None = None
        self.last_long_term_run: datetime | None = None
        self.short_term_aggregations = 0
        self.long_term_aggregations = 0
        self.errors = 0

    def _get_influxdb_client(self) -> InfluxDBClient:
        """Get or create InfluxDB client"""
        if not InfluxDBClient:
            raise ImportError("influxdb_client package not installed")
        
        if not self.client:
            self.client = InfluxDBClient(
                url=self.influxdb_url,
                token=self.influxdb_token,
                org=self.influxdb_org
            )
            self.query_api = self.client.query_api()
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        
        return self.client

    def _get_eligible_entities(self) -> list[dict[str, Any]]:
        """
        Get list of entities eligible for statistics aggregation from SQLite.

        Returns:
            List of dictionaries with statistic_id, state_class, has_mean, has_sum, unit_of_measurement
        """
        try:
            import sqlite3

            with sqlite3.connect(self.sqlite_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT statistic_id, state_class, has_mean, has_sum, unit_of_measurement
                    FROM statistics_meta
                """)
                return [
                    {
                        "statistic_id": row["statistic_id"],
                        "state_class": row["state_class"],
                        "has_mean": bool(row["has_mean"]),
                        "has_sum": bool(row["has_sum"]),
                        "unit_of_measurement": row["unit_of_measurement"]
                    }
                    for row in cursor
                ]
        except Exception as e:
            logger.error(f"Error fetching eligible entities from SQLite: {e}")
            return []

    async def aggregate_short_term(self) -> dict[str, Any]:
        """
        Aggregate raw events into 5-minute statistics (Epic 45.3).
        
        Returns:
            Dictionary with aggregation results
        """
        try:
            logger.info("Starting short-term statistics aggregation (5-minute)...")
            start_time = datetime.now(timezone.utc)
            
            # Get InfluxDB client
            self._get_influxdb_client()
            
            # Get eligible entities
            eligible_entities = self._get_eligible_entities()
            if not eligible_entities:
                logger.warning("No eligible entities found for statistics aggregation")
                return {"success": False, "error": "No eligible entities"}
            
            logger.info(f"Found {len(eligible_entities)} eligible entities for aggregation")
            
            # Calculate time range: last 5 minutes (or since last run)
            if self.last_short_term_run:
                range_start = self.last_short_term_run
            else:
                range_start = datetime.now(timezone.utc) - timedelta(minutes=5)
            
            range_end = datetime.now(timezone.utc)
            
            # Aggregate entities in batches to avoid N+1 query problem
            aggregated_points = []
            entities_processed = 0
            BATCH_SIZE = 50

            # Format time for Flux query
            start_flux = range_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            end_flux = range_end.strftime("%Y-%m-%dT%H:%M:%SZ")

            for batch_start in range(0, len(eligible_entities), BATCH_SIZE):
                batch = eligible_entities[batch_start:batch_start + BATCH_SIZE]
                entity_ids = [e["statistic_id"] for e in batch]
                entity_map = {e["statistic_id"]: e for e in batch}

                try:
                    # Build batched entity filter
                    entity_filter = " or ".join(
                        f'r.entity_id == "{eid}"' for eid in entity_ids
                    )

                    base_query = f'''
                    from(bucket: "{self.influxdb_bucket}")
                      |> range(start: time(v: "{start_flux}"), stop: time(v: "{end_flux}"))
                      |> filter(fn: (r) => r._measurement == "home_assistant_events")
                      |> filter(fn: (r) => {entity_filter})
                      |> filter(fn: (r) => r._field == "state_value")
                      |> filter(fn: (r) => exists r._value)
                      |> filter(fn: (r) => isNumeric(r._value))
                    '''

                    # Execute batched queries for mean, min, max
                    mean_query = base_query + '|> aggregateWindow(every: 5m, fn: mean, createEmpty: false)'
                    result = self.query_api.query(mean_query)

                    # Process mean results keyed by (entity_id, time)
                    mean_values: dict[tuple, dict] = {}
                    for table in result:
                        for record in table.records:
                            time_key = record.get_time()
                            value = record.get_value()
                            eid = record.values.get("entity_id", "")
                            if value is not None and isinstance(value, (int, float)):
                                mean_values[(eid, time_key)] = {"mean": float(value)}

                    # Query for min and max in batch
                    if mean_values:
                        min_query = base_query + '|> aggregateWindow(every: 5m, fn: min, createEmpty: false)'
                        max_query = base_query + '|> aggregateWindow(every: 5m, fn: max, createEmpty: false)'

                        min_result = self.query_api.query(min_query)
                        max_result = self.query_api.query(max_query)

                        for table in min_result:
                            for record in table.records:
                                time_key = record.get_time()
                                value = record.get_value()
                                eid = record.values.get("entity_id", "")
                                key = (eid, time_key)
                                if key in mean_values and value is not None and isinstance(value, (int, float)):
                                    mean_values[key]["min"] = float(value)

                        for table in max_result:
                            for record in table.records:
                                time_key = record.get_time()
                                value = record.get_value()
                                eid = record.values.get("entity_id", "")
                                key = (eid, time_key)
                                if key in mean_values and value is not None and isinstance(value, (int, float)):
                                    mean_values[key]["max"] = float(value)

                    # Create aggregated points
                    for (eid, time_key), values in mean_values.items():
                        entity = entity_map.get(eid, {})
                        point = Point("statistics_short_term") \
                            .tag("entity_id", eid) \
                            .tag("state_class", entity.get("state_class", "")) \
                            .field("mean", values["mean"]) \
                            .time(time_key)

                        if "min" in values:
                            point = point.field("min", values["min"])
                        if "max" in values:
                            point = point.field("max", values["max"])

                        aggregated_points.append(point)

                    entities_processed += len(batch)

                except Exception as e:
                    logger.error(f"Error aggregating entity batch: {e}")
                    self.errors += 1
                    continue
            
            # Write aggregated points to InfluxDB
            if aggregated_points:
                self.write_api.write(
                    bucket=self.influxdb_bucket,
                    org=self.influxdb_org,
                    record=aggregated_points
                )
                logger.info(f"Wrote {len(aggregated_points)} short-term statistics points for {entities_processed} entities")
            
            # Update tracking
            self.last_short_term_run = range_end
            self.short_term_aggregations += 1
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                "success": True,
                "entities_processed": entities_processed,
                "points_written": len(aggregated_points),
                "duration_seconds": duration
            }
            
        except Exception as e:
            logger.error(f"Error in short-term aggregation: {e}")
            self.errors += 1
            return {"success": False, "error": str(e)}

    async def aggregate_long_term(self) -> dict[str, Any]:
        """
        Aggregate short-term statistics into hourly statistics (Epic 45.4).
        
        Returns:
            Dictionary with aggregation results
        """
        try:
            logger.info("Starting long-term statistics aggregation (hourly)...")
            start_time = datetime.now(timezone.utc)
            
            # Get InfluxDB client
            self._get_influxdb_client()
            
            # Get eligible entities
            eligible_entities = self._get_eligible_entities()
            if not eligible_entities:
                logger.warning("No eligible entities found for statistics aggregation")
                return {"success": False, "error": "No eligible entities"}
            
            # Calculate time range: last hour (or since last run)
            if self.last_long_term_run:
                range_start = self.last_long_term_run
            else:
                range_start = datetime.now(timezone.utc) - timedelta(hours=1)
            
            range_end = datetime.now(timezone.utc)
            
            # Aggregate entities from short-term statistics in batches
            aggregated_points = []
            entities_processed = 0
            BATCH_SIZE = 50

            # Format time for Flux query
            start_flux = range_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            end_flux = range_end.strftime("%Y-%m-%dT%H:%M:%SZ")

            for batch_start in range(0, len(eligible_entities), BATCH_SIZE):
                batch = eligible_entities[batch_start:batch_start + BATCH_SIZE]
                entity_ids = [e["statistic_id"] for e in batch]
                entity_map = {e["statistic_id"]: e for e in batch}

                try:
                    # Build batched entity filter
                    entity_filter = " or ".join(
                        f'r.entity_id == "{eid}"' for eid in entity_ids
                    )

                    # Query short-term statistics and aggregate to hourly
                    flux_query = f'''
                    from(bucket: "{self.influxdb_bucket}")
                      |> range(start: time(v: "{start_flux}"), stop: time(v: "{end_flux}"))
                      |> filter(fn: (r) => r._measurement == "statistics_short_term")
                      |> filter(fn: (r) => {entity_filter})
                      |> filter(fn: (r) => r._field == "mean")
                      |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
                    '''

                    # Execute query
                    result = self.query_api.query(flux_query)

                    # Process results and create aggregated points
                    for table in result:
                        for record in table.records:
                            record_time = record.get_time()
                            value = record.get_value()
                            eid = record.values.get("entity_id", "")

                            if value is None or not isinstance(value, (int, float)):
                                continue

                            entity = entity_map.get(eid, {})
                            # Create aggregated point
                            point = Point("statistics") \
                                .tag("entity_id", eid) \
                                .tag("state_class", entity.get("state_class", "")) \
                                .field("mean", float(value)) \
                                .time(record_time)

                            aggregated_points.append(point)

                    entities_processed += len(batch)

                except Exception as e:
                    logger.error(f"Error aggregating entity batch: {e}")
                    self.errors += 1
                    continue
            
            # Write aggregated points to InfluxDB
            if aggregated_points:
                self.write_api.write(
                    bucket=self.influxdb_bucket,
                    org=self.influxdb_org,
                    record=aggregated_points
                )
                logger.info(f"Wrote {len(aggregated_points)} long-term statistics points for {entities_processed} entities")
            
            # Update tracking
            self.last_long_term_run = range_end
            self.long_term_aggregations += 1
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                "success": True,
                "entities_processed": entities_processed,
                "points_written": len(aggregated_points),
                "duration_seconds": duration
            }
            
        except Exception as e:
            logger.error(f"Error in long-term aggregation: {e}")
            self.errors += 1
            return {"success": False, "error": str(e)}

    def get_statistics(self) -> dict[str, Any]:
        """Get aggregation statistics"""
        return {
            "short_term_aggregations": self.short_term_aggregations,
            "long_term_aggregations": self.long_term_aggregations,
            "errors": self.errors,
            "last_short_term_run": self.last_short_term_run.isoformat() if self.last_short_term_run else None,
            "last_long_term_run": self.last_long_term_run.isoformat() if self.last_long_term_run else None
        }

