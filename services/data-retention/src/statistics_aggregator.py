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
            
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT statistic_id, state_class, has_mean, has_sum, unit_of_measurement
                FROM statistics_meta
            """)
            
            entities = []
            for row in cursor.fetchall():
                entities.append({
                    "statistic_id": row[0],  # entity_id
                    "state_class": row[1],
                    "has_mean": bool(row[2]),
                    "has_sum": bool(row[3]),
                    "unit_of_measurement": row[4]
                })
            
            conn.close()
            return entities
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
            
            # Aggregate each entity
            aggregated_points = []
            entities_processed = 0
            
            for entity in eligible_entities:
                entity_id = entity["statistic_id"]
                has_mean = entity["has_mean"]
                has_sum = entity["has_sum"]
                
                try:
                    # Format time for Flux query
                    start_flux = range_start.strftime("%Y-%m-%dT%H:%M:%SZ")
                    end_flux = range_end.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    # Query raw events for this entity in the time range
                    # Aggregate with mean, min, max (where applicable)
                    base_query = f'''
                    from(bucket: "{self.influxdb_bucket}")
                      |> range(start: time(v: "{start_flux}"), stop: time(v: "{end_flux}"))
                      |> filter(fn: (r) => r._measurement == "home_assistant_events")
                      |> filter(fn: (r) => r.entity_id == "{entity_id}")
                      |> filter(fn: (r) => r._field == "state_value")
                      |> filter(fn: (r) => exists r._value)
                      |> filter(fn: (r) => isNumeric(r._value))
                    '''
                    
                    # Execute query for mean
                    mean_query = base_query + '|> aggregateWindow(every: 5m, fn: mean, createEmpty: false)'
                    result = self.query_api.query(mean_query)
                    
                    # Process mean results
                    mean_values = {}
                    for table in result:
                        for record in table.records:
                            time_key = record.get_time()
                            value = record.get_value()
                            if value is not None and isinstance(value, (int, float)):
                                mean_values[time_key] = {"mean": float(value)}
                    
                    # Query for min and max if has_mean
                    if has_mean and mean_values:
                        min_query = base_query + '|> aggregateWindow(every: 5m, fn: min, createEmpty: false)'
                        max_query = base_query + '|> aggregateWindow(every: 5m, fn: max, createEmpty: false)'
                        
                        min_result = self.query_api.query(min_query)
                        max_result = self.query_api.query(max_query)
                        
                        for table in min_result:
                            for record in table.records:
                                time_key = record.get_time()
                                value = record.get_value()
                                if time_key in mean_values and value is not None and isinstance(value, (int, float)):
                                    mean_values[time_key]["min"] = float(value)
                        
                        for table in max_result:
                            for record in table.records:
                                time_key = record.get_time()
                                value = record.get_value()
                                if time_key in mean_values and value is not None and isinstance(value, (int, float)):
                                    mean_values[time_key]["max"] = float(value)
                    
                    # Create aggregated points
                    for time_key, values in mean_values.items():
                        point = Point("statistics_short_term") \
                            .tag("entity_id", entity_id) \
                            .tag("state_class", entity.get("state_class", "")) \
                            .field("mean", values["mean"]) \
                            .time(time_key)
                        
                        if "min" in values:
                            point = point.field("min", values["min"])
                        if "max" in values:
                            point = point.field("max", values["max"])
                        
                        aggregated_points.append(point)
                    
                    entities_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error aggregating entity {entity_id}: {e}")
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
            
            # Aggregate each entity from short-term statistics
            aggregated_points = []
            entities_processed = 0
            
            for entity in eligible_entities:
                entity_id = entity["statistic_id"]
                has_mean = entity["has_mean"]
                has_sum = entity["has_sum"]
                
                try:
                    # Format time for Flux query
                    start_flux = range_start.strftime("%Y-%m-%dT%H:%M:%SZ")
                    end_flux = range_end.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    # Query short-term statistics and aggregate to hourly
                    flux_query = f'''
                    from(bucket: "{self.influxdb_bucket}")
                      |> range(start: time(v: "{start_flux}"), stop: time(v: "{end_flux}"))
                      |> filter(fn: (r) => r._measurement == "statistics_short_term")
                      |> filter(fn: (r) => r.entity_id == "{entity_id}")
                      |> filter(fn: (r) => r._field == "mean")
                      |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
                    '''
                    
                    # Execute query
                    result = self.query_api.query(flux_query)
                    
                    # Process results and create aggregated points
                    for table in result:
                        for record in table.records:
                            time = record.get_time()
                            value = record.get_value()
                            
                            if value is None or not isinstance(value, (int, float)):
                                continue
                            
                            # Create aggregated point
                            point = Point("statistics") \
                                .tag("entity_id", entity_id) \
                                .tag("state_class", entity.get("state_class", "")) \
                                .field("mean", float(value)) \
                                .time(time)
                            
                            aggregated_points.append(point)
                    
                    entities_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error aggregating entity {entity_id}: {e}")
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

