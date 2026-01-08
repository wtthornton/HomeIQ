# Entity Discovery Investigation: Missing Binary Sensor Entities

**Date:** 2026-01-08  
**Issue:** Binary sensor entities (motion, presence) not available to HA AI Agent  
**Root Cause:** Entity discovery failing - no entities syncing to Data API

---

## Problem Summary

During testing of the HA AI Agent automation generation, we discovered that:
1. The AI generated fictional motion sensors instead of using real presence sensors
2. Querying Data API for `binary_sensor.*`, `device_tracker.*`, or `person.*` entities returned 0 results
3. This prevented the AI from generating correct YAML with proper presence sensor `entity_id`

---

## Root Cause Analysis

### Entity Discovery Status

**Discovery Service Status:**
- Manual discovery trigger: `POST /api/v1/discovery/trigger`
- Result: **0 entities discovered, 0 devices discovered**
- Entity registry HTTP endpoint: `/api/config/entity_registry/list` → **HTTP 404 (Not Found)**
- WebSocket fallback: **Not available** (no WebSocket connection)

**Logs Evidence:**
```
⚠️  HTTP entity registry endpoint failed: HTTP 404 - 404: Not Found
❌ No WebSocket available for fallback - entity discovery failed
This indicates a configuration issue - check HA_HTTP_URL and HA_TOKEN, or ensure WebSocket is available
```

### Sync Flow (Current State)

```
Home Assistant Entity Registry
        ↓
[FAILS] HTTP GET /api/config/entity_registry/list (404 - endpoint doesn't exist)
        ↓
[FAILS] WebSocket fallback (no WebSocket connection available)
        ↓
0 entities discovered
        ↓
No entities synced to Data API SQLite
        ↓
HA AI Agent has no entity context
        ↓
AI generates fictional entities (binary_sensor.office_motion_1, etc.)
```

### Expected Sync Flow

```
Home Assistant Entity Registry
        ↓
WebSocket command: {"type": "config/entity_registry/list"}
        ↓
Entities discovered (N entities)
        ↓
POST /internal/entities/bulk_upsert → Data API
        ↓
Entities stored in SQLite
        ↓
HA AI Agent queries Data API
        ↓
AI uses real entities (presence sensors, motion sensors, etc.)
```

**Note:** Home Assistant entity registry listing is **WebSocket-only** - there is no HTTP endpoint. The code incorrectly attempts HTTP first, which always returns 404, then falls back to WebSocket (which isn't available).

---

## Impact

1. **HA AI Agent Context Building:**
   - `enhanced_context_builder.py` queries Data API for binary sensors
   - Returns 0 results (no entities in database)
   - AI generates fictional entity IDs as fallback

2. **Test Validation:**
   - Test requirement: "Proper presence sensor entity_id"
   - Cannot be validated (no presence sensors available)
   - AI's behavior is reasonable given missing context

3. **System Functionality:**
   - Entity metadata not available to any service
   - Device/area mappings not cached
   - All services relying on entity registry data are affected

---

## Configuration Issue

**Environment Variables (websocket-ingestion):**
- `HA_HTTP_URL`: Should point to Home Assistant HTTP API
- `HA_TOKEN`: Should contain valid Home Assistant long-lived access token
- WebSocket connection: Should be established on service startup

**Diagnosis:**
- Entity registry endpoint returns 404 because **the endpoint doesn't exist in HTTP API** (entity registry listing is WebSocket-only)
- The real issue is: **WebSocket connection is not established**, so fallback fails
- Root cause: Missing or incorrect WebSocket configuration:
  1. `HA_WS_URL` or `HA_URL` not set (WebSocket URL)
  2. WebSocket connection not established on service startup
  3. Home Assistant not accessible from container
  4. Token invalid or expired
  5. Network/firewall blocking WebSocket connections

---

## Recommended Next Steps

### 1. Run Troubleshooting Script

```powershell
# Run automated troubleshooting script
python scripts/troubleshoot_ha_connection.py
```

This script will:
- Test HTTP connectivity to Home Assistant
- Validate token authentication
- Confirm entity registry endpoint returns 404 (expected - WebSocket-only)
- Provide specific recommendations based on findings

### 2. Verify Home Assistant Connection

```powershell
# Check if Home Assistant is accessible (HTTP)
$haUrl = "http://192.168.1.86:8123"
$haToken = "<your-token>"

# Test basic API access
Invoke-RestMethod -Uri "$haUrl/api/config" -Headers @{Authorization="Bearer $haToken"}
```

### 2. Check websocket-ingestion Configuration

```powershell
# Check environment variables
docker-compose exec websocket-ingestion env | Select-String -Pattern "HA_|HOME_ASSISTANT"
```

### 3. Check WebSocket Connection Status

```powershell
# Check websocket-ingestion logs for connection status
docker-compose logs websocket-ingestion | Select-String -Pattern "WebSocket|CONNECTED|DISCONNECTED" | Select-Object -First 20
```

### 4. Manual Entity Sync (If HA Accessible)

If Home Assistant is accessible, entities can be synced manually by:
1. Fixing configuration (HA_HTTP_URL, HA_TOKEN)
2. Restarting websocket-ingestion service
3. Triggering discovery: `POST http://localhost:8001/api/v1/discovery/trigger`

---

## Test Results Impact

**Test:** "When I enter my office turn on the lights and when I leave turn them off in 5 mins"

**Expected Requirements:**
1. ✅ State trigger with `for: "00:05:00"` - **PASSED**
2. ✅ `target.area_id: office` for lights - **PASSED**
3. ❌ Proper presence sensor `entity_id` - **FAILED (cannot validate - no entities available)**

**Conclusion:**
The test cannot be fully validated until entity discovery is fixed. The AI's behavior (generating fictional motion sensors) is reasonable given the lack of real entity context.

---

## Files Referenced

- `services/websocket-ingestion/src/discovery_service.py` - Entity discovery logic
- `services/websocket-ingestion/src/api/routers/discovery.py` - Discovery trigger endpoint
- `services/data-api/src/devices_endpoints.py` - Entity bulk_upsert endpoint
- `services/ha-ai-agent-service/src/services/enhanced_context_builder.py` - Binary sensor context building
- `implementation/TEST_RESULTS_OFFICE_AUTOMATION.md` - Original test results

---

## Related Issues

This investigation was triggered by test results documenting missing presence sensors. The root cause is entity discovery failure, not a problem with the HA AI Agent's logic.
