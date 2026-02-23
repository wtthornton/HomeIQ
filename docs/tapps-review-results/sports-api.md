# TAPPS Code Quality Review: sports-api

**Service Tier:** Tier 4 (Enhanced Data Sources)
**Review Date:** 2026-02-22
**Preset:** standard (gate threshold: 70.0)
**Reviewer:** Claude Code (tapps-mcp)

## Summary

| Metric | Value |
|--------|-------|
| Files Reviewed | 3 |
| Initial Failures | 1 (`main.py` scored 0.0) |
| Issues Found | 82 (78 lint + 2 security in `main.py`, 2 lint in `health_check.py`) |
| Issues Fixed | 82 |
| **Final Status** | **ALL PASS (100.0)** |

## Files Reviewed

### 1. `src/__init__.py`
- **Score:** 100.0 (before) -> 100.0 (after)
- **Gate:** PASS
- **Issues:** None

### 2. `src/health_check.py`
- **Score:** 90.0 (before) -> 100.0 (after)
- **Gate:** PASS (was passing before, now perfect)
- **Issues Found (2):**
  - `W293` (line 31): Blank line contains whitespace in docstring
  - `SIM108` (line 105): If-else block should use ternary operator for `influx_state` assignment
- **Fixes:**
  - Removed trailing whitespace from docstring blank line
  - Replaced 4-line if-else with ternary: `influx_state = "degraded" if write_age > 1800 else "healthy"`

### 3. `src/main.py`
- **Score:** 0.0 (before) -> 100.0 (after)
- **Gate:** FAIL -> PASS
- **Issues Found (80):**
  - `F401` (line 22): `typing.Literal` imported but unused
  - `PTH118`/`PTH120` (line 33): `os.path.join()`/`os.path.dirname()` should use `pathlib.Path`
  - `W293` (54 instances): Blank lines containing trailing whitespace throughout docstrings and method bodies
  - `ARG002` (line 542): Unused method argument `error` in `_handle_dns_error()`
  - `ARG001` (line 639): Unused function argument `app` in `lifespan()`
  - `B311` (line 605): `random.uniform()` flagged for non-crypto use (used for backoff jitter)
  - `B104` (line 729): Binding to all interfaces `0.0.0.0`
- **Fixes:**
  - Removed unused `Literal` import
  - Replaced `os.path.join(os.path.dirname(__file__), ...)` with `Path(__file__).resolve().parent / ...`
  - Added `from pathlib import Path` import
  - Removed trailing whitespace from all 54 blank lines (ruff auto-fix + unsafe-fix for docstrings)
  - Renamed `error` to `_error` in `_handle_dns_error()` signature (parameter preserved for API compatibility)
  - Renamed `app` to `_app` in `lifespan()` signature (required by FastAPI but not used in body)
  - Added `# noqa: S311` to `random.uniform(0, 1)` -- intentionally non-crypto, used for backoff jitter
  - Made bind address configurable via `SERVICE_HOST` env var (defaults to `0.0.0.0` for Docker) with `# noqa: S104` suppression

## Security Notes

Two Bandit findings remain as informational (acknowledged, not blocking):

1. **B311** (low severity): `random.uniform(0, 1)` in backoff jitter calculation. This is intentionally non-cryptographic -- it adds randomness to retry delays to prevent thundering herd, not for security purposes.

2. **B104** (medium severity): Binding to `0.0.0.0`. Standard for Docker container services; now configurable via `SERVICE_HOST` environment variable. Suppressed with noqa comment.

Both are acknowledged via noqa comments and the security gate passes.

## Complexity Note

tapps reports a maximum cyclomatic complexity estimate of ~14 (moderate level). The suggestion is to consider splitting complex functions. The `_component_status()` method in `health_check.py` and `_add_optional_fields()` in `main.py` are the most complex, but their logic is straightforward conditional field mapping that would not benefit significantly from further decomposition.

## Architecture Notes

The sports-api service is a well-structured Tier 4 service following the Epic 31 standalone pattern:
- **Single responsibility:** Polls Home Assistant for Team Tracker sensors, parses game state, writes to InfluxDB
- **InfluxDB fallback logic:** Configurable fallback hostnames with DNS error detection and automatic reconnection
- **Retry logic:** Exponential backoff with configurable max retries for InfluxDB writes
- **Rate limiting:** Sliding-window rate limiter on `/sports-data` endpoint (30 req/min)
- **Cache layer:** In-memory cache of parsed sensor data returned on API failures
- **Health checks:** Comprehensive `/health` endpoint tracking uptime, component connectivity, InfluxDB write success/failure counts, and background task state
- **Security:** API key authentication on data endpoints, Bearer token redaction in error logs
- **Background polling:** Continuous fetch loop with exponential backoff + jitter on consecutive errors
- **Rich data model:** Captures 6 high-value automation attributes (home/away, team colors, winner flags, event name, last play) beyond basic game state
