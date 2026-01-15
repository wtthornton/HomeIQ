# Device Type Classification - Next Steps Execution

**Date:** January 16, 2026  
**Status:** ⚠️ In Progress - Entity Linking Endpoint Created, Testing Required

---

## Summary

I've created the entity-device linking endpoint and improved classification logic. However, the endpoint needs the correct Home Assistant API path. Once the endpoint works, the process will:

1. **Link entities to devices** (using Home Assistant entity registry)
2. **Classify devices** (using domain-based classification)
3. **Verify filter works** (returns only matching device types)

---

## What's Been Done

### ✅ 1. Fixed Query and Filter

- Added `device_type` to SELECT query
- Fixed filter to exclude NULL and empty strings
- Filter now correctly returns 0 devices when filtering by "switch" (all unclassified)

### ✅ 2. Improved Classification Logic

- Added domain-based classification as PRIMARY method
- Maps entity domains directly to device_type:
  - `light` → `"light"`
  - `switch` → `"switch"`
  - `sensor` → `"sensor"`
  - etc.
- Pattern matching is now FALLBACK for complex devices

### ✅ 3. Created Entity-Device Linking Endpoint

**Endpoint:** `POST /api/devices/link-entities`

**Purpose:** Re-link entities to devices using Home Assistant API

**Process:**
1. Get all entities without `device_id` (NULL or empty)
2. Query Home Assistant entity registry API
3. Match entities to devices by `device_id`
4. Update entity `device_id` in database
5. Verify device exists before linking

**Status:** ⚠️ Endpoint created but needs correct HA API endpoint URL

### ✅ 4. Created Batch Classification Endpoint

**Endpoint:** `POST /api/devices/classify-all`

**Purpose:** Classify all unclassified devices

**Process:**
1. Get all devices without `device_type` (NULL or empty)
2. For each device, get entities
3. Extract entity domains
4. Classify using domain-based classification
5. Update `device_type` and `device_category` in database

**Status:** ✅ Ready - Will work once entities are linked

---

## Current Issue: Home Assistant API Endpoint

**Problem:** The entity registry endpoint returns 404

**Error:** `Failed to fetch entity registry from Home Assistant: 404`

**Possible Causes:**
1. Incorrect endpoint URL
2. Home Assistant version differences
3. API authentication issues

**Possible Endpoints to Try:**
- `/api/config/entity_registry/list` (websocket-style, might need POST)
- `/api/config/entity_registry` (REST endpoint)
- Alternative: Use websocket connection (as websocket-ingestion does)

---

## Next Steps

### Step 1: Fix Entity Registry API Endpoint

**Option A: Use REST API (if available)**
- Check correct endpoint in Home Assistant docs
- Verify authentication headers
- Test endpoint manually

**Option B: Use Existing Websocket Connection**
- Query websocket-ingestion service for entity registry
- Use cached entity-device mappings
- Create internal endpoint to get mappings

**Option C: Query Database Directly**
- If entities have `config_entry_id` or `unique_id`, use to match
- Match by area_id and name patterns
- Less reliable but no HA API dependency

### Step 2: Test Entity Linking

Once endpoint works:
```powershell
POST /api/devices/link-entities
```

**Expected Result:**
- Links entities to devices
- Returns count of linked entities

### Step 3: Run Classification

After entities are linked:
```powershell
POST /api/devices/classify-all
```

**Expected Result:**
- Classifies devices based on entity domains
- Updates `device_type` for all devices

### Step 4: Verify Filter

After classification:
```powershell
GET /api/devices?device_type=switch
```

**Expected Result:**
- Returns only devices with `device_type = "switch"`
- No devices with NULL or empty `device_type`

---

## Files Modified

1. ✅ `services/data-api/src/devices_endpoints.py`
   - Added `link_entities_to_devices()` endpoint
   - Fixed `classify_all_devices()` endpoint
   - Improved classification logic

2. ✅ `services/data-api/src/services/device_classifier.py`
   - Added `classify_device_from_domains()` method
   - Domain-based classification (no HA API needed)

3. ✅ `services/device-context-classifier/src/patterns.py`
   - Added domain-based classification
   - Domain-to-device-type mapping

4. ✅ `services/ai-automation-ui/src/components/ha-agent/DevicePicker.tsx`
   - Better empty state messages
   - More device type options

---

## Alternative Solution: Use Websocket-Ingestion Service

Since websocket-ingestion already has entity-device mappings cached, we could:

**Option 1: Create Internal Endpoint in websocket-ingestion**
- Expose entity-device mappings via internal API
- data-api calls websocket-ingestion for mappings
- More reliable (uses existing websocket connection)

**Option 2: Query Database Directly**
- Match entities by `config_entry_id` to devices
- Match by `area_id` and name patterns
- Use device metadata for classification

---

## Summary

**Status:** ⚠️ Entity linking endpoint created but needs correct HA API endpoint

**Next:** Fix entity registry API endpoint, then:
1. Link entities to devices ✅
2. Classify devices ✅
3. Verify filter works ✅

**Current Behavior:**
- Filter correctly returns 0 devices (all unclassified) ✅
- Classification ready but blocked by entity linking ⚠️
- Entity linking endpoint created but needs HA API fix ⚠️
