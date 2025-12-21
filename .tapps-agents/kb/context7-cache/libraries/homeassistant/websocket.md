<!--
library: homeassistant
topic: websocket
context7_id: /home-assistant/core
cached_at: 2025-12-21T00:41:07.333808+00:00Z
cache_hits: 0
-->

# Home Assistant WebSocket API

## Real-time Communication with Home Assistant WebSocket API

```python
import asyncio
import websockets
import json

async def connect_to_homeassistant():
    uri = "ws://localhost:8123/api/websocket"
    async with websockets.connect(uri) as websocket:
        # Receive auth_required
        await websocket.recv()
        # Send auth
        await websocket.send(json.dumps({
            "type": "auth",
            "access_token": "YOUR_TOKEN"
        }))
        # Receive auth result
        auth_result = json.loads(await websocket.recv())
        if auth_result["type"] != "auth_ok":
            return
        
        # Subscribe to state changes
        await websocket.send(json.dumps({
            "id": 1,
            "type": "subscribe_events",
            "event_type": "state_changed"
        }))
        
        # Get all states
        await websocket.send(json.dumps({
            "id": 2,
            "type": "get_states"
        }))
        
        # Call a service
        await websocket.send(json.dumps({
            "id": 3,
            "type": "call_service",
            "domain": "light",
            "service": "turn_on",
            "service_data": {
                "entity_id": "light.bedroom",
                "brightness": 200
            }
        }))
```

## Event Bus - Publishing and Subscribing to Events

```python
from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.const import EVENT_STATE_CHANGED

@callback
def state_changed_listener(event: Event) -> None:
    entity_id = event.data.get("entity_id")
    old_state = event.data.get("old_state")
    new_state = event.data.get("new_state")
    if new_state and old_state:
        print(f"{entity_id} changed from {old_state.state} to {new_state.state}")

remove_listener = hass.bus.async_listen(EVENT_STATE_CHANGED, state_changed_listener)
```

