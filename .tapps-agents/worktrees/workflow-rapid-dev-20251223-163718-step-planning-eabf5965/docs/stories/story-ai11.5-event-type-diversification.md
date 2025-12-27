# Story AI11.5: Event Type Diversification

**Epic:** AI-11 - Realistic Training Data Enhancement  
**Story ID:** AI11.5  
**Type:** Feature  
**Points:** 4  
**Status:** ✅ **COMPLETE**  
**Estimated Effort:** 8-10 hours  
**Created:** December 2, 2025  
**Completed:** December 2, 2025

---

## Story Description

Expand event generation to include webhooks, scripts, scenes, voice commands, and API calls to reflect real-world Home Assistant event diversity.

**Current State:**
- Only `state_changed` events generated
- Missing automation triggers, script calls, scenes, voice commands
- Limited event diversity (3 types → 7+ types)

**Target:**
- Event type distribution matching real HA deployments
- Webhook trigger events (IFTTT, custom APIs)
- Script execution events (reusable components)
- Scene activation events (lighting/climate presets)
- Voice command events (Alexa, Google, Assist)
- API call events (external integrations)
- 7+ event types with proper distributions

---

## Acceptance Criteria

- [x] Event type distribution implemented (state_changed: 60%, automation_triggered: 15%, script_started: 8%, scene_activated: 5%, voice_command: 5%, webhook_triggered: 4%, api_call: 3%)
- [x] Webhook trigger events (IFTTT, custom APIs) implemented
- [x] Script execution events (reusable components) implemented
- [x] Scene activation events (lighting/climate presets) implemented
- [x] Voice command events (Alexa, Google, Assist) implemented
- [x] API call events (external integrations) implemented
- [x] Event types have realistic attributes and metadata
- [x] Unit tests for all event types (16 tests, all passing)
- [x] Event distribution matches target percentages (within tolerance)
- [x] Backward compatible with existing event generation

---

## Technical Approach

### Event Type Distribution

Events will be distributed according to:
- **state_change**: 60% - Device state changes (existing)
- **automation_trigger**: 15% - Automation triggered events
- **script_call**: 8% - Script execution events
- **scene_activation**: 5% - Scene activation events
- **voice_command**: 5% - Voice assistant commands
- **webhook_trigger**: 4% - Webhook-triggered events
- **api_call**: 3% - External API call events

### Event Structure

Each event type will have:
- `event_type`: Type identifier
- `entity_id`: Related entity (if applicable)
- `timestamp`: Event timestamp
- `attributes`: Type-specific attributes
- `context`: Event context (user, source, etc.)

---

## Tasks

### Task 1: Define Event Type Distributions
- [x] Create event type distribution configuration
- [x] Define event type probabilities
- [x] Add event type constants

### Task 2: Implement Event Type Generators
- [x] Implement `_generate_automation_trigger_event()`
- [x] Implement `_generate_script_call_event()`
- [x] Implement `_generate_scene_activation_event()`
- [x] Implement `_generate_voice_command_event()`
- [x] Implement `_generate_webhook_trigger_event()`
- [x] Implement `_generate_api_call_event()`

### Task 3: Update Event Generation Logic
- [x] Modify `generate_events()` to use event type distribution
- [x] Add event type selection logic
- [x] Ensure proper event type distribution

### Task 4: Unit Tests
- [x] Test each event type generation
- [x] Test event type distribution
- [x] Test event attributes and structure
- [x] Test integration with device generation
- [x] All 16 tests passing

---

## Files Modified

- `services/ai-automation-service/src/training/synthetic_event_generator.py`
- `services/ai-automation-service/tests/training/test_synthetic_event_generator.py` (new or update)

---

## Definition of Done

- [x] All 7 event types implemented
- [x] Event type distribution matches target (within 5% tolerance)
- [x] Event types have realistic attributes
- [x] Unit tests pass (16 tests, 100% pass rate, 94% code coverage)
- [x] Code follows 2025 patterns (Python 3.12+, type hints, async/await)
- [x] Documentation updated with event type descriptions

## Implementation Summary

**Files Modified:**
- `services/ai-automation-service/src/training/synthetic_event_generator.py`
  - Added `EVENT_TYPE_DISTRIBUTION` dictionary
  - Added event type constants (VOICE_PLATFORMS, WEBHOOK_SOURCES, API_SERVICES, SCENE_TYPES)
  - Added `_select_event_type()` method
  - Added `_generate_event_by_type()` method
  - Implemented 6 new event type generators:
    - `_generate_automation_trigger_event()`
    - `_generate_script_call_event()`
    - `_generate_scene_activation_event()`
    - `_generate_voice_command_event()`
    - `_generate_webhook_trigger_event()`
    - `_generate_api_call_event()`
  - Updated `generate_events()` to use event type distribution

**Files Created:**
- `services/ai-automation-service/tests/training/test_event_type_diversification.py`
  - 16 comprehensive unit tests
  - All tests passing

**Event Types Implemented:**
1. **state_changed**: 60% - Device state changes (existing, enhanced)
2. **automation_triggered**: 15% - Automation trigger events
3. **script_started**: 8% - Script execution events
4. **scene_activated**: 5% - Scene activation events
5. **voice_command**: 5% - Voice assistant commands (Alexa, Google, Assist, Siri)
6. **webhook_triggered**: 4% - Webhook-triggered events (IFTTT, Zapier, custom APIs)
7. **api_call**: 3% - External API call events

**Next Steps:**
- Story AI11.6 will add blueprint automation templates that use automation trigger events
- Story AI11.9 will validate end-to-end event type integration

---

## Related Stories

- **Story AI11.4**: Expanded Failure Scenario Library (failure scenarios can affect event types)
- **Story AI11.6**: Blueprint Automation Templates (uses automation trigger events)
- **Story AI11.9**: End-to-End Pipeline Integration (validates event type integration)

---

## Notes

- Event types should reflect real Home Assistant event patterns
- Distribution percentages are targets - actual distribution may vary slightly
- Some event types may not have direct entity associations (webhooks, API calls)
- Voice commands should include common assistant platforms (Alexa, Google, Assist)

