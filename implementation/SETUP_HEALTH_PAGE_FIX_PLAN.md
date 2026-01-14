# Setup & Health Page Fix Plan

**Date:** January 18, 2026  
**Status:** Planning  
**Priority:** High

## Problem Summary

The Setup & Health page (`localhost:3000/#setup`) is displaying incorrect or missing data:

1. **Overall Health Score: 0/100** (should show partial credit even with errors)
2. **Home Assistant Core: Version unknown** (should detect HA version)
3. **Integrations: (0)** (should show at least MQTT and Data API)
4. **Response Time: 0.0ms** (should show actual performance metrics)

## Root Cause Analysis

### Issue 1: Health Score Showing 0/100

**Expected Behavior:**
- Scoring algorithm should give partial credit:
  - HA Core "error/unknown": 25 points (35% weight = 8.75)
  - Empty integrations: 30 points (35% weight = 10.5)
  - 0ms response time: 80 points (15% weight = 12)
  - Reliability (default): 100 points (15% weight = 15)
  - **Minimum expected score: ~46/100**

**Possible Causes:**
1. API endpoint returning error (503/500)
2. Health service not initialized (`health_services.get("monitor")` returns None)
3. Scoring algorithm receiving None/null values instead of dicts
4. Frontend defaulting to 0 when API fails

**Files to Check:**
- `services/ha-setup-service/src/main.py` (line 180-189) - Health service initialization
- `services/ha-setup-service/src/health_service.py` (line 90-94) - Score calculation
- `services/ha-setup-service/src/scoring_algorithm.py` (line 59-101) - Score algorithm
- `services/health-dashboard/src/hooks/useEnvironmentHealth.ts` (line 86) - Frontend default

### Issue 2: HA Core Version Unknown

**Expected Behavior:**
- Should call `/api/config` endpoint with HA token
- Extract version from response: `data.get("version", "unknown")`
- Return version even if status is "warning" or "error"

**Possible Causes:**
1. HA_TOKEN not configured in environment
2. HA URL not accessible (network issue)
3. Authentication failure (401)
4. Timeout (10 second timeout)
5. API endpoint returning error

**Files to Check:**
- `services/ha-setup-service/src/health_service.py` (line 178-239) - `_check_ha_core_direct()`
- `services/ha-setup-service/src/config.py` - HA_URL and HA_TOKEN configuration
- Environment variables: `HA_TOKEN`, `HOME_ASSISTANT_TOKEN`, `HA_URL`

### Issue 3: Integrations Showing 0

**Expected Behavior:**
- Should always return at least 2 integrations:
  - MQTT (from `_check_mqtt_integration()`)
  - Data API (from `_check_data_api()`)

**Possible Causes:**
1. `_check_integrations()` returning empty list
2. Exception in integration checks causing empty result
3. Normalization failing (line 114-154 in health_service.py)
4. API response not including integrations array

**Files to Check:**
- `services/ha-setup-service/src/health_service.py` (line 241-255) - `_check_integrations()`
- `services/ha-setup-service/src/health_service.py` (line 257-316) - `_check_mqtt_integration()`
- `services/ha-setup-service/src/health_service.py` (line 354-390) - `_check_data_api()`

### Issue 4: Response Time 0.0ms

**Expected Behavior:**
- `_check_performance()` returns hardcoded values:
  ```python
  {
      "response_time_ms": 45.2,
      "cpu_usage_percent": 12.5,
      "memory_usage_mb": 256.0,
      "uptime_seconds": 86400
  }
  ```

**Possible Causes:**
1. Performance dict not being passed to scoring algorithm correctly
2. PerformanceMetrics schema validation failing
3. Frontend not reading `performance.response_time_ms` correctly

**Files to Check:**
- `services/ha-setup-service/src/health_service.py` (line 392-400) - `_check_performance()`
- `services/ha-setup-service/src/health_service.py` (line 162) - PerformanceMetrics creation
- `services/health-dashboard/src/components/EnvironmentHealthCard.tsx` (line 250) - Frontend display

## Diagnostic Steps

### Step 1: Test API Endpoint Directly

```powershell
# Test the health endpoint
$response = Invoke-RestMethod -Uri "http://localhost:8020/api/health/environment"
$response | ConvertTo-Json -Depth 10

# Check for errors
$response.health_score
$response.ha_version
$response.integrations.Count
$response.performance.response_time_ms
```

**Expected Output:**
```json
{
  "health_score": 46,
  "ha_status": "warning",
  "ha_version": "unknown",
  "integrations": [
    {
      "name": "MQTT",
      "status": "error",
      ...
    },
    {
      "name": "Data API",
      "status": "error",
      ...
    }
  ],
  "performance": {
    "response_time_ms": 45.2,
    ...
  }
}
```

### Step 2: Check Service Logs

```powershell
# Check ha-setup-service logs
docker logs ha-setup-service --tail 100

# Look for:
# - "HealthMonitoringService initialized"
# - "HA core check starting"
# - "Environment health retrieved"
# - Any exceptions or errors
```

### Step 3: Verify Configuration

```powershell
# Check environment variables
docker exec ha-setup-service env | Select-String "HA_"

# Should see:
# HA_URL=http://192.168.1.86:8123
# HA_TOKEN=... (or HOME_ASSISTANT_TOKEN)
```

## Fix Plan

### Fix 1: Ensure Health Service Initialization

**File:** `services/ha-setup-service/src/main.py`

**Issue:** Health service might not be initialized before endpoint is called.

**Fix:**
1. Add startup check to ensure health service is initialized
2. Add fallback response if service not initialized
3. Improve error message in 503 response

**Code Changes:**
```python
# In main.py, ensure health service is initialized in lifespan
# Add check in get_environment_health endpoint
if not health_service:
    # Return minimal response instead of 503
    return EnvironmentHealthResponse(
        health_score=0,
        ha_status=HealthStatus.UNKNOWN,
        ha_version=None,
        integrations=[],
        performance=PerformanceMetrics(response_time_ms=0),
        issues_detected=["Health monitoring service not initialized"],
        timestamp=datetime.now()
    )
```

### Fix 2: Improve HA Core Version Detection

**File:** `services/ha-setup-service/src/health_service.py`

**Issue:** Version detection fails silently or returns "unknown" without proper error context.

**Fix:**
1. Add better logging for HA connection attempts
2. Return version from error responses when available
3. Add configuration validation on startup
4. Improve error messages

**Code Changes:**
```python
# In _check_ha_core_direct():
# 1. Log configuration status
logger.info(f"HA Configuration: URL={ha_url}, Token={'SET' if ha_token else 'MISSING'}")

# 2. Return more detailed error information
if not ha_token:
    return {
        "status": "warning",
        "version": "unknown",
        "error": "HA_TOKEN not configured. Set HA_TOKEN or HOME_ASSISTANT_TOKEN environment variable."
    }

# 3. Extract version even from error responses
if response.status != 200:
    # Try to get version from error response if available
    try:
        error_data = await response.json()
        version = error_data.get("version")
        if version:
            return {"status": "warning", "version": version, "error": f"HTTP {response.status}"}
    except:
        pass
```

### Fix 3: Ensure Integrations Always Returned

**File:** `services/ha-setup-service/src/health_service.py`

**Issue:** Integration checks might fail and return empty list.

**Fix:**
1. Ensure `_check_integrations()` always returns at least MQTT and Data API
2. Wrap each check in try-except to prevent one failure from breaking others
3. Return error status instead of omitting integration

**Code Changes:**
```python
async def _check_integrations(self) -> list[dict]:
    """Check all integrations status - always returns at least MQTT and Data API"""
    integrations = []

    # Check MQTT integration (always include, even if check fails)
    try:
        mqtt_status = await self._check_mqtt_integration()
        integrations.append(mqtt_status)
    except Exception as e:
        logger.error(f"MQTT check failed: {e}", exc_info=True)
        integrations.append({
            "name": "MQTT",
            "type": "mqtt",
            "status": IntegrationStatus.ERROR.value,
            "is_configured": False,
            "is_connected": False,
            "error_message": str(e),
            "last_check": datetime.now()
        })

    # Check Data API (always include, even if check fails)
    try:
        data_api_status = await self._check_data_api()
        integrations.append(data_api_status)
    except Exception as e:
        logger.error(f"Data API check failed: {e}", exc_info=True)
        integrations.append({
            "name": "Data API",
            "type": "homeiq",
            "status": IntegrationStatus.ERROR.value,
            "is_configured": True,  # Service exists, just not reachable
            "is_connected": False,
            "error_message": str(e),
            "last_check": datetime.now()
        })

    return integrations
```

### Fix 4: Verify Performance Metrics Returned

**File:** `services/ha-setup-service/src/health_service.py`

**Issue:** Performance metrics might not be properly serialized.

**Fix:**
1. Ensure `_check_performance()` always returns valid dict
2. Verify PerformanceMetrics schema accepts the data
3. Add logging to track performance data flow

**Code Changes:**
```python
async def _check_performance(self) -> dict:
    """Check system performance metrics"""
    try:
        # For now, return hardcoded values (will be enhanced in Epic 30)
        performance = {
            "response_time_ms": 45.2,
            "cpu_usage_percent": 12.5,
            "memory_usage_mb": 256.0,
            "uptime_seconds": 86400
        }
        logger.debug(f"Performance metrics: {performance}")
        return performance
    except Exception as e:
        logger.error(f"Performance check failed: {e}", exc_info=True)
        # Return minimal valid performance data
        return {
            "response_time_ms": 0.0,
            "cpu_usage_percent": None,
            "memory_usage_mb": None,
            "uptime_seconds": None
        }
```

### Fix 5: Improve Frontend Error Handling

**File:** `services/health-dashboard/src/hooks/useEnvironmentHealth.ts`

**Issue:** Frontend might default to 0 when API fails.

**Fix:**
1. Better error messages for API failures
2. Show last known health data if available
3. Add retry logic with exponential backoff

**Code Changes:**
```typescript
// In useEnvironmentHealth.ts:
// 1. Don't reset health to null on error if we have cached data
if (error && health) {
  // Keep showing last known health data
  setError(errorMessage);
  setLoading(false);
  return; // Don't clear health data
}

// 2. Add better error context
if (response.status === 503) {
  errorMessage = 'The setup service is not available. Health monitoring may not be initialized yet.';
}
```

### Fix 6: Add Comprehensive Logging

**Files:** Multiple

**Issue:** Insufficient logging makes debugging difficult.

**Fix:**
1. Add structured logging at key points
2. Log health score calculation breakdown
3. Log API response structure

**Code Changes:**
```python
# In health_service.py check_environment_health():
logger.info(
    "Health check completed",
    extra={
        "health_score": health_score,
        "component_scores": component_scores,
        "ha_status": ha_status.get("status"),
        "ha_version": ha_status.get("version"),
        "integration_count": len(integrations),
        "performance": performance,
        "issues_count": len(issues)
    }
)
```

## Testing Plan

### Test 1: API Endpoint Direct Test
- [ ] Call `/api/health/environment` directly
- [ ] Verify response structure matches schema
- [ ] Verify health_score is calculated (not 0)
- [ ] Verify integrations array has at least 2 items
- [ ] Verify performance metrics are present

### Test 2: HA Connection Test
- [ ] With HA_TOKEN configured: Verify version is detected
- [ ] Without HA_TOKEN: Verify graceful error with helpful message
- [ ] With invalid HA_TOKEN: Verify warning status with error message
- [ ] With HA unreachable: Verify timeout handling

### Test 3: Integration Checks
- [ ] Verify MQTT integration always appears (even if error)
- [ ] Verify Data API integration always appears (even if error)
- [ ] Verify error messages are descriptive

### Test 4: Frontend Display
- [ ] Verify health score displays correctly (not 0)
- [ ] Verify HA version displays (or "Version unknown" with reason)
- [ ] Verify integrations list shows items
- [ ] Verify performance metrics display
- [ ] Verify error messages are user-friendly

### Test 5: Edge Cases
- [ ] Service not initialized: Verify graceful handling
- [ ] All checks fail: Verify partial health score (not 0)
- [ ] Network timeout: Verify error handling
- [ ] Invalid response: Verify schema validation

## Implementation Order

1. **Fix 1: Health Service Initialization** (Critical - prevents 503 errors)
2. **Fix 3: Ensure Integrations Always Returned** (Critical - fixes 0 integrations)
3. **Fix 4: Verify Performance Metrics** (Critical - fixes 0.0ms)
4. **Fix 2: Improve HA Core Detection** (Important - fixes version unknown)
5. **Fix 6: Add Comprehensive Logging** (Important - improves debugging)
6. **Fix 5: Improve Frontend Error Handling** (Nice to have - better UX)

## Success Criteria

✅ Health score shows meaningful value (≥25) even with errors  
✅ HA version displays or shows helpful error message  
✅ Integrations list shows at least 2 items (MQTT, Data API)  
✅ Performance metrics display actual values (not 0.0ms)  
✅ Error messages are user-friendly and actionable  
✅ Logs provide sufficient debugging information  

## Related Files

- `services/ha-setup-service/src/main.py` - API endpoint
- `services/ha-setup-service/src/health_service.py` - Health monitoring logic
- `services/ha-setup-service/src/scoring_algorithm.py` - Score calculation
- `services/ha-setup-service/src/config.py` - Configuration
- `services/health-dashboard/src/hooks/useEnvironmentHealth.ts` - Frontend hook
- `services/health-dashboard/src/components/EnvironmentHealthCard.tsx` - UI component
- `services/health-dashboard/nginx.conf` - Proxy configuration

## Notes

- Health scoring algorithm already implements graceful degradation (returns 25 for HA error, 30 for empty integrations, 80 for 0ms response time)
- The issue is likely that the API is failing before reaching the scoring algorithm
- Need to verify health service is initialized in `main.py` lifespan
- Consider adding health check endpoint that doesn't require database (for startup checks)
