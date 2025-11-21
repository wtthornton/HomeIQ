"""
InfluxDB Client for Admin API Statistics Queries
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any

try:
    from influxdb_client import InfluxDBClient
    from influxdb_client.client.query_api import QueryApi
except ImportError:
    # Graceful fallback if influxdb_client not installed
    InfluxDBClient = None
    QueryApi = None

logger = logging.getLogger(__name__)


class AdminAPIInfluxDBClient:
    """InfluxDB client for Admin API statistics queries"""

    def __init__(self):
        """Initialize InfluxDB client configuration"""
        self.url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        self.token = os.getenv("INFLUXDB_TOKEN")
        self.org = os.getenv("INFLUXDB_ORG", "homeiq")
        self.bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")

        self.client: InfluxDBClient | None = None
        self.query_api: QueryApi | None = None

        # Performance tracking
        self.query_count = 0
        self.error_count = 0
        self.avg_query_time_ms = 0.0
        self.is_connected = False

    async def connect(self) -> bool:
        """
        Connect to InfluxDB

        Returns:
            True if connection successful, False otherwise
        """
        if InfluxDBClient is None:
            logger.error("influxdb_client package not installed")
            return False

        try:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org,
                timeout=30000,  # 30 seconds
            )

            # Test connection
            await self._test_connection()

            self.query_api = self.client.query_api()
            self.is_connected = True

            logger.info(f"Admin API connected to InfluxDB at {self.url}")
            return True

        except Exception as e:
            logger.exception(f"Failed to connect to InfluxDB: {e}")
            self.is_connected = False
            return False

    async def _test_connection(self):
        """Test InfluxDB connection using health check endpoint"""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session, session.get(
                f"{self.url}/health",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    msg = f"InfluxDB health check failed: {response.status}"
                    raise Exception(msg)
                logger.debug("InfluxDB health check passed")
        except Exception as e:
            logger.exception(f"InfluxDB connection test failed: {e}")
            raise

    async def get_event_statistics(self, period: str = "1h") -> dict[str, Any]:
        """
        Get event processing statistics from InfluxDB

        Args:
            period: Time period (1h, 6h, 24h, 7d)

        Returns:
            Dictionary with event statistics
        """
        if not self.is_connected or not self.query_api:
            msg = "InfluxDB client not connected"
            raise Exception(msg)

        query = f"""
from(bucket: "{self.bucket}")
    |> range(start: -{period})
    |> filter(fn: (r) => r._measurement == "home_assistant_events")
    |> count()
    |> group()
    |> sum()
"""

        result = await self._execute_query(query)

        # Calculate events per minute
        time_seconds = self._period_to_seconds(period)
        total_events = sum(r.get("_value", 0) for r in result)
        events_per_minute = (total_events / time_seconds) * 60 if time_seconds > 0 else 0

        return {
            "total_events": total_events,
            "events_per_minute": round(events_per_minute, 2),
            "period": period,
        }

    async def get_error_rate(self, period: str = "1h") -> dict[str, Any]:
        """
        Calculate error rate from InfluxDB metrics

        Args:
            period: Time period

        Returns:
            Dictionary with error statistics
        """
        if not self.is_connected or not self.query_api:
            msg = "InfluxDB client not connected"
            raise Exception(msg)

        # Query for total writes
        total_query = f"""
from(bucket: "{self.bucket}")
    |> range(start: -{period})
    |> filter(fn: (r) => r._measurement == "service_metrics")
    |> filter(fn: (r) => r._field == "write_attempts" or r._field == "events_processed")
    |> sum()
"""

        # Query for errors
        error_query = f"""
from(bucket: "{self.bucket}")
    |> range(start: -{period})
    |> filter(fn: (r) => r._measurement == "service_metrics")
    |> filter(fn: (r) => r._field == "write_errors" or r._field == "error")
    |> sum()
"""

        total_result = await self._execute_query(total_query)
        error_result = await self._execute_query(error_query)

        total = sum(r.get("_value", 0) for r in total_result)
        errors = sum(r.get("_value", 0) for r in error_result)

        error_rate = (errors / total * 100) if total > 0 else 0

        return {
            "total_writes": total,
            "write_errors": errors,
            "error_rate_percent": round(error_rate, 2),
            "period": period,
        }

    async def get_service_metrics(self, service_name: str, period: str = "1h") -> dict[str, Any]:
        """
        Get metrics for a specific service from InfluxDB

        Args:
            service_name: Name of the service
            period: Time period

        Returns:
            Service metrics dictionary
        """
        if not self.is_connected or not self.query_api:
            msg = "InfluxDB client not connected"
            raise Exception(msg)

        query = f"""
from(bucket: "{self.bucket}")
    |> range(start: -{period})
    |> filter(fn: (r) => r._measurement == "service_metrics")
    |> filter(fn: (r) => r.service == "{service_name}")
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> last()
"""

        result = await self._execute_query(query)

        if not result:
            return {"error": f"No data found for service {service_name}"}

        metrics = result[0]

        return {
            "service": service_name,
            "events_processed": metrics.get("events_processed", 0),
            "processing_time_ms": metrics.get("processing_time_ms", 0),
            "success_rate": metrics.get("success_rate", 100),
            "last_update": metrics.get("_time"),
            "period": period,
        }

    async def get_all_service_statistics(self, period: str = "1h") -> dict[str, Any]:
        """
        Get aggregated statistics across all services

        Args:
            period: Time period

        Returns:
            Dictionary with aggregated metrics
        """
        if not self.is_connected or not self.query_api:
            msg = "InfluxDB client not connected"
            raise Exception(msg)

        # Query for all service metrics
        query = f"""
from(bucket: "{self.bucket}")
    |> range(start: -{period})
    |> filter(fn: (r) => r._measurement == "service_metrics")
    |> group(columns: ["service"])
    |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
"""

        result = await self._execute_query(query)

        # Group by service
        services = {}
        for record in result:
            service = record.get("service", "unknown")
            if service not in services:
                services[service] = {
                    "events_processed": 0,
                    "avg_processing_time": 0,
                    "success_rate": 100,
                }

            field = record.get("_field")
            value = record.get("_value", 0)

            if field == "events_processed":
                services[service]["events_processed"] += value
            elif field == "processing_time_ms":
                services[service]["avg_processing_time"] = value
            elif field == "success_rate":
                services[service]["success_rate"] = value

        return {
            "services": services,
            "period": period,
            "timestamp": datetime.now().isoformat(),
        }

    async def get_event_trends(self, period: str = "24h", window: str = "1h") -> dict[str, Any]:
        """
        Get event processing trends over time

        Args:
            period: Overall time period
            window: Aggregation window (1m, 5m, 1h)

        Returns:
            Time-series trend data
        """
        if not self.is_connected or not self.query_api:
            msg = "InfluxDB client not connected"
            raise Exception(msg)

        query = f"""
from(bucket: "{self.bucket}")
    |> range(start: -{period})
    |> filter(fn: (r) => r._measurement == "home_assistant_events")
    |> aggregateWindow(every: {window}, fn: count, createEmpty: false)
"""

        result = await self._execute_query(query)

        trends = []
        for record in result:
            time_value = record.get("_time")
            time_str = time_value.isoformat() if hasattr(time_value, "isoformat") else str(time_value)

            trends.append({
                "time": time_str,
                "count": record.get("_value", 0),
            })

        return {
            "trends": trends,
            "period": period,
            "window": window,
        }

    async def _execute_query(self, query: str) -> list[dict[str, Any]]:
        """
        Execute InfluxDB query and return results

        Args:
            query: Flux query string

        Returns:
            List of result dictionaries
        """
        if not self.query_api:
            msg = "InfluxDB client not connected"
            raise Exception(msg)

        try:
            start_time = datetime.now()

            # Execute query in thread pool (InfluxDB client is synchronous)
            result = await asyncio.to_thread(
                self.query_api.query,
                query=query,
                org=self.org,
            )

            # Track performance
            query_time = (datetime.now() - start_time).total_seconds() * 1000
            self.query_count += 1

            # Update average query time
            if self.query_count == 1:
                self.avg_query_time_ms = query_time
            else:
                self.avg_query_time_ms = (
                    (self.avg_query_time_ms * (self.query_count - 1) + query_time)
                    / self.query_count
                )

            # Convert to list of dictionaries
            data = []
            for table in result:
                for record in table.records:
                    data.append(record.values)

            logger.debug(f"Query returned {len(data)} records in {query_time:.2f}ms")
            return data

        except Exception as e:
            self.error_count += 1
            logger.exception(f"Error executing query: {e}")
            raise

    def _period_to_seconds(self, period: str) -> int:
        """
        Convert period string to seconds

        Args:
            period: Period string (e.g., "1h", "24h", "7d")

        Returns:
            Number of seconds
        """
        conversions = {
            "15m": 15 * 60,
            "1h": 60 * 60,
            "6h": 6 * 60 * 60,
            "24h": 24 * 60 * 60,
            "7d": 7 * 24 * 60 * 60,
        }
        return conversions.get(period, 3600)  # Default to 1 hour

    def get_connection_status(self) -> dict[str, Any]:
        """
        Get connection status and statistics

        Returns:
            Dictionary with connection info and stats
        """
        return {
            "is_connected": self.is_connected,
            "url": self.url,
            "org": self.org,
            "bucket": self.bucket,
            "query_count": self.query_count,
            "error_count": self.error_count,
            "avg_query_time_ms": round(self.avg_query_time_ms, 2),
            "success_rate": (
                ((self.query_count - self.error_count) / self.query_count * 100)
                if self.query_count > 0 else 100
            ),
        }

    async def close(self):
        """Close InfluxDB connection"""
        try:
            if self.client:
                self.client.close()
                logger.info("InfluxDB connection closed")
        except Exception as e:
            logger.exception(f"Error closing InfluxDB connection: {e}")
        finally:
            self.client = None
            self.query_api = None
            self.is_connected = False

