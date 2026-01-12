# Zigbee2MQTT UI Investigation - Complete

**Date:** 2026-01-12  
**Status:** Investigation Complete - Code Updated

## Key Finding

From Home Assistant UI investigation via Playwright:

1. **Zigbee2MQTT add-on exists** - Visible in sidebar navigation
2. **MQTT integration exists** - Listed in "Configured" integrations
3. **No "Zigbee2MQTT" integration** - Not in the configured integrations list
4. **Integration name pattern**: Zigbee2MQTT devices in Home Assistant likely use **"mqtt"** as the integration name, not "zigbee2mqtt"

## Code Update

Updated `discovery_service.py` to also check for devices with `integration='mqtt'` but with Zigbee identifiers (containing 'ieee' or 'zigbee').

**Change:**
- Added check for `integration_lower == 'mqtt'`
- For MQTT integration devices, verify they are Zigbee devices by checking identifiers
- Only set `source='zigbee2mqtt'` if identifiers contain 'zigbee' or 'ieee'

## Next Steps

1. Service restarted with updated code
2. Wait for next discovery cycle (or trigger manually)
3. Verify devices with `integration='mqtt'` and Zigbee identifiers now have `source='zigbee2mqtt'`
