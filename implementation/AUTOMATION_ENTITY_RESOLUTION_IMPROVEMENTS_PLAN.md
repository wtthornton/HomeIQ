# Automation Entity Resolution Improvements Plan

**Date:** 2026-01-16  
**Issue:** Unknown entity warnings in Home Assistant UI after automation creation  
**Root Cause:** Scene pre-creation fails when entities are unavailable or validation is insufficient

## Improvement Summary

This plan addresses the root causes of "Unknown entity" warnings in Home Assistant automations by improving entity validation, scene pre-creation reliability, and entity resolution patterns.

## Priority 1: Entity Availability Validation Before Scene Pre-Creation

### Problem
Scene pre-creation attempts to create scenes with entities that may be unavailable, causing silent failures and UI warnings.

### Solution
Add entity availability checks before scene pre-creation:

1. **Check entity state** before calling scene.create
2. **Validate entity exists** in Home Assistant
3. **Retry logic** for transient unavailability
4. **Clear error reporting** when validation fails

### Implementation
- **File:** `services/ha-ai-agent-service/src/tools/ha_tools.py`
- **Method:** `_pre_create_scenes()` - Add entity availability validation
- **Method:** `_validate_entity_availability()` - New helper method

### Testing
- Test with unavailable entity → should log warning but continue
- Test with available entity → should create scene successfully
- Test with entity becoming available during retry → should succeed on retry

## Priority 2: Enhanced Entity Resolution for "Switch LED" Patterns

### Problem
"office switches LED" is ambiguous and entity resolution may not match correctly.

### Solution
Improve entity resolution to handle combined device descriptions:

1. **Pattern matching** for "switch LED" (LED indicator on switch)
2. **Device relationship awareness** (switch → LED indicator light)
3. **Better keyword matching** for combined descriptions

### Implementation
- **File:** `services/ha-ai-agent-service/src/services/entity_resolution/entity_resolution_service.py`
- **Method:** `_extract_device_type_keywords()` - Enhance for combined patterns
- **Method:** `_score_entities()` - Improve scoring for device relationships

### Testing
- Test "office switches LED" → should resolve to `light.office_go`
- Test "switch LED indicator" → should find LED entities associated with switches
- Test confidence scores → should be high for correct matches

## Priority 3: System Prompt Entity Validation Guidance

### Problem
System prompt doesn't emphasize entity availability checks before scene creation.

### Solution
Update system prompt to include entity availability validation:

1. **Add to pre-generation checklist** - Entity availability check
2. **Emphasize validation** - Verify entities are available before scene.create
3. **Guidance for unavailable entities** - How to handle when entities are unavailable

### Implementation
- **File:** `services/ha-ai-agent-service/src/prompts/system_prompt.py`
- **Section:** Pre-Generation Validation Checklist
- **Section:** Scene Creation Best Practices

### Testing
- Verify prompt includes entity availability checks
- Verify LLM follows validation guidance
- Test automations created with updated prompt

## Priority 4: Improved Error Handling and User Feedback

### Problem
Silent failures during scene pre-creation don't provide user feedback.

### Solution
Enhance error handling and user notifications:

1. **Explicit warnings** in preview response when entities unavailable
2. **User notifications** when scene pre-creation fails
3. **Success verification** after scene creation
4. **Retry mechanism** with exponential backoff

### Implementation
- **File:** `services/ha-ai-agent-service/src/tools/ha_tools.py`
- **Method:** `_create_automation_in_ha()` - Add user feedback for scene pre-creation
- **Response:** Include scene pre-creation results in creation response

### Testing
- Test with unavailable entity → should show warning in response
- Test scene pre-creation success → should report success
- Test retry logic → should retry on transient failures

## Implementation Order

1. **Priority 1** - Entity availability validation (critical for preventing failures)
2. **Priority 3** - System prompt updates (guides LLM behavior)
3. **Priority 2** - Entity resolution improvements (better matching)
4. **Priority 4** - Error handling enhancements (user experience)

## Success Criteria

- ✅ No "Unknown entity" warnings when entities are available
- ✅ Clear warnings when entities are unavailable (instead of silent failure)
- ✅ Scene pre-creation success rate > 95% for available entities
- ✅ Entity resolution accuracy > 90% for "switch LED" patterns
- ✅ User receives clear feedback about scene pre-creation status

## Metrics to Track

- Scene pre-creation success rate
- Entity availability validation accuracy
- Entity resolution confidence scores for "switch LED" patterns
- User-reported "Unknown entity" warnings

## Timeline

- **Phase 1** (Priority 1): 1-2 hours - Entity availability validation
- **Phase 2** (Priority 3): 30 minutes - System prompt updates
- **Phase 3** (Priority 2): 1-2 hours - Entity resolution improvements
- **Phase 4** (Priority 4): 1 hour - Error handling enhancements

**Total Estimated Time:** 3.5-5.5 hours
