# Energy Correlator Service - Deep Code Review

**Service:** energy-correlator (Port 8017, Tier 2)
**Review Date:** February 6, 2026
**Reviewer:** Claude Opus 4.6 (automated deep code review)
**Files Reviewed:** 6 source files, 9 test files, 5 config files (20 files total)

---

## Executive Summary

**Overall Health Score: 7.0 / 10**

The energy-correlator service is a well-structured microservice with solid architecture for correlating Home Assistant device events with power consumption changes. It demonstrates good separation of concerns, meaningful use of async patterns, and a comprehensive test suite. However, several security issues (Flux injection), performance concerns (fallback N+1 queries), and test quality gaps reduce the score. The codebase shows evidence of thoughtful Epic 48 improvements (DeferredEvent dataclass, retry queue monitoring, configurable retry intervals) but has unresolved issues that could impact production reliability.

**Strengths:**
- Clean separation: main.py (service), correlator.py (logic), influxdb_wrapper.py (data), security.py (validation)
- Good use of dataclasses (DeferredEvent) for memory efficiency
- Power cache with bisect-based lookup is an excellent optimization
- Comprehensive test suite (9 test files across unit and integration)
- Proper async/await patterns with `asyncio.to_thread` for blocking InfluxDB calls
- Configurable parameters via environment variables with sensible defaults
- Multi-stage Docker build with non-root user

**Weaknesses:**
- Critical Flux injection vulnerability in all InfluxDB queries
- Fallback power query (N+1 pattern) when cache miss occurs
- Health endpoint always reports "healthy" regardless of failure state
- Tests use deprecated `datetime.utcnow()` and have several assertion gaps
- ASYNCHRONOUS write API used with `asyncio.to_thread` is redundant/conflicting
- IPv6 address parsing broken in security module
- `logger` module-level monkey-patching pattern is fragile

---

## Critical Issues (Must Fix)

### C1. Flux Injection Vulnerability in All InfluxDB Queries

**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\correlator.py`, lines 219-234, 357-364, 553-559
**Severity:** CRITICAL
**Impact:** An attacker who can control entity names, bucket names, or time values could inject arbitrary Flux query code.

The bucket name is validated at startup via `validate_bucket_name()`, but the Flux queries use f-string interpolation directly. While the bucket is validated, the `start_time.isoformat()` and `now.isoformat()` values are derived from datetime objects (safe), the pattern itself is dangerous and should use parameterized queries for defense-in-depth.

More critically, if any event data (entity_id, domain) were ever used in queries (currently they are not, but the pattern invites it), it would be exploitable.

**Current Code (correlator.py line 219):**
```python
flux_query = f'''
from(bucket: "{self.influxdb_bucket}")
  |> range(start: {start_time.isoformat()}Z, stop: {now.isoformat()}Z)
  |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
  ...
'''
```

**Recommended Fix:**
```python
# Use the InfluxDB client's parameterized query support
flux_query = '''
from(bucket: bucket_name)
  |> range(start: start_time, stop: stop_time)
  |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
  ...
'''
params = {
    "bucket_name": self.influxdb_bucket,
    "start_time": start_time,
    "stop_time": now,
}
# Pass params to query_api.query()
```

Note: The influxdb-client Python library supports parameterized Flux queries via `query_api.query(query, params=params)`. If parameterized queries are not available for all Flux functions, at minimum add explicit sanitization for any interpolated value.

---

### C2. Health Endpoint Always Reports "healthy"

**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\health_check.py`, line 29
**Severity:** CRITICAL
**Impact:** Load balancers and orchestrators relying on `/health` will never know the service is degraded or unhealthy, defeating the purpose of the health check.

**Current Code:**
```python
health_data = {
    "status": "healthy",  # Always "healthy" regardless of error state
    ...
}
```

**Recommended Fix:**
```python
async def handle(self, request: web.Request) -> web.Response:
    uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
    success_rate = (
        1.0 if self.total_fetches == 0
        else (self.total_fetches - self.failed_fetches) / self.total_fetches
    )

    # Determine status based on success rate and recency
    if self.total_fetches == 0 and uptime < 120:
        status = "starting"
    elif success_rate < 0.5:
        status = "unhealthy"
    elif success_rate < 0.9:
        status = "degraded"
    else:
        status = "healthy"

    # Also check staleness - if last success was too long ago
    if self.last_successful_fetch:
        seconds_since_success = (
            datetime.now(timezone.utc) - self.last_successful_fetch
        ).total_seconds()
        if seconds_since_success > 300:  # 5 minutes with no success
            status = "unhealthy"

    health_data = {
        "status": status,
        ...
    }

    status_code = 200 if status in ("healthy", "starting") else 503
    return web.json_response(health_data, status=status_code)
```

---

### C3. ASYNCHRONOUS Write API Conflicting with asyncio.to_thread

**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\influxdb_wrapper.py`, lines 43, 94-99, 101-118
**Severity:** CRITICAL
**Impact:** The `ASYNCHRONOUS` write option creates a background thread pool for writes within the InfluxDB client, while `asyncio.to_thread` creates another thread. This double-threading means write errors are silently swallowed (the ASYNCHRONOUS API uses callbacks for error handling, which are not wired up), and `write_points` may return before the write actually completes.

**Current Code:**
```python
self.write_api = self.client.write_api(write_options=ASYNCHRONOUS)

def _write_points_blocking(self, points):
    self.write_api.write(...)  # Returns immediately due to ASYNCHRONOUS

async def write_points(self, points):
    await asyncio.to_thread(self._write_points_blocking, points)
    # This returns immediately - write hasn't actually completed
```

**Recommended Fix:**
```python
from influxdb_client.client.write_api import SYNCHRONOUS

self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

def _write_points_blocking(self, points):
    self.write_api.write(
        bucket=self.influxdb_bucket,
        org=self.influxdb_org,
        record=points
    )
    # Now this blocks until write completes or raises an error

async def write_points(self, points):
    if not points:
        return
    try:
        await asyncio.to_thread(self._write_points_blocking, points)
    except ApiException as e:
        logger.exception(f"InfluxDB API error writing points: {e}")
        raise
```

Using `SYNCHRONOUS` with `asyncio.to_thread` gives true async behavior while ensuring write errors are properly propagated.

---

## High Priority Issues

### H1. N+1 Query Pattern on Power Cache Miss

**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\correlator.py`, lines 335-378
**Severity:** HIGH
**Impact:** When the power cache does not contain data for a given time (cache miss), `_get_power_at_time` falls through to execute a direct InfluxDB query. In a batch of N events where all have cache misses, this creates N individual queries to InfluxDB, negating the entire cache optimization.

**Current Code:**
```python
async def _get_power_at_time(self, target_time):
    if self._power_cache:
        cached_value = self._lookup_power_in_cache(target_time, self._power_cache)
        if cached_value is not None:
            return cached_value

    # Fallback: individual query per event - N+1 problem
    flux_query = f'''
    from(bucket: "{self.influxdb_bucket}")
      |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
      ...
    '''
    results = await self.client.query(flux_query)
```

**Recommended Fix:**
When operating in batch mode (inside `process_recent_events`), cache misses should return `None` without fallback queries. The fallback is only appropriate for one-off lookups outside the batch flow.

```python
async def _get_power_at_time(
    self, target_time: datetime, *, allow_fallback: bool = True
) -> float | None:
    if self._power_cache:
        cached_value = self._lookup_power_in_cache(target_time, self._power_cache)
        if cached_value is not None:
            return cached_value

    if not allow_fallback:
        return None  # In batch mode, rely solely on cache

    # Only run individual query when not in batch processing
    ...
```

Then in `_correlate_event_with_power`, pass `allow_fallback=False` when called from `process_recent_events` (the batch path).

---

### H2. IPv6 Address Parsing Broken in Security Module

**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\security.py`, lines 74-75
**Severity:** HIGH
**Impact:** IPv6 addresses contain colons. The naive `peername.split(':')[0]` approach will incorrectly parse IPv6 addresses like `::1` or `fe80::1%eth0:54321`, breaking internal network validation for any IPv6 traffic.

**Current Code:**
```python
if ':' in peername:
    peername = peername.split(':')[0]
```

**Recommended Fix:**
```python
# Handle IPv6 addresses properly
if peername.startswith('['):
    # IPv6 with port: [::1]:54321
    bracket_end = peername.find(']')
    if bracket_end != -1:
        peername = peername[1:bracket_end]
elif peername.count(':') == 1:
    # IPv4 with port: 192.168.1.1:54321
    peername = peername.split(':')[0]
# else: bare IPv6 address (no port) or bare IPv4 - use as-is
```

Additionally, add IPv6 loopback to default networks:
```python
default_networks = [
    '127.0.0.1/32', '::1/128',
    '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16',
    'fe80::/10'  # Link-local
]
```

---

### H3. No Validation of Non-Numeric Environment Variables

**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\main.py`, lines 49-58
**Severity:** HIGH
**Impact:** If `PROCESSING_INTERVAL`, `LOOKBACK_MINUTES`, or other numeric env vars contain non-numeric values (e.g., a typo like `60s`), the service will crash with an unhelpful `ValueError` from `int()` with no indication of which variable was invalid.

**Current Code:**
```python
self.processing_interval = int(os.getenv('PROCESSING_INTERVAL', '60'))
```

**Recommended Fix:**
```python
def _parse_int_env(name: str, default: int, min_val: int | None = None) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid value for {name}: '{raw}'. Must be an integer."
        )
    if min_val is not None and value < min_val:
        raise ValueError(
            f"Invalid value for {name}: {value}. Must be >= {min_val}."
        )
    return value

self.processing_interval = _parse_int_env('PROCESSING_INTERVAL', 60, min_val=1)
self.lookback_minutes = _parse_int_env('LOOKBACK_MINUTES', 5, min_val=1)
```

---

### H4. Logger Monkey-Patching Pattern is Fragile

**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\main.py`, lines 28-29
**Severity:** HIGH
**Impact:** The pattern `security_module.logger = logger` overwrites the module-level `logger` attribute. But `security.py` does not define a `logger` variable at all -- there is no `logger = logging.getLogger(...)` in security.py. This means the assignment creates a new attribute that is never used, since `security.py` does not reference any `logger`. If someone later adds logging to security.py using a module-level `logger`, this silent monkey-patch could cause confusion.

**Current Code (main.py):**
```python
from . import security as security_module
security_module.logger = logger
```

**Recommended Fix:**
Either add a `logger` to `security.py` and use it:
```python
# security.py
import logging
logger = logging.getLogger(__name__)
```

Or remove the monkey-patching from main.py since it serves no purpose currently.

---

## Medium Priority Issues

### M1. Deprecated `datetime.utcnow()` Used in Tests

**File:** `c:\cursor\HomeIQ\services\energy-correlator\tests\conftest.py`, lines 31, 161
**File:** Multiple test files use `datetime.utcnow()` throughout
**Severity:** MEDIUM
**Impact:** `datetime.utcnow()` returns a naive datetime (no timezone info). This is deprecated in Python 3.12+ and can cause subtle bugs when mixed with timezone-aware datetimes used in the source code (which correctly uses `datetime.now(timezone.utc)`). Comparing naive and aware datetimes raises a `TypeError`.

**Current Code:**
```python
now = datetime.utcnow()  # Returns naive datetime
```

**Recommended Fix:**
```python
now = datetime.now(timezone.utc)  # Returns timezone-aware datetime
```

This should be changed across all test files: `conftest.py`, `test_correlator_logic.py`, `test_statistics.py`, `test_edge_cases.py`.

---

### M2. Statistics Endpoint Has No Error Handling

**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\main.py`, lines 163-166
**Severity:** MEDIUM
**Impact:** If `get_statistics()` raises any exception (e.g., due to a race condition or unexpected state), the endpoint returns a 500 with an aiohttp default error page instead of a structured JSON error response.

**Current Code:**
```python
async def get_statistics(request):
    stats = service.correlator.get_statistics()
    return web.json_response(stats)
```

**Recommended Fix:**
```python
async def get_statistics(request):
    try:
        stats = service.correlator.get_statistics()
        return web.json_response(stats)
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return web.json_response(
            {"error": "Failed to retrieve statistics"},
            status=500
        )
```

---

### M3. Power Cache Type Annotation is Incorrect

**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\correlator.py`, line 95
**Severity:** MEDIUM
**Impact:** The type hint says `dict[str, list[float]]` but the actual cache structure is `{"timestamps": list[float], "values": list[float]}` where keys are strings. This is technically correct but misleading -- the annotation suggests arbitrary string keys, when the structure is actually fixed. More importantly, the `_lookup_power_in_cache` signature (line 589) also uses the same vague type.

**Recommended Fix:**
```python
from typing import TypedDict

class PowerCache(TypedDict):
    timestamps: list[float]
    values: list[float]

# Then use:
self._power_cache: PowerCache | None = None
```

---

### M4. Retry Queue Does Not Enforce Size in `_correlate_event_with_power`

**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\correlator.py`, lines 294-303
**Severity:** MEDIUM
**Impact:** When `_correlate_event_with_power` appends to the retry queue, it does not check the queue size. The size enforcement only happens in `_trim_pending_events` after the batch completes. This means the retry queue can temporarily grow unbounded during a single batch processing cycle.

**Current Code:**
```python
if retry_queue is not None:
    deferred = DeferredEvent(...)
    retry_queue.append(deferred)  # No size check
```

**Recommended Fix:**
```python
if retry_queue is not None and len(retry_queue) < self.max_retry_queue_size:
    deferred = DeferredEvent(...)
    retry_queue.append(deferred)
elif retry_queue is not None:
    logger.debug(
        f"Retry queue full ({self.max_retry_queue_size}), "
        f"dropping event for {entity_id}"
    )
```

---

### M5. `_query_recent_events` Returns `'time'` Key but InfluxDB Records Use `'_time'`

**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\correlator.py`, line 243 vs `influxdb_wrapper.py` line 70
**Severity:** MEDIUM
**Impact:** The InfluxDB wrapper maps `record.get_time()` to the key `'time'` (line 70), which is consistent. However, the `_query_recent_events` method checks for `record.get('time')` on line 243 while the test mocks use `'_time'` as the key (e.g., `test_edge_cases.py` line 371, `test_event_processing.py` line 63). This mismatch means some tests may pass for the wrong reasons (the `isinstance(event_time, datetime)` guard filters out events with wrong keys instead of properly testing the flow).

**Recommendation:** Standardize test mocks to use `'time'` (matching the wrapper output) rather than `'_time'` to accurately test the pipeline.

---

### M6. `requirements.txt` vs `requirements-prod.txt` Version Mismatch

**File:** `c:\cursor\HomeIQ\services\energy-correlator\requirements.txt`, line 6
**File:** `c:\cursor\HomeIQ\services\energy-correlator\requirements-prod.txt`, line 3
**Severity:** MEDIUM
**Impact:** `requirements.txt` specifies `python-dotenv>=1.0.0,<2.0.0` while `requirements-prod.txt` specifies `python-dotenv>=1.0.1,<2.0.0`. This inconsistency means dev and prod environments could have different minimum versions.

**Recommended Fix:** Align both files to use the same minimum version (`>=1.0.1`).

---

### M7. No Request Rate Limiting on API Endpoints

**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\main.py`, lines 155-187
**Severity:** MEDIUM
**Impact:** The `/statistics` and `/statistics/reset` endpoints have no rate limiting. While `/statistics/reset` is protected by internal network validation, `/statistics` is publicly accessible and could be abused for DoS.

**Recommended Fix:** Add a simple rate limiter middleware or use aiohttp's built-in middleware support.

---

## Low Priority / Nice-to-Have

### L1. Missing `__init__.py` in `tests/unit/` Directory

**File:** `c:\cursor\HomeIQ\services\energy-correlator\tests\unit\__init__.py` (missing)
**Severity:** LOW
**Impact:** While pytest discovers tests without `__init__.py`, having it is a best practice for package-based imports and IDE support. The `tests/integration/` directory has one, but `tests/unit/` does not.

---

### L2. No Graceful Shutdown Signal Handling

**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\main.py`, lines 192-247
**Severity:** LOW
**Impact:** The service catches `KeyboardInterrupt` but does not handle `SIGTERM` (the standard Docker stop signal). While asyncio.run handles SIGTERM on Linux by default, explicit signal handling would be more robust.

**Recommended Fix:**
```python
import signal

async def main():
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)
    ...
```

---

### L3. README Documents Fields Not Present in Actual Code

**File:** `c:\cursor\HomeIQ\services\energy-correlator\README.md`, lines 59-74
**Severity:** LOW
**Impact:** The README statistics example shows `retry_queue_max_size` and `config.lookback_minutes` which are not present in the actual `get_statistics()` response (line 639-654 of correlator.py). The actual response has `retry_queue_capacity_pct` and `config.max_retry_queue_size` instead. Similarly the README data model section mentions `correlation_confidence` field which is not implemented.

---

### L4. Dockerfile Uses `pip==25.2` Pinned Version

**File:** `c:\cursor\HomeIQ\services\energy-correlator\Dockerfile`, line 7
**Severity:** LOW
**Impact:** Pinning pip to a specific version (`25.2`) means the build will fail if that exact version is no longer available. Use `pip install --upgrade pip` without pinning, or pin to a range.

---

### L5. TEST_PLAN.md is Outdated

**File:** `c:\cursor\HomeIQ\services\energy-correlator\TEST_PLAN.md`, line 7
**Severity:** LOW
**Impact:** The test plan states "Current Coverage: 0% (No tests exist)" but the service now has extensive tests. The test plan should be updated or replaced with the actual test documentation.

---

### L6. No Structured Request Logging Middleware

**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\main.py`
**Severity:** LOW
**Impact:** HTTP requests to the API endpoints are not logged. Adding request logging middleware would improve observability.

---

## Security Findings

### S1. Flux Injection (see C1 above)
**Rating:** CRITICAL - The pattern of f-string interpolation in Flux queries creates injection risk.

### S2. IPv6 Parsing Vulnerability (see H2 above)
**Rating:** HIGH - IPv6 addresses bypass internal network validation.

### S3. No CORS Configuration
**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\main.py`
**Rating:** LOW
**Impact:** The API endpoints have no CORS policy. Since this is an internal service, this is acceptable, but if it's ever exposed to a browser context, CORS should be configured.

### S4. Token Logging Risk
**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\correlator.py`, line 114
**Rating:** LOW
**Impact:** `logger.info(f"Energy correlator connected to InfluxDB at {self.influxdb_url}")` logs the URL, which is fine. But the `self.influxdb_token` is stored as a plain attribute. Ensure it never appears in log messages. Currently safe, but a defensive pattern would be to mark it as private (`self._influxdb_token`).

### S5. Internal Reset Endpoint Combines Custom + Default Networks
**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\security.py`, line 67
**Rating:** LOW
**Impact:** When custom `ALLOWED_NETWORKS` are provided, they are combined with defaults via `list(set(...))`. This means custom networks can only _expand_ access, never restrict it. If an admin wants to restrict to only Docker networks (172.16.0.0/12), they cannot remove 10.0.0.0/8. This might be intentional but should be documented.

---

## Performance Recommendations

### P1. Batch Power Cache is Excellent - Protect It
The `_build_power_cache` approach (single query for all power data) with `bisect_left` lookup is a strong optimization. The concern is the N+1 fallback in `_get_power_at_time` (see H1). Eliminating the fallback in batch mode would ensure consistent O(1) lookups.

### P2. Consider Limiting Power Cache Size
**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\correlator.py`, line 534
Currently, the power cache loads all `smart_meter` points in the event window + padding. For a 5-minute window with 1-second resolution data, this is ~300 points (manageable). But with sub-second data or longer windows, this could grow large. Consider adding a `|> limit(n: 5000)` or downsampling in the Flux query.

### P3. Double Sort in `_merge_pending_events`
**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\correlator.py`, lines 474, 480
Events are sorted descending (line 474), truncated, then sorted ascending (line 480). This is O(n log n) twice. Could be optimized with `heapq.nlargest` for a single pass, but with max 500 events, this is not critical.

### P4. `process_recent_events` Logs Cumulative Statistics
**File:** `c:\cursor\HomeIQ\services\energy-correlator\src\correlator.py`, lines 188-192
The log message reports `self.total_events_processed` (cumulative) rather than the count from the current batch. This makes monitoring confusing as the numbers grow indefinitely.

**Recommended Fix:**
```python
logger.info(
    f"Batch complete: processed {len(events)} events, "
    f"found {len(batch_points)} correlations "
    f"(cumulative: {self.total_events_processed} events, "
    f"{self.correlations_found} correlations)"
)
```

---

## Test Coverage Analysis

### Overall Assessment: GOOD (7.5/10)

The test suite is comprehensive in breadth but has quality gaps that reduce its effectiveness.

### Strengths

1. **Extensive Coverage of Core Logic:** `test_correlator_logic.py` (327 lines) thoroughly tests power delta calculations, threshold logic, missing data scenarios, and multiple event correlation.

2. **Configuration Testing:** `test_energy_correlator_configuration.py` (280 lines) covers all env var defaults, custom values, type parsing, and complete configuration scenarios.

3. **Statistics Testing:** `test_statistics.py` (376 lines) covers initialization, counter tracking, rate calculations, rounding, reset, error accumulation, and response structure validation.

4. **Security Testing:** `test_security.py` (180 lines) tests valid bucket names, invalid characters, length limits, private/public IP ranges, custom networks, invalid formats, IP:PORT parsing, and edge cases.

5. **Edge Cases:** `test_edge_cases.py` (432 lines) covers boundary conditions, configuration limits, timezone handling, memory limits, and concurrent operations.

6. **Error Scenarios:** `test_error_scenarios.py` (500 lines) covers connection failures, query timeouts, malformed responses, data validation, retry queue overflow, cache failures, and error statistics.

7. **Integration Tests:** Three files covering API endpoints, event processing flow, and InfluxDB query patterns.

### Weaknesses

1. **Deprecated `datetime.utcnow()` in Tests:** The `conftest.py` and several test files use `datetime.utcnow()` which returns naive datetimes. The source code uses `datetime.now(timezone.utc)` (aware). Mixing these can cause `TypeError` in edge cases or produce incorrect time comparisons.

2. **Test Mock Key Mismatch (`'_time'` vs `'time'`):** Several test mocks use `'_time'` as the time key, but the `influxdb_wrapper.py` maps it to `'time'`. This means some tests pass because the `isinstance(event_time, datetime)` guard filters out the mismatched data, not because the logic is working correctly.

3. **Weak Assertions in Integration Tests:**
   - `test_event_processing.py` line 113: `assert stats['events_processed'] >= 0` -- this assertion is trivially true for any non-negative integer. The key `'events_processed'` does not even exist in the actual statistics response (it's `'total_events_processed'`).
   - `test_api_endpoints.py` line 63: `assert "total_correlations" in data or "events_processed" in data` -- neither of these keys exists in the actual response.
   - `test_error_scenarios.py` line 109: `assert correlator.errors >= 0` -- trivially true.

4. **Retry Queue Overflow Test Does Not Validate Properly:**
   - `test_error_scenarios.py` lines 280-349: The test appends DeferredEvent objects to a local `retry_queue` list but never checks that `_trim_pending_events` enforces the limit. The assertion `len(retry_queue) <= correlator.max_retry_queue_size` checks the local list, which is unbounded since `_correlate_event_with_power` simply appends without checking size.

5. **Missing `__init__.py` in `tests/unit/`:** While not critical for pytest, it's inconsistent with `tests/integration/` which has one.

6. **`test_edge_cases.py` Fixture Pattern Issue:** The `correlator_with_mock` fixtures call `await correlator.startup()` which creates a new InfluxDBWrapper and overrides the mock client. Line 38-39:
   ```python
   correlator.client = mock_client
   await correlator.startup()  # This replaces mock_client!
   ```
   The `startup()` call creates a new `InfluxDBWrapper` and calls `connect()`, overwriting the mock. The test only works because the mock_client's `connect()` is also a MagicMock.

7. **No Performance Tests Implemented:** Despite the TEST_PLAN.md having a performance test section, no performance tests exist.

8. **`AioHTTPTestCase` is Deprecated Pattern:** The `test_api_endpoints.py` uses `AioHTTPTestCase` which is the older unittest-style approach. Modern aiohttp testing uses `aiohttp.pytest_plugin` with `aiohttp_client` fixture.

### Test File Summary

| Test File | Lines | Tests | Quality | Notes |
|-----------|-------|-------|---------|-------|
| `conftest.py` | 196 | 8 fixtures | GOOD | Uses deprecated utcnow() |
| `test_correlator_logic.py` | 327 | 12 | GOOD | Solid delta/threshold tests |
| `test_energy_correlator_configuration.py` | 280 | 14 | VERY GOOD | Comprehensive env var coverage |
| `test_statistics.py` | 376 | 16 | VERY GOOD | Thorough rate/counter tests |
| `test_security.py` | 180 | 11 | GOOD | Missing IPv6 test cases |
| `test_edge_cases.py` | 432 | 10 | FAIR | Fixture startup overwrites mocks |
| `test_error_scenarios.py` | 500 | 12 | FAIR | Weak assertions, trivially true checks |
| `test_api_endpoints.py` | 169 | 7 | FAIR | Wrong key names in assertions |
| `test_event_processing.py` | 220 | 5 | FAIR | Wrong key names in assertions |
| `test_influxdb_queries.py` | 165 | 7 | GOOD | Solid query validation |

### Missing Test Coverage

1. **`_build_power_cache` with real data:** No test validates that the cache correctly indexes timestamps and enables bisect lookup.
2. **`_lookup_power_in_cache` boundary conditions:** No test for the case where the target timestamp is exactly at a cache entry.
3. **DeferredEvent serialization round-trip:** `to_dict()` and `from_dict()` are tested indirectly but no explicit round-trip test.
4. **InfluxDB wrapper `_execute_query` parsing:** The table/record parsing logic is untested.
5. **`require_internal_network` middleware function:** Defined in security.py but never tested.
6. **Concurrent write + query operations:** Only concurrent queries are tested.

---

## Architecture Recommendations

### A1. Add a Circuit Breaker for InfluxDB

The service retries indefinitely on InfluxDB failures (with configurable sleep). Consider adding a circuit breaker pattern:
- After N consecutive failures, enter "open" state and stop querying for a cooldown period.
- Report "unhealthy" status during open state.
- Automatically attempt recovery after cooldown.

### A2. Separate Write and Read Buckets

Currently, the service reads from and writes to the same bucket (`home_assistant_events`). Consider writing correlations to a dedicated `energy_correlations` bucket to:
- Avoid namespace pollution
- Enable different retention policies
- Simplify access control

### A3. Consider Structured Events Instead of Raw Dicts

The `process_recent_events` flow passes events as raw dicts through multiple methods. Consider defining a proper `EventRecord` dataclass (similar to `DeferredEvent`) for type safety and IDE support.

### A4. Add Prometheus Metrics Export

The `/statistics` endpoint provides operational metrics, but for production monitoring, consider exposing Prometheus-compatible metrics via `/metrics` endpoint using `prometheus-client` or `aiohttp-prometheus`.

---

## Summary of Findings by Priority

| Priority | Count | Key Issues |
|----------|-------|------------|
| CRITICAL | 3 | Flux injection, always-healthy, ASYNC write conflict |
| HIGH | 4 | N+1 fallback, IPv6 parsing, env var validation, logger monkey-patch |
| MEDIUM | 7 | Deprecated utcnow, no error handling on stats endpoint, type hints, queue size, mock keys, version mismatch, rate limiting |
| LOW | 6 | Missing __init__.py, signal handling, README accuracy, pip pinning, stale test plan, request logging |
| SECURITY | 5 | Flux injection, IPv6 bypass, no CORS, token exposure risk, network combo |

---

**Document Version:** 1.0
**Generated:** February 6, 2026
**Reviewer:** Claude Opus 4.6
**Status:** Complete
