# Performance Patterns Guide

**Last Updated:** November 2025  
**Purpose:** Core performance patterns for HomeIQ development  
**Target Platform:** Home Assistant single-home deployment on NUC (Next Unit of Computing)  
**Context7 Patterns:** Integrated throughout

## Core Performance Principles

1. **Measure First, Optimize Second** - Always profile before optimizing
2. **Async Everything** - Use `async/await` throughout Python services
3. **Batch Over Individual** - Batch database writes, API calls, event processing
4. **Cache Intelligently** - Cache expensive operations with appropriate TTLs
5. **Fail Fast, Recover Gracefully** - Use timeouts, retries, circuit breakers
6. **Memory Over CPU** - Use in-memory caching and data structures (critical for NUC)
7. **Profile Production Reality** - Test with real HA event volumes
8. **Resource-Aware Design** - Optimize for NUC constraints (limited CPU/memory)
9. **Context7 Telemetry** - Structured logging and observability patterns
10. **Single-Home Optimization** - Scale for 1 home, not multi-tenant

## Architecture Performance Patterns

### 1. Hybrid Database Architecture (5-10x Speedup)

**WHY:** InfluxDB excels at time-series writes but has 50ms+ query latency. SQLite provides <10ms metadata lookups.

**PATTERN:**
```
InfluxDB (Time-Series)          SQLite (Metadata)
├── state_changed events        ├── devices (99 devices)
├── metrics & telemetry         ├── entities (100+ entities)
├── historical queries          ├── webhooks
└── retention policies          └── AI suggestions
```

**Performance Impact:**
- Device queries: 50ms (InfluxDB) → <10ms (SQLite) = **5x faster**
- Concurrent reads: Limited (InfluxDB) → Unlimited readers (SQLite WAL)
- Filtering: Slow (InfluxDB tags) → Fast (SQLite indexes)

### 2. Event-Driven Architecture

**WHY:** Webhooks (push) are 100x more efficient than polling for automations.

**PATTERN:**
```
Home Assistant Event → WebSocket → Batch Queue → InfluxDB
                                  ↓
                          Webhook Detection (15s intervals)
                                  ↓
                          HMAC-signed POST → HA Automation
```

**Performance Impact:**
- HA polling: Every 30s (high overhead) → Webhook push (zero overhead)
- Event detection: 15s background loop (minimal CPU)
- Delivery: Retry with exponential backoff (resilient)

### 3. Microservices with Clear Boundaries

**WHY:** Each service has specific performance profile. Isolate slow operations from fast ones.

**PATTERN:**
```
Fast Services (<10ms)           Slow Services (100ms-1s)
├── health checks               ├── OpenAI API calls (AI suggestions)
├── device/entity queries       ├── Weather API (external)
└── metrics endpoints           └── Historical InfluxDB queries
```

### 4. Pattern Detector Threshold Overrides (Single-Home Tuning)

**WHY:** Different device domains tolerate different signal-to-noise ratios. Lights should surface ideas with lower confidence than locks or security sensors.

**PATTERN:**
```
Domain-Specific Thresholds (config.py)
├── time_of_day_min_occurrences = 10            # Base requirement
├── time_of_day_occurrence_overrides = {
│     "light": 8, "switch": 8, "media_player": 6, "lock": 4
│   }
├── time_of_day_confidence_overrides = {
│     "light": 0.6, "switch": 0.6, "media_player": 0.6, "lock": 0.85
│   }
├── co_occurrence_min_support = 10
├── co_occurrence_support_overrides = {
│     "light": 6, "switch": 6, "media_player": 4, "lock": 4
│   }
└── co_occurrence_confidence_overrides = {
      "light": 0.6, "switch": 0.6, "lock": 0.85, "climate": 0.75
   }
```

**Performance Impact:**
- Lights & convenience devices surface faster (reduced thresholds).
- Security devices remain conservative (higher confidence/support).
- Overrides are all controlled in `config.py` for quick tuning without code changes.

### 5. Manual Refresh Guard & Telemetry

**WHY:** Prevent duplicate OpenAI spend and track nightly batch health.

**PATTERN:**
```
Manual Refresh Flow
┌──────────────────────────────┐
│ POST /api/suggestions/refresh│
└──────────────┬──────────────┘
               │ (cooldown: 24h)
               ▼
┌──────────────────────────────┐
│ manual_refresh_triggers (DB) │  ➜ persists audit trail
└──────────────┬──────────────┘
               ▼
┌──────────────────────────────┐
│ Scheduler.trigger_manual_run │
└──────────────┬──────────────┘
               ▼
┌──────────────────────────────┐
│ analysis_run_status (DB)     │  ➜ started_at, status, duration, metrics
└──────────────────────────────┘
```

**Outputs:**
- `/api/suggestions/refresh/status` tells the UI when the next manual refresh is allowed.
- `/api/analysis/status` now includes `analysis_run` with the most recent batch timestamp and status for dashboards.

## Database Performance Patterns

### SQLite Optimization

**CRITICAL SETTINGS:**
```python
# Connection Pragmas (set on each connection)
PRAGMA journal_mode=WAL          # Writers don't block readers
PRAGMA synchronous=NORMAL        # Fast writes, survives OS crash
PRAGMA cache_size=-64000         # 64MB cache (negative = KB)
PRAGMA temp_store=MEMORY         # Fast temp tables
PRAGMA foreign_keys=ON           # Referential integrity
PRAGMA busy_timeout=30000        # 30s lock wait (vs fail immediately)
```

**Best Practices:**
1. **Use WAL Mode Always** - Allows concurrent readers + single writer
2. **Index Your Queries** - Add indexes on filter columns
3. **Batch Inserts** - Use bulk operations, not loops
4. **Async Session Management** - Always use context managers
5. **Query Optimization** - Use eager loading for relationships

### InfluxDB Optimization

**CRITICAL SETTINGS:**
```python
# Batch Writer
batch_size = 1000                # Points per batch
batch_timeout = 5.0              # Seconds before force flush
max_retries = 3                  # Retry on network errors
```

**Best Practices:**
1. **Batch Everything** - Never write single points
2. **Use Appropriate Tags vs Fields** - Tags for filtering, fields for values
3. **Retention Policies** - Configure data lifecycle
4. **Query Optimization** - Specific time range + field selection
5. **Connection Pooling** - Reuse InfluxDB client

## API Performance Patterns

### FastAPI Best Practices (Context7 Patterns)

**Response Time Targets (NUC-Optimized):**
- Health checks: <10ms
- Device/Entity queries: <10ms (SQLite)
- Event queries: <100ms (InfluxDB)
- AI operations: <5s (OpenAI API)

**Context7 Key Patterns:**

1. **Lifespan Context Managers** - Modern FastAPI pattern
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize services
    health_services["checker"] = HealthChecker()
    yield
    # Shutdown: Clean up resources
    health_services.clear()

app = FastAPI(lifespan=lifespan)
```

2. **Pydantic Settings Pattern** - Type-validated configuration
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    batch_size: int = 100
    batch_timeout: float = 5.0
    
    model_config = SettingsConfigDict(env_file=".env")

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

3. **Global State with Setter Pattern** - Context7 telemetry pattern
```python
_metrics_collector = None

def set_metrics_collector(collector):
    """Set metrics collector for telemetry"""
    global _metrics_collector
    _metrics_collector = collector

def get_metrics_collector():
    """Get metrics collector instance"""
    return _metrics_collector
```

4. **Async Dependencies** - Use async database sessions
5. **Background Tasks** - Use FastAPI BackgroundTasks for slow operations
6. **Request Validation** - Use Pydantic models
7. **Connection Pooling** - Reuse HTTP client sessions
8. **Correlation IDs** - Track requests across services (Context7 structured logging)

## Caching Strategies

### 1. TTL-based LRU Cache
```python
cache = WeatherCache(max_size=1000, default_ttl=300)  # 5 minutes
```

### 2. Differentiated TTL Cache
```python
CACHE_TTLS = {
    "live_scores": 15,        # 15 seconds (game in progress)
    "recent_scores": 300,     # 5 minutes (game just ended)
    "fixtures": 3600,         # 1 hour (schedule data)
}
```

### 3. Direct Database Cache
Write directly to SQLite on WebSocket connection instead of periodic sync.

## Event Processing Performance

### Batch Processing Pattern
```python
class BatchProcessor:
    def __init__(self, batch_size: int = 100, batch_timeout: float = 5.0):
        self.batch_size = batch_size      # Max events per batch
        self.batch_timeout = batch_timeout  # Max seconds to wait
```

**Two Flush Triggers:**
1. **Size-based:** Batch reaches 100 events → flush immediately
2. **Time-based:** 5 seconds elapsed → flush partial batch

**Performance Impact:**
- Database writes: 1 batch write vs 100 individual writes = **10-100x faster**

## Frontend Performance Patterns

### Vite Build Optimization
- Code splitting with vendor chunk
- Hash naming for cache busting
- Multi-stage builds for smaller images

### State Management (Zustand)
- Selective subscriptions to prevent unnecessary re-renders
- Batch updates to reduce re-render frequency

### React Performance Patterns
1. **Memoization** - useMemo for expensive calculations
2. **Lazy Loading** - Code splitting with Suspense
3. **Virtualization** - For long lists (1000+ items)
4. **Debouncing** - For search inputs

## Performance Monitoring (Context7 Telemetry Patterns)

### Structured Logging with Correlation IDs
```python
from shared.logging_config import get_logger
from contextvars import ContextVar

correlation_id: ContextVar[str] = ContextVar('correlation_id', default=None)
logger = get_logger(__name__)

# Set correlation ID at request start
correlation_id.set(request_id)

# Log with correlation ID (automatically included in JSON logs)
logger.info("Processing event", extra={"event_id": event.id})
```

### Metrics Collection (Context7 Pattern)
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

### NUC-Specific Resource Monitoring
```python
# Monitor NUC resource constraints
metrics.set_gauge("cpu_percent", psutil.cpu_percent(interval=1))
metrics.set_gauge("memory_mb", psutil.virtual_memory().used / 1024 / 1024)
metrics.set_gauge("disk_usage_percent", psutil.disk_usage('/').percent)

# Alert thresholds for NUC (more conservative)
if cpu_percent > 70:  # Lower threshold for NUC
    logger.warning("High CPU usage", extra={"cpu_percent": cpu_percent})
```

### Key Metrics to Track (Single-Home NUC)
1. **Throughput:** requests_per_minute, events_per_minute, batch_size
2. **Latency:** response_time_ms, query_duration_ms, processing_duration_ms
3. **Resource (NUC):** cpu_percent, memory_mb, queue_size, disk_usage_percent
4. **Error:** error_count, retry_count, error_rate_percent
5. **Home Assistant:** websocket_connection_status, event_rate_per_second
6. **Context7 Telemetry:** correlation_id_tracking, structured_log_rate

## NUC-Specific Optimizations

### Resource Constraints
- **CPU:** Typically 2-4 cores (Intel NUC) - optimize for single-threaded performance
- **Memory:** 4-16GB RAM - prioritize memory efficiency
- **Storage:** SSD recommended for SQLite WAL and InfluxDB
- **Network:** Single home = lower event volume (100-500 events/sec typical)

### NUC-Optimized Settings
```python
# SQLite for NUC (conservative memory)
PRAGMA cache_size=-32000  # 32MB (vs 64MB for larger systems)
PRAGMA temp_store=MEMORY  # Use RAM for temp tables

# InfluxDB batch settings for NUC
batch_size = 500          # Smaller batches (vs 1000)
batch_timeout = 3.0       # Faster flush (vs 5.0)

# Service memory limits (NUC)
websocket-ingestion: 256MB  # Reduced from 512MB
data-api: 128MB            # Reduced from 256MB
admin-api: 128MB           # Reduced from 256MB
```

### Single-Home Event Volume
- **Typical:** 100-500 events/sec (vs 1000+ for multi-home)
- **Peak:** 1000 events/sec (device discovery, bulk updates)
- **Batch Size:** 50-100 events (vs 100-200 for multi-home)
- **Batch Timeout:** 3-5 seconds (faster response for single user)

## Common Anti-Patterns to Avoid

1. **Blocking the Event Loop** - Use aiohttp, not requests
2. **N+1 Database Queries** - Use eager loading
3. **Unbounded Queries** - Always use LIMIT clauses
4. **Not Using Connection Pooling** - Reuse HTTP sessions
5. **Inefficient Frontend Re-renders** - Use useMemo, selective subscriptions
6. **Logging Too Much** - Batch log statements (Context7 structured logging)
7. **Not Setting Timeouts** - Always configure timeouts
8. **Ignoring NUC Constraints** - Over-provisioning memory/CPU
9. **Missing Correlation IDs** - Context7 telemetry requirement
10. **Synchronous Operations** - Blocking calls in async functions

## Performance Targets (NUC Single-Home)

| Endpoint Type | Target | Acceptable | Investigation |
|---------------|--------|------------|---------------|
| Health checks | <10ms | <50ms | >100ms |
| Device queries | <10ms | <50ms | >100ms |
| Event queries | <100ms | <200ms | >500ms |
| Dashboard load | <2s | <5s | >10s |
| WebSocket events | <50ms | <100ms | >200ms |
| AI suggestions | <5s | <10s | >15s |

**NUC Resource Targets:**
- CPU per service: <30% normal, <60% peak
- Memory per service: <60% of limit
- Total system memory: <80% of available
- Disk I/O: <70% utilization

## Quick Reference Commands

```bash
# Monitor performance
docker stats
docker-compose logs -f websocket-ingestion | grep -E "duration_ms|error"

# Performance testing
ab -n 1000 -c 10 http://localhost:8003/health
locust -f tests/performance/locustfile.py --headless -u 100 -r 10 --run-time 5m

# Profiling
python -m cProfile -o output.prof services/data-api/src/main.py
python -m memory_profiler services/data-api/src/main.py
```
