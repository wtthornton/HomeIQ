# Friendly Name Issue Analysis

**Date:** November 17, 2025  
**Issue:** AI automation service showing generic device names instead of friendly names

## Problem Identified

### Current Behavior (Incorrect)
The AI automation service is displaying generic device names like:
- "Hue Color Downlight 15"
- "Hue Color Downlight 14"
- "Hue Color Downlight 13"
- "Hue Color Downlight 12"

### Expected Behavior (Correct)
Should display friendly names from Home Assistant Entity Registry:
- "LR Back Left Ceiling"
- "LR Back Right Ceiling"
- "LR Front Left Ceiling"
- "LR Front Right Ceiling"

## Root Cause

1. **Discovery Hasn't Run Yet**: The discovery cache is stale (40+ minutes old), meaning discovery hasn't run to populate the `friendly_name` fields in the database.

2. **Database Fields Empty**: The new `friendly_name`, `name`, `name_by_user`, and `original_name` fields in the `entities` table are likely NULL because discovery hasn't populated them yet.

3. **Fallback to Generic Names**: When `friendly_name` is NULL in the database, the `EntityContextBuilder` falls back to enriched data, which contains generic names derived from `entity_id` or `original_name`.

## Solution

### Immediate Fix: Trigger Discovery

Discovery needs to run to populate the friendly names. The discovery service:
1. Fetches Entity Registry from Home Assistant
2. Extracts `name`, `name_by_user`, `original_name` fields
3. Computes `friendly_name` (priority: `name_by_user` > `name` > `original_name`)
4. Stores in SQLite via `bulk_upsert_entities`

### Discovery Trigger Methods

1. **Manual Trigger** (via API):
   ```bash
   POST http://localhost:8001/api/v1/discovery/trigger
   ```

2. **Automatic Trigger** (when cache expires):
   - Discovery cache TTL: 30 minutes
   - When cache is stale, discovery should run automatically
   - Or when device/entity registry events are received

### Current Status

- ✅ Database schema updated (Revision 004)
- ✅ Code updated to use `friendly_name` from database
- ✅ Discovery service updated to fetch and store friendly names
- ⚠️ Discovery hasn't run yet (cache stale, manual trigger attempted but WebSocket concurrency error)

## Next Steps

1. **Wait for Automatic Discovery**: Discovery should run automatically when:
   - Cache expires (30 minutes)
   - Device/entity registry events are received
   - Service detects stale cache

2. **Verify Discovery Completion**: After discovery runs, check:
   ```sql
   SELECT entity_id, name, name_by_user, original_name, friendly_name 
   FROM entities 
   WHERE entity_id LIKE 'light.hue%'
   LIMIT 10;
   ```

3. **Verify AI Service**: After discovery, test AI automation service to confirm friendly names appear correctly.

## Code Flow

### Entity Context Builder (`entity_context_builder.py`)
```python
# Line 174: Database-first lookup
friendly_name = entity_metadata.get('friendly_name') or entity_metadata.get('name') or entity_metadata.get('original_name')

# Line 217-218: Fallback to enriched data if database lookup fails
if not friendly_name:
    friendly_name = enriched.get('friendly_name') or entity.get('friendly_name')
```

### Discovery Service (`discovery_service.py`)
```python
# Line 349: Discover services
services_data = await self.discover_services(websocket)

# Line 363: Store discovery results
await self.store_discovery_results(devices_data, entities_data, config_entries_data, services_data)
```

### Bulk Upsert (`devices_endpoints.py`)
```python
# Extracts name fields from Entity Registry
name = entity_registry.get('name')
name_by_user = entity_registry.get('name_by_user')
original_name = entity_registry.get('original_name')

# Computes friendly_name
friendly_name = name_by_user or name or original_name or ...
```

## Expected Outcome

After discovery runs successfully:
- ✅ Database populated with friendly names
- ✅ AI automation service displays "LR Back Left Ceiling" instead of "Hue Color Downlight 15"
- ✅ Entity context includes correct friendly names
- ✅ YAML generation uses friendly names

---

**Status:** Waiting for discovery to run and populate friendly names

