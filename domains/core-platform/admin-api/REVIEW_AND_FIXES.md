# Admin API - Deep Code Review & Fixes (Revised)

**Service**: admin-api (Tier 1 Mission-Critical - SYSTEM CONTROL PLANE)
**Port**: 8004
**Review Date**: 2026-02-06
**Reviewer**: Claude Opus 4.6 Deep Analysis (Revision 2 -- Full Re-Read of All Files)
**Files Reviewed**: 24 source files, 14 test files, 2 config files, 2 shared modules
**Overall Health Score**: 5.5 / 10

> **Note on Revision 2**: This revision corrects several inaccuracies from the initial
> automated review. The earlier report incorrectly flagged: (a) SSRF in ha_proxy as
> CRITICAL when `_validate_entity_id` regex prevents it, (b) Flux injection in
> devices/events endpoints when `_sanitize_flux_value` is present, (c) hardcoded health
> dependencies when `main.py` performs real async checks, (d) blocking Docker calls when
> `asyncio.to_thread` is used, and (e) deadlock in `metrics_tracker` when the private
> `_get_stats_unlocked` method avoids re-acquiring the lock. This revision is based on
> a complete re-read of every source file, test file, and shared module.

---

## Executive Summary

The admin-api is the **system control plane** for the entire HomeIQ platform -- it manages
Docker containers, health monitoring, configuration, MQTT/Zigbee settings, API keys, and
proxies requests to Home Assistant. As a Tier 1 service, it carries the highest security
burden of any service in the platform.

The service demonstrates competent architecture with proper authentication enforcement,
SSRF prevention patterns, Flux query sanitization in device/event queries, and real
dependency health checks. However, it suffers from **critical security gaps** in its
secondary entry point (`simple_main.py`), **MQTT credential exposure** through a public
endpoint, **Flux injection vectors** in the InfluxDB statistics client (separate from the
sanitized device/event queries), and **systematic connection pool waste** that creates
performance bottlenecks under load. Test coverage is approximately 55%, with zero tests
for Docker management, MQTT configuration, HA proxy, and API key service endpoints.

**Score Breakdown**:
- Security: 4/10 (critical gaps in simple_main.py, MQTT exposure, API key in URLs)
- Architecture: 6/10 (good separation, but dual alert implementations, leaked globals)
- Performance: 5/10 (no connection pooling, per-request client creation)
- Test Coverage: 5/10 (~55% coverage, major endpoint gaps)
- Code Quality: 7/10 (generally clean, good patterns where present)
- Reliability: 6/10 (graceful fallbacks, but in-memory state lost on restart)

---

## CRITICAL Issues

### CRIT-01: `simple_main.py` -- Wildcard CORS with Credentials (Authentication Bypass Vector)

**File**: `c:\cursor\HomeIQ\services\admin-api\src\simple_main.py`, lines 53-59
**Severity**: CRITICAL
**Category**: Security

```python
# CURRENT (DANGEROUS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Any origin can make requests
    allow_credentials=True,   # Cookies/auth headers sent automatically
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impact**: This combination violates the CORS specification and enables credential-based
cross-origin attacks. Any malicious website can make authenticated requests to admin-api if
a user has credentials cached in their browser. Additionally, `simple_main.py` has **zero
authentication** on any endpoint -- no API key, no JWT, no auth middleware whatsoever.

**Fix**: Either remove `simple_main.py` entirely (it appears to be a development artifact
not referenced by the production Dockerfile) or add authentication and restrict CORS:

```python
# FIXED
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

### CRIT-02: MQTT GET Endpoint Exposes Credentials Without Authentication

**File**: `c:\cursor\HomeIQ\services\admin-api\src\mqtt_config_endpoints.py`, lines 142-152
**Severity**: CRITICAL
**Category**: Security

```python
# CURRENT - Public endpoint returning MQTT password
@public_router.get("/mqtt", response_model=MqttConfig)
async def get_mqtt_config() -> MqttConfig:
    """
    This endpoint is public (no authentication required) to allow the dashboard
    to load existing configuration. Configuration values are not sensitive
    (they're already in environment variables or config files).
    """
    data = _load_effective_config()
    return MqttConfig.model_validate(data, from_attributes=False)
```

The `MqttConfig` model at lines 44-64 includes `MQTT_PASSWORD` (line 53-56). The comment
claims "configuration values are not sensitive" but MQTT credentials grant access to the
MQTT broker which controls all Zigbee devices. The `_load_effective_config()` function at
lines 121-132 loads `MQTT_PASSWORD` from both environment variables and the JSON config
file, returning it in full.

Any unauthenticated HTTP client can call `GET /api/v1/config/integrations/mqtt` and
receive the plaintext MQTT password.

**Fix**: Either require authentication on the GET endpoint, or mask the password field
before returning:

```python
@public_router.get("/mqtt")
async def get_mqtt_config() -> dict:
    data = _load_effective_config()
    config = MqttConfig.model_validate(data, from_attributes=False)
    result = config.model_dump(by_alias=True)
    if result.get("MQTT_PASSWORD"):
        result["MQTT_PASSWORD"] = "********"
    return result
```

---

### CRIT-03: API Keys Embedded in Validation URLs (Logged in Clear Text)

**File**: `c:\cursor\HomeIQ\services\admin-api\src\api_key_service.py`, lines 49, 70, 240
**Severity**: CRITICAL
**Category**: Security

```python
# Line 49: API key placed directly in URL query string
'validation_url': 'https://api.openweathermap.org/data/2.5/weather?lat=0&lon=0&appid={key}',

# Line 70: Same pattern with AirNow
'validation_url': 'https://www.airnowapi.org/aq/observation/zipCode/current/?format=application/json&zipCode=10001&distance=25&API_KEY={key}',

# Line 240: key substituted into URL
test_url = config['validation_url'].format(key=api_key)
```

API keys in URL query strings are logged by web servers, reverse proxies, CDNs, and
browser history. The `aiohttp` library also logs URLs at DEBUG level. Any log aggregation
system receiving these logs will contain the plaintext API keys.

**Fix**: Use headers for API key transmission where the third-party API supports it, or
ensure URLs are never logged at any level:

```python
# For services that must use URL-based keys, suppress URL logging:
logger.debug(f"Testing API key for {service} (URL redacted)")
# Never log test_url itself
```

---

### CRIT-04: Flux Injection in InfluxDB Statistics Client via `period`, `window`, and `service_name` Parameters

**File**: `c:\cursor\HomeIQ\services\admin-api\src\influxdb_client.py`, lines 103-110, 139-154, 185-192, 275-279
**Severity**: CRITICAL
**Category**: Security (Injection)

**Important distinction**: The `devices_endpoints.py` and `events_endpoints.py` files
correctly use `_sanitize_flux_value()` for user input. However, the separate
`influxdb_client.py` (used by `StatsEndpoints`) does NOT sanitize its inputs:

```python
# influxdb_client.py line 103-110: period parameter NOT validated
query = f'''
from(bucket: "{self.bucket}")
    |> range(start: -{period})
    |> filter(fn: (r) => r._measurement == "home_assistant_events")
'''

# Line 189: service_name NOT sanitized
    |> filter(fn: (r) => r.service == "{service_name}")

# Line 279: window parameter NOT validated
    |> aggregateWindow(every: {window}, fn: count, createEmpty: false)
```

The `period` and `window` parameters flow from HTTP query parameters through
`StatsEndpoints` methods. A crafted value like `1h)\n|> drop()` could alter query
behavior. The `_period_to_seconds` method (line 353) uses an allowlist but only for
the seconds conversion -- it does NOT gate whether the raw value enters the Flux query.

**Fix**: Validate all parameters against explicit allowlists before use in queries:

```python
ALLOWED_PERIODS = {"15m", "1h", "6h", "24h", "7d"}
ALLOWED_WINDOWS = {"1m", "5m", "1h"}

def _validate_period(self, period: str) -> str:
    if period not in ALLOWED_PERIODS:
        raise ValueError(f"Invalid period: {period}. Allowed: {ALLOWED_PERIODS}")
    return period

def _sanitize_flux_value(self, value: str) -> str:
    """Match the pattern used in devices_endpoints.py and events_endpoints.py"""
    return str(value).replace('\\', '\\\\').replace('"', '\\"')
```

---

### CRIT-05: API Key Service Writes Secrets to Plaintext Files on Disk

**File**: `c:\cursor\HomeIQ\services\admin-api\src\api_key_service.py`, lines 309-352
**Severity**: CRITICAL
**Category**: Security

```python
# Line 158: Secret set directly in process environment
os.environ[config['env_var']] = api_key

# Lines 344-346: Secret written to plaintext file without permission restrictions
with open(config_path, 'w') as f:
    f.writelines(lines)
```

When `ADMIN_API_ALLOW_SECRET_WRITES=true`, the `update_api_key` method (line 130):
1. Sets the API key in `os.environ` (line 158) -- visible to child processes and `/proc`
2. Writes it to `.env.production` in plaintext (lines 344-346) without setting file
   permissions (unlike `config_manager.py` which at least sets `0o600` at line 164)

The `allow_secret_writes` guard at line 318-321 correctly raises `PermissionError` when
disabled, but the `os.environ` write at line 158 happens BEFORE the file write check.

**Mitigation**: The `allow_secret_writes` guard defaults to `false`, which is the correct
production configuration. However, when enabled, the file should be written with
restrictive permissions and the `os.environ` write should happen only after successful
file persistence.

---

## HIGH Priority Issues

### HIGH-01: Global Mutable Counters Without Thread Safety

**File**: `c:\cursor\HomeIQ\services\admin-api\src\main.py`, lines 90-92, 296-305
**Severity**: HIGH
**Category**: Concurrency Bug

```python
# Module-level globals (line 90-92)
_start_time = time.time()
_request_count = 0
_error_count = 0

# Modified in async middleware without locks (line 296-305)
async def log_requests(request, call_next):
    global _request_count, _error_count
    response = await call_next(request)
    _request_count += 1              # Race condition under concurrent requests
    if response.status_code >= 500:
        _error_count += 1            # Race condition
```

While CPython's GIL provides some protection for simple integer operations, the `+=`
pattern is not guaranteed atomic in asyncio when multiple coroutines are in flight.
The counters are used in the enhanced health endpoint (line 375-376) to calculate
error rates -- inaccurate counts produce misleading health data for a Tier 1 service.

**Fix**: Use `asyncio.Lock` or move to an atomically-updated counter:

```python
import asyncio
_counters_lock = asyncio.Lock()

async def log_requests(request, call_next):
    response = await call_next(request)
    async with _counters_lock:
        global _request_count, _error_count
        _request_count += 1
        if response.status_code >= 500:
            _error_count += 1
    return response
```

---

### HIGH-02: New `aiohttp.ClientSession` Created Per Health Check Request

**File**: `c:\cursor\HomeIQ\services\admin-api\src\health_endpoints.py`, lines 214, 261, 279, 298, 338, 348
**Severity**: HIGH
**Category**: Performance

```python
# Every single health check creates and destroys a TCP connection pool (line 214)
async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
    async with session.get(f"{service_url}{health_path}") as response:
```

This pattern appears in `_check_services` (line 214), `_get_websocket_service_data`
(line 261), `_check_dependencies` (line 279, 298), `_check_influxdb_health` (line 338),
and `_check_service_health` (line 348). Each call creates a new connection pool with full
TCP/TLS handshake overhead. The `_check_services` method iterates over 12 services,
creating 12 separate sessions sequentially.

The health check endpoints are called frequently (every few seconds by the dashboard),
making this a significant performance drain.

**Estimated overhead**: Each health poll creates ~12 unnecessary TCP connections. At a
5-second poll interval, that is ~144 wasted connections per minute.

**Fix**: Create a shared session at `__init__` time and close it on shutdown:

```python
class HealthEndpoints:
    def __init__(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5)
        )

    async def close(self):
        if self._session:
            await self._session.close()
```

---

### HIGH-03: InfluxDB Client Created Per Request in Events Endpoint

**File**: `c:\cursor\HomeIQ\services\admin-api\src\events_endpoints.py`, lines 458-468
**Severity**: HIGH
**Category**: Performance / Resource Leak

```python
async def _get_events_from_influxdb(self, event_filter, limit, offset):
    from influxdb_client import InfluxDBClient
    # ...
    client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org)
    query_api = client.query_api()
    # ... use client ...
    client.close()  # Line 543 - Only closed on success path
```

A new InfluxDB client is created for every event query. If an exception occurs between
creation (line 468) and `client.close()` (line 543), the connection leaks. The `close()`
call is not in a `finally` block or context manager.

**Fix**: Use a shared client instance or wrap in try/finally:

```python
client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org)
try:
    query_api = client.query_api()
    # ... use client ...
finally:
    client.close()
```

---

### HIGH-04: DeviceIntelligenceClient Has No Lifecycle Management

**File**: `c:\cursor\HomeIQ\services\admin-api\src\device_intelligence_client.py`, lines 18-22, 164-179
**Severity**: HIGH
**Category**: Resource Leak

```python
class DeviceIntelligenceClient:
    def __init__(self, base_url: str = "http://device-intelligence-service:8019"):
        self.client = httpx.AsyncClient(timeout=30.0)  # Created, never closed in normal flow
```

The global singleton `_device_intelligence_client` (line 165) is created lazily but
`close_device_intelligence_client()` (line 174) is never called from `main.py`'s
shutdown sequence in the `lifespan()` handler (lines 648-691). This leaks HTTP connections.

**Fix**: Add to the lifespan shutdown handler in `main.py`:

```python
# In lifespan() shutdown section:
from .device_intelligence_client import close_device_intelligence_client
await close_device_intelligence_client()
```

---

### HIGH-05: HA Proxy Module-Level Token Loading Prevents Rotation

**File**: `c:\cursor\HomeIQ\services\admin-api\src\ha_proxy_endpoints.py`, lines 10-11
**Severity**: HIGH
**Category**: Security / Operations

```python
# Read once at import time - cannot be refreshed without full restart
HA_URL = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
HA_TOKEN = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
```

If the Home Assistant long-lived access token is rotated (which is security best
practice), the admin-api must be fully restarted to pick up the new value. For a Tier 1
service, this creates an operational risk where token rotation causes downtime.

Note: The entity_id validation regex at line 19 (`r'^[a-z_]+\.[a-z0-9_]+$'`) is
correctly restrictive and prevents SSRF/path traversal attacks. This was incorrectly
flagged as vulnerable in the initial review.

**Fix**: Read from environment on each request:

```python
def _get_ha_config() -> tuple[str | None, str | None]:
    url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
    token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
    return url, token
```

---

### HIGH-06: Dual AlertManager Implementations Create Confusion

**Files**:
- `c:\cursor\HomeIQ\services\admin-api\src\alerting_service.py` (local implementation)
- `c:\cursor\HomeIQ\services\admin-api\src\health_endpoints.py`, line 22 (imports `shared.alert_manager`)
- `c:\cursor\HomeIQ\services\admin-api\src\main.py`, line 58 (imports `shared.monitoring.alerting_service`)

**Severity**: HIGH
**Category**: Architecture

The codebase contains potentially **three** alert system instances:

1. **Local** `alerting_service` singleton at `alerting_service.py:328` --
   `AlertingService` wrapping a local `AlertManager`
2. **Shared** `alert_manager` imported at `health_endpoints.py:22` from
   `shared.alert_manager` via `get_alert_manager("admin-api")`
3. **Shared** `alerting_service` imported at `main.py:58` from `shared.monitoring`

Alerts fired via the health endpoint's dependency checks (using shared alert_manager)
are invisible to the local `alerting_service`, and vice versa. Monitoring endpoints
may query one instance while health endpoints write to another.

**Fix**: Consolidate to a single alert system. Use the shared `alerting_service` from
`shared.monitoring` as the canonical implementation and remove the local duplicate.

---

### HIGH-07: Docker Socket Access Without RBAC

**File**: `c:\cursor\HomeIQ\services\admin-api\src\docker_service.py`, lines 57-84
**Severity**: HIGH
**Category**: Security

```python
docker_host = os.getenv('DOCKER_HOST', 'unix:///var/run/docker.sock')
self.client = docker.from_env()
```

Docker socket access grants the ability to start, stop, and restart containers. While
`docker_endpoints.py` enforces an allowlist via `_ensure_allowed_service` (line 376-383),
there is no role-based access control -- any authenticated user has identical permissions.
A compromised API key allows stopping critical Tier 1 services (websocket-ingestion,
influxdb).

**Positive notes**:
- The allowlist at `docker_endpoints.py:376-383` correctly restricts operations to
  known HomeIQ services
- All Docker operations are properly wrapped in `asyncio.to_thread()` (correcting the
  earlier review's claim of blocking calls)
- Authentication is enforced on all Docker endpoints via `secure_dependency` at
  `main.py:509`
- Container operations are logged with username for audit trails

**Recommendation**: Add role-based permissions (e.g., `docker:read` vs `docker:write`)
to the auth system to limit which authenticated users can perform destructive operations.

---

## MEDIUM Priority Issues

### MED-01: `_calculate_uptime_percentage` Receives Wrong Type

**File**: `c:\cursor\HomeIQ\services\admin-api\src\health_endpoints.py`, lines 371-403
**Severity**: MEDIUM
**Category**: Bug

```python
def _calculate_uptime_percentage(self, dependencies: list[dict[str, Any]], uptime_seconds: float) -> float:
    # ...
    healthy_count = sum(1 for dep in dependencies if dep.get('status') == 'healthy')
```

The method signature expects `list[dict[str, Any]]` and calls `.get('status')`, but the
`dependencies` variable passed at line 130 is a list of `DependencyHealth` objects (from
`shared.types.health`), not dicts. The `.get('status')` call on a Pydantic model or
dataclass will either fail with `AttributeError` or always return `None`, causing
`healthy_count` to always be 0 and `uptime_percentage` to always be 0.0.

**Fix**: Use attribute access instead of dict access:

```python
healthy_count = sum(1 for dep in dependencies if getattr(dep, 'status', None) == HealthStatusEnum.HEALTHY)
```

---

### MED-02: Config Manager Non-Atomic File Writes

**File**: `c:\cursor\HomeIQ\services\admin-api\src\config_manager.py`, lines 123-160
**Severity**: MEDIUM
**Category**: Reliability

```python
# Read file -> modify in memory -> write back (not atomic)
with open(env_file) as f:
    lines = f.readlines()
# ... modify lines ...
with open(env_file, 'w') as f:    # File truncated here
    f.writelines(new_lines)        # Data written here -- gap = data loss risk
```

If the process crashes between truncating the file (when `'w'` mode opens it) and
completing the write, the configuration file is lost or corrupted. The
`config_manager.py` correctly sets `0o600` permissions after write (line 163-164),
which is good -- but the write itself is not atomic.

**Fix**: Use write-to-temp-then-rename:

```python
import tempfile
tmp_fd, tmp_path = tempfile.mkstemp(dir=str(env_file.parent))
with os.fdopen(tmp_fd, 'w') as f:
    f.writelines(new_lines)
os.replace(tmp_path, str(env_file))
```

---

### MED-03: In-Memory State Lost on Restart (Alerts, Metrics, Logs)

**File**: Multiple files
**Severity**: MEDIUM
**Category**: Reliability

The following services store all state in memory with no persistence:

| Component | File | Limit | Data Lost on Restart |
|-----------|------|-------|---------------------|
| AlertManager | `alerting_service.py:124-129` | Unlimited history | Alert rules, active alerts, history |
| MetricsCollector | `metrics_service.py` | 1000 values/metric | All counters, gauges, timers |
| LogAggregator | `logging_service.py:110` | 10,000 entries | All aggregated logs |
| ResponseTimeTracker | `metrics_tracker.py:25` | 1,000 measurements/service | Response time percentiles |
| RateLimiter | `shared/rate_limiter.py:46` | Unlimited buckets (1h cleanup) | Per-IP rate state |
| Global counters | `main.py:90-92` | N/A | `_request_count`, `_error_count` |

A restart of admin-api loses all historical data. For a Tier 1 service, this means
post-incident analysis, alerting history, and performance trends are unreliable.

---

### MED-04: MQTT Config Persisted to JSON Without File Permissions

**File**: `c:\cursor\HomeIQ\services\admin-api\src\mqtt_config_endpoints.py`, lines 135-139
**Severity**: MEDIUM
**Category**: Security

```python
def _persist_config(payload: dict[str, Any]) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as config_file:
        json.dump(payload, config_file, indent=2, sort_keys=True)
    # No chmod -- file inherits default umask permissions (often 0644)
```

The MQTT config (including `MQTT_PASSWORD`) is written without restricting file
permissions. Compare with `config_manager.py` which correctly sets `0o600` at line 164.

**Fix**: Add `os.chmod(path, 0o600)` after writing.

---

### MED-05: Error Details Leaked to Clients in Multiple Endpoints

**File**: Multiple files
**Severity**: MEDIUM
**Category**: Security (Information Disclosure)

```python
# docker_endpoints.py line 108 -- leaks internal error details
detail=f"Failed to list containers: {str(e)}"

# ha_proxy_endpoints.py line 55 -- can reveal internal HA URL
detail=f"Failed to reach Home Assistant: {exc}"

# devices_endpoints.py line 259 -- leaks internal architecture
detail=f"Failed to retrieve entities: {str(e)}"
```

Internal error details (connection strings, internal hostnames, stack traces) are
returned to the client. The `ha_proxy_endpoints.py` error message can reveal the
internal Home Assistant URL.

**Fix**: Return generic error messages to clients; log details server-side only.

---

### MED-06: httpx AsyncClient Created Per HA Proxy Request

**File**: `c:\cursor\HomeIQ\services\admin-api\src\ha_proxy_endpoints.py`, lines 42-44
**Severity**: MEDIUM
**Category**: Performance

```python
async def _fetch_from_home_assistant(path: str) -> Any:
    # ...
    async with httpx.AsyncClient(timeout=10.0) as client:  # New client per request
        response = await client.get(url, headers=headers)
```

Each proxy request creates a new `httpx.AsyncClient`, establishing a new TCP connection
pool with potential TLS overhead. HA proxy requests could be frequent when the dashboard
is actively browsing device states.

**Fix**: Use a module-level or class-level shared client.

---

### MED-07: `_validate_key_format` Has Weak Validation

**File**: `c:\cursor\HomeIQ\services\admin-api\src\api_key_service.py`, lines 262-288
**Severity**: MEDIUM
**Category**: Security

```python
def _validate_key_format(self, service: str, api_key: str) -> bool:
    if not api_key or len(api_key.strip()) == 0:
        return False
    if service == 'weather':
        return len(api_key) >= 20     # Length check only
    elif service == 'air-quality':
        return len(api_key) >= 5      # Very permissive
    else:
        return len(api_key) >= 5      # Very permissive
```

The validation only checks string length, not character composition. An API key
containing shell metacharacters, newlines, or null bytes would pass validation and
be written to the `.env.production` file (when secret writes are enabled), potentially
allowing `.env` file injection (e.g., a key containing `\nMALICIOUS_VAR=value`).

**Fix**: Validate that API keys contain only safe characters:

```python
import re
if not re.match(r'^[A-Za-z0-9_\-\.]+$', api_key):
    return False
```

---

### MED-08: Module-Level Side Effects in `main.py`

**File**: `c:\cursor\HomeIQ\services\admin-api\src\main.py`, lines 645, 706-711
**Severity**: MEDIUM
**Category**: Architecture

```python
# Line 645: AdminAPIService instantiated at import time
admin_api_service = AdminAPIService()

# Lines 706-711: Middleware and routes added at import time
admin_api_service.app = app
admin_api_service._add_middleware()
admin_api_service._add_routes()
admin_api_service._add_exception_handlers()
```

The `AdminAPIService.__init__` reads environment variables and creates auth managers,
rate limiters, Docker services, and more. This executes on `import main`, which
complicates testing and can fail if environment variables are not set.

The `AdminAPIService.start()` method ALSO calls `_add_middleware()` and `_add_routes()`,
meaning that if `start()` is called after module-level initialization, middleware and
routes could be added twice.

**Fix**: Use the `lifespan` pattern exclusively and defer `AdminAPIService` creation.

---

## LOW Priority Issues

### LOW-01: Deprecated `datetime.utcnow()` Usage

**File**: `c:\cursor\HomeIQ\shared\auth.py`, lines 115, 119, 199, 234
**Severity**: LOW
**Category**: Code Quality

```python
user["last_login"] = datetime.utcnow()  # Deprecated in Python 3.12+
```

`datetime.utcnow()` is deprecated and returns a naive datetime. Use
`datetime.now(timezone.utc)` instead. The `alerting_service.py` correctly uses
`datetime.now(timezone.utc)` throughout -- the auth module should follow suit.

---

### LOW-02: `health_check.py` Appears to Be Dead Code

**File**: `c:\cursor\HomeIQ\services\admin-api\src\health_check.py`
**Severity**: LOW
**Category**: Code Quality

This file implements an aiohttp-based health check handler, but `main.py` uses FastAPI
exclusively. It is never imported or referenced by any active code path.

---

### LOW-03: Inconsistent Error Handling Patterns

**File**: Multiple files
**Severity**: LOW
**Category**: Code Quality

Some endpoints return `JSONResponse` directly on error (e.g., `events_endpoints.py`
line 107), while others raise `HTTPException` (e.g., `docker_endpoints.py` line 106).
Note that `events_endpoints.py` also uses `JSONResponse` without importing it (line
107), which would cause a `NameError` at runtime -- but this file appears to be dead
code (migrated to data-api per `main.py` line 512).

---

### LOW-04: Module-Level `sys.path.append` Manipulation

**File**: `c:\cursor\HomeIQ\services\admin-api\src\main.py`, line 22;
`health_endpoints.py`, line 17
**Severity**: LOW
**Category**: Code Quality

```python
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
```

Multiple files modify `sys.path` at module level to import shared modules. This is
fragile and can cause import order issues. Consider using proper Python packaging with
a `pyproject.toml` or consistent path setup.

---

### LOW-05: Rate Limiter Skips Health Endpoints But Not Public Metrics

**File**: `c:\cursor\HomeIQ\shared\rate_limiter.py`, lines 121-122
**Severity**: LOW
**Category**: Operations

```python
if request.url.path in ("/health", "/api/health", "/api/v1/health"):
    return await call_next(request)
```

The rate limiter exempts health endpoints but applies to public metrics endpoints
(`/api/metrics/realtime`, `/api/v1/real-time-metrics`). The dashboard polls these
frequently and could trigger rate limiting, causing the dashboard to display stale data.

---

### LOW-06: Emoji Characters in Log Messages

**File**: `c:\cursor\HomeIQ\services\admin-api\src\main.py`, lines 266-274
**Severity**: LOW

Log messages contain emoji characters ("OpenTelemetry tracing configured", etc.) which
can cause encoding issues in some log aggregation systems.

---

## Security Audit Summary

### Authentication & Authorization

| Aspect | Status | Location | Notes |
|--------|--------|----------|-------|
| API key enforcement | GOOD | `main.py:138-147` | Required by default, anonymous mode warns |
| JWT support | GOOD | `shared/auth.py:194-203` | PBKDF2-SHA256, configurable TTL |
| Constant-time comparison | GOOD | `shared/auth.py:133` | `secrets.compare_digest` used |
| Auth cannot be disabled | GOOD | `shared/auth.py:58-61` | `ValueError` raised if no key |
| Token verification | GOOD | `shared/auth.py:210-215` | `verify_signature` and `verify_exp` both True |
| RBAC | MISSING | N/A | All authenticated users have identical permissions |
| Password policy | MISSING | N/A | No minimum length/complexity enforcement |
| Session cleanup | ADEQUATE | `shared/auth.py:268-277` | Manual cleanup, no automatic expiry sweep |

### Input Validation

| Aspect | Status | Location | Notes |
|--------|--------|----------|-------|
| Entity ID validation (HA proxy) | GOOD | `ha_proxy_endpoints.py:14-21` | Regex `^[a-z_]+\.[a-z0-9_]+$` |
| Flux sanitization (devices/events) | GOOD | `devices_endpoints.py:17-19`, `events_endpoints.py:17-19` | `_sanitize_flux_value` escapes `\` and `"` |
| Flux sanitization (influxdb_client) | MISSING | `influxdb_client.py:103+` | Raw `period`, `service_name`, `window` interpolated |
| MQTT broker URL validation | GOOD | `mqtt_config_endpoints.py:66-77` | Scheme allowlist |
| Docker service allowlist | GOOD | `docker_endpoints.py:376-383` | `_ensure_allowed_service` |
| Config sensitive key blocking | GOOD | `config_manager.py:116-121` | Pattern matching blocks sensitive writes |
| API key format validation | WEAK | `api_key_service.py:262-288` | Length only, no character validation |

### Attack Surface

| Vector | Risk Level | Mitigation |
|--------|-----------|------------|
| CORS bypass via simple_main.py | CRITICAL | No auth + wildcard CORS + credentials |
| MQTT credential theft | CRITICAL | Public GET returns plaintext password |
| Flux injection (influxdb_client.py) | CRITICAL | Unvalidated period/service_name/window |
| API key exposure in URLs | CRITICAL | Keys in query strings logged by infrastructure |
| SSRF via HA proxy | LOW | Entity ID regex prevents path traversal |
| Docker socket abuse | MEDIUM | Allowlist enforced, but no RBAC |
| Config file tampering | LOW | `ADMIN_API_ALLOW_SECRET_WRITES` guard (default: false) |
| .env injection via API keys | MEDIUM | No character validation on key values |

---

## Architecture Review

### Strengths

1. **Clean separation of concerns**: Each endpoint module is self-contained with its own
   router, models, and business logic.
2. **Graceful degradation**: Docker service falls back to mock mode; events fall back to
   mock data; device queries fall back from Device Intelligence Service to InfluxDB.
3. **Auth enforcement pattern**: `secure_dependency = [Depends(self.auth_manager.get_current_user)]`
   applied at router level (`main.py:464`) ensures consistent authentication.
4. **Shared module reuse**: Auth, rate limiting, correlation middleware, observability,
   and health types are properly shared across services.
5. **Docker allowlist**: `_ensure_allowed_service` (docker_endpoints.py:376) prevents
   operations on non-project containers.
6. **Proper async wrapping**: Docker SDK calls correctly use `asyncio.to_thread()`
   (docker_service.py:117, 180, etc.).
7. **InfluxDB connection tracking**: `influxdb_client.py` tracks query performance
   metrics (count, errors, avg time).
8. **Flux sanitization**: Present in device and event query paths (though missing in
   statistics client).

### Weaknesses

1. **Dual entry points**: `main.py` and `simple_main.py` serve the same purpose but with
   wildly different security postures.
2. **Triple alert systems**: Local `AlertingService`, shared `alert_manager`, and shared
   `alerting_service` all coexist without coordination.
3. **Module-level side effects**: `AdminAPIService()` created on import, middleware added
   at module level AND in `start()` method.
4. **No dependency injection**: Services are tightly coupled via module-level singletons.
5. **Mixed HTTP client libraries**: `aiohttp` in health/events, `httpx` in HA proxy and
   device intelligence client. Should standardize on one.
6. **Connection pool waste**: Per-request client creation in 6+ locations.

### Component Dependency Map

```
main.py (AdminAPIService)
  |-- shared.auth.AuthManager (API key + JWT + sessions)
  |-- shared.rate_limiter.RateLimiter (token bucket, 100 req/60s default)
  |-- shared.monitoring.{MonitoringEndpoints, StatsEndpoints, alerting_service, logging_service, metrics_service}
  |-- HealthEndpoints -> shared.types.health, shared.alert_manager (aiohttp sessions)
  |-- DockerEndpoints -> DockerService (docker SDK via asyncio.to_thread), APIKeyService
  |-- ConfigEndpoints -> ConfigManager (.env file read/write)
  |-- ha_proxy_endpoints -> httpx (HA_URL, HA_TOKEN module-level)
  |-- mqtt_config_endpoints -> JSON file persistence (public GET, secured PUT)
  |-- [DEAD] DevicesEndpoints -> DeviceIntelligenceClient (httpx), AdminAPIInfluxDBClient
  |-- [DEAD] EventsEndpoints -> InfluxDB (per-request client), aiohttp
```

---

## Performance Analysis

### Connection Pool Waste

| Location | File:Line | Issue | Impact |
|----------|-----------|-------|--------|
| Health service checks | `health_endpoints.py:214` | New `aiohttp.ClientSession` per service | ~12 TCP connections per health poll |
| Health InfluxDB check | `health_endpoints.py:338` | New session per InfluxDB check | Full TCP setup |
| Health WebSocket check | `health_endpoints.py:261` | New session per WS data fetch | Full TCP setup |
| Health dependencies | `health_endpoints.py:279,298` | New session per dependency | Full TCP setup |
| HA proxy requests | `ha_proxy_endpoints.py:43` | New `httpx.AsyncClient` per request | TCP + TLS per request |
| Events InfluxDB | `events_endpoints.py:468` | New `InfluxDBClient` per query | Full connection setup |
| Enhanced health (main.py) | `main.py:99` | New `aiohttp.ClientSession` per dep check | 3 sessions per health call |

### In-Memory Storage Limits

| Component | Limit | Growth Pattern |
|-----------|-------|---------------|
| `ResponseTimeTracker` | 1,000 measurements/service | Capped, oldest evicted |
| `LogAggregator` | 10,000 entries | Capped, oldest evicted |
| `MetricsCollector` | 1,000 values/metric | Capped via max_values |
| Rate limiter buckets | Unlimited (1h cleanup) | Grows with unique IPs |
| Alert history | **Unlimited** | Memory leak potential |
| Session store | **Unlimited** (manual cleanup) | Grows with active sessions |

The **alert history** list (`alerting_service.py:127`) and **session store**
(`shared/auth.py:73`) have no upper bound and will grow indefinitely. In a long-running
Tier 1 service, these could eventually cause memory pressure.

---

## Test Coverage Analysis

### Coverage Matrix

| Module | Test File | Coverage | Notes |
|--------|-----------|----------|-------|
| `auth.py` (shared) | `test_auth.py` | HIGH | 11 tests: register, authenticate, JWT, API key |
| `alerting_service.py` | `test_alerting_service.py` | HIGH | Rules, alerts, cooldown, evaluation, lifecycle |
| `config_endpoints.py` | `test_config_endpoints.py` | HIGH | CRUD, validation, error handling |
| `devices_endpoints.py` | `test_devices_endpoints.py` | MEDIUM | Flux query building, device/entity CRUD |
| `events_endpoints.py` | `test_events_endpoints.py` | MEDIUM | Retrieval, filtering, search |
| `health_endpoints.py` | `test_health_endpoints.py` | MEDIUM | Status, dependency checks, degraded states |
| `influxdb_client.py` | `test_influxdb_client_simple.py` | LOW | Only init, connection failure, period conversion |
| `logging_service.py` | `test_logging_service.py` | HIGH | LogEntry, aggregator, statistics |
| `metrics_service.py` | `test_metrics_service.py` | HIGH | Counters, gauges, timers, performance tracker |
| `monitoring_endpoints.py` | `test_monitoring_endpoints.py` | HIGH | All monitoring endpoints with mocked auth |
| `stats_endpoints.py` | `test_stats_endpoints.py` | MEDIUM | Statistics, recommendations |
| `main.py` | `test_main.py` | LOW | App creation, basic routes |
| **docker_endpoints.py** | **NONE** | **ZERO** | No tests for container start/stop/restart/logs |
| **docker_service.py** | **NONE** | **ZERO** | No tests for Docker SDK interaction |
| **mqtt_config_endpoints.py** | **NONE** | **ZERO** | No tests for MQTT config read/write |
| **ha_proxy_endpoints.py** | **NONE** | **ZERO** | No tests for HA proxy or SSRF prevention |
| **api_key_service.py** | **NONE** | **ZERO** | No tests for API key management |
| **device_intelligence_client.py** | **NONE** | **ZERO** | No tests for HTTP client |
| **metrics_tracker.py** | (indirect) | LOW | Used by other tests but no dedicated tests |
| **config_manager.py** | (indirect) | LOW | Used by config_endpoints tests, no direct tests |
| **simple_main.py** | **NONE** | **ZERO** | No tests for the insecure entry point |

### Critical Test Gaps

1. **Docker operations** (start/stop/restart): These are the highest-risk operations in
   admin-api. A bug could take down production services. Zero test coverage.

2. **MQTT credential handling**: The public GET endpoint returning credentials has no
   test verifying the password is masked (it is not masked -- that is the bug).

3. **HA Proxy SSRF prevention**: The `_validate_entity_id` regex is security-critical
   but has no dedicated tests for bypass attempts (e.g., `sensor.test/../config`,
   `SENSOR.Test`, Unicode normalization, null bytes).

4. **API key validation**: The `_test_api_key` method makes outbound HTTP calls with
   user-provided API keys but has no tests for error handling, timeout behavior, or
   malicious key values.

5. **Security-specific tests missing**:
   - No injection tests (Flux injection via influxdb_client.py parameters)
   - No authentication bypass tests for each secured endpoint
   - No rate limiting behavior tests
   - No CORS enforcement tests

### Recommended Test Additions (Priority Order)

1. `test_docker_endpoints.py`: Container lifecycle, allowlist enforcement, error handling
2. `test_ha_proxy_endpoints.py`: SSRF prevention, entity_id validation edge cases
3. `test_mqtt_config_endpoints.py`: Password masking verification, PUT validation
4. `test_api_key_service.py`: Key format validation, URL handling, secret write protection
5. `test_security.py`: Cross-cutting security tests (auth bypass, Flux injection, CORS)
6. `test_influxdb_client_injection.py`: Period/window/service_name injection tests

---

## Corrections from Initial Review

The following items from the initial automated review (Revision 1) were **incorrect**
and have been removed or corrected in this revision:

| Initial Finding | Why It Was Wrong |
|----------------|-----------------|
| CRIT-05: SSRF via HA proxy | `_validate_entity_id` at line 14-21 uses regex `^[a-z_]+\.[a-z0-9_]+$` which prevents path traversal. The earlier review missed this function. |
| CRIT-01/02/03: Flux injection in devices/events | Both `devices_endpoints.py:17-19` and `events_endpoints.py:17-19` implement `_sanitize_flux_value()`. The injection risk exists only in `influxdb_client.py`. |
| HIGH-01: Hardcoded health dependencies | `main.py:346-351` performs real async dependency checks via `_check_dependency()` with `asyncio.gather()`. The earlier review confused this with mock data patterns. |
| HIGH-02: 100% uptime always | `main.py:375-376` calculates real error rate from `_request_count` and `_error_count` counters. |
| HIGH-06: Blocking Docker calls | All Docker SDK calls in `docker_service.py` are correctly wrapped in `asyncio.to_thread()` (lines 117, 180, 186, 192, 226, 232, 238, 272, 275, 281, 320, 385). |
| MED-02: Deadlock in metrics_tracker | `get_all_stats()` calls `_get_stats_unlocked()` (line 102), not `get_stats()`, so there is no lock re-acquisition. The private method was added specifically to avoid this. |
| CRIT-04: Unauthenticated MQTT PUT | The PUT endpoint is on `router` (line 155), NOT `public_router`. In `main.py:498-503`, the `router` is included with `secure_dependency`. Only GET is public. |
| HIGH-05: status variable shadowing | In `docker_endpoints.py:366-374`, the variable is named `key_status` in the actual code at line 367. The earlier review appears to have examined an older version. |

---

## Recommendations Summary (Prioritized)

### Immediate Actions (This Sprint)

1. **Remove or secure `simple_main.py`** -- CRIT-01
2. **Mask MQTT password in public GET response** -- CRIT-02
3. **Add period/window/service_name allowlist validation in `influxdb_client.py`** -- CRIT-04
4. **Move API keys from URL query strings to headers where possible** -- CRIT-03
5. **Add character validation to API key format checking** -- MED-07

### Short-Term (Next 2 Sprints)

6. Add connection pooling (shared `aiohttp.ClientSession`) across health endpoints -- HIGH-02
7. Consolidate alert systems to single implementation -- HIGH-06
8. Add `asyncio.Lock` for global counters or use atomic counter -- HIGH-01
9. Close DeviceIntelligenceClient on shutdown -- HIGH-04
10. Fix `_calculate_uptime_percentage` type mismatch -- MED-01
11. Write tests for Docker, MQTT, HA proxy, API key endpoints
12. Set file permissions on MQTT config writes -- MED-04
13. Fix InfluxDB client leak in events_endpoints.py -- HIGH-03

### Medium-Term (Next Quarter)

14. Implement RBAC for Docker operations -- HIGH-07
15. Add persistent storage for alerts and metrics -- MED-03
16. Implement atomic file writes for config -- MED-02
17. Refactor HA_URL/HA_TOKEN to lazy loading -- HIGH-05
18. Standardize on single HTTP client library (aiohttp or httpx)
19. Add security-focused test suite (injection, SSRF, auth bypass)
20. Remove dead code files (health_check.py, devices_endpoints.py if fully migrated)
21. Add upper bounds to alert history and session store to prevent memory leaks
22. Fix module-level side effects in main.py -- MED-08

---

## Appendix: Files Reviewed

### Source Files (24)
- `c:\cursor\HomeIQ\services\admin-api\src\main.py` (723 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\simple_main.py` (93 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\auth.py`
- `c:\cursor\HomeIQ\services\admin-api\src\api_key_service.py` (353 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\alerting_service.py` (330 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\alert_endpoints.py`
- `c:\cursor\HomeIQ\services\admin-api\src\config_manager.py` (381 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\config_endpoints.py`
- `c:\cursor\HomeIQ\services\admin-api\src\health_check.py`
- `c:\cursor\HomeIQ\services\admin-api\src\health_endpoints.py` (446 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\monitoring_endpoints.py`
- `c:\cursor\HomeIQ\services\admin-api\src\metrics_service.py`
- `c:\cursor\HomeIQ\services\admin-api\src\metrics_tracker.py` (129 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\metrics_endpoints.py`
- `c:\cursor\HomeIQ\services\admin-api\src\stats_endpoints.py`
- `c:\cursor\HomeIQ\services\admin-api\src\logging_service.py` (211 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\influxdb_client.py` (406 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\docker_service.py` (446 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\docker_endpoints.py` (384 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\devices_endpoints.py` (408 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\events_endpoints.py` (571 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\mqtt_config_endpoints.py` (179 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\ha_proxy_endpoints.py` (100 lines)
- `c:\cursor\HomeIQ\services\admin-api\src\device_intelligence_client.py` (180 lines)

### Shared Modules (2)
- `c:\cursor\HomeIQ\shared\auth.py` (368 lines)
- `c:\cursor\HomeIQ\shared\rate_limiter.py` (140 lines)

### Test Files (14)
- `c:\cursor\HomeIQ\services\admin-api\tests\conftest.py`
- `c:\cursor\HomeIQ\services\admin-api\tests\test_auth.py`
- `c:\cursor\HomeIQ\services\admin-api\tests\test_alerting_service.py`
- `c:\cursor\HomeIQ\services\admin-api\tests\test_config_endpoints.py`
- `c:\cursor\HomeIQ\services\admin-api\tests\test_devices_endpoints.py`
- `c:\cursor\HomeIQ\services\admin-api\tests\test_events_endpoints.py`
- `c:\cursor\HomeIQ\services\admin-api\tests\test_health_endpoints.py`
- `c:\cursor\HomeIQ\services\admin-api\tests\test_influxdb_client_simple.py`
- `c:\cursor\HomeIQ\services\admin-api\tests\test_logging_service.py`
- `c:\cursor\HomeIQ\services\admin-api\tests\test_metrics_service.py`
- `c:\cursor\HomeIQ\services\admin-api\tests\test_monitoring_endpoints.py`
- `c:\cursor\HomeIQ\services\admin-api\tests\test_stats_endpoints.py`
- `c:\cursor\HomeIQ\services\admin-api\tests\test_main.py`

### Configuration Files (2)
- `c:\cursor\HomeIQ\services\admin-api\requirements.txt`
- `c:\cursor\HomeIQ\services\admin-api\Dockerfile`
