# QA Critical Fixes - Implementation Plan

**Date:** January 27, 2025  
**Status:** Ready for Implementation

## Summary

During comprehensive QA evaluation of the web application, two critical issues were identified:
1. ✅ **Setup & Health Page** - Port configuration fixed, requires rebuild
2. ❌ **Logs Page** - CORS configuration missing, requires code fix

---

## Issue #1: Setup & Health Page - ✅ CODE FIXED

### Problem
- **Error:** Failed to fetch from `http://localhost:8020/api/health/environment`
- **Root Cause:** Port mismatch - setup-service container is mapped to port 8027 externally, but dashboard was configured to use port 8020

### Fix Applied
**File:** `services/health-dashboard/src/hooks/useEnvironmentHealth.ts`  
**Change:** Updated SETUP_SERVICE_URL from `http://localhost:8020` to `http://localhost:8027`

```typescript
// Before
const SETUP_SERVICE_URL = 'http://localhost:8020';  // Port 8020

// After
const SETUP_SERVICE_URL = 'http://localhost:8027';  // Port 8027 (container internal port is 8020, external is 8027)
```

### Verification
- ✅ Service is healthy on port 8027
- ✅ Code change applied and committed
- ⚠️ Dashboard needs clean rebuild to apply changes

### Implementation Steps Required

```bash
# 1. Stop current dashboard
docker-compose stop health-dashboard

# 2. Clean rebuild (no cache)
docker-compose build --no-cache health-dashboard

# 3. Start dashboard
docker-compose up -d health-dashboard

# 4. Wait for container to be healthy
docker ps --filter name=dashboard

# 5. Test Setup & Health page
curl http://localhost:3000/setup-health
```

---

## Issue #2: Logs Page - ❌ REQUIRES CODE FIX

### Problem
- **Error:** `ERR_FAILED` when fetching from `http://localhost:8015/api/v1/logs?limit=100`
- **Console Error:** `Access to fetch at 'http://localhost:8015/api/v1/logs' from origin 'http://localhost:3000'`
- **Root Cause:** log-aggregator service has **NO CORS configuration**, blocking browser requests

### Current Status
- ✅ Service is running and healthy on port 8015
- ✅ Service responds to direct requests (PowerShell/curl)
- ❌ Browser requests are blocked by CORS policy
- ❌ No CORS headers in log-aggregator code

### Required Fix

**File:** `services/log-aggregator/src/main.py` (or wherever Flask app is configured)

**Add CORS middleware to allow browser requests:**

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:3001"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
```

### Verification Steps

1. **Check current code:**
   ```bash
   grep -r "CORS\|cors" services/log-aggregator/
   ```

2. **Add CORS support** (if not present)

3. **Update requirements.txt** (if flask-cors not installed):
   ```
   flask-cors>=4.0.0
   ```

4. **Rebuild log-aggregator:**
   ```bash
   docker-compose build --no-cache log-aggregator
   docker-compose restart log-aggregator
   ```

5. **Test from browser:**
   - Navigate to http://localhost:3000/logs
   - Check browser console for CORS errors
   - Verify logs are displayed

---

## Testing Plan

### Pre-Implementation
- [x] Verify setup-service is healthy on port 8027
- [x] Verify log-aggregator is healthy on port 8015
- [x] Confirm port mismatch in dashboard code
- [x] Confirm CORS missing in log-aggregator

### Implementation
- [x] Fix dashboard port configuration
- [ ] Rebuild dashboard with fix
- [ ] Test Setup & Health page
- [ ] Add CORS to log-aggregator
- [ ] Rebuild log-aggregator
- [ ] Test Logs page

### Post-Implementation
- [ ] Verify both pages work correctly
- [ ] Test all interactive elements
- [ ] Verify no console errors
- [ ] Update QA evaluation report
- [ ] Document changes in CHANGELOG

---

## Additional Findings

### Non-Critical Issues
1. **Calendar Service** - DNS resolution error (`homeiq-calendar:8013`)
   - System continues to function
   - Error is shown but doesn't block functionality
   - Low priority fix

---

## Implementation Priority

**Immediate (Critical):**
1. ✅ Fix dashboard port configuration (DONE)
2. 🔲 Rebuild dashboard to apply fix
3. 🔲 Add CORS to log-aggregator
4. 🔲 Test both pages

**Short-term (Important):**
- Fix calendar service connectivity
- Add retry mechanisms for failed API calls
- Improve error messages

**Long-term (Enhancements):**
- Add comprehensive E2E tests
- Implement health check monitoring
- Add performance metrics
- Enhance accessibility

---

## Files Modified

1. ✅ `services/health-dashboard/src/hooks/useEnvironmentHealth.ts` - Port fix
2. 🔲 `services/log-aggregator/src/main.py` - CORS configuration (TODO)
3. 🔲 `services/log-aggregator/requirements.txt` - Add flask-cors (TODO)

---

## Notes

- Docker build cache was preventing TypeScript changes from being applied
- Clean rebuild required: `docker-compose build --no-cache`
- Browser cache may need to be cleared after dashboard rebuild
- CORS is required for all backend services that frontend consumes directly

---

## References

- Original QA Evaluation: `implementation/qa-web-application-evaluation.md`
- Previous Fix Attempts: `implementation/QA_FIXES_APPLIED.md`
- Docker Compose Config: `docker-compose.yml`

