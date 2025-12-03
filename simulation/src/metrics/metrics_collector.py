"""
Metrics Collector

Comprehensive metrics collection for simulation framework.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Metrics collector for simulation framework.
    
    Collects comprehensive metrics for:
    - Workflow execution (3 AM, Ask AI)
    - Performance (latency, throughput)
    - Quality (accuracy, validation results)
    - Resource usage (memory, CPU)
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: dict[str, Any] = {
            "workflows": {},
            "performance": {},
            "quality": {},
            "resources": {}
        }
        self.start_time = datetime.now(timezone.utc)
        
        logger.info("MetricsCollector initialized")

    def record_workflow_metric(
        self,
        workflow_type: str,
        home_id: str,
        metric_name: str,
        value: Any,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Record a workflow metric.
        
        Args:
            workflow_type: "3am" or "ask_ai"
            home_id: Home identifier
            metric_name: Metric name
            value: Metric value
            metadata: Optional metadata
        """
        if workflow_type not in self.metrics["workflows"]:
            self.metrics["workflows"][workflow_type] = {}
        
        if home_id not in self.metrics["workflows"][workflow_type]:
            self.metrics["workflows"][workflow_type][home_id] = {}
        
        self.metrics["workflows"][workflow_type][home_id][metric_name] = {
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }

    def record_performance_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "seconds",
        metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Record a performance metric.
        
        Args:
            metric_name: Metric name
            value: Metric value
            unit: Unit of measurement
            metadata: Optional metadata
        """
        if metric_name not in self.metrics["performance"]:
            self.metrics["performance"][metric_name] = []
        
        self.metrics["performance"][metric_name].append({
            "value": value,
            "unit": unit,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        })

    def record_quality_metric(
        self,
        metric_name: str,
        value: Any,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Record a quality metric.
        
        Args:
            metric_name: Metric name
            value: Metric value
            metadata: Optional metadata
        """
        if metric_name not in self.metrics["quality"]:
            self.metrics["quality"][metric_name] = []
        
        self.metrics["quality"][metric_name].append({
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        })

    def get_summary(self) -> dict[str, Any]:
        """
        Get metrics summary.
        
        Returns:
            Summary dictionary
        """
        end_time = datetime.now(timezone.utc)
        duration = (end_time - self.start_time).total_seconds()
        
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "workflows": {
                workflow_type: {
                    "total_homes": len(homes),
                    "homes": list(homes.keys())
                }
                for workflow_type, homes in self.metrics["workflows"].items()
            },
            "performance": {
                metric_name: {
                    "count": len(values),
                    "avg": sum(v["value"] for v in values) / len(values) if values else 0,
                    "min": min(v["value"] for v in values) if values else 0,
                    "max": max(v["value"] for v in values) if values else 0
                }
                for metric_name, values in self.metrics["performance"].items()
            },
            "quality": {
                metric_name: {
                    "count": len(values),
                    "values": [v["value"] for v in values]
                }
                for metric_name, values in self.metrics["quality"].items()
            }
        }

    def clear(self) -> None:
        """Clear all metrics."""
        self.metrics = {
            "workflows": {},
            "performance": {},
            "quality": {},
            "resources": {}
        }
        self.start_time = datetime.now(timezone.utc)

