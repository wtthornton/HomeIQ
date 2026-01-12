# Zigbee2MQTT API Research - Final Summary

**Date:** 2026-01-12  
**Research Methods**: Web search, code analysis, Context7 (rate-limited)  
**Status**: Research Complete - Ready for Implementation

## Key Findings

### ✅ Service Implementation is CORRECT

**Subscription Pattern** (from code analysis):
```python
# Service subscribes to:
- {base_topic}/bridge/devices          # Retained device list (expected on startup)
- {base_topic}/bridge/groups           # Retained group list
- {base_topic}/bridge/info             # Bridge information
- {base_topic}/bridge/networkmap       # Network topology
- {base_topic}/bridge/response/device/list   # Response to request
- {base_topic}/bridge/response/group/list    # Response to request
```

**Request Pattern** (from code analysis):
```python
# Service publishes to:
- {base_topic}/bridge/request/device/list    # Request device list
- {base_topic}/bridge/request/group/list     # Request group list
```

**Expected Message Format** (from code):
- Array of device objects: `[{"ieee_address": "...", "friendly_name": "...", ...}]`
- Fields expected: `ieee_address`, `friendly_name`, `model`, `manufacturer`, `lqi`, `battery`, `availability`, etc.

### 📚 Official Documentation Findings (Web Research)

**From zigbee2mqtt.io documentation:**
1. ✅ `bridge/devices` topic SHOULD exist
2. ✅ Should be published as **retained message**
3. ✅ Typically published on **startup**
4. ✅ Format: Array of device objects

**Known Issues (GitHub):**
- Some users report `bridge/devices` not being published
- Retained message not always set
- Timing issues (service subscribes after message published)

### 🔍 Root Cause Hypothesis

Based on research and current status:

**Most Likely Causes:**
1. **Timing Issue**: Service subscribed AFTER `bridge/devices` was published (not retained)
2. **Retained Message Not Set**: Zigbee2MQTT not publishing as retained message
3. **Topic Not Published**: Zigbee2MQTT 2.7.2 may have bug or configuration issue
4. **Request/Response Pattern**: Service requests but Zigbee2MQTT doesn't respond to `bridge/request/device/list`

### ✅ Verified Working
- Base topic matches: `zigbee2mqtt` ✅
- Service subscribed correctly ✅
- Event loop fixed (no errors) ✅
- Service requests device list every 5 minutes ✅

### ❌ Still Unknown
- Does `bridge/devices` topic actually exist in Zigbee2MQTT logs?
- Is it published as retained message?
- Does request/response pattern work?

## Recommended Next Steps (Priority Order)

### Step 1: Check Zigbee2MQTT Logs (5 minutes) ⭐ HIGHEST PRIORITY
**Action**: In Zigbee2MQTT → Logs, filter for `bridge/devices`
**Expected Results**:
- If found: Topic exists, check timestamp (startup only?)
- If not found: Topic not published, move to Step 2

### Step 2: Test MQTT Subscription Directly (10 minutes)
**Action**: Use MQTT client to subscribe to `zigbee2mqtt/bridge/devices`
**Command**: `mosquitto_sub -h 192.168.1.86 -p 1883 -t "zigbee2mqtt/bridge/devices" -v`
**Expected Results**:
- If message received: Topic exists, check if retained
- If no message: Topic not published or not retained

### Step 3: Test Request/Response Pattern (5 minutes)
**Action**: Watch Zigbee2MQTT logs when service publishes request
**Expected Results**:
- Check if Zigbee2MQTT responds to `bridge/request/device/list`
- Look for `bridge/response/device/list` in logs

### Step 4: Research HTTP API (15 minutes)
**Action**: Check if Zigbee2MQTT 2.7.2 exposes HTTP API
**Expected Results**:
- If available: Cleaner solution than MQTT
- If not available: Move to Step 5

### Step 5: Use Home Assistant API (Fallback)
**Action**: Query HA device registry for Zigbee devices
**Expected Results**:
- Devices should have integration field set
- May not have all Zigbee2MQTT-specific fields (LQI, etc.)

## Decision Matrix

| Scenario | Solution |
|----------|----------|
| `bridge/devices` found in logs | Check if retained, verify message format |
| `bridge/devices` not found in logs | Use HTTP API or HA API fallback |
| Request/response doesn't work | Use HTTP API instead |
| Topic exists but not retained | Request manually or use HTTP API |
| HTTP API available | Implement HTTP client (preferred) |

## Implementation Notes

### If HTTP API Available:
1. Add HTTP client to device-intelligence-service
2. Query endpoint (e.g., `http://192.168.1.86:8123/api/zigbee2mqtt/devices`)
3. Parse JSON response (should match MQTT format)
4. Integrate with existing discovery flow

### If Using HA API:
1. Query HA device registry
2. Filter by integration (`zigbee2mqtt` or similar)
3. Merge with existing device discovery
4. Note: May not have LQI, battery, etc. fields

## Success Criteria

- ✅ 6 Zigbee devices in database with `source='zigbee2mqtt'`
- ✅ Devices visible in dashboard
- ✅ Device metadata includes: LQI, battery, availability, IEEE address
- ✅ Devices stay in sync (real-time or periodic updates)

## References

- **Official Documentation**: https://www.zigbee2mqtt.io/guide/usage/mqtt_topics_and_messages.html
- **GitHub Issues**: 
  - #24420: bridge/devices not retained
  - #15299: Devices disappearing from list
- **Service Code**: `services/device-intelligence-service/src/clients/mqtt_client.py`

## Next Immediate Action

**CHECK ZIGBEE2MQTT LOGS FOR `bridge/devices`** - This will determine which solution path to take.
