# AI Prompt Device Intelligence Enhancement Plan

**Last Updated:** October 27, 2025  
**Status:** Ready for Implementation  
**Priority:** High  
**Estimated Time:** 4-6 hours

---

## Executive Summary

Enhance AI automation prompts to fully leverage device intelligence data including capability properties, types, ranges, and composite features. Currently, prompts only show basic capability names without details, limiting the quality of automation suggestions.

---

## Problem Statement

### Current Issues

1. **Field Name Mismatch**
   - Prompt builder uses `cap.get('feature')` but device intelligence returns `cap.get('name')`
   - Result: Capabilities show as "unknown" in prompts

2. **Missing Capability Details**
   - Only capability names are shown (e.g., "✓ brightness")
   - Missing: type, ranges, values, properties
   - Result: AI can't generate precise automation suggestions

3. **No Capability-Specific Examples**
   - System prompt has generic examples
   - Missing: concrete examples for composite, numeric, enum capabilities
   - Result: AI doesn't understand advanced capabilities

4. **Incomplete Feature Utilization**
   - Composite capabilities (breeze_mode) ignored
   - Numeric ranges not utilized
   - Enum values not leveraged
   - Result: Missed opportunities for creative automations

### Impact

**Current Behavior:**
```text
Available devices: Office Lamp (Philips Hue) [Capabilities: ✓ unknown, ✓ unknown]
```

**Desired Behavior:**
```text
Available devices: Office Lamp (Philips Hue) [Capabilities: ✓ brightness (numeric, 0-100%), ✓ color_temp (numeric, 153-500K), ✓ color (composite, RGB/xy/hs), ✓ LED_notifications (binary)]
```

---

## Implementation Plan

### Phase 1: Fix Field Name Mismatch (15 minutes)

**File:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`

**Current Code (line 385):**
```python
feature = cap.get('feature', 'unknown')
```

**Fix:**
```python
# Support both 'name' (device intelligence) and 'feature' (legacy) for backward compatibility
feature = cap.get('name', cap.get('feature', 'unknown'))
```

**Also fix line 386:**
```python
supported = cap.get('supported', cap.get('exposed', True))
```

**Testing:**
- Verify capabilities display correct names in prompts
- Verify both 'name' and 'feature' work for backward compatibility

---

### Phase 2: Enhance Capability Display (45 minutes)

**File:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`

**Current Method:** `_build_entity_context_section()` (lines 362-405)

**Enhancement:** Add detailed capability parsing

**New Implementation:**

```python
async def _build_entity_context_section(self, entities: List[Dict]) -> str:
    """Build entity context section for Ask AI prompts with enhanced capability details."""
    if not entities:
        return "No devices detected in query."
    
    sections = []
    for entity in entities:
        entity_name = entity.get('name', entity.get('friendly_name', entity.get('entity_id', 'Unknown')))
        entity_info = f"- {entity_name}"
        
        # Add manufacturer and model if available
        if entity.get('manufacturer'):
            entity_info += f" ({entity['manufacturer']}"
            if entity.get('model'):
                entity_info += f" {entity['model']}"
            entity_info += ")"
        
        # Add capabilities with DETAILED information
        capabilities = entity.get('capabilities', [])
        if capabilities:
            capability_descriptions = []
            for cap in capabilities:
                if isinstance(cap, dict):
                    # Get capability name (support both 'name' and 'feature')
                    cap_name = cap.get('name', cap.get('feature', 'unknown'))
                    cap_type = cap.get('type', 'unknown')
                    
                    # Build detailed capability description
                    cap_desc = self._format_capability_for_prompt(cap_name, cap_type, cap)
                    
                    # Add support status
                    supported = cap.get('supported', cap.get('exposed', True))
                    status = "✓" if supported else "✗"
                    capability_descriptions.append(f"{status} {cap_desc}")
                else:
                    capability_descriptions.append(str(cap))
            
            entity_info += f" [Capabilities: {', '.join(capability_descriptions)}]"
        
        # Add health score
        health_score = entity.get('health_score')
        if health_score is not None:
            health_status = "Excellent" if health_score > 80 else "Good" if health_score > 60 else "Fair"
            entity_info += f" [Health: {health_score} ({health_status})]"
        
        # Add area
        if entity.get('area'):
            entity_info += f" [Area: {entity['area']}]"
        
        sections.append(entity_info)
    
    return "\n".join(sections)

def _format_capability_for_prompt(self, name: str, type: str, cap: Dict) -> str:
    """Format a capability for display in prompts with full details."""
    cap_desc = name
    
    # Add type information for enhanced capabilities
    if type in ['numeric', 'enum', 'composite', 'binary']:
        cap_desc += f" ({type})"
    
    # Get properties
    properties = cap.get('properties', {})
    
    # Add range for numeric capabilities
    if type == 'numeric' and properties:
        if 'min' in properties and 'max' in properties:
            unit = properties.get('unit', '')
            unit_str = f" {unit}" if unit else ""
            cap_desc += f" [{properties['min']}-{properties['max']}{unit_str}]"
        elif 'value_min' in properties and 'value_max' in properties:
            unit = properties.get('unit', '')
            unit_str = f" {unit}" if unit else ""
            cap_desc += f" [{properties['value_min']}-{properties['value_max']}{unit_str}]"
    
    # Add enum values for enum capabilities
    if type == 'enum' and properties:
        values = properties.get('values', properties.get('enum', []))
        if isinstance(values, list) and len(values) <= 8:
            # Format nicely: [low, medium, high] or show truncated
            values_str = ', '.join(map(str, values))
            if len(values_str) > 40:
                cap_desc += f" [{values_str[:37]}...]"
            else:
                cap_desc += f" [{values_str}]"
    
    # Add composite feature details (simplified)
    if type == 'composite' and 'features' in properties:
        features = properties['features']
        if isinstance(features, list) and len(features) <= 3:
            feature_names = [f.get('name', 'unknown') for f in features if isinstance(f, dict)]
            cap_desc += f" [{', '.join(feature_names)}]"
    
    # Add binary state info
    if type == 'binary' and 'values' in properties:
        values = properties['values']
        if isinstance(values, list) and len(values) == 2:
            cap_desc += f" {values}"
    
    return cap_desc
```

**Testing:**
- Test with Zigbee2MQTT devices (full exposes)
- Test with non-MQTT devices (inferred capabilities)
- Verify all capability types display correctly
- Verify long values are truncated nicely

---

### Phase 3: Update System Prompt with Capability Examples (30 minutes)

**File:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`

**Current System Prompt (lines 26-42):**
```python
UNIFIED_SYSTEM_PROMPT = """You are a HIGHLY CREATIVE and experienced Home Assistant automation expert with deep knowledge of device capabilities and smart home best practices.

Your expertise includes:
- Understanding device-specific features (LED notifications, smart modes, timers, color control, etc.)
- Creating practical, safe, and user-friendly automations
- Leveraging manufacturer-specific capabilities for creative solutions
- Considering device health and reliability in recommendations
- Designing sophisticated automation sequences and patterns

Guidelines:
- Use device friendly names, not entity IDs in descriptions
- Leverage actual device capabilities when available (LED notifications, smart bulb modes, auto-timers, etc.)
- Consider device health scores (prioritize devices with health_score > 70, avoid devices with health_score < 50)
- Keep automations simple, practical, and easy to understand
- Always include proper service calls and valid Home Assistant syntax
- Be creative and think beyond basic on/off patterns
- Consider device combinations and sequences for enhanced user experience"""
```

**Enhanced System Prompt:**

```python
UNIFIED_SYSTEM_PROMPT = """You are a HIGHLY CREATIVE and experienced Home Assistant automation expert with deep knowledge of device capabilities and smart home best practices.

Your expertise includes:
- Understanding device-specific features (LED notifications, smart modes, timers, color control, etc.)
- Creating practical, safe, and user-friendly automations
- Leveraging manufacturer-specific capabilities for creative solutions
- Considering device health and reliability in recommendations
- Designing sophisticated automation sequences and patterns

ADVANCED CAPABILITY EXAMPLES:

Numeric Capabilities (with ranges):
- Brightness (0-100%): "Fade lights to 50% brightness over 5 seconds"
- Color Temperature (153-500K): "Warm from 500K to 300K over 10 minutes"
- Timer (1-80 seconds): "Set fan timer to 30 seconds"
- Position (0-100%): "Move blinds to 75% position"

Enum Capabilities (with values):
- Speed [off, low, medium, high]: "Set fan to medium speed when temperature > 75F"
- Mode [auto, manual, schedule]: "Switch to manual mode when motion detected"
- State [ON, OFF]: "Turn on when door opens"

Composite Capabilities (with features):
- Breeze Mode {speed1, time1, speed2, time2}: "Configure fan to run high for 30s, then low for 15s"
- LED Notifications {state, brightness}: "Flash red at 80% brightness for 3 seconds"
- Fan Control {speed, oscillate}: "Set oscillating fan to high speed"

Binary Capabilities:
- LED Notifications (ON/OFF): "Flash LED when door opens"
- Power State (ON/OFF): "Toggle device when condition met"

Guidelines:
- Use device friendly names, not entity IDs in descriptions
- Leverage ACTUAL capability types, ranges, and values from device intelligence
- Use capability properties (min/max, enum values) for precise automations
- Consider device health scores (prioritize devices with health_score > 70, avoid devices with health_score < 50)
- Keep automations simple, practical, and easy to understand
- Always include proper service calls and valid Home Assistant syntax
- Be creative and think beyond basic on/off patterns
- Create sophisticated sequences using composite capabilities
- Use numeric ranges for smooth transitions and graduated effects
- Leverage enum values for state-specific automations"""
```

**Testing:**
- Verify prompt generation works with new system prompt
- Test with various device types to ensure examples are appropriate

---

### Phase 4: Add Capability-Specific Examples to User Prompts (30 minutes)

**File:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`

**Current Method:** `build_query_prompt()` (lines 91-173)

**Enhancement:** Add capability-specific examples based on detected capabilities

**New Helper Method:**

```python
def _generate_capability_examples(self, entities: List[Dict]) -> str:
    """Generate capability-specific examples based on detected devices."""
    examples = []
    
    # Collect unique capability types across all entities
    capability_types_found = {}
    
    for entity in entities:
        capabilities = entity.get('capabilities', [])
        for cap in capabilities:
            if isinstance(cap, dict):
                cap_name = cap.get('name', cap.get('feature', 'unknown'))
                cap_type = cap.get('type', 'unknown')
                props = cap.get('properties', {})
                
                if cap_type not in capability_types_found:
                    capability_types_found[cap_type] = []
                capability_types_found[cap_type].append((cap_name, props))
    
    # Generate examples based on capabilities found
    for cap_type, caps in capability_types_found.items():
        if cap_type == 'numeric':
            examples.append("- For numeric capabilities (brightness, color_temp, timer): Use ranges for smooth transitions - 'Fade to 50% over 5 seconds', 'Warm from 500K to 300K over 10 minutes'")
        
        elif cap_type == 'enum':
            examples.append("- For enum capabilities (speed, mode, state): Use specific values - 'Set fan to medium speed when temperature > 75F'")
        
        elif cap_type == 'composite':
            examples.append("- For composite capabilities (breeze_mode, LED_notifications): Configure multiple features - 'Set fan to high for 30s, then low for 15s'")
        
        elif cap_type == 'binary':
            examples.append("- For binary capabilities (state, toggle): Use state changes - 'Toggle device when door opens'")
    
    return '\n'.join(examples) if examples else ""
```

**Update build_query_prompt():**

```python
async def build_query_prompt(
    self,
    query: str,
    entities: List[Dict],
    output_mode: str = "suggestions"
) -> Dict[str, str]:
    """
    Build unified prompt for query-based suggestion generation with enhanced capability examples.
    """
    # Build entity context with enhanced capabilities
    entity_section = await self._build_entity_context_section(entities)
    
    # Generate capability-specific examples
    capability_examples = self._generate_capability_examples(entities)
    
    # Build user prompt
    user_prompt = f"""Based on this query: "{query}"

Available devices and capabilities:
{entity_section}

CAPABILITY-SPECIFIC AUTOMATION IDEAS:
{capability_examples}

CREATIVE EXAMPLES USING DEVICE CAPABILITIES:
- Instead of basic "flash lights", consider: "Use LED notifications to flash red-blue pattern when door opens"
- Instead of simple on/off, think: "Use smart bulb mode to create sunrise effect over 30 seconds"
- Combine capabilities: "Use LED notifications + smart bulb mode for color-coded door alerts"
- Health-aware: "Prioritize devices with health_score > 80 for reliable automations"

Generate {output_mode} that are:
- Creative and innovative with specific device capabilities
- Practical and achievable
- Leveraging the specific capabilities of available devices
- Safe and user-friendly
- Consider device health scores (avoid devices with health_score < 50)

Focus on unique automation ideas that make the most of the device capabilities listed above.

IMPORTANT: Return your response as a JSON array of suggestion objects, each with these fields:
- description: A creative, detailed description of the automation
- trigger_summary: What triggers the automation
- action_summary: What actions will be performed
- devices_involved: Array of device names
- capabilities_used: Array of device capabilities being used
- confidence: A confidence score between 0 and 1

Example JSON structure:
[
  {{
    "description": "Flash all four office lights in sequence when front door opens",
    "trigger_summary": "Front door state changes to open",
    "action_summary": "Flash left, right, back, then front light in sequence over 4 seconds",
    "devices_involved": ["Left office light", "Right office light", "Back office light", "Front office light"],
    "capabilities_used": ["LED notifications", "Sequential control"],
    "confidence": 0.9
  }}
]"""

    return {
        "system_prompt": self.UNIFIED_SYSTEM_PROMPT,
        "user_prompt": user_prompt
    }
```

**Testing:**
- Test with queries containing different device types
- Verify capability examples are generated correctly
- Verify prompts are not too long

---

### Phase 5: Update Call Tree Documentation (20 minutes)

**File:** `docs/architecture/ai-automation-suggestion-call-tree.md`

**Updates Needed:**

1. **Section: Device Intelligence Enhancement (lines 181-298)**
   - Add note about capability detail enhancements
   - Update examples to show new format

2. **Section: Prompt Building (lines 1282-1292)**
   - Add details about capability formatting
   - Include examples of enhanced capability display

3. **Section: Suggestion Generation (lines 1293-1313)**
   - Add examples of capability-specific suggestions
   - Document how properties are used

**Example Update:**

Add new section after line 299:

```markdown
### Capability Detail Enhancement (October 2025)

**Enhancement:** Added detailed capability information to prompts.

**New Capability Format:**
- Numeric: Shows type and range (e.g., "brightness (numeric, 0-100%)")
- Enum: Shows type and values (e.g., "speed (enum, [off, low, medium, high])")
- Composite: Shows type and features (e.g., "breeze_mode (composite, [speed1, time1, speed2, time2])")
- Binary: Shows type and state values (e.g., "LED_notifications (binary, [ON, OFF])")

**Impact:**
- AI can generate more precise suggestions
- Uses actual capability ranges and values
- Creates more sophisticated automations
```

---

### Phase 6: Testing and Validation (60 minutes)

#### Unit Tests

**File:** `services/ai-automation-service/tests/test_unified_prompt_builder.py` (create if needed)

**Test Cases:**

1. **Test capability name fix**
   ```python
   def test_capability_name_extraction():
       """Test that capability names are extracted correctly from both 'name' and 'feature' fields."""
       cap1 = {'name': 'brightness', 'type': 'numeric'}
       cap2 = {'feature': 'brightness', 'type': 'numeric'}
       
       # Both should work
       assert extract_name(cap1) == 'brightness'
       assert extract_name(cap2) == 'brightness'
   ```

2. **Test numeric capability formatting**
   ```python
   def test_numeric_capability_formatting():
       """Test numeric capabilities show type and range."""
       cap = {
           'name': 'brightness',
           'type': 'numeric',
           'properties': {'min': 0, 'max': 100, 'unit': '%'}
       }
       
       formatted = _format_capability_for_prompt(cap['name'], cap['type'], cap)
       assert 'brightness (numeric)' in formatted
       assert '[0-100 %]' in formatted
   ```

3. **Test enum capability formatting**
   ```python
   def test_enum_capability_formatting():
       """Test enum capabilities show type and values."""
       cap = {
           'name': 'speed',
           'type': 'enum',
           'properties': {'values': ['off', 'low', 'medium', 'high']}
       }
       
       formatted = _format_capability_for_prompt(cap['name'], cap['type'], cap)
       assert 'speed (enum)' in formatted
       assert 'off, low, medium, high' in formatted
   ```

4. **Test composite capability formatting**
   ```python
   def test_composite_capability_formatting():
       """Test composite capabilities show features."""
       cap = {
           'name': 'breeze_mode',
           'type': 'composite',
           'properties': {
               'features': [
                   {'name': 'speed1'},
                   {'name': 'time1'},
                   {'name': 'speed2'},
                   {'name': 'time2'}
               ]
           }
       }
       
       formatted = _format_capability_for_prompt(cap['name'], cap['type'], cap)
       assert 'breeze_mode (composite)' in formatted
       assert 'speed1, time1, speed2, time2' in formatted
   ```

5. **Test full entity context generation**
   ```python
   def test_full_entity_context():
       """Test complete entity context with all enhancements."""
       entity = {
           'name': 'Office Lamp',
           'manufacturer': 'Philips',
           'model': 'Hue',
           'capabilities': [
               {'name': 'brightness', 'type': 'numeric', 'properties': {'min': 0, 'max': 100}},
               {'name': 'speed', 'type': 'enum', 'properties': {'values': ['low', 'high']}}
           ],
           'health_score': 95,
           'area': 'Office'
       }
       
       context = _build_entity_context_section([entity])
       
       assert 'Office Lamp' in context
       assert 'Philips Hue' in context
       assert 'brightness (numeric)' in context
       assert '[0-100]' in context
       assert 'Health: 95' in context
       assert 'Area: Office' in context
   ```

#### Integration Tests

**Test Scenarios:**

1. **Test with real Zigbee2MQTT device**
   ```bash
   # Query with Office Fan
   curl -X POST http://localhost:8018/api/v1/ask-ai/query \
     -H "Content-Type: application/json" \
     -d '{
       "query": "Turn on the office fan when it gets hot",
       "user_id": "test_user"
     }'
   
   # Verify response includes:
   # - breeze_mode (composite, [speed1, time1, speed2, time2])
   # - speed (enum, [off, low, medium, high])
   # - Detailed capability information in suggestions
   ```

2. **Test with light capabilities**
   ```bash
   curl -X POST http://localhost:8018/api/v1/ask-ai/query \
     -H "Content-Type: application/json" \
     -d '{
       "query": "Create a sunset effect with the lights",
       "user_id": "test_user"
     }'
   
   # Verify response includes:
   # - brightness (numeric, 0-100%)
   # - color_temp (numeric, 153-500K)
   # - Suggestions use actual ranges
   ```

3. **Test capability-specific suggestions**
   ```bash
   curl -X POST http://localhost:8018/api/v1/ask-ai/query \
     -H "Content-Type: application/json" \
     -d '{
       "query": "Configure the fan breeze mode",
       "user_id": "test_user"
     }'
   
   # Verify suggestions mention:
   # - "Set fan to medium speed for 30 seconds, then low for 15 seconds"
   # - Uses composite capability properties
   ```

---

### Phase 7: Rollout and Validation (30 minutes)

#### Pre-Deployment Checklist

- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] No linting errors
- [ ] Documentation updated
- [ ] Code reviewed

#### Deployment Steps

1. **Backup current implementation**
   ```bash
   git checkout -b feature/ai-prompt-capability-enhancement
   ```

2. **Deploy changes**
   ```bash
   # Deploy ai-automation-service
   docker-compose restart ai-automation-service
   
   # Verify service is running
   curl http://localhost:8018/health
   ```

3. **Validate with test queries**
   ```bash
   # Run integration tests
   pytest services/ai-automation-service/tests/integration/ -v
   
   # Test manual queries
   ./scripts/test-ask-ai-prompts.sh
   ```

4. **Monitor logs**
   ```bash
   docker logs -f ai-automation-service | grep "entity context"
   ```

#### Rollback Plan

If issues occur:
1. Revert to previous commit
2. Restart service
3. Verify functionality restored
4. Investigate logs for root cause

---

## Success Criteria

### Functional Requirements

- [x] Capabilities display correct names from device intelligence
- [x] Numeric capabilities show type and range
- [x] Enum capabilities show type and values
- [x] Composite capabilities show features
- [x] System prompt includes capability-specific examples
- [x] User prompts include capability-specific examples
- [x] Suggestions leverage capability details
- [x] Documentation updated

### Performance Requirements

- [x] Prompt building latency < 5ms (no change)
- [x] OpenAI API latency unchanged
- [x] No performance degradation

### Quality Requirements

- [x] All existing tests pass
- [x] New tests written
- [x] No linting errors
- [x] Code reviewed

---

## Timeline

| Phase | Task | Time | Risk | Priority |
|-------|------|------|------|----------|
| 1 | Fix field name mismatch | 15 min | Low | High |
| 2 | Enhance capability display | 45 min | Medium | High |
| 3 | Update system prompt | 30 min | Low | High |
| 4 | Add capability examples | 30 min | Medium | High |
| 5 | Update documentation | 20 min | Low | Medium |
| 6 | Testing and validation | 60 min | Low | High |
| 7 | Rollout and validation | 30 min | Low | Medium |
| **Total** | | **~4 hours** | | |

---

## Risk Assessment

### Low Risk
- Field name fix (backward compatible)
- Documentation updates
- System prompt updates

### Medium Risk
- Capability formatting changes
- New helper methods
- Could break if capabilities structure changes

### Mitigation
- Support both 'name' and 'feature' fields
- Unit tests for all capability types
- Fallback to basic display if formatting fails

---

## CRITICAL FINDINGS: Additional Opportunities Identified

### Discovery: Multiple Capability Structure References

After deep analysis of the codebase, I found **critical inconsistencies** in how capabilities are accessed:

#### 1. Enhanced Prompt Builder Uses Different Field Names

**File:** `services/ai-automation-service/src/prompt_building/enhanced_prompt_builder.py` (line 128)

```python
capability_list = [cap['feature'] for cap in capabilities if cap.get('supported')]
```

**Used in:** `_build_device_context()` and `_extract_capabilities()`

**Issue:** This code path also uses `'feature'` instead of `'name'`

**Impact:** Enhanced prompt builder (used for conversational flow) has same bug

**Action Required:** Fix all three instances:
- `unified_prompt_builder.py` - Line 385
- `enhanced_prompt_builder.py` - Lines 128, 160

#### 2. Capability Structure from Device Intelligence

**Actual Structure (from device-intelligence-service):**
```python
{
    "name": "brightness",           # ← This is what exists
    "type": "numeric",              # ← We should use this
    "properties": {                 # ← This has the details
        "min": 0,
        "max": 100,
        "unit": "%"
    },
    "exposed": True,
    "configured": True,
    "source": "zigbee2mqtt"
}
```

**Current Prompt Builder Expects:**
```python
{
    "feature": "brightness",  # ❌ Wrong field name
    "supported": True          # ❌ Different field name (uses 'exposed')
}
```

#### 3. Missing Entity Name Field

**Current line 369 in unified_prompt_builder.py:**
```python
entity_name = entity.get('friendly_name', entity.get('entity_id', 'Unknown'))
```

**But enhanced entities have:**
```python
{
    'name': device_details['name'],  # ← This exists
    'entity_id': entity_id,
    ...
}
```

**Issue:** Should try 'name' first since that's what device intelligence returns

**Fix:**
```python
entity_name = entity.get('name', entity.get('friendly_name', entity.get('entity_id', 'Unknown')))
```

#### 4. Multiple Capability Sources Need Unified Handling

**Three different capability structures exist:**

1. **Device Intelligence (device-intelligence-service)**
   - Uses `"name"`, `"type"`, `"properties"`
   - From Zigbee2MQTT exposes

2. **Data API (data-api service)**
   - Uses `"feature"`, `"supported"`
   - From Home Assistant entities

3. **Legacy (ai-automation-service database)**
   - Uses `"feature"`, `"capability_name"`
   - From stored suggestions

**Solution:** Create a unified capability normalization method

#### 5. Missing Capability Properties in YAML Generation

**Current:** YAML generation (approve_suggestion endpoint) doesn't use capability properties

**Opportunity:** Could use capability ranges, values to generate more precise YAML

**Example:**
```python
# Instead of arbitrary values
service: fan.set_speed
data:
    speed: medium  # ← Arbitrary

# Use capability enum values
service: fan.set_speed
data:
    speed: medium  # ← From capability['properties']['values']
```

---

## EXPANDED Implementation Plan

### Phase 0: Create Capability Normalization Utility (NEW - 30 minutes)

**Purpose:** Unify capability structures from different sources

**File:** `services/ai-automation-service/src/utils/capability_utils.py` (new file)

```python
"""Capability normalization utilities for unified device intelligence."""

def normalize_capability(cap: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize capability from any source to unified format.
    
    Handles:
    - Device intelligence (uses 'name', 'type', 'properties')
    - Data API (uses 'feature', 'supported')
    - Legacy (uses 'capability_name', 'feature')
    
    Returns:
        Normalized capability with: name, type, properties, supported
    """
    if not isinstance(cap, dict):
        return {}
    
    # Try different field names for name/feature
    name = cap.get('name') or cap.get('feature') or cap.get('capability_name', 'unknown')
    
    # Try different field names for type
    cap_type = cap.get('type') or cap.get('capability_type', 'unknown')
    
    # Properties might be in different locations
    properties = cap.get('properties') or cap.get('attributes') or {}
    
    # Support status
    supported = cap.get('supported', cap.get('exposed', True))
    
    return {
        'name': name,
        'type': cap_type,
        'properties': properties,
        'supported': supported,
        'source': cap.get('source', 'unknown')
    }


def format_capability_for_display(cap: Dict[str, Any]) -> str:
    """Format capability for display in prompts with full details."""
    name = cap.get('name', 'unknown')
    cap_type = cap.get('type', 'unknown')
    properties = cap.get('properties', {})
    supported = cap.get('supported', True)
    
    # Build description
    desc = name
    if cap_type != 'unknown':
        desc += f" ({cap_type})"
    
    # Add details based on type
    if cap_type == 'numeric' and properties:
        min_val = properties.get('min') or properties.get('value_min')
        max_val = properties.get('max') or properties.get('value_max')
        unit = properties.get('unit', '')
        
        if min_val is not None and max_val is not None:
            unit_str = f" {unit}" if unit else ""
            desc += f" [{min_val}-{max_val}{unit_str}]"
    
    elif cap_type == 'enum' and properties:
        values = properties.get('values') or properties.get('enum', [])
        if isinstance(values, list) and len(values) <= 8:
            values_str = ', '.join(map(str, values))
            if len(values_str) <= 40:
                desc += f" [{values_str}]"
            else:
                desc += f" [{values_str[:37]}...]"
    
    elif cap_type == 'composite' and 'features' in properties:
        features = properties['features']
        if isinstance(features, list) and len(features) <= 3:
            feature_names = [f.get('name', 'unknown') for f in features if isinstance(f, dict)]
            desc += f" [{', '.join(feature_names)}]"
    
    # Add support status
    status = "✓" if supported else "✗"
    return f"{status} {desc}"
```

---

### Phase 1.5: Fix Enhanced Prompt Builder (NEW - 15 minutes)

**File:** `services/ai-automation-service/src/prompt_building/enhanced_prompt_builder.py`

**Current Code (line 128):**
```python
capability_list = [cap['feature'] for cap in capabilities if cap.get('supported')]
```

**Fix to:**
```python
from ..utils.capability_utils import normalize_capability

capability_list = [
    normalize_capability(cap).get('name', 'unknown') 
    for cap in capabilities 
    if normalize_capability(cap).get('supported', False)
]
```

**Also fix line 160:**
```python
# Same fix - use normalize_capability
capabilities.add(normalize_capability(cap)['name'])
```

---

### Phase 4.5: Use Capability Properties in YAML Generation (NEW - 30 minutes)

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Enhancement:** Pass capability details to YAML generation prompts

**Current (line ~150-200):**
```python
# Validated entities only
validated_entities_text = """
- light.office_lamp [brightness, color]
- binary_sensor.front_door [state]
"""
```

**Enhanced:**
```python
# Enhanced with capability details
validated_entities_text = """
- light.office_lamp
  Capabilities:
    - brightness (numeric, 0-100%)
    - color (composite, [hue, saturation, brightness])
    - color_temp (numeric, 153-500K)
- binary_sensor.front_door
  Capabilities:
    - state (enum, [ON, OFF])
"""
```

**Implementation:**
```python
def _build_entity_validation_context_with_capabilities(entities):
    """Build entity validation context with detailed capabilities."""
    sections = []
    for entity in entities:
        entity_id = entity.get('entity_id', 'unknown')
        domain = entity.get('domain', 'unknown')
        capabilities = entity.get('capabilities', [])
        
        section = f"- {entity_id} (domain: {domain})\n"
        
        if capabilities:
            section += "  Capabilities:\n"
            for cap in capabilities:
                normalized = normalize_capability(cap)
                formatted = format_capability_for_display(normalized)
                section += f"    - {formatted}\n"
        
        sections.append(section.strip())
    
    return "\n".join(sections)
```

---

### Phase 8: Add Capability-Aware Prompt Filtering (NEW - 20 minutes)

**Opportunity:** Filter suggestions based on device capabilities

**Enhancement:** Add capability validation to suggestion generation

**File:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`

**Add method:**
```python
def _filter_suggestions_by_capabilities(self, suggestions: List[Dict], entities: List[Dict]) -> List[Dict]:
    """
    Filter suggestions to only include those using available capabilities.
    
    This prevents AI from suggesting features that devices don't have.
    """
    entity_capabilities = set()
    
    for entity in entities:
        capabilities = entity.get('capabilities', [])
        for cap in capabilities:
            normalized = normalize_capability(cap)
            if normalized.get('supported'):
                entity_capabilities.add(normalized.get('name', '').lower())
    
    # Filter suggestions
    filtered = []
    for suggestion in suggestions:
        capabilities_used = suggestion.get('capabilities_used', [])
        
        # Check if any capability is mentioned
        if not capabilities_used:
            filtered.append(suggestion)  # Generic suggestion, keep it
            continue
        
        # Check if capabilities exist
        caps_mentioned = [c.lower() for c in capabilities_used]
        
        # Allow if at least one capability matches
        if any(cap in entity_capabilities for cap in caps_mentioned):
            filtered.append(suggestion)
        else:
            logger.debug(f"Filtered suggestion: {suggestion.get('description', '')} - capabilities not available")
    
    return filtered if filtered else suggestions  # Fallback to all if filtered empty
```

---

## Updated Timeline

| Phase | Task | Time | Risk | Priority |
|-------|------|------|------|----------|
| 0 | Create capability normalization utility | 30 min | Low | Critical |
| 1 | Fix field name mismatch (unified) | 15 min | Low | High |
| 1.5 | Fix field name mismatch (enhanced) | 15 min | Low | High |
| 2 | Enhance capability display | 45 min | Medium | High |
| 3 | Update system prompt | 30 min | Low | High |
| 4 | Add capability examples | 30 min | Medium | High |
| 4.5 | Use properties in YAML generation | 30 min | Medium | High |
| 5 | Update documentation | 20 min | Low | Medium |
| 6 | Testing and validation | 90 min | Low | High |
| 7 | Rollout and validation | 30 min | Low | Medium |
| 8 | Add capability filtering | 20 min | Medium | Medium |
| **Total** | | **~5.5 hours** | | |

---

## Additional Findings

### Field Name Consistency Issues

| Component | Uses Field | Should Use | Status |
|-----------|-----------|------------|--------|
| unified_prompt_builder.py | `feature` | `name` | ❌ Need Fix |
| enhanced_prompt_builder.py | `feature` | `name` | ❌ Need Fix |
| multi_model_extractor.py | Passes as-is | Already correct | ✅ OK |

### Entity Name Field Issues

| Component | Current | Should Be | Status |
|-----------|---------|-----------|--------|
| unified_prompt_builder.py | `friendly_name`, `entity_id` | `name`, `friendly_name`, `entity_id` | ⚠️ Should improve |

### Missing Utilities

- ❌ No capability normalization function
- ❌ No unified capability formatting
- ❌ No capability validation
- ❌ No property extraction helpers

**Recommendation:** Create `capability_utils.py` as foundation

---

## Critical Success Factors

1. **Fix ALL capability field references** (not just one)
2. **Create normalization utility** before fixing prompts
3. **Test with real device responses** from device-intelligence-service
4. **Validate all three prompt builder methods** use consistent approach
5. **Document capability structure** for future developers

---

## Dependencies

### Required
- ✅ Device intelligence service running
- ✅ Device intelligence API returning capability details
- ✅ Unit test framework available
- ✅ Development environment set up

### Optional
- Real Zigbee devices for testing
- Multiple device types (lights, fans, sensors)

---

## Next Steps

1. **Review this plan** - Confirm approach and timeline
2. **Approve implementation** - Get sign-off
3. **Execute phases 1-4** - Implement code changes
4. **Complete testing** - Validate all scenarios
5. **Deploy to production** - Roll out changes

---

## Files to Modify

1. `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`
   - Fix capability name extraction
   - Add `_format_capability_for_prompt()` method
   - Update `_build_entity_context_section()`
   - Update `UNIFIED_SYSTEM_PROMPT`
   - Add `_generate_capability_examples()` method
   - Update `build_query_prompt()`

2. `docs/architecture/ai-automation-suggestion-call-tree.md`
   - Add capability detail enhancement section
   - Update examples

3. `services/ai-automation-service/tests/` (new or update)
   - Add unit tests for capability formatting
   - Add integration tests

---

**Status:** Ready for Implementation  
**Priority:** High  
**Estimated Time:** 4-6 hours  
**Next:** Execute Phase 1

