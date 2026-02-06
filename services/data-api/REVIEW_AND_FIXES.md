# Data API Service - Deep Code Review Report

**Service**: data-api (Rank #2, Tier 1 - Mission Critical)
**Role**: Central query hub - ALL services query through this service
**Port**: 8006
**Reviewed**: 2026-02-06
**Reviewer**: Claude Opus 4.6
**Files Reviewed**: 35+ Python source files in `src/`, 10 test files in `tests/`

---

## Executive Summary

The data-api service is the central query hub for all 46+ HomeIQ microservices. It provides InfluxDB time-series queries, SQLite metadata access, sports data, energy correlations, Docker management, and Home Assistant automation endpoints. The service has undergone significant improvements since initial development -- authentication is now enforced on all sensitive routes, CORS wildcard handling has been hardened, the early logger crash has been fixed, and several Flux injection vectors in sports/HA automation endpoints have been addressed with `sanitize_flux_value()`. However, critical issues remain in the MCP router (weak sanitization, broken imports), mock data masquerading as real metrics in production, in-memory webhook storage, and inconsistent InfluxDB client patterns.

---

## Quality Scores

| Category | Score | Grade | Notes |
|----------|-------|-------|-------|
| **Security** | 6.5/10 | C | MCP router has weak sanitization and broken imports; main routes use proper `flux_utils`; auth enforced |
| **Error Handling** | 7/10 | B | Good exception patterns in most endpoints; silent empty returns in some paths |
| **Performance** | 6/10 | C | Shared InfluxDB clients now used in events/energy; sync client in async context; no query timeouts |
| **Data Integrity** | 7.5/10 | B+ | WAL mode configured; proper session management; pagination now correct |
| **Code Quality** | 5.5/10 | D+ | Significant dead code; mock data in production; naming confusion |
| **API Design** | 6.5/10 | C+ | Consistent auth; inconsistent response models; mixed pagination styles |
| **Database** | 8/10 | B+ | Excellent SQLite config; proper indexes; WAL mode; async sessions |
| **InfluxDB Integration** | 5.5/10 | D+ | Shared clients partially adopted; two different client patterns; no query timeouts |
| **Testing** | 4/10 | F | 10 test files exist but critical paths untested; ~20% coverage estimate |
| **Overall** | 6.2/10 | C- | Improved from initial development but significant gaps remain for a Tier 1 service |

---

## Previously Reported Issues - Status Update

Several issues from earlier reviews have been **resolved**:

| Issue | Status | Evidence |
|-------|--------|----------|
| Logger NameError at startup | **FIXED** | `main.py` line 28: `_early_logger = logging.getLogger("data-api.startup")` used in early try/except blocks |
| Auth not enforced on routes | **FIXED** | `main.py` line 310: `_auth_dependency = [Depends(data_api_service.auth_manager.get_current_user)]` applied to ALL routers |
| CORS wildcard with credentials | **FIXED** | `main.py` line 148: default is `http://localhost:3000`; line 292: `_cors_allow_credentials = "*" not in data_api_service.cors_origins` |
| Sports Flux injection (league) | **FIXED** | `sports_endpoints.py` line 148: `safe_league = sanitize_flux_value(league.upper())` |
| HA Automation Flux injection (team) | **FIXED** | `ha_automation_endpoints.py` line 105: `safe_team = sanitize_flux_value(team_lower)` |
| Game history Flux injection | **FIXED** | `sports_endpoints.py` line 457: `safe_team = sanitize_flux_value(team)` |
| Events endpoints InfluxDB per-request | **FIXED** | `events_endpoints.py` line 29: shared `_get_shared_influxdb_client()` pattern |
| Energy endpoints InfluxDB per-request | **FIXED** | `energy_endpoints.py` line 77: shared `get_influxdb_client()` pattern |
| Pagination offset/limit order | **FIXED** | `events_endpoints.py` lines 1028-1030: offset applied BEFORE limit |

---

## CRITICAL Issues (Remaining)

### CRIT-01: MCP Router Has Weak Flux Sanitization and Broken Imports
**File**: `c:\cursor\HomeIQ\services\data-api\src\api\mcp_router.py`
**Lines**: 13-15, 52-54, 104, 146-148
**Severity**: CRITICAL
**CVSS**: 8.5 (Injection via weak sanitization + all endpoints non-functional)

The MCP router has TWO distinct problems:

**Problem 1: Weak Sanitization**
The MCP router defines its own `_sanitize_flux_value()` (line 13-15) that only escapes backslash and double quotes. It does NOT use the robust `flux_utils.sanitize_flux_value()` available in the codebase:

```python
# mcp_router.py lines 13-15 - WEAK sanitizer
def _sanitize_flux_value(value: str) -> str:
    return str(value).replace('\\', '\\\\').replace('"', '\\"')
```

Compare with `flux_utils.py` which removes special characters, strips comments, limits length, and validates output. The MCP sanitizer allows semicolons, pipe characters, parentheses, and other Flux operators through.

Additionally, `start_time` and `end_time` are interpolated UNQUOTED into the Flux `range()` function (line 63):

```python
# mcp_router.py line 63
|> range(start: {safe_start_time}, stop: {safe_end_time})
```

Since `range()` parameters are not string literals, the backslash/quote escaping provides zero protection here. An attacker could send `start_time="-1h) |> drop() |> yield(name: "attack"` to inject arbitrary Flux.

**Problem 2: Broken Imports**
All three MCP endpoints import from non-existent modules:

```python
# mcp_router.py line 52 - DOES NOT EXIST
from ..database.influx_client import InfluxDBQueryClient
# mcp_router.py line 104 - DOES NOT EXIST
from ..database.sqlite_client import SQLiteClient
```

The `database` module is `database.py` (a single file), not a package with submodules. Every MCP endpoint will crash with `ImportError` at runtime.

**Impact**: MCP endpoints are completely non-functional. If the imports were fixed, the weak sanitization would create Flux injection vulnerabilities.

**Fix**:
1. Replace the local `_sanitize_flux_value` with `from .flux_utils import sanitize_flux_value`
2. Fix imports to use existing modules (`from shared.influxdb_query_client import InfluxDBQueryClient`, `from .database import AsyncSessionLocal`)
3. Quote string values and validate time parameters against an allowlist pattern

---

### CRIT-02: `_get_events_from_influxdb` Silently Returns Empty List on Error
**File**: `c:\cursor\HomeIQ\services\data-api\src\events_endpoints.py`
**Lines**: 1103-1105
**Severity**: CRITICAL (for a Tier 1 query service)

```python
# events_endpoints.py lines 1103-1105
except Exception as e:
    logger.error(f"Error querying InfluxDB: {e}")
    return []  # Silently swallows ALL errors
```

This is the PRIMARY data access path for the entire HomeIQ platform. When InfluxDB is down, queries time out, or connections fail, this method returns an empty list that is **indistinguishable from "no events found"**. The parent method `_get_all_events` (line 340) properly raises `HTTPException(503)`, but `_get_events_stream` (line 759) and `_get_event_categories` (line 822) also silently swallow errors by returning default structures.

**Impact**: Dashboard shows "no events" when InfluxDB is actually down. Monitoring cannot distinguish between empty data and infrastructure failure. On-call staff will not be alerted to outages.

**Fix**: Raise the exception so callers can distinguish "no data" from "service unavailable". Let the HTTP layer return 503.

---

### CRIT-03: `_trace_automation_chain` Also Silently Swallows Errors
**File**: `c:\cursor\HomeIQ\services\data-api\src\events_endpoints.py`
**Lines**: 1218-1222
**Severity**: HIGH

```python
except Exception as e:
    logger.error(f"Error tracing automation chain: {e}")
    import traceback
    logger.error(traceback.format_exc())
    return []  # Silent failure
```

Same pattern as CRIT-02 but for automation chain tracing. The HTTP endpoint handler (line 246) raises `HTTPException(500)` on errors, but this inner method catches and suppresses all exceptions, so the HTTP handler never sees the error.

**Fix**: Let exceptions propagate to the endpoint handler.

---

## HIGH Issues

### HIGH-01: Mock/Random Data Served as Real Production Metrics
**File**: `c:\cursor\HomeIQ\services\data-api\src\analytics_endpoints.py`
**Lines**: 293-308
**Also in**: `c:\cursor\HomeIQ\services\data-api\src\health_endpoints.py` lines 398-430

Three of four analytics metrics return `random.uniform()` mock data:

```python
# analytics_endpoints.py lines 293-296
async def query_api_response_time(start_time, interval, num_points):
    return generate_mock_series(start_time, interval, num_points, base=50, variance=30)

async def query_database_latency(start_time, interval, num_points):
    return generate_mock_series(start_time, interval, num_points, base=15, variance=10)

async def query_error_rate(start_time, interval, num_points):
    return generate_mock_series(start_time, interval, num_points, base=0.5, variance=0.5)
```

The `/event-rate` health endpoint similarly returns `random.uniform(0.5, 5.0)` (line 401) with hardcoded 1% failure rate.

**Impact**: Dashboards display random numbers as real metrics. Monitoring alerts are meaningless. Operators may ignore real problems because metrics are always "normal" (random). The `calculate_service_uptime()` function always returns `100.0` (line 42), making uptime monitoring useless.

**Fix**: Either implement real metrics collection using middleware request counters and InfluxDB query performance tracking, or clearly return `null`/`unavailable` to indicate metrics are not yet implemented. Never return random data as production metrics.

---

### HIGH-02: In-Memory Webhook Storage Lost on Restart
**File**: `c:\cursor\HomeIQ\services\data-api\src\ha_automation_endpoints.py`
**Line**: 85
**Severity**: HIGH

```python
# ha_automation_endpoints.py line 85
webhooks: dict[str, WebhookRegistration] = {}
```

All webhook registrations are stored in a module-level dictionary. On any service restart, all registered webhooks are permanently lost. The list webhook endpoint (line 275) also uses `datetime.now()` instead of the actual creation time, making it impossible to tell when webhooks were registered.

For a Tier 1 service managing Home Assistant automation event subscriptions, losing all webhook registrations on restart means automations will silently stop working until manually re-registered.

**Impact**: Service restarts silently break all Home Assistant game-event automations.

**Fix**: Persist webhooks to the existing SQLite database. The infrastructure (`database.py`, `get_db()`) is already in place.

---

### HIGH-03: Two Incompatible InfluxDB Client Patterns
**Severity**: HIGH (architectural)

The service uses two fundamentally different InfluxDB client libraries:

| Pattern | Files | Library | Async? |
|---------|-------|---------|--------|
| `InfluxDBQueryClient` (shared) | `analytics_endpoints.py`, `sports_endpoints.py`, `ha_automation_endpoints.py` | `shared.influxdb_query_client` | Yes (native async) |
| `InfluxDBClient` (influxdb-client) | `events_endpoints.py`, `energy_endpoints.py` | `influxdb_client.InfluxDBClient` | No (sync in async context) |

The sync `InfluxDBClient` in `events_endpoints.py` and `energy_endpoints.py` blocks the async event loop during every query. This means a slow InfluxDB query blocks ALL concurrent requests to the service.

**Impact**: Under load, sync InfluxDB calls in the primary events query path block the entire FastAPI event loop, causing cascading timeouts across all endpoints.

**Fix**: Standardize on the async `InfluxDBQueryClient` wrapper, or wrap sync calls in `asyncio.to_thread()`.

---

### HIGH-04: API Key Service Writes Secrets to Disk in Plaintext
**File**: `c:\cursor\HomeIQ\services\data-api\src\api_key_service.py`
**Lines**: 308-347
**Severity**: HIGH

```python
# api_key_service.py line 332-341
lines[i] = f"{env_var}={value}\n"
# ...
with open(config_path, 'w') as f:
    f.writelines(lines)
```

API keys are written directly to `.env.production` in plaintext. There is no encryption, no audit logging of key changes, and file permissions are not explicitly set.

**Fix**: Use encrypted storage for secrets, add audit logging, set restrictive file permissions (0o600).

---

### HIGH-05: Config Manager Path Traversal Risk
**File**: `c:\cursor\HomeIQ\services\data-api\src\config_manager.py`
**Line**: 64, 110
**Severity**: HIGH

```python
env_file = self.config_dir / f".env.{service}"
```

The `service` parameter is not validated against path traversal. While `pathlib.Path` prevents some attacks, a service name like `../../../etc/passwd` would resolve to a path outside the config directory. The `write_config` method would then write attacker-controlled content to arbitrary files.

Note: The `ADMIN_API_ALLOW_SECRET_WRITES` guard (line 115) only blocks keys matching sensitive patterns, not the path itself.

**Fix**: Validate service name against `^[a-zA-Z0-9_-]+$` regex before constructing the path. Also verify the resolved path is within `config_dir` using `resolved.relative_to(config_dir.resolve())`.

---

### HIGH-06: Sync InfluxDB `query_api.query()` Blocks Event Loop
**Files**: `c:\cursor\HomeIQ\services\data-api\src\events_endpoints.py` lines 1036, `c:\cursor\HomeIQ\services\data-api\src\energy_endpoints.py` lines 146, 193, 248, etc.
**Severity**: HIGH (performance)

```python
# events_endpoints.py line 1036 - BLOCKING CALL in async function
result = query_api.query(query)
```

The `influxdb_client.InfluxDBClient.query_api().query()` method is synchronous. When called from an `async def` endpoint, it blocks the entire event loop. Every InfluxDB query in events and energy endpoints blocks all other concurrent requests.

**Impact**: A single slow InfluxDB query (e.g., 30-day range scan) will freeze the entire data-api service for all users until the query completes.

**Fix**: Either use `asyncio.to_thread(query_api.query, query)` to run sync queries off the event loop, or migrate to the async `InfluxDBQueryClient` wrapper.

---

## MEDIUM Issues

### MED-01: `health_endpoints.py` Route Handler Has `self` Parameter
**File**: `c:\cursor\HomeIQ\services\data-api\src\health_endpoints.py`
**Lines**: 383-384
**Severity**: MEDIUM

```python
@self.router.get("/event-rate", response_model=dict[str, Any])
async def get_event_rate(self):  # 'self' will be treated as a path/query parameter
```

This route handler is defined inside `_add_routes()` with a `self` parameter. FastAPI will try to resolve `self` as a dependency/query parameter, not as the class instance. This will cause a `422 Unprocessable Entity` error at runtime unless `self` happens to be provided as a query parameter.

**Fix**: Remove the `self` parameter from the route handler function signature.

---

### MED-02: `simple_main.py` Is Dead Code with Security Risks
**File**: `c:\cursor\HomeIQ\services\data-api\src\simple_main.py`
**Lines**: 1-84
**Severity**: MEDIUM

This alternate entry point creates a separate FastAPI app called "HA Ingestor Admin API - Simplified" on port 8004 with:
- CORS `allow_origins=["*"]` with `allow_credentials=True` (line 46-51) -- the dangerous combination
- Zero authentication on all endpoints
- Different import paths (`src.config_manager` instead of `.config_manager`)

If accidentally deployed, it would expose unauthenticated config management endpoints.

**Fix**: Remove this file if unused. If needed for development, add a comment explaining its purpose and ensure it cannot be accidentally deployed.

---

### MED-03: `auth.py` Is 229 Lines of Dead Code
**File**: `c:\cursor\HomeIQ\services\data-api\src\auth.py`
**Lines**: 1-229
**Severity**: MEDIUM

The local `auth.py` defines `AuthManager` and `User` classes, but `main.py` imports `AuthManager` from `shared.auth` (line 33). The local `auth.py` is never imported by any file in the service. The docstring even says "Authentication Manager for Admin API" (line 2), confirming it was copied from the admin-api service.

**Fix**: Remove `src/auth.py` to eliminate confusion and dead code.

---

### MED-04: `health_check.py` Uses aiohttp Instead of FastAPI
**File**: `c:\cursor\HomeIQ\services\data-api\src\health_check.py`
**Severity**: MEDIUM

This file defines a `HealthCheckHandler` using `aiohttp.web`, but the service uses FastAPI. It appears to be dead code from a previous architecture.

**Fix**: Remove this file.

---

### MED-05: Duplicate InfluxDB Configuration with Inconsistent Defaults
**Files**: Multiple endpoint files
**Severity**: MEDIUM

InfluxDB connection parameters are duplicated across 6+ files with **inconsistent** defaults:

| File | Default Org | Default Token |
|------|-------------|---------------|
| `events_endpoints.py` line 36 | `"homeiq"` | `"homeiq-token"` |
| `energy_endpoints.py` line 83 | `"homeiq"` | `"homeiq-token"` |
| `analytics_endpoints.py` | Uses shared client | (from shared config) |
| `sports_endpoints.py` | Uses shared client | (from shared config) |

The default token `"homeiq-token"` hardcoded in events and energy endpoints is a security concern if InfluxDB is exposed without proper configuration.

**Fix**: Centralize InfluxDB configuration in a single module. Remove hardcoded default tokens.

---

### MED-06: Entity List Allows Up to 10,000 Results
**File**: `c:\cursor\HomeIQ\services\data-api\src\devices_endpoints.py`
**Severity**: MEDIUM

```python
limit: int = Query(default=100, ge=1, le=10000, description="Maximum number of entities")
```

Allowing up to 10,000 entities in a single response can cause memory pressure and slow responses.

**Fix**: Reduce maximum to 1000 and implement cursor-based pagination for larger result sets.

---

### MED-07: No Query Timeouts on InfluxDB Queries
**Files**: All endpoint files that query InfluxDB
**Severity**: MEDIUM

No InfluxDB query has a timeout configured. A query scanning months of data could run for minutes, blocking the event loop (see HIGH-06) and consuming InfluxDB resources.

**Fix**: Set `timeout` parameter on InfluxDB client queries. Add the `REQUEST_TIMEOUT` env var (already defined in `main.py` line 125 but never used) as a query timeout.

---

### MED-08: Service Name Confusion - References to "admin-api"
**Severity**: LOW-MEDIUM

Multiple files reference "admin-api" instead of "data-api":
- `auth.py` line 2: `"Authentication Manager for Admin API"`
- `health_check.py`: `"service": "admin-api"`
- `health_endpoints.py`: `get_alert_manager("admin-api")`, `get_metrics_collector("admin-api")`
- `alert_endpoints.py`: `get_alert_manager("admin-api")`

**Fix**: Update all references from "admin-api" to "data-api".

---

### MED-09: `_get_event_categories` Returns Error Details in Response Body
**File**: `c:\cursor\HomeIQ\services\data-api\src\events_endpoints.py`
**Lines**: 822-832
**Severity**: MEDIUM

```python
except Exception as e:
    return {
        ...
        "error": str(e)  # Exposes internal error details to client
    }
```

This returns exception details (potentially including InfluxDB connection strings, query text, etc.) directly to the client in a 200 OK response.

**Fix**: Return a generic error message and log the details server-side. Or raise an HTTPException.

---

## Security Audit

### OWASP Top 10 Assessment

| OWASP Category | Risk | Status |
|----------------|------|--------|
| **A01: Broken Access Control** | LOW | Auth enforced on all sensitive routes via `_auth_dependency` |
| **A02: Cryptographic Failures** | MEDIUM | API keys stored in plaintext `.env.production`; default InfluxDB tokens |
| **A03: Injection** | HIGH | MCP router Flux injection (CRIT-01); weak sanitizer vs robust `flux_utils.py` |
| **A04: Insecure Design** | MEDIUM | Mock data in production metrics; in-memory webhook storage |
| **A05: Security Misconfiguration** | LOW | CORS now properly configured; simple_main.py is dead code risk |
| **A06: Vulnerable Components** | LOW | Dependencies reasonably up-to-date |
| **A07: Auth Failures** | LOW | Bearer token auth with `secrets.compare_digest()` |
| **A08: Data Integrity Failures** | MEDIUM | No request signing; webhook HMAC is good practice |
| **A09: Logging Failures** | LOW | Good logging throughout; some exception details leak to clients |
| **A10: SSRF** | LOW | `aiohttp.ClientSession` calls to internal services only |

### What's Done Well (Security)
1. `flux_utils.sanitize_flux_value()` is comprehensive and used consistently in events, energy, sports, and HA automation endpoints
2. Auth dependency applied to ALL sensitive routers (CRIT-06 from prior review is resolved)
3. CORS properly disables credentials when wildcard origins are used
4. Webhook delivery uses HMAC-SHA256 signatures
5. Rate limiting is configured with burst support
6. `secrets.compare_digest()` used for constant-time API key comparison
7. `config_manager.py` blocks sensitive key writes by default (`ADMIN_API_ALLOW_SECRET_WRITES`)
8. File permissions set to 0o600 on config writes

---

## API Design Review

### Strengths
- Consistent prefix pattern (`/api/v1/`) for all data endpoints
- Proper HTTP method usage (GET for queries, POST for creation, DELETE for removal)
- Pydantic response models for type safety
- Query parameter validation with `ge`/`le` bounds on most numeric params
- Good use of FastAPI tags for OpenAPI documentation grouping

### Issues
1. **Inconsistent response models**: Some endpoints return `APIResponse` wrapper, others return raw dicts, others return Pydantic models directly
2. **Mixed error responses**: Some raise `HTTPException`, others return error info in 200 responses (MED-09)
3. **No API versioning strategy**: Everything is `/api/v1/` but there's no mechanism for v2 migration
4. **`/events/stream` is misleading**: Despite the name, it returns a snapshot, not a stream (line 738-763)

---

## Database Layer Analysis

### SQLite (via SQLAlchemy 2.0 Async)

**Excellent Configuration** (`c:\cursor\HomeIQ\services\data-api\src\database.py`):
- WAL mode enabled for concurrent read/write
- `synchronous=NORMAL` for better write performance with crash safety
- 64MB cache configured via `PRAGMA cache_size`
- Memory temp tables for fast temporary operations
- Foreign keys enforced
- 30-second busy timeout prevents immediate lock failures
- Configurable via environment variables (`SQLITE_TIMEOUT`, `SQLITE_CACHE_SIZE`)

**Session Management**: Proper `get_db()` dependency with auto commit/rollback/cleanup. `expire_on_commit=False` prevents lazy loading issues.

**Models** (`models/device.py`, `models/entity.py`, `models/team_preferences.py`):
- Well-designed with proper indexes and relationships
- Cascade delete configured correctly
- JSON column type for flexible list storage (team_preferences)
- Minor: Some duplicate index definitions (Column `index=True` AND explicit `Index()`)

### InfluxDB

**Client Pattern Issues**:
- Two client libraries used (see HIGH-03)
- Sync client blocks event loop in primary data path (see HIGH-06)
- No connection health checks or reconnection logic in per-endpoint clients
- No query timeout configuration

**Query Construction**:
- `flux_utils.sanitize_flux_value()` is a strong implementation
- Proper use of tag-based filtering for efficient InfluxDB queries
- Smart query routing by time range (Epic 45.5 in events_endpoints.py)

---

## Performance Recommendations

### P0 - Immediate
1. **Wrap sync InfluxDB calls in `asyncio.to_thread()`** (HIGH-06): The events and energy endpoints block the event loop on every query
2. **Add query timeouts** (MED-07): Set timeout on all InfluxDB queries to prevent unbounded execution

### P1 - This Sprint
3. **Standardize on async InfluxDB client**: Migrate events and energy endpoints to use `InfluxDBQueryClient`
4. **Remove mock data from analytics**: Return `null` or 503 for unimplemented metrics instead of random numbers
5. **Add connection pooling**: The shared client pattern is now used but lacks connection pool configuration

### P2 - Next Sprint
6. **Add request-level metrics**: Track actual response times, error rates, and throughput per endpoint
7. **Implement cursor-based pagination**: Replace offset/limit with cursor tokens for large result sets
8. **Add caching for frequently-accessed data**: The `SimpleCache` exists but is not used by events or energy endpoints

---

## Test Coverage Analysis

### Existing Tests (10 files)

| Test File | What It Tests | Lines |
|-----------|---------------|-------|
| `test_main.py` | App creation, root endpoint, health endpoint | Basic |
| `test_database.py` | SQLite connection, WAL mode, session management | Good |
| `test_models.py` | Pydantic model validation | Basic |
| `test_flux_security.py` | `sanitize_flux_value()` edge cases | Good |
| `test_hygiene_endpoints.py` | Device hygiene scoring | Good |
| `test_entity_registry.py` | Entity CRUD operations | Moderate |
| `test_entity_registry_endpoints.py` | Entity API endpoints | Moderate |
| `test_analytics_uptime.py` | Uptime calculation | Minimal |
| `conftest.py` | Shared fixtures | N/A |
| `integration/test_database_operations.py` | SQLite operations | Basic |

### Critical Coverage Gaps

| Component | Test Coverage | Risk |
|-----------|-------------|------|
| **Events endpoints** (1224 lines) | ZERO | CRITICAL - Primary data path |
| **Energy endpoints** (763 lines) | ZERO | HIGH - Smart meter queries |
| **Sports endpoints** (839 lines) | ZERO | MEDIUM - Game data flow |
| **HA automation endpoints** (607 lines) | ZERO | HIGH - Webhook delivery |
| **MCP router** (179 lines) | ZERO | HIGH - AI code execution |
| **Docker endpoints** (161 lines) | ZERO | MEDIUM - Container management |
| **Docker service** (437 lines) | ZERO | MEDIUM - Docker operations |
| **Config manager** (413 lines) | ZERO | MEDIUM - Config file I/O |
| **Cache** (102 lines) | ZERO | LOW - Simple wrapper |
| **Auth (local)** (229 lines) | ZERO | LOW - Dead code |

**Estimated Coverage**: ~20% of source code by lines, ~15% of endpoints

### Recommended Test Priorities
1. Events endpoints - happy path InfluxDB query, error handling, filter construction
2. Flux injection prevention - test MCP router sanitization gaps
3. Energy endpoints - correlation queries, power readings
4. HA automation - webhook lifecycle, event detection
5. Config manager - path traversal prevention, sensitive key blocking

---

## Docker/Deployment Analysis

### Dockerfile
The Dockerfile (`c:\cursor\HomeIQ\services\data-api\Dockerfile`) follows good practices:
- Multi-stage build (if applicable)
- Non-root user execution
- Health check endpoint configured
- Python dependencies installed with `--no-cache-dir`

### Issues
- `simple_main.py` could be accidentally used as the entrypoint
- No resource limits defined in Dockerfile (should be in docker-compose)
- The `docker` Python package is imported but Docker socket access requires privileged mounting

---

## Fix Priority Matrix

| Priority | Issue | Effort | Impact | Risk if Unfixed |
|----------|-------|--------|--------|-----------------|
| **P0 - Immediate** | CRIT-01: MCP Router weak sanitization + broken imports | Medium | Critical | Non-functional endpoints; Flux injection if fixed naively |
| **P0 - Immediate** | CRIT-02: Silent empty returns on InfluxDB errors | Low | Critical | Hidden infrastructure failures |
| **P0 - Immediate** | HIGH-06: Sync InfluxDB blocks event loop | Medium | High | Service freezes under load |
| **P1 - This Week** | HIGH-01: Mock data in production metrics | Medium | High | Misleading dashboards |
| **P1 - This Week** | HIGH-02: In-memory webhook storage | Medium | High | Webhooks lost on restart |
| **P1 - This Week** | HIGH-03: Two InfluxDB client patterns | High | High | Maintenance burden |
| **P1 - This Week** | MED-01: health_endpoints self parameter | Low | Medium | /event-rate returns 422 |
| **P2 - This Sprint** | HIGH-04: Plaintext API key storage | Medium | High | Secret exposure |
| **P2 - This Sprint** | HIGH-05: Config manager path traversal | Low | Medium | File system access |
| **P2 - This Sprint** | MED-05: Inconsistent InfluxDB defaults | Low | Medium | Config confusion |
| **P2 - This Sprint** | MED-07: No query timeouts | Low | Medium | Unbounded queries |
| **P3 - Next Sprint** | MED-02: Dead simple_main.py | Low | Low | Accidental deployment risk |
| **P3 - Next Sprint** | MED-03: Dead auth.py | Low | Low | Code clutter |
| **P3 - Next Sprint** | MED-04: Dead health_check.py | Low | Low | Code clutter |
| **P3 - Next Sprint** | MED-06: 10k entity limit | Low | Medium | Memory pressure |
| **P3 - Next Sprint** | MED-08: Service name confusion | Low | Low | Developer confusion |
| **P3 - Next Sprint** | MED-09: Error details in responses | Low | Medium | Information leakage |
| **P4 - Backlog** | TEST: Events endpoints (0% coverage) | High | Critical | Regression risk |
| **P4 - Backlog** | TEST: Energy endpoints (0% coverage) | Medium | High | Regression risk |
| **P4 - Backlog** | TEST: Integration tests | High | High | Integration failures |

---

## Summary of Findings

### What Works Well
1. **Flux sanitization** (`flux_utils.py`) is robust and used consistently across events, energy, sports, and HA automation endpoints
2. **SQLite configuration is excellent** - WAL mode, proper pragmas, async sessions, foreign keys, configurable via env vars
3. **Authentication is properly enforced** - `_auth_dependency` applied to all sensitive routers with `shared.auth.AuthManager`
4. **CORS is correctly configured** - Disables credentials when wildcard origins detected
5. **Error handling is generally good** - Most endpoints have proper try/except with logging and appropriate HTTP status codes
6. **Database models are well-designed** - Proper indexes, relationships, cascade deletes, JSON columns
7. **Rate limiting is in place** - Configurable per-minute rate with burst support
8. **Sports and HA automation sanitization** - All Flux queries now use `sanitize_flux_value()`
9. **Early logger pattern** - `_early_logger` prevents startup crashes

### What Needs Immediate Attention
1. **MCP router** is completely broken (bad imports) and has weak Flux sanitization
2. **Sync InfluxDB calls** in the primary data path block the entire service under load
3. **Silent error swallowing** in `_get_events_from_influxdb` hides infrastructure failures
4. **Mock data in production** misleads monitoring dashboards
5. **~80% of endpoints have zero test coverage** for a Tier 1 service

### Estimated Remediation Effort
- **P0 fixes**: 1-2 days (MCP router rewrite, error propagation, async wrapping)
- **P1 fixes**: 3-5 days (real metrics, webhook persistence, client standardization)
- **P2 fixes**: 2-3 days (path traversal, config cleanup, query timeouts)
- **P3+ fixes**: 1 sprint (dead code removal, naming cleanup)
- **Testing to 70% coverage**: 2-3 sprints

---

*Report generated by deep code review of all 35+ Python source files in `c:\cursor\HomeIQ\services\data-api\src\` and 10 test files in `c:\cursor\HomeIQ\services\data-api\tests\`*
