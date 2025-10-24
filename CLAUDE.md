# CLAUDE.md - Essential Performance Guide for HomeIQ

**Last Updated:** October 24, 2025  
**Version:** 4.0.0  
**Purpose:** Essential performance patterns for AI assistants working on HomeIQ

---

## Core Performance Principles

1. **Measure First, Optimize Second** - Always profile before optimizing
2. **Async Everything** - Use `async/await` throughout Python services
3. **Batch Over Individual** - Batch database writes, API calls, event processing
4. **Cache Intelligently** - Cache expensive operations with appropriate TTLs
5. **Fail Fast, Recover Gracefully** - Use timeouts, retries, circuit breakers
6. **Memory Over CPU** - Use in-memory caching and data structures
7. **Profile Production Reality** - Test with real HA event volumes

## Critical Performance Patterns

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

### 2. Batch Processing Pattern

**Key Concepts:**
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

### 3. SQLite Optimization

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

### 4. InfluxDB Optimization

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
3. **Query Optimization** - Specific time range + field selection

### 5. FastAPI Best Practices

**Response Time Targets:**
- Health checks: <10ms
- Device/Entity queries: <10ms (SQLite)
- Event queries: <100ms (InfluxDB)
- AI operations: <5s (OpenAI API)

**Key Patterns:**
1. **Async Dependencies** - Use async database sessions
2. **Background Tasks** - Use FastAPI BackgroundTasks for slow operations
3. **Connection Pooling** - Reuse HTTP client sessions
4. **Correlation IDs** - Track requests across services

### 6. Caching Strategies

**TTL-based LRU Cache:**
```python
cache = WeatherCache(max_size=1000, default_ttl=300)  # 5 minutes
```

**Differentiated TTL Cache:**
```python
CACHE_TTLS = {
    "live_scores": 15,        # 15 seconds (game in progress)
    "recent_scores": 300,     # 5 minutes (game just ended)
    "fixtures": 3600,         # 1 hour (schedule data)
}
```

### 7. Frontend Performance Patterns

**Vite Build Optimization:**
- Code splitting with vendor chunk
- Hash naming for cache busting
- Multi-stage builds for smaller images

**React Performance Patterns:**
1. **Memoization** - useMemo for expensive calculations
2. **Lazy Loading** - Code splitting with Suspense
3. **Selective Subscriptions** - Subscribe to specific state slices
4. **Batch Updates** - Single state update instead of multiple

## Performance Targets

| Endpoint Type | Target | Acceptable | Investigation |
|---------------|--------|------------|---------------|
| Health checks | <10ms | <50ms | >100ms |
| Device queries | <10ms | <50ms | >100ms |
| Event queries | <100ms | <200ms | >500ms |
| Dashboard load | <2s | <5s | >10s |

## Common Anti-Patterns to Avoid

1. **Blocking the Event Loop** - Use aiohttp, not requests
2. **N+1 Database Queries** - Use eager loading
3. **Unbounded Queries** - Always use LIMIT clauses
4. **Not Using Connection Pooling** - Reuse HTTP sessions
5. **Inefficient Frontend Re-renders** - Use useMemo, selective subscriptions
6. **Logging Too Much** - Batch log statements
7. **Not Setting Timeouts** - Always configure timeouts

## Performance Monitoring

**Usage Pattern:**
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

## Detailed Documentation

For comprehensive performance guidance, see:
- [Performance Patterns Guide](docs/architecture/performance-patterns.md) - Detailed patterns and implementations
- [Performance Targets](docs/architecture/performance-targets.md) - SLAs and monitoring thresholds
- [Performance Anti-Patterns](docs/architecture/performance-anti-patterns.md) - What NOT to do
- [Performance Checklist](docs/architecture/performance-checklist.md) - Optimization checklist

---

**Remember:** Premature optimization is the root of all evil. Profile first, optimize second, test always.

**Document Metadata:**
- **Created:** October 23, 2025
- **Last Updated:** October 24, 2025
- **Version:** 4.0.0 (Essential patterns only)
- **Next Review:** Quarterly or after major architectural changes