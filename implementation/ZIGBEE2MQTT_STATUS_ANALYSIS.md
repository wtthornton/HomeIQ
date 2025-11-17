# Zigbee2MQTT Status Analysis

**Date:** 2025-01-XX  
**Status:** NOT CONFIGURED - Explanation below

## Current Status

Zigbee2MQTT is showing as **"not configured"** in the health dashboard. This is correct based on the current system state.

## Why It's Showing "Not Configured"

The health check uses a two-tier approach (Epic 31 design):

### 1. Primary Method: MQTT Subscription (Preferred)
- **Location**: `health_service._check_zigbee2mqtt_integration()`
- **Method**: Direct MQTT subscription to `zigbee2mqtt/bridge/*` topics
- **Status**: **FAILING** - MQTT client cannot connect

**Why it's failing:**
- The MQTT client requires configuration:
  - `mqtt_broker_url` (default: `mqtt://core-mosquitto:1883`)
  - `mqtt_username` (optional)
  - `mqtt_password` (optional)
  - `zigbee2mqtt_base_topic` (default: `zigbee2mqtt`)
- These settings need to be configured in the ha-setup-service environment variables
- If MQTT connection fails, it falls back to method #2

### 2. Fallback Method: HA API Check
- **Location**: `integration_checker.check_zigbee2mqtt_integration()`
- **Method**: Checks Home Assistant API for Zigbee2MQTT entities
- **Status**: **NOT FOUND** - No Zigbee2MQTT entities detected

**What it checks for:**
- `sensor.zigbee2mqtt_bridge_state` entity
- Any entities starting with `zigbee2mqtt.` prefix

**Why it's not finding anything:**
- Either Zigbee2MQTT addon is not installed in Home Assistant
- Or Zigbee2MQTT is installed but not configured/connected
- Or the entities exist but with different naming (e.g., different integration name)

## The Design is Working Correctly

The Epic 31 design pattern is working as intended:

1. ✅ **Tries MQTT subscription first** (real-time, efficient)
2. ✅ **Falls back to HA API check** (when MQTT unavailable)
3. ✅ **Reports accurate status** ("not configured" is correct)

## What Needs to Be Done

To get Zigbee2MQTT showing as "healthy", you need to:

### Option 1: Configure MQTT Connection (Recommended)
1. **Configure MQTT broker settings** in ha-setup-service:
   - Set `MQTT_BROKER_URL` environment variable (e.g., `mqtt://192.168.1.100:1883`)
   - Set `MQTT_USERNAME` if required
   - Set `MQTT_PASSWORD` if required
   - Set `ZIGBEE2MQTT_BASE_TOPIC` (default is `zigbee2mqtt`)

2. **Restart ha-setup-service** to apply settings

3. **Verify MQTT connection** - The service will then subscribe to Zigbee2MQTT topics directly

### Option 2: Install/Configure Zigbee2MQTT in Home Assistant
1. **Install Zigbee2MQTT addon** in Home Assistant
2. **Configure MQTT integration** in Home Assistant
3. **Connect Zigbee2MQTT to MQTT broker**
4. **Verify entities are created** - Should see `sensor.zigbee2mqtt_bridge_state` and `zigbee2mqtt.*` entities

## Code References

- **MQTT Client**: `services/ha-setup-service/src/zigbee2mqtt_mqtt_client.py`
- **Health Check**: `services/ha-setup-service/src/health_service.py:272-341`
- **Fallback Check**: `services/ha-setup-service/src/integration_checker.py:303-402`
- **Configuration**: `services/ha-setup-service/src/config.py:29-33`

## Summary

**The system is working correctly** - it's accurately reporting that Zigbee2MQTT is not configured. The health check:
- ✅ Tries the preferred MQTT subscription method
- ✅ Falls back to HA API check when MQTT unavailable
- ✅ Correctly identifies that Zigbee2MQTT is not installed/configured

To fix: Configure MQTT broker settings OR install/configure Zigbee2MQTT in Home Assistant.

