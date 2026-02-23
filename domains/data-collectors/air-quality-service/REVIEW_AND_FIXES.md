# Air Quality Service -- Deep Code Review & Fix Plan

**Service:** `air-quality-service` (Port 8012, Tier 4 -- Enhanced Data Sources)
**Review Date:** 2026-02-06
**Reviewer:** Claude Opus 4.6 (automated deep review)
**Total Findings:** 4 CRITICAL | 8 HIGH | 10 MEDIUM | 8 LOW = 30

---

## Executive Summary

The air-quality-service fetches AQI data from OpenWeather API hourly and writes to InfluxDB, following the HomeIQ Epic 31 direct-write pattern. The codebase is small (~350 lines) and well-structured, but has significant issues: malformed error logging calls, naive datetimes throughout, no coordinate validation, API key exposure risk, and a README completely out of sync with implementation.

---

## CRITICAL Issues (Must Fix)

### CRITICAL-01: `log_error_with_context` Called With Wrong Signature

**File:** `src/main.py` lines 218-223, 258-263, 299-304

The shared `log_error_with_context(logger, message, error, **context)` expects an Exception object as the 3rd positional arg. The service passes it as a keyword, so `error` receives `str(e)` instead of the actual exception. All error logs report type as `"str"` instead of the actual exception class.

```python
# BROKEN (current):
log_error_with_context(logger, f"Error fetching AQI: {e}", service="air-quality-service", error=str(e))

# FIXED:
log_error_with_context(logger, f"Error fetching AQI: {e}", e, service="air-quality-service")
```

**Impact:** All error logging produces incorrect metadata. Error type classification is broken.

---

### CRITICAL-02: Naive Datetime Used Throughout -- Timezone-Dependent Timestamp Corruption

**Files:** `src/main.py` lines 9, 181, 203, 205; `src/health_check.py` lines 15, 23, 27, 39

All datetime usage is naive (no timezone). `datetime.fromtimestamp()` returns local time. If container timezone differs from UTC, all InfluxDB timestamps will be offset.

```python
# BROKEN:
timestamp = datetime.fromtimestamp(pollution_data.get('dt', datetime.now().timestamp()))
self.last_fetch_time = datetime.now()

# FIXED:
from datetime import datetime, timezone
timestamp = datetime.fromtimestamp(pollution_data.get('dt', datetime.now(timezone.utc).timestamp()), tz=timezone.utc)
self.last_fetch_time = datetime.now(timezone.utc)
```

---

### CRITICAL-03: No Input Validation on Latitude/Longitude

**File:** `src/main.py` lines 33-34, 82-84

No validation on coordinate ranges. `LATITUDE=999` sends invalid requests. Truthiness check `if lat and lon` rejects latitude 0 (equator) and longitude 0 (prime meridian).

```python
# FIX: Add validation
def _validate_coordinate(self, value, name, min_val, max_val):
    num = float(value)
    if not (min_val <= num <= max_val):
        raise ValueError(f"{name} must be between {min_val} and {max_val}, got {num}")
    return value

# FIX: Use "is not None" instead of truthiness
if lat is not None and lon is not None:
```

---

### CRITICAL-04: API Key Exposure Risk via Query Parameters and Logging

**File:** `src/main.py` lines 136-140, 148

OpenWeather API key is in query parameters. If debug logging is enabled, the full URL including `appid=<key>` gets logged by aiohttp.

```python
# FIX: Add log filter to redact API key
class APIKeyFilter(logging.Filter):
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
    def filter(self, record):
        if self.api_key and self.api_key in record.getMessage():
            record.msg = record.msg.replace(self.api_key, '***REDACTED***')
        return True
```

---

## HIGH Issues (Should Fix)

### HIGH-01: README is Completely Out of Sync With Implementation

**File:** `README.md`

| README Claims | Reality |
|---|---|
| FastAPI 0.121 | Uses aiohttp |
| AirNow API | Uses OpenWeather air_pollution API |
| `AIRNOW_API_KEY` env var | Actual: `WEATHER_API_KEY` |
| `INFLUXDB_BUCKET` default `air_quality_data` | Actual: `events` |
| `uvicorn src.main:app` | Uses `asyncio.run(main())` |
| API Docs at `/docs` | No /docs endpoint |

**Fix:** Rewrite README to match actual implementation.

---

### HIGH-02: No Retry Logic for External API Calls

**File:** `src/main.py` lines 132-225

Single API call with no retry. Transient failure = 1-hour data gap. For HVAC automations during wildfire smoke events, stale data has health implications.

**Fix:** Add retry with exponential backoff (3 attempts, 30s/120s/300s delays).

---

### HIGH-03: InfluxDB Write Failures Incorrectly Tracked as "Failed Fetches"

**File:** `src/main.py` line 264

`self.health_handler.failed_fetches += 1` incremented on InfluxDB write failures. But data was fetched successfully -- only storage failed. Can cause `failed_fetches > total_fetches` = negative success rate.

**Fix:** Add separate `total_writes` and `failed_writes` counters.

---

### HIGH-04: `cache_duration` Defined But Never Used

**File:** `src/main.py` line 49

`self.cache_duration = 60` is set but never referenced. Cached data returned regardless of age (could be 24+ hours old).

**Fix:** Implement cache TTL validation:
```python
def _is_cache_valid(self):
    if not self.cached_data or not self.last_fetch_time:
        return False
    age_minutes = (datetime.now(timezone.utc) - self.last_fetch_time).total_seconds() / 60
    return age_minutes < self.cache_duration
```

---

### HIGH-05: `sys.path` Manipulation Creates Fragile Import Chain

**File:** `src/main.py` lines 17-21

`sys.path.append` resolves incorrectly in Docker (`/shared` instead of `/app/shared`). Works by accident because Dockerfile sets `PYTHONPATH=/app:/app/src`.

**Fix:** Remove `sys.path.append` and rely on PYTHONPATH.

---

### HIGH-06: Float Truncation Loses Precision on Health-Sensitive Pollutant Data

**File:** `src/main.py` lines 188-190, 242-245

`int()` truncation: PM2.5 value `12.4` becomes `12`. EPA threshold is `12.0`. This loses critical precision for health automation triggers.

```python
# BROKEN: 'pm25': int(components.get('pm2_5', 0))
# FIXED:  'pm25': round(float(components.get('pm2_5', 0)), 2)
```

---

### HIGH-07: `KeyboardInterrupt` Cannot Be Caught in Async Context

**File:** `src/main.py` lines 335-341

Docker sends SIGTERM, not SIGINT. No SIGTERM handler registered. `except KeyboardInterrupt` never fires under asyncio.

**Fix:** Register signal handlers:
```python
import signal
loop = asyncio.get_event_loop()
for sig in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(sig, stop_event.set)
```

---

### HIGH-08: No Rate Limiting on `/current-aqi` Endpoint

**File:** `src/main.py` lines 266-282

No rate limiting. Misbehaving automation could flood the endpoint.

**Fix:** Add simple in-memory rate limiter (60 req/min).

---

## MEDIUM Issues (Nice to Fix)

| # | Issue | File | Fix |
|---|---|---|---|
| M-01 | Unused `pandas` in requirements-prod.txt (~50MB bloat) | requirements-prod.txt | Remove pandas line |
| M-02 | Missing `__init__.py` in test directories | tests/, tests/unit/ | Add empty files |
| M-03 | Bare `except:` in test fixture cleanup | tests/conftest.py:138 | Change to `except Exception:` |
| M-04 | Environment variable pollution between tests | tests/conftest.py:124 | Use `monkeypatch.setenv()` |
| M-05 | Health check doesn't verify component connectivity | src/health_check.py | Add components section |
| M-06 | AQI scale conversion oversimplified (only 5 values) | src/main.py:167 | Compute proper EPA AQI or document limitation |
| M-07 | `fetch_interval`/`cache_duration` not configurable | src/main.py:48-49 | Read from env vars |
| M-08 | No test for InfluxDB Point construction | tests/unit/test_air_quality_service.py | Assert on Point content |
| M-09 | No tests for `create_app()`, `run_continuous()`, `main()` | tests/ | Add lifecycle tests |
| M-10 | Dockerfile uses `python -m src.main` import conflicts | Dockerfile:41 | Document or simplify |

---

## LOW Issues (Optional)

| # | Issue | Fix |
|---|---|---|
| L-01 | `health_check.py` uses own logger, not shared | Pass logger from main.py |
| L-02 | Missing type hints in health_check.py | Add type annotations |
| L-03 | pytest.ini suppresses all warnings | Use selective filterwarnings |
| L-04 | Inconsistent use of `log_with_context` vs direct logger | Standardize logging approach |
| L-05 | F-strings evaluated even when log level disabled | Use lazy % formatting for DEBUG |
| L-06 | No `__version__` in package | Add to `__init__.py` |
| L-07 | Coverage threshold at 60% (low) | Raise to 80% |
| L-08 | .dockerignore excludes tests but coverage config references them | Minor inconsistency |

---

## Priority Fix Order

| # | Finding | Effort | Impact |
|---|---|---|---|
| 1 | CRITICAL-01: Fix log_error_with_context signature | 5 min | All error logs malformed |
| 2 | CRITICAL-02: Use timezone-aware datetimes | 15 min | Timestamps potentially wrong |
| 3 | CRITICAL-03: Validate coordinates | 15 min | Prevents garbage InfluxDB data |
| 4 | HIGH-01: Rewrite README | 30 min | Developers can't configure service |
| 5 | HIGH-02: Add retry logic | 30 min | 1-hour data gaps on transient failures |
| 6 | M-01: Remove unused pandas | 2 min | ~50MB image reduction |
| 7 | HIGH-04: Implement cache TTL | 15 min | Prevents stale data |
| 8 | HIGH-06: Preserve float precision | 5 min | Health-critical data accuracy |
| 9 | HIGH-03: Separate write failure tracking | 10 min | Accurate health reporting |
| 10 | CRITICAL-04: Add API key log redaction | 20 min | Credential exposure prevention |

---

## Positive Observations

1. Clean class structure with `AirQualityService` encapsulating all state
2. Proper async patterns -- `asyncio.to_thread` for blocking InfluxDB writes
3. Good test organization (GIVEN/WHEN/THEN pattern)
4. Fail-fast validation on missing credentials
5. Docker security: non-root user, multi-stage build, health check
6. Follows HomeIQ Epic 31 direct-write architecture

---

**Maintained by:** HomeIQ DevOps Team
**Last Updated:** February 6, 2026
