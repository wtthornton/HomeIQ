# Docker Deployment Issues - Review Results

**Date:** November 24, 2025  
**Status:** ⚠️ Issues Found

## Critical Issues

### 1. ❌ ModuleNotFoundError: No module named 'src.services.config'

**Location:** `services/ai-automation-service/src/services/entity/extractor.py`

**Error:**
```
ModuleNotFoundError: No module named 'src.services.config'
File "/app/src/services/entity/extractor.py", line 20, in <module>
    from ..config import settings
```

**Impact:** Entity extraction service is failing to initialize, which affects automation suggestions.

**Root Cause:** The import path is incorrect. Should be using relative imports within the `services` package.

**Fix Needed:** Update the import in `extractor.py` to use correct relative path:
```python
# Current (incorrect):
from ..config import settings

# Should be:
from ...config import settings
# OR
from src.services.config import settings  # If absolute import is needed
```

---

### 2. ⚠️ Health Check API Error

**Location:** Health check endpoint `/health`

**Error in Health Check Response:**
```json
{
  "v2_api": {
    "status": "error",
    "error": "attempted relative import beyond top-level package"
  }
}
```

**Impact:** Health checks are passing, but the v2_api endpoint is not working correctly.

**Status:** Service is marked as healthy, but this indicates a deeper import issue.

---

### 3. ⚠️ Database Schema Warning: Missing 'source_type' Attribute

**Error Messages:**
```
Failed to determine automation style: type object 'Suggestion' has no attribute 'source_type'
```

**Occurrence:** Multiple times during startup

**Impact:** May affect suggestion filtering and categorization.

**Possible Cause:** Database migration not applied or schema mismatch between code and database.

**Fix Needed:** 
- Check if migrations need to be run
- Verify database schema matches expected model

---

## Configuration Issues

### 4. ⚠️ Empty VITE_API_URL Configuration

**Location:** `docker-compose.yml` lines 969 and 976

**Current Configuration:**
```yaml
args:
  - VITE_API_URL=
environment:
  - VITE_API_URL=
```

**Impact:** Frontend uses default API configuration from `src/config/api.ts`, which should work but explicit configuration is preferred.

**Note:** The frontend has fallback logic in `api.ts`:
- Production: `/api` (relative path, proxied by nginx)
- Development: `http://localhost:8018/api`

**Fix Needed:** Set VITE_API_URL explicitly:
```yaml
args:
  - VITE_API_URL=http://ai-automation-service:8018/api
environment:
  - VITE_API_URL=http://ai-automation-service:8018/api
```

**OR** leave empty if nginx reverse proxy handles routing (current setup seems to work).

---

### 5. ⚠️ Port Mapping Inconsistency

**Observation:** 
- `ai-automation-service` is exposed on port **8024** externally (mapped from internal 8018)
- Frontend API config expects port **8018** in development
- In production, frontend uses relative paths (`/api`) which are proxied

**Status:** ✅ **This is actually CORRECT**
- In Docker, frontend uses relative paths proxied through nginx
- External port 8024 is only for direct access from host
- Internal Docker networking uses port 8018

**No action needed** - current configuration is correct.

---

## Resource Usage

### 6. ⚠️ High Memory Usage

**Service:** `ai-automation-service`

**Current Usage:**
- Memory: `439.8MB / 512MB` (85.9%)
- CPU: `0.23%`

**Impact:** Approaching memory limit. May cause issues under load.

**Recommendation:**
- Monitor memory usage
- Consider increasing memory limit to 768M or 1GB if issues occur

---

## Service Status Summary

### ✅ Working Services
- `ai-automation-ui`: ✅ Healthy
- `ai-automation-service`: ✅ Healthy (despite errors)
- All dependencies: ✅ Healthy

### ⚠️ Services with Issues
- `ai-automation-service`: Health check passing but has:
  - ModuleNotFoundError on startup
  - Health check API errors
  - Database schema warnings

---

## Recommended Fixes (Priority Order)

### Priority 1: Fix Module Import Error
1. Fix the import in `services/ai-automation-service/src/services/entity/extractor.py`
2. Verify all relative imports in the `services` package
3. Rebuild and redeploy service

### Priority 2: Investigate Database Schema
1. Check database migrations status
2. Verify `source_type` column exists in `suggestions` table
3. Run migrations if needed

### Priority 3: Fix Health Check API Error
1. Investigate v2_api endpoint import issue
2. Fix relative import problems
3. Verify health check reports correctly

### Priority 4: Optimize Memory Usage
1. Monitor memory trends
2. Increase memory limit if needed
3. Optimize code if memory leak is suspected

---

## Next Steps

1. **Immediate:** Fix the ModuleNotFoundError in `extractor.py`
2. **Verify:** Check database schema for `source_type` column
3. **Monitor:** Watch memory usage trends
4. **Test:** Verify all functionality works after fixes

---

## Testing Checklist After Fixes

- [ ] Service starts without ModuleNotFoundError
- [ ] Health check shows no v2_api errors
- [ ] No database schema warnings
- [ ] Suggestions load correctly
- [ ] Device health integration works
- [ ] Duplicate automation detection works
- [ ] Memory usage stays below 80%

---

**Review completed by:** Automated Docker Review  
**Next review:** After fixes are applied

