# Calendar Service -- Deep Code Review & Fix Plan

**Service:** `calendar-service` (Port 8013, Tier 4 -- Enhanced Data Sources)
**Review Date:** 2026-02-06
**Reviewer:** Claude Opus 4.6 (automated deep review)
**Total Findings:** 5 CRITICAL | 9 HIGH | 11 MEDIUM | 8 LOW = 33

---

## Executive Summary

The calendar-service fetches HA calendar events, parses occupancy indicators (WFH/home/away), generates predictions, and writes to InfluxDB. It has good Pydantic-based config, proper async patterns, and a clever confidence scoring system. However, critical issues include: broken test infrastructure causing 0% effective coverage on core modules, fetching ALL HA entity states to discover calendars, unused Google API dependencies expanding the attack surface, no input validation on calendar entity IDs, and HA token stored as a plain string attribute.

**Overall Test Coverage: 45%** -- below the 70% `fail_under` threshold.

---

## CRITICAL Issues (Must Fix)

### CRITICAL-1: Broken conftest.py -- References Non-Existent Module

**File:** `tests/conftest.py` lines 1-3

`from tests.path_setup import add_service_src` -- `path_setup.py` doesn't exist, no `tests/__init__.py`. Import fails silently (suppressed by `--disable-warnings`). Coverage tracking misaligned: test files use `sys.path.insert(0, '../src')` but `--cov=src` tracks a different path. Result: `event_parser.py` and `ha_client.py` show 0% method coverage despite having comprehensive test cases.

**Fix:** Replace conftest with direct path setup:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
```
Also create `tests/__init__.py`.

---

### CRITICAL-2: `get_calendars()` Fetches ALL HA Entity States

**File:** `src/ha_client.py` lines 89-105

Fetches `/api/states` (ALL entities: 500-2000+, commonly 5-50MB JSON) to filter for `calendar.*`. Exposes sensitive data (GPS coordinates, alarm codes, camera tokens, door lock PINs).

**Fix:** Use HA's dedicated `/api/calendars` endpoint:
```python
async with self.session.get(f"{self.base_url}/api/calendars") as response:
    calendars_data = await response.json()
    return [cal['entity_id'] for cal in calendars_data]
```

---

### CRITICAL-3: HA API Token Stored as Plain Text Attribute

**File:** `src/ha_client.py` lines 28-35

`self.token = token` stored but never used after init (headers dict has it already). Accessible on object, leaks via repr/traceback/debugger.

**Fix:** Remove `self.token = token`. Add `__repr__` that redacts sensitive fields.

---

### CRITICAL-4: No Input Validation on Calendar Entity IDs -- Path Injection

**File:** `src/ha_client.py` lines 140-148

Calendar IDs from `CALENDAR_ENTITIES` env var used directly in URL construction. Value `../../../api/config` produces path traversal URL.

**Fix:** Validate against pattern:
```python
CALENDAR_ID_PATTERN = re.compile(r'^(calendar\.)?[a-z0-9_]+$')
def _validate_calendar_id(self, calendar_id):
    if not CALENDAR_ID_PATTERN.match(calendar_id.strip()):
        raise ValueError(f"Invalid calendar entity ID: {calendar_id!r}")
```

---

### CRITICAL-5: Unused Google API Dependencies in Production

**File:** `requirements-prod.txt` lines 7-10

4 Google packages never imported (confirmed: no `import google` anywhere). Removed in v2.0 per README. Adds 30-50MB, brings `httplib2` (CVE-2021-21240), increases supply chain risk.

**Fix:** Remove all 4 lines from `requirements-prod.txt`:
```
google-auth==2.25.2
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
google-api-python-client==2.110.0
```

---

## HIGH Issues (Should Fix)

### HIGH-1: `predict_home_status()` Return Type Inconsistency

**File:** `src/main.py` lines 176, 250, 263

Declares `-> dict[str, Any]` but returns `None` on error.

**Fix:** Change to `-> dict[str, Any] | None`

---

### HIGH-2: No Retry Logic for HA API Calls

**File:** `src/ha_client.py` (all API methods)

Single attempt per call. 15-min fetch interval means transient failure = 15-min data gap. HA restarts and network hiccups are common on local networks.

**Fix:** Add retry with exponential backoff (3 attempts).

---

### HIGH-3: `except KeyboardInterrupt` Never Fires in Async Context

**File:** `src/main.py` lines 374-377

Docker sends SIGTERM -> asyncio cancels task -> CancelledError, not KeyboardInterrupt.

**Fix:** `except asyncio.CancelledError:`

---

### HIGH-4: UTC End-of-Day Calculation Wrong for Local Time Zones

**File:** `src/main.py` lines 131-132

`now = datetime.now(timezone.utc)` then `end_of_day = now.replace(hour=23, ...)` -- calculates end-of-day in UTC, not user's local time. For UTC-8 user at 8 PM local (04:00 UTC), fetches ~48 hours of events.

**Fix:** Make timezone configurable or fetch from HA `/api/config`:
```python
from zoneinfo import ZoneInfo
local_tz = ZoneInfo(settings.timezone)  # e.g., "America/Los_Angeles"
now_local = datetime.now(local_tz)
end_of_day = now_local.replace(hour=23, minute=59, second=59)
```

---

### HIGH-5: Hardcoded 30-Minute Travel Time Estimate

**File:** `src/main.py` lines 214-215

Not configurable. Rural users may need 60+ min; apartment users may need 5 min.

**Fix:** Add `default_travel_time_minutes: int = 30` to config.py.

---

### HIGH-6: InfluxDB Client `host` Receives Full URL Instead of Hostname

**File:** `src/main.py` lines 107-112

`host="http://influxdb:8086"` -- may cause double-protocol issues depending on library version.

**Fix:** Parse URL: `host=urlparse(self.influxdb_url).hostname`

---

### HIGH-7: `sys.path.append` in Production Code

**File:** `src/main.py` line 15

Redundant with Dockerfile `PYTHONPATH=/app:/app/src`. Can cause import shadowing.

**Fix:** Remove the line.

---

### HIGH-8: Mixed Naive and Timezone-Aware Datetimes in Health Check

**File:** `src/health_check.py` lines 15, 25, 29, 44

Health check uses `datetime.now()` (naive) while main uses `datetime.now(timezone.utc)`. Mixing raises `TypeError` on subtraction.

**Fix:** Use `datetime.now(timezone.utc)` throughout health_check.py.

---

### HIGH-9: Missing InfluxDB Fields vs Documented Schema

**File:** `src/main.py` lines 276-283

`event_count`, `current_event_count`, `upcoming_event_count` computed in prediction but never written to InfluxDB. README documents them in schema.

**Fix:** Add missing `.field()` calls:
```python
.field("event_count", int(prediction.get('event_count', 0)))
.field("current_event_count", int(prediction.get('current_event_count', 0)))
.field("upcoming_event_count", int(prediction.get('upcoming_event_count', 0)))
```

---

## MEDIUM Issues (Nice to Fix)

| # | Issue | Fix |
|---|---|---|
| M-01 | Version drift between dev/prod requirements | Tighten prod ranges to match tested versions |
| M-02 | Unused `pandas` in requirements-prod.txt (~150MB) | Remove pandas line |
| M-03 | 45% test coverage, below 70% threshold | Fix C-1 to align coverage tracking |
| M-04 | No API endpoints beyond `/health` | Add `/prediction`, `/events`, `/refresh` |
| M-05 | Regex patterns not pre-compiled | Pre-compile at class level |
| M-06 | Default "not home" when no events is counterintuitive | Default to `currently_home: True` |
| M-07 | Broad `except Exception` hides programming bugs | Catch specific exceptions |
| M-08 | `hours_until_arrival=0` used as sentinel for "unknown" | Use -1.0 or omit field when None |
| M-09 | No SIGTERM signal handling | Register signal handlers |
| M-10 | No rate limiting on health endpoint | Add simple cache or throttle |
| M-11 | `websockets` dependency may be unnecessary | Review shared module dependency |

---

## LOW Issues (Optional)

| # | Issue | Fix |
|---|---|---|
| L-01 | README documents wrong env var names | Update to actual HA_HTTP_URL, etc. |
| L-02 | tests/README.md references non-existent files | Update file listing |
| L-03 | Dockerfile CMD coupled to PYTHONPATH | Document or use explicit path |
| L-04 | f-strings in log statements cause eager evaluation | Use lazy % formatting for DEBUG |
| L-05 | CalendarEventParser is class of all static methods | Style preference, functional as-is |
| L-06 | `--disable-warnings` suppresses useful diagnostics | Use selective filterwarnings |
| L-07 | HTML/XML coverage reports on every test run | Keep only term-missing in defaults |
| L-08 | Fragile dash-counting heuristic for timezone detection | Simplify with fromisoformat + replace Z |

---

## Priority Fix Order

| # | Finding | Effort | Impact |
|---|---|---|---|
| 1 | CRITICAL-5: Remove unused Google deps | 2 min | Security surface + 30-50MB |
| 2 | M-02: Remove unused pandas | 1 min | ~150MB image reduction |
| 3 | HIGH-8: Fix naive datetimes in health_check | 5 min | Prevent TypeError |
| 4 | HIGH-1: Fix return type annotation | 2 min | Type safety |
| 5 | HIGH-9: Add missing InfluxDB fields | 5 min | Schema completeness |
| 6 | HIGH-3: Fix KeyboardInterrupt catch | 2 min | Correct shutdown |
| 7 | M-08: Fix hours_until_arrival sentinel | 3 min | Correct automation triggers |
| 8 | CRITICAL-1: Fix conftest.py, add tests/__init__.py | 15 min | Restore coverage tracking |
| 9 | CRITICAL-2: Switch to /api/calendars endpoint | 10 min | Security + performance |
| 10 | CRITICAL-4: Add entity ID validation | 15 min | Prevent path injection |
| 11 | CRITICAL-3: Remove self.token, add __repr__ | 5 min | Token protection |
| 12 | HIGH-7: Remove sys.path.append | 5 min | Import stability |
| 13 | HIGH-4: Fix UTC end-of-day calculation | 30 min | Correct event fetching |
| 14 | HIGH-6: Parse InfluxDB URL | 10 min | Connection reliability |
| 15 | HIGH-5: Make travel time configurable | 5 min | User flexibility |

---

## OWASP Security Assessment

| Category | Status | Finding |
|---|---|---|
| A01 Broken Access Control | WARN | No auth on /health (acceptable for Tier 4) |
| A02 Cryptographic Failures | FAIL | Token as plain text attribute (C-3) |
| A03 Injection | FAIL | No entity ID validation (C-4) |
| A05 Security Misconfiguration | FAIL | Unused Google OAuth deps (C-5) |
| A10 SSRF | FAIL | Fetches entire HA state tree (C-2); unvalidated IDs in URLs (C-4) |

---

## Positive Observations

1. **Pydantic Settings**: Clean centralized config with `BaseSettings`
2. **Async Context Manager**: Proper resource management on HA client
3. **Concurrent Calendar Fetching**: `asyncio.gather()` with `return_exceptions=True`
4. **`asyncio.to_thread` for InfluxDB**: Correct async pattern
5. **Health Check Staleness Detection**: 30-min threshold for silent failures
6. **Multi-Stage Docker Build**: Proper builder/production separation
7. **Non-Root User**: appuser:appgroup (UID/GID 1001)
8. **Error Isolation in parse_multiple_events**: Individual failures don't block others
9. **WFH-Overrides-Away Logic**: Correct precedence handling
10. **Confidence Scoring System**: Multi-factor with reasonable defaults

---

**Maintained by:** HomeIQ DevOps Team
**Last Updated:** February 6, 2026
