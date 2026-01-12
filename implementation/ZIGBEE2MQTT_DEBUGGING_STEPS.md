# Zigbee2MQTT Debugging Steps

**Date:** 2026-01-12  
**Status:** Base Topic Verified - Testing MQTT Topics

## Confirmed
- ✅ Base topic matches: `zigbee2mqtt`
- ✅ Zigbee2MQTT working (6 devices)
- ✅ Our service subscribes to correct topics
- ✅ Event loop fix applied (no errors)

## Next: Verify bridge/devices Topic

### Option 1: Check Zigbee2MQTT Logs
1. Go to Zigbee2MQTT → Logs
2. Filter/search for: `bridge/devices`
3. Check if this topic appears (especially on startup)

### Option 2: Test MQTT Directly
If you have mosquitto_sub available:
```bash
mosquitto_sub -h 192.168.1.86 -p 1883 -t "zigbee2mqtt/bridge/devices" -v
```

This will show if a retained message exists on that topic.

### Option 3: Check Zigbee2MQTT Documentation
- Verify if Zigbee2MQTT 2.7.2 publishes to `bridge/devices`
- Check if API changed in recent versions
- See if HTTP API is available as alternative

### Option 4: Restart Zigbee2MQTT and Watch Logs
1. Restart Zigbee2MQTT add-on
2. Watch logs immediately after restart
3. Look for `bridge/devices` being published on startup

## Expected Behavior

If `bridge/devices` exists:
- Should be published as **retained message** on startup
- Should contain array of device objects
- Our service should receive it when subscribing

If `bridge/devices` doesn't exist:
- May need to use HTTP API instead
- Or use different topic pattern
- Or check Zigbee2MQTT version-specific changes
