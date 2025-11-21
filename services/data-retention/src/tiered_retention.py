"""
Tiered Data Retention Manager
Implements hot/warm/cold/archive storage tiers
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from influxdb_client_3 import InfluxDBClient3, Point

logger = logging.getLogger(__name__)


class TieredRetentionManager:
    """Manage tiered data retention with automatic downsampling"""

    def __init__(self):
        self.influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        self.influxdb_token = os.getenv("INFLUXDB_TOKEN")
        self.influxdb_org = os.getenv("INFLUXDB_ORG", "home_assistant")
        self.influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "events")

        self.client: InfluxDBClient3 = None

        # Storage tiers configuration
        self.tiers = {
            "hot": {"retention_days": 7, "resolution": "full"},
            "warm": {"retention_days": 90, "resolution": "hourly"},
            "cold": {"retention_days": 365, "resolution": "daily"},
            "archive": {"retention_days": 1825, "resolution": "monthly"},
        }

    def initialize(self):
        """Initialize InfluxDB client"""
        self.client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org,
        )

    async def downsample_hot_to_warm(self) -> dict[str, Any]:
        """Downsample raw data (7+ days old) to hourly aggregates"""

        logger.info("Starting hot to warm downsampling (raw → hourly)...")

        cutoff_date = datetime.now() - timedelta(days=7)

        try:
            # Create hourly aggregates
            query = f"""
            SELECT
                DATE_TRUNC('hour', time) as hour,
                entity_id,
                domain,
                AVG(normalized_value) as avg_value,
                MIN(normalized_value) as min_value,
                MAX(normalized_value) as max_value,
                COUNT(*) as sample_count,
                SUM(energy_consumption) as total_energy
            FROM home_assistant_events
            WHERE time < TIMESTAMP '{cutoff_date.isoformat()}'
            GROUP BY DATE_TRUNC('hour', time), entity_id, domain
            """

            result = self.client.query(query, language="sql", mode="pandas")

            if not result.empty:
                # Write hourly aggregates
                for _, row in result.iterrows():
                    point = Point("hourly_aggregates") \
                        .tag("entity_id", row["entity_id"]) \
                        .tag("domain", row["domain"]) \
                        .field("avg_value", float(row["avg_value"])) \
                        .field("min_value", float(row["min_value"])) \
                        .field("max_value", float(row["max_value"])) \
                        .field("sample_count", int(row["sample_count"])) \
                        .field("total_energy", float(row.get("total_energy", 0))) \
                        .time(row["hour"])

                    self.client.write(point)

                records_downsampled = len(result)

                # Note: In production, delete raw data here after verification
                # For safety, we'll leave deletion as manual step initially

                logger.info(f"Downsampled {records_downsampled} hourly records")

                return {
                    "status": "success",
                    "records_downsampled": records_downsampled,
                    "cutoff_date": cutoff_date.isoformat(),
                    "timestamp": datetime.now(),
                }
            logger.info("No data to downsample")
            return {"status": "no_data"}

        except Exception as e:
            logger.exception(f"Error in hot to warm downsampling: {e}")
            return {"status": "error", "error": str(e)}

    async def downsample_warm_to_cold(self) -> dict[str, Any]:
        """Downsample hourly data (90+ days old) to daily aggregates"""

        logger.info("Starting warm to cold downsampling (hourly → daily)...")

        cutoff_date = datetime.now() - timedelta(days=90)

        try:
            query = f"""
            SELECT
                DATE_TRUNC('day', hour) as day,
                entity_id,
                domain,
                AVG(avg_value) as avg_value,
                MIN(min_value) as min_value,
                MAX(max_value) as max_value,
                SUM(sample_count) as total_samples,
                SUM(total_energy) as daily_energy
            FROM hourly_aggregates
            WHERE hour < TIMESTAMP '{cutoff_date.isoformat()}'
            GROUP BY DATE_TRUNC('day', hour), entity_id, domain
            """

            result = self.client.query(query, language="sql", mode="pandas")

            if not result.empty:
                # Write daily aggregates
                for _, row in result.iterrows():
                    point = Point("daily_aggregates") \
                        .tag("entity_id", row["entity_id"]) \
                        .tag("domain", row["domain"]) \
                        .field("avg_value", float(row["avg_value"])) \
                        .field("min_value", float(row["min_value"])) \
                        .field("max_value", float(row["max_value"])) \
                        .field("total_samples", int(row["total_samples"])) \
                        .field("daily_energy", float(row.get("daily_energy", 0))) \
                        .time(row["day"])

                    self.client.write(point)

                records_downsampled = len(result)

                logger.info(f"Downsampled {records_downsampled} daily records")

                return {
                    "status": "success",
                    "records_downsampled": records_downsampled,
                    "cutoff_date": cutoff_date.isoformat(),
                    "timestamp": datetime.now(),
                }
            logger.info("No data to downsample")
            return {"status": "no_data"}

        except Exception as e:
            logger.exception(f"Error in warm to cold downsampling: {e}")
            return {"status": "error", "error": str(e)}

    async def run_maintenance_cycle(self) -> dict[str, Any]:
        """Run complete maintenance cycle"""

        logger.info("Starting tiered retention maintenance cycle...")

        start_time = datetime.now()
        results = {}

        # Hot to Warm
        results["hot_to_warm"] = await self.downsample_hot_to_warm()

        # Warm to Cold
        results["warm_to_cold"] = await self.downsample_warm_to_cold()

        duration = (datetime.now() - start_time).total_seconds()

        logger.info(f"Maintenance cycle completed in {duration:.2f}s")

        return {
            "status": "success",
            "duration_seconds": duration,
            "results": results,
            "timestamp": datetime.now(),
        }

