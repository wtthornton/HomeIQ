# Epic AI-19 Replacement Plan: Helpers & Scenes Summary Service

**Date:** January 2025  
**Status:** Plan  
**Replaces:** Story AI19.6 (Sun/Sunrise/Sunset Info Service)

---

## Executive Summary

After researching Home Assistant best practices and documentation, we're replacing the Sun Info Service with a **Helpers & Scenes Summary Service** that provides more actionable context for automation generation.

---

## Why Replace Sun Info Service?

### Issues with Sun Info Service:
1. **Limited Value** - Sun times can be calculated on-demand or accessed via sun entity
2. **Redundant** - Home Assistant already has `sun.sun` entity with sunrise/sunset attributes
3. **Low Context Value** - Doesn't help agent understand available automation components
4. **Better Alternatives** - Agent can query sun entity directly when needed

### Benefits of Helpers & Scenes Summary:
1. **High Context Value** - Shows reusable components available for automations
2. **Actionable** - Agent knows what helpers/scenes exist to use in automations
3. **Best Practice Alignment** - Helpers and scenes are core HA automation patterns
4. **Reduces Tool Calls** - Pre-loads information about available reusable components

---

## New Service: Helpers & Scenes Summary Service

### Purpose
Provide summary of available Home Assistant helpers and scenes that can be used in automations. This gives the agent immediate awareness of reusable components without making tool calls.

### Home Assistant API Endpoints

**Based on REST API Documentation:** https://developers.home-assistant.io/docs/api/rest/

**Helpers & Scenes:**
- `/api/states` - Get all entity states (REST API endpoint)
- Filter helpers by entity_id prefix: `input_boolean.*`, `input_number.*`, `input_select.*`, `input_text.*`, `input_datetime.*`, `input_button.*`, `counter.*`, `timer.*`
- Filter scenes by entity_id prefix: `scene.*`

**Note:** Helpers and scenes are entities in Home Assistant, so they're accessed via the `/api/states` endpoint and filtered by domain.

### Context Format

```
HELPERS:
- input_boolean: morning_routine, night_mode, guest_mode (3 helpers)
- input_number: brightness_level, temperature_setpoint (2 helpers)
- input_select: lighting_mode (options: dim, bright, off), fan_speed (options: low, medium, high) (2 helpers)

SCENES:
- Morning Scene, Evening Scene, Movie Scene, Away Scene (4 scenes)
```

### Cache Strategy
- **TTL:** 10 minutes (helpers/scenes change infrequently)
- **Cache Key:** `helpers_scenes_summary`

---

## Implementation Plan

### Story AI19.6 (Replacement): Helpers & Scenes Summary Service

**Type:** Feature  
**Points:** 2  
**Effort:** 4-6 hours

**Acceptance Criteria:**
- `HelpersScenesService` class created
- Query Home Assistant `/api/config/helper` endpoint
- Query Home Assistant `/api/config/scene` endpoint
- Group helpers by type (input_boolean, input_number, input_select, etc.)
- Format: "input_boolean: morning_routine, night_mode, guest_mode (3 helpers)"
- Include scene names in simple list
- Cache summary with 10-minute TTL
- Handle empty/invalid responses gracefully
- Unit tests with >90% coverage
- Integration test with Home Assistant API

**Technical Notes:**
- Helpers and scenes change rarely, longer cache TTL acceptable
- Focus on helper types and names, not full configurations
- Max 300 tokens for helpers/scenes summary
- Format: Helper type → names → count, then scene names list

---

## Code Changes Required

### 1. Remove Sun Info Service
- Delete `src/services/sun_info_service.py`
- Delete `tests/test_sun_info_service.py`
- Remove from `context_builder.py`
- Remove `astral` dependency from `requirements.txt`

### 2. Create Helpers & Scenes Service
- Create `src/services/helpers_scenes_service.py`
- Add helper methods to `ha_client.py`:
  - `get_helpers()` - Query `/api/config/helper`
  - `get_scenes()` - Query `/api/config/scene`
- Integrate into `context_builder.py`
- Create `tests/test_helpers_scenes_service.py`

### 3. Update Epic Documentation
- Update `docs/prd/epic-ai19-ha-ai-agent-tier1-context-injection.md`
- Replace Story AI19.6 description
- Update context format examples

### 4. Update README
- Update service documentation
- Remove sun info references
- Add helpers/scenes references

---

## Context Builder Integration

The new service will be integrated into `ContextBuilder.build_context()`:

```python
# Story AI19.6 - Helpers & Scenes Summary
try:
    helpers_scenes_summary = await self._helpers_scenes_service.get_summary()
    context_parts.append(f"HELPERS & SCENES:\n{helpers_scenes_summary}\n")
except Exception as e:
    logger.warning(f"⚠️ Failed to get helpers/scenes: {e}")
    context_parts.append("HELPERS & SCENES: (unavailable)\n")
```

---

## Testing Strategy

### Unit Tests
- Test with helpers grouped by type
- Test with scenes list
- Test empty responses
- Test cached responses
- Test API error handling

### Integration Tests
- Test with real Home Assistant API
- Verify helper grouping
- Verify scene extraction
- Verify cache behavior

---

## Benefits

1. **More Actionable Context** - Agent knows what reusable components exist
2. **Reduces Tool Calls** - Pre-loaded helper/scene information
3. **Best Practice Alignment** - Aligns with HA best practices for reusable components
4. **Better Automation Suggestions** - Agent can suggest using existing helpers/scenes
5. **Maintainability** - Helpers/scenes are core HA concepts, more stable than sun calculations

---

## Migration Notes

- No breaking changes to API endpoints
- Context format changes (removes SUN INFORMATION, adds HELPERS & SCENES)
- Cache keys change (removes `sun_info`, adds `helpers_scenes_summary`)
- Dependencies change (removes `astral`, no new dependencies needed)

---

## Next Steps

1. ✅ Create this plan
2. Update epic documentation
3. Update story AI19.6
4. Implement helpers_scenes_service
5. Remove sun_info_service
6. Update tests
7. Update README

