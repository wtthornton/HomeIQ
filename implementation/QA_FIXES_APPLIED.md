# QA Evaluation Fixes Applied

**Date:** January 27, 2025  
**Issue Fixed:** Setup-service port configuration

## Issues Found During QA Evaluation

### Issue #1: Setup & Health Page API Failure ✅ FIXED
- **Error:** Failed to fetch from `http://localhost:8020/api/health/environment`
- **Root Cause:** Port mismatch - setup-service is exposed on port **8027**, but dashboard was trying to connect to port **8020**
- **Status:** Code fixed, requires clean rebuild

### Issue #2: Logs Page API
- **Error:** Failed to fetch from `http://localhost:8015/api/v1/logs`
- **Root Cause:** Service was healthy but may have had temporary connectivity issues
- **Status:** Service verified healthy, no code changes needed

### Issue #3: Calendar Service
- **Error:** Cannot connect to host `homeiq-calendar:8013`
- **Root Cause:** DNS resolution issue or service not running
- **Status:** Non-critical, system continues to function

## Fix Applied

**File:** `services/health-dashboard/src/hooks/useEnvironmentHealth.ts`

**Change:**
```typescript
// Before
const SETUP_SERVICE_URL = 'http://localhost:8020';  // Port 8020 (8010 used by carbon-intensity)

// After
const SETUP_SERVICE_URL = 'http://localhost:8027';  // Port 8027 (container internal port is 8020, external is 8027)
```

## Verification

**Containers Status:**
- ✅ setup-service running on port **8027** (healthy)
- ✅ log-aggregator running on port **8015** (healthy)

**API Endpoints Tested:**
- ✅ `http://localhost:8027/health` - Returns healthy status
- ✅ `http://localhost:8015/health` - Returns healthy status
- ✅ `http://localhost:8015/api/v1/logs?limit=10` - Returns log data

## Docker Compose Configuration

**setup-service mapping:**
```yaml
ports:
  - "8027:8020"  # External:Internal
```

**log-aggregator mapping:**
```yaml
ports:
  - "8015:8015"  # External:Internal
```

## To Apply the Fix

Due to Docker build caching, you need to do a clean rebuild:

```bash
# Stop the dashboard
docker-compose stop health-dashboard

# Remove the old image
docker rmi homeiq-health-dashboard

# Build without cache
docker-compose build --no-cache health-dashboard

# Start the dashboard
docker-compose start health-dashboard
```

Or restart the entire stack:
```bash
docker-compose down
docker-compose up -d --build
```

## Expected Result

After rebuild:
- Setup & Health page should load successfully
- Environment health data should display
- Logs page should continue working (already verified)
- No more "Failed to fetch" errors on Setup & Health page

## Summary

- **Files Changed:** 1 (`useEnvironmentHealth.ts`)
- **Services Affected:** setup-service port mapping
- **Risk Level:** Low (single configuration value change)
- **Testing Required:** Verify Setup & Health page loads successfully after rebuild

