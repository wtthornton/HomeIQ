# TAPPS Code Quality Review: smart-meter-service

**Service Tier:** Tier 2 (Essential)
**Review Date:** 2026-02-22
**Preset:** standard (gate threshold: 70.0)
**Reviewer:** Claude Code (tapps-mcp)

## Summary

| Metric | Value |
|--------|-------|
| Files Reviewed | 6 |
| Initial Failures | 1 (`adapters/home_assistant.py`) |
| Issues Found | 17 (16 lint + 1 security) |
| Issues Fixed | 16 |
| Issues Acknowledged | 1 (B104 — intentional Docker binding) |
| **Final Status** | **ALL PASS** |

## Files Reviewed

### 1. `src/__init__.py`
- **Score:** 100.0 (before) -> 100.0 (after)
- **Gate:** PASS
- **Issues:** None

### 2. `src/adapters/__init__.py`
- **Score:** 100.0 (before) -> 100.0 (after)
- **Gate:** PASS
- **Issues:** None

### 3. `src/adapters/base.py`
- **Score:** 95.0 (before) -> 100.0 (after)
- **Gate:** PASS
- **Issues Found (1):**
  - `ARG002` (line 17): Unused method argument `session` in `test_connection()`
- **Fix:** Renamed parameter to `_session` (underscore prefix signals intentionally unused in abstract base method)

### 4. `src/adapters/home_assistant.py` (FAILED initially)
- **Score:** 50.0 (before) -> 100.0 (after)
- **Gate:** FAIL -> PASS
- **Issues Found (10):**
  - `W293` x8: Blank lines containing trailing whitespace (lines 24, 52, 57, 62, 98, 124, 152, 156)
  - `ARG002` x2: Unused method arguments `api_token` and `device_id` in `fetch_consumption()`
- **Fixes:**
  - Removed trailing whitespace from all 8 blank lines in docstrings (ruff auto-fix)
  - Renamed `api_token` -> `_api_token` and `device_id` -> `_device_id` (unused by design since HA adapter uses token from `__init__`)

### 5. `src/health_check.py`
- **Score:** 95.0 (before) -> 100.0 (after)
- **Gate:** PASS
- **Issues Found (1):**
  - `ARG002` (line 20): Unused method argument `request` in `handle()`
- **Fix:** Renamed to `_request` (required by aiohttp handler signature but not used in implementation)

### 6. `src/main.py`
- **Score:** 80.0 (before) -> 100.0 (after)
- **Gate:** PASS
- **Issues Found (5):**
  - `PTH118` (line 18): `os.path.join()` should use `Path` with `/` operator
  - `PTH120` (line 18): `os.path.dirname()` should use `Path.parent`
  - `SIM105` (line 333): Use `contextlib.suppress(NotImplementedError)` instead of try-except-pass
  - `SIM105` (line 344): Use `contextlib.suppress(asyncio.CancelledError)` instead of try-except-pass
  - `B104` (line 318): Possible binding to all interfaces (security — medium severity)
- **Fixes:**
  - Replaced `os.path.join(os.path.dirname(__file__), ...)` with `Path(__file__).parent / "../../shared"`
  - Added `import contextlib` and `from pathlib import Path`
  - Converted both try-except-pass blocks to `contextlib.suppress()` calls
  - Made bind address configurable via `BIND_ADDRESS` env var (defaults to `0.0.0.0` for Docker)
- **Remaining:** B104 still flagged (expected — Docker services must bind all interfaces), gate passes with `security_passed: true`

## Complexity Note

`main.py` has a moderate complexity hint (`max_cc_estimate: 12`). The `fetch_consumption()` method in `SmartMeterService` handles adapter calls, caching, phantom load detection, and fallback to mock data. Consider extracting cache logic or mock data fallback into separate methods if complexity grows further.
