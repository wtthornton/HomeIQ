# Quick Test Refactor Plan - Option 1 Implementation

**Date:** January 2025  
**Goal:** Change Test button to execute commands directly via HA Conversation API  
**Motivation:** Faster tests, no temporary automations left in HA

---

## Current Flow

```
Query: "Flash the office lights every 30 seconds only after 5pm"
  ↓
Suggestions: ["Flash office lights every 30 seconds after 5pm", ...]
  ↓
Test Button:
  1. Generate YAML from suggestion
  2. Create temp automation ([TEST] prefix)
  3. Trigger automation
  4. Disable automation
  5. Return result (~5 seconds, leaves artifact)
  ↓
Approve Button:
  1. Generate YAML
  2. Create permanent automation
  3. Return result
```

---

## New Flow (Option 1)

```
Query: "Flash the office lights every 30 seconds only after 5pm"
  ↓
Suggestions: ["Flash office lights every 30 seconds after 5pm", ...]
  ↓
Test Button (Quick Test):
  1. Simplify query: "Flash the office lights" (remove conditions)
  2. Execute via HA Conversation API
  3. Return execution result (~1 second, no artifacts)
  ↓
Approve Button (Generate & Create):
  1. Generate full YAML (with all conditions)
  2. Create permanent automation
  3. Return result
```

---

## Implementation Plan

### 1. Create Query Simplification Function

**Location:** `services/ai-automation-service/src/services/`

**Function:** `simplify_query_for_test()`

```python
def simplify_query_for_test(suggestion: Dict[str, Any]) -> str:
    """
    Simplify suggestion to test core behavior without conditions.
    
    Examples:
    - "Flash office lights every 30 seconds only after 5pm"
      → "Flash the office lights"
    
    - "Turn on bedroom lights when door opens after sunset"
      → "Turn on the bedroom lights when door opens"
    
    - "Dim kitchen lights to 50% brightness at 8pm only on weekdays"
      → "Dim the kitchen lights"
    
    Algorithm:
    1. Extract action from suggestion
    2. Remove time-based conditions ("after 5pm", "at 8pm", "between X and Y")
    3. Remove day-based conditions ("only on weekdays", "on weekends")
    4. Keep core trigger-action pattern
    5. Simplify interval/pattern ("every 30 seconds" → removed for quick test)
    """
```

### 2. Modify Test Endpoint

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes:**
- Remove YAML generation from test endpoint
- Add query simplification
- Call HA Conversation API
- Return execution result

### 3. Keep Approve Endpoint As-Is

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes:** None - already generates YAML and creates automation

---

## Code Structure

### New Function: simplify_query_for_test()

```python
# services/ai-automation-service/src/services/query_simplifier.py

import re
from typing import Dict, Any

def simplify_query_for_test(suggestion: Dict[str, Any]) -> str:
    """
    Simplify suggestion description for quick testing.
    
    Removes conditions and time constraints to test core behavior.
    """
    description = suggestion.get('description', '')
    trigger = suggestion.get('trigger_summary', '')
    action = suggestion.get('action_summary', '')
    
    # Strategy 1: Extract just the action
    # "Flash the office lights every 30 seconds only after 5pm"
    # → "Flash the office lights"
    
    # Remove time-based phrases
    time_phrases = [
        r'every\s+\d+\s+seconds?',
        r'every\s+\d+\s+minutes?',
        r'only\s+after\s+\d+[ap]m',
        r'after\s+\d+[ap]m',
        r'before\s+\d+[ap]m',
        r'between\s+\d+[ap]m\s+and\s+\d+[ap]m',
        r'at\s+\d+[ap]m',
        r'during\s+.*?hours?',
    ]
    
    simplified = description
    for phrase in time_phrases:
        simplified = re.sub(phrase, '', simplified, flags=re.IGNORECASE)
    
    # Remove day-based conditions
    day_phrases = [
        r'only\s+on\s+weekdays?',
        r'only\s+on\s+weekends?',
        r'every\s+day',
    ]
    
    for phrase in day_phrases:
        simplified = re.sub(phrase, '', simplified, flags=re.IGNORECASE)
    
    # Clean up extra spaces
    simplified = re.sub(r'\s+', ' ', simplified).strip()
    
    return simplified
```

### Modified Test Endpoint

```python
@router.post("/query/{query_id}/suggestions/{suggestion_id}/test")
async def test_suggestion_from_query(...):
    """
    Test a suggestion by executing the command directly via HA API.
    
    NEW: Quick test by executing command, not creating automation.
    """
    
    # Get suggestion
    suggestion = get_suggestion_from_db(...)
    
    # Simplify for testing
    simplified_command = simplify_query_for_test(suggestion)
    
    # Execute via HA Conversation API
    result = await ha_client.conversation_process(simplified_command)
    
    # Parse response
    data = result.get('response', {}).get('data', {})
    success = data.get('success', [])
    failed = data.get('failed', [])
    
    return {
        "suggestion_id": suggestion_id,
        "executed": len(success) > 0,
        "entities": [e.get('id') for e in success],
        "failed_entities": [e.get('id') for e in failed],
        "speech": result.get('response', {}).get('speech', {}).get('plain', {}).get('speech'),
        "message": f"✅ Test executed successfully on {len(success)} entities" if len(success) > 0 else "❌ Test failed",
        "simplified_command": simplified_command
    }
```

---

## File Changes

### Files to Create:
1. `services/ai-automation-service/src/services/query_simplifier.py` (NEW)

### Files to Modify:
1. `services/ai-automation-service/src/api/ask_ai_router.py`
   - Modify test endpoint (lines 637-770)
   - Keep approve endpoint (no changes)

---

## Testing Plan

### Manual Tests:
1. Test simple query: "Turn on the office lights"
2. Test with time: "Flash lights every 30 seconds only after 5pm"
3. Test complex: "Dim kitchen lights to 50% when door opens after sunset"
4. Test failed execution: Invalid entity

### Expected Results:
- Test should execute in <2 seconds
- No temporary automations created in HA
- Execution result shows which entities were affected
- Failed tests show which entities failed

---

## Benefits

✅ **Faster**: Execute in ~1 second vs ~5 seconds  
✅ **No Artifacts**: No temporary automations left in HA  
✅ **Direct Feedback**: See exactly what happened  
✅ **Simpler**: No YAML generation for testing  
✅ **Better UX**: Quick visual confirmation

## Trade-offs

⚠️ **No YAML Preview**: Can't see what automation will look like  
⚠️ **Limited to Simple Commands**: Complex multi-step might not work  
⚠️ **Execution Only**: Can't test conditions (time-based, etc.)

---

## Next Steps After This Implementation

Once this is complete, we will:
1. Test the quick test functionality
2. Move to next phase: YAML generation optimization
3. Consider hybrid approach for complex automations
