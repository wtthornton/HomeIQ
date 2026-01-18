# Switch LED Entity Resolution Improvements Plan

**Date:** 2026-01-16  
**Issue:** "office switch led" not resolving to `sensor.office_light_switch_led_effect`

## Root Cause

**Entity Resolution Service:**
- Treats "LED" as device type keyword (matches LED strips)
- No pattern matching for "device + attribute" descriptions
- "switch LED" → Incorrectly matches LED devices instead of switch LED sensor

**Verified Entities:**
- ✅ `sensor.office_light_switch_led_effect` - LED effect sensor (color, duration, effect, level)
- ✅ `number.office_light_switch_ledcolorwhenon` - LED color when on (0-255)
- ✅ `number.office_light_switch_ledcolorwhenoff` - LED color when off (0-255)
- ✅ `number.office_light_switch_ledintensitywhenon` - LED intensity when on (0-100)
- ✅ `number.office_light_switch_ledintensitywhenoff` - LED intensity when off (0-100)

## Solution Requirements

### 1. Pattern Matching for "Switch LED"

**Pattern:** "switch LED" → LED indicator on switch device

**Implementation:**
- Add pattern matching before device type keyword matching
- Recognize "device + attribute" descriptions
- Pattern: "switch led" → match entities with both "switch" and "led" in name

### 2. Enhanced Entity Resolution

**Changes:**
1. Add pattern detection: "switch led", "switch's led", "led on switch"
2. Score entities with both keywords higher
3. Prioritize `sensor.*_led_effect` entities for "switch led" patterns

### 3. System Prompt Updates

**Add Section:** "Zigbee Switch LED Indicators"

- Explain LED indicators on switches
- Examples: "office switch led", "flash switch led red"
- Entity naming: `sensor.{device}_led_effect`

## Implementation Plan

### Priority 1: Pattern Matching in Entity Resolution ✅

**File:** `services/ha-ai-agent-service/src/services/entity_resolution/entity_resolution_service.py`

**Changes:**
1. Add `PATTERN_KEYWORDS` for combined descriptions
2. Check patterns before device type keywords
3. Boost score for entities matching both "switch" and "led"

### Priority 2: System Prompt Guidance ✅

**File:** `services/ha-ai-agent-service/src/prompts/system_prompt.py`

**Changes:**
1. Add "Zigbee Switch LED Controls" section
2. Include entity resolution examples
3. Explain LED effect sensor usage
