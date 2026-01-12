# Zigbee2MQTT Devices Not Showing in HomeIQ - Comprehensive Review & Fix Plan

**Date:** January 16, 2026  
**Status:** Analysis Complete - Ready for Implementation  
**Issue:** Zigbee2MQTT devices are not appearing in the HomeIQ device list dashboard

## Executive Summary

Zigbee2MQTT devices are not appearing in the HomeIQ dashboard due to multiple interconnected issues across the device discovery and storage pipeline. The primary issues are:

1. **Integration field not populated** in data-api database (fix exists but needs rediscovery)
2. **device-intelligence-service has 0 devices stored** (service running but not receiving/storing devices)
3. **Dashboard queries data-api only** (doesn't query device-intelligence-service)
4. **Database schema may be out of sync** (migration may not have been run)

## Architecture Review

### Current Device Discovery Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Zigbee2MQTT Bridge                           │
│                  (MQTT Topics)                                  │
└────────────┬────────────────────────┬──────────────────────────┘
             │                        │
             │ MQTT                   │ Device Registry
             │                        │
             ▼                        ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│ device-intelligence-     │  │ Home Assistant               │
│ service (Port 8028)      │  │ Device Registry              │
│                          │  │                              │
│ • Subscribes to          │  │ • Stores devices with        │
│   zigbee2mqtt/bridge/*   │  │   config_entry_id            │
│ • Stores Zigbee metadata │  │ • Does NOT provide           │
│ • Stores exposes/        │  │   integration field          │
│   capabilities           │  │   directly                   │
│                          │  │                              │
│ Status: 0 devices stored │  └──────────┬───────────────────┘
└──────────────────────────┘             │
                                         │ WebSocket/HTTP API
                                         │
                                         ▼
                              ┌──────────────────────────────┐
                              │ websocket-ingestion          │
                              │ (Port 8001)                  │
                              │                              │
                              │ • Discovers devices from HA  │
                              │ • Resolves integration from  │
                              │   config_entry_id            │
                              │ • Stores via data-api        │
                              │                              │
                              │ Fix Applied: Integration     │
                              │ resolution enabled            │
                              └──────────┬───────────────────┘
                                         │
                                         │ HTTP POST
                                         │ /internal/devices/bulk_upsert
                                         │
                                         ▼
                              ┌──────────────────────────────┐
                              │ data-api (Port 8006)         │
                              │ SQLite: metadata.db          │
                              │                              │
                              │ • Stores devices from        │
                              │   websocket-ingestion        │
                              │ • Current: 100 devices,      │
                              │   ALL have integration=null  │
                              │                              │
                              │ Status: Needs rediscovery    │
                              └──────────┬───────────────────┘
                                         │
                                         │ HTTP GET
                                         │ /api/devices
                                         │
                                         ▼
                              ┌──────────────────────────────┐
                              │ health-dashboard (Port 3000) │
                              │                              │
                              │ • Queries data-api only      │
                              │ • Filters by integration=    │
                              │   'zigbee2mqtt'              │
                              │ • Returns 0 results          │
                              │                              │
                              │ Status: No Zigbee devices    │
                              └──────────────────────────────┘
```

### Key Services Analysis

#### 1. websocket-ingestion (Port 8001)
**Purpose:** Discovers devices from Home Assistant and stores them in data-api

**Current Status:**
- ✅ Integration field resolution code exists (lines 637-660 in discovery_service.py)
- ✅ Config entries discovery enabled (line 521)
- ⚠️ Devices in database still have `integration=null` (needs rediscovery)

**Key Code:**
```python
# Build config_entry_id -> integration domain mapping
config_entry_map: dict[str, str] = {}
if config_entries_data:
    for entry in config_entries_data:
        entry_id = entry.get("entry_id")
        domain = entry.get("domain")
        if entry_id and domain:
            config_entry_map[entry_id] = domain

# Resolve integration field for devices
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

**Issue:** Fix exists but devices were stored before fix, or discovery hasn't run since fix was applied.

#### 2. data-api (Port 8006)
**Purpose:** Stores devices in SQLite database (metadata.db)

**Current Status:**
- ✅ Bulk upsert endpoint accepts integration field (line 1232)
- ✅ 100 devices stored
- ❌ ALL devices have `integration=null`
- ❌ Query `GET /api/devices?integration=zigbee2mqtt` returns 0 results

**Database Schema:**
- `devices` table has `integration` column (nullable String)
- Column exists and is indexed
- No schema issues

**Issue:** Integration field not populated because devices stored before fix, or discovery hasn't run since fix.

#### 3. device-intelligence-service (Port 8028)
**Purpose:** Stores Zigbee2MQTT devices with exposes/capabilities from MQTT

**Current Status:**
- ✅ Service running and healthy
- ✅ MQTT connection established
- ✅ Database schema has Zigbee fields (lqi, availability_status, battery_level, etc.)
- ❌ 0 devices stored
- ❌ Database may be out of sync (migration script exists but may not have been run)

**Key Components:**
- **MQTT Client:** Subscribes to `zigbee2mqtt/bridge/devices` topic
- **Discovery Service:** Unifies HA and Zigbee2MQTT device data
- **Device Parser:** Merges device information from multiple sources
- **Database Storage:** Stores unified devices with Zigbee metadata

**Possible Issues:**
1. MQTT messages not being received
2. Message handlers not processing correctly
3. Database storage failing silently
4. Schema mismatch (migration not run)
5. Devices not matching between Zigbee2MQTT and HA registries

**Database Schema:**
- Schema model has all Zigbee fields (lines 48-56 in database.py)
- Migration script exists: `scripts/migrate_add_zigbee_fields.py`
- Migration may not have been run on production database

#### 4. health-dashboard (Port 3000)
**Purpose:** Displays devices to users

**Current Status:**
- ✅ Queries data-api for devices
- ✅ Supports filtering by integration
- ❌ No Zigbee devices returned (integration=null in database)
- ⚠️ Only queries data-api, doesn't query device-intelligence-service

**Query Pattern:**
```typescript
const response = await dataApi.getDevices({
  limit: 1000,
  integration: 'zigbee2mqtt',  // This filter returns 0 results
  ...
});
```

## Root Cause Analysis

### Primary Root Cause: Integration Field Not Populated

**Issue:** All devices in data-api database have `integration=null`, preventing filtering and display of Zigbee2MQTT devices.

**Why:**
1. Home Assistant device registry doesn't provide `integration` field directly
2. Integration must be resolved from `config_entry_id` → `integration domain` mapping
3. Fix was applied to websocket-ingestion, but:
   - Devices were stored before fix, OR
   - Discovery hasn't run since fix was applied

**Impact:**
- Dashboard query `GET /api/devices?integration=zigbee2mqtt` returns 0 results
- Zigbee devices exist in database but can't be filtered/displayed

### Secondary Root Cause: device-intelligence-service Not Storing Devices

**Issue:** device-intelligence-service has 0 devices stored despite service running and MQTT connected.

**Possible Reasons:**
1. **MQTT messages not received:** Service may not be subscribed to correct topics
2. **Message processing failure:** Messages received but not processed correctly
3. **Database schema mismatch:** Migration not run, causing insert failures
4. **Device matching failure:** Zigbee2MQTT devices don't match HA devices
5. **Service not discovering:** Discovery service not running or failing silently

**Impact:**
- Zigbee-specific metadata (LQI, battery, availability) not stored
- Device exposes/capabilities not available
- device-intelligence-service database empty

### Tertiary Issue: Dashboard Only Queries data-api

**Issue:** Dashboard only queries data-api, doesn't query device-intelligence-service for Zigbee metadata.

**Impact:**
- Even if device-intelligence-service stores devices, dashboard won't show them
- Zigbee-specific metadata not available in dashboard
- Two separate device databases (data-api and device-intelligence-service)

**Note:** This is by design - data-api is the primary device store. device-intelligence-service should populate data-api, not be queried separately.

## Verification Steps

### Step 1: Verify Integration Field Fix Status

**Check if devices have integration field populated:**
```sql
-- Query data-api database
SELECT device_id, name, integration, config_entry_id 
FROM devices 
WHERE integration IS NULL 
LIMIT 20;

-- Check if any Zigbee devices exist (by name pattern)
SELECT device_id, name, manufacturer, model, integration
FROM devices 
WHERE name LIKE '%Office%' OR name LIKE '%Bar%' OR name LIKE '%Light%' OR name LIKE '%Sensor%';
```

**Check if config entries discovery is working:**
```bash
# Check websocket-ingestion logs for integration resolution
docker compose logs websocket-ingestion | grep -i "integration\|config_entry\|Built config entry mapping"
```

**Expected Output:**
```
🔧 Built config entry mapping: X entries
Resolved integration 'zigbee2mqtt' for device [name] from config_entry [id]
```

### Step 2: Verify device-intelligence-service Status

**Check service health:**
```powershell
# Check service health
Invoke-RestMethod -Uri "http://localhost:8028/health"

# Check device count
Invoke-RestMethod -Uri "http://localhost:8028/api/devices?limit=1"
```

**Check service logs:**
```bash
docker compose logs device-intelligence-service | Select-Object -Last 100
```

**Look for:**
- MQTT connection status
- Device discovery messages
- Database storage errors
- Schema errors (missing columns)

### Step 3: Verify MQTT Subscription

**Check if service is receiving MQTT messages:**
```bash
# Check logs for MQTT messages
docker compose logs device-intelligence-service | grep -i "mqtt\|zigbee\|device\|discover"
```

**Manually subscribe to MQTT topic to verify messages:**
```bash
# Requires mosquitto client
mosquitto_sub -h 192.168.1.86 -p 1883 -t "zigbee2mqtt/bridge/devices" -v
```

**Expected:** Should see JSON device list from Zigbee2MQTT

### Step 4: Verify Database Schema

**Check if migration has been run:**
```sql
-- Query device-intelligence-service database
PRAGMA table_info(devices);

-- Check if Zigbee columns exist
SELECT name FROM pragma_table_info('devices') WHERE name IN ('lqi', 'availability_status', 'battery_level', 'source');
```

**Expected:** Should see lqi, availability_status, battery_level, source columns

**If columns missing, run migration:**
```bash
cd services/device-intelligence-service
python scripts/migrate_add_zigbee_fields.py
```

### Step 5: Verify Home Assistant Device Registry

**Check if Zigbee devices are in HA registry:**
```powershell
# Query HA device registry (requires HA token)
$haUrl = "http://192.168.1.86:8123"
$haToken = $env:HA_TOKEN
$headers = @{
    "Authorization" = "Bearer $haToken"
    "Content-Type" = "application/json"
}

$devices = Invoke-RestMethod -Uri "$haUrl/api/config/device_registry/list" -Headers $headers
$zigbeeDevices = $devices | Where-Object { $_.config_entries -ne $null -and $_.name -match "Office|Bar|Light|Sensor" }
$zigbeeDevices | Select-Object id, name, config_entries, identifiers | Format-Table
```

**Expected:** Should see Zigbee devices with config_entry_id pointing to zigbee2mqtt integration

## Fix Plan

### Phase 1: Fix Integration Field (IMMEDIATE - Highest Priority)

**Goal:** Populate integration field in data-api database so Zigbee devices can be filtered and displayed.

**Steps:**
1. **Trigger device rediscovery in websocket-ingestion:**
   ```bash
   # Restart service to trigger discovery
   docker compose restart websocket-ingestion
   
   # Or trigger discovery via API if endpoint exists
   # Check logs to verify discovery runs
   docker compose logs -f websocket-ingestion
   ```

2. **Verify integration field is populated:**
   ```sql
   SELECT device_id, name, integration 
   FROM devices 
   WHERE integration = 'zigbee2mqtt';
   ```

3. **Verify dashboard shows Zigbee devices:**
   - Open health-dashboard
   - Filter by integration: zigbee2mqtt
   - Should see Zigbee devices

**Success Criteria:**
- ✅ Integration field populated for all devices in data-api
- ✅ Query `GET /api/devices?integration=zigbee2mqtt` returns Zigbee devices
- ✅ Dashboard displays Zigbee devices when filtered by integration

**Estimated Time:** 15-30 minutes (mostly verification)

### Phase 2: Fix device-intelligence-service (HIGH PRIORITY)

**Goal:** Ensure device-intelligence-service stores Zigbee devices with metadata.

**Steps:**
1. **Run database migration (if needed):**
   ```bash
   cd services/device-intelligence-service
   python scripts/migrate_add_zigbee_fields.py
   ```

2. **Verify MQTT connection:**
   ```bash
   # Check service logs
   docker compose logs device-intelligence-service | grep -i "mqtt\|connected\|subscribe"
   ```

3. **Trigger device discovery:**
   ```powershell
   # If discovery endpoint exists
   Invoke-RestMethod -Uri "http://localhost:8028/api/devices/discover" -Method Post
   ```

4. **Check if devices are stored:**
   ```sql
   SELECT COUNT(*) FROM devices;
   SELECT id, name, integration, source FROM devices LIMIT 10;
   ```

5. **Investigate if devices not stored:**
   - Check logs for errors
   - Verify MQTT messages are received
   - Check if device matching logic is working
   - Verify database write permissions

**Success Criteria:**
- ✅ Database schema has all Zigbee fields
- ✅ Service receives MQTT messages
- ✅ Devices stored in device-intelligence-service database
- ✅ Zigbee metadata (LQI, battery, availability) populated

**Estimated Time:** 1-2 hours (depends on root cause)

### Phase 3: Integrate device-intelligence-service with data-api (MEDIUM PRIORITY)

**Goal:** Ensure device-intelligence-service populates data-api with Zigbee metadata, or data-api queries device-intelligence-service for enrichment.

**Options:**
1. **Option A: device-intelligence-service populates data-api**
   - Add API call from device-intelligence-service to data-api
   - Enrich devices with Zigbee metadata when storing
   - Pros: Single source of truth (data-api)
   - Cons: Requires service-to-service communication

2. **Option B: data-api queries device-intelligence-service for enrichment**
   - Add enrichment endpoint in data-api
   - Query device-intelligence-service when fetching devices
   - Merge Zigbee metadata into device responses
   - Pros: data-api remains primary store
   - Cons: Requires query coordination

3. **Option C: Unified device store (data-api only)**
   - Migrate device-intelligence-service logic to data-api
   - Single device database
   - Pros: Simplified architecture
   - Cons: Requires significant refactoring

**Recommended:** Option A (device-intelligence-service populates data-api)

**Steps:**
1. Add data-api client to device-intelligence-service
2. Call data-api `/internal/devices/bulk_upsert` when devices discovered
3. Include Zigbee metadata in device data
4. Verify devices appear in data-api with Zigbee metadata

**Success Criteria:**
- ✅ Zigbee devices in data-api have Zigbee metadata (LQI, battery, etc.)
- ✅ Dashboard can display Zigbee-specific information
- ✅ Single source of truth for device data (data-api)

**Estimated Time:** 2-4 hours (implementation + testing)

### Phase 4: Enhance Dashboard (LOW PRIORITY)

**Goal:** Display Zigbee-specific metadata in dashboard (LQI, battery, availability).

**Steps:**
1. Update device model to include Zigbee fields
2. Add Zigbee metadata display in device details
3. Add filters for Zigbee-specific attributes
4. Add Zigbee device status indicators

**Success Criteria:**
- ✅ Dashboard displays Zigbee metadata
- ✅ Users can filter by Zigbee attributes
- ✅ Zigbee device status clearly visible

**Estimated Time:** 2-3 hours (UI development)

## Implementation Priority

1. **Phase 1 (IMMEDIATE):** Fix integration field - enables basic device display
2. **Phase 2 (HIGH):** Fix device-intelligence-service - enables Zigbee metadata
3. **Phase 3 (MEDIUM):** Integrate services - enables full Zigbee support
4. **Phase 4 (LOW):** Enhance dashboard - improves user experience

## Testing Plan

### Phase 1 Testing
- [ ] Verify integration field populated after rediscovery
- [ ] Verify dashboard shows Zigbee devices with integration filter
- [ ] Verify query `GET /api/devices?integration=zigbee2mqtt` returns devices

### Phase 2 Testing
- [ ] Verify database schema has Zigbee fields
- [ ] Verify MQTT messages received
- [ ] Verify devices stored in device-intelligence-service
- [ ] Verify Zigbee metadata populated

### Phase 3 Testing
- [ ] Verify devices in data-api have Zigbee metadata
- [ ] Verify service-to-service communication works
- [ ] Verify data consistency between services

### Phase 4 Testing
- [ ] Verify dashboard displays Zigbee metadata
- [ ] Verify filters work correctly
- [ ] Verify status indicators accurate

## Related Files

### Code Files
- `services/websocket-ingestion/src/discovery_service.py` - Integration field resolution
- `services/data-api/src/devices_endpoints.py` - Device storage endpoint
- `services/device-intelligence-service/src/core/discovery_service.py` - Device discovery
- `services/device-intelligence-service/src/clients/mqtt_client.py` - MQTT client
- `services/device-intelligence-service/src/models/database.py` - Database schema
- `services/health-dashboard/src/hooks/useDevices.ts` - Device query hook

### Documentation Files
- `implementation/analysis/ZIGBEE2MQTT_DEVICES_MISSING_RESEARCH.md` - Previous research
- `implementation/analysis/ZIGBEE2MQTT_DEVICES_FIX.md` - Integration field fix documentation

### Migration Scripts
- `services/device-intelligence-service/scripts/migrate_add_zigbee_fields.py` - Database migration

## Next Steps

1. ✅ Complete research and analysis (this document)
2. ⏭️ Execute Phase 1: Fix integration field (trigger rediscovery)
3. ⏭️ Verify Phase 1 success (check database and dashboard)
4. ⏭️ Execute Phase 2: Fix device-intelligence-service
5. ⏭️ Execute Phase 3: Integrate services (if needed)
6. ⏭️ Execute Phase 4: Enhance dashboard (if needed)

## Notes

- The integration field fix already exists in code - just needs rediscovery to take effect
- device-intelligence-service architecture is separate from data-api - may need integration
- Dashboard currently only queries data-api - consider if device-intelligence-service should be queried separately or integrated
- Zigbee2MQTT devices may exist in HA registry but with different names/identifiers than in Zigbee2MQTT UI
