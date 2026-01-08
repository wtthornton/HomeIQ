# Entity Discovery Root Cause and Fix

**Date:** 2026-01-08  
**Status:** Root Cause Identified - Fix Required  
**Priority:** High

---

## Root Cause Identified

### The Problem

**Entity discovery fails due to WebSocket concurrency issue:**

1. ✅ Configuration is correct (HA_HTTP_URL, HA_TOKEN, HA_WS_URL all set correctly)
2. ✅ WebSocket connection is established and working (2.4M events received)
3. ❌ Entity discovery returns 0 entities due to concurrency error

**Error from Logs:**
```
❌ Cannot call receive() while listen() loop is running. Discovery should use message routing instead. Error: Concurrent call to receive() is not allowed
❌ Entity registry WebSocket command failed: No response
❌ WebSocket fallback returned empty result - entity discovery failed
```

### Root Cause Analysis

**Code Flow:**
1. Discovery service tries HTTP endpoint `/api/config/entity_registry/list` (which doesn't exist) → Returns 404
2. Falls back to WebSocket command `config/entity_registry/list`
3. WebSocket fallback uses `_wait_for_response()` which calls `websocket.receive()` directly
4. **FAILS**: The WebSocket connection is already consumed by the listen loop handling incoming events
5. Result: "Concurrent call to receive() is not allowed" error
6. Result: 0 entities discovered

**Code Location:**
- `services/websocket-ingestion/src/discovery_service.py`
- Method: `discover_entities()` (line 155-301)
- Fallback method: `_discover_entities_websocket()` (line 303-361)
- Problem method: `_wait_for_response()` (line 425-498)

**The Comment in Code (Line 432-437):**
```python
"""
IMPORTANT: This method should NOT be called while the listen() loop is running,
as it will cause "Concurrent call to receive() is not allowed" errors.

For discovery during active connection, use message routing through the connection manager.
"""
```

### Why HTTP-First Approach Fails

The code tries HTTP first to "avoid WebSocket concurrency issues" (line 159 comment), but:
- ❌ HTTP endpoint `/api/config/entity_registry/list` doesn't exist in Home Assistant
- ✅ Entity registry listing is WebSocket-only
- ❌ WebSocket fallback fails due to concurrency

---

## Solution Options

### Option 1: Use HTTP API State Endpoint (Recommended - Quick Fix)

**Home Assistant State API can return entity list:**

Instead of entity registry list, use the states API which returns all entity states:
- Endpoint: `GET /api/states`
- Returns: Array of state objects (one per entity)
- Can extract entity_id from each state

**Pros:**
- ✅ HTTP API (no WebSocket concurrency issues)
- ✅ Works during active WebSocket connection
- ✅ Returns all entities with current states
- ✅ Simple implementation

**Cons:**
- ⚠️ Returns state data, not full registry metadata (but entity_id is sufficient for discovery)
- ⚠️ May need to query registry for metadata separately (optional)

**Implementation:**
```python
# In discover_entities() method
async with session.get(
    f"{ha_url}/api/states",  # Use states API instead
    headers=headers,
    timeout=aiohttp.ClientTimeout(total=30)
) as response:
    if response.status == 200:
        states = await response.json()
        # Extract entity_ids from states
        entities = [{"entity_id": state["entity_id"]} for state in states]
        # Optionally fetch full registry metadata via WebSocket (if needed)
```

### Option 2: Implement Message Routing (Complex - Long-term Fix)

**Implement message routing through connection manager:**

Create a message routing mechanism where:
1. Discovery service sends command via connection manager
2. Connection manager routes command through send queue
3. Listen loop receives response and routes to pending response futures
4. Discovery service waits on future for response

**Pros:**
- ✅ Proper architecture for concurrent WebSocket usage
- ✅ Reusable for other WebSocket commands during active connection
- ✅ Follows the pattern suggested in code comments

**Cons:**
- ⚠️ Requires significant refactoring
- ⚠️ More complex implementation
- ⚠️ Need to modify connection manager and discovery service

**Implementation Complexity:** High - Requires:
- Message ID routing mechanism in connection manager
- Response futures dictionary
- Integration with listen loop message handling
- Thread-safe message routing

### Option 3: Create Separate WebSocket Connection for Discovery (Not Recommended)

Create a separate WebSocket connection just for discovery commands.

**Cons:**
- ❌ Additional connection overhead
- ❌ More complex connection management
- ❌ Not a clean solution

---

## Recommended Fix: Option 1 (HTTP States API)

**Quick Fix Implementation:**

Modify `discover_entities()` to use `/api/states` endpoint instead of `/api/config/entity_registry/list`:

```python
async def discover_entities(self, websocket: ClientWebSocketResponse | None = None) -> list[dict[str, Any]]:
    """
    Discover all entities from Home Assistant
    
    Uses HTTP States API to avoid WebSocket concurrency issues.
    States API returns all entities with their current states.
    """
    try:
        # ... existing code ...
        
        # Use States API (HTTP) - returns all entities with states
        async with session.get(
            f"{ha_url}/api/states",  # Changed from /api/config/entity_registry/list
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 200:
                states = await response.json()
                
                # Convert states to entity registry format
                entities = []
                for state in states:
                    entity_id = state.get("entity_id")
                    if entity_id:
                        entities.append({
                            "entity_id": entity_id,
                            # Extract domain from entity_id
                            "platform": entity_id.split(".")[0] if "." in entity_id else "unknown",
                            # States API doesn't provide full registry metadata,
                            # but entity_id is sufficient for basic discovery
                        })
                
                entity_count = len(entities)
                logger.info(f"✅ Discovered {entity_count} entities via States API")
                
                # ... rest of processing ...
                return entities
            else:
                # ... error handling ...
```

**Why This Works:**
- ✅ HTTP API endpoint exists and works
- ✅ No WebSocket concurrency issues
- ✅ Returns all entities (entity_id is primary requirement)
- ✅ Simple change (minimal code modification)
- ✅ Fast implementation

**Limitations:**
- ⚠️ States API doesn't return full registry metadata (device_id, area_id, etc.)
- ⚠️ May need WebSocket registry commands for full metadata (can be done separately if needed)
- ⚠️ For basic entity discovery (entity_id list), this is sufficient

---

## Implementation Plan

### Step 1: Implement HTTP States API Fix

1. Modify `discover_entities()` method in `discovery_service.py`
2. Change endpoint from `/api/config/entity_registry/list` to `/api/states`
3. Parse states response to extract entity_ids
4. Test with manual discovery trigger

### Step 2: Test and Verify

1. Trigger discovery: `POST http://localhost:8001/api/v1/discovery/trigger`
2. Verify entities discovered: Check response for `entities_discovered > 0`
3. Verify entities in Data API: Query `/api/v1/entities`
4. Verify HA AI Agent can query entities

### Step 3: Optional - Enhanced Metadata (Future)

If full registry metadata is needed:
- Keep HTTP states API for entity discovery (works during active connection)
- Optionally fetch metadata for specific entities via WebSocket (using message routing) when needed
- Or use entity registry update events (already subscribed) to populate metadata over time

---

## Files to Modify

1. **`services/websocket-ingestion/src/discovery_service.py`**
   - Method: `discover_entities()` (lines 155-301)
   - Change: Use `/api/states` endpoint instead of `/api/config/entity_registry/list`
   - Change: Parse states response to extract entity_ids

---

## Testing Plan

### Test 1: Manual Discovery Trigger
```powershell
$result = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/discovery/trigger" -Method Post
$result | ConvertTo-Json
# Expected: entities_discovered > 0
```

### Test 2: Verify Entities in Data API
```powershell
$entities = Invoke-RestMethod -Uri "http://localhost:8006/api/v1/entities?limit=10"
$entities.Count
# Expected: > 0 entities
```

### Test 3: Verify HA AI Agent Can Query Entities
```powershell
# Test query for binary sensors
$binarySensors = Invoke-RestMethod -Uri "http://localhost:8006/api/v1/entities?domain=binary_sensor&limit=10"
$binarySensors.Count
# Expected: > 0 if binary sensors exist in Home Assistant
```

---

## Related Issues

- Entity discovery failure prevents HA AI Agent from using real entity data
- Test validation fails for presence sensor requirement
- Device/area mappings not cached (affects Epic 23.2 functionality)

---

## Status

- ✅ Root cause identified
- ✅ Solution designed (HTTP States API)
- ⏳ Implementation pending
- ⏳ Testing pending
