# Zigbee2MQTT Device Discovery - Action Plan

**Date:** 2026-01-12  
**Status:** Research Complete - Action Plan Created  
**Zigbee2MQTT Version:** 2.7.2

## Research Findings

### ✅ Confirmed Working
- Base topic matches: `zigbee2mqtt` ✅
- Zigbee2MQTT operational: 6 devices connected ✅
- MQTT connection established ✅
- Service event loop fix applied ✅
- Service subscribed to correct topics ✅

### ❌ Issues Identified
- Service not receiving device list messages
- `bridge/devices` topic may not be published by Zigbee2MQTT
- Request/response pattern may not work as expected

## Action Plan

### Phase 1: Verify bridge/devices Topic Exists (HIGH PRIORITY)

**Objective**: Confirm if Zigbee2MQTT publishes to `zigbee2mqtt/bridge/devices`

**Steps**:
1. **Check Zigbee2MQTT Logs**
   - Filter logs for: `bridge/devices`
   - Check startup logs (when Zigbee2MQTT first started)
   - Look for any mentions of device list publishing

2. **Test MQTT Subscription Directly**
   - Use MQTT client (mosquitto_sub if available) to subscribe:
     ```bash
     mosquitto_sub -h 192.168.1.86 -p 1883 -t "zigbee2mqtt/bridge/devices" -v
     ```
   - Check if retained message exists
   - Verify message format if received

3. **Check Zigbee2MQTT Documentation**
   - Review Zigbee2MQTT 2.7.2 API documentation
   - Verify if `bridge/devices` is still supported
   - Check for API changes in recent versions

**Expected Outcome**: 
- If topic exists: Verify message format and fix parsing if needed
- If topic doesn't exist: Move to Phase 2 (Alternative approaches)

---

### Phase 2: Alternative Approaches (IF Phase 1 Fails)

**Option A: Use Zigbee2MQTT HTTP API** (PREFERRED if available)

**Research Required**:
- Check if Zigbee2MQTT 2.7.2 exposes HTTP API
- Verify endpoint for device list (e.g., `/api/devices`)
- Check authentication requirements

**Implementation**:
- Add HTTP client to device-intelligence-service
- Query device list via HTTP instead of MQTT
- Integrate with existing discovery flow

**Option B: Query via Home Assistant API** (FALLBACK)

**Research Required**:
- Verify if Zigbee devices are in Home Assistant device registry
- Check HA API endpoint for devices
- Confirm integration field would be set correctly

**Implementation**:
- Query HA device registry for devices with Zigbee integration
- Filter by integration type
- Merge with existing device discovery

**Option C: Use Different MQTT Topic Pattern**

**Research Required**:
- Check if Zigbee2MQTT uses different topic format
- Verify if device list is published to device-specific topics
- Check if we need to subscribe to all device topics and aggregate

**Implementation**:
- Modify subscription pattern
- Aggregate device data from multiple topics
- Update message parsing logic

---

### Phase 3: Debug Current Implementation (ONGOING)

**Steps**:
1. **Add Enhanced Logging**
   - Log all MQTT messages received (even unhandled ones)
   - Log topic names and payload sizes
   - Verify message handler is being called

2. **Verify MQTT Connection**
   - Confirm service is actually connected to broker
   - Verify subscriptions are active
   - Check if messages are being received but not processed

3. **Test Request/Response Pattern**
   - Manually publish to `zigbee2mqtt/bridge/request/device/list`
   - Watch Zigbee2MQTT logs for response
   - Check if response is published to expected topic

---

### Phase 4: Implementation and Testing

**After identifying solution**:

1. **Implement Fix**
   - Update code based on chosen approach
   - Ensure error handling and logging
   - Maintain backward compatibility if possible

2. **Test**
   - Verify devices are received
   - Check database for `source='zigbee2mqtt'` devices
   - Verify all 6 Zigbee devices appear

3. **Monitor**
   - Watch logs for errors
   - Verify devices stay in sync
   - Check dashboard for Zigbee devices

---

## Recommended Next Steps (IMMEDIATE)

1. **Priority 1**: Check Zigbee2MQTT logs for `bridge/devices`
   - This will tell us if the topic exists
   - Quickest way to determine next action

2. **Priority 2**: Research Zigbee2MQTT HTTP API
   - May be more reliable than MQTT bridge topics
   - Could be cleaner solution

3. **Priority 3**: Add debug logging to service
   - Log all received MQTT messages
   - Verify messages are being received

## Decision Matrix

| Scenario | Solution |
|----------|----------|
| `bridge/devices` exists in logs | Fix message parsing/format |
| `bridge/devices` doesn't exist | Use HTTP API or HA API |
| Messages received but not processed | Fix message handler |
| Request/response pattern doesn't work | Use HTTP API |

## Success Criteria

- ✅ 6 Zigbee devices appear in database with `source='zigbee2mqtt'`
- ✅ Devices visible in dashboard
- ✅ Device data includes LQI, battery, availability status
- ✅ Devices stay in sync with Zigbee2MQTT
