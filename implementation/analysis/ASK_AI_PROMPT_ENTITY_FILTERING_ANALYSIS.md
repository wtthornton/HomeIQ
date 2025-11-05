# Ask AI Prompt Entity Filtering Analysis

**Date:** January 6, 2025  
**Issue:** User Prompt includes ALL entities (20+) but only 3 are selected  
**Query ID:** #7674  
**Impact:** High token usage, increased costs, unnecessary context

## Problem Analysis

### Current Flow

1. **Entity Resolution (Line 2477-2497):**
   - Fetches ALL entities matching query context (location + domain)
   - Example: Query "office lights" → Fetches ALL 20+ office lights
   - Includes: Office Front Left, Office Back Left, Office Back Right, Office Strip, etc.

2. **Entity Enrichment (Line 2594-2601):**
   - Enriches ALL resolved entities (20+ entities)
   - Fetches capabilities, attributes, metadata for each

3. **Entity Context JSON Building (Line 2614-2618):**
   - Builds `entity_context_json` from ALL enriched entities
   - Includes complete data for all 20+ lights

4. **User Prompt Generation (Line 2633-2638):**
   - Sends FULL `entity_context_json` (all 20+ entities) to OpenAI
   - This is what appears in the "User Prompt" debug panel

5. **Suggestion Generation & Mapping (Line 2567-2662):**
   - AI generates suggestions
   - We map devices to entities → Only 3 entities selected
   - But prompt already had all 20+ entities

### Root Cause

The `entity_context_json` is built **BEFORE** we know which entities will actually be used. It includes all entities that match the query context, not just the ones selected in the final suggestion.

### Impact

1. **Token Usage:** 
   - User prompt includes 20+ entities with full metadata
   - Each entity has: entity_id, friendly_name, capabilities, attributes, etc.
   - Estimated: 2000-5000+ extra tokens per query

2. **Cost:**
   - OpenAI charges per token
   - Extra tokens = extra cost
   - Multiplied by number of queries = significant cost increase

3. **AI Confusion:**
   - Too many options might confuse the AI
   - AI might select wrong entities or get overwhelmed

4. **Debug Panel:**
   - Shows full context (all 20+ entities) in User Prompt
   - But only 3 are actually used
   - Makes debugging harder

## Solution Options

### Option A: Filter Entity Context After Mapping (Recommended)

**Approach:**
- Build full entity_context_json for initial prompt (needed for AI to know options)
- After suggestions are generated and mapped, build FILTERED entity_context_json
- Store filtered version in debug data for each suggestion
- Show filtered version in debug panel

**Pros:**
- ✅ AI still has full context to make good suggestions
- ✅ Debug panel shows only entities actually used
- ✅ Reduces confusion in debug panel
- ✅ Minimal code changes

**Cons:**
- ⚠️ Initial prompt still has all entities (but this is necessary)

**Implementation:**
1. After mapping devices to entities (line 2659), filter enriched_data to only validated_entities
2. Rebuild entity_context_json with filtered entities
3. Store in suggestion debug data

### Option B: Smart Entity Filtering Before Prompt

**Approach:**
- Limit entities in initial prompt based on query specificity
- Use entity extraction to determine which entities are relevant
- Only include entities that match extracted device names

**Pros:**
- ✅ Reduces initial prompt size
- ✅ Lower token usage from start

**Cons:**
- ❌ Might miss entities AI should consider
- ❌ Complex logic to determine relevance
- ❌ Might reduce suggestion quality

### Option C: Two-Stage Entity Context

**Approach:**
- Initial prompt: Include summary of available entities (count, types)
- Detailed context: Only include entities that match extracted names
- After mapping: Rebuild full context for selected entities only

**Pros:**
- ✅ Balanced approach
- ✅ Reduces tokens while maintaining context

**Cons:**
- ⚠️ More complex implementation
- ⚠️ Summary might not be enough for AI

## Recommended Solution: Option A

**Why:**
- Preserves AI's ability to make good suggestions (needs full context)
- Fixes debug panel to show only relevant entities
- Simple to implement
- Addresses the user's concern (debug panel shows too many entities)

**Implementation Plan:**

1. **After device mapping (line 2659):**
   - Filter `enriched_data` to only include entities in `validated_entities`
   - Rebuild `entity_context_json` with filtered entities
   - Store in suggestion debug data

2. **Update debug data storage:**
   - Store both:
     - `full_entity_context_json`: Original (all entities) - for reference
     - `filtered_entity_context_json`: Only entities used in suggestion

3. **Update debug panel:**
   - Show filtered version in User Prompt tab
   - Optionally show "X more entities were available" note

## Code Changes Required

### 1. Filter Entity Context After Mapping

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Location:** After line 2659 (after device mapping)

```python
# After mapping devices to entities, filter entity context
if validated_entities and enriched_data:
    # Filter enriched_data to only validated entities
    filtered_enriched_data = {
        entity_id: enriched_data[entity_id]
        for entity_id in validated_entities.values()
        if entity_id in enriched_data
    }
    
    # Rebuild entity context JSON with filtered entities
    filtered_enriched_entities = []
    for entity_id in validated_entities.values():
        if entity_id in enriched_data:
            enriched = enriched_data[entity_id]
            filtered_enriched_entities.append({
                'entity_id': entity_id,
                'friendly_name': enriched.get('friendly_name', entity_id),
                'name': enriched.get('friendly_name', entity_id.split('.')[-1] if '.' in entity_id else entity_id)
            })
    
    context_builder = EntityContextBuilder()
    filtered_entity_context_json = await context_builder.build_entity_context_json(
        entities=filtered_enriched_entities,
        enriched_data=filtered_enriched_data
    )
else:
    filtered_entity_context_json = None
```

### 2. Store Filtered Context in Debug Data

**Location:** Line 2659 (debug data creation)

```python
base_suggestion['debug'] = {
    'device_selection': device_debug,
    'system_prompt': openai_debug_data.get('system_prompt', ''),
    'user_prompt': openai_debug_data.get('user_prompt', ''),  # Full prompt (original)
    'filtered_user_prompt': filtered_user_prompt,  # NEW: Filtered prompt
    'openai_response': openai_debug_data.get('openai_response'),
    'token_usage': openai_debug_data.get('token_usage'),
    'entity_context_stats': {  # NEW: Context statistics
        'total_entities_available': len(enriched_data) if enriched_data else 0,
        'entities_used_in_suggestion': len(validated_entities) if validated_entities else 0,
        'filtered_entity_context_json': filtered_entity_context_json
    }
}
```

### 3. Update Debug Panel to Show Filtered Version

**File:** `services/ai-automation-ui/src/components/ask-ai/DebugPanel.tsx`

**Changes:**
- Show filtered_user_prompt in User Prompt tab (if available)
- Show entity_context_stats to indicate filtering
- Option to toggle between full and filtered view

## Testing Plan

1. **Test Query:** "Turn on office lights when I enter"
2. **Expected:**
   - Initial prompt includes all office lights (for AI selection)
   - Debug panel shows filtered version (only 3 selected lights)
   - Entity context stats show: "3 of 20 entities used"
3. **Verify:**
   - Token usage reduced in debug panel
   - Only relevant entities shown
   - Suggestions still work correctly

## Success Metrics

- ✅ Debug panel shows only entities used in suggestion
- ✅ Entity context stats visible
- ✅ Token usage reduced in displayed prompt
- ✅ Suggestions still generate correctly
- ✅ No regression in suggestion quality

