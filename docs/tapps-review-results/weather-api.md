# TAPPS Code Quality Review: weather-api

**Service Tier:** Tier 2 (Essential)
**Review Date:** 2026-02-22
**Preset:** standard (gate threshold: 70.0)
**Reviewer:** Claude Code (tapps-mcp)

## Summary

| Metric | Value |
|--------|-------|
| Files Reviewed | 3 |
| Initial Failures | 0 |
| Issues Found | 15 (2 lint + 1 security + 12 f-string logging) |
| Issues Fixed | 15 |
| **Final Status** | **ALL PASS (100.0)** |

## Files Reviewed

### 1. `src/__init__.py`
- **Score:** 100.0 (before) -> 100.0 (after)
- **Gate:** PASS
- **Issues:** None

### 2. `src/health_check.py`
- **Score:** 90.0 (before) -> 100.0 (after)
- **Gate:** PASS
- **Complexity:** Moderate (max CC ~11)
- **Issues Found (2):**
  - `W293` (line 31): Blank line contains whitespace in docstring
  - `SIM108` (line 105): If-else block should use ternary operator for `influx_state` assignment
- **Fixes:**
  - Removed trailing whitespace from blank line in `handle()` docstring
  - Replaced 3-line if-else block with ternary: `influx_state = "degraded" if write_age > 1800 else "healthy"`

### 3. `src/main.py`
- **Score:** 100.0 (before) -> 100.0 (after)
- **Gate:** PASS
- **Complexity:** Moderate (max CC ~12)
- **Issues Found (13):**
  - `B104` (line 504): Possible binding to all interfaces `0.0.0.0` (security -- medium severity, OWASP A05:2021)
  - 12 instances of f-string logging (G004 pattern) across `_initialize_influxdb()`, `fetch_weather()`, `store_in_influxdb()`, and `run_continuous()` -- f-strings in logger calls defeat lazy evaluation and waste CPU when the log level is disabled
- **Fixes:**
  - Made bind address configurable via `SERVICE_HOST` env var (defaults to `0.0.0.0` for Docker) with `# noqa: S104` suppression and explanatory comment
  - Converted all 12 f-string logging calls to %-style formatting for proper lazy evaluation:
    - `logger.info(f"...")` -> `logger.info("...", arg1, arg2)`
    - `logger.warning(f"...")` -> `logger.warning("...", arg1, arg2)`
    - `logger.error(f"...")` -> `logger.error("...", arg1, arg2)`

## Architecture Notes

The weather-api is a well-structured Tier 2 (Essential) service with:
- **Single responsibility:** Fetches weather data from OpenWeatherMap API and writes to InfluxDB
- **Cache layer:** In-memory cache with configurable TTL (default 15 min) and thundering-herd protection via `asyncio.Lock`
- **InfluxDB fallback:** Multi-hostname fallback logic with configurable `INFLUXDB_FALLBACK_HOSTS` for DNS resolution resilience
- **Retry logic:** Configurable retry count with exponential backoff for InfluxDB writes, with DNS-aware reconnection
- **Auth flexibility:** Supports both header-based (`X-API-Key`) and query-parameter (`appid`) authentication modes with security warning for query mode
- **Health checks:** Comprehensive `/health` endpoint with component-level status tracking (API, weather client, cache, InfluxDB, background task)
- **Background fetch:** Continuous fetch loop with consecutive failure tracking and capped exponential backoff (max 30 min)
- **Input validation:** Location string validated against regex to prevent injection
- **Metrics:** Dedicated `/metrics` and `/cache/stats` endpoints for observability
