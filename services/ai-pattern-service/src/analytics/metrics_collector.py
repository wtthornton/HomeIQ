"""
Metrics Collector

Collects and aggregates metrics from various sources for analytics.
Integrates with InfluxDB for time-series storage.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class InfluxDBClient(Protocol):
    """Protocol for InfluxDB client interface."""
    
    async def write_point(
        self,
        measurement: str,
        tags: dict[str, str],
        fields: dict[str, Any],
        timestamp: datetime | None = None,
    ) -> None:
        """Write a single point to InfluxDB."""
        ...
    
    async def query(self, query: str) -> list[dict[str, Any]]:
        """Execute a query and return results."""
        ...


@dataclass
class MetricPoint:
    """Represents a single metric data point."""
    
    measurement: str
    tags: dict[str, str]
    fields: dict[str, Any]
    timestamp: datetime


class MetricsCollector:
    """
    Collects metrics and writes them to storage.
    
    Supports both in-memory storage and InfluxDB for persistence.
    """
    
    def __init__(
        self,
        influx_client: InfluxDBClient | None = None,
        bucket: str = "homeiq_analytics",
    ):
        """
        Initialize metrics collector.
        
        Args:
            influx_client: Optional InfluxDB client for persistent storage
            bucket: InfluxDB bucket name
        """
        self.influx_client = influx_client
        self.bucket = bucket
        self._in_memory_metrics: list[MetricPoint] = []
        
        logger.info(
            f"MetricsCollector initialized "
            f"(InfluxDB: {'enabled' if influx_client else 'disabled'})"
        )
    
    async def record_deployment(
        self,
        automation_id: str,
        blueprint_id: str | None = None,
        synergy_id: str | None = None,
        source: str = "synergy",
    ) -> None:
        """
        Record an automation deployment metric.
        
        Args:
            automation_id: Home Assistant automation ID
            blueprint_id: Optional blueprint ID
            synergy_id: Optional synergy ID
            source: Deployment source
        """
        point = MetricPoint(
            measurement="automation_deployment",
            tags={
                "automation_id": automation_id,
                "blueprint_id": blueprint_id or "none",
                "synergy_id": synergy_id or "none",
                "source": source,
            },
            fields={
                "count": 1,
                "has_blueprint": 1 if blueprint_id else 0,
                "from_synergy": 1 if synergy_id else 0,
            },
            timestamp=datetime.utcnow(),
        )
        
        await self._write_point(point)
    
    async def record_execution(
        self,
        automation_id: str,
        success: bool,
        execution_time_ms: int | None = None,
        error_type: str | None = None,
    ) -> None:
        """
        Record an automation execution metric.
        
        Args:
            automation_id: Home Assistant automation ID
            success: Whether execution was successful
            execution_time_ms: Execution time in milliseconds
            error_type: Error type if failed
        """
        point = MetricPoint(
            measurement="automation_execution",
            tags={
                "automation_id": automation_id,
                "success": str(success).lower(),
                "error_type": error_type or "none",
            },
            fields={
                "count": 1,
                "success": 1 if success else 0,
                "failure": 0 if success else 1,
                "execution_time_ms": execution_time_ms or 0,
            },
            timestamp=datetime.utcnow(),
        )
        
        await self._write_point(point)
    
    async def record_rating(
        self,
        automation_id: str,
        rating: float,
        blueprint_id: str | None = None,
    ) -> None:
        """
        Record a user rating metric.
        
        Args:
            automation_id: Home Assistant automation ID
            rating: User rating (1-5)
            blueprint_id: Optional blueprint ID
        """
        point = MetricPoint(
            measurement="automation_rating",
            tags={
                "automation_id": automation_id,
                "blueprint_id": blueprint_id or "none",
            },
            fields={
                "rating": rating,
                "count": 1,
            },
            timestamp=datetime.utcnow(),
        )
        
        await self._write_point(point)
    
    async def record_synergy_view(
        self,
        synergy_id: str,
        synergy_type: str,
    ) -> None:
        """
        Record a synergy view metric (for adoption tracking).
        
        Args:
            synergy_id: Synergy identifier
            synergy_type: Type of synergy
        """
        point = MetricPoint(
            measurement="synergy_view",
            tags={
                "synergy_id": synergy_id,
                "synergy_type": synergy_type,
            },
            fields={
                "count": 1,
            },
            timestamp=datetime.utcnow(),
        )
        
        await self._write_point(point)
    
    async def get_adoption_rate(self, days: int = 30) -> dict[str, Any]:
        """
        Calculate adoption rate over the specified period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with adoption metrics
        """
        if self.influx_client:
            # Query InfluxDB for adoption data
            query = f"""
                from(bucket: "{self.bucket}")
                |> range(start: -{days}d)
                |> filter(fn: (r) => r._measurement == "synergy_view" or r._measurement == "automation_deployment")
                |> group(columns: ["_measurement"])
                |> count()
            """
            results = await self.influx_client.query(query)
            
            synergy_views = sum(r.get("_value", 0) for r in results if r.get("_measurement") == "synergy_view")
            deployments = sum(r.get("_value", 0) for r in results if r.get("_measurement") == "automation_deployment")
            
            return {
                "period_days": days,
                "synergy_views": synergy_views,
                "deployments": deployments,
                "adoption_rate": (deployments / synergy_views * 100) if synergy_views > 0 else 0.0,
                "target": 30.0,
            }
        else:
            # Calculate from in-memory metrics
            cutoff = datetime.utcnow() - timedelta(days=days)
            period_metrics = [m for m in self._in_memory_metrics if m.timestamp >= cutoff]
            
            synergy_views = len([m for m in period_metrics if m.measurement == "synergy_view"])
            deployments = len([m for m in period_metrics if m.measurement == "automation_deployment"])
            
            return {
                "period_days": days,
                "synergy_views": synergy_views,
                "deployments": deployments,
                "adoption_rate": (deployments / synergy_views * 100) if synergy_views > 0 else 0.0,
                "target": 30.0,
            }
    
    async def get_success_rate(self, days: int = 30) -> dict[str, Any]:
        """
        Calculate success rate over the specified period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with success metrics
        """
        if self.influx_client:
            query = f"""
                from(bucket: "{self.bucket}")
                |> range(start: -{days}d)
                |> filter(fn: (r) => r._measurement == "automation_execution")
                |> group(columns: ["success"])
                |> count()
            """
            results = await self.influx_client.query(query)
            
            successes = sum(r.get("_value", 0) for r in results if r.get("success") == "true")
            failures = sum(r.get("_value", 0) for r in results if r.get("success") == "false")
            total = successes + failures
            
            return {
                "period_days": days,
                "total_executions": total,
                "successful": successes,
                "failed": failures,
                "success_rate": (successes / total * 100) if total > 0 else 0.0,
                "target": 85.0,
            }
        else:
            cutoff = datetime.utcnow() - timedelta(days=days)
            period_metrics = [
                m for m in self._in_memory_metrics
                if m.measurement == "automation_execution" and m.timestamp >= cutoff
            ]
            
            successes = sum(m.fields.get("success", 0) for m in period_metrics)
            failures = sum(m.fields.get("failure", 0) for m in period_metrics)
            total = successes + failures
            
            return {
                "period_days": days,
                "total_executions": total,
                "successful": successes,
                "failed": failures,
                "success_rate": (successes / total * 100) if total > 0 else 0.0,
                "target": 85.0,
            }
    
    async def get_average_rating(self, days: int = 30) -> dict[str, Any]:
        """
        Calculate average user rating over the specified period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with rating metrics
        """
        if self.influx_client:
            query = f"""
                from(bucket: "{self.bucket}")
                |> range(start: -{days}d)
                |> filter(fn: (r) => r._measurement == "automation_rating")
                |> mean(column: "rating")
            """
            results = await self.influx_client.query(query)
            
            avg_rating = results[0].get("_value", 0.0) if results else 0.0
            count = len(results)
            
            return {
                "period_days": days,
                "total_ratings": count,
                "average_rating": avg_rating,
                "target": 4.0,
            }
        else:
            cutoff = datetime.utcnow() - timedelta(days=days)
            period_metrics = [
                m for m in self._in_memory_metrics
                if m.measurement == "automation_rating" and m.timestamp >= cutoff
            ]
            
            ratings = [m.fields.get("rating", 0) for m in period_metrics]
            
            return {
                "period_days": days,
                "total_ratings": len(ratings),
                "average_rating": sum(ratings) / len(ratings) if ratings else 0.0,
                "target": 4.0,
            }
    
    async def _write_point(self, point: MetricPoint) -> None:
        """Write a metric point to storage."""
        # Always store in memory
        self._in_memory_metrics.append(point)
        
        # Write to InfluxDB if available
        if self.influx_client:
            try:
                await self.influx_client.write_point(
                    measurement=point.measurement,
                    tags=point.tags,
                    fields=point.fields,
                    timestamp=point.timestamp,
                )
            except Exception as e:
                logger.error(f"Failed to write metric to InfluxDB: {e}")
    
    def cleanup_old_metrics(self, days: int = 90) -> int:
        """
        Remove old in-memory metrics.
        
        Args:
            days: Retention period in days
            
        Returns:
            Number of metrics removed
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        original_count = len(self._in_memory_metrics)
        
        self._in_memory_metrics = [
            m for m in self._in_memory_metrics
            if m.timestamp >= cutoff
        ]
        
        removed = original_count - len(self._in_memory_metrics)
        if removed > 0:
            logger.info(f"Cleaned up {removed} old metrics")
        
        return removed
