# Device Suggestions - Docker Fixes

**Date:** January 16, 2026  
**Environment:** Docker (Production)  
**Status:** ✅ Fixes Applied

---

## Critical Fix Applied

### Fix 1: Nginx Proxy Path Rewrite (CRITICAL)

**File:** `services/ai-automation-ui/nginx.conf`  
**Line:** 88

**Problem:**
- Frontend requests: `/api/data/devices`
- Nginx was forwarding to: `http://data-api:8006/api/data/devices`
- But data-api expects: `http://data-api:8006/api/devices`
- Result: 404 error

**Fix Applied:**
```nginx
# BEFORE (WRONG):
proxy_pass $backend/api/data/$1;

# AFTER (CORRECT):
# Rewrite /api/data/* to /api/* (remove /data from path)
proxy_pass $backend/api/$1;
```

**What This Does:**
- Frontend request: `/api/data/devices?limit=100`
- Nginx rewrites to: `http://data-api:8006/api/devices?limit=100`
- Matches what data-api service expects

**Verification:**
After rebuilding the Docker container, test:
```powershell
# From host machine
Invoke-RestMethod -Uri "http://localhost:3001/api/data/devices?limit=10" -Headers @{Authorization="Bearer $env:API_KEY"}
```

---

## Docker Rebuild Required

### Steps to Apply Fix

1. **Rebuild the container:**
   ```powershell
   docker-compose build ai-automation-ui
   ```

2. **Restart the service:**
   ```powershell
   docker-compose up -d ai-automation-ui
   ```

3. **Verify nginx config is updated:**
   ```powershell
   docker exec ai-automation-ui cat /etc/nginx/conf.d/default.conf | Select-String -Pattern "api/data" -Context 2
   ```

4. **Test the endpoint:**
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:3001/api/data/devices?limit=5" -Headers @{Authorization="Bearer $env:API_KEY"; "X-HomeIQ-API-Key"=$env:API_KEY}
   ```

---

## Additional Docker Configuration Checks

### Verify Data-API Service is Running

```powershell
# Check if data-api is healthy
docker ps | Select-String "data-api"

# Check data-api health
Invoke-RestMethod -Uri "http://localhost:8006/health"

# Test data-api devices endpoint directly
Invoke-RestMethod -Uri "http://localhost:8006/api/devices?limit=5" -Headers @{Authorization="Bearer $env:API_KEY"; "X-HomeIQ-API-Key"=$env:API_KEY}
```

### Verify Network Connectivity

```powershell
# From inside ai-automation-ui container
docker exec ai-automation-ui ping -c 2 data-api

# Test connectivity to data-api
docker exec ai-automation-ui wget -O- http://data-api:8006/health
```

### Check Nginx Logs

```powershell
# View nginx access logs
docker logs ai-automation-ui 2>&1 | Select-String "api/data"

# View nginx error logs
docker exec ai-automation-ui tail -f /var/log/nginx/error.log
```

---

## Playwright Tests for Docker

### Update Test Configuration

**File:** `tests/e2e/ai-automation-ui/playwright.config.ts`

**Current:**
```typescript
use: {
  baseURL: 'http://localhost:3001',
  // ...
}
```

**For Docker Testing:**
```typescript
use: {
  baseURL: process.env.TEST_BASE_URL || 'http://localhost:3001',
  // ...
}
```

### Docker Test Script

**Create:** `tests/e2e/run-docker-tests.ps1`

```powershell
# Run Playwright tests against Docker container
$env:TEST_BASE_URL = "http://localhost:3001"
$env:TEST_API_KEY = $env:API_KEY

cd tests/e2e
npx playwright test ai-automation-ui/pages/device-suggestions.spec.ts --reporter=list
```

### Test Prerequisites

1. **Services must be running:**
   ```powershell
   docker-compose up -d ai-automation-ui data-api ha-ai-agent-service
   ```

2. **Wait for services to be healthy:**
   ```powershell
   docker-compose ps
   # All services should show "healthy" status
   ```

3. **Verify API is accessible:**
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:3001/api/data/devices?limit=1" -Headers @{Authorization="Bearer $env:API_KEY"}
   ```

---

## Complete Fix Checklist

### ✅ Completed

- [x] Fixed nginx proxy path rewrite (`/api/data/*` → `/api/*`)
- [x] Updated nginx.conf with correct proxy_pass
- [x] Documented Docker rebuild steps

### 🔄 Required Actions

- [ ] Rebuild Docker container: `docker-compose build ai-automation-ui`
- [ ] Restart service: `docker-compose up -d ai-automation-ui`
- [ ] Verify fix works: Test device picker in UI
- [ ] Run Playwright tests against Docker
- [ ] Update test documentation

---

## Testing the Fix

### Manual Test Steps

1. **Open browser:** `http://localhost:3001/ha-agent`

2. **Click "🔌 Select Device" button**

3. **Verify:**
   - Device picker opens
   - Devices load (no 404 error)
   - Device list displays
   - Search works
   - Filters work

4. **Select a device:**
   - Click on a device
   - Verify device context displays
   - Verify suggestions appear (if any)

### Automated Test

```powershell
# Run Playwright tests
cd tests/e2e
npx playwright test ai-automation-ui/pages/device-suggestions.spec.ts --headed
```

---

## Expected Behavior After Fix

### Before Fix:
- ❌ Device picker opens
- ❌ Error: "Failed to load devices: API Error: Not Found"
- ❌ "No devices available" message
- ❌ Cannot select devices
- ❌ Cannot generate suggestions

### After Fix:
- ✅ Device picker opens
- ✅ Devices load successfully
- ✅ Device list displays
- ✅ Search and filters work
- ✅ Device selection works
- ✅ Suggestions generate after selection

---

## Troubleshooting

### If devices still don't load:

1. **Check nginx config was updated:**
   ```powershell
   docker exec ai-automation-ui grep -A 5 "api/data" /etc/nginx/conf.d/default.conf
   ```
   Should show: `proxy_pass $backend/api/$1;`

2. **Check data-api is accessible:**
   ```powershell
   docker exec ai-automation-ui wget -O- http://data-api:8006/health
   ```

3. **Check nginx error logs:**
   ```powershell
   docker logs ai-automation-ui 2>&1 | Select-String -Pattern "error|404" -Context 3
   ```

4. **Verify API key is set:**
   ```powershell
   docker exec ai-automation-ui env | Select-String "API_KEY"
   ```

5. **Test proxy directly:**
   ```powershell
   # From host
   Invoke-RestMethod -Uri "http://localhost:3001/api/data/devices?limit=1" `
     -Headers @{
       Authorization="Bearer $env:API_KEY"
       "X-HomeIQ-API-Key"=$env:API_KEY
     }
   ```

---

## Related Files Modified

1. ✅ `services/ai-automation-ui/nginx.conf` - Fixed proxy path rewrite
2. 📝 `implementation/DEVICE_SUGGESTIONS_DOCKER_FIXES.md` - This document

---

## Next Steps

1. **Rebuild and test:**
   ```powershell
   docker-compose build ai-automation-ui
   docker-compose up -d ai-automation-ui
   ```

2. **Verify in browser:**
   - Navigate to `http://localhost:3001/ha-agent`
   - Test device picker
   - Verify devices load

3. **Run Playwright tests:**
   ```powershell
   cd tests/e2e
   npx playwright test ai-automation-ui/pages/device-suggestions.spec.ts
   ```

4. **Update test documentation** if needed

---

## Summary

**Root Cause:** Nginx proxy was forwarding `/api/data/devices` to `/api/data/devices` on backend, but data-api expects `/api/devices`.

**Fix:** Changed nginx `proxy_pass` to rewrite path: `/api/data/*` → `/api/*`

**Status:** ✅ Fix applied, requires Docker rebuild

**Action Required:** Rebuild Docker container and verify fix works.
