# Database Review Report
**Date:** November 16, 2025  
**Reviewer:** Automated Database Review Script  
**Status:** ✅ Databases Operational with Minor Warnings

## Executive Summary

Both databases (InfluxDB and SQLite) are operational and healthy. Data is being written and updated correctly. Two minor warnings were identified that should be reviewed but do not indicate critical issues.

---

## InfluxDB Review

### Connection Status
- ✅ **Status:** Connected and healthy
- **URL:** http://localhost:8086
- **Organization:** ha-ingestor
- **Bucket:** home_assistant_events

### Buckets Found
1. **home_assistant_events** (Primary bucket)
   - Retention: 0d (infinite)
   - Status: Active, receiving data

2. **weather_data**
   - Retention: 0d (infinite)
   - Status: Active

3. **_tasks** (System bucket)
   - Retention: 3d
   - Status: Active

4. **_monitoring** (System bucket)
   - Retention: 7d
   - Status: Active

### Data Statistics
- **Latest Data Point:** 2025-11-16 23:29:10 UTC (fresh, within last hour)
- **Data Age:** ✅ Fresh (updating correctly)
- **Measurements:** home_assistant_events

### Schema Analysis

#### Tags Found (in recent data):
- ✅ `entity_id` - Present
- ✅ `domain` - Present
- ✅ `event_type` - Present
- ⚠️ `area_id` - **NOT FOUND in recent data**
- ⚠️ `device_id` - **NOT FOUND in recent data**

#### Fields Found (in recent data):
- ✅ `state_value` - Present (contains full state object)
- ✅ `previous_state` - Present (contains full previous state object)
- ✅ `context_id` - Present
- ⚠️ `duration_in_state_seconds` - Not checked (may be present in older data)

### Sample Data Point
```
Measurement: home_assistant_events
Time: 2025-11-16 23:29:10.157000+00:00
Entity: sensor.slzb_06p7_coordinator_core_chip_temp
Domain: sensor
Event Type: state_changed
Fields: context_id, previous_state, state_value
```

### Issues Identified

#### ⚠️ WARNING: Missing Expected Tags
**Issue:** Expected tags `area_id` and `device_id` are not present in recent data points.

**Impact:** 
- These tags are defined in the schema (Epic 23.2) for device-level and area-level aggregation
- Queries filtering by device_id or area_id may not work as expected
- This may indicate that the enrichment/normalization process is not adding these tags

**Recommendation:**
1. Check websocket-ingestion service logs to see if device_id and area_id are being extracted
2. Verify that device/entity lookups are working correctly
3. Review the event processing code to ensure these tags are being added

**Code Reference:**
- Schema definition: `services/websocket-ingestion/src/influxdb_schema.py`
- Expected tags: `TAG_DEVICE_ID`, `TAG_AREA_ID` (lines 63-64)

---

## SQLite Review

### Connection Status
- ✅ **Status:** Connected and accessible
- **Database:** metadata.db
- **Location:** homeiq-data-api container (/app/data/metadata.db)
- **Journal Mode:** WAL (optimal for concurrency)

### Tables Found

#### 1. `devices` Table
- **Row Count:** 96 devices
- **Schema:** ✅ Correct (13 columns)
  - Primary Key: `device_id` (VARCHAR)
  - Required Fields: `name` (NOT NULL)
  - Metadata Fields: manufacturer, model, sw_version, area_id, integration, etc.
  - Timestamps: `created_at`, `last_seen`

**Column Structure:**
```
[PK] device_id            VARCHAR         NOT NULL
     name                 VARCHAR         NOT NULL
     name_by_user         VARCHAR         NULL
     manufacturer         VARCHAR         NULL
     model                VARCHAR         NULL
     sw_version           VARCHAR         NULL
     area_id              VARCHAR         NULL
     integration          VARCHAR         NULL
     entry_type           VARCHAR         NULL
     configuration_url    VARCHAR         NULL
     suggested_area       VARCHAR         NULL
     last_seen            DATETIME        NULL
     created_at           DATETIME        NULL
```

**Data Status:**
- ✅ Latest `last_seen`: 2025-11-16 15:05:52 (fresh, today)
- ⚠️ Latest `created_at`: 2025-11-04 05:37:56 (12 days ago)
  - **Note:** This is expected - `created_at` is when devices were first registered, not when they were last updated
  - `last_seen` is the correct field to check for data freshness

#### 2. `entities` Table
- **Row Count:** 680 entities
- **Schema:** ✅ Correct (8 columns)
  - Primary Key: `entity_id` (VARCHAR)
  - Foreign Key: `device_id` → `devices.device_id` (CASCADE on delete)
  - Required Fields: `domain` (NOT NULL)
  - Metadata Fields: platform, unique_id, area_id, disabled

**Column Structure:**
```
[PK] entity_id            VARCHAR         NOT NULL
     device_id            VARCHAR         NULL (FK to devices.device_id)
     domain               VARCHAR         NOT NULL
     platform             VARCHAR         NULL
     unique_id            VARCHAR         NULL
     area_id              VARCHAR         NULL
     disabled             BOOLEAN         NULL
     created_at           DATETIME        NULL
```

**Data Status:**
- ✅ Latest `created_at`: 2025-11-16 15:05:53 (fresh, today)
- ✅ Data is actively updating

### Foreign Key Relationships
- ✅ **No orphaned entities** - All entity.device_id references point to valid devices
- ✅ Foreign key constraint: `device_id → devices.device_id` with CASCADE delete

### Indexes
**Devices Table:**
- `ix_devices_integration` on `integration`
- `ix_devices_area_id` on `area_id`
- `idx_device_integration` on `integration`
- `idx_device_manufacturer` on `manufacturer`
- `idx_device_area` on `area_id`

**Entities Table:**
- `ix_entities_domain` on `domain`
- `idx_entity_domain` on `domain`
- `ix_entities_area_id` on `area_id`
- `ix_entities_device_id` on `device_id`
- `idx_entity_device` on `device_id`
- `idx_entity_area` on `area_id`

**Note:** Some duplicate indexes exist (e.g., `ix_devices_integration` and `idx_device_integration`). This is not an error but could be optimized.

### Database Integrity
- ✅ **Integrity Check:** PASSED
- ✅ **Journal Mode:** WAL (Write-Ahead Logging) - optimal for concurrent access
- ✅ **Foreign Keys:** Enabled and enforced

### Issues Identified

#### ⚠️ WARNING: Devices Table created_at Age
**Issue:** Latest `created_at` timestamp is 12 days old.

**Impact:** 
- **NONE** - This is expected behavior
- `created_at` represents when devices were first registered, not when they were last updated
- `last_seen` field shows recent activity (2025-11-16 15:05:52)

**Recommendation:**
- No action needed - this is correct behavior
- Consider renaming the warning check to only flag `last_seen` age, not `created_at`

---

## Summary of Issues

### Critical Issues: 0
✅ No critical issues found

### Warnings: 2

1. **InfluxDB Missing Tags** (Medium Priority)
   - Expected tags `area_id` and `device_id` not found in recent data
   - May impact device/area-level queries
   - **Action Required:** Investigate why these tags are not being added during event processing

2. **Devices Table created_at Age** (Low Priority - False Positive)
   - Latest `created_at` is 12 days old
   - **Not an issue** - `last_seen` shows fresh data
   - **Action Required:** Update review script to check `last_seen` instead of `created_at` for data freshness

---

## Recommendations

### Immediate Actions
1. ✅ **None** - Databases are healthy and operational

### Short-term Improvements
1. **Investigate Missing InfluxDB Tags**
   - Review websocket-ingestion event processing code
   - Verify device/entity lookup is working
   - Ensure `device_id` and `area_id` are being extracted and added as tags

2. **Optimize Indexes**
   - Review duplicate indexes (e.g., `ix_devices_integration` vs `idx_device_integration`)
   - Consider removing redundant indexes to improve write performance

3. **Update Review Script**
   - Change data freshness check to use `last_seen` instead of `created_at` for devices table
   - Add check for `duration_in_state_seconds` field in InfluxDB

### Long-term Considerations
1. **Schema Documentation**
   - Document the actual InfluxDB schema being used (may differ from schema.py)
   - Note that state_value and previous_state contain full JSON objects, not just state strings

2. **Monitoring**
   - Set up alerts for:
     - Data freshness (no new data in last hour)
     - Missing expected tags/fields
     - Database integrity issues

---

## Verification Commands

### Check InfluxDB Data
```bash
# Query recent data with device_id and area_id tags
docker exec homeiq-influxdb influx query '
  from(bucket: "home_assistant_events")
    |> range(start: -1h)
    |> filter(fn: (r) => exists r.device_id or exists r.area_id)
    |> limit(n: 10)
' --org ha-ingestor --token ha-ingestor-token
```

### Check SQLite Data Freshness
```bash
# Check devices last_seen
docker exec homeiq-data-api sqlite3 /app/data/metadata.db \
  "SELECT MAX(last_seen) as latest, COUNT(*) as total FROM devices;"

# Check entities freshness
docker exec homeiq-data-api sqlite3 /app/data/metadata.db \
  "SELECT MAX(created_at) as latest, COUNT(*) as total FROM entities;"
```

---

## Conclusion

Both databases are **healthy and operational**. Data is being written and updated correctly. The two warnings identified are minor and do not impact system functionality:

1. Missing InfluxDB tags should be investigated to ensure proper device/area-level querying
2. The devices table `created_at` warning is a false positive - data is fresh based on `last_seen`

**Overall Status: ✅ HEALTHY**

