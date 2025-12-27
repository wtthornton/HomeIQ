# Monitoring and Observability

**Last Updated:** January 2025  
**Target Platform:** Home Assistant single-home deployment on NUC (Next Unit of Computing)  
**Context7 Patterns:** Integrated throughout

## Monitoring Stack

- **Frontend Monitoring:** Browser console errors, API response times
- **Backend Monitoring:** Python logging with structured JSON format (Context7 pattern)
- **Error Tracking:** Comprehensive error logging with request context and correlation IDs
- **Performance Monitoring:** Response time tracking, database query performance
- **Telemetry:** Context7 global state pattern for service statistics
- **Resource Monitoring:** NUC-specific CPU, memory, and disk usage tracking

## Context7 Telemetry Patterns

### Structured Logging with Correlation IDs

**Context7 Pattern:** All services use structured JSON logging with correlation IDs for request tracing.

```python
from shared.logging_config import get_logger
from contextvars import ContextVar

correlation_id: ContextVar[str] = ContextVar('correlation_id', default=None)
logger = get_logger(__name__)

# Set correlation ID at request start
correlation_id.set(request_id)

# Log with correlation ID (automatically included in JSON logs)
logger.info("Processing event", extra={"event_id": event.id, "endpoint": "/api/events"})
```

**Log Format:**
```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "level": "INFO",
  "service": "data-api",
  "message": "Processing event",
  "correlation_id": "req-abc123",
  "context": {
    "filename": "main.py",
    "lineno": 42,
    "function": "process_event",
    "module": "api"
  },
  "extra": {
    "event_id": "evt-xyz789",
    "endpoint": "/api/events"
  }
}
```

### Global State Pattern for Telemetry

**Context7 Pattern:** Services use global state with setter pattern for telemetry collection.

```python
# Global state with setter (Context7 pattern)
_metrics_collector = None

def set_metrics_collector(collector):
    """Set metrics collector for telemetry"""
    global _metrics_collector
    _metrics_collector = collector

def get_metrics_collector():
    """Get metrics collector instance"""
    return _metrics_collector

# Usage in lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    metrics = MetricsCollector()
    set_metrics_collector(metrics)
    yield
    # Cleanup
```

### Metrics Collection

```python
from shared.metrics_collector import get_metrics_collector

metrics = get_metrics_collector("data-api")

# Counter: Increment on events
metrics.increment_counter("requests_total", tags={"endpoint": "/health"})

# Gauge: Set current value
metrics.set_gauge("queue_size", len(current_queue))

# Timer: Track durations
with metrics.timer("database_query"):
    result = await db.execute(query)
```

## Key Metrics

### Frontend Metrics
- API response times
- JavaScript errors
- Component render performance
- User interactions
- Bundle size and load times

### Backend Metrics
- Request rate and response times
- Error rate by endpoint
- Database query performance (SQLite <10ms, InfluxDB <100ms)
- WebSocket connection health
- Weather API response times
- **Correlation ID tracking** - Request tracing across services
- **Context7 telemetry overhead** - <2% CPU, <1% bandwidth

### NUC-Specific Resource Metrics
- **CPU per service:** <30% normal, <60% peak
- **Memory per service:** <60% of limit
- **Total system memory:** <70% (reserve for Home Assistant)
- **Disk I/O:** <70% utilization
- **SQLite cache:** <32MB (NUC-optimized)
- **InfluxDB memory:** <256MB (NUC-optimized)

## Environment Health Monitoring (Epic 31 Refresh – Nov 2025)

### Backend
- `/api/health/environment` now emits structured logs (`event=environment_health`) capturing health score, HA status, integration count, and detected issue totals.
- Health normalization safeguards strip unexpected integration fields while still persisting contextual `check_details` payloads for each integration.
- Any schema mismatch falls back to a synthetic `error` entry and logs a warning instead of surfacing 500s to the dashboard.
- **Context7 Pattern:** All health endpoints use correlation IDs for request tracing.

### Frontend
- `useEnvironmentHealth` surfaces backend error details directly (e.g. `Setup service error 503: Health monitoring service not initialized`) and guards against empty/malformed payloads.
- The Setup & Health tab renders integration `check_details` (broker host, bridge state, failure recommendations, etc.) to give operators actionable diagnostics without leaving the dashboard.
- Retry behaviour (`Try Again →`) reuses the same fetch path so new health data benefits immediately from backend logging and normalization changes.

## Observability Patterns

### Request Tracing with Correlation IDs

**Context7 Pattern:** All requests include correlation IDs for end-to-end tracing.

```python
from shared.correlation_middleware import CorrelationMiddleware

# Add middleware to FastAPI app
app.add_middleware(CorrelationMiddleware)

# Correlation ID automatically set in context
# Accessible via: correlation_id.get()
```

### Structured Logging Best Practices

1. **Always include correlation IDs** - Set at request start, included in all logs
2. **Use structured JSON format** - Machine-readable, searchable logs
3. **Include context information** - Service name, endpoint, function name
4. **Add extra fields** - Event IDs, entity IDs, processing times
5. **Batch log statements** - Avoid excessive logging in hot paths

### Performance Monitoring

**Context7 Pattern:** Use timing decorators and metrics collection.

```python
from shared.metrics_collector import get_metrics_collector

metrics = get_metrics_collector("service-name")

@metrics.timing_decorator("endpoint_name")
async def endpoint_handler():
    # Endpoint logic
    pass
```

### NUC Resource Monitoring

**Critical for NUC deployments:** Monitor resource constraints continuously.

```python
import psutil

# Monitor NUC resources
cpu_percent = psutil.cpu_percent(interval=1)
memory_mb = psutil.virtual_memory().used / 1024 / 1024
disk_usage = psutil.disk_usage('/').percent

# Alert thresholds for NUC
if cpu_percent > 70:  # Lower threshold for NUC
    logger.warning("High CPU usage", extra={"cpu_percent": cpu_percent})
if memory_mb > 1024:  # 1GB limit for services
    logger.warning("High memory usage", extra={"memory_mb": memory_mb})
```

## Alerting and Thresholds

### Performance Alerts (NUC-Optimized)
- **Response Time:** P95 > target × 2
- **Error Rate:** >5% for 5 minutes
- **Memory Usage:** >80% of limit for 10 minutes
- **CPU Usage:** >70% for 15 minutes (NUC threshold)
- **Queue Size:** >500 events for 5 minutes (single-home)

### Resource Alerts (NUC-Specific)
- **Total System Memory:** >85% (critical)
- **CPU per Service:** >70% (critical for NUC)
- **Disk Usage:** >85% (critical)
- **InfluxDB Memory:** >320MB (warning for NUC)

## Log Aggregation

### Docker Logging Configuration
- **Format:** JSON structured logs
- **Driver:** `json-file` with rotation
- **Rotation:** 10MB files, 3 files max
- **Labels:** Service identification for filtering

### Log Analysis
- **Correlation ID search** - Trace requests across services
- **Service filtering** - Filter logs by service name
- **Level filtering** - Filter by log level (DEBUG, INFO, WARNING, ERROR)
- **Time range queries** - Query logs by timestamp

## Monitoring Tools

### Built-in Tools
- **Health Dashboard** - Real-time service health and metrics
- **Docker Stats** - Container resource usage
- **Structured Logs** - JSON format for easy parsing
- **Metrics Collector** - In-memory metrics aggregation

### External Tools (Optional)
- **Grafana** - Advanced dashboards and visualization
- **Prometheus** - Metrics collection and alerting
- **ELK Stack** - Log aggregation and analysis

## Best Practices

1. **Always use correlation IDs** - Enable request tracing
2. **Structured logging** - JSON format for all logs
3. **Resource monitoring** - Track NUC constraints continuously
4. **Performance metrics** - Monitor response times and throughput
5. **Error tracking** - Comprehensive error logging with context
6. **Context7 patterns** - Follow Context7 telemetry patterns
7. **NUC awareness** - Monitor resource constraints specific to NUC