# Sports API -- Deep Code Review & Fix Plan

**Service:** `sports-api` (Port 8005, Tier 4 -- Enhanced Data Sources)
**Review Date:** 2026-02-06
**Reviewer:** Claude Opus 4.6 (automated deep review)
**Total Findings:** 4 CRITICAL | 8 HIGH | 10 MEDIUM | 10 LOW = 32

---

## Executive Summary

The sports-api polls the HA REST API for Team Tracker sensor data, parses it, and writes to InfluxDB. It has good code structure with clean separation of concerns and comprehensive type hints. However, critical security issues include no authentication on any endpoint, potential token leakage in error logs, no rate limiting, and unbounded raw data exposure via `all_attributes`.

---

## CRITICAL Issues (Must Fix)

### CRITICAL-1: No Authentication on Any API Endpoint

**File:** `src/main.py` lines 627-686

Every endpoint (`/`, `/sports-data`, `/stats`, `/metrics`, `/health`) is unauthenticated. `/sports-data` triggers live HA fetch + InfluxDB write on every call. The shared `AuthManager` at `shared/auth.py` exists but is unused.

**Fix:** Add API key authentication using shared `AuthManager` for `/sports-data` and `/stats`.

---

### CRITICAL-2: HA Long-Lived Access Token May Leak into Log Messages

**File:** `src/main.py` lines 260-262

`aiohttp` exceptions can include full request URL and headers (with Bearer token) in their string representation.

```python
# BROKEN:
logger.error(f"Error fetching Team Tracker sensors: {e}")

# FIXED:
safe_msg = str(e)
if self.ha_token:
    safe_msg = safe_msg.replace(self.ha_token, "[REDACTED]")
logger.error(f"Error fetching Team Tracker sensors: {safe_msg}")
```

---

### CRITICAL-3: No Rate Limiting -- Denial-of-Service Vector

**File:** `src/main.py` lines 656-668

`/sports-data` triggers HA fetch + InfluxDB write per call. No rate limiting. Shared `RateLimiter` exists but unused.

**Fix:** Add rate limiting middleware. Make `/sports-data` return cached data only (see HIGH-2).

---

### CRITICAL-4: `all_attributes` Field Stores Unbounded Raw Data

**File:** `src/main.py` line 319

Entire raw HA attributes dict stored and exposed to API consumers. Contains internal metadata, has no size bounds, no schema validation.

**Fix:** Remove `all_attributes` from parsed output. The parsed dict already captures useful attributes.

---

## HIGH Issues (Should Fix)

### HIGH-1: Deprecated `datetime.utcnow()` Used Throughout (8 Occurrences)

**Files:** `src/main.py` lines 354, 517, 538; `src/health_check.py` lines 25, 36, 60, 65, 103

```python
# BROKEN: datetime.utcnow().replace(tzinfo=timezone.utc)
# FIXED:  datetime.now(timezone.utc)
```

---

### HIGH-2: GET `/sports-data` Triggers Side Effects (Fetch + Write)

**File:** `src/main.py` lines 656-668

GET should be idempotent. Background task already handles polling. Every GET doubles as a write to InfluxDB.

**Fix:** Make `/sports-data` return cached data only:
```python
@app.get("/sports-data")
async def get_sports_data():
    sensors = sports_service.cached_sensors or []
    return SportsDataResponse(sensors=sensors, ...)
```

---

### HIGH-3: `SportsDataResponse.last_update` Type Mismatch Causes Runtime Crash

**File:** `src/main.py` lines 56-60, 664-668

`last_update: str` is required but `None` is passed on startup (no successful fetch yet). Pydantic ValidationError = 500.

**Fix:** `last_update: str | None = None`

---

### HIGH-4: InfluxDB Client Initialization Never Validates Connection

**File:** `src/main.py` lines 184-210

`InfluxDBClient3.__init__()` is lazy -- no network call. The try/except always succeeds. Fallback URL loop is dead code.

**Fix:** Perform a lightweight probe query after creating the client.

---

### HIGH-5: `_safe_int` Returns `None` Creating Inconsistent InfluxDB Schema

**File:** `src/main.py` lines 379-402

Pre-game sensors have no scores (`None`). InfluxDB fields are sometimes int, sometimes absent.

**Fix:** Conditionally add score fields only when values are present.

---

### HIGH-6: Global Mutable State with No Error Protection

**File:** `src/main.py` lines 589-604

If `startup()` fails partway, `sports_service` is half-initialized. `not sports_service` guard passes, subsequent calls fail with AttributeError.

**Fix:** Only set global on full success:
```python
service = SportsService()
await service.startup()
service.start_background_task()
sports_service = service  # atomic swap on full success
```

---

### HIGH-7: `/metrics` and `/health` Return Identical Responses

**File:** `src/main.py` lines 638-653

Both call `health_handler.handle(sports_service)`. `/stats` at line 671 already provides operational metrics.

**Fix:** Differentiate `/metrics` or remove it.

---

### HIGH-8: No Connection Pool Limits on aiohttp Session

**File:** `src/main.py` line 174

Default 100 total connections, unlimited per host. All pile up against single HA instance under load.

**Fix:** `connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)`

---

## MEDIUM Issues (Nice to Fix)

| # | Issue | File | Fix |
|---|---|---|---|
| M-1 | Fetches ALL HA states then filters client-side | src/main.py:237-255 | Use individual entity endpoints |
| M-2 | Major test coverage gaps (endpoints, retry, health) | tests/test_main.py | Add endpoint + retry tests |
| M-3 | Test deps in production requirements | requirements.txt:10-12 | Split into requirements-prod.txt |
| M-4 | `sys.path.append` hack for shared imports | src/main.py:30 | Rely on PYTHONPATH |
| M-5 | CORS origins hardcoded, methods too permissive | src/main.py:614-620 | Configurable via CORS_ORIGINS env var |
| M-6 | Fixed 300s error backoff (no exponential) | src/main.py:561 | Implement exponential backoff with jitter |
| M-7 | Emoji in structured JSON log messages | src/main.py:202,209 | Use plain text markers |
| M-8 | No `__init__.py` in tests directory | tests/ | Add empty file |
| M-9 | HA error response body discarded | src/main.py:256-258 | Log truncated error body |
| M-10 | Health check doesn't degrade on persistent fetch failures | src/health_check.py:68-80 | Check HA token, cache age, failure ratio |

---

## LOW Issues (Optional)

| # | Issue | Fix |
|---|---|---|
| L-1 | `SERVICE_VERSION` duplicated in two files | Import from `__init__.py` |
| L-2 | Dockerfile CMD hardcodes port despite SERVICE_PORT | Use shell form CMD |
| L-3 | `--disable-warnings` hides deprecation signals | Use selective filterwarnings |
| L-4 | Deprecated FastAPI event handler pattern | Use lifespan context manager |
| L-5 | README links to wrong Team Tracker repo | Fix to vasqued2/ha-teamtracker |
| L-6 | No env.template file | Create env.template |
| L-7 | Unnecessary pandas dependency (~50-80MB) | Remove `[pandas]` extra |
| L-8 | Unnecessary hasattr/getattr guards | Access attributes directly |
| L-9 | Missing conftest.py for shared fixtures | Extract shared fixtures |
| L-10 | Broken relative documentation links | Fix paths |

---

## Priority Fix Order

| # | Finding | Effort | Impact |
|---|---|---|---|
| 1 | HIGH-3: Fix `last_update` type (startup crash) | 1 min | Prevents startup crash |
| 2 | HIGH-2: Make `/sports-data` cache-only | 10 min | Eliminates DoS vector |
| 3 | CRITICAL-2: Sanitize tokens from error logs | 10 min | Token leakage prevention |
| 4 | CRITICAL-4: Remove `all_attributes` | 5 min | Info disclosure + memory |
| 5 | CRITICAL-1: Add API key authentication | 30 min | Use shared AuthManager |
| 6 | CRITICAL-3: Add rate limiting | 15 min | Defense in depth |
| 7 | HIGH-1: Replace `datetime.utcnow()` | 10 min | 8 occurrences |
| 8 | M-3 + L-7: Split requirements, remove pandas | 10 min | Smaller image |
| 9 | HIGH-4: Validate InfluxDB connection | 15 min | Make fallback functional |
| 10 | HIGH-6: Protect global startup state | 10 min | Prevent half-init |

---

## Positive Observations

1. Clean separation of concerns: `SportsService`, `HealthCheckHandler`, Pydantic models
2. Well-structured init methods broken into focused sub-methods
3. Graceful background task lifecycle with proper cancellation
4. Type annotations used consistently throughout
5. Multi-stage Docker build with non-root user
6. Comprehensive sensor parsing capturing full Team Tracker attribute set
7. DNS error detection and recovery pattern
8. Good `.dockerignore` excluding tests, docs, IDE files

---

**Maintained by:** HomeIQ DevOps Team
**Last Updated:** February 6, 2026
