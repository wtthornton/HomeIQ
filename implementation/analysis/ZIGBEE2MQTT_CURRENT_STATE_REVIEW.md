# Zigbee2MQTT Device Capture - Current State Review

**Date:** January 16, 2026  
**Status:** Comprehensive Review Complete  
**Issue:** Zigbee2MQTT devices not being captured in HomeIQ

## Executive Summary

After reviewing the codebase and documentation, the issue has been extensively researched and several fixes have been applied, but **Zigbee2MQTT devices are still not appearing in the dashboard**. The root causes are:

1. **Integration field fix exists** but devices may need rediscovery
2. **Multiple services involved** (websocket-ingestion, data-api, device-intelligence-service)
3. **Unclear current state** - need to verify if devices exist in Home Assistant
4. **Dashboard shows 104 devices** but none identified as Zigbee2MQTT

## Current Architecture

### Device Discovery Flow

```
Home Assistant Device Registry
    ↓ (via websocket-ingestion)
    - Discovers devices via WebSocket API
    - Resolves integration from config_entries
    - Stores via data-api bulk_upsert
    ↓
data-api (SQLite: metadata.db)
    - Stores devices with integration field
    - Query endpoint: GET /api/devices?integration=zigbee2mqtt
    ↓
health-dashboard (Port 3000)
    - Displays devices
    - Filters by integration
```

### Key Services

1. **websocket-ingestion** (Port 8001)
   - **Purpose:** Discovers devices from Home Assistant device registry
   - **Status:** ✅ Fix exists for integration field resolution
   - **Fix Location:** `services/websocket-ingestion/src/discovery_service.py:667-690`
   - **Issue:** Devices may have been stored before fix, or discovery hasn't run since fix

2. **data-api** (Port 8006)
   - **Purpose:** Stores devices in SQLite database
   - **Status:** ✅ Schema supports integration field
   - **Issue:** All devices have `integration=null` in database

3. **device-intelligence-service** (Port 8028)
   - **Purpose:** Stores Zigbee2MQTT devices with exposes/capabilities (via MQTT)
   - **Status:** ❌ 0 devices stored
   - **Issue:** MQTT messages not being received or processed

## Root Cause Analysis

### Issue 1: Integration Field Not Populated ✅ FIX EXISTS

**Status:** Code fix exists but needs verification

**Fix Applied:**
- **File:** `services/websocket-ingestion/src/discovery_service.py`
- **Lines:** 667-690
- **What it does:**
  1. Discovers config entries from Home Assistant
  2. Builds mapping: `config_entry_id` → `integration domain`
  3. Resolves integration field for each device from its config_entries array

**Code Evidence:**
```python
# Build config_entry_id -> integration domain mapping
config_entry_map: dict[str, str] = {}
if config_entries_data:
    for entry in config_entries_data:
        entry_id = entry.get("entry_id")
        domain = entry.get("domain")
        if entry_id and domain:
            config_entry_map[entry_id] = domain
    logger.info(f"🔧 Built config entry mapping: {len(config_entry_map)} entries")

# Resolve integration field for devices from config_entries
if devices_data and config_entry_map:
    for device in devices_data:
        if "integration" not in device or not device.get("integration"):
            config_entries = device.get("config_entries", [])
            if config_entries:
                first_entry_id = config_entries[0]
                integration = config_entry_map.get(first_entry_id)
                if integration:
                    device["integration"] = integration
```

**Why Devices Still Show NULL:**
1. Devices were stored **before** the fix was applied
2. Discovery hasn't run **since** the fix was applied
3. Fix requires WebSocket connection (line 521: `if websocket else []`)
4. Config entries discovery may not be working

**Action Required:** 
- ✅ Verify fix is in code (confirmed)
- ⏳ Trigger device rediscovery
- ⏳ Verify integration field is populated in database
- ⏳ Check logs for integration resolution messages

### Issue 2: Zigbee2MQTT Devices May Not Exist in Home Assistant

**Status:** Needs Verification

**Evidence:**
- Dashboard shows 104 devices total
- Previous analysis (2026-01-12) showed 101 devices, none with `integration='zigbee2mqtt'`
- No devices with `integration='mqtt'` or containing 'zigbee'

**Possible Scenarios:**
1. **Zigbee2MQTT integration not installed** in Home Assistant
2. **Zigbee devices not paired** with Zigbee2MQTT
3. **Integration name mismatch** - devices exist but integration field not set correctly
4. **Devices exist but different integration** (e.g., 'mqtt' instead of 'zigbee2mqtt')

**Action Required:**
- ⏳ Query Home Assistant device registry directly
- ⏳ Check if Zigbee2MQTT add-on is installed and running
- ⏳ Verify devices are paired in Zigbee2MQTT UI
- ⏳ Check device identifiers for IEEE addresses

### Issue 3: device-intelligence-service Not Storing Devices

**Status:** Separate Issue (MQTT-based, not required for basic device capture)

**Current State:**
- ✅ Service running and healthy
- ✅ MQTT connection established
- ❌ 0 devices stored
- ❌ No MQTT messages received

**Note:** This service is for **enhanced Zigbee2MQTT data** (LQI, battery, exposes). The primary device capture should work via websocket-ingestion → data-api.

**Action Required:**
- ⏳ Verify MQTT topics are being published by Zigbee2MQTT
- ⏳ Check service logs for MQTT message reception
- ⏳ This is a separate issue from basic device capture

## Documentation Review

### Previous Analysis Documents

1. **ZIGBEE2MQTT_DEVICES_MISSING_RESEARCH.md** (2026-01-08)
   - Initial research finding multiple issues
   - Database schema mismatch identified
   - Integration field issue documented

2. **ZIGBEE2MQTT_DEVICES_FIX.md** (2026-01-08)
   - Integration field fix documented
   - Code changes explained
   - Verification steps provided

3. **ZIGBEE2MQTT_COMPREHENSIVE_SOLUTIONS.md** (2026-01-12)
   - Multiple solution options analyzed
   - Recommended solution: Set source from HA integration
   - Focus on device-intelligence-service

4. **ZIGBEE2MQTT_REVIEW.md** (2026-01-12)
   - Review showing 0 Zigbee devices found
   - 101 devices discovered, none with zigbee integration
   - MQTT not receiving messages

5. **ZIGBEE2MQTT_FINAL_STATUS.md** (2026-01-12)
   - Database schema fix applied
   - MQTT event loop fix applied
   - Verification pending

### Key Findings from Documentation

- ✅ Integration field fix code exists and is correct
- ✅ Database schema supports integration field
- ❌ Devices still have `integration=null` in database
- ❌ No Zigbee devices found in previous reviews
- ⚠️ Multiple fixes applied but verification incomplete

## Current State Assessment

### What We Know ✅

1. **Code fixes exist:**
   - Integration field resolution in websocket-ingestion
   - Database schema supports integration field
   - device-intelligence-service has logic to identify Zigbee devices

2. **Services are running:**
   - websocket-ingestion: Running (periodic discovery every 30 minutes)
   - data-api: Running (104 devices stored)
   - device-intelligence-service: Running (0 devices stored)

3. **Dashboard shows devices:**
   - 104 devices total
   - Integration filter shows 0 integrations (all null)

### What We Don't Know ❓

1. **Are Zigbee2MQTT devices in Home Assistant?**
   - Need to query HA device registry directly
   - Check if Zigbee2MQTT add-on is installed
   - Verify devices are paired

2. **Is integration field fix working?**
   - Need to check logs for integration resolution
   - Verify config entries discovery is working
   - Check if devices are being rediscovered

3. **What is the current database state?**
   - How many devices have `integration=null`?
   - Are there any devices with `integration='zigbee2mqtt'`?
   - When was the last discovery run?

## Next Steps - Diagnostic Plan

### Step 1: Verify Home Assistant Device Registry (CRITICAL)

**Purpose:** Confirm Zigbee2MQTT devices exist in Home Assistant

**Actions:**
1. Query HA device registry via API
2. Check for devices with Zigbee2MQTT integration
3. Verify Zigbee2MQTT add-on is installed and running
4. Check Zigbee2MQTT UI for paired devices

**Commands:**
```powershell
# Query HA device registry
$haUrl = "http://192.168.1.86:8123"
$haToken = $env:HA_TOKEN
$headers = @{Authorization="Bearer $haToken"}

$devices = Invoke-RestMethod -Uri "$haUrl/api/config/device_registry/list" -Headers $headers

# Filter for potential Zigbee devices
$zigbeeDevices = $devices | Where-Object {
    $_.config_entries -or
    ($_.name -match "Office|Bar|Light|Sensor|Switch")
}

Write-Host "Total devices: $($devices.Count)"
Write-Host "Potential Zigbee devices: $($zigbeeDevices.Count)"
```

### Step 2: Check websocket-ingestion Logs

**Purpose:** Verify integration field fix is working

**Actions:**
1. Check logs for integration resolution messages
2. Verify config entries discovery is working
3. Check when last discovery ran
4. Look for errors in discovery process

**Commands:**
```powershell
# Check logs for integration resolution
docker compose logs websocket-ingestion --tail 500 | Select-String -Pattern "integration|config_entry|Built config entry mapping|Resolved integration"

# Check last discovery time
docker compose logs websocket-ingestion --tail 100 | Select-String -Pattern "DISCOVERY|Starting.*discovery"
```

### Step 3: Verify Database State

**Purpose:** Check current state of integration field in database

**Actions:**
1. Query database for devices with null integration
2. Check if any devices have integration='zigbee2mqtt'
3. Check when devices were last updated
4. Verify integration field is being populated

**Commands:**
```powershell
# Query data-api for devices
$response = Invoke-RestMethod -Uri "http://localhost:8006/api/devices?limit=200"

# Check integration field distribution
$response.devices | Group-Object integration | Select-Object Name, Count | Sort-Object Count -Descending

# Check for Zigbee devices
$zigbee = $response.devices | Where-Object { 
    $_.integration -eq 'zigbee2mqtt' -or 
    $_.integration -eq 'mqtt' -or
    ($_.integration -and $_.integration -match 'zigbee')
}
Write-Host "Zigbee devices: $($zigbee.Count)"
```

### Step 4: Trigger Device Rediscovery (If Needed)

**Purpose:** Force rediscovery to populate integration field

**Actions:**
1. Restart websocket-ingestion service (triggers discovery)
2. OR trigger discovery manually via API (if available)
3. Monitor logs for integration resolution
4. Verify database is updated

**Commands:**
```powershell
# Restart service to trigger discovery
docker compose restart websocket-ingestion

# Monitor logs
docker compose logs websocket-ingestion --tail 100 --follow
```

### Step 5: Verify Dashboard (After Fixes)

**Purpose:** Confirm Zigbee devices appear in dashboard

**Actions:**
1. Check dashboard device count
2. Filter by integration='zigbee2mqtt'
3. Verify devices are displayed correctly
4. Check device details show integration

## Recommended Action Plan

### Immediate Actions (Today)

1. ✅ **Verify Zigbee2MQTT is installed** in Home Assistant
   - Check HA Settings → Add-ons
   - Verify Zigbee2MQTT add-on is installed and running
   - Check Zigbee2MQTT UI for paired devices

2. ✅ **Query Home Assistant device registry**
   - Use API to check for Zigbee devices
   - Look for devices with config_entries related to Zigbee2MQTT
   - Verify devices exist in HA

3. ✅ **Check websocket-ingestion logs**
   - Look for integration resolution messages
   - Verify config entries discovery is working
   - Check for errors

4. ✅ **Verify database state**
   - Query data-api for current devices
   - Check integration field distribution
   - Verify if any devices have integration populated

### If Zigbee Devices Exist in HA

5. ✅ **Trigger device rediscovery**
   - Restart websocket-ingestion
   - Monitor logs for integration resolution
   - Verify database is updated

6. ✅ **Verify dashboard**
   - Check if Zigbee devices appear
   - Test integration filter
   - Verify device details

### If Zigbee Devices Don't Exist in HA

7. ✅ **Install/Configure Zigbee2MQTT**
   - Install Zigbee2MQTT add-on
   - Configure MQTT connection
   - Pair Zigbee devices

8. ✅ **Wait for device discovery**
   - Devices should appear after pairing
   - Integration field should be populated automatically

## Related Files

- **Code Files:**
  - `services/websocket-ingestion/src/discovery_service.py` - Integration field fix
  - `services/data-api/src/devices_endpoints.py` - Device storage endpoint
  - `services/device-intelligence-service/src/core/discovery_service.py` - Zigbee device identification

- **Documentation:**
  - `implementation/analysis/ZIGBEE2MQTT_DEVICES_MISSING_RESEARCH.md`
  - `implementation/analysis/ZIGBEE2MQTT_DEVICES_FIX.md`
  - `implementation/ZIGBEE2MQTT_COMPREHENSIVE_SOLUTIONS.md`
  - `implementation/analysis/ZIGBEE2MQTT_REVIEW.md`

## Conclusion

The integration field fix exists in the codebase and should work correctly. The primary next step is to:

1. **Verify Zigbee2MQTT devices exist in Home Assistant**
2. **Check if integration field fix is working** (check logs)
3. **Trigger rediscovery if needed** (restart service)
4. **Verify database is updated** (query data-api)

The issue is likely one of:
- Zigbee devices don't exist in HA (need to install/configure Zigbee2MQTT)
- Devices exist but integration field hasn't been populated (need rediscovery)
- Integration field fix isn't working (need to debug logs)
