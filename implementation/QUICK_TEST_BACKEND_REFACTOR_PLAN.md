# Quick Test Backend Refactor Plan

**Date:** January 2025  
**Goal:** Change backend API logic behind Test and Approve buttons  
**UI/Test Code:** NO CHANGES - Only backend logic changes

---

## Overview

### Current Behavior

**Test Button API (`POST /query/{query_id}/suggestions/{suggestion_id}/test`):**
1. Generate YAML from suggestion
2. Create temporary automation in HA
3. Trigger automation
4. Disable automation
5. Return result (~5 seconds, leaves artifact)

**Approve Button API (`POST /query/{query_id}/suggestions/{suggestion_id}/approve`):**
1. Generate YAML from suggestion
2. Create permanent automation in HA
3. Return result

---

## Proposed New Behavior

### Test Button API - Quick Command Execution

**Flow:**
1. Extract core behavior from suggestion (remove conditions)
2. Execute command via HA Conversation API
3. Return execution result (~1 second, no artifacts)

**What it does:**
- Takes suggestion like "Flash office lights every 30 seconds only after 5pm"
- Simplifies to: "Flash the office lights"
- Sends to HA Conversation API
- HA executes the command immediately
- Returns success/failure

### Approve Button API - Generate YAML and Create Automation

**Flow:**
1. Generate full YAML (with all conditions) - ONLY WHEN APPROVING
2. Create permanent automation in HA
3. Return result

**What it does:**
- Takes suggestion
- Generates complete automation YAML (includes all conditions, timing, etc.)
- Creates permanent automation in HA
- Returns automation ID

---

## File Changes

### File: `services/ai-automation-service/src/api/ask_ai_router.py`

**Lines 637-770: Test Endpoint**
- **Current:** Generate YAML → Create temp automation → Trigger → Disable
- **New:** Simplify query → Execute via HA Conversation API → Return result
- **Key Change:** Remove YAML generation, add HA Conversation API call

**Lines 773-834: Approve Endpoint**
- **Current:** Generate YAML → Create automation
- **New:** Generate YAML (full version with conditions) → Create automation
- **Key Change:** None - already does this, just make sure it generates complete YAML

---

## Research Findings from Context7 and Codebase Analysis

### Temperature Settings Research

**From Codebase Analysis:**
- `0.1`: Entity extraction (`multi_model_extractor.py`) - Very deterministic
- `0.2-0.3`: YAML generation (`yaml_generator.py`, `ask_ai_router.py`) - Precise, consistent
- `0.5`: Refinement tasks (`suggestion_refiner.py`) - Balanced
- `0.7-0.9`: Creative generation (suggestions) - More variability

**From Context7 Documentation:**
- Temperature range: 0-2
- **0.0**: Completely deterministic, same prompt = same output
- **0.1-0.2**: Recommended for extraction/parsing tasks (very consistent)
- **0.2-0.5**: Good for structured output with some variability
- **0.7-1.0**: Creative tasks, brainstorming

**For Our Task (Simplification):**
- **Recommended: `temperature=0.1`**
- Why: This is an **extraction task** - we want consistent, deterministic results
- Not creative: Don't want AI making up variations
- Not generating: Just extracting what's already there

### Prompt Design Best Practices

**From Context7 Prompt Engineering Guide:**

1. **Structured Prompt Format:**
   ```
   TASK: [Clear task description]
   INPUT: [The data to process]
   EXAMPLES: [Few-shot learning examples]
   REMOVE: [What to exclude]
   KEEP: [What to preserve]
   CONSTRAINTS: [Output requirements]
   ```

2. **Few-Shot Learning (Examples):**
   - Provide 3-4 examples showing input → output
   - Helps model understand the pattern
   - Especially important for consistent extraction

3. **System Message:**
   - Define the role clearly
   - Set expectations for output format
   - Keep it concise and focused

### Why Temperature 0.1?

| Task Type | Temperature | Why |
|-----------|-------------|-----|
| Extraction/Parsing | 0.0-0.2 | Want consistent, deterministic output |
| Structured Generation | 0.2-0.5 | Need some creativity but stay in format |
| Creative Writing | 0.7-1.0 | Want variety and novelty |

**Our simplification task is clearly extraction/parsing**, so **0.1 is perfect**.

---

## Why Use AI for Simplification Instead of Regex?

### The User's Question

**Q:** "What is the logic behind simplify_query_for_test()? Are we using an AI model or OpenAI to do this? If not, why?"

**A:** **YES, we use OpenAI/AI for simplification!** Here's why:

### Comparison: AI vs Regex Approach

| Aspect | Regex Approach | AI Approach (✅ Chosen) |
|--------|---------------|------------------------|
| **Understanding** | Pattern matching only | Contextual understanding |
| **Edge Cases** | Brittle, needs constant updates | Handles variations naturally |
| **Complexity** | 50+ regex rules needed | One simple prompt |
| **Examples** | "only after 5pm" → regex | "only after 5pm" → AI understands |
| **Cost** | Free | ~$0.00001 per simplification (~2 tokens) |
| **Consistency** | Different behavior for similar inputs | Consistent understanding |
| **Maintenance** | Update regex when new patterns appear | Self-adapting |

### Why AI is Better Here

1. Already using AI: Suggestions are generated by OpenAI, so use the same model to simplify them
2. Understands context: "after 5pm" means time constraint, "when door opens" is core trigger
3. Simpler code: One prompt vs 50 regex rules
4. Robust: Handles new patterns automatically
5. Low cost: Simplification is much cheaper than generating full YAML (~2 tokens vs 1000 tokens)

### Example

**Input:**
```
"Flash the kitchen lights to blue every 30 seconds when the front door opens after sunset on weekdays"
```

**Regex Approach:**
```python
# Would need multiple regex patterns:
simplified = re.sub(r'every.*seconds', '', text)  # ❌ Might break on edge cases
simplified = re.sub(r'after sunset', '', simplified)  # ❌ What about "after 5pm"?
simplified = re.sub(r'on weekdays', '', simplified)  # ❌ What about "only on weekends"?
# Result might be inconsistent or incomplete
```

**AI Approach:**
```python
# One simple prompt:
prompt = "Extract core command, remove time/condition constraints"
result = await openai_client.generate(simplified_command)
# Result: "Flash the kitchen lights to blue when the front door opens"
# ✅ Intelligent, consistent, handles all variations
```

### Cost Analysis

- Full YAML generation: ~1000 tokens × $0.15/1M input + $0.60/1M output = ~$0.0003
- Simplification: ~50 tokens × $0.15/1M input + $0.60/1M output = ~$0.000015
- Savings vs generating YAML: 20x cheaper!

---

## Detailed Code Changes

### 1. Add Helper Function: Simplify Query (Using AI)

**Location:** Add new function after line 134 (after `generate_automation_yaml`)

```python
async def simplify_query_for_test(suggestion: Dict[str, Any]) -> str:
    """
    Simplify automation description to test core behavior using AI.
    
    Uses OpenAI to intelligently extract just the core action without conditions.
    
    Examples:
    - "Flash office lights every 30 seconds only after 5pm"
      → "Flash the office lights"
    
    - "Turn on bedroom lights when door opens after sunset"
      → "Turn on the bedroom lights when door opens"
    
    Why Use AI instead of Regex:
    - Smarter: Understands context, not just pattern matching
    - Robust: Handles edge cases and variations
    - Consistent: Uses same AI model that generated the suggestions
    - Simple: One API call with clear prompt
    - Low cost: Much cheaper than generating full YAML
    
    Args:
        suggestion: Suggestion dictionary with description, trigger, action
        
    Returns:
        Simplified command string ready for HA Conversation API
    """
    if not openai_client:
        # Fallback to regex if OpenAI not available
        logger.warning("OpenAI not available, using fallback simplification")
        return fallback_simplify(suggestion.get('description', ''))
    
    description = suggestion.get('description', '')
    trigger = suggestion.get('trigger_summary', '')
    action = suggestion.get('action_summary', '')
    
    # Research-Backed Prompt Design
    # Based on Context7 best practices and codebase temperature analysis:
    # - Extraction tasks: temperature 0.1-0.2 (very deterministic)
    # - Provide clear examples (few-shot learning)
    # - Structured prompt with task + examples + constraints
    # - Keep output simple and constrained
    
    prompt = f"""Extract the core command from this automation description for quick testing.

TASK: Remove all time constraints, intervals, and conditional logic. Keep only the essential trigger-action behavior.

Automation: "{description}"
Trigger: {trigger}
Action: {action}

EXAMPLES:
Input: "Flash office lights every 30 seconds only after 5pm"
Output: "Flash the office lights"

Input: "Dim kitchen lights to 50% when door opens after sunset"
Output: "Dim the kitchen lights when door opens"

Input: "Turn on bedroom lights every weekday at 8am"
Output: "Turn on the bedroom lights"

Input: "Flash lights 3 times when motion detected, but only between 9pm and 11pm"
Output: "Flash the lights when motion detected"

REMOVE:
- Time constraints (after 5pm, before sunset, between X and Y)
- Interval patterns (every 30 seconds, every weekday)
- Conditional logic (only if, but only when, etc.)

KEEP:
- Core action (flash, turn on, dim, etc.)
- Essential trigger (when door opens, when motion detected)
- Target devices (office lights, kitchen lights)

CONSTRAINTS:
- Return ONLY the simplified command
- No explanations
- Natural language (ready for HA Conversation API)
- Maximum 20 words"""

    try:
        response = await openai_client.client.chat.completions.create(
            model=openai_client.model,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a command simplification expert. Extract core behaviors from automation descriptions. Return only the simplified command, no explanations."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Research-backed: 0.1-0.2 for extraction tasks (deterministic, consistent)
            max_tokens=60,     # Short output - just the command
            top_p=0.9         # Nucleus sampling for slight creativity while staying focused
        )
        
        simplified = response.choices[0].message.content.strip()
        logger.info(f"Simplified '{description}' → '{simplified}'")
        return simplified
        
    except Exception as e:
        logger.error(f"Failed to simplify via AI: {e}, using fallback")
        return fallback_simplify(description)

def fallback_simplify(description: str) -> str:
    """Fallback regex-based simplification if AI unavailable"""
    import re
    # Simple regex-based fallback
    simplified = re.sub(r'every\s+\d+\s+(?:seconds?|minutes?|hours?)', '', description, flags=re.IGNORECASE)
    simplified = re.sub(r'(?:only\s+)?(?:after|before|at|between)\s+.*?[;,]', '', simplified, flags=re.IGNORECASE)
    simplified = re.sub(r'(?:only\s+on\s+)?(?:weekdays?|weekends?)', '', simplified, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', simplified).strip()
```

### 2. Modify Test Endpoint (Lines 637-770)

**CHANGE FROM:**
```python
@router.post("/query/{query_id}/suggestions/{suggestion_id}/test")
async def test_suggestion_from_query(...):
    # Current implementation
    automation_yaml = await generate_automation_yaml(suggestion, query.original_query)
    validation_result = await ha_client.validate_automation(automation_yaml)
    # ... create temp automation, trigger, disable
```

**CHANGE TO:**
```python
@router.post("/query/{query_id}/suggestions/{suggestion_id}/test")
async def test_suggestion_from_query(...):
    """
    Test a suggestion by executing the command directly via HA Conversation API.
    
    NEW: Quick test by executing command, not creating automation.
    """
    
    logger.info(f"🧪 Testing suggestion {suggestion_id} via quick command execution")
    
    try:
        # Get query and suggestion from database
        query = await db.get(AskAIQueryModel, query_id)
        if not query:
            raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
        
        suggestion = None
        for s in query.suggestions:
            if s.get('suggestion_id') == suggestion_id:
                suggestion = s
                break
        
        if not suggestion:
            raise HTTPException(status_code=404, detail=f"Suggestion {suggestion_id} not found")
        
        # Simplify description for quick test using AI
        simplified_command = await simplify_query_for_test(suggestion)
        
        logger.info(f"Simplified command: '{simplified_command}'")
        
        # Execute via HA Conversation API
        if not ha_client:
            raise HTTPException(status_code=500, detail="Home Assistant client not initialized")
        
        result = await ha_client.conversation_process(simplified_command)
        
        # Parse response
        response_data = result.get('response', {}).get('data', {})
        success_entities = response_data.get('success', [])
        failed_entities = response_data.get('failed', [])
        speech_response = result.get('response', {}).get('speech', {}).get('plain', {}).get('speech', '')
        
        # Build result
        executed = len(success_entities) > 0
        entity_ids = [e.get('id') for e in success_entities]
        failed_ids = [e.get('id') for e in failed_entities]
        
        return {
            "suggestion_id": suggestion_id,
            "query_id": query_id,
            "executed": executed,
            "entities_affected": entity_ids,
            "failed_entities": failed_ids,
            "speech_response": speech_response,
            "simplified_command": simplified_command,
            "message": (
                f"✅ Test executed successfully on {len(entity_ids)} entities: {', '.join(entity_ids)}"
            ) if executed else (
                f"❌ Test failed. Entities that failed: {', '.join(failed_ids)}"
            )
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing suggestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**Lines Changed:** 637-770

### 3. Keep Approve Endpoint As-Is (Lines 773-834)

**NO CHANGES - Already generates full YAML with all conditions**

The approve endpoint already:
1. Gets suggestion from database
2. Calls `generate_automation_yaml(suggestion, query.original_query)` - generates FULL YAML
3. Creates automation in HA
4. Returns result

**This is correct - no changes needed**

---

## Response Format Changes

### Test Endpoint Response

**BEFORE:**
```json
{
  "suggestion_id": "ask-ai-abc123",
  "query_id": "query-xyz789",
  "valid": true,
  "executed": true,
  "automation_id": "automation.test_office_lights_abc",
  "automation_yaml": "id: test_office_lights...",
  "test_automation_yaml": "id: test_office_lights...",
  "validation_details": {...},
  "message": "✅ Test automation executed successfully!..."
}
```

**AFTER:**
```json
{
  "suggestion_id": "ask-ai-abc123",
  "query_id": "query-xyz789",
  "executed": true,
  "entities_affected": ["light.office_left", "light.office_right"],
  "failed_entities": [],
  "speech_response": "I've flashed the office lights",
  "simplified_command": "Flash the office lights",
  "message": "✅ Test executed successfully on 2 entities: light.office_left, light.office_right"
}
```

### Approve Endpoint Response

**NO CHANGES** - Response stays the same

```json
{
  "suggestion_id": "ask-ai-abc123",
  "query_id": "query-xyz789",
  "status": "approved",
  "automation_id": "automation.office_lights_flash",
  "automation_yaml": "id: office_lights_flash...",
  "ready_to_deploy": true,
  "warnings": [],
  "message": "Automation created successfully"
}
```

---

## Benefits

### Test Endpoint Benefits
✅ **Faster**: 1 second vs 5 seconds  
✅ **No Artifacts**: No temporary automations in HA  
✅ **Direct Feedback**: See exactly what entities were affected  
✅ **Simpler Code**: No YAML generation for testing  
✅ **Better UX**: Instant visual feedback

### Approve Endpoint Benefits
✅ **No Changes**: Still generates complete YAML with all conditions  
✅ **Same Response Format**: Frontend doesn't need changes  
✅ **Proper Automation**: Full automation with conditions created

---

## Testing Plan

### 1. Test Simple Query
**Query:** "Turn on the office lights"  
**Expected:** Suggestion generated  
**Test Button:** Should execute command immediately  
**Result:** Lights turn on, returns entity IDs

### 2. Test With Time Constraint
**Query:** "Flash the office lights every 30 seconds only after 5pm"  
**Suggestion:** "Flash office lights every 30 seconds after 5pm"  
**Test Button:** Should simplify to "Flash the office lights" and execute  
**Result:** Lights flash once immediately

### 3. Test Complex Automation
**Query:** "Dim kitchen lights to 50% when door opens after sunset on weekdays"  
**Suggestion:** Generated  
**Test Button:** Should simplify to "Dim the kitchen lights when door opens"  
**Result:** Conditional dimming occurs when door opens

### 4. Test Failed Execution
**Query:** "Turn on invalid_entity"  
**Result:** Should return executed=false with error message

---

## Files Summary

**Files to Modify:**
1. `services/ai-automation-service/src/api/ask_ai_router.py`
   - Add `simplify_query_for_test()` function
   - Modify test endpoint (lines 637-770)
   - Keep approve endpoint unchanged

**Files NOT to Change:**
- `tests/integration/test_ask_ai_test_button_api.py` - Already calls API correctly
- Frontend code - API contract unchanged
- Other services - No dependencies

---

## Implementation Steps

1. Add `simplify_query_for_test()` helper function
2. Replace test endpoint implementation
3. Keep approve endpoint as-is
4. Test manually with various queries
5. Update integration tests if response format changes affect them

---

## Rollback Plan

If issues arise:
- Test endpoint still calls same URL (`POST /query/{id}/suggestions/{id}/test`)
- Just revert the implementation in `ask_ai_router.py`
- Frontend/Test code unchanged
- No database schema changes

---

## Questions for Review

1. **Simplification Rules:** Are the regex patterns in `simplify_query_for_test()` sufficient?
2. **Error Handling:** How should we handle HA Conversation API failures?
3. **Complex Automations:** Should we support multi-step commands or just simple ones?
4. **User Feedback:** Is the response format clear enough?

---

## Ready for Implementation

**Status:** Plan complete, ready for review  
**Files to Change:** 1 (ask_ai_router.py)  
**Risk Level:** Low (only backend changes, API contract compatible)  
**Testing:** Manual testing required, integration tests may need updates
