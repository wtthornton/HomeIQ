# Health Score Analysis - Why Score is 0/100

**Date:** 2025-01-XX  
**Issue:** Health score showing 0/100 (or 1/100) in Setup & Health dashboard  
**Status:** Root cause identified

## Problem Summary

The health score in the Setup & Health dashboard is showing 0/100 when it should be at least 15-30 points based on the scoring algorithm.

## Root Cause Analysis

### Health Score Calculation

The health score is calculated using a weighted algorithm with 4 components:

1. **HA Core Status** (35% weight)
   - Healthy: 100 points → 35 points
   - Warning: 50 points → 17.5 points
   - Error/Unknown: 0 points → 0 points

2. **Integrations** (35% weight)
   - Each integration scored individually
   - Healthy: 100 points, Warning: 50 points, Error: 0 points
   - Average across all integrations
   - If no integrations: 0 points → 0 points

3. **Performance** (15% weight)
   - Based on `response_time_ms`:
     - < 100ms: 100 points → 15 points
     - < 250ms: 80 points → 12 points
     - < 500ms: 60 points → 9 points
     - < 1000ms: 30 points → 4.5 points
     - >= 1000ms: 0 points → 0 points

4. **Reliability** (15% weight)
   - Defaults to 100 points if no data → 15 points
   - Based on uptime and error rates if data provided

### Expected Minimum Score

Even if HA Core and Integrations both fail (0 points each), the minimum score should be:
- Performance: 15 points (0ms response time scores 100 × 0.15 = 15)
- Reliability: 15 points (default 100 × 0.15 = 15)
- **Total: 30 points**

### Actual Issue

The score is showing 0/100, which suggests:

1. **HA Core Check is Failing** ✅ Confirmed
   - Status: "error" or "unknown"
   - Version: "unknown"
   - This gives 0 points (35% weight = 0)

2. **Integrations Check is Empty or Failing** ✅ Confirmed
   - UI shows "Integrations (0)"
   - This gives 0 points (35% weight = 0)

3. **Performance Check Issue** ⚠️ Suspected
   - UI shows "Response Time: 0.0ms"
   - If `response_time_ms` is 0, it should score 100 points (15% weight = 15)
   - **Possible issue**: Performance check might be failing and returning malformed data

4. **Reliability Check Issue** ⚠️ Suspected
   - Should default to 100 points (15% weight = 15)
   - **Possible issue**: Reliability data might be provided with `uptime_seconds: 0`, causing it to score 0

### Key Finding

Looking at the code in `health_service.py` line 76-81:

```python
performance = performance_check if not isinstance(performance_check, Exception) else {
    "response_time_ms": 0,
    "cpu_usage_percent": 0,
    "memory_usage_mb": 0,
    "uptime_seconds": 0
}
```

The fallback performance dict includes `uptime_seconds: 0`, but this is for **performance**, not **reliability**. However, if the performance check fails and this fallback is used, the `uptime_seconds: 0` might be incorrectly used for reliability scoring.

**However**, the reliability scoring is separate and should default to 100 if no `reliability_data` is provided (line 95 in `scoring_algorithm.py`).

## Most Likely Root Cause

The most likely issue is that **the performance check is failing** and returning an exception, which causes the fallback dict to be used. However, even with the fallback, the score should be at least 15 points.

**Alternative theory**: The `_check_performance()` method might be returning a dict with `response_time_ms` >= 1000, which would score 0 points. But the placeholder implementation returns `45.2ms`, which should score 100 points.

## Recommendations

1. **Check HA Core Connection**
   - Verify Home Assistant is accessible at the configured URL
   - Verify the HA token is valid
   - Check network connectivity

2. **Check Integrations**
   - Verify integrations are being detected
   - Check if integration checks are failing silently

3. **Debug Performance Check**
   - Add logging to see what `_check_performance()` is actually returning
   - Verify the performance dict structure matches expectations

4. **Add Debug Logging**
   - Log component scores before calculating total
   - Log the actual values being used in the calculation
   - This will help identify which component is causing the 0 score

5. **Fix Minimum Score Logic**
   - Ensure that even with all failures, the score reflects partial functionality
   - Consider giving partial credit for services that are partially working

## Root Cause Identified ✅

**The API endpoint is returning the wrong response!**

When accessing `/setup-service/api/health/environment` through the nginx proxy, it's returning the service info endpoint (`/`) instead of the health endpoint (`/api/health/environment`).

### Evidence:
1. **Backend logs show correct score**: `✅ Health check complete - Score: 88/100`
2. **API response is wrong**: Returns service info JSON instead of health data
3. **Frontend defaults to 0**: Since `health_score` is missing, it defaults to 0

### Nginx Proxy Issue

The nginx configuration at `services/health-dashboard/nginx.conf:288-295`:

```nginx
location /setup-service/ {
    set $setup "http://ha-setup-service:8020";
    proxy_pass $setup/;
    ...
}
```

The `proxy_pass $setup/;` with trailing slash should strip `/setup-service/` and proxy the rest, but it appears to be routing incorrectly.

## Resolution ✅

**Fixed:** The nginx proxy configuration has been corrected.

### Solution Applied

Changed the nginx configuration from using variables in `proxy_pass` to using a direct server address with trailing slash:

**Before:**
```nginx
location /setup-service/ {
    set $setup "http://ha-setup-service:8020";
    proxy_pass $setup/;
    ...
}
```

**After:**
```nginx
location /setup-service/ {
    proxy_pass http://ha-setup-service:8020/;
    ...
}
```

The trailing slash in `proxy_pass` automatically strips the `/setup-service/` prefix, so `/setup-service/api/health/environment` correctly proxies to `http://ha-setup-service:8020/api/health/environment`.

### Verification

- ✅ Health score now displays correctly: **88/100** (was showing 0/100)
- ✅ HA Status: warning
- ✅ Integrations: 3 (MQTT healthy, Zigbee2MQTT not configured, Data API healthy)
- ✅ Performance metrics displaying correctly
- ✅ Container rebuilt with fix

### Files Changed

- `services/health-dashboard/nginx.conf` - Fixed proxy_pass configuration
- Container rebuilt to include the fix permanently

## Files to Review

- `services/ha-setup-service/src/health_service.py` - Health check logic
- `services/ha-setup-service/src/scoring_algorithm.py` - Scoring calculation
- `services/ha-setup-service/src/main.py` - API endpoint
- `services/health-dashboard/src/hooks/useEnvironmentHealth.ts` - Frontend hook

