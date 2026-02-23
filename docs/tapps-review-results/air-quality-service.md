# TAPPS Code Quality Review: air-quality-service

**Service Tier:** Tier 4 (Enhanced Data Sources)
**Review Date:** 2026-02-22
**Preset:** standard (gate threshold: 70.0)
**Reviewer:** Claude Code (tapps-mcp)

## Summary

| Metric | Value |
|--------|-------|
| Files Reviewed | 3 |
| Initial Failures | 0 |
| Issues Found | 5 (4 lint + 1 security) |
| Issues Fixed | 5 |
| **Final Status** | **ALL PASS (100.0)** |

## Files Reviewed

### 1. `src/__init__.py`
- **Score:** 100.0 (before) -> 100.0 (after)
- **Gate:** PASS
- **Issues:** None

### 2. `src/health_check.py`
- **Score:** 95.0 (before) -> 100.0 (after)
- **Gate:** PASS
- **Issues Found (1):**
  - `ARG002` (line 24): Unused method argument `request` in `handle()`
- **Fix:** Renamed to `_request` (required by aiohttp handler signature but not used in implementation)

### 3. `src/main.py`
- **Score:** 85.0 (before) -> 100.0 (after)
- **Gate:** PASS
- **Issues Found (4):**
  - `I001` (line 6): Import block is un-sorted or un-formatted — `from health_check` was in wrong position relative to third-party imports
  - `B904` (line 103): Missing `raise ... from err` in except clause within `_validate_coordinate()`
  - `ARG002` (line 337): Unused method argument `request` in `get_current_aqi()`
  - `B104` (line 423): Possible binding to all interfaces `0.0.0.0` (security — medium severity)
- **Fixes:**
  - Reordered imports: moved `from health_check import HealthCheckHandler` into alphabetical position within the third-party block (between `dotenv` and `influxdb_client_3`)
  - Added `from err` to `raise ValueError(...)` in `_validate_coordinate()` to properly chain exceptions per B904
  - Renamed `request` to `_request` in `get_current_aqi()` (required by aiohttp route signature but not used)
  - Made bind address configurable via `SERVICE_HOST` env var (defaults to `0.0.0.0` for Docker) with `# noqa: S104  # nosec B104` suppression

## Architecture Notes

The air-quality-service is a well-structured Tier 4 service with:
- **Single responsibility:** Fetches AQI data from OpenWeather API and writes to InfluxDB
- **Retry logic:** 3-attempt retry with configurable exponential backoff delays (30s, 120s, 300s)
- **Rate limiting:** Sliding-window rate limiter on `/current-aqi` endpoint (60 req/min)
- **Cache layer:** In-memory cache with configurable duration to reduce API calls
- **Health checks:** Comprehensive `/health` endpoint tracking uptime, fetch stats, and component connectivity
- **Security:** API key redaction filter on all log output
- **HA integration:** Optional automatic location detection from Home Assistant config API
- **Async-safe InfluxDB writes:** Uses `asyncio.to_thread()` to avoid blocking the event loop with synchronous `InfluxDBClient3.write()`
