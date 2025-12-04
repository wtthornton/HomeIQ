# Prompt and Context Injection Analysis

**Date:** December 4, 2025  
**Test Case:** "Make the office lights blink red every 15 minutes and then return back to the state they were"  
**Service:** ha-ai-agent-service

---

## Executive Summary

This analysis compares what information the LLM **needs** to create the automation vs what information it **actually receives** in the prompt. The analysis reveals critical gaps in context injection that prevent the LLM from generating correct automations.

---

## What the LLM Needs (Requirements Analysis)

For the automation request: **"Make the office lights blink red every 15 minutes and then return back to the state they were"**

### 1. Entity Resolution
- ✅ **Need:** Office light entity IDs or area_id for "office"
- ❌ **Have:** All lights show as "unassigned" - no office area mapping
- **Impact:** LLM cannot use `target.area_id: office` (prompt recommends this)

### 2. Time Trigger Pattern
- ✅ **Need:** How to trigger every 15 minutes
- ✅ **Have:** System prompt mentions time triggers but no specific pattern example
- **Impact:** LLM may not know `time_pattern` with `minutes: "/15"`

### 3. Color/Blink Capability
- ✅ **Need:** How to set lights to red color (RGB values)
- ❌ **Have:** "No capability patterns found" - no RGB color information
- **Impact:** LLM doesn't know RGB values for red or if lights support color

### 4. State Restoration Pattern
- ✅ **Need:** How to save current state and restore it
- ❌ **Have:** System prompt mentions "save current state" but no YAML pattern
- **Impact:** LLM doesn't know to use `scene.create` with `snapshot_entities`

### 5. Service Information
- ✅ **Need:** Available light services and parameters
- ❌ **Have:** "AVAILABLE SERVICES:" with empty content
- **Impact:** LLM doesn't know service parameters (rgb_color, brightness, etc.)

### 6. Area Information
- ✅ **Need:** Office area ID for targeting
- ❌ **Have:** "No areas found"
- **Impact:** Cannot use `target.area_id: office` as recommended in prompt

---

## Current Context Injection (What's Actually Provided)

### ✅ Entity Inventory (PARTIALLY HELPFUL)
```
Light: 52 entities (unassigned: 52)
  Examples: Bottom Of Stairs (light.bottom_of_stairs, device_id: f5d4aa05..., state: unavailable)
```

**What Helps:**
- Shows light entities exist
- Provides entity_id format
- Shows device_id format

**What Doesn't Help:**
- ❌ All lights are "unassigned" - no office area mapping
- ❌ No office-specific lights identified
- ❌ Examples don't show office lights

### ❌ Areas (MISSING - CRITICAL)
```
AREAS:
No areas found
```

**Impact:** 
- Cannot use `target.area_id: office` as recommended in system prompt
- Must use individual `entity_id` entries instead
- Less maintainable automation

### ❌ Available Services (MISSING - CRITICAL)
```
AVAILABLE SERVICES:

```

**Impact:**
- LLM doesn't know:
  - `light.turn_on` accepts `rgb_color: [255, 0, 0]` for red
  - `scene.create` accepts `snapshot_entities` for state saving
  - Service parameter formats and constraints

### ❌ Device Capability Patterns (MISSING - CRITICAL)
```
DEVICE CAPABILITY PATTERNS:
No capability patterns found
```

**Impact:**
- LLM doesn't know:
  - Lights support RGB color (0-255 range)
  - Color format (rgb_color vs hs_color)
  - Brightness range (0-255)

### ✅ Helpers & Scenes (PARTIALLY HELPFUL)
```
Scenes: Backyard Bright (scene.backyard_bright), ... (171 total scenes)
```

**What Helps:**
- Shows scene entity_id format
- Demonstrates scene naming patterns

**What Doesn't Help:**
- ❌ Doesn't explain how to CREATE scenes for state restoration
- ❌ Doesn't show `scene.create` with `snapshot_entities` pattern

---

## System Prompt Analysis

### ✅ What Helps

1. **Clear Single Purpose:** "Your ONLY job is to create automations"
2. **Tool Definition:** Explains `create_automation_from_prompt` tool
3. **YAML Structure:** Shows basic automation format
4. **Mode Selection:** Explains automation modes

### ❌ What's Missing

1. **State Restoration Pattern:**
   - Prompt says: "Saves current state" and "Restores previous state"
   - But doesn't show HOW (no YAML example)
   - Missing: `scene.create` with `snapshot_entities` pattern

2. **Time Pattern Trigger:**
   - Prompt shows: `platform: time` with `at: "07:00:00"`
   - But doesn't show `time_pattern` for recurring triggers
   - Missing: `minutes: "/15"` pattern example

3. **Color/Blink Pattern:**
   - Prompt doesn't explain how to set colors
   - Missing: RGB color format example
   - Missing: Blink pattern (turn on, delay, restore)

4. **Service Parameter Examples:**
   - Prompt shows basic `light.turn_on` with `brightness`
   - Missing: `rgb_color` parameter
   - Missing: `scene.create` service example

---

## Gap Analysis: Required vs Provided

| Requirement | Status | Impact | Priority |
|------------|--------|--------|----------|
| Office area ID | ❌ Missing | High - Cannot use area targeting | **CRITICAL** |
| Office light entity IDs | ⚠️ Partial | Medium - Must search through 52 unassigned lights | High |
| Light service parameters | ❌ Missing | High - Doesn't know rgb_color format | **CRITICAL** |
| Scene.create pattern | ❌ Missing | High - Doesn't know state restoration | **CRITICAL** |
| Time pattern trigger | ⚠️ Partial | Medium - No recurring pattern example | High |
| Color capabilities | ❌ Missing | High - Doesn't know RGB values | **CRITICAL** |
| State restoration YAML | ❌ Missing | High - No pattern example | **CRITICAL** |

---

## Recommendations

### 1. Fix Areas Service (CRITICAL)
**Problem:** "No areas found" but entities have area_id
**Solution:** 
- Check why areas service returns empty
- Ensure area_id mapping from entities is included in context
- Add area_id to entity inventory examples

### 2. Fix Services Summary (CRITICAL)
**Problem:** Services summary is empty
**Solution:**
- Debug why `get_services()` returns empty
- Ensure service schemas are included in context
- Add critical services: `light.turn_on`, `scene.create`, `scene.turn_on`

### 3. Fix Capability Patterns (CRITICAL)
**Problem:** No capability patterns found
**Solution:**
- Debug why capability patterns service returns empty
- Include RGB color ranges (0-255)
- Include brightness ranges
- Include supported color modes

### 4. Add State Restoration Pattern to System Prompt (CRITICAL)
**Problem:** Prompt mentions state restoration but no YAML example
**Solution:** Add to system prompt:
```yaml
# State Restoration Pattern
action:
  # 1. Save current state
  - service: scene.create
    data:
      scene_id: restore_state_{{ automation_id }}
      snapshot_entities:
        - light.office_light_1
        - light.office_light_2
  # 2. Apply effect
  - service: light.turn_on
    target:
      area_id: office
    data:
      rgb_color: [255, 0, 0]
  # 3. Restore state
  - service: scene.turn_on
    target:
      entity_id: scene.restore_state_{{ automation_id }}
```

### 5. Add Time Pattern Trigger Example (HIGH)
**Problem:** No recurring trigger pattern shown
**Solution:** Add to system prompt:
```yaml
trigger:
  - platform: time_pattern
    minutes: "/15"  # Every 15 minutes
```

### 6. Add Color/Blink Pattern Example (HIGH)
**Problem:** No color or blink pattern shown
**Solution:** Add to system prompt:
```yaml
# Blink pattern with color
action:
  - service: light.turn_on
    target:
      area_id: office
    data:
      rgb_color: [255, 0, 0]  # Red (RGB: 0-255 each)
      brightness: 255
  - delay: "00:00:01"  # Blink duration
```

### 7. Enhance Entity Inventory (MEDIUM)
**Problem:** All lights show as "unassigned"
**Solution:**
- Include area_id in entity examples even if "unassigned"
- Group entities by area when area_id is available
- Show office-specific lights if area_id matches

---

## Test Results

Created test file: `services/ha-ai-agent-service/tests/integration/test_office_lights_blink_automation.py`

**Test Coverage:**
- ✅ Context contains office lights
- ✅ Context contains light services
- ✅ Context contains color capabilities
- ✅ System prompt contains state restoration pattern
- ✅ Complete prompt has all required info
- ✅ Automation YAML structure validation

**Run Tests:**
```bash
cd services/ha-ai-agent-service
pytest tests/integration/test_office_lights_blink_automation.py -v
```

---

## Conclusion

The current prompt and context injection have **critical gaps** that prevent the LLM from generating correct automations:

1. **Missing Areas** - Cannot use area targeting
2. **Missing Services** - Doesn't know service parameters
3. **Missing Capabilities** - Doesn't know color formats
4. **Missing Patterns** - No state restoration YAML example
5. **Missing Examples** - No time pattern or color examples

**Priority Actions:**
1. Fix services summary (returns empty)
2. Fix capability patterns (returns empty)
3. Add state restoration pattern to system prompt
4. Add time pattern trigger example
5. Fix areas service or include area_id in entity inventory

These fixes will enable the LLM to generate correct automations for the test case.

