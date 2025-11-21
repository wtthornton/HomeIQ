"""
Shared Metrics Collector
Epic 17.3: Essential Performance Metrics

Lightweight metrics collection for service monitoring without external dependencies.
"""

import logging
import time
from collections.abc import Callable
from contextlib import contextmanager, suppress
from datetime import datetime
from functools import wraps
from typing import Any

import psutil

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Lightweight metrics collector for service performance monitoring"""

    def __init__(self, service_name: str, influxdb_client=None):
        """
        Initialize metrics collector

        Args:
            service_name: Name of the service
            influxdb_client: Optional InfluxDB client for metric storage
        """
        self.service_name = service_name
        self.influxdb_client = influxdb_client

        # In-memory counters
        self.counters = {}
        self.gauges = {}
        self.timers = {}
        self.start_time = time.time()

        # Process info for system metrics
        try:
            self.process = psutil.Process()
        except Exception as e:
            logger.warning(f"Could not initialize psutil Process: {e}")
            self.process = None

    def increment_counter(self, name: str, value: int = 1, tags: dict[str, str] | None = None):
        """
        Increment a counter metric

        Args:
            name: Counter name
            value: Value to increment by
            tags: Optional tags for the metric
        """
        key = self._make_key(name, tags)
        self.counters[key] = self.counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, tags: dict[str, str] | None = None):
        """
        Set a gauge metric

        Args:
            name: Gauge name
            value: Current value
            tags: Optional tags for the metric
        """
        key = self._make_key(name, tags)
        self.gauges[key] = value

    def record_timing(self, name: str, duration_ms: float, tags: dict[str, str] | None = None):
        """
        Record a timing metric

        Args:
            name: Timer name
            duration_ms: Duration in milliseconds
            tags: Optional tags for the metric
        """
        key = self._make_key(name, tags)
        if key not in self.timers:
            self.timers[key] = {
                "count": 0,
                "total": 0.0,
                "min": float("inf"),
                "max": 0.0,
            }

        timer = self.timers[key]
        timer["count"] += 1
        timer["total"] += duration_ms
        timer["min"] = min(timer["min"], duration_ms)
        timer["max"] = max(timer["max"], duration_ms)

    @contextmanager
    def timer(self, name: str, tags: dict[str, str] | None = None):
        """
        Context manager for timing operations

        Args:
            name: Timer name
            tags: Optional tags for the metric

        Example:
            with metrics.timer('api_request', {'endpoint': '/health'}):
                # ... operation to time
                pass
        """
        start = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start) * 1000
            self.record_timing(name, duration_ms, tags)

    def timing_decorator(self, name: str | None = None, tags: dict[str, str] | None = None):
        """
        Decorator for timing function execution

        Args:
            name: Timer name (uses function name if not provided)
            tags: Optional tags for the metric

        Example:
            @metrics.timing_decorator('process_event')
            def process_event(event):
                # ... processing logic
                pass
        """
        def decorator(func: Callable):
            metric_name = name or f"{func.__name__}_duration"

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.time()
                try:
                    return await func(*args, **kwargs)
                finally:
                    duration_ms = (time.time() - start) * 1000
                    self.record_timing(metric_name, duration_ms, tags)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.time()
                try:
                    return func(*args, **kwargs)
                finally:
                    duration_ms = (time.time() - start) * 1000
                    self.record_timing(metric_name, duration_ms, tags)

            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    def get_system_metrics(self) -> dict[str, Any]:
        """
        Get current system metrics (CPU, memory, disk)

        Returns:
            Dictionary of system metrics
        """
        metrics = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": time.time() - self.start_time,
        }

        if self.process:
            try:
                # CPU metrics
                metrics["cpu"] = {
                    "percent": self.process.cpu_percent(interval=0.1),
                    "num_threads": self.process.num_threads(),
                }

                # Memory metrics
                mem_info = self.process.memory_info()
                metrics["memory"] = {
                    "rss_bytes": mem_info.rss,
                    "rss_mb": mem_info.rss / (1024 * 1024),
                    "percent": self.process.memory_percent(),
                }

                # File descriptor count (Unix only)
                with suppress(AttributeError, NotImplementedError):
                    metrics["file_descriptors"] = self.process.num_fds()

            except Exception as e:
                logger.warning(f"Error collecting system metrics: {e}")

        return metrics

    def get_all_metrics(self) -> dict[str, Any]:
        """
        Get all collected metrics

        Returns:
            Dictionary containing all metrics
        """
        # Calculate timer averages
        timer_stats = {}
        for key, timer in self.timers.items():
            if timer["count"] > 0:
                timer_stats[key] = {
                    "count": timer["count"],
                    "total_ms": timer["total"],
                    "avg_ms": timer["total"] / timer["count"],
                    "min_ms": timer["min"],
                    "max_ms": timer["max"],
                }

        return {
            "service": self.service_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": time.time() - self.start_time,
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "timers": timer_stats,
            "system": self.get_system_metrics(),
        }

    async def write_to_influxdb(self, measurement: str = "service_metrics"):
        """
        Write current metrics to InfluxDB

        Args:
            measurement: InfluxDB measurement name
        """
        if not self.influxdb_client:
            return

        try:
            from influxdb_client import Point
            from influxdb_client.client.write_api import SYNCHRONOUS

            write_api = self.influxdb_client.write_api(write_options=SYNCHRONOUS)

            # Write counters
            for key, value in self.counters.items():
                point = Point(measurement) \
                    .tag("service", self.service_name) \
                    .tag("metric_type", "counter") \
                    .field(key, value)
                write_api.write(bucket=self.influxdb_bucket, record=point)

            # Write gauges
            for key, value in self.gauges.items():
                point = Point(measurement) \
                    .tag("service", self.service_name) \
                    .tag("metric_type", "gauge") \
                    .field(key, value)
                write_api.write(bucket=self.influxdb_bucket, record=point)

            # Write timer averages
            for key, timer in self.timers.items():
                if timer["count"] > 0:
                    avg_ms = timer["total"] / timer["count"]
                    point = Point(measurement) \
                        .tag("service", self.service_name) \
                        .tag("metric_type", "timer") \
                        .field(f"{key}_avg_ms", avg_ms) \
                        .field(f"{key}_count", timer["count"])
                    write_api.write(bucket=self.influxdb_bucket, record=point)

            # Write system metrics
            system_metrics = self.get_system_metrics()
            if "cpu" in system_metrics:
                point = Point(measurement) \
                    .tag("service", self.service_name) \
                    .tag("metric_type", "system") \
                    .field("cpu_percent", system_metrics["cpu"]["percent"]) \
                    .field("memory_mb", system_metrics["memory"]["rss_mb"])
                write_api.write(bucket=self.influxdb_bucket, record=point)

            logger.debug(f"Wrote metrics to InfluxDB for {self.service_name}")

        except Exception as e:
            logger.exception(f"Error writing metrics to InfluxDB: {e}")

    def reset_metrics(self):
        """Reset all metrics counters"""
        self.counters.clear()
        self.gauges.clear()
        self.timers.clear()

    def _make_key(self, name: str, tags: dict[str, str] | None = None) -> str:
        """Create a unique key from name and tags"""
        if not tags:
            return name

        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"


# Global metrics collector instances per service
_metrics_collectors: dict[str, MetricsCollector] = {}


def get_metrics_collector(service_name: str, influxdb_client=None) -> MetricsCollector:
    """
    Get or create a metrics collector for a service

    Args:
        service_name: Name of the service
        influxdb_client: Optional InfluxDB client

    Returns:
        MetricsCollector instance
    """
    if service_name not in _metrics_collectors:
        _metrics_collectors[service_name] = MetricsCollector(service_name, influxdb_client)

    return _metrics_collectors[service_name]
