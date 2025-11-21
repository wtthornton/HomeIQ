"""
Metrics API for accessing performance metrics data
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi


@dataclass
class MetricsQuery:
    """Metrics query parameters"""
    measurement: str
    service: str | None = None
    operation: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int | None = None
    tags: dict[str, str] | None = None


@dataclass
class MetricsResponse:
    """Metrics query response"""
    measurement: str
    data: list[dict[str, Any]]
    total_count: int
    query_time_ms: float
    timestamp: datetime


class MetricsAPI:
    """API for querying metrics data from InfluxDB"""

    def __init__(self, influxdb_client: InfluxDBClient, bucket: str = "homeiq-metrics"):
        self.influxdb_client = influxdb_client
        self.bucket = bucket
        self.query_api: QueryApi = influxdb_client.query_api()

    async def query_metrics(self, query: MetricsQuery) -> MetricsResponse:
        """Query metrics data from InfluxDB"""
        start_time = time.time()

        # Build Flux query
        flux_query = self._build_flux_query(query)

        try:
            # Execute query
            tables = self.query_api.query(flux_query)

            # Process results
            data = []
            for table in tables:
                for record in table.records:
                    data.append({
                        "timestamp": record.get_time().isoformat(),
                        "measurement": record.get_measurement(),
                        "fields": record.values,
                        "tags": {k: v for k, v in record.values.items() if k.startswith("_")},
                    })

            query_time_ms = (time.time() - start_time) * 1000

            return MetricsResponse(
                measurement=query.measurement,
                data=data,
                total_count=len(data),
                query_time_ms=query_time_ms,
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            msg = f"Error querying metrics: {e!s}"
            raise Exception(msg)

    def _build_flux_query(self, query: MetricsQuery) -> str:
        """Build Flux query string"""
        # Base query
        flux_query = f"""
        from(bucket: "{self.bucket}")
        |> range(start: {self._format_time(query.start_time or datetime.utcnow() - timedelta(hours=1))})
        |> filter(fn: (r) => r._measurement == "{query.measurement}")
        """

        # Add service filter
        if query.service:
            flux_query += f'|> filter(fn: (r) => r.service == "{query.service}")'

        # Add operation filter
        if query.operation:
            flux_query += f'|> filter(fn: (r) => r.operation == "{query.operation}")'

        # Add tag filters
        if query.tags:
            for key, value in query.tags.items():
                flux_query += f'|> filter(fn: (r) => r.{key} == "{value}")'

        # Add time range filter
        if query.end_time:
            flux_query += f"|> range(start: {self._format_time(query.start_time or datetime.utcnow() - timedelta(hours=1))}, stop: {self._format_time(query.end_time)})"

        # Add limit
        if query.limit:
            flux_query += f"|> limit(n: {query.limit})"

        # Sort by time
        flux_query += '|> sort(columns: ["_time"])'

        return flux_query

    def _format_time(self, dt: datetime) -> str:
        """Format datetime for Flux query"""
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    async def get_service_performance_metrics(self, service: str, hours: int = 24) -> dict[str, Any]:
        """Get performance metrics for a specific service"""
        query = MetricsQuery(
            measurement="performance",
            service=service,
            start_time=datetime.utcnow() - timedelta(hours=hours),
        )

        response = await self.query_metrics(query)

        # Process and aggregate data
        operations = {}
        for record in response.data:
            operation = record["fields"].get("operation", "unknown")
            if operation not in operations:
                operations[operation] = {
                    "count": 0,
                    "total_duration": 0,
                    "avg_duration": 0,
                    "min_duration": float("inf"),
                    "max_duration": 0,
                    "success_count": 0,
                    "error_count": 0,
                }

            op_data = operations[operation]
            op_data["count"] += 1

            duration = record["fields"].get("duration_ms", 0)
            op_data["total_duration"] += duration
            op_data["avg_duration"] = op_data["total_duration"] / op_data["count"]
            op_data["min_duration"] = min(op_data["min_duration"], duration)
            op_data["max_duration"] = max(op_data["max_duration"], duration)

            status = record["fields"].get("status", "unknown")
            if status == "success":
                op_data["success_count"] += 1
            else:
                op_data["error_count"] += 1

        return {
            "service": service,
            "time_range_hours": hours,
            "operations": operations,
            "total_operations": sum(op["count"] for op in operations.values()),
            "query_time_ms": response.query_time_ms,
        }

    async def get_system_metrics(self, hours: int = 1) -> dict[str, Any]:
        """Get system resource metrics"""
        query = MetricsQuery(
            measurement="system_resources",
            start_time=datetime.utcnow() - timedelta(hours=hours),
        )

        response = await self.query_metrics(query)

        # Process system metrics
        metrics = {
            "cpu": [],
            "memory": [],
            "disk": [],
            "network": [],
        }

        for record in response.data:
            timestamp = record["timestamp"]
            fields = record["fields"]

            metrics["cpu"].append({
                "timestamp": timestamp,
                "percent": fields.get("cpu_percent", 0),
            })

            metrics["memory"].append({
                "timestamp": timestamp,
                "percent": fields.get("memory_percent", 0),
                "used_bytes": fields.get("memory_used_bytes", 0),
                "total_bytes": fields.get("memory_total_bytes", 0),
            })

            metrics["disk"].append({
                "timestamp": timestamp,
                "percent": fields.get("disk_percent", 0),
                "used_bytes": fields.get("disk_used_bytes", 0),
                "total_bytes": fields.get("disk_total_bytes", 0),
            })

            metrics["network"].append({
                "timestamp": timestamp,
                "bytes_sent": fields.get("network_bytes_sent", 0),
                "bytes_recv": fields.get("network_bytes_recv", 0),
            })

        return {
            "time_range_hours": hours,
            "metrics": metrics,
            "total_records": response.total_count,
            "query_time_ms": response.query_time_ms,
        }

    async def get_metrics_summary(self) -> dict[str, Any]:
        """Get overall metrics summary"""
        # Get performance metrics summary
        perf_query = MetricsQuery(
            measurement="performance",
            start_time=datetime.utcnow() - timedelta(hours=24),
        )
        perf_response = await self.query_metrics(perf_query)

        # Get system metrics summary
        sys_query = MetricsQuery(
            measurement="system_resources",
            start_time=datetime.utcnow() - timedelta(hours=1),
        )
        sys_response = await self.query_metrics(sys_query)

        # Get counter metrics summary
        counter_query = MetricsQuery(
            measurement="counters",
            start_time=datetime.utcnow() - timedelta(hours=24),
        )
        counter_response = await self.query_metrics(counter_query)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "performance_metrics": {
                "total_operations": perf_response.total_count,
                "query_time_ms": perf_response.query_time_ms,
            },
            "system_metrics": {
                "total_records": sys_response.total_count,
                "query_time_ms": sys_response.query_time_ms,
            },
            "counter_metrics": {
                "total_records": counter_response.total_count,
                "query_time_ms": counter_response.query_time_ms,
            },
        }


class MetricsHealthChecker:
    """Health checker for metrics collection system"""

    def __init__(self, metrics_api: MetricsAPI):
        self.metrics_api = metrics_api

    async def check_health(self) -> dict[str, Any]:
        """Check metrics system health"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
        }

        try:
            # Check if we can query recent metrics
            recent_query = MetricsQuery(
                measurement="performance",
                start_time=datetime.utcnow() - timedelta(minutes=5),
            )

            response = await self.metrics_api.query_metrics(recent_query)

            health_status["checks"]["recent_metrics"] = {
                "status": "healthy",
                "records_found": response.total_count,
                "query_time_ms": response.query_time_ms,
            }

            # Check system metrics
            sys_query = MetricsQuery(
                measurement="system_resources",
                start_time=datetime.utcnow() - timedelta(minutes=5),
            )

            sys_response = await self.metrics_api.query_metrics(sys_query)

            health_status["checks"]["system_metrics"] = {
                "status": "healthy",
                "records_found": sys_response.total_count,
                "query_time_ms": sys_response.query_time_ms,
            }

        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            health_status["checks"]["recent_metrics"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        return health_status


# Utility functions for common metrics queries
async def get_service_health_metrics(metrics_api: MetricsAPI, service: str) -> dict[str, Any]:
    """Get health metrics for a specific service"""
    try:
        # Get recent performance metrics
        perf_metrics = await metrics_api.get_service_performance_metrics(service, hours=1)

        # Calculate health score
        total_ops = perf_metrics["total_operations"]
        if total_ops > 0:
            success_rate = sum(
                op["success_count"] / op["count"] * op["count"]
                for op in perf_metrics["operations"].values()
            ) / total_ops
        else:
            success_rate = 1.0

        # Calculate average response time
        avg_response_time = sum(
            op["avg_duration"] * op["count"]
            for op in perf_metrics["operations"].values()
        ) / total_ops if total_ops > 0 else 0

        return {
            "service": service,
            "health_score": success_rate,
            "success_rate": success_rate,
            "avg_response_time_ms": avg_response_time,
            "total_operations": total_ops,
            "operations": perf_metrics["operations"],
        }

    except Exception as e:
        return {
            "service": service,
            "health_score": 0,
            "error": str(e),
        }


async def get_system_health_metrics(metrics_api: MetricsAPI) -> dict[str, Any]:
    """Get system health metrics"""
    try:
        system_metrics = await metrics_api.get_system_metrics(hours=1)

        # Calculate average resource usage
        cpu_data = system_metrics["metrics"]["cpu"]
        memory_data = system_metrics["metrics"]["memory"]
        disk_data = system_metrics["metrics"]["disk"]

        avg_cpu = sum(point["percent"] for point in cpu_data) / len(cpu_data) if cpu_data else 0
        avg_memory = sum(point["percent"] for point in memory_data) / len(memory_data) if memory_data else 0
        avg_disk = sum(point["percent"] for point in disk_data) / len(disk_data) if disk_data else 0

        # Calculate health score (lower resource usage = higher health)
        health_score = max(0, 1 - (avg_cpu + avg_memory + avg_disk) / 300)  # Normalize to 0-1

        return {
            "health_score": health_score,
            "avg_cpu_percent": avg_cpu,
            "avg_memory_percent": avg_memory,
            "avg_disk_percent": avg_disk,
            "metrics_count": system_metrics["total_records"],
        }

    except Exception as e:
        return {
            "health_score": 0,
            "error": str(e),
        }
