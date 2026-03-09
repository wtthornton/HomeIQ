"""Operational metrics for memory operations.

Provides a callback-based metrics interface that consumers can hook into
any metrics backend (InfluxDB, Prometheus, etc.). Includes a default
in-memory counter for testing and health checks.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Type for metrics callback: (metric_name, value, tags_dict)
MetricsCallback = Callable[[str, float, dict[str, str]], None]

_callbacks: list[MetricsCallback] = []
_counters: dict[str, float] = defaultdict(float)
_histograms: dict[str, list[float]] = defaultdict(list)

# Maximum histogram samples to keep in memory
_MAX_HISTOGRAM_SAMPLES = 1000


def register_callback(callback: MetricsCallback) -> None:
    """Register a metrics callback for external reporting.

    Args:
        callback: Function called with (metric_name, value, tags).
    """
    _callbacks.append(callback)
    logger.debug("Registered metrics callback: %s", callback.__name__)


def clear_callbacks() -> None:
    """Remove all registered callbacks (useful for testing)."""
    _callbacks.clear()


def emit(metric: str, value: float = 1.0, tags: dict[str, str] | None = None) -> None:
    """Emit a metric value.

    Updates internal counters and notifies all registered callbacks.

    Args:
        metric: Metric name (e.g., 'memory_save_count').
        value: Metric value (default 1.0 for counters).
        tags: Optional tags dict (e.g., {'type': 'preference'}).
    """
    tags = tags or {}
    _counters[metric] += value

    for callback in _callbacks:
        try:
            callback(metric, value, tags)
        except Exception as e:
            logger.warning("Metrics callback failed: %s", e)


def emit_histogram(metric: str, value: float, tags: dict[str, str] | None = None) -> None:
    """Emit a histogram/timing metric.

    Args:
        metric: Metric name (e.g., 'memory_search_latency_ms').
        value: Metric value.
        tags: Optional tags dict.
    """
    tags = tags or {}

    samples = _histograms[metric]
    if len(samples) >= _MAX_HISTOGRAM_SAMPLES:
        samples.pop(0)
    samples.append(value)

    for callback in _callbacks:
        try:
            callback(metric, value, tags)
        except Exception as e:
            logger.warning("Metrics callback failed: %s", e)


@contextmanager
def measure(metric: str, tags: dict[str, str] | None = None):
    """Context manager to measure operation duration in milliseconds.

    Usage:
        with measure('memory_search_latency_ms', {'mode': 'hybrid'}):
            results = await search.search(query)

    Args:
        metric: Metric name for the timing.
        tags: Optional tags dict.
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        emit_histogram(metric, duration_ms, tags)


def get_counters() -> dict[str, float]:
    """Return current counter values (for health checks)."""
    return dict(_counters)


def get_histogram_stats(metric: str) -> dict[str, float]:
    """Return histogram statistics for a metric.

    Returns:
        Dict with count, min, max, avg, p50, p95, p99 values.
    """
    samples = _histograms.get(metric, [])
    if not samples:
        return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}

    sorted_samples = sorted(samples)
    count = len(sorted_samples)

    return {
        "count": count,
        "min": sorted_samples[0],
        "max": sorted_samples[-1],
        "avg": sum(sorted_samples) / count,
        "p50": sorted_samples[int(count * 0.5)],
        "p95": sorted_samples[min(int(count * 0.95), count - 1)],
        "p99": sorted_samples[min(int(count * 0.99), count - 1)],
    }


def reset() -> None:
    """Reset all counters and histograms (for testing)."""
    _counters.clear()
    _histograms.clear()
