# OpenAI Prompt Template - Area Logic Enhancements

**Date:** November 18, 2025  
**Related:** ASK_AI_AREA_FILTERING_FIX.md  
**Status:** ✅ Implemented

## Overview

Enhanced the OpenAI prompt template in `nl_automation_generator.py` to include comprehensive area filtering logic. This ensures the AI consistently respects area restrictions when generating automations.

## Prompt Template Structure

### 1. Dynamic Area Restriction Notice (Top of Prompt)

This section appears **only when user specifies an area**, making it highly visible:

#### Single Area Example:
```
**IMPORTANT - Area Restriction:**
The user has specified devices in the "Office" area. You MUST use ONLY devices that are located in the Office area. 
The available devices list below has already been filtered to show only Office devices. DO NOT use devices from other areas.
```

#### Multiple Areas Example:
```
**IMPORTANT - Area Restriction:**
The user has specified devices in these areas: Office and Kitchen. You MUST use ONLY devices that are located in these areas.
The available devices list below has already been filtered to show only devices from these areas. DO NOT use devices from other areas.
```

**Placement:** Between the system message and the available devices list  
**Purpose:** Catch AI's attention immediately with prominent warning  
**Format:** Bold header, direct commands, clear consequences

### 2. Area Filtering in Main Instructions

This instruction is **always present** in the numbered instructions list:

```
3. **AREA FILTERING:** If the user specifies a location (e.g., "in the office", "kitchen and bedroom"):
   - Use ONLY entities from that area/those areas
   - The available devices list is already filtered by area if specified
   - DO NOT use entities from other areas
   - Verify entity_id matches the specified area(s)
```

**Placement:** Instruction #3 (high priority)  
**Purpose:** Permanent guideline in the instruction set  
**Format:** Bold header, bulleted sub-instructions with clear examples

### 3. Filtered Device List

When area filter is active, the "Available Devices" list only shows devices from the specified area(s):

```
**Available Devices:**
- Lights (4): Bar, LR Back Left Ceiling, LR Front Right Ceiling, Master Back Left
```

**With area filter (office):**
```
**Available Devices:**
- Lights (2): Office Ceiling, Office Desk Lamp
```

This prevents the AI from even seeing devices from other areas.

## Implementation Details

### Code Location
File: `services/ai-automation-service/src/nl_automation_generator.py`

### Key Methods

#### `_build_prompt()` - Lines 227-441
Constructs the full prompt with area logic:
```python
def _build_prompt(
    self,
    request: NLAutomationRequest,
    automation_context: Dict,
    area_filter: Optional[str] = None
) -> str:
    # ... build device summary ...
    
    # Add area filter notice if applicable
    area_notice = ""
    if area_filter:
        # Handle single vs multiple areas
        areas = [a.replace('_', ' ').title() for a in area_filter.split(',')]
        if len(areas) == 1:
            area_notice = f"""
**IMPORTANT - Area Restriction:**
The user has specified devices in the "{areas[0]}" area...
"""
        else:
            area_list = ', '.join(areas[:-1]) + ' and ' + areas[-1]
            area_notice = f"""
**IMPORTANT - Area Restriction:**
The user has specified devices in these areas: {area_list}...
"""
    
    # Build full prompt
    prompt = f"""You are a Home Assistant automation expert...
{area_notice}
**Available Devices:**
{device_summary}

**Instructions:**
1. Generate a COMPLETE, VALID Home Assistant automation...
2. Use ONLY devices that exist in the available devices list above
3. **AREA FILTERING:** If the user specifies a location...
   - Use ONLY entities from that area/those areas
   - The available devices list is already filtered by area if specified
   - DO NOT use entities from other areas
   - Verify entity_id matches the specified area(s)
...
"""
```

#### `_retry_generation()` - Lines 739-808
Preserves area logic on retry:
```python
async def _retry_generation(
    self,
    request: NLAutomationRequest,
    automation_context: Dict,
    error_message: str,
    area_filter: Optional[str] = None
) -> GeneratedAutomation:
    # Add area notice for retry
    area_notice = ""
    if area_filter:
        areas = [a.replace('_', ' ').title() for a in area_filter.split(',')]
        if len(areas) == 1:
            area_notice = f"\nIMPORTANT: Use ONLY devices from the {areas[0]} area.\n"
        else:
            area_list = ', '.join(areas[:-1]) + ' and ' + areas[-1]
            area_notice = f"\nIMPORTANT: Use ONLY devices from these areas: {area_list}.\n"
    
    retry_prompt = f"""The previous generation attempt failed...
{area_notice}
Original request: "{request.request_text}"
..."""
```

## Why This Approach Works

### 1. Dual Reinforcement
- **Top notice:** Catches attention immediately
- **Instruction #3:** Provides permanent reference

### 2. Pre-Filtered Data
- Available devices list is already filtered by area
- AI can't accidentally use devices it doesn't see

### 3. Multiple Reminders
- Area restriction appears 3 times:
  1. Dynamic notice at top
  2. Instruction #3 in main list
  3. Filtered device list

### 4. Clear Examples
- Shows exact syntax: "in the office", "kitchen and bedroom"
- Explains what to do and what NOT to do
- Uses bold and formatting for emphasis

### 5. Handles Edge Cases
- Single area: "the Office area"
- Multiple areas: "Office and Kitchen"
- Grammatically correct lists: "Office, Kitchen and Bedroom"

## Example Prompts Generated

### Single Area Request
**User Input:** "In the office, flash all the Hue lights for 45 secs"

**Generated Prompt Structure:**
```
You are a Home Assistant automation expert...

**IMPORTANT - Area Restriction:**
The user has specified devices in the "Office" area. You MUST use ONLY devices that are located in the Office area. 
The available devices list below has already been filtered to show only Office devices. DO NOT use devices from other areas.

**Available Devices:**
- Lights (2): Office Ceiling, Office Desk Lamp

**Instructions:**
1. Generate a COMPLETE, VALID Home Assistant automation...
2. Use ONLY devices that exist in the available devices list above
3. **AREA FILTERING:** If the user specifies a location (e.g., "in the office", "kitchen and bedroom"):
   - Use ONLY entities from that area/those areas
   - The available devices list is already filtered by area if specified
   - DO NOT use entities from other areas
   - Verify entity_id matches the specified area(s)
...
```

### Multiple Area Request
**User Input:** "Turn on lights in the office and kitchen at 7 AM"

**Generated Prompt Structure:**
```
You are a Home Assistant automation expert...

**IMPORTANT - Area Restriction:**
The user has specified devices in these areas: Office and Kitchen. You MUST use ONLY devices that are located in these areas.
The available devices list below has already been filtered to show only devices from these areas. DO NOT use devices from other areas.

**Available Devices:**
- Lights (4): Office Ceiling, Office Desk Lamp, Kitchen Main, Kitchen Under Cabinet

**Instructions:**
1. Generate a COMPLETE, VALID Home Assistant automation...
2. Use ONLY devices that exist in the available devices list above
3. **AREA FILTERING:** If the user specifies a location (e.g., "in the office", "kitchen and bedroom"):
   - Use ONLY entities from that area/those areas
   - The available devices list is already filtered by area if specified
   - DO NOT use entities from other areas
   - Verify entity_id matches the specified area(s)
...
```

## Testing Recommendations

### Visual Inspection
1. Generate automation with area specified
2. Check logs for the generated prompt
3. Verify area restriction notice appears
4. Confirm device list is filtered

### Functional Testing
1. **Test single area:** "In the office, turn on lights"
   - Should only use office entities
2. **Test multiple areas:** "In the kitchen and bedroom, turn on lights"
   - Should only use kitchen + bedroom entities
3. **Test no area:** "Turn on all lights"
   - Should work normally (no filtering)

### Error Cases
1. **Typo in area:** "In the offce, turn on lights"
   - Should not detect area, use all entities
2. **Unknown area:** "In the spaceship, turn on lights"
   - Should not detect area, use all entities

## Benefits

✅ **Clear Communication:** AI receives explicit, repeated instructions  
✅ **Data Filtering:** Pre-filtered device list prevents mistakes  
✅ **Prominent Warnings:** Bold notice at top catches attention  
✅ **Consistent Behavior:** Works for single or multiple areas  
✅ **Backward Compatible:** No area = no restriction (existing behavior)  

## Future Enhancements

1. **Dynamic area list:** Learn areas from Home Assistant config
2. **Area validation:** Warn user if area doesn't exist
3. **Fuzzy matching:** Handle typos in area names
4. **Area synonyms:** Support "LR" → "living_room", etc.
5. **Confidence scoring:** Lower confidence if area unclear

## Related Documentation

- `ASK_AI_AREA_FILTERING_FIX.md` - Complete fix documentation
- `nl_automation_generator.py` - Implementation code
- `test_area_filtering.py` - Test suite

