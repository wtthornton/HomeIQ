# Device Type Classification Fix

**Date:** January 16, 2026  
**Issue:** Device type filter shows incorrect devices (all devices show when filtering by "switch")  
**Root Cause:** Multiple issues with device type assignment and filtering

---

## Problems Identified

### Problem 1: Query Doesn't Select device_type Column

**File:** `services/data-api/src/devices_endpoints.py` (line 201-216)

**Issue:**
- `device_type` and `device_category` are NOT in the SELECT query
- Filter is applied but column isn't selected, so filter may not work correctly
- Response hardcodes `device_type=None` for all devices

**Fix Applied:** ✅
- Added `Device.device_type` and `Device.device_category` to selected columns
- Extract actual values from database rows
- Use database values in response instead of hardcoding None

### Problem 2: Filter Doesn't Exclude NULL Values

**File:** `services/data-api/src/devices_endpoints.py` (line 238-239)

**Issue:**
- Filter `WHERE device_type = 'switch'` matches NULL values incorrectly
- Should exclude NULL values when filtering

**Fix Applied:** ✅
- Changed to: `WHERE device_type IS NOT NULL AND device_type = 'switch'`
- Now properly excludes devices without classification

### Problem 3: All Devices Have NULL device_type

**Root Cause:**
- Device classification may not be running
- Classification patterns are too restrictive
- Devices aren't being classified when synced from Home Assistant

**Status:** ⚠️ Needs Investigation

---

## Classification Logic Issues

### Current Pattern Matching

**File:** `services/device-context-classifier/src/patterns.py`

**Problem:**
- Patterns require specific attributes (e.g., "brightness", "state")
- Many devices don't match because they lack exact attribute names
- Should use entity domains as primary classification method

**Example:**
```python
"light": {
    "required": ["brightness", "state"],  # Too restrictive
    "optional": ["color", "color_temp", "effect"],
}
```

**Issue:** A light device might have domain="light" but if attributes don't include "brightness" exactly, it won't match.

### Better Approach: Domain-Based Classification

**Recommended:**
1. **Primary:** Classify by entity domain (light → "light", switch → "switch")
2. **Secondary:** Refine based on attributes if needed
3. **Fallback:** Use device name/manufacturer patterns

---

## Fixes Applied

### ✅ Fix 1: Add device_type to SELECT Query

**File:** `services/data-api/src/devices_endpoints.py`

**Before:**
```python
device_columns = [
    Device.device_id,
    Device.name,
    # ... other columns
    # device_type NOT included
]
```

**After:**
```python
device_columns = [
    Device.device_id,
    Device.name,
    # ... other columns
    Device.device_type,      # ✅ Added
    Device.device_category,  # ✅ Added
    # ... rest of columns
]
```

### ✅ Fix 2: Extract device_type from Database

**Before:**
```python
device_type=None,  # Hardcoded
device_category=None,  # Hardcoded
```

**After:**
```python
device_type = row[10] if row_len > 10 else None      # From database
device_category = row[11] if row_len > 11 else None  # From database
```

### ✅ Fix 3: Fix Filter to Exclude NULL

**Before:**
```python
if device_type:
    query = query.where(Device.device_type == device_type)
```

**After:**
```python
if device_type:
    query = query.where(
        Device.device_type.isnot(None),
        Device.device_type == device_type
    )
```

---

## Remaining Issues

### Issue 1: Devices Not Classified

**Problem:** All devices have `device_type = NULL`

**Possible Causes:**
1. Classification service not running
2. Classification not triggered during device sync
3. Classification patterns too restrictive (no matches)

**Investigation Needed:**
- Check if device classification is enabled
- Check if classification runs during device sync
- Review classification patterns for common devices

### Issue 2: Classification Patterns Too Restrictive

**Problem:** Patterns require exact attribute names that may not exist

**Example:**
- Pattern requires "brightness" attribute
- But entity might have "brightness_pct" or no brightness attribute
- Device doesn't match and gets NULL device_type

**Solution Needed:**
- Use entity domain as primary classifier
- Make attribute matching more flexible
- Add domain-to-device-type mapping

---

## Recommended Improvements

### Improvement 1: Domain-Based Classification

**Create:** `services/device-context-classifier/src/domain_mapping.py`

```python
# Primary classification: Entity domain → device_type
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
    "vacuum": "vacuum",
    "media_player": "media_player",
    # ... more mappings
}

def classify_by_domain(entity_domains: list[str]) -> str | None:
    """Classify device by primary entity domain."""
    # Use most common domain or highest priority domain
    domain_priority = ["light", "switch", "sensor", "climate", "fan", "lock"]
    
    for domain in domain_priority:
        if domain in entity_domains:
            return DOMAIN_TO_DEVICE_TYPE.get(domain)
    
    # Fallback: use first domain
    if entity_domains:
        return DOMAIN_TO_DEVICE_TYPE.get(entity_domains[0])
    
    return None
```

### Improvement 2: Update Classification Service

**File:** `services/data-api/src/services/device_classifier.py`

**Enhancement:**
1. Use domain-based classification first
2. Refine with pattern matching if needed
3. Fallback to domain mapping

### Improvement 3: Trigger Classification on Device Sync

**Check:**
- When devices are synced from Home Assistant
- If classification is called automatically
- If classification needs to be triggered manually

---

## Testing the Fixes

### Test 1: Verify Filter Works

```powershell
# Should return 0 devices (all have NULL device_type)
Invoke-RestMethod -Uri "http://localhost:3001/api/data/devices?limit=10&device_type=switch"
```

**Expected:** Empty list or devices with actual device_type="switch"

### Test 2: Check device_type Values

```powershell
# Check what device_type values exist
$response = Invoke-RestMethod -Uri "http://localhost:3001/api/data/devices?limit=100"
$response.devices | Group-Object device_type | Where-Object { $_.Name }
```

**Expected:** Should show distribution of device_type values (or all NULL)

### Test 3: Test Filter After Classification

After running classification:
```powershell
# Should only return actual switches
Invoke-RestMethod -Uri "http://localhost:3001/api/data/devices?device_type=switch"
```

---

## Next Steps

1. ✅ **Fix query to select device_type** - DONE
2. ✅ **Fix filter to exclude NULL** - DONE
3. ✅ **Extract device_type from database** - DONE
4. ⚠️ **Investigate why devices aren't classified** - TODO
5. ⚠️ **Improve classification logic** - TODO
6. ⚠️ **Trigger classification for existing devices** - TODO

---

## Files Modified

1. ✅ `services/data-api/src/devices_endpoints.py` - Fixed query and filter

## Files to Review/Modify

1. `services/device-context-classifier/src/patterns.py` - Improve classification
2. `services/data-api/src/services/device_classifier.py` - Add domain-based classification
3. Device sync process - Ensure classification runs

---

## Summary

**Fixed:**
- ✅ Query now selects device_type column
- ✅ Filter excludes NULL values
- ✅ Response uses actual database values

**Remaining:**
- ⚠️ Devices need to be classified (all currently NULL)
- ⚠️ Classification logic needs improvement
- ⚠️ Classification may need to be triggered

**Status:** Filter will work correctly once devices are classified. Need to run classification or improve classification logic.
