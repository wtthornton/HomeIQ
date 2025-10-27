# Device Intelligence Service - Field Population Analysis

**Date:** October 27, 2025  
**Service:** device-intelligence-service  
**Issue:** Manufacturer, model, integration fields showing as "Unknown" in database

---

## Executive Summary

The Device Intelligence Service database shows **all devices with manufacturer="Unknown"** even though Home Assistant provides this data. Analysis reveals that the service **correctly fetches manufacturer data** from HA, but there's a mismatch between what the parser receives from HA and what gets stored in the database.

---

## 1. Data Flow Analysis

### 1.1 Current Data Pipeline

```
Home Assistant API (HA_API)
    ↓
HA WebSocket Client (ha_client.py)
    ↓ GETS: manufacturer, model, integration
    ↓
DeviceParser (device_parser.py)
    ↓ PARSE: Creates UnifiedDevice with HA data
    ↓
DiscoveryService (discovery_service.py)
    ↓ STORES: Bulk upsert to database
    ↓
SQLite Database (devices table)
    ↓ ISSUE: manufacturer="Unknown" in DB
```

### 1.2 Code Location for Data Fetching

**File:** `services/device-intelligence-service/src/clients/ha_client.py`

**Line 292-294:** Manufacturer and model ARE being extracted from HA API:
```python
manufacturer=device_data.get("manufacturer"),
model=device_data.get("model"),
integration=device_data.get("integration"),
```

---

## 2. Root Cause Analysis

### 2.1 DeviceParser Logic

**File:** `services/device-intelligence-service/src/core/device_parser.py`

**Line 131:** Parsing logic for manufacturer field:
```python
manufacturer=ha_device.manufacturer or zigbee_device.manufacturer if zigbee_device else "Unknown",
```

**Key Finding:** The parser correctly tries to get manufacturer from HA device first, then falls back to Zigbee device. If neither exists, it defaults to "Unknown".

### 2.2 The Actual Problem

**Hypothesis:** Home Assistant API returns `manufacturer: null` for devices that don't have this field populated in HA's device registry.

**Evidence from Database:**
```json
{
  "device_id": "1ba44a8f25eab1397cb48dd7b743edcd",
  "name": "Sun",
  "manufacturer": "Unknown",  // ← This is NULL in HA, becomes "Unknown" in our DB
  "model": "Unknown",
  "integration": "Unknown"     // ← Also NULL
}
```

**Confirmation:** Lines 131-132 in device_parser.py show:
- If `ha_device.manufacturer` is `None`, it falls back to Zigbee or defaults to "Unknown"
- `ha_device.manufacturer` is likely NULL in HA's response for most devices

---

## 3. Database Schema Review

### 3.1 Current Schema

**File:** `services/device-intelligence-service/src/models/database.py`

**Lines 17-56:** Device table definition:
```python
class Device(Base):
    __tablename__ = 'devices'
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    manufacturer: Mapped[Optional[str]] = mapped_column(String)        # ✅ Optional
    model: Mapped[Optional[str]] = mapped_column(String)                 # ✅ Optional
    area_id: Mapped[Optional[str]] = mapped_column(String, index=True)   # ✅ Optional
    area_name: Mapped[Optional[str]] = mapped_column(String)             # ✅ Optional
    integration: Mapped[str] = mapped_column(String, nullable=False)      # ⚠️ REQUIRED but wrong
    ...
```

### 3.2 Schema Issues Identified

| Field | Current Definition | Issue | Impact |
|-------|------------------|-------|--------|
| `integration` | `nullable=False` | Home Assistant returns NULL for some devices | Throws errors, uses "unknown" fallback |
| `manufacturer` | `Optional[str]` | HA returns NULL for many devices | Stores as "Unknown" |
| `model` | `Optional[str]` | HA returns NULL for many devices | Stores as "Unknown" |
| `area_id` | `Optional[str]` | Most devices have NULL area | Missing spatial data |
| `area_name` | `Optional[str]` | Not populated from HA | Missing area name |
| `sw_version` | `Optional[str]` | Missing in HA response | NULL in database |
| `hw_version` | `Optional[str]` | Missing in HA response | NULL in database |

---

## 4. Storage Process Analysis

### 4.1 Data Conversion

**File:** `services/device-intelligence-service/src/core/discovery_service.py`

**Lines 251-270:** Converting UnifiedDevice to database format:

```python
device_data = {
    "id": device.id,
    "name": device.name,
    "manufacturer": device.manufacturer,              # ← Gets "Unknown" from parser
    "model": device.model,                            # ← Gets "Unknown" from parser
    "area_id": device.area_id,
    "integration": device.integration or "unknown",    # ← Fallback adds "unknown"
    ...
}
```

**Line 259:** Integration fallback logic:
```python
"integration": device.integration or "unknown",  # Provide default for NOT NULL constraint
```

This proves the schema requires `integration` to be NOT NULL, but HA sometimes returns NULL.

### 4.2 Bulk Upsert

**File:** `services/device-intelligence-service/src/core/repository.py`

**Lines 186-207:** Bulk upsert logic handles the data correctly. No issues in storage.

---

## 5. Why "Unknown" Values?

### 5.1 Home Assistant Device Registry Reality

**Not All Devices Have Manufacturer Data:**
- Built-in entities (Sun, Home Assistant Core, etc.) have no manufacturer
- Third-party integrations vary in data quality
- Zigbee devices may have manufacturer via Zigbee2MQTT, but not HA registry

### 5.2 Current Parser Behavior

**Lines 131-149 in device_parser.py:**
```python
unified_device = UnifiedDevice(
    manufacturer=ha_device.manufacturer or zigbee_device.manufacturer if zigbee_device else "Unknown",
    model=ha_device.model or zigbee_device.model if zigbee_device else "Unknown",
    integration=ha_device.integration,  # Could be None from HA
    ...
)
```

**The Logic:**
1. Try `ha_device.manufacturer` (often None)
2. Try `zigbee_device.manufacturer` (if Zigbee device exists)
3. Default to "Unknown"

### 5.3 Why Integration is "Unknown"

**Line 259 in discovery_service.py:**
```python
"integration": device.integration or "unknown",
```

This indicates that `device.integration` (from parser) can be None/NULL, forcing the fallback to "unknown".

---

## 6. Database Fields Audit

### 6.1 Fields That Work

✅ **Populated Correctly:**
- `id` - Device ID from HA
- `name` - Device name from HA
- `created_at` - Timestamp
- `updated_at` - Timestamp
- `entity_count` - Calculated from entities

### 6.2 Fields Missing Data

❌ **Frequently NULL:**
- `manufacturer` - NULL from HA for most devices → Stored as "Unknown"
- `model` - NULL from HA for most devices → Stored as "Unknown"
- `integration` - NULL from HA → Defaults to "unknown"
- `area_id` - NULL for many devices → Missing area mapping
- `area_name` - NOT extracted from HA area registry → Always NULL
- `sw_version` - Missing in HA API response
- `hw_version` - Missing in HA API response
- `power_source` - Only available from Zigbee devices
- `via_device_id` - Rarely populated

### 6.3 Missing Fields (Should Add)

🔴 **Not Currently Stored:**
- `device_class` - Device type classification
- `suggested_area` - HA's suggested area
- `config_entries` - HA integration config entries
- `connections` - Physical connections (MAC, IP, etc.)
- `identifiers` - Device identifiers (important for Zigbee)
- `zigbee_ieee` - IEEE address for Zigbee devices (if separate from identifiers)
- `device_type` - Light, sensor, switch, etc.
- `is_battery_powered` - Power source indicator
- `supports_zigbee` - Has Zigbee data available

---

## 7. Recommendations

### 7.1 Immediate Fixes

#### 7.1.1 Add Area Name Extraction

**File:** `services/device-intelligence-service/src/core/device_parser.py`  
**Line 123-125:** Already gets area name but not stored in schema

**Add to database schema:**
```python
area_name: Mapped[Optional[str]] = mapped_column(String)  # ← Already in schema!
```

**Fix storage logic:**
```python
# In discovery_service.py line 259
device_data = {
    ...
    "area_name": device.area_name,  # ← Already calculated in parser line 125!
    ...
}
```

#### 7.1.2 Store Integration Correctly

**Line 259 in discovery_service.py:**
```python
# CURRENT:
"integration": device.integration or "unknown",

# SHOULD BE:
"integration": ha_device.integration if ha_device else "unknown",
```

The issue is that `device.integration` is the UnifiedDevice field, but we need to check the original HA device.

### 7.2 Schema Improvements

#### 7.2.1 Add Missing Fields

Update `services/device-intelligence-service/src/models/database.py` Device class:

```python
class Device(Base):
    # EXISTING FIELDS...
    
    # ADD THESE:
    device_class: Mapped[Optional[str]] = mapped_column(String)
    config_entry_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    connections_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)  # MAC, IP, etc.
    identifiers_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)   # Device IDs
    zigbee_ieee: Mapped[Optional[str]] = mapped_column(String, index=True)
    is_battery_powered: Mapped[bool] = mapped_column(Boolean, default=False)
    device_type: Mapped[Optional[str]] = mapped_column(String, index=True)
```

#### 7.2.2 Migration Strategy

```sql
-- Add new columns with default values
ALTER TABLE devices ADD COLUMN device_class TEXT;
ALTER TABLE devices ADD COLUMN config_entry_id TEXT;
ALTER TABLE devices ADD COLUMN connections_json JSON;
ALTER TABLE devices ADD COLUMN identifiers_json JSON;
ALTER TABLE devices ADD COLUMN zigbee_ieee TEXT;
ALTER TABLE devices ADD COLUMN is_battery_powered INTEGER DEFAULT 0;
ALTER TABLE devices ADD COLUMN device_type TEXT;

-- Create indexes
CREATE INDEX idx_devices_config_entry_id ON devices(config_entry_id);
CREATE INDEX idx_devices_zigbee_ieee ON devices(zigbee_ieee);
CREATE INDEX idx_devices_device_type ON devices(device_type);
```

### 7.3 Code Fixes

#### 7.3.1 Fix Integration Storage

**File:** `services/device-intelligence-service/src/core/discovery_service.py`

**Line 256-259:** Update to use HA device integration:
```python
# BEFORE:
"integration": device.integration or "unknown",

# AFTER:
"integration": ha_device.integration if ha_device and ha_device.integration else "unknown",
```

#### 7.3.2 Add Device Class Extraction

**File:** `services/device-intelligence-service/src/core/device_parser.py`

**Line 128-149:** Add device class to UnifiedDevice:
```python
unified_device = UnifiedDevice(
    ...
    device_class=self._extract_device_class(ha_device, device_entities),
    ...
)

def _extract_device_class(self, ha_device, entities):
    """Extract device class from entities."""
    for entity in entities:
        if entity.domain == 'light':
            return 'light'
        elif entity.domain == 'sensor':
            return 'sensor'
        # Add more logic...
    return None
```

---

## 8. GUI Automation vs Database Comparison

### 8.1 What GUI Shows

From user's screenshot:
- **Office device:** "Signify Netherlands B.V."
- **Area:** office
- **Entity IDs:** Available (device_id, entity_id)
- **Integration:** hue

### 8.2 What Database Stores

Current database shows:
- **Manufacturer:** "Unknown"
- **Model:** "Unknown"  
- **Integration:** "Unknown"
- **Area:** office (but area_name is missing)

### 8.3 The Disconnect

The GUI pulls **live data from Home Assistant API**, while the database has **stale data** from Device Intelligence service discovery.

**Root cause:** The Device Intelligence discovery service is not storing the data correctly that HA provides.

---

## 9. Files Requiring Changes

| File | Purpose | Changes Needed |
|------|---------|---------------|
| `src/models/database.py` | Schema definition | Add new fields: device_class, config_entry_id, connections_json, etc. |
| `src/core/device_parser.py` | Data parsing | Extract device_class, store more HA fields |
| `src/core/discovery_service.py` | Data storage | Fix integration storage, add area_name storage |
| `src/clients/ha_client.py` | HA API client | Already fetches all needed data ✅ |

---

## 10. Testing Plan

### 10.1 Verification Steps

1. **Check HA API Response:**
```python
# Test what HA actually returns
response = await ha_client.get_device_registry()
for device in response:
    print(f"{device.name}: manufacturer={device.manufacturer}, integration={device.integration}")
```

2. **Verify Storage:**
```python
# After storage, verify database
SELECT name, manufacturer, model, integration, area_id, area_name 
FROM devices 
WHERE name LIKE '%Office%';
```

3. **Compare GUI vs Database:**
- Take screenshot of HA GUI for "Office" device
- Query database for same device
- Compare fields

### 10.2 Expected Results After Fix

- ✅ `manufacturer` = "Signify Netherlands B.V." (not "Unknown")
- ✅ `model` = actual model number
- ✅ `integration` = "hue" (not "Unknown")
- ✅ `area_name` = "office" (not NULL)
- ✅ `device_class` = "light"
- ✅ `config_entry_id` = Hue bridge config entry ID

---

## 11. Implementation Priority

### Priority 1: Critical Fixes (Do First)
1. ✅ Fix `area_name` storage (already in code, not stored)
2. ✅ Fix `integration` storage (using "unknown" fallback)
3. ✅ Investigate why `manufacturer` is NULL in HA response

### Priority 2: Schema Enhancements
4. Add `device_class` field
5. Add `config_entry_id` field
6. Add `connections_json` and `identifiers_json` fields

### Priority 3: Data Enrichment
7. Extract and store device type from entities
8. Add battery-powered indicator
9. Store Zigbee IEEE address separately

---

## 12. Conclusion

The Device Intelligence Service **correctly fetches data from Home Assistant**, but:

1. **Missing Fields:** `area_name` is calculated but never stored in database
2. **Incorrect Fallback:** Integration defaults to "unknown" when HA returns NULL
3. **Database Schema:** Lacks fields for device type, connections, and identifiers
4. **Parser Logic:** Needs to extract device class from entities

**The root cause:** The parser receives `manufacturer: None` from Home Assistant for most devices. This suggests either:
- HA device registry doesn't have manufacturer data populated
- The HA device data structure is being read incorrectly

**Next Steps:**
1. Debug HA API response to see actual manufacturer values
2. Fix area_name storage
3. Fix integration storage logic
4. Add device class extraction
5. Run migration to add missing fields
6. Re-run discovery service to populate with correct data

---

## Appendix: SQL Queries for Analysis

```sql
-- Check current data quality
SELECT 
    COUNT(*) as total_devices,
    COUNT(CASE WHEN manufacturer != 'Unknown' THEN 1 END) as with_manufacturer,
    COUNT(CASE WHEN model != 'Unknown' THEN 1 END) as with_model,
    COUNT(CASE WHEN integration != 'unknown' THEN 1 END) as with_integration,
    COUNT(CASE WHEN area_name IS NOT NULL THEN 1 END) as with_area_name
FROM devices;

-- Find all manufacturers
SELECT DISTINCT manufacturer, COUNT(*) 
FROM devices 
GROUP BY manufacturer 
ORDER BY COUNT(*) DESC;

-- Check Office devices specifically
SELECT name, manufacturer, model, integration, area_name 
FROM devices 
WHERE name LIKE '%Office%' OR area_name = 'office';
```

