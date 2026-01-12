# Zigbee2MQTT Device Discovery - Comprehensive Plan

**Date:** 2026-01-12  
**Created with**: tapps-agents research and planning tools  
**Status**: Ready for Implementation

## Executive Summary

**Problem**: Service subscribes to `zigbee2mqtt/bridge/devices` but receives 0 devices despite Zigbee2MQTT having 6 devices online.

**Root Cause Analysis**:
- ✅ Base topic matches (`zigbee2mqtt`)
- ✅ Event loop fixed (no errors)
- ✅ Service subscribed correctly
- ❓ `bridge/devices` topic may not be published by Zigbee2MQTT 2.7.2
- ❓ Request/response pattern may not work

**Solution Strategy**: Multi-phase approach with fallback options

---

## Phase 1: Verification (IMMEDIATE)

### Step 1.1: Check Zigbee2MQTT Logs
**Action**: In Zigbee2MQTT → Logs, filter for `bridge/devices`
**Expected**: See if topic is published (especially on startup)
**Time**: 2 minutes

### Step 1.2: Test MQTT Subscription
**Action**: Use mosquitto_sub to subscribe to `zigbee2mqtt/bridge/devices`
**Command**: `mosquitto_sub -h 192.168.1.86 -p 1883 -t "zigbee2mqtt/bridge/devices" -v`
**Expected**: See if retained message exists
**Time**: 5 minutes

### Step 1.3: Verify Request/Response
**Action**: Watch Zigbee2MQTT logs when service requests device list
**Expected**: See if Zigbee2MQTT responds to `bridge/request/device/list`
**Time**: 2 minutes

**Decision Point**: 
- If `bridge/devices` exists → Fix message parsing
- If `bridge/devices` doesn't exist → Move to Phase 2

---

## Phase 2: Alternative Approaches

### Option 2A: Zigbee2MQTT HTTP API (PREFERRED)

**Research Needed**:
- Does Zigbee2MQTT 2.7.2 expose HTTP API?
- What endpoint for device list? (e.g., `http://192.168.1.86:8123/api/zigbee2mqtt/devices`)
- Authentication required?

**Implementation Steps**:
1. Add HTTP client to device-intelligence-service
2. Query device list endpoint
3. Parse JSON response (should match MQTT format)
4. Integrate with existing discovery flow

**Pros**:
- More reliable than MQTT topics
- Easier to debug (HTTP requests/responses)
- No async event loop issues

**Cons**:
- Requires HTTP endpoint availability
- May need authentication
- Polling instead of real-time updates

### Option 2B: Home Assistant Device Registry (FALLBACK)

**Research Needed**:
- Are Zigbee devices in HA device registry?
- What integration field do they have? (`zigbee2mqtt`?)
- Can we filter by integration type?

**Implementation Steps**:
1. Query HA device registry API
2. Filter devices with `integration='zigbee2mqtt'` or similar
3. Merge with existing device discovery
4. Map HA device data to our format

**Pros**:
- Already querying HA for devices
- Integration field should be set
- Real-time via WebSocket updates

**Cons**:
- Depends on HA integration
- May not have all Zigbee2MQTT-specific fields (LQI, etc.)
- Less direct than Zigbee2MQTT API

---

## Phase 3: Enhanced Debugging (ONGOING)

### Add Comprehensive Logging

**Changes Needed**:
1. Log all MQTT messages received (even unhandled)
2. Log topic names and payload sizes
3. Add debug mode for MQTT message flow

**File**: `services/device-intelligence-service/src/clients/mqtt_client.py`

**Code Addition**:
```python
def _on_message(self, client, userdata, msg):
    """MQTT message callback."""
    logger.debug(f"📨 MQTT message received: topic={msg.topic}, payload_size={len(msg.payload)}")
    # ... existing code
```

### Verify MQTT Connection State

**Checks**:
1. Confirm service is actually connected
2. Verify subscriptions are active
3. Check broker connection status

---

## Phase 4: Implementation Priority

### Priority 1: Verify bridge/devices Topic
- **Why**: Quickest way to determine if MQTT approach will work
- **Action**: Check Zigbee2MQTT logs
- **Time**: 5 minutes

### Priority 2: Research HTTP API
- **Why**: May be cleaner solution than MQTT
- **Action**: Check Zigbee2MQTT documentation/API
- **Time**: 15 minutes

### Priority 3: Implement Solution
- **Why**: Get devices working
- **Action**: Implement chosen approach
- **Time**: 1-2 hours

---

## Success Metrics

- ✅ 6 Zigbee devices in database with `source='zigbee2mqtt'`
- ✅ Devices visible in dashboard
- ✅ Device metadata includes: LQI, battery, availability, IEEE address
- ✅ Devices stay in sync (real-time or periodic updates)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| bridge/devices not published | High | High | Use HTTP API or HA API fallback |
| HTTP API not available | Medium | Medium | Use HA API or device-specific topics |
| Performance issues | Low | Low | Use async HTTP client, caching |

## Timeline Estimate

- **Phase 1 (Verification)**: 10 minutes
- **Phase 2 (Research)**: 30 minutes
- **Phase 3 (Implementation)**: 1-2 hours
- **Phase 4 (Testing)**: 30 minutes
- **Total**: 2-3 hours

## Next Immediate Action

**Check Zigbee2MQTT logs for `bridge/devices`** - This will determine which path to take.
