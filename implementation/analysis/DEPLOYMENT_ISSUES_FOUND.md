# Deployment Issues Found

**Date:** November 25, 2025  
**Status:** ⚠️ Issues Identified

---

## Issues Discovered

### 1. ✅ Service Status: HEALTHY
- `ai-automation-service` is running and healthy
- Port: 8024 (mapped from 8018)
- Status: Up 2 hours (healthy)

### 2. ⚠️ V2 API Import Error
**Error:**
```json
"v2_api":{"status":"error","error":"attempted relative import beyond top-level package"}
```

**Impact:** V2 API endpoints may not be working

**Location:** Health endpoint shows this error

### 3. ⚠️ Home Type Endpoint: 401 Unauthorized
**Error:**
```
GET /api/home-type/classify?home_id=default HTTP/1.1" 401 Unauthorized
Failed to get home type: HTTP 401
```

**Impact:** 
- Home type classification endpoint requires authentication
- `HomeTypeClient` calls are failing
- Falls back to default home type (working, but not ideal)

**Root Cause:** Endpoint likely requires API key authentication

### 4. ⚠️ SQL Expression Error
**Error:**
```
Failed to determine automation style: SQL expression element expected, got MetaData().
```

**Impact:** Automation style detection failing

**Location:** Likely in database query code

---

## Next Steps to Fix

### Priority 1: Fix Home Type Endpoint Authentication
- Check if endpoint requires API key
- Update `HomeTypeClient` to include API key in requests
- Or make endpoint public (if appropriate)

### Priority 2: Fix V2 API Import Error
- Find v2_api code
- Fix relative import issue
- Verify v2 endpoints work

### Priority 3: Fix SQL Expression Error
- Find automation style code
- Fix SQL query/MetaData issue
- Verify automation style detection works

---

## Current Workaround

**Home Type Integration:**
- ✅ Falls back to 'standard_home' when endpoint fails
- ✅ All features work with default home type
- ⚠️ Not using actual classified home type (until endpoint fixed)

**Service Health:**
- ✅ Service is healthy and running
- ✅ Core functionality works
- ⚠️ Some features degraded (home type, automation style)

---

**Status:** Service operational but with some feature degradation

