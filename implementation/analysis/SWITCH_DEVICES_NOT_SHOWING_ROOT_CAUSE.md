# Root Cause Analysis: Switch Devices Not Showing

**Date:** January 20, 2026  
**Issue:** No switches appearing in device filter despite known switch devices existing  
**Status:** Root Cause Identified

---

## Executive Summary

**Root Cause:** Devices are not classified because:
1. **Entities are not linked to devices** (primary issue) - Entities have empty `device_id` fields, preventing domain-based classification
2. **Classification has not been run** - Even with metadata fallback available, the batch classification endpoint hasn't been executed
3. **Metadata classification may miss switches** - If device names don't contain keywords like "switch", "outlet", or "smart plug", they won't be classified via metadata fallback

---

## Problem Flow

```
1. User filters by "switch" device type
   ↓
2. Query executes: WHERE device_type = 'switch' AND device_type IS NOT NULL
   ↓
3. Returns 0 results because ALL devices have device_type = NULL or ''
   ↓
4. Dashboard shows: "No devices found with type 'switch'"
```

---

## Root Cause Details

### Issue 1: Entity-Device Linking Missing (BLOCKER)

**Problem:**
- Entities exist in database (`entities` table)
- Devices exist in database (`devices` table)
- **BUT**: Entities have empty `device_id` fields (not linked to devices)

**Evidence from Previous Analysis:**
- Documented in `implementation/DEVICE_TYPE_FIXES_COMPLETE.md`
- Example: `sensor.sun_next_dawn` has `device_id: ''` (empty string)

**Impact:**
- Classification uses entity domains (most reliable method)
- Queries entities: `SELECT * FROM entities WHERE device_id = 'device_id'`
- Returns 0 entities because `device_id` is empty
- Can't determine device type from entity domains

**Why This Happens:**
- Entity sync from Home Assistant may not establish device-entity relationships
- `device_id` field not populated during entity sync process
- Device-entity relationship needs to be established from HA entity registry

---

### Issue 2: Classification Not Executed

**Problem:**
- Classification endpoints exist:
  - `POST /api/devices/classify-all` - Batch classify all devices
  - `POST /api/devices/{device_id}/classify` - Classify single device
- **BUT**: Classification has not been run on existing devices
- All devices remain with `device_type = NULL` or `device_type = ''`

**Impact:**
- Even if metadata classification could identify switches, it hasn't been attempted
- Devices remain unclassified until endpoint is executed

---

### Issue 3: Metadata Classification Limitations

**Problem:**
- When entity links are missing, classification falls back to metadata matching (name/manufacturer/model)
- Pattern matching looks for keywords: "switch", "outlet", "smart plug", "smartplug"
- **Issue**: If switch devices are named differently (e.g., "Office Light" but it's actually a switch), they won't be classified

**Example:**
- Device name: "Office Light Switch" → ✅ Would match "switch" keyword
- Device name: "Office Light" (but it's a switch) → ❌ Won't match, classified as "light" or remains unclassified

**Code Reference:**
```python
# services/data-api/src/services/device_classifier.py:188
elif any(keyword in combined for keyword in ["switch", "outlet", "smart plug", "smartplug"]):
    return {
        "device_id": device_id,
        "device_type": "switch",
        "device_category": "control"
    }
```

---

## Classification Architecture

### Primary Method: Domain-Based Classification (IDEAL)

**Process:**
1. Get all entities for device: `SELECT * FROM entities WHERE device_id = 'device_id'`
2. Extract entity domains: `["switch", "sensor", "light"]`
3. Map domains to device type: `switch` domain → `device_type = "switch"`
4. Update device in database

**Domain Mapping:**
```python
DOMAIN_TO_DEVICE_TYPE = {
    "switch": "switch",  # ← This is what identifies switches
    "light": "light",
    "sensor": "sensor",
    "binary_sensor": "sensor",
    # ... etc
}
```

**Requirement:** Entities must be linked to devices (`device_id` must be populated)

### Fallback Method: Metadata Classification (LIMITED)

**Process:**
1. If no entities found, use device name/manufacturer/model
2. Match keywords: "switch", "outlet", "smart plug"
3. Update device in database

**Limitations:**
- Relies on naming conventions
- May miss switches with non-standard names
- Less reliable than domain-based classification

---

## Verification Steps

### Step 1: Check Entity-Device Linking

**Query to check:**
```sql
-- Count entities with empty device_id
SELECT COUNT(*) FROM entities WHERE device_id IS NULL OR device_id = '';

-- Count entities linked to devices
SELECT COUNT(*) FROM entities WHERE device_id IS NOT NULL AND device_id != '';

-- Sample unlinked entities
SELECT entity_id, domain, device_id FROM entities 
WHERE (device_id IS NULL OR device_id = '') 
AND domain = 'switch' 
LIMIT 10;
```

**Expected Result:**
- If many entities have empty `device_id`, this confirms Issue #1

### Step 2: Check Device Classification Status

**Query to check:**
```sql
-- Count unclassified devices
SELECT COUNT(*) FROM devices 
WHERE device_type IS NULL OR device_type = '';

-- Count classified devices
SELECT COUNT(*) FROM devices 
WHERE device_type IS NOT NULL AND device_type != '';

-- Sample unclassified devices
SELECT device_id, name, manufacturer, model, device_type 
FROM devices 
WHERE device_type IS NULL OR device_type = ''
LIMIT 10;
```

**Expected Result:**
- If many devices have NULL/empty `device_type`, this confirms Issue #2

### Step 3: Check for Switch Entities

**Query to check:**
```sql
-- Count switch entities
SELECT COUNT(*) FROM entities WHERE domain = 'switch';

-- Sample switch entities (regardless of device_id)
SELECT entity_id, domain, device_id, platform 
FROM entities 
WHERE domain = 'switch' 
LIMIT 10;
```

**Expected Result:**
- If switch entities exist but `device_id` is empty, this confirms entities aren't linked

---

## Solution Paths

### Immediate Fix (Workaround)

**Run Classification with Metadata Fallback:**
```bash
# Call classification endpoint (uses metadata if entities not linked)
curl -X POST "http://localhost:8006/api/devices/classify-all"
```

**Result:**
- Devices with "switch", "outlet", "smart plug" in name will be classified
- Devices without these keywords may remain unclassified

### Proper Fix (Recommended)

**Step 1: Link Entities to Devices**
```bash
# Use entity-device linking endpoint
curl -X POST "http://localhost:8006/api/devices/link-entities"
```

**This endpoint:**
- Queries Home Assistant entity registry API
- Gets `device_id` for each entity
- Updates `entity.device_id` in database
- Falls back to `config_entry_id` matching if HA API unavailable

**Step 2: Run Classification**
```bash
# Now classification will use entity domains (more reliable)
curl -X POST "http://localhost:8006/api/devices/classify-all"
```

**Result:**
- All devices with switch entities will be classified as "switch"
- More reliable than metadata matching

### Long-Term Fix (Preventive)

**Fix Entity Sync Process:**
- Ensure entity sync from Home Assistant populates `device_id` field
- Verify device-entity relationships are established during sync
- Add validation to check entity-device links after sync

**Location:** Entity sync service (likely in `websocket-ingestion` or `data-api`)

---

## Expected Outcomes

### After Linking Entities and Running Classification

**Query Results:**
```sql
-- Should return switch devices
SELECT device_id, name, device_type 
FROM devices 
WHERE device_type = 'switch';
```

**API Results:**
```bash
# Should return switches
curl "http://localhost:8006/api/devices?device_type=switch"
```

**Dashboard:**
- Device picker should show switches when filtering by "switch" type
- Count of switches should match actual switch devices in Home Assistant

---

## Related Documentation

- `implementation/DEVICE_TYPE_CLASSIFICATION_ANALYSIS.md` - Initial analysis
- `implementation/DEVICE_TYPE_FIXES_COMPLETE.md` - Previous fixes and known issues
- `implementation/DEVICE_TYPE_CLASSIFICATION_COMPLETE.md` - Classification implementation
- `services/data-api/src/devices_endpoints.py` - Classification endpoints (lines 1854-2162)
- `services/data-api/src/services/device_classifier.py` - Classification logic

---

## Next Steps

1. ✅ **Verify root cause** - Run verification queries above
2. ⏳ **Link entities to devices** - Execute `POST /api/devices/link-entities`
3. ⏳ **Run classification** - Execute `POST /api/devices/classify-all`
4. ⏳ **Verify switches appear** - Check dashboard and API
5. ⏳ **Fix entity sync** - Ensure future entities are linked automatically
