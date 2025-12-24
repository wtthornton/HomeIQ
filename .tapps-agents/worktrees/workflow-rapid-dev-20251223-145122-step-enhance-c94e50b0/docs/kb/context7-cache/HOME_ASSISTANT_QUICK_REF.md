# Home Assistant API - Quick Reference

**Last Updated:** October 12, 2025  
**Full Documentation:** `libraries/homeassistant/docs.md`  
**Version:** 2025.10.x

---

## WebSocket API Quick Start

### 1. Connect & Authenticate

```python
import aiohttp

async def connect():
    session = aiohttp.ClientSession()
    ws = await session.ws_connect('ws://homeassistant:8123/api/websocket')
    
    # Wait for auth_required
    msg = await ws.receive_json()
    
    # Authenticate
    await ws.send_json({
        'type': 'auth',
        'access_token': 'YOUR_TOKEN'
    })
    
    # Wait for auth_ok
    msg = await ws.receive_json()
    return ws
```

### 2. Subscribe to State Changes

```json
{
  "id": 1,
  "type": "subscribe_events",
  "event_type": "state_changed"
}
```

### 3. Process Events

```python
async for msg in ws:
    data = msg.json()
    if data['type'] == 'event':
        event = data['event']
        entity_id = event['data']['entity_id']
        new_state = event['data']['new_state']['state']
        # Process event...
```

---

## REST API Quick Start

### Get All States

```bash
curl -H "Authorization: Bearer TOKEN" \
     http://localhost:8123/api/states
```

### Call a Service

```bash
curl -X POST \
     -H "Authorization: Bearer TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"entity_id": "light.living_room"}' \
     http://localhost:8123/api/services/light/turn_on
```

---

## Common Patterns

### Event Structure

```json
{
  "id": 1,
  "type": "event",
  "event": {
    "event_type": "state_changed",
    "data": {
      "entity_id": "sensor.temperature",
      "new_state": {
        "state": "23.5",
        "attributes": {...}
      }
    }
  }
}
```

### State Structure

```json
{
  "entity_id": "sensor.temperature",
  "state": "23.5",
  "attributes": {
    "unit_of_measurement": "°C",
    "friendly_name": "Temperature"
  },
  "last_changed": "2025-10-12T10:30:00Z",
  "last_updated": "2025-10-12T10:30:00Z"
}
```

---

## Key Differences

| Operation | Use REST API | Use WebSocket API |
|-----------|--------------|-------------------|
| Real-time updates | ❌ No | ✅ Yes |
| Query current state | ✅ Yes | ✅ Yes |
| Call services | ✅ Yes | ✅ Yes |
| Subscribe to events | ❌ No | ✅ Yes |
| One-off queries | ✅ Preferred | ❌ Overkill |
| Long-lived connections | ❌ Not ideal | ✅ Perfect |

---

## Best Practices

### WebSocket
1. ✅ Subscribe to specific event types (not all events)
2. ✅ Handle reconnection with exponential backoff
3. ✅ Unsubscribe when done
4. ✅ Use message coalescing for high-frequency updates

### REST
1. ✅ Use services API to control devices
2. ✅ Cache responses appropriately
3. ✅ Handle rate limiting
4. ✅ Validate responses

---

## HA-Ingestor Integration

**Our Usage:**
- ✅ WebSocket API for real-time event streaming
- ✅ Subscribe to `state_changed` events only
- ✅ Async processing with aiohttp
- ✅ Store events in InfluxDB

**Services Using HA API:**
- `websocket-ingestion` (Primary - WebSocket)
- `admin-api` (Secondary - could use REST)
- `enrichment-pipeline` (Indirect - processes events)

---

## Need More Details?

📄 **Full Documentation:** `docs/kb/context7-cache/libraries/homeassistant/docs.md`  
📊 **Update Report:** `docs/kb/context7-cache/HOME_ASSISTANT_API_KB_UPDATE_2025-10-12.md`  
🔍 **Meta Info:** `docs/kb/context7-cache/libraries/homeassistant/meta.yaml`

**Context7 ID:** `/home-assistant/developers.home-assistant`  
**Trust Score:** 10/10  
**Code Snippets:** 1824  
**Next Refresh:** November 11, 2025

