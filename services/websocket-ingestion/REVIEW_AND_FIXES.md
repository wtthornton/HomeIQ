# WebSocket Ingestion Service - Deep Code Review & Fix Plan

**Service:** websocket-ingestion (Tier 1, Rank #1 - Mission Critical)
**Port:** 8001 | **Stack:** Python 3.12, FastAPI, aiohttp, InfluxDB Client
**Reviewed:** February 6, 2026
**Reviewer:** Claude Opus 4.6 Deep Review

---

## Executive Summary

The websocket-ingestion service is the **single most critical component** in the HomeIQ platform -- all Home Assistant event data flows through it. The architecture is fundamentally sound with good patterns (state machines, exponential backoff, batch processing, backpressure management). However, several reliability, performance, and security issues threaten data integrity in production.

**Health Score: 7.0/10**

| Metric | Score | Status |
|--------|-------|--------|
| **Architecture** | 8.0/10 | PASS - Good patterns, well-structured modules |
| **Reliability** | 6.5/10 | WARN - Silent data loss, race conditions |
| **Security** | 6.0/10 | WARN - Auth data in logs, Flux injection partially mitigated |
| **Performance** | 7.0/10 | PASS - Good batching, but triple-buffering concern |
| **Maintainability** | 6.5/10 | WARN - Major duplication in health_check.py |
| **Test Coverage** | 6.5/10 | WARN - Critical paths under-tested |
| **Overall** | 7.0/10 | PASS - Solid foundation with targeted fixes needed |

---

## CRITICAL Issues (Must Fix Immediately)

### CRIT-01: Silent Data Loss on InfluxDB Write Failure
**File:** `src/influxdb_batch_writer.py` **Lines:** 262-277
**Severity:** CRITICAL | **Type:** Data Loss / Reliability

When `_write_batch()` exhausts all retries, the batch is permanently lost. The `_process_batch_with_metrics()` method increments `total_points_failed` but the data is never retried, queued to a dead-letter store, or persisted for later recovery. For a Tier 1 service where every event matters, this is unacceptable.

```python
# influxdb_batch_writer.py:262-277
async def _process_batch_with_metrics(self, batch_to_process: list[Point]):
    # ...
    success = await self._write_batch(batch_to_process)
    # ...
    if success:
        self.total_batches_written += 1
        self.total_points_written += len(batch_to_process)
    else:
        self.total_points_failed += len(batch_to_process)
        # ^^^ Data is SILENTLY LOST here - no dead-letter queue, no persistence
```

**Impact:** Under InfluxDB outages or network issues, all events during the outage are permanently lost with no way to recover them.

**Fix:** Implement a dead-letter queue that persists failed batches to disk (the `EventQueue` class already has JSONL persistence support but is unused -- see CRIT-04). Failed batches should be written to a recovery file and retried on a background schedule.

---

### CRIT-02: ASYNCHRONOUS InfluxDB Write Mode with asyncio.to_thread Creates Triple-Buffering
**File:** `src/influxdb_wrapper.py` **Lines:** 129, 245-250
**Severity:** CRITICAL | **Type:** Performance / Reliability

The InfluxDB client is initialized with `ASYNCHRONOUS` write mode (line 129), which means the client itself manages an internal write buffer and background thread. Then `write_points()` wraps this in `asyncio.to_thread()` (line 245), adding another layer of async. Combined with `InfluxDBBatchWriter`'s own batching, this creates **triple-buffering**:

1. `InfluxDBBatchWriter.current_batch` (application-level batch)
2. `asyncio.to_thread()` (thread pool dispatch)
3. InfluxDB client ASYNCHRONOUS mode (client-internal buffer + background thread)

```python
# influxdb_wrapper.py:129 - Client uses ASYNCHRONOUS mode
self.write_api = self.client.write_api(write_options=ASYNCHRONOUS)

# influxdb_wrapper.py:245-250 - Then wrapped in asyncio.to_thread
await asyncio.to_thread(
    self.write_api.write,
    bucket=self.bucket,
    org=self.org,
    record=points
)
```

**Impact:**
- `asyncio.to_thread()` returns immediately because the ASYNCHRONOUS write API just queues internally
- The `write_points()` method returns `True` (success) before data is actually written to InfluxDB
- If the service crashes, data in the InfluxDB client's internal buffer is lost
- Error reporting is unreliable -- errors from the internal buffer are not propagated back

**Fix:** Change to `SYNCHRONOUS` write mode so that `asyncio.to_thread()` actually blocks until the write completes:
```python
self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
```

---

### CRIT-03: No Timeout on WebSocket Authentication Receives
**File:** `src/websocket_client.py` **Lines:** 130, 151
**Severity:** CRITICAL | **Type:** Reliability / Hang

The authentication flow calls `await self.websocket.receive()` twice with no timeout. If Home Assistant becomes unresponsive during auth, the service hangs indefinitely:

```python
# websocket_client.py:130 - No timeout
auth_required_msg = await self.websocket.receive()

# websocket_client.py:151 - No timeout
auth_result_msg = await self.websocket.receive()
```

**Impact:** The service can hang permanently during startup or reconnection if HA is slow or unresponsive during auth. Since this is a Tier 1 service, a hung connection blocks ALL event ingestion.

**Fix:** Add `asyncio.wait_for()` with a reasonable timeout:
```python
auth_required_msg = await asyncio.wait_for(
    self.websocket.receive(), timeout=30.0
)
```

---

### CRIT-04: EventQueue Initialized But Never Used in Data Pipeline
**File:** `src/main.py` **Line:** 181, `src/event_queue.py`
**Severity:** CRITICAL | **Type:** Architecture / Dead Code

`EventQueue` is instantiated in `main.py:181` with a 10,000 event capacity and has JSONL disk persistence support, but it is **never used** in the actual event pipeline. Events flow through:

```
WebSocket -> _on_event() -> BatchProcessor -> AsyncEventProcessor.event_queue -> Workers -> InfluxDBBatchWriter
```

The `EventQueue` instance at `self.event_queue` is a completely separate, disconnected component.

```python
# main.py:181 - Created but never used for event processing
self.event_queue = EventQueue(maxsize=10000)
```

**Impact:** The `EventQueue` has disk persistence capability that could solve CRIT-01 (silent data loss), but it is wasted. Meanwhile, the actual pipeline uses `AsyncEventProcessor`'s internal `asyncio.Queue` which has no persistence.

**Fix:** Either integrate `EventQueue` into the pipeline (replacing `AsyncEventProcessor`'s internal queue) to gain disk persistence, or remove it entirely to reduce confusion.

---

## HIGH Issues

### HIGH-01: Auth Data Logged at INFO Level
**File:** `src/websocket_client.py` **Lines:** 135, 152, 156
**Severity:** HIGH | **Type:** Security / Information Disclosure

While the token is masked on line 146 ("Sending auth message (token masked)"), the auth result and auth data are still logged verbatim:

```python
# Line 135 - Logs full parsed auth data
logger.info(f"Parsed auth data: {auth_data}")

# Line 152 - Logs full auth result message
logger.info(f"Received auth result: {auth_result_msg.data}")

# Line 156 - Logs parsed auth result
logger.info(f"Parsed auth result: {auth_result}")
```

The `auth_data` and `auth_result` may contain server version information, HA instance details, or other sensitive data that aids reconnaissance.

**Fix:** Reduce to DEBUG level and extract only safe fields:
```python
logger.debug(f"Auth data type: {auth_data.get('type')}")
logger.debug(f"Auth result type: {auth_result.get('type')}")
```

---

### HIGH-02: Listen Loop Can Spawn Duplicate Reconnect Tasks
**File:** `src/connection_manager.py` **Lines:** 350-376
**Severity:** HIGH | **Type:** Race Condition

When the listen loop encounters an error, it creates a new reconnect task (line 375) without checking if one already exists:

```python
# connection_manager.py:372-375
current_state = self.state_machine.get_state()
if current_state in [ConnectionState.RECONNECTING, ConnectionState.FAILED]:
    self.reconnect_task = asyncio.create_task(self._reconnect_loop())
    # ^^^ Overwrites previous reconnect_task without cancelling it
break
```

If a reconnect task is already running (from a previous disconnection or from `start()` line 149), this creates a **second** concurrent reconnect loop. The old task continues running but its reference is lost, making it uncancel-able.

**Fix:** Cancel the existing reconnect task before creating a new one:
```python
if self.reconnect_task and not self.reconnect_task.done():
    self.reconnect_task.cancel()
self.reconnect_task = asyncio.create_task(self._reconnect_loop())
```

---

### HIGH-03: Concurrent WebSocket Usage During Discovery
**File:** `src/connection_manager.py` **Lines:** 509-531
**Severity:** HIGH | **Type:** Race Condition

The `_on_connect()` method passes the WebSocket to discovery operations (line 526) while the listen loop is also reading from the same WebSocket (line 138, `_listen_loop`). Since `_on_connect()` is called from `websocket_client.py:109` (inside `connect()`, before the listen loop starts in `start()` line 138), the timing depends on the callback chain:

```python
# connection_manager.py:509 - Subscribes to events (sends WS messages)
await self._subscribe_to_events()

# connection_manager.py:526 - Passes WS to discovery (sends WS messages)
await self.discovery_service.discover_all(websocket=websocket_for_discovery)

# connection_manager.py:531 - Subscribes to registry events (sends WS messages)
await self.discovery_service.subscribe_to_device_registry_events(self.client.websocket)
```

The code comments on lines 517-518 acknowledge this: _"This may cause concurrency issues with event listening"_.

**Impact:** Message routing via `pending_responses` Futures may receive responses intended for other requests, or discovery responses may be misrouted to event handlers.

**Fix:** Add a WebSocket access semaphore, or ensure discovery completes fully before the listen loop starts. Since `_on_connect` runs before `listen_task` is created (line 138), the current ordering may actually be safe, but the callback from `main.py:431` (`discover_all` again) runs after the listen task starts, creating the actual race.

---

### HIGH-04: HealthResponse Model Missing `reason` Field
**File:** `src/api/models.py` **Lines:** 10-17
**Severity:** HIGH | **Type:** API Contract Mismatch

The `HealthResponse` Pydantic model does not include a `reason` field, but `health_check.py` sets `health_data["reason"]` in multiple places (lines 110, 113, 116, 123, 128, 231, 234, 237, 244, 249):

```python
# api/models.py:10-17
class HealthResponse(BaseModel):
    status: str
    service: str
    uptime: Optional[str] = None
    timestamp: str
    connection: Optional[Dict[str, Any]] = None
    subscription: Optional[Dict[str, Any]] = None
    # Missing: reason: Optional[str] = None
```

**Impact:** If the health endpoint uses this model for response serialization, the `reason` field will be silently stripped, hiding degradation reasons from monitoring.

**Fix:** Add `reason: Optional[str] = None` to `HealthResponse`.

---

### HIGH-05: Backpressure Drop Strategy Silently Loses Data Without Notification
**File:** `src/influxdb_batch_writer.py` **Lines:** 217-260
**Severity:** HIGH | **Type:** Observability / Data Loss

When backpressure triggers under `drop_oldest` strategy, data is silently dropped with only a WARNING log. No error callbacks are invoked, no metrics are emitted to InfluxDB, and no alerts are generated:

```python
# influxdb_batch_writer.py:227-236
if self.overflow_strategy == "drop_oldest":
    dropped = min(overflow, len(self.current_batch))
    self.dropped_points += dropped
    del self.current_batch[:dropped]
    logger.warning(
        "Backpressure triggered: dropped %s oldest points...", dropped, ...
    )
    return True  # No error callbacks invoked!
```

**Impact:** Data loss from backpressure is only visible in the statistics dict, not proactively alerted. The `error_callbacks` list exists but is never invoked during drops.

**Fix:** Invoke registered error callbacks when points are dropped, and consider emitting a metric point to InfluxDB to make drops visible in dashboards.

---

## MEDIUM Issues

### MED-01: Health Check Handler Has ~115 Lines of Duplicated Logic
**File:** `src/health_check.py` **Lines:** 29-148 vs 150-264
**Severity:** MEDIUM | **Type:** Code Duplication

The `handle()` (aiohttp) and `handle_fastapi()` methods are nearly identical -- ~115 lines of duplicated health data construction, subscription status calculation, event rate computation, and health determination logic. The only difference is the return type (`web.json_response()` vs `dict`).

**Fix:** Extract shared logic into a private `_build_health_data()` method:
```python
def _build_health_data(self) -> dict:
    # All shared logic here
    ...

async def handle(self, request):
    health_data = self._build_health_data()
    return web.json_response(health_data, status=200)

async def handle_fastapi(self):
    return self._build_health_data()
```

---

### MED-02: Historical Event Counter Uses `range(start: 0)` -- Full Table Scan
**File:** `src/historical_event_counter.py` **Lines:** 48-64
**Severity:** MEDIUM | **Type:** Performance

Both queries use `range(start: 0)` which scans ALL data from Unix epoch to now:

```python
# historical_event_counter.py:48-55
total_events_query = '''
    from(bucket: "home_assistant_events")
    |> range(start: 0)  # Scans ALL data from epoch!
    |> filter(fn: (r) => r._measurement == "home_assistant_events")
    |> count()
    |> group()
    |> sum(column: "_value")
'''
```

**Impact:** As the database grows, this query becomes increasingly expensive. With months of data at 100+ events/minute, this could take minutes to execute and strain InfluxDB during service startup.

**Fix:** Use a reasonable time range (e.g., `range(start: -365d)`) or maintain a running counter in a separate measurement that can be queried cheaply.

---

### MED-03: InfluxDB Schema Accesses Private Point Attributes
**File:** `src/influxdb_schema.py` **Lines:** 512, 517, 533
**Severity:** MEDIUM | **Type:** Fragile Coupling

The `validate_point()` method accesses private attributes `_name`, `_tags`, and `_fields` on InfluxDB `Point` objects:

```python
# influxdb_schema.py:512-533
measurement = point._name       # Private attribute
tags = point._tags              # Private attribute
fields = point._fields          # Private attribute
```

**Impact:** These private attributes can change in any minor version of the `influxdb-client` library without notice, causing validation to break silently (AttributeError caught by broad except).

**Fix:** Use the `Point.to_line_protocol()` method to serialize and parse, or check if the library provides public accessors.

---

### MED-04: `_add_event_fields` Stores Full Dict as String
**File:** `src/influxdb_schema.py` **Lines:** 331-336
**Severity:** MEDIUM | **Type:** Data Quality

When `event_data["new_state"]` is a dictionary (the full state object from HA), `str(state)` stores the Python dict representation as a string:

```python
# influxdb_schema.py:334-336
state = event_data.get("new_state")
if state is not None:
    point = point.field(self.FIELD_STATE, str(state))
    # If state is a dict like {"state": "on", "attributes": {...}, ...}
    # This stores "{'state': 'on', 'attributes': {...}}" as a string
```

**Impact:** The stored value is an unparseable Python repr string instead of the actual state value (e.g., "on", "off", "22.5"). Downstream consumers cannot easily extract the state.

**Fix:** Extract the actual state value:
```python
if isinstance(state, dict):
    point = point.field(self.FIELD_STATE, str(state.get("state", "")))
else:
    point = point.field(self.FIELD_STATE, str(state))
```

---

### MED-05: Error Handler Uses Broad String Matching for Categorization
**File:** `src/error_handler.py` **Lines:** 54-76
**Severity:** MEDIUM | **Type:** Incorrect Classification

The `categorize_error()` method uses keyword matching on error strings. The keyword `"invalid"` in the auth category (line 64) will match many non-auth errors:

```python
# error_handler.py:64
if any(keyword in error_str for keyword in ['auth', 'token', 'unauthorized', 'forbidden', 'invalid']):
    return ErrorCategory.AUTHENTICATION, ErrorSeverity.CRITICAL
```

For example, "invalid JSON format" or "invalid entity_id" would be categorized as AUTHENTICATION/CRITICAL, triggering inappropriate alerts.

**Fix:** Use more specific patterns or check exception types first:
```python
if any(keyword in error_str for keyword in ['auth', 'token', 'unauthorized', 'forbidden']):
    return ErrorCategory.AUTHENTICATION, ErrorSeverity.CRITICAL
if 'invalid' in error_str and any(k in error_str for k in ['auth', 'token', 'credential']):
    return ErrorCategory.AUTHENTICATION, ErrorSeverity.CRITICAL
```

---

### MED-06: MessageIDManager.get_next_id_sync() Is Not Thread-Safe
**File:** `src/message_id_manager.py` **Lines:** 57-84
**Severity:** MEDIUM | **Type:** Concurrency Bug

The `get_next_id_sync()` method has a code path (line 78) that increments the counter without any locking when the event loop is running:

```python
# message_id_manager.py:74-79
if loop.is_running():
    # For now, just increment (not thread-safe in sync context)
    # This is a fallback - prefer async usage
    self._counter += 1
    return self._counter
```

The code comment acknowledges this is not thread-safe. If called from multiple threads (e.g., via `asyncio.to_thread`), counter values could collide.

**Fix:** Use `threading.Lock` for the sync path, or raise an error forcing callers to use the async version.

---

### MED-07: InfluxDB Health Check Creates New aiohttp Sessions
**File:** `src/influxdb_wrapper.py` **Lines:** 154-170
**Severity:** MEDIUM | **Type:** Resource Leak / Performance

The `_test_connection()` method creates a new `aiohttp.ClientSession` every time it runs (every 60 seconds via the health check loop):

```python
# influxdb_wrapper.py:157
async with aiohttp.ClientSession() as session:
    async with session.get(f"{self.url}/health", ...) as response:
        ...
# Falls through to ANOTHER new session on failure:
async with aiohttp.ClientSession() as session:  # Line 167
    async with session.get(f"{self.url}/ping", ...) as response:
```

**Impact:** Creates up to 2 new TCP connections per health check (every 60s). Under heavy load, this creates unnecessary connection churn with InfluxDB.

**Fix:** Reuse a persistent session stored as an instance variable, or use the existing InfluxDB client's health method.

---

### MED-08: Three Separate Batching/Queueing Layers in Pipeline
**Severity:** MEDIUM | **Type:** Over-Engineering

The event processing pipeline has three distinct batching/queueing layers:

```
Event -> BatchProcessor (batch_size=50, timeout=5s)
      -> AsyncEventProcessor.event_queue (asyncio.Queue, 10 workers)
      -> InfluxDBBatchWriter.current_batch (batch_size=1000, timeout=5s)
      -> InfluxDB
```

Each layer adds latency, memory usage, and complexity. The `BatchProcessor` collects events into batches, then `_process_batch` feeds them one-by-one into `AsyncEventProcessor`, which has its own queue and worker pool, which eventually feeds processed events into `InfluxDBBatchWriter`.

**Impact:** Increased end-to-end latency (~10s+ in worst case from double timeouts), more complex failure reasoning, and harder debugging.

**Fix:** Consider collapsing `BatchProcessor` and `AsyncEventProcessor` into a single component. The worker pool pattern in `AsyncEventProcessor` already handles concurrency.

---

### MED-09: EventRateMonitor Holds Lock During O(n log n) Sort for Eviction
**File:** `src/event_rate_monitor.py` **Lines:** 61-68
**Severity:** MEDIUM | **Type:** Performance

When `events_by_entity` exceeds `_max_entity_entries` (10,000), it sorts the entire dict while holding the async lock:

```python
# event_rate_monitor.py:61-68 (inside async lock)
if len(self.events_by_entity) > self._max_entity_entries:
    sorted_entities = sorted(
        self.events_by_entity.items(), key=lambda x: x[1]
    )  # O(n log n) while holding lock
    entries_to_remove = ...
    for key, _ in sorted_entities[:entries_to_remove]:
        del self.events_by_entity[key]
```

**Impact:** At 10,000 entries, the sort takes a non-trivial amount of time while blocking all other `record_event()` calls. Since `record_event()` is called for every single HA event, this creates a latency spike.

**Fix:** Use an approximate eviction strategy (e.g., random sampling) or move eviction to a background task outside the lock.

---

## LOW Issues

### LOW-01: Excessive Emoji and Banner Logging in Production Code
**Files:** `src/connection_manager.py`, `src/discovery_service.py`, `src/event_subscription.py`
**Severity:** LOW | **Type:** Maintainability

Extensive use of emoji characters and `"=" * 80` banner logging throughout the codebase:

```python
logger.info("=" * 80)
logger.info("CONNECTED TO HOME ASSISTANT")
logger.info("=" * 80)
logger.info("Preparing to subscribe to events...")
logger.info("All prerequisites met, waiting 1 second before subscribing...")
```

**Impact:** Makes logs harder to parse with log aggregation tools (ELK, Loki). Banner lines waste log storage.

**Fix:** Use structured logging with key-value pairs instead of banner formatting. Reserve emoji for development/debug only.

---

### LOW-02: EventQueue Has Unused Disk Persistence Feature
**File:** `src/event_queue.py`
**Severity:** LOW | **Type:** Dead Feature

`EventQueue` implements JSONL-based disk persistence, but since the queue itself is unused (CRIT-04), this feature is also unused. This is a missed opportunity -- the persistence code could serve as the dead-letter queue for CRIT-01.

---

### LOW-03: Empty ServiceContainer
**File:** `src/service_container.py`
**Severity:** LOW | **Type:** Dead Code

`ServiceContainer` extends `BaseServiceContainer` but adds nothing. It exists as a placeholder for a dependency injection pattern that is not used.

---

### LOW-04: Inline Import of InfluxDBBatchWriter
**File:** `src/main.py` **Line:** 237
**Severity:** LOW | **Type:** Style

```python
# main.py:237 - Inline import
from .influxdb_batch_writer import InfluxDBBatchWriter
```

Should be at module level with other imports for clarity.

---

### LOW-05: requirements-prod.txt Has Stale Version Pins
**File:** `requirements-prod.txt`
**Severity:** LOW | **Type:** Dependency Management

`requirements-prod.txt` (used by Docker) has older version ranges than `requirements.txt`:

| Package | requirements.txt | requirements-prod.txt |
|---------|-----------------|----------------------|
| fastapi | `>=0.128.0,<0.129.0` | `>=0.115.0,<1.0.0` |
| aiohttp | `>=3.13.3,<4.0.0` | `>=3.13.2,<4.0.0` |
| pydantic | `>=2.12.5,<3.0.0` | `>=2.9.0,<3.0.0` |
| psutil | `>=7.2.1,<8.0.0` | `>=5.9.0,<6.0.0` |

Also, `requirements-prod.txt` includes `asyncio-mqtt>=0.16.0,<1.0.0` which is not used anywhere in the websocket-ingestion source code.

**Fix:** Align version pins and remove unused `asyncio-mqtt` dependency.

---

## Security Audit

### SEC-01: Flux Query Injection (Partially Mitigated)
**File:** `src/influxdb_wrapper.py` **Lines:** 476-542
**Status:** PARTIALLY FIXED

The `_sanitize_flux_value()` method (line 476) escapes backslashes and double quotes. The `query_devices()` and `query_entities()` methods now use this sanitizer (lines 502-506, 534-538). However:

1. The `bucket` parameter in `query_devices()` and `query_entities()` is still interpolated directly (lines 494, 527): `from(bucket: "{bucket}")`
2. The sanitizer only handles `\` and `"` -- it does not handle Flux-specific injection vectors like `)` or `|>`

**Residual Risk:** LOW (bucket names are typically controlled by the application, not user input).

### SEC-02: CORS Configuration (Fixed)
**File:** `src/api/app.py` **Lines:** 53-60
**Status:** FIXED

CORS is now configured via `CORS_ALLOWED_ORIGINS` environment variable with a safe default of `http://localhost:3000`. Methods and headers are restricted.

### SEC-03: Discovery Service Token Logging
**File:** `src/discovery_service.py` **Line:** 277
**Status:** MOSTLY FIXED

Token is now masked showing only last 4 characters:
```python
logger.info(f"Using token: ***{ha_token[-4:]}" if ha_token else "No token!")
```

This is a reasonable approach. Residual risk is minimal.

### SEC-04: SSL Verification Configurable
**File:** `src/discovery_service.py` **Lines:** 286-289
**Status:** ACCEPTABLE

SSL verification is configurable via `SSL_VERIFY` env var, defaulting to `true`. This is appropriate for local/internal network deployments.

### SEC-05: No Input Validation on HA WebSocket Path
**Severity:** LOW
**Status:** INFORMATIONAL

The ingestion path from Home Assistant has no message validation beyond JSON parsing. The `security.py` rate limiter and message validation are only applied to the client-facing `/ws` endpoint (Epic 50), not to the HA ingestion path. This is by design -- HA is a trusted source -- but should be documented.

---

## Performance Analysis

### Bottleneck Identification

| Component | Throughput | Bottleneck | Severity |
|-----------|-----------|------------|----------|
| **WebSocket Receive** | ~1000 events/sec | Single connection, no parallelism | LOW |
| **BatchProcessor** | Configurable (50 events, 5s) | Timeout adds latency | MEDIUM |
| **AsyncEventProcessor** | 10 workers, 1000/sec rate limit | Rate limiter contention | MEDIUM |
| **InfluxDBBatchWriter** | 1000 points/batch, 5s timeout | Triple-buffering (CRIT-02) | HIGH |
| **EventRateMonitor** | Lock on every event | O(n log n) eviction sort | MEDIUM |
| **Historical Counter** | One-time at startup | Full table scan (MED-02) | LOW |

### Event Pipeline Latency Analysis

Best case (batch full): ~0ms (immediate flush)
Typical case: BatchProcessor timeout (5s) + InfluxDBBatchWriter timeout (5s) = **~10 seconds**
Worst case with backpressure: Up to 15+ seconds

### Memory Footprint

- `EventRateMonitor.event_timestamps`: bounded by `maxlen=window_size_minutes * 200` = 12,000 entries at default -- GOOD
- `EventRateMonitor.events_by_entity`: bounded by `_max_entity_entries=10,000` with eviction -- GOOD
- `InfluxDBBatchWriter.current_batch`: bounded by `max_pending_points=20,000` -- GOOD
- `AsyncEventProcessor.event_queue`: bounded by `maxsize=10,000` -- GOOD
- `MemoryManager`: monitors RSS via psutil with configurable threshold -- GOOD

---

## Architecture Review

### Module Coupling Diagram

```
main.py (WebSocketIngestionService)
  |
  +-- ConnectionManager
  |     +-- HomeAssistantWebSocketClient (WebSocket connection)
  |     +-- ConnectionStateMachine (state management)
  |     +-- EventSubscriptionManager (HA event subscriptions)
  |     +-- DiscoveryService (device/entity/area discovery)
  |     +-- EventProcessor (event validation & enrichment)
  |     +-- EventRateMonitor (rate tracking)
  |     +-- ErrorHandler (error categorization)
  |
  +-- BatchProcessor (event batching)
  +-- AsyncEventProcessor (worker pool)
  |     +-- ProcessingStateMachine
  |     +-- RateLimiter (token bucket)
  |
  +-- InfluxDBBatchWriter (InfluxDB batching)
  |     +-- InfluxDBConnectionManager (InfluxDB client)
  |     +-- InfluxDBSchema (point creation/validation)
  |
  +-- MemoryManager (RSS monitoring)
  +-- HistoricalEventCounter (startup totals)
  +-- EventQueue (UNUSED)
  +-- HealthCheckHandler (health endpoint)
  +-- FastAPI app (REST API)
```

### Strengths
- Clear separation of concerns between connection management, event processing, and storage
- State machine pattern for both connection and processing lifecycle
- Exponential backoff with jitter for reconnection (prevents thundering herd)
- Backpressure management with configurable overflow strategies
- Entity filtering (Epic 45.2) for selective event capture
- Circuit breaker pattern in HTTP client for enrichment service
- Non-root Docker user with multi-stage build

### Weaknesses
- Three separate batching layers add unnecessary complexity (MED-08)
- EventQueue class is completely disconnected from pipeline (CRIT-04)
- Discovery runs both from `ConnectionManager._on_connect()` (line 526) and `main.py._on_connect()` (line 431)
- Shared path resolution is duplicated between `main.py` and `state_machine.py`

---

## Test Coverage Gap Analysis

### Test File Inventory

33 test files found in `services/websocket-ingestion/tests/`. Key coverage:

| Component | Test File | Coverage Quality |
|-----------|-----------|-----------------|
| BatchProcessor | `test_batch_processor.py` | **Excellent** - lifecycle, handlers, errors, config |
| InfluxDBBatchWriter | `test_influxdb_batch_writer.py` | **Basic** - only backpressure tests |
| Main Service | `test_main_service.py` | **Good** - init, start/stop, callbacks, writes |
| EventProcessor | `test_event_processor.py` | Present |
| ConnectionManager | `test_connection_manager.py` | Present |
| DiscoveryService | `test_discovery_service.py` | Present |
| WebSocketClient | `test_websocket_client.py` | Present |

### Critical Test Gaps

1. **No test for InfluxDB write failure recovery** - The write path in `InfluxDBBatchWriter._write_batch()` (retry logic, error propagation) has no tests. Only backpressure (`drop_oldest`, `drop_new`) is tested.

2. **No test for double-discovery trigger** - When `ConnectionManager._on_connect()` triggers discovery AND `main.py._on_connect()` triggers discovery again, there is no test verifying idempotency.

3. **No integration test for full pipeline** - No end-to-end test covering: WebSocket event -> EventProcessor -> BatchProcessor -> AsyncEventProcessor -> InfluxDBBatchWriter -> InfluxDB mock.

4. **No test for authentication timeout** - CRIT-03 (no timeout on auth receives) has no test verifying behavior when auth hangs.

5. **No test for concurrent WebSocket access** - HIGH-03 (discovery + listen loop using same WebSocket) has no test for message routing correctness.

6. **No test for `EventRateMonitor` eviction behavior** - MED-09 (O(n log n) sort under lock) has no test for performance under high entity counts.

7. **No test for `HistoricalEventCounter` with large datasets** - MED-02 (`range(start: 0)`) has no test for query performance.

---

## Docker & Deployment Review

### Dockerfile Analysis
**File:** `Dockerfile`

**Strengths:**
- Multi-stage Alpine build (small image)
- Non-root user (`appuser:appgroup`, UID/GID 1001)
- Health check with curl (`HEALTHCHECK --interval=30s`)
- Pip cache mount for build optimization
- CA certificates installed for TLS

**Issues:**

1. **`requirements-prod.txt` has stale versions** (LOW-05) - The Docker build uses `requirements-prod.txt` which has older/looser version pins than `requirements.txt`. This means Docker images may have different dependency versions than development.

2. **Unused `asyncio-mqtt` in prod requirements** - `requirements-prod.txt` includes `asyncio-mqtt` which is not used by this service, adding ~2MB to the image.

3. **Health check port matches EXPOSE** - EXPOSE 8001 and health check uses `localhost:8001` -- consistent. GOOD.

4. **No signal handling** - `CMD ["python", "-m", "src.main"]` -- should verify the service handles SIGTERM for graceful shutdown.

---

## Fix Priority & Effort Matrix

| ID | Issue | Priority | Effort | Impact |
|----|-------|----------|--------|--------|
| CRIT-02 | ASYNCHRONOUS InfluxDB mode | P0 | 5min | Data integrity |
| CRIT-03 | No auth timeout | P0 | 10min | Service hang |
| HIGH-01 | Auth data in logs | P0 | 10min | Security |
| CRIT-01 | Silent data loss | P1 | 2hr | Data loss |
| HIGH-02 | Duplicate reconnect tasks | P1 | 15min | Reliability |
| HIGH-04 | Missing HealthResponse.reason | P1 | 5min | API contract |
| HIGH-05 | No callbacks on backpressure drop | P1 | 30min | Observability |
| MED-01 | Health check duplication | P2 | 30min | Maintainability |
| MED-02 | Full table scan at startup | P2 | 15min | Performance |
| MED-04 | Dict stored as string | P2 | 15min | Data quality |
| MED-05 | Broad error categorization | P2 | 20min | Reliability |
| MED-06 | MessageID not thread-safe | P2 | 10min | Concurrency |
| MED-07 | Health check session creation | P2 | 15min | Resources |
| MED-08 | Triple batching layers | P3 | 4hr | Architecture |
| MED-09 | Lock during sort | P3 | 30min | Performance |
| CRIT-04 | Unused EventQueue | P3 | 1hr | Architecture |
| HIGH-03 | Concurrent WS during discovery | P3 | 2hr | Race condition |
| MED-03 | Private Point attributes | P3 | 1hr | Fragile coupling |
| LOW-01 | Emoji logging | P4 | 1hr | Maintainability |
| LOW-05 | Stale prod requirements | P4 | 15min | Dependencies |

---

## Recommended Fix Phases

### Phase 1: Immediate (This Sprint - ~2 hours)
1. **CRIT-02**: Change `ASYNCHRONOUS` to `SYNCHRONOUS` in `influxdb_wrapper.py:129`
2. **CRIT-03**: Add `asyncio.wait_for()` timeout to auth receives in `websocket_client.py`
3. **HIGH-01**: Reduce auth logging to DEBUG with safe field extraction in `websocket_client.py`
4. **HIGH-02**: Add reconnect task cancellation guard in `connection_manager.py:375`
5. **HIGH-04**: Add `reason` field to `HealthResponse` in `api/models.py`

### Phase 2: Short-Term (Next 2 Sprints - ~6 hours)
1. **CRIT-01**: Implement dead-letter queue using `EventQueue`'s disk persistence
2. **HIGH-05**: Wire backpressure drops to error callbacks
3. **MED-01**: Extract shared health check logic
4. **MED-02**: Limit historical query range
5. **MED-04**: Fix state field extraction in schema
6. **MED-05**: Improve error categorization specificity

### Phase 3: Medium-Term (Backlog - ~10 hours)
1. **CRIT-04/MED-08**: Integrate EventQueue into pipeline or simplify batching layers
2. **HIGH-03**: Add WebSocket access coordination for discovery
3. **MED-03**: Replace private Point attribute access
4. **MED-09**: Optimize EventRateMonitor eviction
5. Add missing test coverage for write failures, auth timeout, full pipeline

---

## Summary

The websocket-ingestion service has a **solid architectural foundation** with well-implemented state machines, batching, backpressure, and reconnection patterns. The code is well-organized across focused modules.

The most urgent fixes are:
1. **Switch InfluxDB to SYNCHRONOUS mode** (CRIT-02) -- the current ASYNCHRONOUS mode with `asyncio.to_thread` means write success/failure reporting is unreliable
2. **Add authentication timeouts** (CRIT-03) -- a hung HA server can permanently block the service
3. **Stop logging auth data** (HIGH-01) -- auth responses are logged at INFO level
4. **Implement data loss recovery** (CRIT-01) -- failed batches are permanently lost

These four fixes would bring the health score from 7.0 to approximately 8.0-8.5/10.
