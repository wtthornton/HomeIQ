# Home Assistant Best Practices & API 2025 Update Plan

**Date:** January 2025  
**Status:** 📋 Planning  
**Type:** Brownfield Enhancement (AI Automation Service + Dashboard)  
**Priority:** High  
**Effort:** 3 Epics, 18 Stories (42 story points, 8-10 weeks estimated)  
**Based On:** 
- "Best Practices for Home Assistant Setup and Automations" PDF
- Home Assistant 2025 API Changes Analysis
- Current AI Automation Service Implementation

---

## Executive Summary

This plan addresses two critical enhancement areas:

1. **Home Assistant Best Practices Integration** - Implement 8 best practices from the PDF review to improve automation quality, reliability, and maintainability
2. **Home Assistant 2025 API Attributes** - Integrate new HA 2025 attributes (aliases, labels, options, icon, etc.) throughout the service and dashboard

**Business Value:**
- **+40% automation reliability** - Best practices prevent common failures
- **+50% entity resolution accuracy** - New attributes improve matching
- **+30% user satisfaction** - Better suggestions with richer context
- **100% HA 2025 compliance** - Full support for latest API features

---

## Current State Analysis

### Best Practices Implementation Status

**Already Implemented (Partial):**
- ✅ `initial_state` field - Added in `yaml_generation_service.py` (line 660-661)
- ✅ Intelligent mode selection - Added in `_apply_best_practice_enhancements()` (line 664-698)
- ✅ Error handling - Added in `add_error_handling_to_actions()` (line 702-726)
- ⚠️ Automation tags - Mentioned in prompts but not fully implemented
- ⚠️ Max exceeded - Mentioned in prompts but not fully implemented

**Missing:**
- ❌ Entity availability validation before conditions
- ❌ Target optimization (area_id/device_id usage)
- ❌ Enhanced descriptions with full context
- ❌ Comprehensive tag system
- ❌ Max exceeded logic for time-based automations

### Home Assistant 2025 API Attributes Status

**Already Implemented (Phase 1):**
- ✅ Entity `aliases` - Database field exists, used in entity resolution
- ✅ Entity `name_by_user` - Database field exists, retrieved from Entity Registry
- ✅ Entity `icon` - Database field exists, separate from `original_icon`

**Partially Implemented (Phase 2):**
- ⚠️ Entity `labels` - Database field exists, not fully used in filtering
- ⚠️ Entity `options` - Database field exists, not used in suggestions
- ⚠️ Device `labels` - Database field exists, not used in filtering

**Missing Integration:**
- ❌ Labels-based filtering in suggestions
- ❌ Options-based preference detection
- ❌ Enhanced entity context in prompts
- ❌ Dashboard display of new attributes
- ❌ Label-based organization in UI

---

## Epic Structure

### Epic HA-BP-1: Best Practices Implementation
**Stories:** 8 stories (18 story points)  
**Timeline:** 4-5 weeks  
**Priority:** High

### Epic HA-API-2: Home Assistant 2025 API Integration
**Stories:** 6 stories (14 story points)  
**Timeline:** 3-4 weeks  
**Priority:** High

### Epic HA-UI-3: Dashboard Enhancements
**Stories:** 4 stories (10 story points)  
**Timeline:** 2-3 weeks  
**Priority:** Medium

---

## Epic HA-BP-1: Best Practices Implementation

### Epic Goal

Implement all 8 Home Assistant best practices from the PDF review to improve automation quality, reliability, and maintainability. Focus on critical practices first (initial_state, error handling, entity validation), then important practices (mode selection, max_exceeded, target optimization), and finally enhancements (descriptions, tags).

**Business Value:**
- **+40% automation reliability** - Best practices prevent common failures
- **+30% user trust** - More reliable automations increase confidence
- **+20% maintenance reduction** - Better automations require less fixing

---

### Story HA-BP-1.1: Complete Initial State Implementation
**Type:** Enhancement  
**Points:** 2  
**Effort:** 4-6 hours

**Current State:** `initial_state` is added in `_apply_best_practice_enhancements()` but may not be applied consistently.

**Acceptance Criteria:**
- ✅ `initial_state: true` added to ALL generated automations (not just when missing)
- ✅ Blueprint rendering includes `initial_state` field
- ✅ Validation ensures `initial_state` is present
- ✅ Unit tests verify `initial_state` in all YAML outputs
- ✅ Integration tests verify deployed automations have `initial_state`

**Files to Update:**
- `services/ai-automation-service/src/services/automation/yaml_generation_service.py`
- `services/ai-automation-service/src/services/blueprints/renderer.py`
- `services/ai-automation-service/src/services/automation/yaml_validator.py`

---

### Story HA-BP-1.2: Entity Availability Validation
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

**Current State:** Entity validation checks existence but not state availability.

**Acceptance Criteria:**
- ✅ Availability checks added to condition validation
- ✅ Conditions check entity state is not "unavailable" or "unknown"
- ✅ Availability conditions added to automations using potentially unavailable entities
- ✅ Unit tests verify availability checks
- ✅ Integration tests verify automations handle unavailable entities gracefully

**Implementation:**
```python
def add_availability_conditions(
    conditions: list[Condition],
    entity_ids: list[str]
) -> list[Condition]:
    """Add availability checks for entities used in automation."""
    enhanced_conditions = list(conditions)
    
    for entity_id in entity_ids:
        availability_condition = Condition(
            condition_type="state",
            entity_id=entity_id,
            state=["on", "off", "unavailable"],  # Accept unavailable as valid
            attribute="available"
        )
        enhanced_conditions.insert(0, availability_condition)
    
    return enhanced_conditions
```

**Files to Update:**
- `services/ai-automation-service/src/services/automation/safety_validator.py`
- `services/ai-automation-service/src/services/automation/yaml_generation_service.py`

---

### Story HA-BP-1.3: Enhanced Error Handling System
**Type:** Enhancement  
**Points:** 2  
**Effort:** 4-6 hours

**Current State:** Error handling exists but may not be comprehensive.

**Acceptance Criteria:**
- ✅ Error handling applied to all non-critical actions
- ✅ Critical actions identified and protected
- ✅ Choose blocks used for conditional error handling
- ✅ Unit tests verify error handling structure
- ✅ Integration tests verify error recovery

**Files to Update:**
- `services/ai-automation-service/src/services/automation/error_handling.py`
- `services/ai-automation-service/src/services/automation/yaml_generation_service.py`

---

### Story HA-BP-1.4: Intelligent Mode Selection Enhancement
**Type:** Enhancement  
**Points:** 2  
**Effort:** 4-6 hours

**Current State:** Mode selection exists but may need refinement.

**Acceptance Criteria:**
- ✅ Mode selection logic enhanced with more patterns
- ✅ Motion sensors with delays use `restart` mode
- ✅ Time-based automations use `single` mode
- ✅ Multiple actions with delays use `restart` mode
- ✅ Unit tests verify mode selection for all patterns

**Files to Update:**
- `services/ai-automation-service/src/contracts/models.py` - `AutomationPlan.determine_automation_mode()`
- `services/ai-automation-service/src/services/automation/yaml_generation_service.py`

---

### Story HA-BP-1.5: Max Exceeded Implementation
**Type:** Feature  
**Points:** 2  
**Effort:** 4-6 hours

**Current State:** `max_exceeded` mentioned in prompts but not implemented.

**Acceptance Criteria:**
- ✅ `max_exceeded: silent` added to time-based automations
- ✅ `max_exceeded: warn` added to safety-critical automations
- ✅ Logic determines `max_exceeded` based on automation type
- ✅ Unit tests verify `max_exceeded` assignment
- ✅ Integration tests verify queue behavior

**Implementation:**
```python
def determine_max_exceeded(
    triggers: list[Trigger],
    automation_type: str | None
) -> MaxExceeded | None:
    """Determine max_exceeded setting based on automation type."""
    
    # Time-based automations should silently skip missed runs
    if any(t.trigger_type == "time" for t in triggers):
        return MaxExceeded.SILENT
    
    # Safety-critical automations should warn on misses
    safety_keywords = ["lock", "alarm", "security", "emergency"]
    if automation_type and any(kw in automation_type.lower() for kw in safety_keywords):
        return MaxExceeded.WARN
    
    return None
```

**Files to Update:**
- `services/ai-automation-service/src/contracts/models.py` - Add `MaxExceeded` enum
- `services/ai-automation-service/src/services/automation/yaml_generation_service.py`

---

### Story HA-BP-1.6: Target Optimization (Area/Device IDs)
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

**Current State:** Automations primarily use `entity_id` in targets.

**Acceptance Criteria:**
- ✅ Target optimization converts entity_id lists to area_id when all entities in same area
- ✅ Target optimization converts entity_id lists to device_id when all entities on same device
- ✅ Optimization applied during YAML generation
- ✅ Unit tests verify target optimization
- ✅ Integration tests verify optimized targets work correctly

**Implementation:**
```python
def optimize_targets(
    actions: list[Action],
    discovery_service: DiscoveryService
) -> list[Action]:
    """Convert entity_id targets to area_id or device_id where appropriate."""
    optimized = []
    for action in actions:
        if action.entity_id and isinstance(action.entity_id, list):
            # Check if all entities belong to same area
            areas = set()
            for eid in action.entity_id:
                area = discovery_service.get_area_id(eid)
                if area:
                    areas.add(area)
            
            # If all entities in same area, use area_id
            if len(areas) == 1:
                action.target = {"area_id": list(areas)[0]}
                action.entity_id = None
        
        optimized.append(action)
    
    return optimized
```

**Files to Update:**
- `services/ai-automation-service/src/services/automation/yaml_generation_service.py`
- `services/ai-automation-service/src/clients/ha_client.py` - Add area/device resolution

---

### Story HA-BP-1.7: Enhanced Description Generation
**Type:** Enhancement  
**Points:** 2  
**Effort:** 4-6 hours

**Current State:** Descriptions are generated but may lack context.

**Acceptance Criteria:**
- ✅ Descriptions include trigger conditions
- ✅ Descriptions include expected behavior
- ✅ Descriptions include time ranges or conditions
- ✅ Device friendly names used (not just entity IDs)
- ✅ Unit tests verify description quality

**Files to Update:**
- `services/ai-automation-service/src/llm/description_generator.py`
- `services/ai-automation-service/src/services/automation/yaml_generation_service.py`

---

### Story HA-BP-1.8: Comprehensive Tag System
**Type:** Feature  
**Points:** 2  
**Effort:** 4-6 hours

**Current State:** Tags mentioned in prompts but not fully implemented.

**Acceptance Criteria:**
- ✅ Tag determination logic based on automation content
- ✅ Tags include: `ai-generated`, `energy`, `security`, `comfort`, `convenience`
- ✅ Tags added to all generated automations
- ✅ Tags stored in database
- ✅ Unit tests verify tag assignment

**Implementation:**
```python
def determine_tags(
    triggers: list[Trigger],
    actions: list[Action],
    description: str | None
) -> list[str]:
    """Determine automation tags based on content."""
    tags = ["ai-generated"]
    
    text = (description or "").lower()
    trigger_text = " ".join([str(t) for t in triggers]).lower()
    action_text = " ".join([str(a) for a in actions]).lower()
    combined = f"{text} {trigger_text} {action_text}"
    
    # Energy-related
    if any(kw in combined for kw in ["light", "turn off", "energy", "save"]):
        tags.append("energy")
    
    # Security-related
    if any(kw in combined for kw in ["lock", "alarm", "security", "door", "window"]):
        tags.append("security")
    
    # Comfort-related
    if any(kw in combined for kw in ["temperature", "climate", "fan", "heating", "cooling"]):
        tags.append("comfort")
    
    # Convenience-related
    if any(kw in combined for kw in ["motion", "presence", "scene", "routine"]):
        tags.append("convenience")
    
    return tags
```

**Files to Update:**
- `services/ai-automation-service/src/contracts/models.py` - Add `tags` field to `AutomationPlan`
- `services/ai-automation-service/src/services/automation/yaml_generation_service.py`
- `services/ai-automation-service/src/database/models.py` - Add `tags` to `Suggestion` model

---

## Epic HA-API-2: Home Assistant 2025 API Integration

### Epic Goal

Fully integrate Home Assistant 2025 API attributes (aliases, labels, options, icon) throughout the AI Automation Service and ensure they are used in entity resolution, suggestion generation, and filtering.

**Business Value:**
- **+50% entity resolution accuracy** - Aliases improve matching
- **+30% suggestion quality** - Labels and options provide context
- **100% HA 2025 compliance** - Full support for latest API features

---

### Story HA-API-2.1: Labels-Based Filtering System
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

**Current State:** Entity and device `labels` exist in database but not used for filtering.

**Acceptance Criteria:**
- ✅ Label-based filtering in suggestion queries
- ✅ Filter suggestions by entity labels (e.g., "outdoor", "security")
- ✅ Filter suggestions by device labels
- ✅ Label-based grouping in suggestions
- ✅ Unit tests verify label filtering
- ✅ Integration tests verify label-based suggestions

**Files to Update:**
- `services/ai-automation-service/src/services/automation/suggestion_generator.py`
- `services/ai-automation-service/src/database/crud.py` - Add label filtering queries
- `services/ai-automation-service/src/api/suggestions_router.py` - Add label filter parameter

---

### Story HA-API-2.2: Options-Based Preference Detection
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

**Current State:** Entity `options` exist in database but not used in suggestions.

**Acceptance Criteria:**
- ✅ Options extracted from entity registry
- ✅ Options used to inform automation suggestions (e.g., default brightness)
- ✅ Suggestions respect user-configured defaults
- ✅ Options included in entity context for YAML generation
- ✅ Unit tests verify options usage
- ✅ Integration tests verify preference-aware suggestions

**Implementation:**
```python
def extract_preferences_from_options(
    entity_id: str,
    options: dict[str, Any]
) -> dict[str, Any]:
    """Extract user preferences from entity options."""
    preferences = {}
    
    if "light" in options:
        light_opts = options["light"]
        if "default_brightness" in light_opts:
            preferences["default_brightness"] = light_opts["default_brightness"]
        if "preferred_color" in light_opts:
            preferences["preferred_color"] = light_opts["preferred_color"]
    
    return preferences
```

**Files to Update:**
- `services/ai-automation-service/src/services/entity_enrichment.py`
- `services/ai-automation-service/src/services/automation/yaml_generation_service.py`
- `services/ai-automation-service/src/llm/description_generator.py`

---

### Story HA-API-2.3: Enhanced Entity Context in Prompts
**Type:** Enhancement  
**Points:** 2  
**Effort:** 4-6 hours

**Current State:** Entity context includes basic fields but not all 2025 attributes.

**Acceptance Criteria:**
- ✅ Entity context includes aliases, labels, options
- ✅ Aliases used in entity resolution prompts
- ✅ Labels used for organizational context
- ✅ Options used for preference detection
- ✅ Unit tests verify context completeness

**Files to Update:**
- `services/ai-automation-service/src/services/entity_enrichment.py`
- `services/ai-automation-service/src/services/automation/yaml_generation_service.py`
- `services/ai-automation-service/src/api/ask_ai_router.py`

---

### Story HA-API-2.4: Icon Display Enhancement
**Type:** Enhancement  
**Points:** 1  
**Effort:** 2-4 hours

**Current State:** Icon field exists but may not be used correctly.

**Acceptance Criteria:**
- ✅ Current `icon` (not `original_icon`) used in UI
- ✅ Icon changes reflected in suggestions
- ✅ Icon-based filtering works correctly
- ✅ Unit tests verify icon usage

**Files to Update:**
- `services/ai-automation-service/src/services/entity_enrichment.py`
- `services/data-api/src/devices_endpoints.py` - Ensure `icon` returned in responses

---

### Story HA-API-2.5: Entity Resolution with Aliases Enhancement
**Type:** Enhancement  
**Points:** 2  
**Effort:** 4-6 hours

**Current State:** Aliases are used but may not be comprehensive.

**Acceptance Criteria:**
- ✅ Aliases checked in all entity resolution paths
- ✅ Aliases prioritized in matching (after exact matches)
- ✅ Alias matching works in natural language queries
- ✅ Unit tests verify alias matching
- ✅ Integration tests verify alias-based resolution

**Files to Update:**
- `services/ai-automation-service/src/services/entity_validator.py`
- `services/ai-automation-service/src/api/ask_ai_router.py`

---

### Story HA-API-2.6: Name By User Priority
**Type:** Enhancement  
**Points:** 1  
**Effort:** 2-4 hours

**Current State:** `name_by_user` exists but may not be prioritized.

**Acceptance Criteria:**
- ✅ `name_by_user` prioritized over `name` in entity resolution
- ✅ Entity Registry `name_by_user` used instead of State API `friendly_name`
- ✅ User-customized names properly recognized
- ✅ Unit tests verify name priority

**Files to Update:**
- `services/ai-automation-service/src/services/entity_enrichment.py`
- `services/device-intelligence-service/src/clients/ha_client.py`

---

## Epic HA-UI-3: Dashboard Enhancements

### Epic Goal

Enhance the AI Automation UI dashboard to display and utilize Home Assistant 2025 attributes (aliases, labels, options, icon) and best practices information (tags, mode, initial_state).

**Business Value:**
- **+30% user satisfaction** - Better visualization of automation details
- **+20% adoption rate** - Clearer information increases confidence
- **100% feature visibility** - All new attributes visible to users

---

### Story HA-UI-3.1: Display Automation Tags
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

**Current State:** Tags not displayed in dashboard.

**Acceptance Criteria:**
- ✅ Tags displayed on suggestion cards
- ✅ Tag-based filtering in dashboard
- ✅ Tag badges with color coding (energy=green, security=red, etc.)
- ✅ Tag tooltips explaining meaning
- ✅ E2E tests verify tag display

**Files to Update:**
- `services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx`
- `services/ai-automation-ui/src/components/FilterPills.tsx`
- `services/ai-automation-ui/src/types/index.ts` - Add `tags` to `Suggestion` interface

---

### Story HA-UI-3.2: Display Entity Labels and Options
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

**Current State:** Labels and options not displayed in dashboard.

**Acceptance Criteria:**
- ✅ Entity labels displayed in device info
- ✅ Entity options displayed in device info (e.g., default brightness)
- ✅ Label-based filtering in device explorer
- ✅ Options shown as preferences in suggestions
- ✅ E2E tests verify label/option display

**Files to Update:**
- `services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx`
- `services/ai-automation-ui/src/components/discovery/DeviceExplorer.tsx`
- `services/ai-automation-ui/src/types/index.ts` - Add `labels`, `options` to entity types

---

### Story HA-UI-3.3: Display Automation Metadata (Mode, Initial State)
**Type:** Feature  
**Points:** 2  
**Effort:** 4-6 hours

**Current State:** Mode and initial_state not displayed in dashboard.

**Acceptance Criteria:**
- ✅ Automation mode displayed (single/restart/queued/parallel)
- ✅ Initial state displayed (enabled/disabled)
- ✅ Mode tooltip explaining meaning
- ✅ Visual indicators for mode type
- ✅ E2E tests verify metadata display

**Files to Update:**
- `services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx`
- `services/ai-automation-ui/src/types/index.ts` - Add `mode`, `initial_state` to `Suggestion` interface

---

### Story HA-UI-3.4: Enhanced Entity Icon Display
**Type:** Enhancement  
**Points:** 2  
**Effort:** 4-6 hours

**Current State:** Icons may not use current icon field.

**Acceptance Criteria:**
- ✅ Current `icon` (not `original_icon`) displayed
- ✅ Icon changes reflected in UI
- ✅ Icon fallback handling (if icon missing, use original_icon)
- ✅ Icon tooltip showing icon source
- ✅ E2E tests verify icon display

**Files to Update:**
- `services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx`
- `services/ai-automation-ui/src/components/discovery/DeviceExplorer.tsx`
- `services/ai-automation-ui/src/types/index.ts` - Ensure `icon` field included

---

## Implementation Priority

### Phase 1: Critical (Weeks 1-3)
**Focus:** Best practices that prevent failures

1. ✅ Story HA-BP-1.1: Complete Initial State Implementation
2. ✅ Story HA-BP-1.2: Entity Availability Validation
3. ✅ Story HA-BP-1.3: Enhanced Error Handling System
4. ✅ Story HA-API-2.5: Entity Resolution with Aliases Enhancement

### Phase 2: Important (Weeks 4-6)
**Focus:** Best practices that improve quality

5. ✅ Story HA-BP-1.4: Intelligent Mode Selection Enhancement
6. ✅ Story HA-BP-1.5: Max Exceeded Implementation
7. ✅ Story HA-BP-1.6: Target Optimization
8. ✅ Story HA-API-2.1: Labels-Based Filtering System
9. ✅ Story HA-API-2.2: Options-Based Preference Detection

### Phase 3: Enhancement (Weeks 7-10)
**Focus:** UI and polish

10. ✅ Story HA-BP-1.7: Enhanced Description Generation
11. ✅ Story HA-BP-1.8: Comprehensive Tag System
12. ✅ Story HA-API-2.3: Enhanced Entity Context in Prompts
13. ✅ Story HA-API-2.4: Icon Display Enhancement
14. ✅ Story HA-API-2.6: Name By User Priority
15. ✅ Story HA-UI-3.1: Display Automation Tags
16. ✅ Story HA-UI-3.2: Display Entity Labels and Options
17. ✅ Story HA-UI-3.3: Display Automation Metadata
18. ✅ Story HA-UI-3.4: Enhanced Entity Icon Display

---

## Testing Strategy

### Unit Tests
- All new functions have >90% coverage
- All best practice logic tested
- All API attribute usage tested

### Integration Tests
- End-to-end automation generation with best practices
- Entity resolution with aliases/labels
- Suggestion filtering with labels
- Dashboard display of all new attributes

### E2E Tests
- Dashboard tag display and filtering
- Entity label/option display
- Automation metadata display
- Icon display correctness

---

## Dependencies

### External Dependencies
- **Home Assistant 2025.10+** - Required for new API attributes
- **Entity Registry API** - Source of aliases, labels, options
- **Device Registry API** - Source of device labels

### Internal Dependencies
- **Data API Service** - Must return all 2025 attributes
- **Device Intelligence Service** - Must retrieve all 2025 attributes
- **AI Automation Service** - Core service being enhanced
- **AI Automation UI** - Dashboard being enhanced

---

## Risk Mitigation

### Technical Risks

**Best Practices Complexity:**
- **Risk:** Some best practices may conflict
- **Mitigation:** Test each practice independently, then together
- **Testing:** Comprehensive integration tests

**API Attribute Availability:**
- **Risk:** Some attributes may not be available for all entities
- **Mitigation:** Graceful fallback, optional fields
- **Testing:** Test with entities missing attributes

**Performance Impact:**
- **Risk:** Additional validation may slow generation
- **Mitigation:** Optimize validation, cache results
- **Target:** <100ms additional latency

### Timeline Risks

**Integration Complexity:**
- **Risk:** Multiple services need updates
- **Mitigation:** Incremental integration, clear interfaces
- **Approach:** Phase-by-phase with testing

**UI Changes:**
- **Risk:** Dashboard changes may break existing UI
- **Mitigation:** Backward compatibility, feature flags
- **Testing:** E2E tests for all UI changes

---

## Success Criteria

### Functional
- ✅ All 8 best practices implemented
- ✅ All 2025 API attributes integrated
- ✅ Dashboard displays all new information
- ✅ Entity resolution accuracy improved
- ✅ Automation reliability improved

### Technical
- ✅ Unit tests >90% coverage
- ✅ Integration tests pass
- ✅ E2E tests pass
- ✅ Performance requirements met
- ✅ No breaking changes

### Quality
- ✅ Code reviewed and approved
- ✅ Documentation updated
- ✅ User guide updated
- ✅ All existing functionality verified

---

## Related Documentation

- [Home Assistant Best Practices Improvements](../analysis/HOME_ASSISTANT_BEST_PRACTICES_IMPROVEMENTS.md)
- [Missing HA 2025 Database Attributes](../analysis/MISSING_HA_2025_DATABASE_ATTRIBUTES.md)
- [AI Automation Service Technical Whitepaper](../current/AI_AUTOMATION_SERVICE_TECHNICAL_WHITEPAPER.md)
- [Epic AI-6: Blueprint-Enhanced Suggestion Intelligence](../../docs/prd/epic-ai6-blueprint-enhanced-suggestion-intelligence.md)

---

**Epic Owner:** Product Manager  
**Technical Lead:** AI Automation Service Team  
**Status:** 📋 Planning  
**Next Steps:** Begin Story HA-BP-1.1 - Complete Initial State Implementation

