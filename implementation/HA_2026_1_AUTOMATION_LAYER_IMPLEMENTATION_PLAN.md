# Home Assistant 2026.1 Automation Layer Implementation Plan

**Date:** January 8, 2026  
**Focus:** JSON to YAML Layer Architecture - Purpose-Specific Triggers Support  
**Principle:** Keep JSON layer generic, handle HA-specific details in YAML conversion  
**Status:** Alpha - No backward compatibility required, clean implementation preferred

---

## Architecture Overview

HomeIQ uses a three-layer architecture for automations:

```
HomeIQ JSON (Generic) 
    ↓ [HomeIQToAutomationSpecConverter]
AutomationSpec (Intermediate)
    ↓ [VersionAwareRenderer + AutomationRenderer]
Home Assistant YAML (HA-Specific)
```

**Key Principle:** The JSON layer remains generic and platform-agnostic. HA-specific formatting is handled in the YAML conversion layer.

---

## Current Architecture

### Layer 1: HomeIQ JSON Schema (Generic)
- **File:** `shared/homeiq_automation/schema.py`
- **Classes:** `HomeIQTrigger`, `HomeIQCondition`, `HomeIQAction`, `HomeIQAutomation`
- **Purpose:** Generic automation representation with HomeIQ metadata
- **Extensibility:** Uses `extra: dict[str, Any]` for additional fields

### Layer 2: Converter (JSON → AutomationSpec)
- **File:** `shared/homeiq_automation/converter.py`
- **Class:** `HomeIQToAutomationSpecConverter`
- **Purpose:** Converts HomeIQ JSON to AutomationSpec (intermediate format)
- **Strategy:** Copies standard fields, preserves HomeIQ extensions in `extra`

### Layer 3: YAML Renderer (AutomationSpec → YAML)
- **Files:** 
  - `shared/yaml_validation_service/renderer.py` (AutomationRenderer)
  - `shared/yaml_validation_service/version_aware_renderer.py` (VersionAwareRenderer)
- **Purpose:** Renders AutomationSpec to Home Assistant YAML
- **Strategy:** Copies `extra` dict fields directly to YAML output

---

## Implementation Strategy

### Clean, Simplified Approach (Alpha - No Backward Compatibility)

**Approach:**
1. Replace old trigger fields with clean, generic `trigger_config` structure
2. Use unified `Target` model for all targeting (replaces old `device_id`, `area_id` fields)
3. Converter maps generic fields to YAML-compatible fields in `TriggerSpec.extra`
4. Renderer outputs `extra` fields directly to YAML (no changes needed)

**Benefits:**
- Clean, consistent schema (no legacy fields)
- JSON layer remains generic and platform-agnostic
- HA-specific details isolated to converter layer
- Renderer stays simple (just outputs `extra` fields)
- Simpler code (no dual-path logic)

---

## Implementation Details

### Phase 1: Clean HomeIQ JSON Schema (Generic)

**File:** `shared/homeiq_automation/schema.py`

#### 1.1 Add Generic Trigger Configuration Model

Add a clean `TriggerConfig` model that replaces all old trigger fields:

```python
class TriggerConfig(BaseModel):
    """Generic trigger configuration for all trigger types."""
    # Entity/device/area targeting
    entity_id: str | list[str] | None = None
    device_id: str | list[str] | None = None
    
    # Generic trigger parameters (key-value pairs for any trigger type)
    parameters: dict[str, Any] = Field(default_factory=dict)
    
    # Examples of parameters based on trigger type:
    # - state triggers: {"to": "on", "from": "off"}
    # - time triggers: {"at": "08:00:00"}
    # - button triggers: {"action": "press"}
    # - climate triggers: {"mode": "heating", "temperature_threshold": 20.0}
```

#### 1.2 Replace HomeIQTrigger with Clean Schema

Replace old fields with clean structure (REMOVE old fields, use only new):

```python
class HomeIQTrigger(BaseModel):
    """HomeIQ trigger specification (generic, platform-agnostic)."""
    platform: str = Field(..., description="Trigger platform (e.g., 'state', 'button', 'climate')")
    
    # Single source of truth for trigger configuration
    config: TriggerConfig = Field(..., description="Trigger configuration")
    
    # Enhanced targeting (areas, floors, labels)
    target: Target | None = Field(None, description="Enhanced targeting (areas, floors, labels)")
    
    # Additional trigger fields (rarely used)
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional trigger-specific fields")
```

**Rationale:**
- Single `config` field replaces all old fields (`entity_id`, `to`, `from_state`, `at`, etc.)
- Cleaner, more consistent schema
- `parameters` dict handles all platform-specific fields generically
- No legacy fields to maintain

#### 1.2 Add Enhanced Targeting Model

Add a generic `Target` model for enhanced targeting (areas, floors, labels):

```python
class Target(BaseModel):
    """Generic target specification for triggers, conditions, and actions."""
    entity_id: str | list[str] | None = None
    device_id: str | list[str] | None = None
    area_id: str | list[str] | None = None
    floor_id: str | list[str] | None = None
    labels: list[str] | None = None

class HomeIQTrigger(BaseModel):
    # ... existing fields ...
    
    # Enhanced targeting (NEW)
    target: Target | None = Field(None, description="Enhanced targeting (areas, floors, labels)")
```

#### 1.3 Update HomeIQCondition and HomeIQAction

Replace old `device_id`, `area_id` fields with unified `target` field:

```python
class HomeIQCondition(BaseModel):
    """HomeIQ condition specification (generic, platform-agnostic)."""
    condition: str = Field(..., description="Condition type (e.g., 'state', 'numeric_state', 'time')")
    
    # Entity/state fields
    entity_id: str | list[str] | None = Field(None, description="Entity ID(s)")
    state: str | None = Field(None, description="State value for state conditions")
    above: float | None = Field(None, description="Above value for numeric_state conditions")
    below: float | None = Field(None, description="Below value for numeric_state conditions")
    
    # Enhanced targeting (replaces old device_id, area_id fields)
    target: Target | None = Field(None, description="Enhanced targeting (areas, floors, labels)")
    
    # Additional condition fields
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional condition-specific fields")

class HomeIQAction(BaseModel):
    """HomeIQ action specification (generic, platform-agnostic)."""
    service: str | None = Field(None, description="Service to call (e.g., 'light.turn_on')")
    scene: str | None = Field(None, description="Scene to activate")
    delay: str | None = Field(None, description="Delay duration (e.g., '00:00:05')")
    data: dict[str, Any] = Field(default_factory=dict, description="Service data")
    
    # Enhanced targeting (REPLACES old dict target field)
    target: Target | None = Field(None, description="Enhanced targeting (areas, floors, labels, devices, entities)")
    
    # Advanced action types
    choose: list[dict[str, Any]] | None = Field(None, description="Choose action")
    repeat: dict[str, Any] | None = Field(None, description="Repeat action")
    parallel: list[dict[str, Any]] | None = Field(None, description="Parallel actions")
    sequence: list[dict[str, Any]] | None = Field(None, description="Sequence actions")
    
    # Error handling
    error: str | None = Field(None, description="Error handling ('continue', 'stop', 'abort')")
    
    # HomeIQ extensions
    energy_impact_w: float | None = Field(None, ge=0.0, description="Estimated power consumption")
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional action-specific fields")
```

**Rationale:**
- Remove old `device_id`, `area_id` fields from conditions
- Replace dict `target` with `Target` model in actions (cleaner, type-safe)
- Consistent targeting model across triggers, conditions, and actions

---

### Phase 2: Update Converter (JSON → AutomationSpec)

**File:** `shared/homeiq_automation/converter.py`

#### 2.1 Simplify Trigger Conversion

Replace old conversion logic with clean, simple approach:

```python
def _convert_trigger(self, trigger: HomeIQTrigger) -> TriggerSpec:
    """Convert HomeIQ trigger to TriggerSpec."""
    trigger_data: dict[str, Any] = {
        "platform": trigger.platform,
    }
    
    # Map trigger config to YAML fields
    yaml_fields = self._map_trigger_config_to_yaml(
        platform=trigger.platform,
        config=trigger.config
    )
    trigger_data.setdefault("extra", {}).update(yaml_fields)
    
    # Handle enhanced targeting
    if trigger.target:
        target_dict = self._target_to_dict(trigger.target)
        if target_dict:
            trigger_data.setdefault("extra", {})["target"] = target_dict
    
    # Merge any additional extra fields
    if trigger.extra:
        trigger_data.setdefault("extra", {}).update(trigger.extra)
    
    return TriggerSpec(**trigger_data)

def _target_to_dict(self, target: Target) -> dict[str, Any]:
    """Convert Target model to YAML-compatible dict."""
    target_dict: dict[str, Any] = {}
    if target.area_id:
        target_dict["area_id"] = target.area_id
    if target.floor_id:
        target_dict["floor_id"] = target.floor_id
    if target.labels:
        target_dict["labels"] = target.labels
    if target.device_id:
        target_dict["device_id"] = target.device_id
    if target.entity_id:
        target_dict["entity_id"] = target.entity_id
    return target_dict

def _map_trigger_config_to_yaml(
    self, 
    platform: str, 
    config: TriggerConfig
) -> dict[str, Any]:
    """
    Map generic trigger configuration to YAML-compatible fields.
    
    Maps platform-agnostic config to HA 2026.1 YAML format.
    """
    yaml_fields: dict[str, Any] = {}
    
    # Always include entity_id if present
    if config.entity_id:
        yaml_fields["entity_id"] = config.entity_id
    
    # Copy all parameters directly (they're already in YAML-compatible format)
    # Examples:
    # - state triggers: {"to": "on", "from": "off"}
    # - time triggers: {"at": "08:00:00"}
    # - button triggers: {"action": "press"}
    # - climate triggers: {"mode": "heating", "temperature_threshold": 20.0}
    yaml_fields.update(config.parameters)
    
    return yaml_fields
```

**Note:** The converter is now much simpler - it just copies `parameters` directly to YAML fields. The JSON layer uses `parameters` dict to store platform-specific fields generically.
```

#### 2.2 Simplify Condition and Action Conversion

Update `_convert_condition` and `_convert_action` with clean, simple logic:

```python
def _convert_condition(self, condition: HomeIQCondition) -> ConditionSpec:
    """Convert HomeIQ condition to ConditionSpec."""
    condition_data: dict[str, Any] = {
        "condition": condition.condition,
    }
    
    # Copy standard fields
    if condition.entity_id is not None:
        condition_data["entity_id"] = condition.entity_id
    if condition.state is not None:
        condition_data["state"] = condition.state
    if condition.above is not None:
        condition_data["above"] = condition.above
    if condition.below is not None:
        condition_data["below"] = condition.below
    
    # Handle enhanced targeting
    if condition.target:
        target_dict = self._target_to_dict(condition.target)
        if target_dict:
            condition_data.setdefault("extra", {})["target"] = target_dict
    
    # Merge extra fields
    if condition.extra:
        condition_data.setdefault("extra", {}).update(condition.extra)
    
    return ConditionSpec(**condition_data)

def _convert_action(self, action: HomeIQAction) -> ActionSpec:
    """Convert HomeIQ action to ActionSpec."""
    action_data: dict[str, Any] = {}
    
    # Copy standard fields
    if action.service:
        action_data["service"] = action.service
    if action.scene:
        action_data["scene"] = action.scene
    if action.delay:
        action_data["delay"] = action.delay
    if action.data:
        action_data["data"] = action.data
    
    # Handle enhanced targeting (REPLACES old dict target)
    if action.target:
        target_dict = self._target_to_dict(action.target)
        if target_dict:
            action_data["target"] = target_dict
    
    # Advanced actions
    if action.choose:
        action_data["choose"] = action.choose
    if action.repeat:
        action_data["repeat"] = action.repeat
    if action.parallel:
        action_data["parallel"] = action.parallel
    if action.sequence:
        action_data["sequence"] = action.sequence
    
    # Error handling
    if action.error:
        action_data["error"] = action.error
    
    # HomeIQ extensions (preserve in extra)
    if action.energy_impact_w is not None:
        action_data.setdefault("extra", {})["energy_impact_w"] = action.energy_impact_w
    
    # Merge extra fields
    if action.extra:
        action_data.setdefault("extra", {}).update(action.extra)
    
    return ActionSpec(**action_data)
```

---

### Phase 3: YAML Renderer (No Changes Required)

**Files:** 
- `shared/yaml_validation_service/renderer.py`
- `shared/yaml_validation_service/version_aware_renderer.py`

**Status:** No changes required

**Rationale:** The renderer already handles `extra` fields by copying them directly to YAML output (see `AutomationRenderer._trigger_to_dict`, line 116: `result.update(trigger.extra)`). Since we're putting YAML-compatible fields in `extra`, they will be rendered correctly.

**Note:** For HA 2026.1+ with purpose-specific triggers, the YAML output will include the fields from `extra` directly, which is exactly what we want.

---

## Implementation Checklist

### Phase 1: Schema Updates (Clean Implementation)
- [ ] Add `TriggerConfig` model to `shared/homeiq_automation/schema.py`
- [ ] Add `Target` model to `shared/homeiq_automation/schema.py`
- [ ] **REMOVE** old fields from `HomeIQTrigger` (entity_id, to, from_state, at, minutes, hours, days, device_id, area_id)
- [ ] Replace with clean `config: TriggerConfig` field in `HomeIQTrigger`
- [ ] Add `target: Target | None` field to `HomeIQTrigger`
- [ ] **REMOVE** old fields from `HomeIQCondition` (device_id, area_id)
- [ ] Add `target: Target | None` field to `HomeIQCondition`
- [ ] **REPLACE** dict `target` field with `target: Target | None` in `HomeIQAction`
- [ ] Update schema version in `HomeIQAutomation.version` to "2.0.0" (breaking change)

### Phase 2: Converter Updates (Simplified)
- [ ] **REPLACE** `_convert_trigger` with simplified version (no legacy field handling)
- [ ] Add `_map_trigger_config_to_yaml` method (simple - just copies parameters)
- [ ] Add `_target_to_dict` helper method
- [ ] **REPLACE** `_convert_condition` with simplified version
- [ ] **REPLACE** `_convert_action` with simplified version (no dict target merging)
- [ ] Add unit tests for all new trigger types
- [ ] Add unit tests for enhanced targeting

### Phase 3: Testing & Validation
- [ ] Create test cases for all new trigger types (button, climate, device_tracker, humidifier, light, lock, scene, siren, update)
- [ ] Create test cases for enhanced targeting (areas, floors, labels)
- [ ] Test YAML output matches HA 2026.1 format
- [ ] Integration tests with actual HA 2026.1 instance
- [ ] Test database migration (delete old automation data if needed)

### Phase 4: Documentation
- [ ] Update schema documentation with new fields
- [ ] Document trigger_config usage patterns
- [ ] Document enhanced targeting usage
- [ ] Update converter documentation
- [ ] Add examples for new trigger types

---

## Example: Button Trigger

### HomeIQ JSON (Generic)
```json
{
  "platform": "button",
  "config": {
    "entity_id": "button.living_room_button",
    "parameters": {
      "action": "press"
    }
  }
}
```

### After Converter (AutomationSpec)
```python
TriggerSpec(
    platform="button",
    extra={
        "entity_id": "button.living_room_button",
        "action": "press"
    }
)
```

### YAML Output (HA 2026.1)
```yaml
trigger:
  - platform: button
    entity_id: button.living_room_button
    action: press
```

---

## Example: State Trigger (Old Format Replaced)

### HomeIQ JSON (Generic) - NEW FORMAT
```json
{
  "platform": "state",
  "config": {
    "entity_id": "light.living_room",
    "parameters": {
      "to": "on",
      "from": "off"
    }
  }
}
```

### YAML Output (HA 2026.1)
```yaml
trigger:
  - platform: state
    entity_id: light.living_room
    to: on
    from: off
```

---

## Example: Enhanced Targeting

### HomeIQ JSON (Generic)
```json
{
  "platform": "state",
  "config": {
    "parameters": {
      "to": "on"
    }
  },
  "target": {
    "area_id": "living_room",
    "labels": ["outdoor", "security"]
  }
}
```

### YAML Output (HA 2026.1)
```yaml
trigger:
  - platform: state
    to: on
    target:
      area_id: living_room
      labels:
        - outdoor
        - security
```

---

## Database Migration

Since we're in alpha, we can delete existing automation data:

1. **Option 1:** Delete all automations from database
   - Simplest approach
   - Users will need to regenerate automations

2. **Option 2:** Write migration script (if data is valuable)
   - Convert old format to new format
   - Update database records
   - More complex but preserves data

**Recommendation:** Option 1 (delete data) - cleaner, simpler, we're in alpha.

---

## Testing Strategy

### Unit Tests
1. Test each new trigger type (button, climate, device_tracker, humidifier, light, lock, scene, siren, update)
2. Test enhanced targeting (areas, floors, labels) in triggers, conditions, actions
3. Test converter mapping logic (config → YAML fields)
4. Test all state trigger parameters (to, from, at, etc.)

### Integration Tests
1. Test YAML output with HA 2026.1 (verify format matches)
2. Test with actual HA 2026.1 instance (validate automations work)
3. Test round-trip conversion (JSON → YAML → JSON) if needed

### Test Files
- `tests/test_trigger_converter.py` - Converter unit tests
- `tests/test_yaml_output_2026_1.py` - YAML output validation for HA 2026.1

---

## File Changes Summary

### Modified Files
1. `shared/homeiq_automation/schema.py`
   - Add `TriggerConfig` model
   - Add `Target` model
   - Update `HomeIQTrigger`, `HomeIQCondition`, `HomeIQAction`

2. `shared/homeiq_automation/converter.py`
   - Update `_convert_trigger` method
   - Add `_map_trigger_config_to_yaml` method
   - Update `_convert_condition` method
   - Update `_convert_action` method

### New Files
1. `tests/test_trigger_converter.py` - Converter tests
2. `tests/test_yaml_output_2026_1.py` - YAML output tests

### Unchanged Files
- `shared/yaml_validation_service/renderer.py` - No changes needed
- `shared/yaml_validation_service/version_aware_renderer.py` - No changes needed
- `shared/homeiq_automation/yaml_transformer.py` - No changes needed (uses converter)

---

## Success Criteria

1. ✅ JSON layer remains generic (no HA-specific fields in schema)
2. ✅ Clean, simplified schema (no legacy fields)
3. ✅ All new trigger types supported (button, climate, device_tracker, humidifier, light, lock, scene, siren, update)
4. ✅ Enhanced targeting supported (areas, floors, labels)
5. ✅ YAML output matches HA 2026.1 format
6. ✅ Converter is simple and efficient (no dual-path logic)
7. ✅ Renderer works without changes (uses `extra` dict)
8. ✅ Database migration handled (data deleted or migrated)

---

## Timeline Estimate

- **Phase 1 (Schema Updates):** 1-2 days (simpler without backward compatibility)
- **Phase 2 (Converter Updates):** 2-3 days (simpler without dual-path logic)
- **Phase 3 (Testing):** 2-3 days (no backward compatibility tests)
- **Phase 4 (Documentation):** 1 day

**Total:** 6-9 days (faster due to simplified implementation)

---

## References

- [Home Assistant 2026.1 Release Notes](https://www.home-assistant.io/blog/2026/01/07/release-20261/)
- [Home Assistant Purpose-Specific Triggers](https://www.home-assistant.io/docs/automation/trigger/#purpose-specific-triggers)
- HomeIQ Automation Schema: `shared/homeiq_automation/schema.py`
- HomeIQ Converter: `shared/homeiq_automation/converter.py`
- YAML Renderer: `shared/yaml_validation_service/renderer.py`

---

**Plan Created:** January 8, 2026  
**Last Updated:** January 8, 2026  
**Status:** Updated for Alpha - No Backward Compatibility  
**Notes:** Simplified implementation, clean schema, no legacy fields, database migration (delete data)
