# HA Agent API Flow Deep Dive Analysis

**Service**: `http://localhost:3001/ha-agent` (ha-ai-agent-service)  
**Date**: January 2025  
**Analysis Scope**: User prompt → JSON/YAML generation process and device validation

---

## Executive Summary

The ha-agent interface uses **two distinct automation generation flows**:

1. **Current Production Flow (ha-ai-agent-service)**: `User Prompt → YAML (Direct Generation) → Validation → Preview → Create`
2. **Alternative Flow (ai-automation-service-new)**: `User Prompt → HomeIQ JSON → Validation → YAML Conversion → Create`

**Key Finding**: The ha-agent interface **does NOT currently use JSON as an intermediate step**. It generates YAML directly from user prompts. However, there is infrastructure available for JSON-based generation that could be integrated.

---

## Current Production Flow (ha-ai-agent-service)

### Flow Architecture

```
User Prompt (Natural Language)
    ↓
OpenAI Agent (with System Prompt + Home Assistant Context)
    ↓
YAML Generation (Direct - No JSON Intermediate)
    ↓
preview_automation_from_prompt Tool
    ├─ YAML Validation (ValidationChain)
    │   ├─ YAMLValidationStrategy (YAML Validation Service)
    │   ├─ AIAutomationValidationStrategy (AI Automation Service)
    │   └─ BasicValidationStrategy (Fallback)
    ├─ Entity/Area/Service Extraction
    ├─ Safety Checks
    └─ Preview Response
    ↓
User Approval
    ↓
create_automation_from_prompt Tool
    ├─ YAML Validation (Re-validation)
    └─ Home Assistant API (Create Automation)
```

### Key Components

#### 1. Chat Endpoint (`/api/v1/chat`)
- **Location**: `services/ha-ai-agent-service/src/api/chat_endpoints.py`
- **Service**: `ha-ai-agent-service` (port 8000, proxied to 3001 via frontend)
- **Flow**:
  1. Receives user message
  2. Calls OpenAI Agent API with system prompt and context
  3. Agent generates YAML directly (no JSON step)
  4. Agent calls `preview_automation_from_prompt` tool
  5. Tool validates YAML and returns preview
  6. User approves → Agent calls `create_automation_from_prompt`
  7. Tool creates automation in Home Assistant

#### 2. System Prompt
- **Location**: `services/ha-ai-agent-service/src/prompts/system_prompt.py`
- **Purpose**: Instructs OpenAI agent to generate Home Assistant automation YAML
- **Key Instructions**:
  - Generate valid Home Assistant 2025.10+ YAML directly
  - Use context to find entities, areas, services
  - Call `preview_automation_from_prompt` FIRST (mandatory)
  - Wait for user approval before creating
  - Prefer `target.area_id` over multiple `entity_id` entries

#### 3. Preview Tool (`preview_automation_from_prompt`)
- **Location**: `services/ha-ai-agent-service/src/tools/ha_tools.py:108`
- **Input**: `user_prompt`, `automation_yaml`, `alias`
- **Process**:
  1. Validates request parameters
  2. Parses YAML to dict
  3. Runs validation chain:
     - YAML syntax validation
     - Entity/device validation (via Data API)
     - Safety checks
  4. Extracts entities, areas, services from YAML
  5. Builds preview response
- **Output**: Preview with validation results, affected entities, safety warnings

#### 4. Validation Chain
- **Location**: `services/ha-ai-agent-service/src/services/validation/validation_chain.py`
- **Strategies** (in order):
  1. **YAMLValidationStrategy**: Uses YAML Validation Service (comprehensive)
  2. **AIAutomationValidationStrategy**: Uses AI Automation Service (fallback)
  3. **BasicValidationStrategy**: Basic syntax/structure checks (final fallback)
- **Purpose**: Validates YAML syntax, entities exist, safety rules

#### 5. Entity Resolution Service
- **Location**: `services/ha-ai-agent-service/src/services/entity_resolution/entity_resolution_service.py`
- **Purpose**: Resolves entities from user prompts (not used in current flow, but available)
- **Business Rules**:
  1. Area filtering first
  2. Positional keyword matching (top, left, right, back, front, desk, ceiling, floor)
  3. Device type matching (LED, WLED, strip, bulb)
  4. Validation (verify matches user description)

---

## Alternative Flow (ai-automation-service-new)

### Flow Architecture

```
User Prompt (Natural Language)
    ↓
OpenAI Client (generate_homeiq_automation_json)
    ↓
HomeIQ JSON Generation (Structured Output with Schema)
    ├─ Core automation fields (alias, triggers, actions, conditions)
    ├─ HomeIQ metadata (created_by, use_case, complexity, safety_score)
    ├─ Device context (device_ids, entity_ids, device_types, area_ids)
    ├─ Pattern context (if applicable)
    ├─ Safety checks
    └─ Energy impact calculations
    ↓
JSON Validation (HomeIQAutomationValidator)
    ├─ Pydantic schema validation
    ├─ Entity ID validation (Data API)
    ├─ Device ID validation (Data API)
    ├─ Device capability validation
    ├─ Safety rule validation
    └─ Consistency checks
    ↓
JSON to AutomationSpec Conversion (HomeIQToAutomationSpecConverter)
    ↓
YAML Rendering (AutomationRenderer)
    ↓
YAML Validation (YAMLValidationClient - optional)
    ↓
Final YAML
```

### Key Components

#### 1. JSON Generation Service (`YAMLGenerationService`)
- **Location**: `services/ai-automation-service-new/src/services/yaml_generation_service.py`
- **Method**: `generate_homeiq_json()`
- **Process**:
  1. Builds prompt with HomeIQ context (patterns, devices, areas)
  2. Calls `OpenAIClient.generate_homeiq_automation_json()`
  3. LLM generates JSON using structured output (`response_format={"type": "json_object"}`)
  4. Validates JSON using `HomeIQAutomationValidator`
  5. Returns HomeIQ JSON Automation

#### 2. OpenAI Client (`generate_homeiq_automation_json`)
- **Location**: `services/ai-automation-service-new/src/clients/openai_client.py:268`
- **Process**:
  1. Builds system prompt with HomeIQ JSON schema
  2. Includes HomeIQ context (patterns, devices, areas) if available
  3. Uses `response_format={"type": "json_object"}` for structured output
  4. Parses JSON response
  5. Returns automation JSON dictionary

#### 3. JSON to YAML Conversion
- **Location**: `services/ai-automation-service-new/src/services/yaml_generation_service.py:206`
- **Process** (`_generate_yaml_from_homeiq_json`):
  1. Generates HomeIQ JSON from suggestion
  2. Converts JSON to `HomeIQAutomation` Pydantic model
  3. Converts `HomeIQAutomation` to `AutomationSpec` (via `HomeIQToAutomationSpecConverter`)
  4. Renders `AutomationSpec` to YAML (via `AutomationRenderer`)
  5. Optionally validates YAML via YAML Validation Service

#### 4. JSON Validation (`HomeIQAutomationValidator`)
- **Location**: `shared/homeiq_automation/validator.py`
- **Validation Steps**:
  1. Pydantic schema validation
  2. Entity ID validation (fetches from Data API, checks existence)
  3. Device ID validation (fetches from Data API, checks existence)
  4. Device capability validation (checks if device supports requested features)
  5. Safety rule validation (checks critical devices, time constraints)
  6. Energy impact validation (checks if energy impact calculations are reasonable)
  7. Consistency checks (device_context matches triggers/conditions/actions)

---

## Device/Entity Validation Analysis

### Current Production Flow (ha-ai-agent-service)

#### Validation Points

1. **YAML Validation Service** (if available):
   - Validates YAML syntax
   - Validates entities exist (via Data API)
   - Normalizes YAML
   - Provides fixes for common issues

2. **AI Automation Service** (fallback):
   - Validates YAML via `/api/v1/yaml/validate` endpoint
   - Entity validation
   - Safety validation

3. **Basic Validation** (final fallback):
   - YAML syntax check
   - Required fields check (alias, trigger, action)
   - Group entity warnings

4. **Entity Extraction** (`_extract_entities_from_yaml`):
   - Extracts entity IDs from triggers, conditions, actions
   - Extracts from `target.entity_id` in actions
   - Returns list of unique entity IDs
   - **Note**: Does NOT validate entities exist (only extracts)

5. **Safety Checks** (`_check_safety_requirements`):
   - Checks for security domains (lock, alarm, camera, person, device_tracker)
   - Checks for critical services (lock.lock, lock.unlock, alarm_control_panel.alarm_arm, etc.)
   - Returns safety warnings

#### Validation Gaps

1. **No Entity Existence Validation in Preview Tool**:
   - `_extract_entities_from_yaml()` only extracts entities, doesn't validate
   - Entity validation happens in ValidationChain, but only if YAML Validation Service or AI Automation Service is available
   - If only BasicValidationStrategy runs, entities are NOT validated

2. **No Device Validation**:
   - No device ID validation
   - No device capability validation
   - No device health score checks

3. **No Device Context Extraction**:
   - Device IDs, device types, area IDs are not extracted or validated
   - Only entity IDs are extracted

4. **Incomplete Safety Validation**:
   - Basic safety checks (security domains, critical services)
   - No time constraint validation
   - No energy impact validation

### Alternative Flow (ai-automation-service-new)

#### Validation Points

1. **Pydantic Schema Validation**:
   - Validates JSON structure matches `HomeIQAutomation` schema
   - Type checking, required fields, enum validation
   - Comprehensive schema validation

2. **Entity ID Validation** (`_validate_entities`):
   - Fetches all entities from Data API
   - Checks each entity ID in automation exists
   - Detects group entities and provides specific warnings
   - Returns list of invalid entity IDs

3. **Device ID Validation** (`_validate_devices`):
   - Fetches all devices from Data API
   - Checks each device ID in `device_context` exists
   - Returns list of invalid device IDs

4. **Device Capability Validation** (`_validate_device_capabilities`):
   - Checks if devices support requested features (e.g., effects, presets, modes)
   - Validates numeric ranges (brightness, temperature, etc.)
   - Returns warnings for unsupported capabilities

5. **Safety Rule Validation** (`_validate_safety_rules`):
   - Checks critical devices (locks, security systems)
   - Validates time constraints (if automation has time-based triggers)
   - Checks `requires_confirmation` flag for critical automations
   - Returns errors for unsafe automations, warnings for potentially unsafe

6. **Consistency Checks** (`_validate_consistency`):
   - Checks device_context matches triggers/conditions/actions
   - Checks area_context matches device_context.area_ids
   - Returns warnings for inconsistencies

#### Validation Strengths

1. **Comprehensive Validation**:
   - Multiple validation layers (schema, entities, devices, capabilities, safety, consistency)
   - Clear error messages for each validation failure

2. **Device Context Awareness**:
   - Validates device IDs exist
   - Validates device capabilities
   - Checks device context matches automation structure

3. **Safety-First Approach**:
   - Validates safety rules before YAML generation
   - Checks time constraints for security automations
   - Validates requires_confirmation flag

4. **Consistency Validation**:
   - Ensures device_context matches automation structure
   - Prevents mismatches between metadata and actual automation

---

## What's Good ✅

### Current Production Flow (ha-ai-agent-service)

1. **Direct YAML Generation**:
   - Fast - no intermediate JSON step
   - Simple - fewer transformation steps
   - Lower latency - direct to YAML

2. **Preview-and-Approval Workflow**:
   - User sees preview before creation
   - Safety warnings shown before approval
   - User can review and approve/reject

3. **Multiple Validation Strategies**:
   - Fallback chain ensures validation always runs
   - YAML Validation Service provides comprehensive validation
   - Basic validation ensures minimum quality

4. **Entity Extraction**:
   - Extracts entities, areas, services from YAML
   - Shows affected entities in preview
   - Helps user understand automation scope

5. **Safety Checks**:
   - Basic safety validation (security domains, critical services)
   - Safety warnings in preview
   - Prevents obviously unsafe automations

6. **Rich Context**:
   - Home Assistant context (entities, areas, services, capabilities) provided to LLM
   - Entity resolution service available (though not used in current flow)
   - Device type information from Device Mapping Library

### Alternative Flow (ai-automation-service-new)

1. **Structured JSON Format**:
   - HomeIQ JSON includes rich metadata (use_case, complexity, safety_score, energy_impact)
   - Device context captured (device_ids, entity_ids, device_types, area_ids)
   - Pattern context support (if automation from pattern)
   - Better traceability and analytics

2. **Comprehensive Validation**:
   - Pydantic schema validation ensures type safety
   - Entity and device existence validation
   - Device capability validation
   - Safety rule validation
   - Consistency checks

3. **Separation of Concerns**:
   - JSON generation separate from YAML rendering
   - JSON validation separate from YAML validation
   - Clear transformation pipeline

4. **Reusability**:
   - JSON can be stored, queried, analyzed
   - JSON can be converted to different YAML formats
   - JSON enables analytics and pattern detection

---

## What's Bad ❌

### Current Production Flow (ha-ai-agent-service)

1. **No JSON Intermediate Step**:
   - No structured metadata capture (use_case, complexity, energy_impact)
   - No device context metadata
   - Limited analytics/traceability
   - Cannot query automations by metadata

2. **Incomplete Entity Validation**:
   - Entity validation only runs if YAML Validation Service or AI Automation Service is available
   - If only BasicValidationStrategy runs, entities are NOT validated
   - Entities could be invalid and still pass validation

3. **No Device Validation**:
   - Device IDs not validated
   - Device capabilities not validated
   - Device health scores not considered
   - No device context extraction

4. **Limited Safety Validation**:
   - Basic safety checks only (security domains, critical services)
   - No time constraint validation
   - No energy impact validation
   - No device capability safety checks (e.g., can this device actually do this?)

5. **No Consistency Checks**:
   - Device context not extracted or validated
   - No check if metadata matches automation structure
   - No validation that entities match device_context

6. **YAML-First Approach Limitations**:
   - Harder to add metadata after YAML generation
   - Cannot easily modify automation structure (need to parse YAML)
   - Limited querying capabilities

### Alternative Flow (ai-automation-service-new)

1. **Not Currently Used in ha-agent**:
   - Alternative flow exists but is not integrated into ha-agent interface
   - Would require significant integration work

2. **Additional Latency**:
   - JSON generation step adds latency
   - JSON validation adds latency
   - JSON to YAML conversion adds latency
   - Multiple API calls (OpenAI, Data API, YAML Validation Service)

3. **Complexity**:
   - More transformation steps
   - More failure points
   - More code to maintain

4. **YAML Validation Not Always Used**:
   - YAML validation is optional (if `yaml_validation_client` is None, skips validation)
   - Could generate invalid YAML if validation service unavailable

---

## Recommendations to Make This Process Amazing 🚀

### 1. **Integrate JSON-Based Flow into ha-agent** (High Priority)

**Why**: The JSON-based flow provides structured metadata, comprehensive validation, and better traceability.

**How**:
- Add option to use JSON-based flow in `preview_automation_from_prompt` tool
- If `use_json_flow=True`, call `ai-automation-service-new` to generate JSON first
- Convert JSON to YAML for preview
- Store JSON in preview response for analytics

**Benefits**:
- Rich metadata capture (use_case, complexity, energy_impact, safety_score)
- Device context validation
- Better analytics and querying
- Consistency validation

**Implementation**:
```python
# In preview_automation_from_prompt tool
if use_json_flow and self.ai_automation_client:
    # Generate HomeIQ JSON via ai-automation-service-new
    automation_json = await self.ai_automation_client.generate_json_from_prompt(
        user_prompt=request.user_prompt,
        context=home_assistant_context
    )
    # Convert JSON to YAML
    automation_yaml = await self.ai_automation_client.json_to_yaml(automation_json)
    # Use YAML for preview, but store JSON for analytics
```

### 2. **Mandatory Entity Validation** (Critical)

**Why**: Currently, entity validation only runs if YAML Validation Service is available. Invalid entities could pass validation.

**How**:
- Add mandatory entity validation in BasicValidationStrategy
- Fetch entities from Data API and validate each entity ID
- Fail validation if invalid entities found (don't just warn)

**Implementation**:
```python
# In BasicValidationStrategy.validate()
if self.tool_handler.data_api_client:
    entities = await self.tool_handler.data_api_client.fetch_entities()
    valid_entity_ids = {e.get("entity_id") for e in entities}
    invalid_entities = [eid for eid in extracted_entities if eid not in valid_entity_ids]
    if invalid_entities:
        errors.append(f"Invalid entity IDs: {', '.join(invalid_entities)}")
```

### 3. **Add Device Validation** (High Priority)

**Why**: Device IDs are not currently validated. Device capabilities are not checked. Device health scores are not considered.

**How**:
- Extract device IDs from YAML (if available) or infer from entity IDs
- Validate device IDs exist via Data API
- Check device capabilities (if automation uses device-specific features)
- Consider device health scores (prioritize devices with health_score > 70)

**Implementation**:
```python
# In preview_automation_from_prompt tool
async def _validate_devices(self, automation_dict: dict[str, Any]) -> list[str]:
    """Validate device IDs and capabilities."""
    errors = []
    device_ids = self._extract_device_ids(automation_dict)
    
    if device_ids and self.data_api_client:
        devices = await self.data_api_client.fetch_devices()
        valid_device_ids = {d.get("device_id") for d in devices}
        invalid_devices = [did for did in device_ids if did not in valid_device_ids]
        if invalid_devices:
            errors.append(f"Invalid device IDs: {', '.join(invalid_devices)}")
        
        # Check device capabilities
        capability_errors = self._validate_device_capabilities(automation_dict, devices)
        errors.extend(capability_errors)
    
    return errors
```

### 4. **Enhanced Safety Validation** (High Priority)

**Why**: Current safety validation is basic. Missing time constraint validation, energy impact validation, device capability safety checks.

**How**:
- Add time constraint validation for security automations
- Add energy impact validation (if automation uses power-consuming devices)
- Add device capability safety checks (e.g., can this device actually do this safely?)
- Add safety score calculation

**Implementation**:
```python
# In BusinessRuleValidator
async def validate_time_constraints(
    self, automation_dict: dict[str, Any], entities: list[str]
) -> list[str]:
    """Validate time constraints for security automations."""
    errors = []
    
    # Check if automation uses security entities
    security_entities = [e for e in entities if e.split(".")[0] in self.SECURITY_DOMAINS]
    
    if security_entities:
        # Check if automation has time-based triggers
        triggers = automation_dict.get("trigger", [])
        has_time_trigger = any(
            t.get("platform") in ["time", "time_pattern", "sun", "calendar"]
            for t in (triggers if isinstance(triggers, list) else [triggers])
        )
        
        if not has_time_trigger:
            warnings.append(
                "Security automation without time constraints - "
                "consider adding time-based triggers for safety"
            )
    
    return errors
```

### 5. **Device Context Extraction and Validation** (Medium Priority)

**Why**: Device context (device_ids, device_types, area_ids) is not currently extracted or validated.

**How**:
- Extract device IDs from entity IDs (via Data API)
- Extract device types from devices
- Extract area IDs from entities/devices
- Validate device context matches automation structure

**Implementation**:
```python
# In preview_automation_from_prompt tool
async def _extract_device_context(
    self, automation_dict: dict[str, Any]
) -> dict[str, Any]:
    """Extract device context from automation."""
    entity_ids = self._extract_entities_from_yaml(automation_dict)
    
    if entity_ids and self.data_api_client:
        entities = await self.data_api_client.fetch_entities()
        entity_map = {e.get("entity_id"): e for e in entities}
        
        device_ids = set()
        device_types = set()
        area_ids = set()
        
        for entity_id in entity_ids:
            entity = entity_map.get(entity_id)
            if entity:
                if entity.get("device_id"):
                    device_ids.add(entity.get("device_id"))
                if entity.get("device_type"):
                    device_types.add(entity.get("device_type"))
                if entity.get("area_id"):
                    area_ids.add(entity.get("area_id"))
        
        return {
            "device_ids": list(device_ids),
            "device_types": list(device_types),
            "area_ids": list(area_ids),
            "entity_ids": entity_ids
        }
    
    return {"device_ids": [], "device_types": [], "area_ids": [], "entity_ids": entity_ids}
```

### 6. **Add Consistency Checks** (Medium Priority)

**Why**: No validation that metadata matches automation structure. Device context not validated against automation.

**How**:
- Validate device context matches entities in automation
- Validate area context matches device context
- Validate use_case matches automation structure
- Validate complexity matches automation structure

**Implementation**:
```python
# In preview_automation_from_prompt tool
def _validate_consistency(
    self,
    automation_dict: dict[str, Any],
    device_context: dict[str, Any]
) -> list[str]:
    """Validate consistency between automation and metadata."""
    warnings = []
    
    # Check device context matches entities
    automation_entities = set(self._extract_entities_from_yaml(automation_dict))
    context_entities = set(device_context.get("entity_ids", []))
    
    if automation_entities != context_entities:
        warnings.append(
            f"Entity mismatch: automation has {len(automation_entities)} entities, "
            f"device context has {len(context_entities)} entities"
        )
    
    return warnings
```

### 7. **Add JSON Storage for Analytics** (Low Priority)

**Why**: JSON enables analytics, querying, pattern detection, and better traceability.

**How**:
- Generate JSON in preview tool (even if not used for YAML generation)
- Store JSON in preview response
- Store JSON in database for analytics
- Enable querying automations by metadata (use_case, complexity, device_types, etc.)

**Implementation**:
```python
# In preview_automation_from_prompt tool
async def _generate_json_for_analytics(
    self, request: AutomationPreviewRequest, automation_dict: dict[str, Any]
) -> dict[str, Any]:
    """Generate JSON for analytics (even if not used for YAML generation)."""
    # Extract metadata from YAML
    device_context = await self._extract_device_context(automation_dict)
    
    # Generate JSON with metadata
    automation_json = {
        "alias": request.alias,
        "description": automation_dict.get("description"),
        "triggers": automation_dict.get("trigger", []),
        "actions": automation_dict.get("action", []),
        "device_context": device_context,
        "use_case": self._infer_use_case(automation_dict),
        "complexity": self._infer_complexity(automation_dict),
        "safety_score": self._calculate_safety_score(automation_dict, device_context)
    }
    
    return automation_json
```

### 8. **Improve Error Messages** (Medium Priority)

**Why**: Current error messages could be more helpful. Missing suggestions for fixes.

**How**:
- Provide specific error messages with entity IDs
- Suggest fixes for common issues (e.g., "Entity 'light.office_led' not found. Did you mean 'light.office_go'?")
- Link to documentation for complex errors
- Provide examples for fix patterns

### 9. **Add Validation Metrics** (Low Priority)

**Why**: No visibility into validation performance, common errors, validation success rates.

**How**:
- Track validation metrics (success rate, error types, latency)
- Log validation results for analysis
- Provide validation dashboard
- Alert on validation failures

### 10. **Add YAML Normalization** (Medium Priority)

**Why**: YAML from LLM may not be normalized (formatting, ordering, etc.). Normalized YAML is easier to read and compare.

**How**:
- Use YAML Validation Service normalization (if available)
- Normalize YAML formatting, ordering
- Ensure consistent YAML style

---

## Priority Matrix

| Recommendation | Priority | Impact | Effort | Recommendation |
|---------------|----------|--------|--------|----------------|
| Mandatory Entity Validation | Critical | High | Low | **Do First** - Prevents invalid automations |
| Add Device Validation | High | High | Medium | **Do Soon** - Validates device capabilities |
| Enhanced Safety Validation | High | High | Medium | **Do Soon** - Improves safety |
| Integrate JSON-Based Flow | High | High | High | **Consider** - Adds metadata and better validation |
| Device Context Extraction | Medium | Medium | Medium | **Do Later** - Improves traceability |
| Consistency Checks | Medium | Medium | Low | **Do Later** - Prevents inconsistencies |
| Improve Error Messages | Medium | Medium | Low | **Do Later** - Better UX |
| JSON Storage for Analytics | Low | Low | Medium | **Consider** - Enables analytics |
| Add Validation Metrics | Low | Low | Medium | **Consider** - Monitoring |
| Add YAML Normalization | Medium | Low | Low | **Do Later** - Better readability |

---

## Conclusion

The ha-agent interface currently uses a **direct YAML generation flow** (no JSON intermediate step), which is fast and simple but lacks structured metadata and comprehensive validation. The **alternative JSON-based flow** in `ai-automation-service-new` provides better validation and metadata but is not currently integrated.

**Key Recommendations**:
1. **Critical**: Add mandatory entity validation (currently optional)
2. **High Priority**: Add device validation and enhanced safety validation
3. **Consider**: Integrate JSON-based flow for better metadata and validation
4. **Future**: Add device context extraction, consistency checks, analytics

**Best Path Forward**:
- Short-term: Add mandatory entity validation and device validation to current flow
- Medium-term: Integrate JSON-based flow as optional enhancement
- Long-term: Move to JSON-first approach with YAML as output format

---

## Appendix: Code References

### Current Production Flow
- Chat Endpoint: `services/ha-ai-agent-service/src/api/chat_endpoints.py`
- Preview Tool: `services/ha-ai-agent-service/src/tools/ha_tools.py:108`
- Validation Chain: `services/ha-ai-agent-service/src/services/validation/validation_chain.py`
- Entity Extraction: `services/ha-ai-agent-service/src/tools/ha_tools.py:640`
- Safety Checks: `services/ha-ai-agent-service/src/tools/ha_tools.py:297`

### Alternative Flow
- JSON Generation: `services/ai-automation-service-new/src/services/yaml_generation_service.py:70`
- OpenAI Client: `services/ai-automation-service-new/src/clients/openai_client.py:268`
- JSON Validation: `shared/homeiq_automation/validator.py:50`
- JSON to YAML: `services/ai-automation-service-new/src/services/yaml_generation_service.py:206`
