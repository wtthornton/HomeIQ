"""HomeIQ observability: metrics, logging, monitoring, alerting, tracing.

Provides shared observability utilities for all HomeIQ services:

- **Logging**: Structured JSON logging with correlation IDs
- **Metrics**: Lightweight in-memory metrics collection (counters, gauges, timers)
- **Correlation**: Request correlation ID propagation across service boundaries
- **Alerting**: Threshold-based alerting with cooldown and severity levels
"""

__version__: str = "1.0.0"

from .alert_manager import AlertManager, AlertSeverity, get_alert_manager
from .correlation_middleware import (
    CorrelationMiddleware,
    FastAPICorrelationMiddleware,
    correlation_context,
    create_correlation_middleware,
    propagate_correlation_id,
)
from .logging_config import (
    PerformanceLogger,
    StructuredFormatter,
    generate_correlation_id,
    get_correlation_id,
    get_logger,
    set_correlation_id,
    setup_logging,
)
from .metrics_collector import MetricsCollector, get_metrics_collector

__all__: list[str] = [
    "AlertManager",
    "AlertSeverity",
    "CorrelationMiddleware",
    "FastAPICorrelationMiddleware",
    "MetricsCollector",
    "PerformanceLogger",
    "StructuredFormatter",
    "correlation_context",
    "create_correlation_middleware",
    "generate_correlation_id",
    "get_alert_manager",
    "get_correlation_id",
    "get_logger",
    "get_metrics_collector",
    "propagate_correlation_id",
    "set_correlation_id",
    "setup_logging",
]
