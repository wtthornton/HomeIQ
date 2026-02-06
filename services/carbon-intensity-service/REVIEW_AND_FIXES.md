# Carbon Intensity Service -- Deep Code Review & Fix Plan

**Service:** `carbon-intensity-service` (Port 8010, Tier 4 -- Enhanced Data Sources)
**Review Date:** 2026-02-06
**Reviewer:** Claude Opus 4.6 (automated deep review)
**Total Findings:** 6 CRITICAL | 8 HIGH | 11 MEDIUM | 7 LOW = 32

---

## Executive Summary

The carbon-intensity-service fetches grid carbon intensity data from WattTime v3 API and writes to InfluxDB. It has a mature standby-mode pattern for unconfigured credentials and proper placeholder detection. However, critical issues include: a test that always fails (asserts wrong exception), a logic bug where `ensure_valid_token()` reports success with no token, arithmetic crash on `None` API values, and a registration script that exposes credentials via CLI arguments.

---

## CRITICAL Issues (Must Fix)

### CRITICAL-01: Test Asserts Wrong Exception -- Always Fails

**File:** `tests/test_main.py` lines 158-163

Test expects `ValueError` matching `"WATTTIME_API_TOKEN"` but this exception never exists. When WattTime creds are missing, service enters standby mode (no exception). The only `ValueError` raised is for missing `INFLUXDB_TOKEN`.

**Fix:** Replace with tests matching actual behavior:
```python
async def test_missing_influxdb_token_raises():
    with pytest.raises(ValueError, match="INFLUXDB_TOKEN"):
        CarbonIntensityService()

async def test_missing_watttime_credentials_enters_standby(monkeypatch):
    monkeypatch.setenv('INFLUXDB_TOKEN', 'test_token')
    service = CarbonIntensityService()
    assert service.credentials_configured is False
```

---

### CRITICAL-02: `ensure_valid_token()` Returns `True` When No Token Exists

**File:** `src/main.py` lines 268-287

When user sets only `WATTTIME_API_TOKEN` (static token, no username/password) and token expires: method checks `not token_expires_at` (True), then `username and password` (False), falls to `return True`. Reports "valid" without checking `self.api_token` exists.

**Fix:** Add guard at end:
```python
if not self.api_token:
    logger.error("No API token available")
    return False
return True
```

---

### CRITICAL-03: `_parse_watttime_response` Crashes on `None` Values

**File:** `src/main.py` lines 289-307

`.get('renewable_pct', 0)` returns `None` when key exists with `None` value. `100 - None` raises `TypeError`.

**Fix:**
```python
carbon_intensity = raw_data.get('moer') or 0
renewable_pct = raw_data.get('renewable_pct') or 0
data = {
    'carbon_intensity': float(carbon_intensity),
    'renewable_percentage': float(renewable_pct),
    'fossil_percentage': 100.0 - float(renewable_pct),
}
```

---

### CRITICAL-04: `register_watttime.py` Exposes Password via CLI Arguments

**File:** `register_watttime.py` lines 176-184

Password passed as `sys.argv[2]` -- visible in process listing, shell history, audit logs.

**Fix:** Use `getpass.getpass()`:
```python
import getpass
password = getpass.getpass("Password: ")
```

---

### CRITICAL-05: API Token Partially Logged in Registration Script

**File:** `register_watttime.py` line 104

`print(f"Token received: {token[:30]}...")` -- 30 chars of JWT is enough to identify structure.

**Fix:** `print(f"Token received: {'*' * 20} (length: {len(token)})")`

---

### CRITICAL-06: InfluxDB Client `host` Parameter May Receive Full URL

**File:** `src/main.py` lines 132-137

`host=self.influxdb_url` where value is `"http://influxdb:8086"`. Depending on library version, may cause double-protocol URLs. This is a codebase-wide concern across HomeIQ services.

**Fix:** Parse URL and pass hostname only, or verify `influxdb3-python==0.3.0` behavior and add startup validation.

---

## HIGH Issues (Should Fix)

### HIGH-01: No Retry Logic for Transient HTTP Failures

**File:** `src/main.py` lines 396-409

Only retry for 401 (token expired). 429/500/502/503 all result in 15-minute wait. Carbon-aware automations get stale data.

**Fix:** Add exponential backoff for retryable status codes (3 attempts, 5/10/20s delays).

---

### HIGH-02: No Rate Limit / Quota Tracking for WattTime API

WattTime free tier: 100 calls/day. At 15-min intervals = 96 calls/day. Token refresh + 401 retries can exceed quota. No daily call counter, no rate limit header parsing.

**Fix:** Track daily API calls, stop fetching at 90 calls, parse `Retry-After` headers.

---

### HIGH-03: InfluxDB Write Failures Are Invisible to Health Monitoring

**File:** `src/main.py` lines 465-473

Errors logged but no counter in HealthCheckHandler. Health reports `"healthy"` while silently discarding every data point.

**Fix:** Add `influxdb_write_failures` and `last_successful_write` to health handler.

---

### HIGH-04: Health Check Returns HTTP 200 When Service Is Non-Functional

**File:** `src/health_check.py` lines 34-37

Credentials missing = HTTP 200, `"status": "healthy"`. Docker healthcheck and health-dashboard see green.

**Fix:** Return `"status": "unconfigured"` or add a `/ready` endpoint that returns 503.

---

### HIGH-05: Test Fixture Creates Real External Clients

**File:** `tests/test_main.py` lines 27-33

`startup()` creates real `aiohttp.ClientSession` and `InfluxDBClient3`. Incomplete mocks = real API calls in CI.

**Fix:** Mock external clients at fixture level.

---

### HIGH-06: `conftest.py` Depends on Non-Existent Top-Level `tests/path_setup.py`

**File:** `tests/conftest.py` lines 1-3

`from tests.path_setup import add_service_src` -- fragile import from project root.

**Fix:** Use self-contained path setup in conftest.

---

### HIGH-07: `requirements-prod.txt` Includes Unnecessary `pandas` (~50MB)

**File:** `requirements-prod.txt` line 4

`pandas` never imported. Service only writes to InfluxDB (no queries). ~50-80MB wasted in 192MB container.

**Fix:** Remove `pandas>=2.2.0,<3.0.0`.

---

### HIGH-08: No Connection Timeout on InfluxDB Writes

**File:** `src/main.py` line 461

`asyncio.to_thread(self.influxdb_client.write, point)` with no timeout. Blocked writes exhaust thread pool.

**Fix:** `await asyncio.wait_for(asyncio.to_thread(...), timeout=15.0)`

---

## MEDIUM Issues (Nice to Fix)

| # | Issue | Fix |
|---|---|---|
| M-01 | README documents wrong tech stack (FastAPI, wrong endpoints, wrong defaults) | Rewrite README |
| M-02 | `cache_duration=15` defined but never used (dead code) | Implement TTL or remove |
| M-03 | `fetch_interval` hardcoded at 900s, not configurable | Read from `FETCH_INTERVAL` env var |
| M-04 | All `datetime.now()` uses naive datetimes | Use `datetime.now(timezone.utc)` |
| M-05 | `sys.path.append` for shared module is fragile | Rely on PYTHONPATH |
| M-06 | No input validation on `GRID_REGION` | Validate alphanumeric + underscore |
| M-07 | No graceful signal handling for Docker shutdown | Register SIGTERM/SIGINT handlers |
| M-08 | Shallow test coverage (5 tests, many untested paths) | Target 85% coverage |
| M-09 | `grid_operator` tag derived by naive string split | Use lookup dict or defensive split |
| M-10 | `check_username_available` uses login-as-probe pattern | Document as unreliable |
| M-11 | `.dockerignore` groups `.env` with virtual envs | Move to separate section |

---

## LOW Issues (Optional)

| # | Issue | Fix |
|---|---|---|
| L-01 | Emoji characters in log messages | Use plain text markers |
| L-02 | Inconsistent status code check style | Use `if status in (200, 201)` |
| L-03 | No dev/test requirements file | Create requirements-dev.txt |
| L-04 | Version pinning strategy backwards (dev=exact, prod=ranges) | Swap strategies |
| L-05 | `__init__.py` has no `__version__` | Add version string |
| L-06 | pytest.ini suppresses all warnings | Use selective filterwarnings |
| L-07 | `register_watttime.py` not documented in README | Add documentation |

---

## Priority Fix Order

| # | Finding | Effort | Impact |
|---|---|---|---|
| 1 | CRITICAL-01: Fix broken test | Low | Broken test suite |
| 2 | CRITICAL-02: Fix token validation logic | Low | Unauthenticated API calls |
| 3 | CRITICAL-03: Handle None values in parsing | Low | Service crash on API changes |
| 4 | CRITICAL-06: Validate InfluxDB host parameter | Low | Potential data loss |
| 5 | HIGH-03: Add write failure tracking | Low | Silent data loss |
| 6 | HIGH-04: Fix health check for unconfigured state | Low | False positive monitoring |
| 7 | CRITICAL-04: Fix password exposure in CLI | Medium | Security breach |
| 8 | CRITICAL-05: Mask token in logs | Low | Token leakage |
| 9 | HIGH-01: Add retry logic | Medium | Data gaps |
| 10 | HIGH-07: Remove unused pandas | Low | Image bloat |

---

## Positive Observations

1. **Standby Mode Pattern**: Graceful degradation when credentials missing
2. **Placeholder Credential Detection**: Checks for common template values
3. **Cache Fallback**: Returns cached data on API failure
4. **`asyncio.to_thread` for InfluxDB**: Correct async pattern
5. **Multi-Stage Docker Build**: Builder/production separation
6. **Non-Root Container User**: appuser:1001
7. **Docker Healthcheck with Start Period**: Avoids false negatives
8. **Content-Type Validation**: On token refresh responses
9. **Structured Logging**: Via shared logging_config module

---

**Maintained by:** HomeIQ DevOps Team
**Last Updated:** February 6, 2026
