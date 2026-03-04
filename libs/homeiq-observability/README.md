# homeiq-observability

Shared observability utilities for the HomeIQ platform: structured logging, metrics collection, correlation middleware, and alerting.

## Features

- **StructuredFormatter**: JSON-formatted log output with correlation IDs
- **MetricsCollector**: Lightweight in-memory metrics (counters, gauges, timers)
- **CorrelationMiddleware**: Request correlation ID propagation across services
- **AlertManager**: Threshold-based alerting system

## Installation

```bash
pip install -e libs/homeiq-observability/
```

## Usage

```python
from homeiq_observability.logging_config import setup_logging, get_logger
from homeiq_observability.metrics_collector import MetricsCollector
from homeiq_observability.correlation_middleware import CorrelationMiddleware
```
