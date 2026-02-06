# Weather API Deep Code Review Report

**Service**: weather-api (Tier 2, Port 8009)
**Reviewed**: 2026-02-06
**Reviewer**: Claude Opus 4.6 (Automated Deep Review)
**Files Reviewed**: 3 Python source files in `src/`, 4 test files in `tests/`, Dockerfile, Dockerfile.dev, requirements.txt, requirements-prod.txt, pytest.ini
**Total Lines of Code**: ~470 (src/ only), ~130 (tests/)

---

## Quality Scores

| Category | Score | Grade | Notes |
|---|---|---|---|
| **Security** | 6/10 | C | API key in query params leaks to logs/proxies; no input validation on location; wildcard CORS in future risk |
| **Error Handling** | 7/10 | B- | Good InfluxDB retry logic with backoff; graceful degradation; but silent cache fallback masks failures |
| **Performance** | 7/10 | B- | Cache-first pattern is good; but single-location cache only; no connection pooling tuning; blocking InfluxDB init |
| **Code Quality** | 7/10 | B | Clean single-file design; good use of Pydantic; but version mismatch in `__init__.py`; deprecated `datetime.utcnow()` usage |
| **API Design** | 6/10 | C | Missing documented endpoints (forecast, historical); metrics duplicates health; no pagination or query parameters |
| **Docker/Deployment** | 8/10 | A- | Multi-stage build, non-root user, health checks; minor issue with hardcoded port in CMD |
| **Monitoring** | 7/10 | B- | Good component-level health checks; structured logging; but no Prometheus metrics; no request tracing |
| **Test Coverage** | 4/10 | F | Only happy-path tests; no mocking of external APIs; no InfluxDB write tests; no error scenario tests |
| **Overall** | 6.5/10 | C+ | Solid foundation with good patterns, but significant test coverage gaps and several security/correctness issues |

---

## CRITICAL Issues

### CRIT-01: API Key Leaked in Query Parameters When auth_mode=query
**Severity**: CRITICAL | **File**: `src/main.py` | **Lines**: 201-202

When `WEATHER_API_AUTH_MODE=query`, the API key is appended as a query parameter (`appid`). This means the key appears in:
- Server access logs (both on the weather-api side and any reverse proxy)
- Browser history if ever called from a frontend
- aiohttp debug logs
- Any HTTP proxy or WAF logs in the path

```python
# CURRENT (main.py:201-202) - API key in query string
else:
    params["appid"] = self.api_key
```

**Impact**: API key exposure could lead to unauthorized usage of the OpenWeatherMap account, billing charges, and rate-limit exhaustion.

**Fix**: The header-based auth mode (`X-API-Key` header) is the correct default and should be strongly preferred. Add a warning at startup when query mode is explicitly chosen. The README already documents the header-first approach, but the code should log a security advisory:

```python
# FIX: Add warning in __init__ when query mode is configured
if self.auth_mode == "query":
    logger.warning(
        "SECURITY: WEATHER_API_AUTH_MODE=query sends API key in URL parameters. "
        "This exposes the key in logs and proxy caches. Use 'header' mode unless "
        "your API plan does not support header authentication."
    )
```

**Note**: OpenWeatherMap's free-tier API only supports `appid` query parameter, NOT custom headers like `X-API-Key`. The header mode (`X-API-Key`) will return 401 on free-tier keys. This means most users will be forced into the insecure query mode, making this a practical security concern.

---

### CRIT-02: No Input Validation on WEATHER_LOCATION Environment Variable
**Severity**: HIGH-CRITICAL | **File**: `src/main.py` | **Line**: 61

The `WEATHER_LOCATION` environment variable is passed directly to the OpenWeatherMap API without any validation or sanitization:

```python
# CURRENT (main.py:61)
self.location = os.getenv('WEATHER_LOCATION', 'Las Vegas')

# Later used in (main.py:193):
params = {
    "q": self.location,
    "units": "metric"
}
```

**Impact**: While this is an environment variable (not user input), a malicious or misconfigured value could cause unexpected behavior. More importantly, if the `/current-weather` endpoint is later extended to accept a `location` query parameter (as the README suggests it should: "Query parameters: location (optional): Override default location"), this becomes a direct injection vector.

**Fix**: Add basic validation on location values:

```python
# FIX: Validate location at initialization
import re
location = os.getenv('WEATHER_LOCATION', 'Las Vegas')
if not re.match(r'^[a-zA-Z\s,.-]{1,100}$', location):
    raise ValueError(f"Invalid WEATHER_LOCATION: must be alphanumeric with spaces/commas, got '{location}'")
self.location = location
```

---

## HIGH Priority Issues

### HIGH-01: `datetime.utcnow()` is Deprecated - Use `datetime.now(timezone.utc)` Instead
**Severity**: HIGH | **File**: `src/main.py` | **Lines**: 208, 240, 293 | **File**: `src/health_check.py` | **Lines**: 25, 36, 60, 65, 103

`datetime.utcnow()` was deprecated in Python 3.12 (PEP 587). The code already imports `timezone` and calls `.replace(tzinfo=timezone.utc)`, but this is subtly different from `datetime.now(timezone.utc)` -- `utcnow()` returns a naive datetime and then `replace()` attaches timezone info without conversion. While functionally equivalent for UTC, it is deprecated and will produce warnings in future Python versions.

```python
# CURRENT (appears 7+ times across both files)
datetime.utcnow().replace(tzinfo=timezone.utc)

# FIX: Replace every occurrence with:
datetime.now(timezone.utc)
```

Affected locations:
- `src/main.py:208` - `fetch_weather()` timestamp generation
- `src/main.py:240` - `get_current_weather()` cache check
- `src/main.py:293` - `store_in_influxdb()` write timestamp
- `src/health_check.py:25` - `__init__` start_time
- `src/health_check.py:36` - `handle()` current time
- `src/health_check.py:60` - error handler timestamp
- `src/health_check.py:65` - `get_uptime_seconds()`
- `src/health_check.py:103` - `_component_status()` write age check

---

### HIGH-02: Version Mismatch Between `__init__.py` and `main.py`
**Severity**: HIGH | **File**: `src/__init__.py` | **Line**: 2

`__init__.py` declares `__version__ = "1.0.0"` while `main.py` declares `SERVICE_VERSION = "2.2.0"`. This is confusing and could cause issues for any tooling that reads the package version.

```python
# CURRENT (__init__.py:2)
__version__ = "1.0.0"

# FIX: Sync with main.py
__version__ = "2.2.0"
```

Better yet, define the version in one place and import it:

```python
# __init__.py
__version__ = "2.2.0"

# main.py
from . import __version__
SERVICE_VERSION = __version__
```

---

### HIGH-03: requirements-prod.txt is Completely Out of Sync with Actual Dependencies
**Severity**: HIGH | **Files**: `requirements.txt`, `requirements-prod.txt`

The production requirements file lists completely different packages than what the code actually uses:

```
# requirements-prod.txt (WRONG)
aiohttp>=3.13.2,<4.0.0
influxdb-client>=1.49.0,<2.0.0    # <-- WRONG: code uses influxdb3-python / InfluxDBClient3
python-dotenv>=1.0.1,<2.0.0
requests>=2.32.3,<3.0.0           # <-- Not used anywhere in the code
```

Critical issues:
1. **`influxdb-client` vs `influxdb3-python`**: The code imports `from influxdb_client_3 import InfluxDBClient3`, which comes from `influxdb3-python`, NOT `influxdb-client`. Installing `influxdb-client` will NOT provide the required module.
2. **`requests` is not used**: The code uses `aiohttp` for HTTP requests. `requests` is a synchronous library not used anywhere.
3. **Missing `fastapi`**: The core web framework is not listed in production requirements.
4. **Missing `uvicorn`**: The ASGI server is not listed.
5. **Missing `pydantic`**: Used for data models, not listed.

**Fix**: Rebuild `requirements-prod.txt` to match actual runtime dependencies:

```
# requirements-prod.txt (FIXED)
fastapi>=0.123.0,<0.124.0
uvicorn[standard]>=0.32.0,<0.33.0
aiohttp>=3.13.2,<4.0.0
python-dotenv>=1.0.0,<2.0.0
pydantic>=2.9.0,<3.0.0
influxdb3-python[pandas]>=0.3.0,<1.0.0
```

---

### HIGH-04: InfluxDB Initialization Does Not Actually Test the Connection
**Severity**: HIGH | **File**: `src/main.py` | **Lines**: 146-169

The `_initialize_influxdb()` method claims to try each fallback URL, but it never actually tests the connection. The `InfluxDBClient3()` constructor does not make a network call -- it just creates an object. The comment on line 158-159 even acknowledges this:

```python
# CURRENT (main.py:158-159)
# Test connection by attempting a simple operation
# Note: InfluxDBClient3 doesn't have a direct ping, so we'll test on first write
```

This means:
- The "fallback URL" logic never actually fails over during initialization
- `self.working_influxdb_host` is always set to the first URL in the list
- The log message "Successfully initialized InfluxDB client" is misleading -- no connection was verified

**Fix**: Attempt a lightweight read query to verify connectivity:

```python
async def _initialize_influxdb(self) -> InfluxDBClient3 | None:
    for url in self.influxdb_urls:
        try:
            logger.info(f"Attempting to connect to InfluxDB at {url}")
            client = InfluxDBClient3(
                host=url,
                token=self.influxdb_token,
                database=self.influxdb_bucket,
                org=self.influxdb_org
            )
            # Actually test the connection
            await asyncio.to_thread(client.query, "SELECT 1")
            self.working_influxdb_host = url
            logger.info(f"Successfully verified InfluxDB connection at: {url}")
            return client
        except Exception as e:
            logger.warning(f"Failed to connect to InfluxDB at {url}: {e}")
            continue
    return None
```

---

### HIGH-05: Unreachable Dead Code in `store_in_influxdb()`
**Severity**: MEDIUM-HIGH | **File**: `src/main.py` | **Lines**: 266-288

There is a redundant null check for `self.influxdb_client` that can never be reached:

```python
async def store_in_influxdb(self, weather: dict[str, Any]):
    if not weather:
        return

    if not self.influxdb_client:               # Line 266: First check
        logger.warning("InfluxDB client not initialized, skipping write")
        return                                  # Returns here if None

    timestamp = datetime.fromisoformat(weather['timestamp'])
    point = Point("weather") ...               # Build point

    # If client initialization failed, try to reinitialize
    if not self.influxdb_client:               # Line 283: UNREACHABLE - already returned above
        logger.warning("...")
        self.influxdb_client = await self._initialize_influxdb()
        ...
```

The second `if not self.influxdb_client:` block at line 283 is dead code because the function already returns at line 268 if the client is None.

**Fix**: Remove the redundant check at line 283-288, or restructure so the reinitialization attempt happens instead of the early return:

```python
async def store_in_influxdb(self, weather: dict[str, Any]):
    if not weather:
        return

    if not self.influxdb_client:
        logger.warning("InfluxDB client not available, attempting to reinitialize...")
        self.influxdb_client = await self._initialize_influxdb()
        if not self.influxdb_client:
            logger.error("Cannot write to InfluxDB - client unavailable after reinit attempt")
            return

    # ... rest of method (build point, write with retries)
```

---

## MEDIUM Priority Issues

### MED-01: `/metrics` Endpoint is an Exact Duplicate of `/health`
**Severity**: MEDIUM | **File**: `src/main.py` | **Lines**: 428-434

Both `/health` and `/metrics` return identical data from `health_handler.handle()`. This is confusing and violates the principle of least surprise. The README describes `/metrics` as "Lightweight JSON metrics (mirror of /health data, Prometheus wrapper planned)."

```python
# CURRENT - identical implementation
@app.get("/health")
async def health():
    return await weather_service.health_handler.handle(weather_service)

@app.get("/metrics")
async def metrics():
    return await weather_service.health_handler.handle(weather_service)
```

**Fix**: Either differentiate the endpoints (metrics should return Prometheus-format or just numeric metrics) or remove `/metrics` until Prometheus integration is implemented. At minimum, add a comment explaining the duplication:

```python
@app.get("/metrics")
async def metrics():
    """Lightweight metrics (currently mirrors /health; Prometheus format planned)"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return {
        "fetch_count": weather_service.fetch_count,
        "cache_hits": weather_service.cache_hits,
        "cache_misses": weather_service.cache_misses,
        "influx_write_success_count": weather_service.influx_write_success_count,
        "influx_write_failure_count": weather_service.influx_write_failure_count,
        "cache_ttl": weather_service.cache_ttl,
    }
```

---

### MED-02: InfluxDB Point Missing `feels_like` Field
**Severity**: MEDIUM | **File**: `src/main.py` | **Lines**: 272-280

The weather data fetched includes `feels_like` and `description`, but only `temperature`, `humidity`, `pressure`, `wind_speed`, and `cloudiness` are written to InfluxDB. Two useful fields are lost:

```python
# CURRENT - missing feels_like and description
point = Point("weather") \
    .tag("location", weather['location']) \
    .tag("condition", weather['condition']) \
    .field("temperature", float(weather['temperature'])) \
    .field("humidity", int(weather['humidity'])) \
    .field("pressure", int(weather['pressure'])) \
    .field("wind_speed", float(weather['wind_speed'])) \
    .field("cloudiness", int(weather['cloudiness'])) \
    .time(timestamp)
```

**Fix**: Add the missing fields:

```python
point = Point("weather") \
    .tag("location", weather['location']) \
    .tag("condition", weather['condition']) \
    .tag("description", weather['description']) \
    .field("temperature", float(weather['temperature'])) \
    .field("feels_like", float(weather['feels_like'])) \
    .field("humidity", int(weather['humidity'])) \
    .field("pressure", int(weather['pressure'])) \
    .field("wind_speed", float(weather['wind_speed'])) \
    .field("cloudiness", int(weather['cloudiness'])) \
    .time(timestamp)
```

---

### MED-03: CORS Origins Are Hardcoded and Limited
**Severity**: MEDIUM | **File**: `src/main.py` | **Lines**: 396-401

CORS is hardcoded to only allow `localhost:3000` and `localhost:3001`. This will break if:
- The health-dashboard runs on a different port
- The service is accessed from a different host in production
- Docker networking uses different hostnames

```python
# CURRENT
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    ...
)
```

**Fix**: Make CORS origins configurable via environment variable:

```python
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:3001')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins.split(',')],
    allow_credentials=True,
    allow_methods=["GET"],  # This is a read-only API
    allow_headers=["*"],
)
```

Also note: `allow_methods=["*"]` is overly permissive for a read-only weather API. It should be restricted to `["GET", "OPTIONS"]`.

---

### MED-04: No Rate Limiting on API Endpoints
**Severity**: MEDIUM | **File**: `src/main.py`

There is no rate limiting on any endpoint. The `/current-weather` endpoint triggers a cache-miss fetch to OpenWeatherMap when the cache is expired, meaning a burst of requests during cache expiry could trigger multiple simultaneous API calls.

**Impact**: OpenWeatherMap free tier allows 60 calls/minute. Without rate limiting, a burst of concurrent requests during cache expiry could exhaust the API quota.

**Fix**: The cache already prevents most redundant calls, but adding a lock would prevent thundering herd:

```python
import asyncio

class WeatherService:
    def __init__(self):
        ...
        self._fetch_lock = asyncio.Lock()

    async def get_current_weather(self) -> dict[str, Any] | None:
        # Check cache first (no lock needed for reads)
        now = datetime.now(timezone.utc)
        if self.cached_weather and self.cache_time:
            age = (now - self.cache_time).total_seconds()
            if age < self.cache_ttl:
                self.cache_hits += 1
                return self.cached_weather

        # Lock to prevent thundering herd on cache miss
        async with self._fetch_lock:
            # Double-check cache after acquiring lock
            if self.cached_weather and self.cache_time:
                age = (datetime.now(timezone.utc) - self.cache_time).total_seconds()
                if age < self.cache_ttl:
                    self.cache_hits += 1
                    return self.cached_weather

            self.cache_misses += 1
            weather = await self.fetch_weather()
            if weather:
                self.cached_weather = weather
                self.cache_time = datetime.now(timezone.utc)
                self.last_successful_fetch = self.cache_time
                await self.store_in_influxdb(weather)
            return weather
```

---

### MED-05: Background Task Error Recovery is Coarse-Grained
**Severity**: MEDIUM | **File**: `src/main.py` | **Lines**: 328-342

When the continuous fetch loop encounters an error, it waits 300 seconds (5 minutes) regardless of the error type. A transient network blip and a permanent configuration error get the same treatment:

```python
# CURRENT
except Exception as e:
    self.last_background_error = str(e)
    logger.error(f"Error in continuous loop: {e}")
    await asyncio.sleep(300)  # Always 5 minutes
```

**Fix**: Implement progressive backoff based on consecutive failures:

```python
async def run_continuous(self):
    consecutive_failures = 0
    while True:
        try:
            await self.get_current_weather()
            consecutive_failures = 0  # Reset on success
            await asyncio.sleep(self.cache_ttl)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            consecutive_failures += 1
            self.last_background_error = str(e)
            backoff = min(300 * consecutive_failures, 1800)  # Max 30 minutes
            logger.error(f"Error in continuous loop (failure #{consecutive_failures}): {e}. "
                         f"Retrying in {backoff}s")
            await asyncio.sleep(backoff)
```

---

### MED-06: `sys.path` Manipulation for Shared Module Import
**Severity**: MEDIUM | **File**: `src/main.py` | **Lines**: 23-24

Appending to `sys.path` at module level is fragile and can cause import conflicts:

```python
# CURRENT
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from shared.logging_config import setup_logging
```

**Impact**: This path manipulation happens at import time, affects the entire Python process, and the relative path `../../shared` may resolve incorrectly depending on how the module is loaded (e.g., directly vs. as a package).

**Fix**: The Dockerfile already sets `PYTHONPATH=/app`, which should make `shared` importable without path manipulation. Remove the `sys.path.append` line and rely on `PYTHONPATH`:

```python
# FIX: Remove sys.path manipulation, rely on PYTHONPATH=/app from Dockerfile/pytest.ini
# sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))  # REMOVE
from shared.logging_config import setup_logging
```

The `pytest.ini` already has `pythonpath = . ../..` which handles the test environment.

---

### MED-07: Dockerfile CMD Hardcodes Port 8009 Despite SERVICE_PORT Env Var
**Severity**: MEDIUM | **File**: `Dockerfile` | **Line**: 55

The Dockerfile hardcodes `--port 8009` in CMD, ignoring the `SERVICE_PORT` environment variable that `main.py` respects:

```dockerfile
# CURRENT
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8009"]
```

Meanwhile `main.py:472` reads `SERVICE_PORT`:
```python
port = int(os.getenv('SERVICE_PORT', '8009'))
```

**Fix**: Use shell form or make the port configurable:

```dockerfile
CMD uvicorn src.main:app --host 0.0.0.0 --port ${SERVICE_PORT:-8009}
```

Or use the `main.py` entrypoint which reads the env var:

```dockerfile
CMD ["python", "-m", "src.main"]
```

---

## LOW Priority Issues

### LOW-01: f-string Logging Should Use % Formatting
**Severity**: LOW | **File**: `src/main.py` | **Multiple lines**

Several log statements use f-strings instead of the `%`-style formatting recommended for `logging`:

```python
# CURRENT (multiple occurrences)
logger.info(f"InfluxDB fallback URLs configured: {len(self.influxdb_urls)} URLs")
logger.info(f"Attempting to connect to InfluxDB at {url}")
logger.info(f"Fetched weather: {weather['temperature']}C, {weather['condition']}")
```

Using f-strings means the string is always interpolated, even if the log level is above INFO. With `%`-style, interpolation only happens if the message will be emitted:

```python
# FIX
logger.info("InfluxDB fallback URLs configured: %d URLs (original + %d fallbacks)",
            len(self.influxdb_urls), len(fallback_hosts))
logger.info("Attempting to connect to InfluxDB at %s", url)
logger.info("Fetched weather: %.1fC, %s", weather['temperature'], weather['condition'])
```

---

### LOW-02: Unicode Emoji Characters in Log Messages
**Severity**: LOW | **File**: `src/main.py` | **Lines**: 161, 168

Log messages contain emoji characters which can cause issues with some log aggregation systems, terminals, and parsers:

```python
logger.info(f"... Successfully initialized InfluxDB client with URL: {url}")  # line 161 has checkmark emoji
logger.error(f"... Failed to connect to InfluxDB with any URL: {self.influxdb_urls}")  # line 168 has X emoji
```

**Fix**: Replace emoji with text prefixes:

```python
logger.info("[OK] Successfully initialized InfluxDB client with URL: %s", url)
logger.error("[FAIL] Failed to connect to InfluxDB with any URL: %s", self.influxdb_urls)
```

---

### LOW-03: Cache is Single-Location Only
**Severity**: LOW | **File**: `src/main.py` | **Lines**: 98-101

The cache stores only one location's weather data. If the README's documented `location` query parameter were implemented, requests for different locations would thrash the cache.

```python
# CURRENT
self.cached_weather: dict[str, Any] | None = None
self.cache_time: datetime | None = None
```

**Fix**: If multi-location support is planned, use a dict keyed by location:

```python
self._cache: dict[str, tuple[dict[str, Any], datetime]] = {}

async def get_current_weather(self, location: str | None = None) -> dict[str, Any] | None:
    loc = location or self.location
    now = datetime.now(timezone.utc)
    if loc in self._cache:
        data, cache_time = self._cache[loc]
        if (now - cache_time).total_seconds() < self.cache_ttl:
            self.cache_hits += 1
            return data
    # ... fetch and cache
```

---

### LOW-04: No `__init__.py` in tests/ Directory
**Severity**: LOW | **File**: `tests/`

The tests directory lacks an `__init__.py` file. While pytest discovers tests without it, having one ensures consistent import behavior and prevents namespace collisions when running tests across multiple services.

---

### LOW-05: `--disable-warnings` in pytest.ini Suppresses Useful Deprecation Warnings
**Severity**: LOW | **File**: `pytest.ini` | **Line**: 19

```ini
addopts =
    --disable-warnings
```

This suppresses all warnings, including Python deprecation warnings that would flag the `datetime.utcnow()` issue (HIGH-01). Remove this flag to see important warnings during development.

---

## Security Findings

### SEC-01: API Key Exposure via Query Parameters (see CRIT-01)
Already covered above. The OpenWeatherMap free tier only supports `appid` query parameter, making header mode non-functional for most users.

### SEC-02: No HTTPS Enforcement
**File**: `src/main.py`

The service runs on plain HTTP. While TLS termination is typically handled by a reverse proxy in production, the service itself does not enforce or redirect to HTTPS. The `base_url` for OpenWeatherMap is correctly using HTTPS (line 62).

### SEC-03: InfluxDB Token in Environment Variable
**File**: `src/main.py` | **Line**: 92

The InfluxDB token is read from an environment variable, which is standard practice. However, the token value could appear in:
- Docker inspect output
- Process environment listings (`/proc/PID/environ`)
- Container orchestrator logs

**Recommendation**: For production, use Docker secrets or a secrets manager. The current env-var approach is acceptable for development.

### SEC-04: CORS `allow_credentials=True` with Specific Origins
**File**: `src/main.py` | **Line**: 398

`allow_credentials=True` is set, which means cookies and authorization headers are sent with cross-origin requests. Since origins are restricted to localhost, this is low risk but should be reviewed if origins are made configurable.

### SEC-05: No Authentication on Any Endpoint
**File**: `src/main.py`

None of the endpoints (`/health`, `/metrics`, `/current-weather`, `/cache/stats`) require authentication. For an internal microservice this may be acceptable, but `/metrics` and `/cache/stats` expose operational data that could aid an attacker in reconnaissance.

---

## Performance Recommendations

### PERF-01: Thundering Herd on Cache Expiry
When the cache TTL expires, multiple concurrent requests to `/current-weather` will all see the cache as expired and simultaneously call `fetch_weather()`. This multiplies external API calls.

**Fix**: See MED-04 above (asyncio.Lock with double-checked locking).

### PERF-02: Background Fetch Interval Equals Cache TTL
**File**: `src/main.py` | **Line**: 335

The background task sleeps for `cache_ttl` seconds (default 900s = 15 minutes). The README documents `FETCH_INTERVAL_SECONDS=300` as a separate config, but the code does not use this variable -- it uses the cache TTL for both.

```python
# CURRENT - uses cache_ttl for fetch interval
await asyncio.sleep(self.cache_ttl)
```

**Fix**: Add a separate fetch interval:

```python
self.fetch_interval = int(os.getenv('FETCH_INTERVAL_SECONDS', '300'))

# In run_continuous():
await asyncio.sleep(self.fetch_interval)
```

This ensures the cache is always warm (fetch every 5 min, cache valid for 15 min), matching the documented architecture.

### PERF-03: `asyncio.to_thread()` for InfluxDB Writes
**File**: `src/main.py` | **Line**: 292

Using `asyncio.to_thread()` for InfluxDB writes is correct (the client is synchronous), but each write creates a new thread. For high-frequency writes, consider using a thread pool:

```python
from concurrent.futures import ThreadPoolExecutor

class WeatherService:
    def __init__(self):
        ...
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="influxdb")

    async def store_in_influxdb(self, weather):
        ...
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self.influxdb_client.write, point)
```

### PERF-04: InfluxDB URL Parsing is Fragile
**File**: `src/main.py` | **Lines**: 70-76

The URL parsing logic uses string splitting which can fail on edge cases:

```python
# CURRENT - fragile parsing
if '://' in influxdb_url:
    self.influxdb_host = influxdb_url.split('://')[1].split(':')[0]
    self.influxdb_port = influxdb_url.split(':')[-1] if ':' in influxdb_url.split('://')[1] else '8086'
```

**Fix**: Use `urllib.parse`:

```python
from urllib.parse import urlparse

parsed = urlparse(influxdb_url)
self.influxdb_host = parsed.hostname or 'influxdb'
self.influxdb_port = str(parsed.port or 8086)
```

---

## Test Coverage Analysis

### Current State: 4/10

The test suite has **significant gaps** that undermine confidence in the service:

#### What IS Tested (Positive):
- Root endpoint returns service info (`test_main.py`)
- Health endpoint returns healthy status (`test_main.py`, `test_health_check.py`)
- Metrics endpoint returns data (`test_main.py`)
- CORS headers present (`test_main.py`)
- OpenAPI docs accessible (`test_main.py`)
- Cache stats endpoint returns structure (`test_weather_service.py`)
- Health check handler components and uptime (`test_health_check.py`)

#### What is NOT Tested (Critical Gaps):

| Missing Test | Priority | Description |
|---|---|---|
| `fetch_weather()` success path | CRITICAL | No test mocks OpenWeatherMap API and verifies response parsing |
| `fetch_weather()` error paths | CRITICAL | No test for 401, 429, 500, timeout, DNS failure responses |
| `store_in_influxdb()` | CRITICAL | No test verifies InfluxDB Point construction or write logic |
| InfluxDB retry/backoff | HIGH | No test for retry logic, exponential backoff, or reconnection |
| Cache hit/miss logic | HIGH | No test verifies cache TTL expiry and refresh behavior |
| Background task lifecycle | HIGH | No test for `start_background_task()`, `stop_background_task()`, or `run_continuous()` |
| Auth mode switching | MEDIUM | No test verifies header vs query parameter auth behavior |
| InfluxDB fallback URLs | MEDIUM | No test for the hostname fallback mechanism |
| Service startup/shutdown | MEDIUM | No test for the lifespan handlers |
| WeatherService initialization | MEDIUM | No test for missing env vars, invalid config |
| `WeatherResponse` model validation | LOW | No test that Pydantic rejects invalid data |
| Health check degraded states | LOW | No test for degraded/initializing status paths |

#### Test Health Check Stub is Missing Attributes:
**File**: `tests/test_health_check.py` | **Line**: 13-32

The `_healthy_service_stub()` is missing attributes that `_component_status()` checks:
- `last_influx_write_error` (checked at line 98 of `health_check.py`)
- `influx_write_failure_count` (checked at line 74)
- `influx_write_success_count` (checked at line 77)

This means the health check tests would fail if the code paths that access these attributes are exercised. The stub passes only because the happy path does not hit those branches.

#### Example Test That Should Exist:

```python
# test_weather_service.py - Mock OpenWeatherMap API
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_fetch_weather_success():
    """Test successful weather fetch from OpenWeatherMap"""
    mock_response_data = {
        "main": {"temp": 25.0, "feels_like": 23.0, "humidity": 45, "pressure": 1013},
        "weather": [{"main": "Clear", "description": "clear sky"}],
        "wind": {"speed": 3.5},
        "clouds": {"all": 10},
        "name": "Las Vegas"
    }

    with patch.dict(os.environ, {
        'WEATHER_API_KEY': 'test-key',
        'INFLUXDB_TOKEN': 'test-token'
    }):
        service = WeatherService()
        service.session = MagicMock()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=False)
        service.session.get = MagicMock(return_value=mock_context)

        weather = await service.fetch_weather()

        assert weather is not None
        assert weather['temperature'] == 25.0
        assert weather['condition'] == 'Clear'
        assert weather['location'] == 'Las Vegas'

@pytest.mark.asyncio
async def test_fetch_weather_api_down():
    """Test graceful degradation when OpenWeatherMap is down"""
    # Should return cached data (or None) without raising
    ...

@pytest.mark.asyncio
async def test_store_in_influxdb_retry_on_failure():
    """Test that InfluxDB writes retry with exponential backoff"""
    ...

@pytest.mark.asyncio
async def test_cache_expiry():
    """Test that expired cache triggers a fresh fetch"""
    ...
```

---

## Architecture Recommendations

### ARCH-01: README Documents Endpoints That Do Not Exist
The README documents three endpoints that are not implemented:
- `GET /forecast` - 24-hour weather forecast
- `GET /historical` - Historical weather queries from InfluxDB
- `GET /current-weather?location=...` - Location query parameter

These should either be implemented or removed from the README to avoid confusion.

### ARCH-02: Consider Separating Concerns
While the single-file approach (`main.py`) is documented as intentional (following carbon-intensity/air-quality patterns), at ~470 lines it is approaching the limit of comfortable single-file maintenance. The `WeatherService` class handles:
- HTTP client management
- External API calls
- Caching
- InfluxDB writing with retries and fallback
- Background task management
- Health tracking

Consider extracting the InfluxDB writer into a shared utility, as other services (carbon-intensity, air-quality) likely have identical write-with-retry-and-fallback logic.

### ARCH-03: No Graceful Shutdown Signal Handling
The service relies on FastAPI's shutdown event, but there is no explicit signal handler for SIGTERM/SIGINT. In Kubernetes or Docker, a SIGTERM is sent before the container is killed. While uvicorn handles this, adding explicit handling ensures the background task and InfluxDB client are cleaned up properly.

### ARCH-04: Health Check Does Not Return HTTP 503 for Degraded State
**File**: `src/main.py` | **Lines**: 419-425

The `/health` endpoint always returns HTTP 200, even when the status is "degraded" or "unhealthy". Load balancers and orchestrators use the HTTP status code, not the JSON body, to determine health.

```python
# CURRENT - always 200
@app.get("/health")
async def health():
    if not weather_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return await weather_service.health_handler.handle(weather_service)
```

**Fix**:

```python
@app.get("/health")
async def health():
    if not weather_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    result = await weather_service.health_handler.handle(weather_service)
    status_code = 200 if result.get("status") == "healthy" else 503
    return JSONResponse(content=result, status_code=status_code)
```

---

## Summary of All Issues by Priority

| ID | Priority | Category | Summary |
|---|---|---|---|
| CRIT-01 | CRITICAL | Security | API key leaked in query parameters with auth_mode=query |
| CRIT-02 | HIGH-CRITICAL | Security | No validation on WEATHER_LOCATION |
| HIGH-01 | HIGH | Code Quality | Deprecated `datetime.utcnow()` used throughout |
| HIGH-02 | HIGH | Code Quality | Version mismatch `__init__.py` (1.0.0) vs `main.py` (2.2.0) |
| HIGH-03 | HIGH | Deployment | `requirements-prod.txt` lists wrong packages entirely |
| HIGH-04 | HIGH | Reliability | InfluxDB initialization never tests the connection |
| HIGH-05 | MEDIUM-HIGH | Code Quality | Dead code - unreachable InfluxDB reinitialization block |
| MED-01 | MEDIUM | API Design | `/metrics` is exact duplicate of `/health` |
| MED-02 | MEDIUM | Data Quality | InfluxDB write missing `feels_like` field |
| MED-03 | MEDIUM | Security | Hardcoded CORS origins |
| MED-04 | MEDIUM | Performance | No thundering herd protection on cache miss |
| MED-05 | MEDIUM | Reliability | Background task error recovery is not progressive |
| MED-06 | MEDIUM | Code Quality | Fragile `sys.path` manipulation for shared imports |
| MED-07 | MEDIUM | Deployment | Dockerfile CMD hardcodes port, ignoring SERVICE_PORT |
| LOW-01 | LOW | Code Quality | f-string logging instead of %-style |
| LOW-02 | LOW | Code Quality | Emoji characters in log messages |
| LOW-03 | LOW | Feature | Cache is single-location only |
| LOW-04 | LOW | Testing | Missing `__init__.py` in tests directory |
| LOW-05 | LOW | Testing | `--disable-warnings` suppresses useful deprecation notices |
| PERF-01 | MEDIUM | Performance | Thundering herd on cache expiry (same as MED-04) |
| PERF-02 | MEDIUM | Performance | Background fetch interval equals cache TTL (should be shorter) |
| PERF-03 | LOW | Performance | Thread-per-write for InfluxDB |
| PERF-04 | LOW | Code Quality | Fragile URL parsing with string splits |
| SEC-05 | LOW | Security | No authentication on operational endpoints |
| ARCH-01 | MEDIUM | Documentation | README documents endpoints that do not exist |
| ARCH-02 | LOW | Architecture | Single file approaching maintainability limit |
| ARCH-03 | LOW | Reliability | No explicit graceful shutdown signal handling |
| ARCH-04 | MEDIUM | Reliability | Health check returns 200 for degraded state |
| TESTS | HIGH | Testing | Test coverage at ~4/10 with critical gaps (see Test Coverage Analysis) |

---

**Overall Health Score: 6.5 / 10**

The weather-api service has a solid foundation with good patterns (cache-first, retry with backoff, component health checks, structured logging, proper Docker multi-stage build). However, it suffers from significant test coverage gaps, a completely broken `requirements-prod.txt`, deprecated API usage, and several correctness issues (dead code, missing InfluxDB fields, undocumented/unimplemented endpoints). The security posture is acceptable for an internal microservice but has room for improvement around API key handling.

**Top 5 Actions (in priority order)**:
1. Fix `requirements-prod.txt` to list actual dependencies (HIGH-03) -- production deployment may be broken
2. Add unit tests with mocked external dependencies for `fetch_weather()` and `store_in_influxdb()` (TESTS)
3. Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)` (HIGH-01)
4. Fix dead code in `store_in_influxdb()` and add InfluxDB connection verification (HIGH-04, HIGH-05)
5. Add thundering herd protection with async lock on cache miss (MED-04)

---

**Last Updated**: 2026-02-06
**Reviewer**: Claude Opus 4.6 (Automated Deep Review)
