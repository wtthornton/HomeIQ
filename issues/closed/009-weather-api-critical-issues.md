---
status: Closed
priority: Critical
service: weather-api
created: 2025-11-15
closed: 2025-11-15
labels: [critical, performance, reliability]
---

# [CRITICAL] Weather API Service - Blocking I/O and Silent Failures

**Use 2025 patterns, architecture and versions for decisions and ensure the Readme files are up to date.**

## Overview
The weather-api service has **6 issues** including blocking synchronous I/O in async context, unguarded background tasks, and false health checks that violate CLAUDE.md performance patterns.

---

## CRITICAL Issues

### 1. **Blocking Synchronous InfluxDB Write in Async Context**
**Location:** `main.py:187`
**Severity:** CRITICAL

**Issue:** The InfluxDB client's `write()` method is **synchronous** but is being called in an async function.

```python
self.influxdb_client.write(point)  # Line 187 - BLOCKING!
```

**Impact:**
- **Blocks entire event loop** - prevents other requests from being processed
- Performance degradation - service stalls during writes
- Violates async best practices from CLAUDE.md
- Can cause cascading timeouts in dependent services
- This happens every 15 minutes (900-second cache TTL)

**Fix:** Use async InfluxDB writes or run in thread executor:
```python
loop = asyncio.get_event_loop()
await loop.run_in_executor(None, self.influxdb_client.write, point)
```

---

### 2. **Unguarded Background Task with No Error Recovery**
**Location:** `main.py:216`
**Severity:** CRITICAL

**Issue:** Background task created without reference, exception handling, or monitoring.

```python
asyncio.create_task(weather_service.run_continuous())  # No reference stored, no exception handling
```

**Problems:**
1. No task reference stored (task can be garbage collected)
2. No exception handling wrapper
3. No monitoring or recovery mechanism

**Impact:**
- If `run_continuous()` raises unhandled exception, it **silently dies**
- No weather data collection occurs after failure
- No alerts or logs about task failure
- Service appears healthy but core functionality is broken

**Fix:** Store task reference and add exception handler:
```python
async def _run_with_exception_handling():
    try:
        await weather_service.run_continuous()
    except Exception as e:
        logger.exception("Background task failed")
        # Implement retry or alert mechanism

background_task = asyncio.create_task(_run_with_exception_handling())
```

---

### 3. **Missing Null Checks for Client Objects**
**Location:** `main.py:121, 187`
**Severity:** CRITICAL

**Issue:** No validation that client objects are initialized before use.

```python
async with self.session.get(url, params=params) as response:  # Line 121
    # No check if self.session is None

self.influxdb_client.write(point)  # Line 187
    # No check if self.influxdb_client is None
```

**Impact:**
- Service crashes during startup race conditions
- `AttributeError: 'NoneType' object has no attribute 'get'`
- No graceful degradation

**Fix:** Add null checks:
```python
if not self.session:
    raise RuntimeError("HTTP session not initialized")

if not self.influxdb_client:
    logger.warning("InfluxDB client not initialized, skipping write")
    return
```

---

## HIGH Severity Issues

### 4. **Health Check Reports False Status**
**Location:** `health_check.py:40-44`
**Severity:** HIGH

**Issue:** Health check **always returns hardcoded values** and never actually checks system state.

```python
"components": {
    "api": "healthy",
    "weather_client": "not_initialized",  # Always hardcoded!
    "cache": "not_initialized",           # Always hardcoded!
    "influxdb": "not_initialized"         # Always hardcoded!
}
```

**Impact:**
- Monitoring systems think service is healthy when it's broken
- No early warning of failures
- Violates health check best practices from CLAUDE.md
- Docker health check always passes even when service is non-functional

**Fix:** Implement actual health checks:
```python
"components": {
    "api": "healthy",
    "weather_client": "healthy" if weather_service.session else "not_initialized",
    "cache": "healthy" if weather_service.cache else "not_initialized",
    "influxdb": "healthy" if weather_service.influxdb_client else "not_initialized",
    "background_task": "running" if background_task and not background_task.done() else "stopped"
}
```

---

## MODERATE Severity Issues

### 5. **No Retry Logic for InfluxDB Writes**
**Location:** `main.py:190-191`
**Severity:** MODERATE

**Issue:** Data lost on transient network failures.

```python
except Exception as e:
    logger.error(f"Error writing to InfluxDB: {e}")
    # Data is lost - no retry, no queue
```

**Impact:**
- Permanent data loss on transient failures
- No circuit breaker pattern (mentioned in CLAUDE.md for websocket-ingestion)
- Violates performance patterns from CLAUDE.md

**Fix:** Implement retry logic with exponential backoff:
```python
for attempt in range(3):
    try:
        await loop.run_in_executor(None, self.influxdb_client.write, point)
        break
    except Exception as e:
        if attempt == 2:
            logger.error(f"Failed to write after 3 attempts: {e}")
        else:
            await asyncio.sleep(2 ** attempt)
```

---

### 6. **API Key Exposed in URL Parameters**
**Location:** `main.py:117`
**Severity:** MODERATE

**Issue:** API key in URL params may appear in logs.

```python
params = {
    "q": self.location,
    "appid": self.api_key,  # API key in URL params
    "units": "metric"
}
```

**Impact:**
- API keys in URLs may appear in access logs, proxy logs, browser history
- Security risk if logs are compromised

**Fix:** Use HTTP headers for authentication (if supported by API), or accept this as OpenWeatherMap's design.

---

## Resolution Summary

- Added guarded background task orchestration with explicit cancellation handling and surfaced task health via `/health` and `/metrics`.
- Converted blocking InfluxDB writes to `asyncio.to_thread` with 3-attempt exponential backoff retries and added null checks before use.
- Hardened OpenWeatherMap client with session validation plus configurable `WEATHER_API_AUTH_MODE` (header default) to keep API keys out of URLs.
- Upgraded health reporting to 2025 format with component states, cache metrics, and background task visibility; `/metrics` now mirrors the JSON payload.
- Updated documentation (service README) to describe the new auth mode, retries, and health output; bumped service version to 2.2.0.
- Tests adjusted to reflect new interfaces; suite currently skips when `influxdb_client_3` wheel is unavailable.

All six tracked issues are remediated following 2025 architecture patterns for the single-home deployment.
