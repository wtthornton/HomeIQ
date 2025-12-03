# Performance Guide (Optimized)

**Last Updated:** December 2025  
**Purpose:** Core performance patterns and anti-patterns for HomeIQ  
**Target:** NUC single-home deployment  
**Full Details:** See `performance-patterns.md` and `performance-anti-patterns.md` for complete examples

## Core Principles

1. **Measure First** - Profile before optimizing
2. **Async Everything** - Use `async/await` throughout
3. **Batch Operations** - Batch DB writes, API calls, events
4. **Cache Intelligently** - TTL-based caching
5. **Fail Fast** - Timeouts, retries, circuit breakers
6. **Memory Over CPU** - In-memory caching (NUC constraint)
7. **Resource-Aware** - Optimize for NUC (2-4 cores, 4-16GB RAM)
8. **Single-Home** - Scale for 1 home, not multi-tenant

## Key Patterns

### Hybrid Database (5-10x Speedup)
- **InfluxDB**: Time-series events, metrics, historical queries
- **SQLite**: Metadata (devices, entities, webhooks) - <10ms queries
- **Impact**: Device queries 50ms → <10ms

### Event-Driven Architecture
- **Pattern**: HA Event → WebSocket → Batch Queue → InfluxDB → Webhook Detection
- **Impact**: Webhook push (zero overhead) vs polling (30s overhead)

### Batch Processing
- **Size**: 100 events per batch (NUC: 50-100)
- **Timeout**: 5s (NUC: 3-5s)
- **Impact**: 10-100x faster than individual writes

### Caching Strategy
- **TTL-based**: Weather (5min), Sports (15s-1h), Devices (direct DB)
- **LRU eviction**: Prevent unbounded growth
- **Hit rate target**: 85%+

## Critical Anti-Patterns

### ❌ Blocking Event Loop
- **BAD**: `requests` in async functions
- **GOOD**: `aiohttp` for async HTTP

### ❌ N+1 Queries
- **BAD**: Loop with individual queries
- **GOOD**: Eager loading with `selectinload()`

### ❌ Unbounded Queries
- **BAD**: Queries without LIMIT
- **GOOD**: Always use LIMIT + time range

### ❌ No Connection Pooling
- **BAD**: New session per request
- **GOOD**: Reuse HTTP/database sessions

### ❌ Individual Writes
- **BAD**: Loop with individual writes
- **GOOD**: Batch writer with auto-flush

### ❌ Missing Timeouts
- **BAD**: Hangs forever if API down
- **GOOD**: `timeout=aiohttp.ClientTimeout(total=10)`

### ❌ Excessive Logging
- **BAD**: Log every event (1000 lines/sec)
- **GOOD**: Batch logging, structured JSON

## Database Optimization

### SQLite (NUC-Optimized)
```python
PRAGMA journal_mode=WAL          # Writers don't block readers
PRAGMA synchronous=NORMAL        # Fast writes
PRAGMA cache_size=-32000         # 32MB (NUC)
PRAGMA temp_store=MEMORY         # Fast temp tables
PRAGMA busy_timeout=30000        # 30s lock wait
```

### InfluxDB (NUC-Optimized)
```python
batch_size = 500          # Smaller for NUC (vs 1000)
batch_timeout = 3.0       # Faster flush (vs 5.0)
```

## API Performance (FastAPI)

### Context7 Patterns
- **Lifespan Context Managers**: `@asynccontextmanager` for startup/shutdown
- **Pydantic Settings**: Type-validated config with `@lru_cache`
- **Global State Setter**: Context7 pattern for telemetry
- **Correlation IDs**: Structured logging with request tracking

### Response Targets (NUC)
- Health checks: <10ms
- Device queries: <10ms (SQLite)
- Event queries: <100ms (InfluxDB)
- Dashboard load: <2s
- AI operations: <5s

## Frontend Optimization

- **Code Splitting**: Vendor chunk separation
- **Memoization**: `useMemo` for expensive calculations
- **Selective Subscriptions**: Zustand slice subscriptions
- **Lazy Loading**: Components on demand
- **Debouncing**: Search inputs

## NUC Resource Limits

- **CPU per service**: <30% normal, <60% peak
- **Memory per service**: <60% of limit
- **Total system memory**: <80% available
- **SQLite cache**: 32MB max (vs 64MB larger systems)
- **InfluxDB memory**: 256MB max (vs 400MB larger systems)

## Monitoring

### Key Metrics
- Throughput: requests/min, events/min, batch_size
- Latency: response_time_ms, query_duration_ms
- Resources: cpu_percent, memory_mb, queue_size
- Errors: error_count, retry_count, error_rate

### Context7 Telemetry
- Structured logging with correlation IDs
- Metrics collection via `metrics_collector.py`
- Request tracing across services

## Quick Reference

### Red Flags
- ❌ `requests` in async code
- ❌ Queries without LIMIT
- ❌ New sessions in loops
- ❌ Cache without TTL
- ❌ Unbounded data structures
- ❌ Missing timeouts
- ❌ `@app.on_event` (use lifespan instead)

### Green Flags
- ✅ `aiohttp` for async HTTP
- ✅ Bounded queries with LIMIT
- ✅ Reused sessions
- ✅ TTL-based caching
- ✅ Bounded structures (deque maxlen)
- ✅ Configured timeouts
- ✅ Lifespan context managers
- ✅ Pydantic settings pattern
- ✅ Correlation IDs

**For detailed examples and complete patterns, see:**
- `performance-patterns.md` - Full pattern details with examples
- `performance-anti-patterns.md` - Complete anti-pattern examples
- `performance-checklist.md` - Optimization checklist

