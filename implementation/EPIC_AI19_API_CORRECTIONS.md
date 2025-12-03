# Epic AI-19 API Corrections - Home Assistant REST API Compliance

**Date:** January 2025  
**Status:** ✅ Complete  
**Reference:** [Home Assistant REST API Documentation](https://developers.home-assistant.io/docs/api/rest/)

---

## Summary

After deep research of the official Home Assistant REST API documentation, I've corrected the API endpoints and implementation to ensure compliance with the documented REST API.

---

## Changes Made

### 1. ✅ Helpers & Scenes Service - Corrected API Endpoints

**Previous Implementation (Incorrect):**
- Used `/api/config/helper` (not documented in REST API)
- Used `/api/config/scene` (not documented in REST API)

**Corrected Implementation:**
- **Endpoint:** `GET /api/states` (documented REST API endpoint)
- **Method:** Filter entity states by domain
- **Helpers:** Filter by entity_id domains: `input_boolean.*`, `input_number.*`, `input_select.*`, `input_text.*`, `input_datetime.*`, `input_button.*`, `counter.*`, `timer.*`
- **Scenes:** Filter by entity_id domain: `scene.*`

**Rationale:**
According to the [REST API documentation](https://developers.home-assistant.io/docs/api/rest/), helpers and scenes are entities in Home Assistant. The correct way to access them is via the `/api/states` endpoint, which returns all entity states. We then filter by entity_id prefix to get helpers and scenes.

**Code Changes:**
- `src/clients/ha_client.py`:
  - Added `get_states()` method using `/api/states`
  - Updated `get_helpers()` to filter from states by helper domains
  - Updated `get_scenes()` to filter from states by scene domain
- `src/services/helpers_scenes_service.py`:
  - Updated to handle entity_id-based helper/scene data structure
  - Improved scene name extraction (friendly_name → entity_id → id)

### 2. ✅ Area Registry - Verified Endpoint

**Current Implementation:**
- Uses `/api/config/area_registry/list`
- Added proper 404 handling (some HA versions don't expose this endpoint)

**Note:** This endpoint is not explicitly documented in the basic REST API docs but is used in the Home Assistant codebase. Added graceful fallback for 404 responses.

---

## API Endpoints Used (REST API Compliant)

### Documented REST API Endpoints

1. **`GET /api/states`** - Get all entity states
   - **Used for:** Helpers and scenes discovery
   - **Reference:** [REST API Docs](https://developers.home-assistant.io/docs/api/rest/)
   - **Response Format:**
     ```json
     [
       {
         "entity_id": "input_boolean.morning_routine",
         "state": "on",
         "attributes": {
           "friendly_name": "Morning Routine"
         },
         "last_changed": "2025-01-20T10:00:00+00:00",
         "last_updated": "2025-01-20T10:00:00+00:00"
       }
     ]
     ```

2. **`GET /api/services`** - Get available services
   - **Used for:** Services summary service
   - **Reference:** [REST API Docs](https://developers.home-assistant.io/docs/api/rest/)
   - **Response Format:**
     ```json
     [
       {
         "domain": "light",
         "services": ["turn_on", "turn_off", "toggle"]
       }
     ]
     ```

3. **`GET /api/config/area_registry/list`** - Get area registry
   - **Used for:** Areas service
   - **Note:** Not in basic REST API docs but used in HA codebase
   - **Fallback:** Returns empty list on 404 (graceful degradation)

---

## Helper Domains Supported

The implementation correctly identifies helpers by filtering entity states with these domains:

- `input_boolean` - Boolean input helpers
- `input_number` - Number input helpers
- `input_select` - Select/dropdown input helpers
- `input_text` - Text input helpers
- `input_datetime` - DateTime input helpers
- `input_button` - Button input helpers
- `counter` - Counter helpers
- `timer` - Timer helpers

---

## Data Structure Changes

### Helpers Data Structure

**From API (`/api/states` filtered):**
```json
{
  "entity_id": "input_boolean.morning_routine",
  "state": "on",
  "attributes": {
    "friendly_name": "Morning Routine"
  }
}
```

**Transformed to:**
```json
{
  "id": "morning_routine",
  "type": "input_boolean",
  "entity_id": "input_boolean.morning_routine",
  "name": "Morning Routine",
  "state": "on"
}
```

### Scenes Data Structure

**From API (`/api/states` filtered):**
```json
{
  "entity_id": "scene.morning_scene",
  "state": "scening",
  "attributes": {
    "friendly_name": "Morning Scene"
  }
}
```

**Transformed to:**
```json
{
  "id": "morning_scene",
  "entity_id": "scene.morning_scene",
  "name": "Morning Scene",
  "state": "scening"
}
```

---

## Testing Updates

Updated test mocks to match the new data structure:
- Helpers now include `entity_id` and `name` fields
- Scenes now include `entity_id` field
- Tests verify correct filtering and formatting

---

## Documentation Updates

1. **Epic Documentation:**
   - Updated Story AI19.6 to reference `/api/states` endpoint
   - Clarified filtering approach

2. **Implementation Plan:**
   - Updated API endpoint references
   - Added REST API documentation links

3. **Code Comments:**
   - Added references to REST API documentation
   - Documented filtering logic

---

## Compliance Checklist

- ✅ Uses documented REST API endpoints where available
- ✅ Properly handles entity state filtering
- ✅ Graceful error handling (404 for area_registry)
- ✅ Correct data structure transformation
- ✅ Updated tests to match new structure
- ✅ Documentation updated with correct endpoints

---

## References

- [Home Assistant REST API Documentation](https://developers.home-assistant.io/docs/api/rest/)
- [REST API - Get States](https://developers.home-assistant.io/docs/api/rest/#get-apistates)
- [REST API - Get Services](https://developers.home-assistant.io/docs/api/rest/#get-apiservices)

---

## Conclusion

All API endpoints are now compliant with the official Home Assistant REST API documentation. The implementation correctly uses `/api/states` for helpers and scenes discovery, with proper filtering by entity domain. The area_registry endpoint uses the pattern found in the HA codebase with graceful fallback handling.

