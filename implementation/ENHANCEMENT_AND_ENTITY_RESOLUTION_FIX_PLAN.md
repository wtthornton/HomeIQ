# Enhancement & Entity Resolution Fix Plan

**Date:** December 4, 2025  
**Status:** Analysis Complete - Ready for Implementation

---

## Issues Identified

### Issue 1: Enhancement Suggestions Timeout ❌
**Problem:** Enhancement suggestions get stuck on "Generating enhancements..." and never return.

**Root Cause (from logs):**
```
openai.APITimeoutError: Request timed out.
File "/app/src/services/enhancement_service.py", line 544, in _generate_fallback_fun
```

**Analysis:**
- The enhancement service makes 5 OpenAI API calls (3 LLM + 1 pattern + 1 synergy)
- Each call can take 10-30 seconds
- Total time can exceed 60+ seconds
- The fun enhancement (fallback) is timing out
- Error is caught but response might be incomplete
- Frontend shows loading state indefinitely

**Impact:**
- User sees "Generating enhancements..." forever
- No enhancements are returned
- Poor user experience

---

### Issue 2: Wrong Entity Resolution ❌
**Problem:** User says "office's top-left light" but system matches to "Office WLED" or kitchen lights.

**Root Cause:**
1. **Entity Inventory Service** only shows 3 examples per domain (line 166: `domain_samples[domain][:3]`)
2. **No area filtering** - Context shows random 3 lights, not filtered by "office" area
3. **No positional keyword matching** - System doesn't search for "top", "left", "top-left" in entity names
4. **Context limitation** - AI only sees 3 light examples total, not all office lights

**Example from user:**
- Request: "Flash all the lights in the office in party colors"
- Matched: Kitchen Strip lights (wrong area!)
- Expected: Office lights only

**Analysis:**
- `EntityInventoryService.get_summary()` fetches all entities but only shows 3 samples
- Samples are not filtered by area when user mentions specific area
- System prompt says to search by `area_id="office"` but context doesn't provide all office lights
- AI has to guess from limited context

**Impact:**
- Wrong entities selected
- Automations affect wrong devices
- User frustration

---

## Fix Plan

### Phase 1: Fix Enhancement Timeout (Priority: HIGH)

#### 1.1 Add Timeout Handling
- **File:** `services/ha-ai-agent-service/src/services/enhancement_service.py`
- **Changes:**
  - Add timeout parameter to OpenAI calls (reduce from default 30s to 15s)
  - Add timeout handling with graceful fallback
  - Return partial results if some enhancements succeed
  - Add progress tracking

#### 1.2 Optimize API Calls
- **Changes:**
  - Run LLM enhancements in parallel (3 calls at once)
  - Add caching for same automation YAML
  - Reduce prompt length for faster responses
  - Use shorter temperature for faster generation

#### 1.3 Improve Error Handling
- **Changes:**
  - Catch timeout errors specifically
  - Return partial enhancements (e.g., if 3/5 succeed, return those)
  - Add retry logic with exponential backoff
  - Log timeout errors clearly

#### 1.4 Frontend Timeout Handling
- **File:** `services/ai-automation-ui/src/components/ha-agent/EnhancementButton.tsx`
- **Changes:**
  - Add 60-second timeout on frontend
  - Show error message if timeout
  - Allow retry button
  - Show partial results if available

---

### Phase 2: Fix Entity Resolution (Priority: CRITICAL)

#### 2.1 Enhance Entity Inventory Context
- **File:** `services/ha-ai-agent-service/src/services/entity_inventory_service.py`
- **Changes:**
  - **Show ALL entities per domain/area**, not just 3 samples
  - **Filter by area** when area is mentioned in user query (requires query analysis)
  - **Include positional keywords** in entity names (top, left, right, back, front, etc.)
  - **Prioritize area-specific entities** in context

#### 2.2 Improve System Prompt Entity Matching
- **File:** `services/ha-ai-agent-service/src/prompts/system_prompt.py`
- **Changes:**
  - Add explicit instructions for positional matching
  - Add examples of correct entity resolution
  - Emphasize area filtering FIRST, then keyword matching
  - Add validation step: "Verify entity matches user's description"

#### 2.3 Add Entity Resolution Helper
- **New File:** `services/ha-ai-agent-service/src/services/entity_resolution_helper.py`
- **Purpose:**
  - Extract area from user query ("office" → area_id="office")
  - Extract positional keywords ("top-left" → ["top", "left"])
  - Filter entities by area first
  - Then match by keywords
  - Return ranked list of matches

#### 2.4 Update Context Builder
- **File:** `services/ha-ai-agent-service/src/services/context_builder.py`
- **Changes:**
  - When user query mentions area, filter entity inventory by that area
  - Include all matching entities, not just 3 samples
  - Add entity resolution helper to context

---

## Implementation Details

### Enhancement Timeout Fix

```python
# services/ha-ai-agent-service/src/services/enhancement_service.py

# Add timeout to OpenAI calls
response = await asyncio.wait_for(
    self.openai_client.chat.completions.create(...),
    timeout=15.0  # 15 second timeout per call
)

# Run LLM enhancements in parallel
async def _generate_llm_enhancements(...):
    tasks = [
        self._generate_small_enhancement(...),
        self._generate_medium_enhancement(...),
        self._generate_large_enhancement(...)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Handle partial failures
```

### Entity Resolution Fix

```python
# services/ha-ai-agent-service/src/services/entity_inventory_service.py

async def get_summary(self, user_query: str | None = None) -> str:
    # Extract area from query if provided
    area_id = self._extract_area_from_query(user_query) if user_query else None
    
    # Filter entities by area if area specified
    if area_id:
        entities = await self.data_api_client.fetch_entities(area_id=area_id, limit=10000)
    else:
        entities = await self.data_api_client.fetch_entities(limit=10000)
    
    # Show ALL entities for key domains (light, switch, etc.), not just 3
    if domain in ["light", "switch", "sensor"]:
        # Show all entities, not just samples
        for entity in entities:
            if entity.get("domain") == domain:
                # Include in summary
```

---

## Testing Plan

### Enhancement Timeout
1. Test with slow OpenAI API (simulate timeout)
2. Verify partial results are returned
3. Verify frontend shows error/retry option
4. Test with normal API speed (should work)

### Entity Resolution
1. Test: "office's top-left light" → should match office light with "top" or "left" in name
2. Test: "office lights" → should match ALL office lights, not kitchen
3. Test: "kitchen strip" → should match kitchen lights only
4. Verify context includes all matching entities

---

## Files to Modify

### Backend
1. `services/ha-ai-agent-service/src/services/enhancement_service.py` - Timeout handling
2. `services/ha-ai-agent-service/src/services/entity_inventory_service.py` - Area filtering
3. `services/ha-ai-agent-service/src/prompts/system_prompt.py` - Entity matching instructions
4. `services/ha-ai-agent-service/src/services/context_builder.py` - Query analysis

### Frontend
1. `services/ai-automation-ui/src/components/ha-agent/EnhancementButton.tsx` - Timeout handling

---

## Priority Order

1. **CRITICAL:** Fix entity resolution (wrong lights matched)
2. **HIGH:** Fix enhancement timeout (stuck loading)
3. **MEDIUM:** Optimize enhancement generation speed
4. **LOW:** Add caching for enhancements

---

## Estimated Time

- Phase 1 (Enhancement Timeout): 2-3 hours
- Phase 2 (Entity Resolution): 3-4 hours
- **Total:** 5-7 hours

---

## Success Criteria

✅ Enhancement suggestions return within 30 seconds  
✅ Partial results shown if some enhancements timeout  
✅ Entity resolution matches correct lights by area + keywords  
✅ Context includes all relevant entities, not just 3 samples  
✅ System prompt provides clear entity matching guidance

