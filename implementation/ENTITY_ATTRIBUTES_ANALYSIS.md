# Entity Attributes Analysis

**Date:** October 29, 2025  
**Status:** ⚠️ Attributes NOT Currently Captured

## Summary

The user is correct that Hue room entities should have an `attributes.is_hue_group: true` attribute to distinguish them from individual lights. However, **entity attributes are not currently being captured or returned by the data-api**.

## Current Architecture

### What We DO Store

The `Entity` model in data-api (`services/data-api/src/models/entity.py`) stores:
- `entity_id` - Entity identifier
- `device_id` - Foreign key to device
- `domain` - Entity domain (light, sensor, etc.)
- `platform` - Integration platform
- `unique_id` - Unique ID within platform
- `area_id` - Room/area location
- `disabled` - Whether entity is disabled
- `created_at` - Creation timestamp

### What We DON'T Store

❌ **Entity attributes** - NOT stored in database
- No `attributes` column in `Entity` model
- No `friendly_name`, `is_hue_group`, `supported_features`, etc.

## Where Attributes ARE Available

### 1. Home Assistant WebSocket Events
Attributes are sent in `state_changed` events:
```json
{
  "event_type": "state_changed",
  "data": {
    "entity_id": "light.office",
    "old_state": {...},
    "new_state": {
      "entity_id": "light.office",
      "state": "on",
      "attributes": {
        "friendly_name": "Office",
        "is_hue_group": true,  // ✅ This attribute exists!
        "supported_features": 43,
        ...
      }
    }
  }
}
```

### 2. Websocket-Ingestion
The `_extract_state_changed_data` function in `event_processor.py` preserves `new_state` and `old_state` objects which include attributes.

### 3. InfluxDB
Full state objects (including attributes) are written to InfluxDB by websocket-ingestion.

## The Problem

### For `light.office` vs `light.hue_office_back_left`

**Without attributes**, we cannot tell the difference between:
- `light.office` - A Hue room entity (group) that controls multiple lights
- `light.hue_office_back_left` - An individual light entity

**The `is_hue_group` attribute would tell us:**
- `light.office` → `attributes.is_hue_group: true` ✅ **It's a group**
- `light.hue_office_back_left` → `attributes.is_hue_group: false` or missing ✅ **It's an individual light**

## Solution Options

### Option 1: Add Attributes to Entity Model
**Modify:** `services/data-api/src/models/entity.py`
```python
class Entity(Base):
    ...
    attributes = Column(JSON)  # Store full attributes dict
```

**Pros:**
- Single source of truth
- Fast lookups
- Can query by attributes

**Cons:**
- Larger database
- Need migration
- Attributes may change over time

### Option 2: Query Attributes from InfluxDB on Demand
**Use existing:** InfluxDB already has state data with attributes

**Pros:**
- No schema changes
- Always current data
- Uses existing infrastructure

**Cons:**
- Slower queries
- More complex code

### Option 3: Add Key Attributes to Entity Model
**Store only:** Selected attributes like `is_hue_group`, `friendly_name`, etc.

**Pros:**
- Balance between speed and storage
- Targeted solution

**Cons:**
- Need to decide which attributes matter
- Still need migration

## Recommendation

**Use Option 1** - Add full attributes JSON column to Entity model because:

1. **Entity resolution needs attributes** - The AI automation service needs to distinguish groups from individual lights
2. **Fast lookups** - Avoid querying InfluxDB for every entity lookup
3. **Rich metadata** - Other attributes (`friendly_name`, `supported_features`) are also useful
4. **Existing data** - We already capture this in InfluxDB, just need to extract and store it

## Implementation Steps

1. **Add attributes column** to Entity model
2. **Extract attributes** from websocket-ingestion events
3. **Store attributes** when upserting entities
4. **Update EntityResponse** to include attributes
5. **Query attributes** in entity resolution service

## Impact on Entity Resolution

Once attributes are available, we can:

```python
# In entity_resolver.py
if entity.attributes.get("is_hue_group") == True:
    logger.info(f"{entity_id} is a Hue room group")
    # Use room entity for controlling all lights
else:
    logger.info(f"{entity_id} is an individual light")
    # Use for specific light control
```

This will enable the AI automation service to correctly distinguish between room groups and individual lights when generating YAML automations.

