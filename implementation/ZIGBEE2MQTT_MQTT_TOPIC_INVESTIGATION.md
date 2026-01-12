# Zigbee2MQTT MQTT Topic Investigation

**Date:** 2026-01-12  
**Issue:** Service requests device list but receives 0 devices

## Current Implementation

Service uses:
- Request topic: `zigbee2mqtt/bridge/request/device/list`
- Response topic: `zigbee2mqtt/bridge/response/device/list`
- Retained topic: `zigbee2mqtt/bridge/devices`

## Potential Issue

Found in archived code (`services/archive/2025-q4/ai-automation-service/src/device_intelligence/capability_batch.py`):
- Uses: `zigbee2mqtt/bridge/request/devices` (different format!)

This suggests the topic format might be:
- `zigbee2mqtt/bridge/request/devices` (plural, no `/list`)
- Instead of: `zigbee2mqtt/bridge/request/device/list`

## Next Steps

1. Check Zigbee2MQTT documentation for correct API format
2. Test with alternative topic format
3. Verify if Zigbee2MQTT version uses different API
