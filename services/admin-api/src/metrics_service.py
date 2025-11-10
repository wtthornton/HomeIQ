"""
Simplified metrics collection utilities for admin-api tests.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional


class MetricType(str, Enum):
    GAUGE = "gauge"
    COUNTER = "counter"
    TIMER = "timer"


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MetricValue:
    timestamp: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "value": self.value,
            "labels": dict(self.labels),
        }


@dataclass
class Metric:
    name: str
    type: MetricType
    description: str
    unit: str
    values: List[MetricValue] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "unit": self.unit,
            "values": [value.to_dict() for value in self.values],
            "labels": dict(self.labels),
        }


class MetricsCollector:
    def __init__(self) -> None:
        self.metrics: Dict[str, Metric] = {}
        self.max_values_per_metric = 1000
        self.system_metrics_enabled = True
        self.metrics_interval = 60.0
        self.is_collecting = False

    def register_metric(
        self,
        name: str,
        metric_type: MetricType,
        description: str,
        unit: str,
        *,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        if name not in self.metrics:
            self.metrics[name] = Metric(
                name=name,
                type=metric_type,
                description=description,
                unit=unit,
                labels=labels or {},
            )

    def record_value(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        metric = self.metrics.get(name)
        if not metric:
            raise ValueError(f"Metric '{name}' not registered")
        metric.values.append(MetricValue(timestamp=_utc_iso_now(), value=value, labels=labels or {}))
        if len(metric.values) > self.max_values_per_metric:
            metric.values = metric.values[-self.max_values_per_metric :]

    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        metric = self.metrics.get(name)
        if not metric or metric.type != MetricType.COUNTER:
            raise ValueError(f"Counter metric '{name}' not registered")
        current = self.get_latest_value(name, labels)
        self.record_value(name, current + value, labels)

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        metric = self.metrics.get(name)
        if not metric or metric.type != MetricType.GAUGE:
            raise ValueError(f"Gauge metric '{name}' not registered")
        self.record_value(name, value, labels)

    def record_timer(self, name: str, value_seconds: float, labels: Optional[Dict[str, str]] = None) -> None:
        metric = self.metrics.get(name)
        if not metric or metric.type != MetricType.TIMER:
            raise ValueError(f"Timer metric '{name}' not registered")
        self.record_value(name, value_seconds, labels)

    def get_latest_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        metric = self.metrics.get(name)
        if not metric or not metric.values:
            return 0.0
        if labels is None:
            return metric.values[-1].value
        for value in reversed(metric.values):
            if value.labels == labels:
                return value.value
        return 0.0

    def get_metric(self, name: str) -> Optional[Metric]:
        return self.metrics.get(name)

    def get_all_metrics(self) -> List[Metric]:
        return list(self.metrics.values())

    def get_metrics_summary(self) -> Dict[str, object]:
        summary = {
            "total_metrics": len(self.metrics),
            "metric_types": {},
            "total_values": 0,
        }
        for metric in self.metrics.values():
            summary["metric_types"].setdefault(metric.type.value, 0)
            summary["metric_types"][metric.type.value] += 1
            summary["total_values"] += len(metric.values)
        return summary

    async def start_collection(self) -> None:
        self.is_collecting = True

    async def stop_collection(self) -> None:
        self.is_collecting = False


class PerformanceTracker:
    def __init__(self, collector: MetricsCollector) -> None:
        self.metrics_collector = collector
        self.operation_timers: Dict[str, float] = {}

    def start_operation(self, operation_name: str) -> str:
        timer_id = f"{operation_name}_{uuid.uuid4().hex[:8]}"
        self.operation_timers[timer_id] = time.perf_counter()
        return timer_id

    def end_operation(self, timer_id: str, labels: Optional[Dict[str, str]] = None) -> None:
        start_time = self.operation_timers.pop(timer_id, None)
        if start_time is None:
            return
        elapsed = time.perf_counter() - start_time
        labels = labels or {}
        labels = {"operation": timer_id.split("_")[0], **labels}
        self.metrics_collector.record_timer("operation_duration_seconds", elapsed, labels)

    def record_event_processed(self, event_type: str, processing_time_ms: float, entity_id: str) -> None:
        self.metrics_collector.record_timer(
            "event_processing_duration_seconds",
            processing_time_ms / 1000.0,
            {"event_type": event_type, "entity_id": entity_id},
        )
        self.metrics_collector.increment_counter(
            "events_processed_total",
            1.0,
            {"event_type": event_type, "entity_id": entity_id},
        )

    def record_error(self, error_type: str, service: str) -> None:
        self.metrics_collector.increment_counter(
            "errors_total",
            1.0,
            {"error_type": error_type, "service": service},
        )

    def record_api_request(self, endpoint: str, method: str, status_code: int, duration_ms: float) -> None:
        labels = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code),
        }
        self.metrics_collector.record_timer("api_request_duration_seconds", duration_ms / 1000.0, labels)
        self.metrics_collector.increment_counter("api_requests_total", 1.0, labels)


class MetricsService:
    def __init__(self) -> None:
        self.collector = MetricsCollector()
        self.performance_tracker = PerformanceTracker(self.collector)
        self.is_running = False
        self._register_default_metrics()

    def _register_default_metrics(self) -> None:
        defaults = [
            ("events_processed_total", MetricType.COUNTER, "Total events processed", "count"),
            ("api_requests_total", MetricType.COUNTER, "Total API requests", "count"),
            ("errors_total", MetricType.COUNTER, "Total errors", "count"),
            ("event_processing_duration_seconds", MetricType.TIMER, "Event processing duration", "seconds"),
            ("api_request_duration_seconds", MetricType.TIMER, "API request duration", "seconds"),
            ("operation_duration_seconds", MetricType.TIMER, "Operation duration", "seconds"),
        ]
        for name, metric_type, description, unit in defaults:
            self.collector.register_metric(name, metric_type, description, unit)

    def get_collector(self) -> MetricsCollector:
        return self.collector

    def get_performance_tracker(self) -> PerformanceTracker:
        return self.performance_tracker

    def get_metrics(self, names: Optional[List[str]] = None) -> List[Dict[str, object]]:
        metrics = (
            [self.collector.metrics[name] for name in names if name in self.collector.metrics]
            if names
            else self.collector.get_all_metrics()
        )
        return [metric.to_dict() for metric in metrics]

    def get_metrics_summary(self) -> Dict[str, object]:
        return self.collector.get_metrics_summary()

    def get_current_metrics(self) -> Dict[str, Dict[str, object]]:
        current = {}
        for name, metric in self.collector.metrics.items():
            value = self.collector.get_latest_value(name)
            current[name] = {
                "value": value,
                "unit": metric.unit,
                "description": metric.description,
            }
        return current

    async def start(self) -> None:
        await self.collector.start_collection()
        self.is_running = True

    async def stop(self) -> None:
        await self.collector.stop_collection()
        self.is_running = False


# Module-level singleton used by other services/tests
metrics_service = MetricsService()

