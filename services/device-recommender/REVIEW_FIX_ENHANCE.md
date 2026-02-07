# Device Recommender - Deep Review: Fix & Enhance Plan

**Service:** device-recommender (Tier 6: Device Management)
**Port:** 8023
**Review Date:** February 6, 2026
**Findings:** 3 CRITICAL, 7 HIGH, 12 MEDIUM, 12 LOW

---

## Executive Summary

The device-recommender service is an **empty shell** - all three engine modules (recommender.py, comparison_engine.py, ha_client.py) containing ~300 lines of code are completely dead. The FastAPI app only serves `/health` and `/`. Beyond the wiring gap, the recommendation engine uses hardcoded relevance scores (0.8 and 0.7), the user satisfaction calculator always returns 0.8, the comparison engine has an unpopulated "features" field, and both HA API response parsers are broken (calling `.get()` on a list). The service needs fundamental work to become functional.

---

## CRITICAL Fixes (Must Fix)

### FIX-1: Wire All Engine Modules to API Endpoints
**Finding:** recommender.py, comparison_engine.py, ha_client.py are 100% dead code
**File:** `src/main.py`
**Action:**
- Import `DeviceRecommender`, `DeviceComparisonEngine`, `HAClient`
- Create instances in lifespan startup
- Add endpoints:
  - `POST /api/v1/recommend` -> DeviceRecommender.recommend_devices()
  - `POST /api/v1/compare` -> DeviceComparisonEngine.compare_devices()
  - `GET /api/v1/devices` -> HAClient.get_user_devices()
- Close HAClient session in lifespan shutdown
- Create Pydantic request/response models

### FIX-2: Close HAClient Session - Prevent Resource Leak
**File:** `src/ha_client.py` lines 28-37, `src/main.py` lines 25-30
**Action:** Initialize HAClient in lifespan startup, close in shutdown

### FIX-3: Add Pydantic Request/Response Models
**Finding:** Zero input validation exists anywhere
**Action:** Create models for:
- `RecommendRequest` (device_type, requirements, user_devices)
- `CompareRequest` (device_ids, devices)
- `RecommendationResponse` (unified schema for both DB and user recommendations)
- `ComparisonResponse`

---

## HIGH Fixes

### FIX-4: Fix HA Device Registry Response Parsing
**Finding:** `data.get("devices", [])` crashes with AttributeError on HA's flat list response
**File:** `src/ha_client.py` line 49
**Action:**
```python
data = await response.json()
devices = data if isinstance(data, list) else data.get("devices", [])
return devices
```

### FIX-5: Fix Entity Registry Fallback Parsing
**Finding:** Same bug in fallback path - `data.get("entities", [])` on a list
**File:** `src/ha_client.py` line 67
**Action:** Same defensive pattern as FIX-4

### FIX-6: Implement Real Relevance Scoring
**Finding:** Hardcoded 0.8 and 0.7 make sorting meaningless
**File:** `src/recommender.py` lines 60, 75
**Action:**
- Use device rating, feature match count, price proximity to compute real scores
- Normalize to 0.0-1.0 range
- Document scoring algorithm

### FIX-7: Implement Real User Satisfaction Calculator
**Finding:** `_calculate_user_satisfaction()` always returns 0.8
**File:** `src/recommender.py` lines 95-98
**Action:** Analyze device health status, usage frequency, battery health to compute real scores

### FIX-8: Fix Silent Exception Swallowing in Entity Fallback
**Finding:** `except Exception: pass` hides all errors
**File:** `src/ha_client.py` lines 81-82
**Action:** Add `logger.error()` call with exception info

### FIX-9: Use Shared Structured Logging in All Modules
**Files:** `src/recommender.py` line 9, `src/comparison_engine.py` line 9, `src/ha_client.py` line 12
**Action:** Replace `logging.getLogger(__name__)` with `logging.getLogger("device-recommender")`

### FIX-10: Type the db_client Parameter
**File:** `src/recommender.py` line 15
**Action:** Use `Protocol` or import type with `TYPE_CHECKING` guard instead of `Any`

---

## MEDIUM Fixes

### FIX-11: Make Health Check Verify Dependencies
### FIX-12: Use Timezone-Aware datetime.now()
### FIX-13: Convert device_ids to Set in compare_devices()
**File:** `src/comparison_engine.py` lines 31-34
### FIX-14: Populate Features Comparison Point
**File:** `src/comparison_engine.py` lines 56-84
### FIX-15: Return HTTP 400 for <2 Devices Instead of 200
**File:** `src/comparison_engine.py` lines 36-40
### FIX-16: Guard _generate_recommendation Against Empty List
**File:** `src/comparison_engine.py` lines 93-96
### FIX-17: Validate HA URL at Construction
**File:** `src/ha_client.py` line 20
### FIX-18: Validate HA Token
**File:** `src/ha_client.py` lines 21-25
### FIX-19: Read DEVICE_DATABASE_API_URL/KEY from Environment
**Finding:** These env vars are set in docker-compose but never read by code
### FIX-20: Unify Recommendation Response Schema
**File:** `src/recommender.py` lines 52-76 - DB and user results have different fields
### FIX-21: Fix _find_similar_devices - Returns User's Own Devices
### FIX-22: Add API Versioning Prefix

---

## LOW Fixes

### FIX-23: Add `src/__init__.py`
### FIX-24: Remove sys.path.append
### FIX-25: Remove Unused curl from Dockerfile
### FIX-26: Fix `--no-cache-dir` vs `--mount=type=cache`
### FIX-27: Add pydantic to requirements.txt
### FIX-28: Add Unit Tests
### FIX-29: Validate Data Types in Comparison Points
### FIX-30: Add Rate Limiting
### FIX-31: Use Lazy Log Formatting
### FIX-32: Fix .dockerignore Location Issue (build context is repo root)
### FIX-33: Add CORS Middleware (if browser access needed)
### FIX-34: Fix Truthiness Check for 0-Watt Devices in Comparison
