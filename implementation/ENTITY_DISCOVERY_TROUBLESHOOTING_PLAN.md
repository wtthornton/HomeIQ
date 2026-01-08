# Entity Discovery Troubleshooting Plan

**Date:** 2026-01-08  
**Status:** Active Investigation  
**Related:** `implementation/ENTITY_DISCOVERY_INVESTIGATION.md`

---

## Root Cause Confirmed

### Key Finding: HTTP Endpoint Doesn't Exist

**Home Assistant Entity Registry Listing is WebSocket-Only**

The code in `discovery_service.py` attempts to use HTTP endpoint:
```
GET /api/config/entity_registry/list
```

**This endpoint does NOT exist in Home Assistant's HTTP API.** Entity registry listing is only available via WebSocket command:
```
{"type": "config/entity_registry/list"}
```

**Current Code Flow (Problematic):**
1. ✅ Try HTTP endpoint `/api/config/entity_registry/list`
2. ❌ HTTP returns 404 (endpoint doesn't exist)
3. ✅ Fallback to WebSocket command `config/entity_registry/list`
4. ❌ **WebSocket connection not available** (this is the actual blocker)

---

## Troubleshooting Script

Created `scripts/troubleshoot_ha_connection.py` to diagnose:

1. **HTTP Connectivity Test**
   - Tests basic connection to Home Assistant
   - Validates token authentication
   - Confirms entity registry endpoint returns 404 (expected)

2. **Connection Status Check**
   - Verifies HA_HTTP_URL configuration
   - Validates HA_TOKEN
   - Tests WebSocket connection capability

**Usage:**
```powershell
# Run from project root
python scripts/troubleshoot_ha_connection.py
```

---

## Configuration Checklist

### Required Environment Variables

**For websocket-ingestion service:**

1. **HA_HTTP_URL** (or HOME_ASSISTANT_URL)
   - Format: `http://<ip>:8123` or `https://<domain>:8123`
   - Example: `http://192.168.1.86:8123`
   - Purpose: HTTP API access for health checks, services API

2. **HA_WS_URL** (or HA_URL)
   - Format: `ws://<ip>:8123/api/websocket` or `wss://<domain>:8123/api/websocket`
   - Example: `ws://192.168.1.86:8123/api/websocket`
   - Purpose: WebSocket connection for entity/device discovery and event streaming

3. **HA_TOKEN** (or HOME_ASSISTANT_TOKEN)
   - Format: Long-lived access token from Home Assistant
   - Generation: Settings → Profile → Long-Lived Access Tokens → Create Token
   - Purpose: Authentication for both HTTP and WebSocket connections

### Verification Steps

1. **Check Environment Variables:**
   ```powershell
   docker-compose exec websocket-ingestion env | Select-String -Pattern "HA_|HOME_ASSISTANT"
   ```

2. **Test HTTP Connectivity:**
   ```powershell
   $haUrl = "http://192.168.1.86:8123"
   $haToken = "<your-token>"
   Invoke-RestMethod -Uri "$haUrl/api/config" -Headers @{Authorization="Bearer $haToken"}
   ```

3. **Check WebSocket Connection Status:**
   ```powershell
   # Check logs for WebSocket connection
   docker-compose logs websocket-ingestion | Select-String -Pattern "WebSocket|CONNECTED|DISCONNECTED" | Select-Object -Last 20
   
   # Check health endpoint
   Invoke-RestMethod -Uri "http://localhost:8001/health"
   ```

4. **Trigger Discovery Manually:**
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8001/api/v1/discovery/trigger" -Method Post
   ```

---

## Next Steps

### Option 1: Fix Configuration (Recommended)

**If WebSocket connection is not established:**

1. **Verify WebSocket URL:**
   - Ensure `HA_WS_URL` or `HA_URL` is set correctly
   - Format: `ws://192.168.1.86:8123/api/websocket` (not `http://`)

2. **Verify Token:**
   - Generate new Long-Lived Access Token in Home Assistant
   - Set `HA_TOKEN` environment variable
   - Restart websocket-ingestion service

3. **Check Network Connectivity:**
   - Ensure Home Assistant is accessible from container
   - Test from container: `docker-compose exec websocket-ingestion ping <ha-ip>`

4. **Review Logs:**
   ```powershell
   docker-compose logs websocket-ingestion | Select-String -Pattern "connection|error|fail" | Select-Object -Last 50
   ```

### Option 2: Code Fix (If WebSocket Connection Issues Persist)

**Current Code Issue:**

The code attempts HTTP first (which always fails), then falls back to WebSocket. Since entity registry listing is WebSocket-only, we should:

1. **Option A: Use WebSocket Directly (Preferred)**
   - Remove HTTP attempt for entity registry
   - Use WebSocket command directly
   - Ensure WebSocket connection is established before discovery runs

2. **Option B: Improve Error Handling**
   - Document that HTTP endpoint doesn't exist (expected 404)
   - Provide clearer error messages when WebSocket fallback fails
   - Add connection status checks before attempting discovery

**Code Location:**
- `services/websocket-ingestion/src/discovery_service.py`
- Method: `discover_entities()` (lines 155-301)

---

## Impact Assessment

### Current Impact

1. **Entity Discovery:** ❌ Failing (0 entities discovered)
2. **Data API Sync:** ❌ No entities in SQLite database
3. **HA AI Agent:** ⚠️  Working with limitations (generates fictional entities as fallback)
4. **Device/Area Mappings:** ❌ Not cached (affects event enrichment)

### Expected After Fix

1. **Entity Discovery:** ✅ Successful (N entities discovered)
2. **Data API Sync:** ✅ Entities stored in SQLite
3. **HA AI Agent:** ✅ Uses real entity data (presence sensors, motion sensors, etc.)
4. **Device/Area Mappings:** ✅ Cached (improves event enrichment performance)

---

## Testing Plan

After fixing configuration or code:

1. **Run Troubleshooting Script:**
   ```powershell
   python scripts/troubleshoot_ha_connection.py
   ```

2. **Trigger Discovery:**
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8001/api/v1/discovery/trigger" -Method Post
   ```

3. **Verify Entity Count:**
   ```powershell
   # Check discovery result
   $result = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/discovery/trigger" -Method Post
   Write-Host "Entities discovered: $($result.entities_discovered)"
   
   # Check Data API
   Invoke-RestMethod -Uri "http://localhost:8006/api/v1/entities?limit=10"
   ```

4. **Test HA AI Agent:**
   - Run test: "When I enter my office turn on the lights and when I leave turn them off in 5 mins"
   - Verify AI uses real presence sensor entities (not fictional ones)
   - Check that `entity_id` matches real entities in system

---

## Documentation References

- **Investigation Document:** `implementation/ENTITY_DISCOVERY_INVESTIGATION.md`
- **Discovery Service Code:** `services/websocket-ingestion/src/discovery_service.py`
- **Discovery Router:** `services/websocket-ingestion/src/api/routers/discovery.py`
- **Home Assistant API Docs:** https://www.home-assistant.io/docs/api/rest
- **WebSocket API Docs:** https://www.home-assistant.io/docs/api/websocket

---

## Related Issues

- Entity discovery failure prevents HA AI Agent from using real entity data
- Test validation fails for presence sensor requirement (no entities available)
- Device/area mappings not cached (affects Epic 23.2 functionality)
