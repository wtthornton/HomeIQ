# Zigbee2MQTT Devices Missing from HomeIQ Database - Research Findings

**Date:** January 8, 2026  
**Issue:** Zigbee2MQTT devices visible in Zigbee2MQTT UI but not stored in HomeIQ database with exposes/capabilities

## Executive Summary

Zigbee2MQTT devices are **not being stored** in HomeIQ's database, and their **exposes settings (capabilities)** are not being captured. The root causes are:

1. **Two Separate Systems**: Zigbee2MQTT bridge maintains its own device list separate from Home Assistant's device registry
2. **Device-Intelligence-Service Not Populated**: The service designed to store Zigbee2MQTT devices has 0 devices stored
3. **Data-API Stores Only HA Devices**: data-api only stores devices from Home Assistant's device registry (via websocket-ingestion), not directly from Zigbee2MQTT
4. **Integration Field Issue**: Even devices in HA registry have `integration=null` in data-api database

## Current Architecture

### Data Flow for Devices

```
Zigbee2MQTT Bridge (MQTT)
    ↓
Home Assistant Device Registry
    ↓ (via websocket-ingestion)
data-api (SQLite: metadata.db)
    ↓
HomeIQ Dashboard

Zigbee2MQTT Bridge (MQTT)
    ↓ (via MQTT client)
device-intelligence-service (SQLite: device_intelligence.db)
    ↓ (currently empty - 0 devices)
```

### Key Services

1. **websocket-ingestion** (Port 8001)
   - Discovers devices from Home Assistant device registry
   - Stores via `POST /internal/devices/bulk_upsert` to data-api
   - **Issue**: Integration field was null (fix applied, but devices still show null)

2. **data-api** (Port 8006)
   - Stores devices in SQLite (`data/metadata.db`)
   - **Current State**: 100 devices stored, but ALL have `integration=null`
   - Devices query: `GET /api/devices?integration=zigbee2mqtt` returns 0 results

3. **device-intelligence-service** (Port 8028)
   - Designed to store Zigbee2MQTT devices with exposes/capabilities
   - Uses MQTT to subscribe to Zigbee2MQTT topics
   - **Current State**: 0 devices stored
   - Health check shows MQTT connected, but no devices discovered

## Root Cause Analysis

### Issue 0: Database Schema Mismatch in device-intelligence-service ⚠️ CRITICAL

**Status:** **CRITICAL BLOCKER** - Database schema missing columns

**Evidence from Logs:**
```
ERROR: Error retrieving devices: (sqlite3.OperationalError) no such column: devices.lqi
[SQL: SELECT devices.id, devices.name, ..., devices.lqi, devices.lqi_updated_at, ...]
```

**Root Cause:**
- Code expects columns: `lqi`, `lqi_updated_at`, `availability_status`, `availability_updated_at`, `battery_level`, `battery_low`, `battery_updated_at`
- Database schema doesn't have these columns
- Alembic migrations haven't been run or are out of sync

**Impact:**
- **Service cannot retrieve devices** - SQL queries fail
- **Service cannot store devices** - Insert queries would also fail
- This explains why 0 devices are stored

**Fix Required:**
1. Run migration script to add Zigbee2MQTT columns
2. Verify schema matches code expectations
3. Re-test device storage and retrieval

**Action:**
```bash
cd services/device-intelligence-service
python scripts/migrate_add_zigbee_fields.py
```

**Note:** The service uses manual migrations (Python script), not Alembic. The migration script adds:
- `lqi`, `lqi_updated_at`
- `availability_status`, `availability_updated_at`
- `battery_level`, `battery_low`, `battery_updated_at`
- `device_type`, `source`
- Creates `zigbee_device_metadata` table

### Issue 1: Integration Field Not Set in data-api

**Status:** Partially Fixed (code fix exists, but data not refreshed)

**Evidence:**
- Fix document: `implementation/analysis/ZIGBEE2MQTT_DEVICES_FIX.md`
- Code fix in `services/websocket-ingestion/src/discovery_service.py`
- All devices in database have `integration=null`

**Root Cause:**
- Home Assistant device registry doesn't provide `integration` field directly
- Requires mapping from `config_entries` → integration domain
- Code fix exists but devices were stored before fix, or discovery hasn't run since fix

**Fix Applied:**
- Enabled config entries discovery
- Built config entry → integration mapping
- Resolves integration from device's config_entries array

**Action Required:**
- Re-run device discovery (restart websocket-ingestion or trigger discovery)
- Verify integration field is populated for new discoveries

### Issue 2: Zigbee2MQTT Devices Not in Home Assistant Device Registry

**Status:** Unknown - Needs Verification

**Evidence from Screenshots:**
- Zigbee2MQTT UI shows 6 devices:
  - Office Light Switch
  - Bar Light Switch
  - Office FP300 Sensor
  - Bar PF300 Sensor
  - Office 4 Button Switch
  - Office Fan Switch

**Question:** Are these devices also in Home Assistant's device registry?

**Possible Scenarios:**
1. Devices ARE in HA registry but integration field not set (Issue 1)
2. Devices are NOT in HA registry (Zigbee2MQTT add-on UI only)
3. Devices in HA registry but with different names/identifiers

**Action Required:**
- Query Home Assistant device registry directly to verify
- Check if Zigbee2MQTT devices appear in HA device registry
- Verify device identifiers match between systems

### Issue 3: device-intelligence-service Not Storing Devices

**Status:** Critical - Service Running But Empty

**Evidence:**
- Service health: ✅ Healthy, MQTT connected
- Device count: 0 devices stored
- Database: `device_intelligence.db` exists but empty

**Root Cause:**
- Service uses MQTT subscription to Zigbee2MQTT topics
- Should receive device list via MQTT topic: `zigbee2mqtt/bridge/devices`
- Either:
  1. MQTT messages not being received
  2. Message handlers not processing correctly
  3. Database storage failing silently
  4. Devices not matching between Zigbee2MQTT and HA

**Action Required:**
- Check device-intelligence-service logs for MQTT messages
- Verify MQTT topic subscriptions are active
- Check if devices are being received but not stored
- Verify database write permissions

### Issue 4: Exposes/Capabilities Not Stored

**Status:** Depends on Issue 3

**Evidence:**
- Database schema supports exposes: `ZigbeeDeviceMetadata` table has `definition_json` and `settings_json`
- Device capabilities table exists: `device_capabilities` stores parsed exposes
- No data in either table (0 devices = no capabilities)

**Root Cause:**
- Exposes are only stored if devices are stored (Issue 3)
- Exposes come from Zigbee2MQTT device definitions
- Stored in `definition.exposes` field in Zigbee2MQTT messages

**Action Required:**
- Fix Issue 3 first (device storage)
- Verify exposes are in MQTT messages
- Ensure exposes are parsed and stored correctly

## Verification Steps

### Step 1: Check Home Assistant Device Registry

```bash
# Query HA device registry for Zigbee devices
curl -H "Authorization: Bearer $HA_TOKEN" \
  "http://192.168.1.86:8123/api/config/device_registry/list" | \
  jq '.[] | select(.name | contains("Office") or contains("Bar")) | {id, name, config_entries, identifiers}'
```

### Step 2: Check data-api Database

```sql
-- Check devices with integration field
SELECT device_id, name, integration, config_entry_id 
FROM devices 
WHERE integration IS NULL 
LIMIT 20;

-- Check if any Zigbee devices exist
SELECT device_id, name, manufacturer, model 
FROM devices 
WHERE name LIKE '%Office%' OR name LIKE '%Bar%';
```

### Step 3: Check device-intelligence-service Logs

```bash
docker compose logs device-intelligence-service | grep -i "zigbee\|mqtt\|device\|discover"
```

### Step 4: Check MQTT Topics

```bash
# Subscribe to Zigbee2MQTT topics to verify messages
mosquitto_sub -h 192.168.1.86 -p 1883 -t "zigbee2mqtt/bridge/devices" -v
```

### Step 5: Verify Zigbee2MQTT HTTP API (if available)

Zigbee2MQTT may expose an HTTP API (check add-on documentation):
- Typical endpoints: `/api/devices`, `/api/groups`
- Access via Home Assistant ingress: `http://192.168.1.86:8123/45df7312_zigbee2mqtt/ingress/api/devices`

## Recommendations

### Immediate Actions

1. **Restart websocket-ingestion** to trigger device rediscovery with integration field fix
2. **Check device-intelligence-service logs** for MQTT message reception
3. **Verify MQTT connectivity** - ensure device-intelligence-service is receiving Zigbee2MQTT messages
4. **Query Home Assistant device registry** to see if Zigbee devices are present

### Short-Term Fixes

1. **Trigger device discovery** in device-intelligence-service via API:
   ```bash
   curl -X POST http://localhost:8028/api/devices/discover
   ```

2. **Check if Zigbee2MQTT HTTP API is available** as alternative to MQTT
   - More reliable than MQTT subscriptions
   - Can query on-demand
   - Less real-time but more predictable

3. **Fix integration field in data-api**:
   - Re-run discovery to populate integration field
   - Update existing devices if needed

### Long-Term Solutions

1. **Unify Device Discovery**:
   - Primary source: Home Assistant device registry (already in place)
   - Secondary source: Zigbee2MQTT bridge (for exposes/capabilities)
   - Match devices between systems using identifiers (IEEE address, friendly name)

2. **Store Exposes in data-api**:
   - Add exposes column to devices table
   - Populate from device-intelligence-service or direct Zigbee2MQTT query
   - Enable capability queries from data-api

3. **Alternative: Use Zigbee2MQTT HTTP API** (if available):
   - More reliable than MQTT subscriptions
   - Query devices and exposes on-demand
   - Cache in device-intelligence-service or data-api

## Related Files

- `services/device-intelligence-service/src/clients/mqtt_client.py` - MQTT client for Zigbee2MQTT
- `services/device-intelligence-service/src/core/discovery_service.py` - Discovery orchestration
- `services/websocket-ingestion/src/discovery_service.py` - HA device discovery
- `implementation/analysis/ZIGBEE2MQTT_DEVICES_FIX.md` - Integration field fix
- `services/data-api/src/models/device.py` - Device storage schema
- `services/device-intelligence-service/src/models/database.py` - Zigbee device schema

## Next Steps

1. ✅ Research complete - document findings
2. ⏭️ Verify Home Assistant device registry for Zigbee devices
3. ⏭️ Check device-intelligence-service logs
4. ⏭️ Test MQTT connectivity and message reception
5. ⏭️ Investigate Zigbee2MQTT HTTP API availability
6. ⏭️ Implement fixes based on findings
