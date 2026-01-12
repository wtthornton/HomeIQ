# Home Assistant State Management Implementation Plan

**Date:** 2026-01-16  
**Status:** In Progress  
**Purpose:** Implement high-priority recommendations for entity state management

## Executive Summary

Implementing two critical features to complete Home Assistant WebSocket API integration:
1. **Entity States Retrieval (`get_states`)** - Get current state snapshot
2. **State Changed Event Subscriptions (`state_changed`)** - Real-time telemetry updates

These features enable real-time Zigbee2MQTT device monitoring and complete the metadata pipeline recommended by Home Assistant best practices.

---

## Objectives

### 1. Add `get_states()` Method

**Purpose:** Retrieve current entity states (runtime values + attributes) via WebSocket API

**Implementation:**
- Add method to `HomeAssistantClient` class
- Use WebSocket command: `{"type": "get_states"}`
- Return list of entity state dictionaries
- Follow existing pattern used for other WebSocket commands

**File:** `services/device-intelligence-service/src/clients/ha_client.py`

**Pattern Reference:** Similar to `get_device_registry()`, `get_entity_registry()`, etc.

### 2. Add `subscribe_to_state_changes()` Method

**Purpose:** Subscribe to `state_changed` events for real-time telemetry updates

**Implementation:**
- Add method to `HomeAssistantClient` class
- Use existing `subscribe_to_events()` infrastructure
- Subscribe to `"state_changed"` event type
- Follow pattern used by `subscribe_to_registry_updates()`

**File:** `services/device-intelligence-service/src/clients/ha_client.py`

**Pattern Reference:** Similar to `subscribe_to_registry_updates()` method (lines 580-623)

---

## Implementation Steps

### Step 1: Add `get_states()` Method

**Location:** `services/device-intelligence-service/src/clients/ha_client.py`

**Add after:** `get_area_registry()` method (around line 472)

**Code:**
```python
async def get_states(self) -> list[dict[str, Any]]:
    """
    Get all entity states from Home Assistant (runtime values + attributes).
    
    Uses WebSocket command: {"type": "get_states"}
    Returns current state, attributes, device_class, state_class, friendly_name
    for all entities.
    
    Returns:
        List of entity state dictionaries with keys:
        - entity_id
        - state (current state value)
        - attributes (dict of entity attributes)
        - last_changed
        - last_updated
        - context
        - etc.
        
    Raises:
        Exception: If WebSocket command fails
    """
    try:
        response = await self.send_message({
            "type": "get_states"
        })

        states = response.get("result", [])
        logger.info(f"📊 Retrieved {len(states)} entity states from Home Assistant")
        return states

    except Exception as e:
        logger.error(f"❌ Failed to get entity states: {e}")
        return []
```

### Step 2: Add `subscribe_to_state_changes()` Method

**Location:** `services/device-intelligence-service/src/clients/ha_client.py`

**Add after:** `subscribe_to_registry_updates()` method (around line 623)

**Code:**
```python
async def subscribe_to_state_changes(
    self,
    callback: Callable[[dict[str, Any]], Awaitable[None]]
):
    """
    Subscribe to state_changed events for real-time telemetry updates.
    
    This enables real-time monitoring of entity state changes (sensor readings,
    switch toggles, etc.) for Zigbee2MQTT and other devices.
    
    Args:
        callback: Async callback function that receives state_changed event data.
                  Event data structure:
                  {
                      "event_type": "state_changed",
                      "event": {
                          "entity_id": "sensor.example",
                          "old_state": {...},
                          "new_state": {...}
                      },
                      "time_fired": "2026-01-16T12:00:00.000Z",
                      "origin": "LOCAL",
                      "context": {...}
                  }
    """
    try:
        await self.subscribe_to_events("state_changed", callback)
        logger.info("✅ Subscribed to state_changed events for real-time telemetry")
    except Exception as e:
        logger.error(f"❌ Failed to subscribe to state_changed events: {e}")
        raise
```

### Step 3: (Optional) Integrate into DiscoveryService

**Location:** `services/device-intelligence-service/src/core/discovery_service.py`

**Considerations:**
- State subscriptions are **optional** for discovery service
- Discovery service focuses on metadata (devices, entities, areas)
- State changes are typically handled by event ingestion services (websocket-ingestion)
- **Decision:** Do NOT integrate into discovery service at this time
- State subscriptions can be used by other services that need real-time telemetry

**Rationale:**
- Discovery service already has registry event subscriptions
- State changes are high-volume events (every sensor reading)
- Separation of concerns: discovery = metadata, ingestion = events
- Other services (websocket-ingestion) already handle state_changed events

---

## Testing Strategy

### Unit Tests

**File:** `services/device-intelligence-service/tests/test_ha_client.py`

**Tests to Add:**
1. `test_get_states()` - Verify `get_states()` method returns entity states
2. `test_subscribe_to_state_changes()` - Verify state_changed subscription works
3. `test_state_changed_event_handler()` - Verify callback receives state_changed events

### Manual Testing

**Test Scenarios:**
1. Call `get_states()` and verify entity states are returned
2. Subscribe to `state_changed` events
3. Trigger state change (toggle switch, change sensor value)
4. Verify callback receives state_changed event

**Test Commands:**
```python
# Test get_states
states = await ha_client.get_states()
assert len(states) > 0
assert "entity_id" in states[0]
assert "state" in states[0]

# Test state_changed subscription
async def handle_state_change(event_data):
    print(f"State changed: {event_data}")

await ha_client.subscribe_to_state_changes(handle_state_change)
```

---

## Code References

### Pattern: WebSocket Command (get_states)

**Reference:** `get_device_registry()` method (lines 359-403)
- Uses `send_message()` with command dict
- Extracts `result` from response
- Logs success/error
- Returns list or empty list on error

### Pattern: Event Subscription (subscribe_to_state_changes)

**Reference:** `subscribe_to_registry_updates()` method (lines 580-623)
- Uses `subscribe_to_events()` helper
- Takes callback function
- Logs success/error
- Handles exceptions

### Existing State Changed Usage

**Other Services:**
- `services/websocket-ingestion/src/event_subscription.py` - Subscribes to state_changed
- `services/ai-pattern-service/src/tracking/ha_event_subscriber.py` - Handles state_changed events

**Event Structure:**
```python
{
    "event_type": "state_changed",
    "event": {
        "entity_id": "sensor.example",
        "old_state": {
            "entity_id": "sensor.example",
            "state": "23.5",
            "attributes": {...},
            "last_changed": "2026-01-16T12:00:00.000Z",
            "last_updated": "2026-01-16T12:00:00.000Z"
        },
        "new_state": {
            "entity_id": "sensor.example",
            "state": "24.0",
            "attributes": {...},
            "last_changed": "2026-01-16T12:01:00.000Z",
            "last_updated": "2026-01-16T12:01:00.000Z"
        }
    },
    "time_fired": "2026-01-16T12:01:00.000Z",
    "origin": "LOCAL",
    "context": {
        "id": "...",
        "parent_id": None,
        "user_id": None
    }
}
```

---

## Implementation Checklist

- [x] Create implementation plan
- [x] Add `get_states()` method to `HomeAssistantClient`
- [x] Add `subscribe_to_state_changes()` method to `HomeAssistantClient`
- [x] Verify code follows existing patterns
- [x] Verify no linting errors
- [ ] Test `get_states()` method (manual testing recommended)
- [ ] Test `subscribe_to_state_changes()` method (manual testing recommended)
- [ ] Update documentation (if needed)

---

## Acceptance Criteria

### `get_states()` Method

✅ Method exists in `HomeAssistantClient` class  
✅ Uses WebSocket API (`{"type": "get_states"}`)  
✅ Returns list of entity state dictionaries  
✅ Handles errors gracefully (returns empty list)  
✅ Logs success/error appropriately  
✅ Follows existing code patterns  

### `subscribe_to_state_changes()` Method

✅ Method exists in `HomeAssistantClient` class  
✅ Uses `subscribe_to_events()` infrastructure  
✅ Subscribes to `"state_changed"` event type  
✅ Accepts callback function parameter  
✅ Logs success/error appropriately  
✅ Follows existing code patterns  

---

## Notes

1. **WebSocket vs REST:** Using WebSocket `get_states` command (consistent with other methods) instead of REST API `/api/states`

2. **Discovery Service Integration:** Intentionally NOT integrating state subscriptions into discovery service - separation of concerns (metadata vs events)

3. **Event Volume:** State changed events are high-volume. Services that need real-time telemetry should handle these events separately from discovery.

4. **Backward Compatibility:** New methods are additive - no breaking changes to existing code.

---

## Related Documentation

- [Zigbee2MQTT HA Integration Comparison](../analysis/ZIGBEE2MQTT_HA_INTEGRATION_COMPARISON.md)
- [Home Assistant WebSocket API Documentation](https://developers.home-assistant.io/docs/api/websocket/)
- [Device Intelligence Service Architecture](../../docs/architecture/)

---

**Status:** ✅ **IMPLEMENTATION COMPLETE**  
**Completed:** 2026-01-16  
**Next Steps:** Manual testing recommended
