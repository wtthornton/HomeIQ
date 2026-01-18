# Switch LED Entity Resolution Issue Analysis

**Date:** 2026-01-16  
**Issue:** "office switch led" not correctly resolved to switch LED indicator controls

## Problem Statement

When user requests "office switch led" (referring to the LED indicator on the Zigbee switch), the entity resolution service treats "LED" as a device type keyword for LED devices (like WLED strips), not as an attribute of switches.

## Root Cause Analysis

### 1. Entity Resolution Service Limitation

**File:** `services/ha-ai-agent-service/src/services/entity_resolution/entity_resolution_service.py`

**Current Behavior:**
```python
DEVICE_TYPE_KEYWORDS = {
    "led": ["led", "wled"],      # Treats "led" as device type (LED strip)
    "strip": ["strip", "stripes"],
    "bulb": ["bulb", "light", "lamp"],
}
```

**Problem:**
- When prompt contains "led", it matches against LED devices (WLED strips, LED bulbs)
- Does not understand "switch LED" pattern (LED indicator on a switch)
- No pattern matching for combined device descriptions

**User Prompt:** "office switch led"
- Entity resolution sees: `device_type="led"` (matches LED devices)
- Should see: `device="switch"` + `attribute="led"` (LED indicator on switch)

### 2. System Prompt Missing Guidance

**File:** `services/ha-ai-agent-service/src/prompts/system_prompt.py`

**Missing:**
- No guidance about LED indicators on switches
- No examples of "switch LED" patterns
- No information about Zigbee switch LED controls

### 3. Zigbee Switch LED Controls

From Zigbee2MQTT interface (Office Light Switch - Inovelli VZM31-SN):
- **LED Effect**: Dropdown (e.g., "clear_effect")
- **Color**: 0-255 (hue color circle)
- **Level**: 0-100 (LED brightness)
- **Duration**: 1-60 seconds, 61-120 minutes, 121-254 hours, 255 indefinitely

**How these are exposed in Home Assistant:**
- Need to verify if exposed as:
  - Separate light entity (e.g., `light.office_light_switch`)
  - Attributes on switch entity
  - Direct MQTT service calls

## Impact

### User Experience
- ❌ User says "office switch led" → System matches wrong entity (LED strip instead of switch LED)
- ❌ Automation created with wrong entity → "Unknown entity" warnings
- ❌ User confusion about why LED controls not working

### System Behavior
- Entity resolution incorrectly categorizes "led" as device type
- No pattern matching for "device + attribute" descriptions
- Missing context about Zigbee switch capabilities

## Solution Requirements

### 1. Enhanced Entity Resolution Pattern Matching

**Pattern:** "switch LED" → LED indicator on switch device

**Implementation:**
```python
# Pattern matching for combined descriptions
PATTERN_KEYWORDS = {
    "switch_led": ["switch led", "switch's led", "switch indicator", "led on switch"],
    "switch_button": ["switch button", "button on switch"],
}
```

### 2. Device Attribute Awareness

**Enhancement:** Understand device relationships
- Switch → LED indicator (attribute, not separate device)
- Switch → Button (attribute, not separate device)

### 3. System Prompt Updates

**Add Section:** "Zigbee Switch LED Controls"

```markdown
## Zigbee Switch LED Indicators

Some Zigbee switches (e.g., Inovelli VZM31-SN) have LED indicator lights with:
- **LED Effect**: Animation effect (clear_effect, blink, pulse, etc.)
- **Color**: Hue color (0-255, or RGB)
- **Level**: LED brightness (0-100)
- **Duration**: Effect duration (1-60 seconds, 61-120 minutes, 121-254 hours)

**Entity Resolution:**
- "office switch led" → LED indicator on office switch
- Not a separate device, but an attribute of the switch
- May be exposed as: light entity, switch attributes, or MQTT service calls
```

### 4. Context Builder Enhancement

**Enhancement:** Include Zigbee switch LED capabilities in context
- When switch entities are detected, include LED control capabilities
- Extract LED exposes from Zigbee2MQTT device definitions
- Include LED effect lists, color modes, etc.

## Implementation Plan

### Priority 1: Pattern Matching for "Switch LED"

**File:** `services/ha-ai-agent-service/src/services/entity_resolution/entity_resolution_service.py`

**Changes:**
1. Add pattern matching for "device + attribute" descriptions
2. Recognize "switch LED" as LED indicator on switch, not LED device
3. Score matches considering device relationships

### Priority 2: System Prompt Updates

**File:** `services/ha-ai-agent-service/src/prompts/system_prompt.py`

**Changes:**
1. Add "Zigbee Switch LED Controls" section
2. Include examples of "switch LED" patterns
3. Explain entity resolution for LED indicators

### Priority 3: Context Enhancement

**File:** `services/ha-ai-agent-service/src/services/context_builder.py`

**Changes:**
1. Include Zigbee switch LED capabilities when switches detected
2. Extract LED exposes from device intelligence service
3. Add LED control examples to context

## Testing Plan

### Test Case 1: "office switch led"
- **Expected:** Resolves to LED indicator on Office Light Switch
- **Verify:** Correct entity/attributes matched

### Test Case 2: "turn office switch led red"
- **Expected:** Sets LED color to red on Office Light Switch
- **Verify:** Correct service call with LED attributes

### Test Case 3: "flash office switch led for 15 seconds"
- **Expected:** Sets LED effect to blink/pulse with 15 second duration
- **Verify:** Correct effect and duration parameters

## Next Steps

1. ✅ Analyze root cause (this document)
2. ⏳ Implement pattern matching in entity resolution
3. ⏳ Update system prompt with Zigbee switch LED guidance
4. ⏳ Test entity resolution with "switch LED" patterns
5. ⏳ Verify LED control automation creation
