# Device Health Monitor - Deep Review: Fix & Enhance Plan

**Service:** device-health-monitor (Tier 6: Device Management)
**Port:** 8019
**Review Date:** February 6, 2026
**Findings:** 3 CRITICAL, 4 HIGH, 8 MEDIUM, 11 LOW

---

## Executive Summary

The device-health-monitor service is **completely non-functional**. While it contains well-structured analysis logic (health_analyzer.py, ha_client.py, models.py), **none of this code is wired to any API endpoint**. The FastAPI app only exposes `/health` and `/` endpoints. Furthermore, the `data-api` service independently implements its own `DeviceHealthService`, making this service entirely redundant in its current state. Multiple crash bugs (timezone mismatch, missing `__init__.py`, wrong API response parsing) would prevent the code from working even if wired up.

**Strategic Decision Required:** Either (a) delete this service and consolidate its richer features into data-api, or (b) fully wire it up as a standalone microservice.

---

## CRITICAL Fixes (Must Fix)

### FIX-1: Wire Business Logic to API Endpoints
**Finding:** Service is a shell - zero endpoints connect to HealthAnalyzer, HAClient, or models
**Files:** `src/main.py`
**Action:**
- Import `HealthAnalyzer`, `HAClient` from respective modules
- Create `HAClient` instance in lifespan startup (read `HA_URL`, `HA_TOKEN` from env)
- Create `HealthAnalyzer` instance with the HAClient
- Store on `app.state`
- Add endpoints:
  - `POST /api/v1/devices/{device_id}/health` -> calls `analyze_device_health()`
  - `GET /api/v1/devices/health-summary` -> batch health check
  - `GET /api/v1/devices/maintenance-alerts` -> filtered alerts
- Close HAClient session in lifespan shutdown
- Add Pydantic request/response models using existing `DeviceHealthReport`, `HealthSummary`, `MaintenanceAlert`

### FIX-2: Add Missing `src/__init__.py`
**Finding:** Relative imports in health_analyzer.py (`from .ha_client import HAClient`) crash without `__init__.py`
**File:** Create `src/__init__.py`
**Action:** Create empty `src/__init__.py` file

### FIX-3: Fix Timezone-Aware vs Naive Datetime Crash
**Finding:** `datetime.now() - last_seen` crashes with `TypeError` when `last_seen` is timezone-aware
**Files:** `src/health_analyzer.py` lines 88, 150
**Action:**
- Replace `datetime.now()` with `datetime.now(timezone.utc)` everywhere
- Add `from datetime import timezone` import
- Also fix the same bug in `data-api/src/services/device_health.py` line 93

---

## HIGH Fixes

### FIX-4: Resolve Redundancy with data-api's DeviceHealthService
**Finding:** data-api has its own DeviceHealthService that actually serves the health endpoints
**Action:** Either:
- **(Option A - Consolidate):** Merge response time analysis, power anomaly detection, and Pydantic models from this service into data-api's DeviceHealthService. Delete this service.
- **(Option B - Separate):** Have data-api call this service over HTTP instead of implementing its own health logic. Remove data-api's duplicate code.

### FIX-5: Fix `get_entity_registry` Response Parsing
**Finding:** `data.get('entities', [])` fails on HA's flat list response with `AttributeError`
**File:** `src/ha_client.py` lines 130-138
**Action:**
```python
data = await response.json()
if isinstance(data, list):
    registry_dict = {e.get('entity_id'): e for e in data if e.get('entity_id')}
elif isinstance(data, dict):
    entities = data.get('entities', [])
    registry_dict = {e.get('entity_id'): e for e in entities if e.get('entity_id')}
```

### FIX-6: Rename/Fix `_calculate_response_time` - It Measures Inter-Event Intervals
**Finding:** Method measures time between state changes, not actual device response time
**File:** `src/health_analyzer.py` lines 143-171
**Action:**
- Rename to `_calculate_average_event_interval()`
- Update the threshold check at line 54 to use appropriate thresholds for event intervals
- Update issue message to describe event interval, not response time

### FIX-7: Secure Access Token Handling
**Finding:** Token stored as plain instance attribute, visible in stack traces
**File:** `src/ha_client.py` lines 28-31
**Action:**
- Remove `self.access_token` storage
- Build headers lazily or store only in the session headers
- Consider reading from env at session creation time (not constructor)

---

## MEDIUM Fixes

### FIX-8: Make Health Check Meaningful
**File:** `src/main.py` lines 42-49
**Action:** Check HA connectivity, verify env vars configured, return `degraded` status when dependencies are down

### FIX-9: Close HAClient Session in Lifespan
**File:** `src/main.py` lines 24-31
**Action:** Call `await ha_client.close()` in lifespan shutdown phase

### FIX-10: Validate `entity_id` Before URL Interpolation
**File:** `src/ha_client.py` lines 59, 101
**Action:** Validate entity_id matches expected pattern (`domain.object_id`) before building URL

### FIX-11: Use Shared Logging in All Modules
**Files:** `src/health_analyzer.py` line 13, `src/ha_client.py` line 12
**Action:** Replace `logging.getLogger(__name__)` with `logging.getLogger("device-health-monitor")` or import shared setup

### FIX-12: Fix `power_spec_w` Truthiness Check
**File:** `src/health_analyzer.py` line 105
**Action:** Change `if power_spec_w and actual_power_w:` to `if power_spec_w is not None and actual_power_w is not None:` and guard against division by zero

### FIX-13: Add Entity Iteration Limits
**File:** `src/health_analyzer.py` lines 173-182, 184-198
**Action:** Add `[:5]` limit to `_get_battery_level` and `_get_last_seen` loops, matching `_calculate_response_time`

### FIX-14: Fix Battery Level `or` Truthiness Bug
**File:** `src/health_analyzer.py` line 179
**Action:** Replace `attributes.get("battery_level") or attributes.get("battery")` with explicit None checks:
```python
battery = attributes.get("battery_level")
if battery is None:
    battery = attributes.get("battery")
```

### FIX-15: Add Bounds Checking on Battery Values
**File:** `src/health_analyzer.py` line 181
**Action:** Wrap in try/except, validate range 0-100, handle "unknown"/"unavailable" strings

---

## LOW Fixes

### FIX-16: Fix `sys.path.append` Path Calculation
**File:** `src/main.py` line 17
**Action:** Remove - rely on PYTHONPATH set in Dockerfile

### FIX-17: Use Pydantic Models as FastAPI Response Types
**File:** `src/health_analyzer.py` line 35
**Action:** Return `DeviceHealthReport` model directly instead of `dict[str, Any]`

### FIX-18: Make `priority` Field an Enum
**File:** `src/models.py` line 33
**Action:** Create `Priority` enum (low, medium, high) similar to `HealthSeverity`

### FIX-19: Remove Duplicate Docker Healthcheck
**File:** `Dockerfile` lines 25, 52-53
**Action:** Remove `curl` from `apk add`; remove Dockerfile HEALTHCHECK (docker-compose overrides it)

### FIX-20: Fix `--no-cache-dir` vs `--mount=type=cache` Conflict
**File:** `Dockerfile` lines 16-17
**Action:** Remove `--no-cache-dir` to leverage BuildKit cache

### FIX-21: Add Unit Tests
**Action:** Create `tests/` directory with tests for HealthAnalyzer, HAClient, models

### FIX-22: Add Logging for Silent Exception Swallowing
**File:** `src/health_analyzer.py` lines 196-197
**Action:** Replace `except Exception: pass` with `except Exception as e: logger.debug("Failed to parse timestamp: %s", e)`

---

## Enhancement Opportunities

### ENHANCE-1: Add HA API Response Caching
Implement per-entity state caching to avoid redundant HTTP requests when checking battery + last_seen for the same entity.

### ENHANCE-2: Prefer Battery-Specific Entities
In `_get_battery_level`, sort entities to check `sensor.*_battery` entities first before falling back to attribute-based detection.

### ENHANCE-3: Add Rate Limiting on HA API Calls
Implement a rate limiter or semaphore to prevent overwhelming HA during bulk health checks.

### ENHANCE-4: Support Configurable Thresholds
Make response time threshold (5000ms), battery threshold (20%), and last-seen threshold (24h) configurable via environment variables.
