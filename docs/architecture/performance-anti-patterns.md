# Performance Anti-Patterns

**Last Updated:** January 2025  
**Purpose:** Common performance anti-patterns to avoid in HomeIQ development  
**Target Platform:** Home Assistant single-home deployment on NUC (Next Unit of Computing)  
**Context7 Patterns:** Anti-patterns related to Context7 best practices

## Database Anti-Patterns

### Anti-Pattern 1: Blocking the Event Loop

**BAD:**
```python
import requests  # Synchronous library

@router.get("/weather")
async def get_weather():
    # BLOCKS all other requests for 500ms!
    response = requests.get("https://api.weather.com/...")
    return response.json()
```

**GOOD:**
```python
import aiohttp

@router.get("/weather")
async def get_weather():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.weather.com/...") as response:
            return await response.json()
```

### Anti-Pattern 2: N+1 Database Queries

**BAD:**
```python
# 1 query for devices + N queries for entities
devices = await session.execute(select(Device))
for device in devices:
    entities = await session.execute(
        select(Entity).where(Entity.device_id == device.id)
    )
    device.entities = entities.all()
```

**GOOD:**
```python
# 1 query with join
devices = await session.execute(
    select(Device).options(selectinload(Device.entities))
)
```

### Anti-Pattern 3: Unbounded Queries

**BAD:**
```python
@router.get("/events")
async def get_events():
    # Could return millions of rows!
    query = 'from(bucket: "events") |> range(start: 0)'
    return await influx_client.query(query)
```

**GOOD:**
```python
@router.get("/events")
async def get_events(
    start: datetime,
    end: datetime,
    limit: int = Query(100, ge=1, le=1000)
):
    # Bounded by time and count
    query = f'''
    from(bucket: "events")
        |> range(start: {start}, stop: {end})
        |> limit(n: {limit})
    '''
    return await influx_client.query(query)
```

### Anti-Pattern 4: Not Using Connection Pooling

**BAD:**
```python
async def fetch_weather():
    # New connection every time (TCP handshake + TLS)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

**GOOD:**
```python
# Module-level session (reused across requests)
http_session = None

async def get_http_session():
    global http_session
    if http_session is None:
        http_session = aiohttp.ClientSession()
    return http_session

async def fetch_weather():
    session = await get_http_session()
    async with session.get(url) as response:
        return await response.json()
```

## Frontend Anti-Patterns

### Anti-Pattern 5: Inefficient Re-renders

**BAD:**
```typescript
function Dashboard() {
  const [data, setData] = useState(null)

  // Fetches every render!
  const stats = calculateExpensiveStats(data)

  return <Display stats={stats} />
}
```

**GOOD:**
```typescript
function Dashboard() {
  const [data, setData] = useState(null)

  // Only recalculates when data changes
  const stats = useMemo(() => calculateExpensiveStats(data), [data])

  return <Display stats={stats} />
}
```

### Anti-Pattern 6: Not Using Selective Subscriptions

**BAD:**
```typescript
// Subscribe to entire store
const store = useSettingsStore()  // Re-renders on ANY change
```

**GOOD:**
```typescript
// Subscribe to specific slice
const darkMode = useSettingsStore((state) => state.darkMode)
```

### Anti-Pattern 7: Multiple State Updates

**BAD:**
```typescript
// Multiple updates trigger multiple re-renders
set({ services })
set({ health })
set({ metrics })
```

**GOOD:**
```typescript
// Single state update
set({ services, health, metrics })
```

## Caching Anti-Patterns

### Anti-Pattern 8: Cache without TTL

**BAD:**
```python
# Stale data forever
cache = {}

def get_data(key):
    if key not in cache:
        cache[key] = fetch_from_api(key)
    return cache[key]
```

**GOOD:**
```python
# TTL-based cache
cache = WeatherCache(max_size=1000, default_ttl=300)  # 5 minutes

async def get_data(key):
    data = await cache.get(key)
    if data is None:
        data = await fetch_from_api(key)
        await cache.put(key, data, ttl=300)
    return data
```

### Anti-Pattern 9: Cache Everything

**BAD:**
```python
# Memory bloat, low hit rate
cache = {}
for item in all_items:
    cache[item.id] = item  # Caching everything
```

**GOOD:**
```python
# Cache expensive operations only
cache = {}
for item in expensive_items:
    cache[item.id] = item  # Only cache what's expensive
```

### Anti-Pattern 10: Ignore Cache Statistics

**BAD:**
```python
# Can't optimize what you don't measure
cache = {}
# No monitoring of hit rates
```

**GOOD:**
```python
# Monitor hit rates
cache = WeatherCache(max_size=1000, default_ttl=300)
stats = cache.get_cache_statistics()
# {"hit_rate": 85.2, "current_size": 234, "evictions": 12}
```

## Event Processing Anti-Patterns

### Anti-Pattern 11: Individual Writes

**BAD:**
```python
# 1000x slower!
for event in events:
    write_api.write(bucket, record=event)
```

**GOOD:**
```python
# Batch writer
for event in events:
    await batch_writer.add_event(event)
# Flushes automatically at batch_size or timeout
```

### Anti-Pattern 12: Not Setting Timeouts

**BAD:**
```python
async with aiohttp.ClientSession() as session:
    # Hangs forever if API is down
    response = await session.get(url)
```

**GOOD:**
```python
async with aiohttp.ClientSession() as session:
    # Fails fast after 10 seconds
    response = await session.get(
        url,
        timeout=aiohttp.ClientTimeout(total=10)
    )
```

### Anti-Pattern 13: Logging Too Much

**BAD:**
```python
for event in events:
    logger.debug(f"Processing event {event}")  # 1000 log lines/sec!
    await process_event(event)
```

**GOOD:**
```python
logger.info(f"Processing batch of {len(events)} events")
for event in events:
    await process_event(event)
logger.info(f"Batch processing complete")
```

## Memory Management Anti-Patterns

### Anti-Pattern 14: Unbounded Queues

**BAD:**
```python
# Can grow indefinitely
self.recent_events = []
```

**GOOD:**
```python
# Automatically drops oldest
self.recent_events = deque(maxlen=1000)
```

### Anti-Pattern 15: Not Using Weak References

**BAD:**
```python
# Memory leaks
cache = {}
```

**GOOD:**
```python
# Auto-removes if no other refs
import weakref
cache = weakref.WeakValueDictionary()
```

## API Design Anti-Patterns

### Anti-Pattern 16: Synchronous Operations in Async Endpoints

**BAD:**
```python
@router.get("/bad")
async def bad_endpoint():
    result = requests.get("https://api.example.com")  # Blocks event loop!
```

**GOOD:**
```python
@router.get("/good")
async def good_endpoint():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com") as response:
            return await response.json()
```

### Anti-Pattern 17: Not Using Background Tasks

**BAD:**
```python
@router.post("/analyze")
async def analyze():
    # Blocks response for 5 seconds
    result = await run_ai_analysis()
    return {"result": result}
```

**GOOD:**
```python
@router.post("/analyze")
async def analyze(background_tasks: BackgroundTasks):
    # Return immediately
    background_tasks.add_task(run_ai_analysis)
    return {"status": "processing"}
```

### Anti-Pattern 18: Manual Validation

**BAD:**
```python
@router.get("/devices")
async def list_devices(limit: int = 100):
    if limit < 1 or limit > 1000:  # Redundant, error-prone
        raise ValueError(...)
```

**GOOD:**
```python
class DeviceQuery(BaseModel):
    limit: int = Field(100, ge=1, le=1000)  # Prevents abuse

@router.get("/devices")
async def list_devices(query: DeviceQuery = Depends()):
    # Already validated, type-safe
    pass
```

## Monitoring Anti-Patterns

### Anti-Pattern 19: Not Monitoring Performance

**BAD:**
```python
# No performance tracking
async def process_event(event):
    await do_work(event)
```

**GOOD:**
```python
# Performance monitoring
@metrics.timing_decorator("process_event")
async def process_event(event):
    await do_work(event)
```

### Anti-Pattern 20: Hard-coded Thresholds

**BAD:**
```python
# Hard-coded values
if response_time > 100:  # What if requirements change?
    alert("Slow response")
```

**GOOD:**
```python
# Configurable thresholds
if response_time > config.PERFORMANCE_THRESHOLD:
    alert("Slow response")
```

## Context7 Anti-Patterns

### Anti-Pattern 21: Using Deprecated FastAPI Event Handlers

**BAD:**
```python
# Deprecated pattern
@app.on_event("startup")
async def startup():
    initialize_services()

@app.on_event("shutdown")
async def shutdown():
    cleanup_services()
```

**GOOD:**
```python
# Context7 Pattern: Lifespan context manager
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    initialize_services()
    yield
    # Shutdown
    cleanup_services()

app = FastAPI(lifespan=lifespan)
```

### Anti-Pattern 22: Not Using Pydantic Settings Pattern

**BAD:**
```python
# Hard-coded or manual env var reading
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
```

**GOOD:**
```python
# Context7 Pattern: Pydantic settings
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    batch_size: int = 100
    batch_timeout: float = 5.0
    
    model_config = SettingsConfigDict(env_file=".env")

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

### Anti-Pattern 23: Missing Correlation IDs in Logging

**BAD:**
```python
# No correlation ID tracking
logger.info("Processing request")
```

**GOOD:**
```python
# Context7 Pattern: Structured logging with correlation IDs
from contextvars import ContextVar
from shared.logging_config import get_logger

correlation_id: ContextVar[str] = ContextVar('correlation_id', default=None)
logger = get_logger(__name__)

# Set at request start
correlation_id.set(request_id)

# Automatically included in structured logs
logger.info("Processing request", extra={"endpoint": "/api/events"})
```

### Anti-Pattern 24: Not Using Global State Setter Pattern

**BAD:**
```python
# Circular dependencies, hard to test
from services.metrics import MetricsCollector
metrics = MetricsCollector()
```

**GOOD:**
```python
# Context7 Pattern: Global state with setter
_metrics_collector = None

def set_metrics_collector(collector):
    global _metrics_collector
    _metrics_collector = collector

def get_metrics_collector():
    return _metrics_collector
```

## NUC-Specific Anti-Patterns

### Anti-Pattern 25: Over-Provisioning Memory

**BAD:**
```python
# Too much memory for NUC
PRAGMA cache_size=-128000  # 128MB (too large for NUC)
```

**GOOD:**
```python
# NUC-optimized memory
PRAGMA cache_size=-32000  # 32MB (appropriate for NUC)
```

### Anti-Pattern 26: Ignoring Single-Home Context

**BAD:**
```python
# Multi-tenant batch sizes
batch_size = 1000  # Too large for single-home
```

**GOOD:**
```python
# Single-home optimized
batch_size = 50-100  # Appropriate for single-home NUC
```

### Anti-Pattern 27: Not Monitoring NUC Resource Constraints

**BAD:**
```python
# No resource monitoring
async def process_events(events):
    await process(events)  # Could exhaust NUC resources
```

**GOOD:**
```python
# NUC resource-aware
import psutil

async def process_events(events):
    cpu_percent = psutil.cpu_percent(interval=1)
    if cpu_percent > 70:  # NUC threshold
        logger.warning("High CPU usage, throttling", extra={"cpu": cpu_percent})
        await asyncio.sleep(0.1)  # Throttle
    await process(events)
```

## Prevention Strategies

### Code Review Checklist
- [ ] No synchronous operations in async functions
- [ ] All database queries have LIMIT clauses
- [ ] Connection pooling used for external APIs
- [ ] Caching has appropriate TTLs
- [ ] Performance monitoring added to critical paths
- [ ] Timeouts configured for all external calls
- [ ] Batch operations used instead of loops
- [ ] Memory usage bounded (deque maxlen, cache size)
- [ ] Context7 patterns used (lifespan, Pydantic settings, correlation IDs)
- [ ] NUC resource constraints considered (memory, CPU limits)
- [ ] Single-home optimizations applied (batch sizes, event volumes)

### Automated Detection
- **Linting Rules:** ESLint rules for React performance
- **Static Analysis:** Python tools to detect blocking calls
- **Performance Tests:** Automated performance regression tests
- **Monitoring:** Real-time performance alerts

### Team Practices
- **Performance Reviews:** Regular performance code reviews
- **Training:** Team education on performance patterns
- **Documentation:** Clear performance guidelines
- **Testing:** Performance testing in CI/CD pipeline

## Quick Reference

### Red Flags to Watch For
- ❌ `requests` library in async code
- ❌ Database queries without LIMIT
- ❌ New HTTP sessions in loops
- ❌ Cache without TTL
- ❌ Unbounded data structures
- ❌ Missing timeouts
- ❌ Individual writes in loops
- ❌ Excessive logging
- ❌ Manual validation
- ❌ No performance monitoring
- ❌ `@app.on_event` instead of lifespan context manager (Context7)
- ❌ Missing Pydantic settings pattern (Context7)
- ❌ No correlation IDs in logging (Context7)
- ❌ Over-provisioning memory for NUC
- ❌ Multi-tenant batch sizes for single-home
- ❌ Ignoring NUC resource constraints

### Green Flags to Look For
- ✅ `aiohttp` for async HTTP
- ✅ Bounded queries with LIMIT
- ✅ Reused HTTP sessions
- ✅ TTL-based caching
- ✅ Bounded data structures (deque maxlen)
- ✅ Configured timeouts
- ✅ Batch operations
- ✅ Minimal, meaningful logging
- ✅ Pydantic validation
- ✅ Performance monitoring decorators
- ✅ Lifespan context managers (Context7)
- ✅ Pydantic settings with `@lru_cache` (Context7)
- ✅ Correlation IDs in structured logs (Context7)
- ✅ Global state with setter pattern (Context7)
- ✅ NUC-optimized memory settings
- ✅ Single-home batch sizes
- ✅ NUC resource monitoring
