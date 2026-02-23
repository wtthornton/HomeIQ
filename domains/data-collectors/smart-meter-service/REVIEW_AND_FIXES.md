# Smart Meter Service - Comprehensive Code Review

**Service:** smart-meter-service (Tier 2, Port 8014)
**Review Date:** February 6, 2026
**Reviewer:** Deep Code Review (Automated)
**Files Reviewed:** 11 source/test/config files

---

## Executive Summary

**Overall Health Score: 6.0 / 10**

The smart-meter-service implements a reasonable adapter pattern for Home Assistant energy monitoring with direct InfluxDB writes (Epic 31). The code is readable and follows basic patterns, but has several critical and high-priority issues that compromise production readiness:

- **Critical**: InfluxDB writes are not batched (individual write per circuit per interval)
- **Critical**: `log_error_with_context` is called with wrong parameter types throughout
- **Critical**: Division-by-zero risk in percentage calculation
- **High**: Token potentially logged in plaintext via f-string
- **High**: `test_connection()` creates its own session, leaking the service session pattern
- **High**: No input validation on energy readings (negative watts, NaN, infinite values)
- **High**: No graceful shutdown signal handling (SIGTERM/SIGINT)
- **Medium**: README documents FastAPI/uvicorn but service actually uses aiohttp
- **Medium**: No configurable fetch interval
- **Medium**: Stale cache served indefinitely without age indicator

The adapter pattern is a good architectural choice, but the base class interface is underutilized and the HA adapter has several resilience gaps.

---

## Critical Issues (Must Fix)

### C1. InfluxDB Writes Are Not Batched - Individual Write Per Data Point

**File:** `src/main.py`, lines 212-246
**Impact:** For N circuits, this performs N+1 synchronous InfluxDB writes per fetch cycle. With 20 circuits at 5-minute intervals, that is 21 write calls every 5 minutes -- each with HTTP overhead.

**Current Code:**
```python
# Line 226 - One write for whole-home
self.influxdb_client.write(point)

# Lines 229-236 - One write PER circuit
for circuit in data.get('circuits', []):
    circuit_point = Point("smart_meter_circuit") \
        .tag("circuit_name", circuit['name']) \
        .field("power_w", float(circuit['power_w'])) \
        .field("percentage", float(circuit['percentage'])) \
        .time(data['timestamp'])
    self.influxdb_client.write(circuit_point)  # Individual write!
```

**Fix:**
```python
async def store_in_influxdb(self, data: dict[str, Any]) -> None:
    """Store consumption data in InfluxDB using batched writes"""
    if not data:
        return

    try:
        points = []

        # Whole-home consumption point
        point = Point("smart_meter") \
            .tag("meter_type", self.meter_type) \
            .field("total_power_w", float(data['total_power_w'])) \
            .field("daily_kwh", float(data['daily_kwh'])) \
            .time(data['timestamp'])
        points.append(point)

        # Circuit-level data points
        for circuit in data.get('circuits', []):
            circuit_point = Point("smart_meter_circuit") \
                .tag("circuit_name", circuit['name']) \
                .field("power_w", float(circuit['power_w'])) \
                .field("percentage", float(circuit['percentage'])) \
                .time(data['timestamp'])
            points.append(circuit_point)

        # Single batched write
        self.influxdb_client.write(points)

        logger.info(f"Wrote {len(points)} points to InfluxDB")

    except Exception as e:
        log_error_with_context(
            logger,
            f"Error writing to InfluxDB: {e}",
            error=e,
            service="smart-meter-service"
        )
```

---

### C2. `log_error_with_context` Called With Wrong Signature

**File:** `src/main.py`, lines 166-171, 263-268, and 240-246
**Impact:** The shared `log_error_with_context` function expects `error: Exception` (the actual exception object), but the service passes `error=str(e)` (a string). This means the error logging loses the exception type, traceback, and the `code` attribute extraction.

**Shared function signature** (`shared/logging_config.py`, line 237):
```python
def log_error_with_context(logger: logging.Logger, message: str, error: Exception, **context):
```

**Current Code (all 3 call sites):**
```python
# Line 166 - WRONG: passes string, not Exception
log_error_with_context(
    logger,
    f"Error fetching from adapter: {e}",
    service="smart-meter-service",
    error=str(e)  # BUG: 'error' goes into **context as a string
)
```

The `error` parameter is a keyword argument here, so it goes into `**context`, not the `error` positional parameter. The function will fail because the positional `error` parameter is not provided.

**Fix (all 3 call sites):**
```python
# Line 166 - Pass exception object as positional arg
log_error_with_context(
    logger,
    f"Error fetching from adapter: {e}",
    error=e,  # Pass the actual Exception object
    service="smart-meter-service"
)
```

Wait -- looking more carefully at the signature: `def log_error_with_context(logger, message, error, **context)` -- `error` is positional. But the callers pass it as `error=str(e)` which works as a keyword arg for the positional parameter. The real bug is passing `str(e)` instead of `e`. This causes `type(error).__name__` to return `'str'` instead of the actual exception class name, and the traceback is lost.

**Corrected Fix:**
```python
log_error_with_context(
    logger,
    f"Error fetching from adapter: {e}",
    error=e,
    service="smart-meter-service"
)
```

---

### C3. Division-by-Zero Risk in Percentage Calculation

**File:** `src/main.py`, lines 133-138
**Impact:** If `data['total_power_w']` is exactly `0.0` (not `> 0`), the code correctly handles it. But if `total_power_w` key is missing entirely, a `KeyError` will crash the fetch cycle.

**Current Code:**
```python
for circuit in data.get('circuits', []):
    if 'percentage' not in circuit:
        circuit['percentage'] = (
            (circuit['power_w'] / data['total_power_w']) * 100
            if data['total_power_w'] > 0 else 0
        )
```

**Additionally in `src/adapters/home_assistant.py`**, line 71:
```python
circuit['percentage'] = (
    (circuit['power_w'] / total_power * 100)
    if total_power > 0 else 0
)
```

There is redundant percentage calculation in both `main.py` and `home_assistant.py`. The HA adapter calculates percentages, then `main.py` checks again and potentially overwrites. This is confusing and the logic should live in one place.

**Fix (main.py) - Add safe access:**
```python
for circuit in data.get('circuits', []):
    if 'percentage' not in circuit:
        total = data.get('total_power_w', 0)
        power = circuit.get('power_w', 0)
        circuit['percentage'] = (
            (power / total) * 100
            if total > 0 else 0
        )
```

---

## High Priority Issues

### H1. HA Token Potentially Logged in Adapter Init

**File:** `src/adapters/home_assistant.py`, line 34
**Impact:** The URL is logged, which is fine, but if someone passes the token as a URL parameter or the URL contains credentials, it will be logged in plaintext.

**Current Code:**
```python
logger.info(f"Home Assistant adapter initialized for {ha_url}")
```

**This is low-risk currently** since the URL and token are separate. However, the `self.headers` dictionary containing the Bearer token is stored as an instance attribute and could be inadvertently logged in debug mode or exception handlers.

**Recommendation:** Ensure the headers dict is never logged. Consider a `__repr__` override:
```python
def __repr__(self):
    return f"HomeAssistantAdapter(url={self.ha_url}, token=***)"
```

---

### H2. `test_connection()` Creates Its Own Session - Leaks Pattern

**File:** `src/adapters/home_assistant.py`, lines 252-273
**Impact:** `test_connection()` creates a brand new `aiohttp.ClientSession()` instead of using the session passed from the service. This bypasses the timeout configuration, creates unnecessary connections, and is inconsistent with the rest of the adapter which receives the session as a parameter.

**Current Code:**
```python
async def test_connection(self) -> bool:
    try:
        async with aiohttp.ClientSession() as session:  # New session!
            async with session.get(url, headers=self.headers) as response:
                ...
```

**Fix:**
```python
async def test_connection(self, session: aiohttp.ClientSession) -> bool:
    """Test connection to Home Assistant using the shared session"""
    url = f"{self.ha_url}/api/"
    try:
        async with session.get(url, headers=self.headers) as response:
            if response.status == 200:
                data = await response.json()
                logger.info(f"Connected to Home Assistant: {data.get('message', 'OK')}")
                return True
            else:
                logger.error(f"Failed to connect to HA: HTTP {response.status}")
                return False
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
```

And update `main.py` line 84:
```python
connected = await self.adapter.test_connection(self.session)
```

---

### H3. No Input Validation on Energy Readings

**File:** `src/main.py` and `src/adapters/home_assistant.py`
**Impact:** Negative wattage, NaN, infinite values, or absurdly large numbers from a malfunctioning sensor will be written to InfluxDB without any validation, corrupting the time-series data.

**Current Code (home_assistant.py line 230):**
```python
power_w = float(state_value)  # No validation!
```

**Fix - Add validation helper:**
```python
import math

def _validate_power_reading(value: float, entity_id: str) -> float | None:
    """Validate a power reading, returning None if invalid"""
    if math.isnan(value) or math.isinf(value):
        logger.warning(f"Invalid power reading from {entity_id}: {value}")
        return None
    if value < 0:
        logger.warning(f"Negative power reading from {entity_id}: {value}W")
        return None
    if value > 100000:  # 100kW sanity check for residential
        logger.warning(f"Unreasonably high power from {entity_id}: {value}W")
        return None
    return value
```

Use in `_get_circuit_data`:
```python
power_w = self._validate_power_reading(float(state_value), entity_id)
if power_w is None:
    continue
```

And in `store_in_influxdb`, validate before writing:
```python
if not isinstance(data.get('total_power_w'), (int, float)):
    logger.error("Invalid total_power_w value")
    return
```

---

### H4. No Graceful Shutdown Signal Handling

**File:** `src/main.py`, lines 296-302
**Impact:** `KeyboardInterrupt` is caught, but `SIGTERM` (Docker's default stop signal) is not handled. The service may not clean up properly in container environments.

**Current Code:**
```python
try:
    await service.run_continuous()
except KeyboardInterrupt:
    logger.info("Received shutdown signal")
finally:
    await service.shutdown()
    await runner.cleanup()
```

**Fix:**
```python
import signal

async def main() -> None:
    """Main entry point"""
    logger.info("Starting Smart Meter Service...")

    service = SmartMeterService()
    await service.startup()

    app = await create_app(service)
    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv('SERVICE_PORT', '8014'))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    logger.info(f"API endpoints available on port {port}")

    # Handle shutdown signals
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handle_signal():
        logger.info("Received shutdown signal")
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal)

    try:
        # Run continuous collection until stop signal
        collection_task = asyncio.create_task(service.run_continuous())
        await stop_event.wait()
        collection_task.cancel()
    finally:
        await service.shutdown()
        await runner.cleanup()
```

---

### H5. Stale Cache Served Indefinitely

**File:** `src/main.py`, lines 174-177
**Impact:** When the adapter fails, cached data is returned regardless of age. A cache from 12 hours ago could still be served, giving users wildly inaccurate readings.

**Current Code:**
```python
if self.cached_data:
    logger.warning("Using cached data after adapter failure")
    return self.cached_data
```

**Fix - Add cache TTL:**
```python
CACHE_MAX_AGE_SECONDS = 900  # 15 minutes (3x fetch interval)

# In fetch_consumption error handler:
if self.cached_data and self.last_fetch_time:
    cache_age = (datetime.now() - self.last_fetch_time).total_seconds()
    if cache_age < self.CACHE_MAX_AGE_SECONDS:
        logger.warning(
            f"Using cached data (age: {cache_age:.0f}s) after adapter failure"
        )
        return self.cached_data
    else:
        logger.warning(
            f"Cached data too old ({cache_age:.0f}s > {self.CACHE_MAX_AGE_SECONDS}s), "
            "falling back to mock data"
        )
```

---

### H6. `_get_sensor_state` Return Type Annotation Is Wrong

**File:** `src/adapters/home_assistant.py`, line 141
**Impact:** The function signature says it returns `str`, but it also returns `None`. The callers (`_get_power_sensor`, `_get_energy_sensor`) check for `None`, so the logic works, but the type annotation is misleading.

**Current Code:**
```python
async def _get_sensor_state(
    self,
    session: aiohttp.ClientSession,
    entity_id: str
) -> str:  # Wrong: also returns None
```

**Fix:**
```python
async def _get_sensor_state(
    self,
    session: aiohttp.ClientSession,
    entity_id: str
) -> str | None:
```

---

## Medium Priority Improvements

### M1. README Documents FastAPI/uvicorn but Service Uses aiohttp

**File:** `README.md`, line 6 and line 45
**Impact:** Confusing for developers. The README says "FastAPI 0.121" and shows `uvicorn src.main:app --reload --port 8014`, but the service actually uses `aiohttp.web` and `asyncio.run(main())`.

**Current README line 6:**
```
**Technology:** Python 3.11+, FastAPI 0.121, aiohttp 3.13, InfluxDB 3.0
```

**Current README line 45:**
```
uvicorn src.main:app --reload --port 8014
```

**Fix:**
```
**Technology:** Python 3.11+, aiohttp 3.13, InfluxDB 3.0
```
```bash
python -m src.main
```

Also line 186 references `http://localhost:8014/docs` (OpenAPI docs) which do not exist since the service is not FastAPI.

---

### M2. Fetch Interval Is Not Configurable

**File:** `src/main.py`, line 48
**Impact:** The 5-minute interval is hardcoded. Users with high-resolution meters may want 30-second intervals; others may want 15 minutes.

**Current Code:**
```python
self.fetch_interval = 300  # 5 minutes
```

**Fix:**
```python
self.fetch_interval = int(os.getenv('FETCH_INTERVAL_SECONDS', '300'))
if self.fetch_interval < 10:
    logger.warning(f"Fetch interval {self.fetch_interval}s too low, setting to 10s minimum")
    self.fetch_interval = 10
```

---

### M3. `_create_adapter` Return Type is `Any` - Should Use Base Class

**File:** `src/main.py`, line 90
**Impact:** The adapter pattern defines `MeterAdapter` as the base class, but `_create_adapter` returns `Any` and the adapter is typed as `None` initially. This defeats the purpose of the adapter pattern's type safety.

**Current Code:**
```python
def _create_adapter(self) -> Any:
    ...
self.adapter = None  # Will be initialized in startup
```

**Fix:**
```python
from adapters.base import MeterAdapter

def _create_adapter(self) -> MeterAdapter | None:
    ...
self.adapter: MeterAdapter | None = None
```

---

### M4. MeterAdapter Base Class Does Not Define `test_connection`

**File:** `src/adapters/base.py`
**Impact:** The base class only defines `fetch_consumption`, but `main.py` line 83 checks `isinstance(self.adapter, HomeAssistantAdapter)` to call `test_connection()`. This is a Liskov substitution violation -- future adapters won't have `test_connection` unless they also implement it.

**Current Code:**
```python
class MeterAdapter(ABC):
    @abstractmethod
    async def fetch_consumption(self, session, api_token, device_id) -> dict[str, Any]:
        pass
```

**Fix:**
```python
class MeterAdapter(ABC):
    @abstractmethod
    async def fetch_consumption(
        self, session: aiohttp.ClientSession, api_token: str, device_id: str
    ) -> dict[str, Any]:
        """Fetch consumption data from meter API"""
        pass

    async def test_connection(self, session: aiohttp.ClientSession) -> bool:
        """Test connection to meter API. Override in subclasses."""
        return True  # Default: assume connected
```

Then in `main.py` replace the `isinstance` check:
```python
# Before:
if isinstance(self.adapter, HomeAssistantAdapter):
    connected = await self.adapter.test_connection()

# After:
if self.adapter:
    connected = await self.adapter.test_connection(self.session)
    if not connected:
        logger.warning("Failed to connect to meter - will use mock data")
```

---

### M5. No Retry Logic for InfluxDB Writes

**File:** `src/main.py`, lines 218-246
**Impact:** A single failed InfluxDB write loses the data point entirely. No retry, no dead-letter queue, no buffering.

**Recommendation:** Add simple retry with exponential backoff:
```python
import asyncio

async def store_in_influxdb(self, data: dict[str, Any], max_retries: int = 3) -> None:
    if not data:
        return

    for attempt in range(max_retries):
        try:
            points = self._build_points(data)
            self.influxdb_client.write(points)
            logger.info(f"Wrote {len(points)} points to InfluxDB")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning(
                    f"InfluxDB write attempt {attempt + 1} failed, retrying in {wait}s: {e}"
                )
                await asyncio.sleep(wait)
            else:
                log_error_with_context(
                    logger,
                    f"InfluxDB write failed after {max_retries} attempts: {e}",
                    error=e,
                    service="smart-meter-service"
                )
```

---

### M6. Circuit Discovery Fetches ALL HA States Every Cycle

**File:** `src/adapters/home_assistant.py`, lines 194-250
**Impact:** `_get_circuit_data` calls `/api/states` which returns ALL entities from Home Assistant (potentially thousands). This is done every 5-minute fetch cycle. Combined with `_get_power_sensor` (up to 4 HTTP calls) and `_get_energy_sensor` (up to 3 HTTP calls), each fetch cycle makes up to 8 HTTP requests.

**Recommendation:** Cache the discovered entity IDs and refresh periodically:
```python
def __init__(self, ha_url: str, ha_token: str):
    ...
    self._discovered_circuits: list[str] | None = None
    self._last_discovery: datetime | None = None
    self._discovery_interval = 3600  # Re-discover every hour

async def _get_circuit_data(self, session: aiohttp.ClientSession) -> list[dict]:
    # Re-discover circuits periodically
    if (self._discovered_circuits is None or
        self._last_discovery is None or
        (datetime.now() - self._last_discovery).total_seconds() > self._discovery_interval):
        await self._discover_circuits(session)

    # Fetch only known circuit sensors
    circuits = []
    for entity_id in (self._discovered_circuits or []):
        state = await self._get_sensor_state(session, entity_id)
        if state is not None:
            # ... build circuit dict
            pass
    return circuits
```

---

### M7. `datetime.now()` Used Without Timezone

**File:** `src/main.py`, lines 130, 141, 153-154, 199, 204-205; `src/adapters/home_assistant.py`, line 80
**Impact:** All timestamps are naive (no timezone). InfluxDB will interpret these as UTC or local time inconsistently. This causes data alignment issues if the server timezone changes.

**Fix:**
```python
from datetime import datetime, timezone

# Replace all datetime.now() with:
datetime.now(timezone.utc)
```

---

### M8. requirements.txt vs requirements-prod.txt Mismatch

**File:** `requirements.txt` and `requirements-prod.txt`
**Impact:** `requirements.txt` pins exact versions (`aiohttp==3.13.2`) while `requirements-prod.txt` uses ranges (`aiohttp>=3.13.2,<4.0.0`). Also, `requirements-prod.txt` includes `pandas>=2.2.0` which is not used anywhere in the service code.

**Current requirements.txt:**
```
aiohttp==3.13.2
python-dotenv==1.2.1
influxdb3-python==0.3.0
```

**Current requirements-prod.txt:**
```
aiohttp>=3.13.2,<4.0.0
python-dotenv>=1.0.1,<2.0.0
influxdb3-python>=0.3.0,<1.0.0
pandas>=2.2.0,<3.0.0  # Not used in the service!
```

**Fix:** Remove `pandas` from `requirements-prod.txt` (it adds ~50MB to the Docker image for no reason). Also align the version strategies between dev and prod.

---

## Low Priority / Nice-to-Have

### L1. No API Endpoints Beyond Health Check

**File:** `src/main.py`, lines 272-276
**Impact:** The service only exposes `/health`. There is no way to query the current power reading, force a refresh, or check the cache status via REST API.

**Recommendation:** Add at minimum:
- `GET /api/current` - Return cached current readings
- `GET /api/status` - Return adapter info, cache age, last fetch time
- `POST /api/refresh` - Force immediate fetch

---

### L2. No `__init__.py` in `tests/` or `tests/unit/`

**File:** `tests/` directory
**Impact:** Missing `__init__.py` files can cause import issues in some test configurations, though pytest usually handles this.

---

### L3. Mock Data Is Static / Not Randomized

**File:** `src/main.py`, lines 185-210
**Impact:** Mock data always returns the same values (2450W, 18.5kWh). For development/demo purposes, slightly randomized values would better simulate real behavior.

---

### L4. `_create_adapter` Has Dead Code Paths

**File:** `src/main.py`, lines 99-107
**Impact:** The Emporia and Sense adapter branches return `None` with a warning. These are pure placeholders and add no value.

---

### L5. Health Check Success Rate Is Not Thread-Safe

**File:** `src/health_check.py`, lines 37-38
**Impact:** `total_fetches` and `failed_fetches` are simple integers incremented without locking. In an asyncio context this is technically safe (single-threaded event loop), but if the service ever moves to multi-threaded execution, this would cause race conditions.

---

## Security Findings

### S1. HA Token Stored in Plain Instance Attribute

**File:** `src/adapters/home_assistant.py`, line 29
**Severity:** Medium
**Impact:** The `self.ha_token` and the full `Authorization` header are stored as plain instance attributes. If the object is ever serialized, logged via `repr()`, or inspected in a debugger's memory dump, the token is exposed.

**Recommendation:** Store only the headers dict (not the raw token) and consider masking in `__repr__`:
```python
def __init__(self, ha_url: str, ha_token: str):
    self.ha_url = ha_url.rstrip('/')
    self.headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json"
    }
    # Don't store ha_token as a separate attribute

def __repr__(self):
    return f"HomeAssistantAdapter(url={self.ha_url})"
```

---

### S2. No HTTPS Enforcement for HA Communication

**File:** `src/adapters/home_assistant.py`
**Severity:** Medium
**Impact:** The adapter accepts any URL scheme. If `HOME_ASSISTANT_URL` is set to `http://`, the Bearer token is sent in plaintext over the network.

**Recommendation:** At minimum, log a warning if not using HTTPS:
```python
if not ha_url.startswith('https://'):
    logger.warning(
        "Home Assistant URL is not HTTPS - token will be sent in plaintext. "
        "This is acceptable for localhost/Docker networking but not for remote connections."
    )
```

---

### S3. No Rate Limiting on Health Endpoint

**File:** `src/main.py`, line 275
**Severity:** Low
**Impact:** The `/health` endpoint has no rate limiting. A flood of health checks could consume resources.

---

### S4. Entity ID Not Sanitized Before URL Construction

**File:** `src/adapters/home_assistant.py`, line 152
**Severity:** Low (HA API handles this, but defense-in-depth)
**Impact:** The `entity_id` is directly interpolated into the URL. While HA entity IDs are typically safe, a malformed entity ID could cause unexpected behavior.

**Current Code:**
```python
url = f"{self.ha_url}/api/states/{entity_id}"
```

**Recommendation:**
```python
import re

if not re.match(r'^[a-z_]+\.[a-z0-9_]+$', entity_id):
    logger.warning(f"Invalid entity_id format: {entity_id}")
    return None
url = f"{self.ha_url}/api/states/{entity_id}"
```

---

## Performance Recommendations

### P1. Batch InfluxDB Writes (See C1 Above)

Single most impactful performance improvement. Switch from N+1 individual writes to a single batched write.

### P2. Cache HA Circuit Discovery (See M6 Above)

Fetching ALL HA states every 5 minutes is wasteful. Cache discovered entity IDs and refresh hourly.

### P3. Use Connection Pooling for HA API

**File:** `src/main.py`, line 68
**Current:** A single `aiohttp.ClientSession` is created, which is correct. However, the `test_connection()` method creates its own session (see H2).

### P4. Consider Write Buffering for Resilience

If InfluxDB is temporarily down, data points are lost. Consider a small in-memory buffer:
```python
self._write_buffer: list[Point] = []
MAX_BUFFER_SIZE = 100

async def store_in_influxdb(self, data):
    points = self._build_points(data)
    self._write_buffer.extend(points)

    try:
        self.influxdb_client.write(self._write_buffer)
        self._write_buffer.clear()
    except Exception:
        if len(self._write_buffer) > self.MAX_BUFFER_SIZE:
            dropped = len(self._write_buffer) - self.MAX_BUFFER_SIZE
            self._write_buffer = self._write_buffer[-self.MAX_BUFFER_SIZE:]
            logger.warning(f"Buffer full, dropped {dropped} oldest points")
```

### P5. Add Performance Metrics Logging

The shared `logging_config.py` provides `PerformanceLogger` but it is never used:
```python
from shared.logging_config import PerformanceLogger

async def fetch_consumption(self):
    with PerformanceLogger(logger, "fetch_consumption"):
        # ... existing code
```

---

## Test Coverage Analysis

### Current Coverage

The test suite has **7 test classes with 20 test methods**, covering:

| Area | Tests | Coverage |
|------|-------|----------|
| Configuration | 3 | Good - validates required env vars and defaults |
| Data Fetching | 5 | Good - success, cache, percentages, error fallback, no adapter |
| Phantom Load Detection | 2 | Partial - only tests 3am detection, not boundary cases |
| High Power Alerts | 1 | Minimal - only checks value, doesn't verify log output |
| InfluxDB Storage | 4 | Good - write, circuit, skip null, error handling |
| Mock Data | 2 | Good - structure and stats update |
| Adapter Creation | 4 | Good - all adapter types tested |
| Service Lifecycle | 4 | Good - startup/shutdown, resource cleanup |

### Critical Test Gaps

**G1. No tests for `HomeAssistantAdapter` at all**
The entire `src/adapters/home_assistant.py` file (275 lines) has zero unit tests. The tests only mock the adapter and test the service layer.

Missing test coverage:
- `_get_sensor_state` - HTTP response parsing, error states, unavailable sensors
- `_get_power_sensor` - fallback sensor name iteration
- `_get_energy_sensor` - fallback sensor name iteration
- `_get_circuit_data` - filtering logic, kW-to-W conversion, state parsing
- `test_connection` - success and failure paths
- Percentage calculation in `fetch_consumption`

**G2. No tests for the health check endpoint**
`health_check.py` has no dedicated tests. The health endpoint's degraded status logic (>600s since last fetch) is untested.

**G3. No integration tests exist**
The `pytest.ini` defines integration markers but no integration tests are present.

**G4. No negative value tests**
No tests verify behavior with negative power readings, NaN values, or empty circuit arrays.

**G5. No tests for `run_continuous` loop**
The continuous loop (line 248-269) is untested. Error recovery (60s sleep on error) is not verified.

**G6. No tests for `create_app` or the web server**
The aiohttp application creation and routing is not tested.

**G7. Phantom load test may not work correctly**
The test at line 118 patches `src.main.datetime`, but `datetime` is also imported in the module scope. The mock may not properly intercept `datetime.now()` calls depending on how the import resolves.

### Recommended Test Additions

```python
# tests/unit/test_home_assistant_adapter.py

class TestHomeAssistantAdapter:
    """Tests for the Home Assistant adapter"""

    @pytest.mark.asyncio
    async def test_get_sensor_state_success(self):
        """Test successful sensor state retrieval"""
        ...

    @pytest.mark.asyncio
    async def test_get_sensor_state_unavailable(self):
        """Test handling of unavailable sensor"""
        ...

    @pytest.mark.asyncio
    async def test_get_sensor_state_404(self):
        """Test handling of missing sensor"""
        ...

    @pytest.mark.asyncio
    async def test_circuit_discovery_filters_correctly(self):
        """Test that circuit discovery filters power sensors properly"""
        ...

    @pytest.mark.asyncio
    async def test_kw_to_w_conversion(self):
        """Test kW to W conversion in circuit discovery"""
        ...

    @pytest.mark.asyncio
    async def test_negative_power_reading(self):
        """Test handling of negative power values"""
        ...

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful HA connection test"""
        ...

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test failed HA connection test"""
        ...


# tests/unit/test_health_check.py

class TestHealthCheck:
    """Tests for the health check endpoint"""

    @pytest.mark.asyncio
    async def test_healthy_status(self):
        """Test healthy response when fetches are recent"""
        ...

    @pytest.mark.asyncio
    async def test_degraded_status(self):
        """Test degraded response when fetches are stale"""
        ...

    @pytest.mark.asyncio
    async def test_success_rate_calculation(self):
        """Test success rate math"""
        ...
```

---

## Docker / Deployment Issues

### D1. Dockerfile Uses `--no-cache-dir` with `--mount=type=cache`

**File:** `Dockerfile`, line 13
**Impact:** Minor inconsistency. The `--mount=type=cache` enables pip caching at the BuildKit level, but `--no-cache-dir` tells pip not to use its own cache. These work together fine, but the `--no-cache-dir` flag is redundant when using BuildKit cache mounts.

### D2. No `.env.example` File

**Impact:** Developers must read the README to understand required environment variables. A `.env.example` file is a common convention.

### D3. HEALTHCHECK Start Period May Be Too Short

**File:** `Dockerfile`, line 38
**Current:** `--start-period=30s`
**Impact:** If InfluxDB or Home Assistant is slow to start, the health check may fail during startup. Consider increasing to 60s.

### D4. No STOPSIGNAL Directive

**File:** `Dockerfile`
**Impact:** Docker sends SIGTERM by default, which is fine, but the Python code only catches `KeyboardInterrupt` (SIGINT). Adding `STOPSIGNAL SIGTERM` is a documentation best practice, and the Python code should handle SIGTERM (see H4).

---

## Architecture Recommendations

### A1. Introduce a Data Model / Pydantic Schema

The service passes raw `dict[str, Any]` throughout. This makes it easy to have missing keys, wrong types, or inconsistent structures. A Pydantic model would provide validation and documentation:

```python
from pydantic import BaseModel, Field, validator
from datetime import datetime

class CircuitReading(BaseModel):
    name: str
    power_w: float = Field(ge=0, le=100000)
    percentage: float = Field(ge=0, le=100, default=0)
    entity_id: str | None = None

class MeterReading(BaseModel):
    total_power_w: float = Field(ge=0, le=100000)
    daily_kwh: float = Field(ge=0, le=1000)
    circuits: list[CircuitReading] = []
    timestamp: datetime

    @validator('total_power_w')
    def validate_power(cls, v):
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"Invalid power value: {v}")
        return v
```

### A2. Consider Event-Driven Circuit Discovery

Instead of polling `/api/states` for ALL entities, use HA's WebSocket API to subscribe to state changes for power sensors. This aligns with the websocket-ingestion pattern already used in Tier 1.

### A3. Add Prometheus Metrics

The health check provides basic stats, but adding Prometheus-compatible metrics would enable better monitoring:
- `smart_meter_fetch_duration_seconds` (histogram)
- `smart_meter_power_watts` (gauge)
- `smart_meter_influxdb_write_errors_total` (counter)
- `smart_meter_cache_hits_total` (counter)

### A4. Consider Splitting Mock Data Into Its Own Adapter

The mock data logic in `main.py` could be a `MockAdapter(MeterAdapter)` class, keeping the service class clean and the adapter pattern consistent:

```python
class MockAdapter(MeterAdapter):
    async def fetch_consumption(self, session, api_token, device_id):
        return {
            'total_power_w': 2450.0,
            'daily_kwh': 18.5,
            'circuits': [...],
            'timestamp': datetime.now(timezone.utc)
        }
```

---

## Summary of Findings by Priority

| Priority | Count | Key Issues |
|----------|-------|------------|
| Critical | 3 | Unbatched InfluxDB writes, wrong error logging signature, division-by-zero risk |
| High | 6 | Token logging risk, leaked session in test_connection, no input validation, no SIGTERM handling, stale cache, wrong type annotation |
| Medium | 8 | README inaccuracies, hardcoded interval, weak typing, no retry, expensive circuit discovery, naive datetimes, requirements mismatch, missing base class method |
| Low | 5 | No REST API beyond health, missing __init__.py, static mock data, dead code, non-thread-safe counters |
| Security | 4 | Plaintext token storage, no HTTPS enforcement, no rate limiting, unsanitized entity IDs |
| Test Gaps | 7 | Zero HA adapter tests, no health check tests, no integration tests, no negative value tests, no continuous loop tests, no web app tests, fragile datetime mocking |

---

**Estimated Effort to Address All Issues:**
- Critical fixes: 2-3 hours
- High priority fixes: 3-4 hours
- Medium improvements: 4-6 hours
- Test gap coverage: 6-8 hours
- Architecture recommendations: 2-3 days

**Recommendation:** Address Critical and High items immediately before considering the service production-ready. The InfluxDB batching fix alone (C1) will have the largest positive impact on performance and reliability.
