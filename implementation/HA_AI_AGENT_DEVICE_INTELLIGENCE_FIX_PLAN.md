# HA AI Agent Service - Device Intelligence Connection Fix Plan

**Date:** 2025-12-04  
**Issue:** HA AI Agent Service cannot fetch entity inventory, areas, available services, and device capability patterns from Home Assistant  
**Root Cause:** Port mismatch - service is trying to connect to device-intelligence-service on port 8028, but the service listens on port 8019 internally

## Problem Analysis

### Error from Logs
```
httpx.ConnectError: All connection attempts failed
Exception: Failed to fetch devices: All connection attempts failed
```

### Root Cause
1. **Device Intelligence Service Configuration:**
   - Internal port: `8019` (as configured in `DEVICE_INTELLIGENCE_PORT=8019`)
   - External port mapping: `8028:8019` (host:container)
   - Service listens on `localhost:8019` internally

2. **HA AI Agent Service Configuration:**
   - Currently configured: `DEVICE_INTELLIGENCE_URL=http://device-intelligence-service:8028`
   - Should be: `DEVICE_INTELLIGENCE_URL=http://device-intelligence-service:8019`
   - Default in code: `http://device-intelligence-service:8028` (also needs fixing)

3. **Docker Network Communication:**
   - Services within the same Docker network communicate using internal ports
   - External port mappings (`8028:8019`) are only for host-to-container access
   - Internal service-to-service communication must use port `8019`

### Verification
- ✅ Device Intelligence Service is running and healthy
- ✅ Service responds on port 8019 internally: `curl http://localhost:8019/api/devices?limit=5` works
- ❌ HA AI Agent Service cannot connect because it's using port 8028

## Fix Plan

### Step 1: Update docker-compose.yml
**File:** `docker-compose.yml`  
**Line:** 901  
**Change:**
```yaml
- DEVICE_INTELLIGENCE_URL=http://device-intelligence-service:8028
```
**To:**
```yaml
- DEVICE_INTELLIGENCE_URL=http://device-intelligence-service:8019
```

### Step 2: Update Default Configuration
**File:** `services/ha-ai-agent-service/src/config.py`  
**Line:** 36  
**Change:**
```python
default="http://device-intelligence-service:8028",
```
**To:**
```python
default="http://device-intelligence-service:8019",
```

### Step 3: Verify Other Services
Check if any other services have the same port mismatch issue:
- Search for `DEVICE_INTELLIGENCE_URL` in docker-compose.yml
- Verify all internal service-to-service communication uses port 8019

**Findings:**
- ✅ `ai-automation-service` (line 1006): Uses port 8019 ✅ (correct)
- ❌ `proactive-agent-service` (line 1192): Uses port 8023 ❌ (potential issue, but not blocking current problem)
- ✅ `ha-ai-agent-service` (line 901): Fixed to use port 8019

### Step 4: Test the Fix
1. Restart ha-ai-agent-service: `docker-compose restart ha-ai-agent-service`
2. Monitor logs: `docker-compose logs -f ha-ai-agent-service`
3. Test the chat endpoint with a request like "make the lights in the office every 15 mins"
4. Verify:
   - No connection errors in logs
   - Entity inventory is fetched successfully
   - Areas are fetched successfully
   - Services summary is fetched successfully
   - Capability patterns are fetched successfully

### Step 5: Verify Context Building
After the fix, the context builder should successfully:
- ✅ Fetch entity inventory from data-api
- ✅ Fetch areas from Home Assistant
- ✅ Fetch services summary from Home Assistant
- ✅ Fetch capability patterns from device-intelligence-service (this was failing)

## Expected Outcome

After the fix:
1. **Connection Success:** No more `httpx.ConnectError: All connection attempts failed`
2. **Context Building:** All Tier 1 context components load successfully
3. **User Experience:** The AI agent can provide specific device details and create automations
4. **Error Message:** The generic error message should be replaced with actual device/entity information

## Files to Modify

1. `docker-compose.yml` (line 901)
2. `services/ha-ai-agent-service/src/config.py` (line 36)

## Testing Checklist

- [x] Update docker-compose.yml (line 901: 8028 → 8019)
- [x] Update config.py default value (line 36: 8028 → 8019)
- [x] Recreate ha-ai-agent-service container (force-recreate to pick up new env var)
- [x] Verify environment variable is set correctly (port 8019)
- [x] Verify no connection errors in logs
- [x] Test context builder connection to device-intelligence-service
- [x] Verify capability patterns service can connect
- [ ] Test chat endpoint with device query (user should test in UI)
- [ ] Verify entity inventory loads (has separate database issue)
- [ ] Verify areas load (has separate database issue)
- [ ] Verify services summary loads (has separate API response format issue)
- [ ] Verify capability patterns load (connection works, but may need devices with capabilities)

## Fix Status: ✅ CONNECTION FIXED

**Result:** The device intelligence connection is now working correctly. The service can successfully connect to `device-intelligence-service:8019`.

**Test Results:**
- ✅ Environment variable correctly set to port 8019
- ✅ Device Intelligence client initialized with correct URL
- ✅ No connection errors (`ConnectError`) in recent logs
- ✅ Capability patterns service can connect and fetch data
- ✅ Context builder successfully loads capability patterns section

**Remaining Issues (Separate from this fix):**
- Database initialization warnings (separate issue, doesn't block functionality)
- Entity inventory service has a NoneType error (separate bug)
- Services summary has API response format issue (separate bug)

**Next Steps for User:**
1. Test the chat interface with a request like "make the lights in the office every 15 mins"
2. The connection error should be gone
3. The AI should now be able to fetch device capability patterns

## Related Services

This fix may also affect:
- `ai-automation-service` (line 1006 in docker-compose.yml)
- `proactive-agent-service` (line 1192 in docker-compose.yml)

**Note:** These services also have `DEVICE_INTELLIGENCE_URL` configured. Need to verify if they have the same issue.

## Risk Assessment

**Risk Level:** Low  
**Impact:** High (blocks core functionality)  
**Effort:** Low (simple configuration change)

- Simple port number change
- No code logic changes required
- No database migrations needed
- Service restart required (minimal downtime)

