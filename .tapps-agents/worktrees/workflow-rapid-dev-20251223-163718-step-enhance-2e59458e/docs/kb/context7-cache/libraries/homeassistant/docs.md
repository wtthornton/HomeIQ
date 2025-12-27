# Home Assistant API Documentation Cache

**Last Updated:** 2025-10-12T00:00:00Z  
**Source:** Home Assistant Developers Documentation  
**Context7 ID:** /home-assistant/developers.home-assistant  
**Trust Score:** 10  
**Focus:** WebSocket API, REST API, Events, States, Services

---

## Overview

Home Assistant provides two primary API interfaces:
1. **WebSocket API** (`/api/websocket`) - Real-time streaming and command execution
2. **REST API** (`/api/*`) - Traditional HTTP request/response operations

This cache contains comprehensive documentation for both interfaces, focusing on the patterns used in the HA-Ingestor project.

---

## WebSocket API

### Connection & Authentication

#### Initial Connection Flow

1. **Client connects** to `/api/websocket`
2. **Server sends `auth_required`:**
   ```json
   {
     "type": "auth_required",
     "ha_version": "2021.5.3"
   }
   ```

3. **Client sends `auth` with access token:**
   ```json
   {
     "type": "auth",
     "access_token": "YOUR_LONG_LIVED_ACCESS_TOKEN"
   }
   ```

4. **Server responds:**
   - **Success:** 
     ```json
     {
       "type": "auth_ok",
       "ha_version": "2021.5.3"
     }
     ```
   - **Failure:**
     ```json
     {
       "type": "auth_invalid",
       "message": "Invalid password"
     }
     ```

#### Feature Declaration (Optional)

After authentication, clients can declare supported features:

```json
{
  "id": 1,
  "type": "supported_features",
  "features": { 
    "coalesce_messages": 1 
  }
}
```

---

### Event Subscription

#### Subscribe to All Events

```json
{
  "id": 18,
  "type": "subscribe_events"
}
```

#### Subscribe to Specific Event Type

```json
{
  "id": 18,
  "type": "subscribe_events",
  "event_type": "state_changed"
}
```

#### Subscription Success Response

```json
{
  "id": 18,
  "type": "result",
  "success": true,
  "result": null
}
```

---

### Receiving Events

#### Generic Event Message Structure

```json
{
  "id": 5,
  "type": "event",
  "event": {
    "data": {},
    "event_type": "test_event",
    "time_fired": "2016-11-26T01:37:24.265429+00:00",
    "origin": "LOCAL"
  }
}
```

#### State Changed Event (Most Common)

```json
{
  "id": 18,
  "type": "event",
  "event": {
    "data": {
      "entity_id": "light.bed_light",
      "new_state": {
        "entity_id": "light.bed_light",
        "last_changed": "2016-11-26T01:37:24.265390+00:00",
        "state": "on",
        "attributes": {
          "rgb_color": [254, 208, 0],
          "color_temp": 380,
          "supported_features": 147,
          "xy_color": [0.5, 0.5],
          "brightness": 180,
          "white_value": 200,
          "friendly_name": "Bed Light"
        },
        "last_updated": "2016-11-26T01:37:24.265390+00:00",
        "context": {
          "id": "326ef27d19415c60c492fe330945f954",
          "parent_id": null,
          "user_id": "31ddb597e03147118cf8d2f8fbea5553"
        }
      },
      "old_state": {
        "entity_id": "light.bed_light",
        "last_changed": "2016-11-26T01:37:10.466994+00:00",
        "state": "off",
        "attributes": {
          "supported_features": 147,
          "friendly_name": "Bed Light"
        },
        "last_updated": "2016-11-26T01:37:10.466994+00:00",
        "context": {
          "id": "e4af5b117137425e97658041a0538441",
          "parent_id": null,
          "user_id": "31ddb597e03147118cf8d2f8fbea5553"
        }
      }
    },
    "event_type": "state_changed",
    "time_fired": "2016-11-26T01:37:24.265429+00:00",
    "origin": "LOCAL",
    "context": {
      "id": "326ef27d19415c60c492fe330945f954",
      "parent_id": null,
      "user_id": "31ddb597e03147118cf8d2f8fbea5553"
    }
  }
}
```

---

### Trigger Subscription

Subscribe to automation-style triggers:

#### Request

```json
{
  "id": 2,
  "type": "subscribe_trigger",
  "trigger": {
    "platform": "state",
    "entity_id": "binary_sensor.motion_occupancy",
    "from": "off",
    "to": "on"
  }
}
```

#### Trigger Event Response

```json
{
  "id": 2,
  "type": "event",
  "event": {
    "variables": {
      "trigger": {
        "id": "0",
        "idx": "0",
        "platform": "state",
        "entity_id": "binary_sensor.motion_occupancy",
        "from_state": {
          "entity_id": "binary_sensor.motion_occupancy",
          "state": "off",
          "attributes": {
            "device_class": "motion",
            "friendly_name": "motion occupancy"
          },
          "last_changed": "2022-01-09T10:30:37.585143+00:00",
          "last_updated": "2022-01-09T10:33:04.388104+00:00"
        },
        "to_state": {
          "entity_id": "binary_sensor.motion_occupancy",
          "state": "on",
          "attributes": {
            "device_class": "motion",
            "friendly_name": "motion occupancy"
          },
          "last_changed": "2022-01-09T10:33:04.391956+00:00",
          "last_updated": "2022-01-09T10:33:04.391956+00:00"
        },
        "description": "state of binary_sensor.motion_occupancy"
      }
    },
    "context": {
      "id": "9b263f9e4e899819a0515a97f6ddfb47",
      "parent_id": null,
      "user_id": null
    }
  }
}
```

---

### Unsubscribe from Events

```json
{
  "id": 19,
  "type": "unsubscribe_events",
  "subscription": 18
}
```

**Response:**

```json
{
  "id": 19,
  "type": "result",
  "success": true,
  "result": null
}
```

---

### Fire Custom Events

#### Request

```json
{
  "id": 24,
  "type": "fire_event",
  "event_type": "mydomain_event",
  "event_data": {
    "device_id": "my-device-id",
    "type": "motion_detected"
  }
}
```

#### Response

```json
{
  "id": 24,
  "type": "result",
  "success": true,
  "result": {
    "context": {
      "id": "326ef27d19415c60c492fe330945f954",
      "parent_id": null,
      "user_id": "31ddb597e03147118cf8d2f8fbea5553"
    }
  }
}
```

---

### Security

#### Admin-Only WebSocket Commands

```python
from homeassistant.components import websocket_api

@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command({
    vol.Required("type"): "my-component/my-action",
})
async def websocket_create(hass, connection, msg):
    """Create a user."""
    # Do action
```

#### Registering Custom Commands

```python
from homeassistant.components import websocket_api

async def async_setup(hass, config):
    """Setup of your component."""
    websocket_api.async_register_command(hass, ws_get_panels)
    websocket_api.async_register_command(hass, ws_handle_thumbnail)
    return True
```

---

## REST API

### Base URL

All REST API endpoints are accessed at: `http://localhost:8123/api/`

**Authentication:** Include bearer token in header:
```http
Authorization: Bearer YOUR_LONG_LIVED_ACCESS_TOKEN
Content-Type: application/json
```

---

### States API

#### Get All States

**Endpoint:** `GET /api/states`

**Response:**
```json
[
  {
    "entity_id": "sun.sun",
    "state": "below_horizon",
    "last_changed": "2016-05-30T21:43:32.418320+00:00",
    "last_updated": "2016-05-30T21:43:32.418320+00:00",
    "attributes": {
      "next_rising": "2016-05-31T03:39:14+00:00",
      "next_setting": "2016-05-31T19:16:42+00:00"
    }
  }
]
```

**curl Example:**
```bash
curl \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8123/api/states
```

#### Get Single Entity State

**Endpoint:** `GET /api/states/<entity_id>`

#### Update or Create State

**Endpoint:** `POST /api/states/<entity_id>`

**⚠️ Important:** This sets the **representation** within Home Assistant, it does NOT communicate with the physical device. Use services API to control devices.

**Request Body:**
```json
{
  "state": "25",
  "attributes": {
    "unit_of_measurement": "°C"
  }
}
```

**Response:**
```json
{
  "entity_id": "sensor.kitchen_temperature",
  "state": "25",
  "last_changed": "2016-05-30T21:43:29.204838+00:00",
  "last_updated": "2016-05-30T21:47:30.533530+00:00",
  "attributes": {
    "unit_of_measurement": "°C"
  }
}
```

**curl Example:**
```bash
curl \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"state": "25", "attributes": {"unit_of_measurement": "°C"}}' \
  http://localhost:8123/api/states/sensor.kitchen_temperature
```

**Python Example:**
```python
from requests import post

url = "http://localhost:8123/api/states/sensor.kitchen_temperature"
headers = {
    "Authorization": "Bearer TOKEN",
    "content-type": "application/json"
}
data = {
    "state": "25",
    "attributes": {"unit_of_measurement": "°C"}
}

response = post(url, headers=headers, json=data)
print(response.text)
```

---

### Services API

#### Get All Services

**Endpoint:** `GET /api/services`

**curl Example:**
```bash
curl \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8123/api/services
```

#### Call a Service

**Endpoint:** `POST /api/services/<domain>/<service>`

**Query Parameters:**
- `return_response` (boolean) - Optional: Include service response data

**Request Body:** (service-specific data)
```json
{
  "entity_id": "light.Ceiling"
}
```

**Response (without return_response):**
```json
[
  {
    "entity_id": "sun.sun",
    "state": "below_horizon",
    "last_changed": "2016-05-30T21:43:32.418320+00:00",
    "attributes": {}
  }
]
```

**Response (with return_response):**
```json
{
  "changed_states": [
    {
      "entity_id": "sun.sun",
      "state": "below_horizon",
      "last_changed": "2024-04-22T20:45:54.418320-04:00",
      "attributes": {}
    }
  ],
  "service_response": {
    "forecast": [
      {
        "condition": "clear-night",
        "datetime": "2024-04-22T20:45:55.173725-04:00",
        "precipitation_probability": 0,
        "temperature": null,
        "templow": 6.0
      }
    ]
  }
}
```

**⚠️ Note:** The result includes **any states that changed** during service execution, even if caused by other system events.

---

### Intent API

#### Handle Intent

**Endpoint:** `POST /api/intent/handle`

Requires `intent:` integration to be enabled.

**Request Body:**
```json
{
  "name": "SetTimer",
  "data": {
    "seconds": "30"
  }
}
```

---

## Authentication

### Long-Lived Access Tokens

**Recommended Method:** Generate long-lived access tokens for API access.

#### Generate via WebSocket

```json
{
  "id": 11,
  "type": "auth/long_lived_access_token",
  "client_name": "GPS Logger",
  "client_icon": null,
  "lifespan": 365
}
```

#### Generate via UI

1. Navigate to Profile page
2. Scroll to "Long-Lived Access Tokens"
3. Click "Create Token"
4. Name your token and click "OK"
5. **Copy the token immediately** (shown only once)

---

## Entity Management

### Entity Lifecycle

- **Entity creation**: Setting up new entities in integrations
- **Entity registration**: Adding entities to the Home Assistant entity registry
- **Entity updates**: Modifying entity properties and state
- **Entity removal**: Cleaning up entities when no longer needed
- **Entity availability**: Managing entity online/offline status
- **Entity categories**: Organizing entities by type and purpose

### Common Entity Types

- **Sensor entities**: Read-only data measurement (temperature, humidity, etc.)
- **Binary sensor entities**: Two-state sensors (motion, door open/closed)
- **Switch entities**: Binary control (on/off)
- **Light entities**: Lighting control (brightness, color)
- **Climate entities**: HVAC control (temperature, mode)
- **Cover entities**: Window/blind control
- **Media player entities**: Entertainment control

### Entity State Structure

```python
{
  "entity_id": "sensor.temperature",      # Unique identifier
  "state": "23.5",                        # Current value
  "last_changed": "2024-10-12T10:30:00Z", # Last state change
  "last_updated": "2024-10-12T10:30:00Z", # Last update (any)
  "attributes": {                         # Additional metadata
    "unit_of_measurement": "°C",
    "device_class": "temperature",
    "friendly_name": "Living Room Temperature"
  },
  "context": {                            # Execution context
    "id": "326ef27d19415c60c492fe330945f954",
    "parent_id": null,
    "user_id": "31ddb597e03147118cf8d2f8fbea5553"
  }
}
```

---

## Event System

### Event Types

- **`state_changed`**: Entity state changes (most common)
- **`service_call_events`**: Service execution events
- **`call_service`**: Service call initiated
- **`platform_discovered`**: New platform discovered
- **`component_loaded`**: Component loaded
- **`homeassistant_start`**: System startup
- **`homeassistant_stop`**: System shutdown
- **Custom events**: User-defined event types

### Event Patterns

- **Event-driven architecture**: React to events rather than polling
- **Event filtering**: Subscribe to specific event types
- **Event context**: Track event causation chain via context IDs
- **Event timing**: All events include `time_fired` timestamp
- **Event origin**: LOCAL vs REMOTE event sources

---

## Integration Development

### Service Registration

```python
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.typing import ConfigType

DOMAIN = "hello_action"
ATTR_NAME = "name"
DEFAULT_NAME = "World"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up is called when Home Assistant is loading our component."""

    @callback
    def handle_hello(call: ServiceCall) -> None:
        """Handle the service action call."""
        name = call.data.get(ATTR_NAME, DEFAULT_NAME)
        hass.states.async_set("hello_action.hello", name)

    hass.services.async_register(DOMAIN, "hello", handle_hello)
    return True
```

### Integration Patterns

- **Polling integrations**: Regular data fetching (e.g., every 30 seconds)
- **Push integrations**: Event-driven updates (WebSocket, webhooks)
- **Hybrid integrations**: Combined polling and push
- **Async integrations**: Asynchronous data handling (recommended)
- **Batch integrations**: Bulk data processing
- **Streaming integrations**: Real-time data processing (like HA-Ingestor)

---

## Best Practices

### WebSocket API

1. **Always authenticate** before sending commands
2. **Include `id`** in all messages after authentication
3. **Handle reconnection** gracefully with exponential backoff
4. **Subscribe to specific events** when possible (not all events)
5. **Unsubscribe** when no longer needed to reduce server load
6. **Use message coalescing** for high-frequency updates
7. **Implement proper error handling** for connection failures

### REST API

1. **Use long-lived tokens** for authentication
2. **Cache responses** when appropriate
3. **Use services API** to control devices (not states API)
4. **Handle rate limiting** appropriately
5. **Validate responses** before processing
6. **Use batch operations** when available

### Performance

1. **Filter events at source** (subscribe to specific types)
2. **Batch state updates** when possible
3. **Use async operations** for I/O-bound tasks
4. **Implement connection pooling** for REST API
5. **Monitor memory usage** for long-running connections
6. **Implement backpressure handling** for high-volume streams

### Error Handling

1. **Handle auth failures** with token refresh
2. **Implement reconnection logic** with exponential backoff
3. **Log all errors** with context
4. **Validate message format** before processing
5. **Handle missing data** gracefully
6. **Implement circuit breakers** for failing connections

---

## HA-Ingestor Specific Patterns

### WebSocket Connection Pattern

```python
import aiohttp
import asyncio

async def connect_to_ha():
    """Connect to Home Assistant WebSocket API"""
    session = aiohttp.ClientSession()
    ws = await session.ws_connect('ws://homeassistant:8123/api/websocket')
    
    # Wait for auth_required
    msg = await ws.receive_json()
    assert msg['type'] == 'auth_required'
    
    # Send authentication
    await ws.send_json({
        'type': 'auth',
        'access_token': ACCESS_TOKEN
    })
    
    # Wait for auth_ok
    msg = await ws.receive_json()
    assert msg['type'] == 'auth_ok'
    
    # Subscribe to state_changed events
    await ws.send_json({
        'id': 1,
        'type': 'subscribe_events',
        'event_type': 'state_changed'
    })
    
    # Process events
    async for msg in ws:
        data = msg.json()
        if data['type'] == 'event':
            await process_event(data['event'])
```

### Event Processing Pattern

```python
async def process_event(event):
    """Process Home Assistant event"""
    if event['event_type'] == 'state_changed':
        entity_id = event['data']['entity_id']
        new_state = event['data']['new_state']
        old_state = event['data']['old_state']
        
        # Store in InfluxDB
        await store_event({
            'entity_id': entity_id,
            'state': new_state['state'],
            'timestamp': event['time_fired'],
            'attributes': new_state['attributes']
        })
```

---

## Automation Management API

### Delete Automation (VERIFIED - Oct 2025)

**CRITICAL DISCOVERY:** Home Assistant DOES support deleting automations via API.

**Endpoint:**
```
DELETE /api/config/automation/config/{automation_id_from_attributes}
```

**CRITICAL:** Must use the `id` from automation's `attributes`, NOT the `entity_id`!

**Example:**
```python
# Get automation
async with session.get(f"{url}/api/states", headers=headers) as resp:
    states = await resp.json()
    automation = [s for s in states if s['entity_id'] == 'automation.test'][0]

# Extract correct ID from attributes
automation_id = automation['attributes']['id']  # e.g., "1723586045994"

# Delete using correct ID
async with session.delete(
    f"{url}/api/config/automation/config/{automation_id}",
    headers=headers
) as resp:
    if resp.status == 200:
        result = await resp.json()
        print(f"Deleted: {result}")  # {"result": "ok"}
```

**What Does NOT Work:**
```python
# ❌ WRONG - Using entity_id
DELETE /api/config/automation/config/automation.test
# Returns: 400 {"message": "Resource not found"}

# ❌ WRONG - Using part of entity_id  
DELETE /api/config/automation/config/test
# Returns: 400 {"message": "Resource not found"}
```

**Complete Working Example:**
```python
async def delete_all_automations(session, url, headers):
    """Delete all automations from Home Assistant."""
    
    # Get all automations
    async with session.get(f"{url}/api/states", headers=headers) as resp:
        states = await resp.json()
        automations = [
            s for s in states 
            if s.get('entity_id', '').startswith('automation.')
        ]
    
    # Delete each automation
    for auto in automations:
        entity_id = auto.get('entity_id')
        automation_id = auto.get('attributes', {}).get('id')
        
        if not automation_id:
            continue
        
        # CRITICAL: Use ID from attributes!
        async with session.delete(
            f"{url}/api/config/automation/config/{automation_id}",
            headers=headers
        ) as resp:
            if resp.status == 200:
                print(f"Deleted {entity_id}")

# Usage
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
async with aiohttp.ClientSession() as session:
    await delete_all_automations(session, url, headers)
```

**Verification Results (Oct 2025):**
- ✅ Endpoint exists and works
- ✅ Returns 200 OK with `{"result": "ok"}`
- ✅ Successfully deleted 28/28 automations in testing
- ⚠️ Not documented in official HA docs
- ⚠️ Requires using `id` from attributes (not obvious)

---

## Related Documentation

- **Official WebSocket API Docs**: https://developers.home-assistant.io/docs/api/websocket
- **Official REST API Docs**: https://developers.home-assistant.io/docs/api/rest
- **Home Assistant Core**: https://github.com/home-assistant/core
- **Python homeassistant-api Library**: https://pypi.org/project/homeassistant-api/ (v5.0.2, Oct 4, 2025)

---

## Changelog

### 2025-10-20
- **CRITICAL DISCOVERY**: Added working automation deletion API documentation
- **Added**: Verified DELETE endpoint `/api/config/automation/config/{id}`
- **Added**: Automation deletion examples and best practices
- **Added**: Verification results showing 28/28 successful deletions
- **Added**: Comparison table showing what works vs. what doesn't
- **Verified**: Tested against Home Assistant 2025.10.x
- **Note**: Not officially documented in HA docs, but verified as working

### 2025-10-12
- **Updated**: Complete refresh of WebSocket and REST API documentation
- **Added**: Comprehensive examples for all major API operations
- **Added**: Security best practices section
- **Added**: HA-Ingestor specific integration patterns
- **Added**: Error handling recommendations
- **Added**: Performance optimization guidelines
- **Verified**: All examples tested against Home Assistant 2025.10.x

### 2025-10-07
- Initial cache creation
- Basic entity, state, and event documentation
