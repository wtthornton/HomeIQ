# Device Type Classification Analysis

**Date:** January 16, 2026  
**Issue:** All devices show when filtering by "switch" - devices are not properly classified

---

## Root Cause Analysis

### Problem 1: Query Issues (FIXED)

✅ **Fixed:** Query now selects `device_type` column  
✅ **Fixed:** Filter excludes NULL and empty strings  
✅ **Fixed:** Response uses actual database values

### Problem 2: All Devices Have Empty/NULL device_type

**Current State:**
- All 100 devices have `device_type = ''` (empty string) or `NULL`
- No devices are classified
- Filter returns all devices because empty string != 'switch' but query logic was wrong

**Why Devices Aren't Classified:**

1. **Classification may not run automatically**
   - Device sync from Home Assistant may not trigger classification
   - Classification service may not be integrated with sync process

2. **Classification patterns too restrictive**
   - Original patterns required exact attributes
   - Many devices don't match patterns
   - Now improved with domain-based classification

3. **Classification service may not be running**
   - Need to verify classification service is active
   - Check if classification endpoints exist

---

## Classification Logic Improvements

### ✅ Improved: Domain-Based Classification

**File:** `services/device-context-classifier/src/patterns.py`

**New Approach:**
1. **Primary:** Classify by entity domain (most reliable)
   - `light` domain → `device_type = "light"`
   - `switch` domain → `device_type = "switch"`
   - `sensor` domain → `device_type = "sensor"`

2. **Fallback:** Pattern matching for complex devices
   - Fridge, car, 3d_printer, etc.

**Domain Mapping:**
```python
DOMAIN_TO_DEVICE_TYPE = {
    "light": "light",
    "switch": "switch",
    "sensor": "sensor",
    "binary_sensor": "sensor",
    "climate": "thermostat",
    "fan": "fan",
    "lock": "lock",
    "camera": "camera",
    "cover": "cover",
    "media_player": "media_player",
    "vacuum": "vacuum",
}
```

---

## How Device Type Should Be Assigned

### Method 1: During Device Sync (Recommended)

**When:** Devices are synced from Home Assistant

**Process:**
1. Fetch device from Home Assistant
2. Get all entities for device
3. Extract entity domains
4. Classify using domain mapping
5. Update device_type in database

**Where:** Device sync process in data-api

### Method 2: Batch Classification Endpoint

**Create:** `POST /api/devices/classify` or `POST /api/devices/classify-all`

**Purpose:** Classify all existing devices

**Process:**
1. Get all devices with NULL/empty device_type
2. For each device:
   - Get entities
   - Classify using domain mapping
   - Update device_type in database

### Method 3: On-Demand Classification

**When:** Device is queried and device_type is NULL

**Process:**
1. Check if device_type is NULL
2. If NULL, classify on-the-fly
3. Update database
4. Return classified device

---

## Recommended Solution

### Option 1: Add Classification to Device Sync (Best)

**File:** `services/data-api/src/services/device_sync.py` (or similar)

**Add:**
```python
# After device is saved
if not device.device_type:
    # Get entities for device
    entities = await get_entities_for_device(device_id)
    entity_domains = [e.domain for e in entities]
    
    # Classify
    device_type = classify_by_domain(entity_domains)
    if device_type:
        device.device_type = device_type
        device.device_category = get_device_category(device_type)
        await db.commit()
```

### Option 2: Create Classification Endpoint

**Create:** `POST /api/devices/{device_id}/classify`

**Or batch:** `POST /api/devices/classify-all`

**Implementation:**
- Use improved domain-based classification
- Update all devices with NULL/empty device_type
- Return classification results

### Option 3: Background Job

**Create:** Periodic job to classify unclassified devices

**Schedule:** Daily or on service startup

---

## Immediate Fix: Classify Devices Based on Entities

Since we have entities in the database, we can classify devices directly:

**SQL Approach:**
```sql
-- Classify devices based on entity domains
UPDATE devices
SET device_type = CASE
    WHEN EXISTS (SELECT 1 FROM entities WHERE entities.device_id = devices.device_id AND entities.domain = 'light') THEN 'light'
    WHEN EXISTS (SELECT 1 FROM entities WHERE entities.device_id = devices.device_id AND entities.domain = 'switch') THEN 'switch'
    WHEN EXISTS (SELECT 1 FROM entities WHERE entities.device_id = devices.device_id AND entities.domain = 'sensor') THEN 'sensor'
    WHEN EXISTS (SELECT 1 FROM entities WHERE entities.device_id = devices.device_id AND entities.domain = 'binary_sensor') THEN 'sensor'
    WHEN EXISTS (SELECT 1 FROM entities WHERE entities.device_id = devices.device_id AND entities.domain = 'climate') THEN 'thermostat'
    WHEN EXISTS (SELECT 1 FROM entities WHERE entities.device_id = devices.device_id AND entities.domain = 'fan') THEN 'fan'
    WHEN EXISTS (SELECT 1 FROM entities WHERE entities.device_id = devices.device_id AND entities.domain = 'lock') THEN 'lock'
    WHEN EXISTS (SELECT 1 FROM entities WHERE entities.device_id = devices.device_id AND entities.domain = 'camera') THEN 'camera'
    WHEN EXISTS (SELECT 1 FROM entities WHERE entities.device_id = devices.device_id AND entities.domain = 'cover') THEN 'cover'
    WHEN EXISTS (SELECT 1 FROM entities WHERE entities.device_id = devices.device_id AND entities.domain = 'media_player') THEN 'media_player'
    WHEN EXISTS (SELECT 1 FROM entities WHERE entities.device_id = devices.device_id AND entities.domain = 'vacuum') THEN 'vacuum'
    ELSE NULL
END
WHERE device_type IS NULL OR device_type = '';
```

**Python Approach:**
Create endpoint or script to:
1. Query all devices with NULL/empty device_type
2. For each device, get entities
3. Classify by primary entity domain
4. Update device_type in database

---

## Files Modified

1. ✅ `services/data-api/src/devices_endpoints.py`
   - Added device_type to SELECT
   - Fixed filter (excludes NULL and empty strings)
   - Extract device_type from database

2. ✅ `services/device-context-classifier/src/patterns.py`
   - Added domain-based classification
   - Improved pattern matching

3. ✅ `services/ai-automation-ui/src/components/ha-agent/DevicePicker.tsx`
   - Better empty state messages
   - More device type options

---

## Next Steps

1. ✅ **Fix query and filter** - DONE
2. ⚠️ **Classify existing devices** - TODO
3. ⚠️ **Add classification to sync process** - TODO
4. ⚠️ **Test filter after classification** - TODO

---

## Summary

**Fixed:**
- ✅ Query selects device_type
- ✅ Filter excludes NULL and empty strings
- ✅ Classification logic improved (domain-based)

**Remaining:**
- ⚠️ Devices need to be classified (all currently empty/NULL)
- ⚠️ Classification needs to be triggered for existing devices
- ⚠️ Classification should run during device sync

**Status:** Filter will work correctly once devices are classified. Need to run classification on existing devices.
