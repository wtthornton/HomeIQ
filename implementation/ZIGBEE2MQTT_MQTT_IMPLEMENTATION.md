# Zigbee2MQTT MQTT Subscription Implementation

## Summary

Implemented MQTT subscription for Zigbee2MQTT health monitoring, replacing HA API polling with direct MQTT topic subscription. This follows the Epic 31 architecture pattern and 2025 best practices.

## Changes Made

### 1. Added MQTT Dependencies
- **File**: `services/ha-setup-service/requirements.txt`
- **Change**: Added `paho-mqtt==2.1.0` for MQTT client support

### 2. Updated Configuration
- **File**: `services/ha-setup-service/src/config.py`
- **Changes**:
  - Added `mqtt_broker_url` (default: `mqtt://core-mosquitto:1883`)
  - Added `mqtt_username` and `mqtt_password` (optional)
  - Added `zigbee2mqtt_base_topic` (default: `zigbee2mqtt`)

### 3. Created MQTT Client
- **File**: `services/ha-setup-service/src/zigbee2mqtt_mqtt_client.py` (NEW)
- **Purpose**: MQTT client for subscribing to Zigbee2MQTT bridge topics
- **Features**:
  - Subscribes to `zigbee2mqtt/bridge/state` (bridge online/offline)
  - Subscribes to `zigbee2mqtt/bridge/devices` (device list)
  - Subscribes to `zigbee2mqtt/bridge/info` (bridge information)
  - Subscribes to `zigbee2mqtt/bridge/event` (bridge events)
  - Automatic reconnection on disconnect
  - READ-ONLY subscription (never publishes to bridge topics)

### 4. Updated Health Service
- **File**: `services/ha-setup-service/src/health_service.py`
- **Changes**:
  - Replaced `_check_zigbee2mqtt_integration()` to use MQTT subscription
  - Added `_ensure_z2m_mqtt_client()` for client initialization
  - Added `_check_zigbee2mqtt_fallback()` for fallback to API when MQTT unavailable
  - Primary method: MQTT subscription (real-time)
  - Fallback method: Integration checker (validation only)

### 5. Simplified Integration Checker
- **File**: `services/ha-setup-service/src/integration_checker.py`
- **Changes**:
  - Updated documentation to note it's for validation only
  - Kept for fallback scenarios and validation
  - Not used for primary monitoring (uses MQTT instead)

## Architecture Pattern

Following Epic 31 pattern:
```
MQTT Broker (core-mosquitto:1883)
    ↓
Zigbee2MQTT MQTT Client (subscribe only)
    ↓
Health Monitoring Service
    ↓
Health Dashboard
```

## Benefits

1. **Real-time Updates**: MQTT pub/sub provides immediate updates
2. **Generic Solution**: Works with any Zigbee2MQTT setup
3. **No HA Integration Required**: Direct MQTT connection
4. **Reduced API Calls**: No polling of HA API
5. **Better Performance**: Event-driven instead of polling
6. **Follows Epic 31 Pattern**: Direct MQTT subscription like other external services

## MQTT Topics Subscribed

- `zigbee2mqtt/bridge/state` - Bridge online/offline status
- `zigbee2mqtt/bridge/devices` - Complete device list (retained)
- `zigbee2mqtt/bridge/info` - Bridge information (version, coordinator)
- `zigbee2mqtt/bridge/event` - Bridge events (device_joined, device_leave)

## Configuration

Add to `.env` file (optional - defaults work for most setups):
```env
MQTT_BROKER_URL=mqtt://core-mosquitto:1883
MQTT_USERNAME=addons  # If MQTT requires authentication
MQTT_PASSWORD=your_password
ZIGBEE2MQTT_BASE_TOPIC=zigbee2mqtt
```

## Testing

1. **Verify MQTT Connection**:
   - Check logs for "✅ Successfully connected to MQTT broker"
   - Check logs for "📡 Subscribed to zigbee2mqtt/bridge/..."

2. **Verify Health Monitoring**:
   - Check `/api/health/environment` endpoint
   - Zigbee2MQTT integration should show `monitoring_method: "mqtt_subscription"`

3. **Verify Fallback**:
   - If MQTT unavailable, should fallback to API method
   - Check logs for "MQTT client not available, falling back to integration checker"

## Code Cleanup

### Removed Redundant Code
- Integration checker still exists but is now fallback-only
- Health service uses MQTT as primary method
- No duplicate monitoring logic

### Kept for Validation
- Integration checker kept for:
  - Initial validation
  - Fallback scenarios
  - Setup wizard validation

## Next Steps

1. **Deploy and Test**: Deploy service and verify MQTT connection
2. **Monitor Logs**: Check for successful MQTT subscriptions
3. **Verify Health Endpoint**: Confirm Zigbee2MQTT status via MQTT
4. **Optional**: Add device state monitoring (`zigbee2mqtt/+` topics)

## References

- Epic 31 Architecture Pattern
- Zigbee2MQTT MQTT Topics: https://www.zigbee2mqtt.io/guide/usage/mqtt_topics_and_messages.html
- Implementation follows same pattern as `device-intelligence-service` MQTT client

