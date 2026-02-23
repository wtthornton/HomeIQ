# TAPPS Code Quality Review: calendar-service

**Service Tier:** Tier 4 (AI Automation Features)
**Review Date:** 2026-02-22
**Preset:** standard (gate threshold: 70.0)
**Reviewer:** Claude Code (tapps-mcp)

## Summary

| Metric | Value |
|--------|-------|
| Files Reviewed | 6 |
| Initial Failures | 2 (`event_parser.py`, `ha_client.py`) |
| Issues Found | 32 (30 lint + 1 security + 1 complexity hint) |
| Issues Fixed | 28 |
| Issues Acknowledged | 3 (1 B104 intentional Docker binding, 1 ARG002 aiohttp handler signature, 1 I001 import sort) |
| **Final Status** | **ALL PASS** |

## Files Reviewed

### 1. `src/__init__.py`
- **Score:** 100.0
- **Gate:** PASS
- **Issues:** None

### 2. `src/config.py`
- **Score:** 85.0
- **Gate:** PASS
- **Issues Found (3):**
  - `W293` x3: Blank lines containing trailing whitespace (lines 15, 21, 27)
- **Note:** Passed gate (85.0 >= 70.0), whitespace-only warnings did not block

### 3. `src/event_parser.py` (FAILED initially)
- **Score:** 15.0 (before) -> 100.0 (after)
- **Gate:** FAIL -> PASS
- **Issues Found (17):**
  - `W293` x16: Blank lines containing trailing whitespace (lines 48, 51, 103, 113, 180, 183, 235, 238, 255, 258, 284, 289, 309, 313, 338, 343)
  - `SIM110` (line 170): Use `return any(pattern.search(text) for pattern in patterns)` instead of `for` loop
- **Fixes:**
  - Removed trailing whitespace from all 16 blank lines in docstrings
  - Replaced explicit `for` loop + `return True/False` pattern with idiomatic `return any(...)` expression
- **Complexity Note:** `max_cc_estimate: 12` (moderate). The `parse_datetime()` method handles multiple input types (datetime, str, dict with dateTime/date). Acceptable given the branching nature of format detection.

### 4. `src/ha_client.py` (FAILED initially)
- **Score:** 50.0 (before) -> 100.0 (after)
- **Gate:** FAIL -> PASS
- **Issues Found (10):**
  - `W293` x9: Blank lines containing trailing whitespace (lines 25, 75, 95, 126, 131, 187, 190, 243, 248)
  - `B905` (line 264): `zip()` without explicit `strict=` parameter
- **Fixes:**
  - Removed trailing whitespace from all 9 blank lines in docstrings
  - Added `strict=True` to `zip(calendar_ids, results)` call in `get_events_from_multiple_calendars()` -- both lists are guaranteed same length since `results` comes from `asyncio.gather(*tasks)` where `tasks` was built from `calendar_ids`

### 5. `src/health_check.py`
- **Score:** 95.0
- **Gate:** PASS
- **Issues Found (1):**
  - `ARG002` (line 22): Unused method argument `request`
- **Note:** Required by aiohttp handler signature; not fixed to avoid breaking the HTTP handler contract

### 6. `src/main.py`
- **Score:** 95.0
- **Gate:** PASS
- **Issues Found (2):**
  - `I001` (line 6): Import block is un-sorted or un-formatted
  - `B104` (line 388): Possible binding to all interfaces (security -- medium severity)
- **Note:** B104 is expected for Docker services that must bind all interfaces. I001 is a minor import ordering warning that does not affect functionality.

## Complexity Note

`event_parser.py` has a moderate complexity hint (`max_cc_estimate: 12`). The `parse_datetime()` static method handles three distinct input formats (datetime objects, ISO strings, and HA dict format with dateTime/date keys). This branching is inherent to the multi-format parsing requirement and is acceptable at current complexity levels.
