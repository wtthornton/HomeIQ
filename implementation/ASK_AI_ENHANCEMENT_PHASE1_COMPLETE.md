# Ask AI Enhancement - Phase 1 Implementation Complete

**Date:** January 6, 2025  
**Status:** ✅ PHASE 1 COMPLETE  
**Phase:** Reduce Suggestions & Add Debug Data

## Summary

Phase 1 of the Ask AI enhancement has been successfully implemented. The system now generates 2 suggestions instead of 5, and includes comprehensive debug information for device selection, OpenAI interactions, and technical prompts.

## Changes Implemented

### 1. Reduced Suggestions from 5 to 2 ✅

**File:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`

- Changed prompt from "Generate 3-5 suggestions" to "Generate EXACTLY 2 suggestions"
- Updated progression strategy to focus on:
  1. First suggestion: Direct, straightforward automation (high confidence 0.9+)
  2. Second suggestion: Enhanced variation with practical improvements (moderate-high confidence 0.8-0.9)

### 2. Debug Data Collection ✅

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**New Functions:**
- `build_device_selection_debug_data()`: Creates detailed debug information for each device showing:
  - Why the device was selected (exact match, fuzzy match, etc.)
  - Entity ID mapping
  - Entity type (group vs individual)
  - All entities in the device (for groups)
  - Device capabilities
  - Suggested actions based on domain

- `generate_technical_prompt()`: Creates structured technical prompts containing:
  - Trigger entities with state transitions
  - Action entities with service calls
  - Entity capabilities mapping
  - Metadata (query, devices involved, confidence)

**Modified Functions:**
- `generate_suggestions_from_query()`: Now captures:
  - OpenAI system prompt
  - OpenAI user prompt
  - OpenAI response (parsed JSON)
  - Token usage (if available)
  - Device selection debug data
  - Technical prompt for each suggestion

### 3. Debug Panel Component ✅

**File:** `services/ai-automation-ui/src/components/ask-ai/DebugPanel.tsx`

**Features:**
- Collapsible panel with three tabs:
  1. **Device Selection Tab:**
     - Shows each device with selection reasoning
     - Displays entity IDs, types, and all entities in groups
     - Lists capabilities and suggested actions
  
  2. **OpenAI Prompts Tab:**
     - Full system prompt
     - Full user prompt
     - OpenAI response (formatted JSON)
     - Token usage statistics
  
  3. **Technical Prompt Tab:**
     - Complete technical prompt (formatted JSON)
     - Trigger entities with details
     - Action entities with service calls

**Integration:**
- Added to `services/ai-automation-ui/src/pages/AskAI.tsx`
- Renders below each suggestion card
- Supports dark mode
- Responsive design

## Data Structure

### Suggestion Object Now Includes:

```typescript
{
  suggestion_id: string;
  description: string;
  trigger_summary: string;
  action_summary: string;
  devices_involved: string[];
  validated_entities: Record<string, string>;
  capabilities_used: string[];
  confidence: number;
  status: 'draft' | ...;
  created_at: string;
  
  // NEW: Debug data
  debug: {
    device_selection: Array<{
      device_name: string;
      entity_id: string | null;
      selection_reason: string;
      entity_type: string | null;
      entities: Array<{ entity_id: string; friendly_name: string }>;
      capabilities: string[];
      actions_suggested: string[];
    }>;
    system_prompt: string;
    user_prompt: string;
    openai_response: any;
    token_usage?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
  };
  
  // NEW: Technical prompt
  technical_prompt: {
    alias: string;
    description: string;
    trigger: {
      entities: Array<{...}>;
      platform: string;
    };
    action: {
      entities: Array<{...}>;
      service_calls: Array<{...}>;
    };
    conditions: any[];
    entity_capabilities: Record<string, string[]>;
    metadata: {
      query: string;
      devices_involved: string[];
      confidence: number;
    };
  };
}
```

## Testing

### Manual Testing Steps:

1. **Navigate to Ask AI page:** `http://localhost:3001/ask-ai`
2. **Submit a query:** e.g., "Turn on the office lights when I enter the office"
3. **Verify:**
   - Only 2 suggestions are generated (not 5)
   - Each suggestion has a "Debug Panel" section below it
   - Debug panel can be expanded/collapsed
   - All three tabs are accessible:
     - Device Selection shows device reasoning
     - OpenAI Prompts shows full prompts and response
     - Technical Prompt shows structured prompt data

### Expected Behavior:

- ✅ Suggestions are limited to 2
- ✅ Debug panel appears for each suggestion
- ✅ Device selection debug shows why each device was chosen
- ✅ OpenAI prompts are visible
- ✅ Technical prompt is generated and stored
- ✅ Technical prompt is displayed in readable format

## Next Steps (Phase 2 & 3)

### Phase 2: Technical Prompt Generation (Planned)
- Enhance technical prompt generation with better trigger/action extraction
- Add condition extraction from suggestions
- Improve service call parameter inference

### Phase 3: Separate YAML Generation (Planned)
- Create `generate_yaml_from_technical_prompt()` function
- Modify `approve_suggestion_from_query()` to use technical prompt only
- Implement hybrid approach (tactical templates + AI)

## Database Considerations

**Note:** The `technical_prompt` field is currently stored in the suggestion object but may need to be persisted to the database. This is tracked as TODO #7 and can be addressed when:
- Database schema changes are approved
- We verify technical prompts are being used correctly
- Performance impact is measured

## Files Modified

### Backend:
1. `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`
2. `services/ai-automation-service/src/api/ask_ai_router.py`

### Frontend:
1. `services/ai-automation-ui/src/components/ask-ai/DebugPanel.tsx` (NEW)
2. `services/ai-automation-ui/src/pages/AskAI.tsx`

## Benefits

1. **Better User Experience:**
   - Fewer suggestions = faster decision-making
   - Debug panel provides transparency
   - Users can understand why devices were selected

2. **Developer Benefits:**
   - Full visibility into OpenAI interactions
   - Technical prompts ready for YAML generation
   - Easier debugging and optimization

3. **Cost Optimization:**
   - Reduced API costs (fewer tokens for 2 vs 5 suggestions)
   - Technical prompts enable template-based YAML generation (future)

## Known Limitations

1. **Token Usage:** Currently not captured from OpenAI responses (method may not expose it)
2. **Technical Prompt Quality:** Simple heuristic-based extraction (can be improved in Phase 2)
3. **Database Storage:** Technical prompts not yet persisted (tracked in TODO #7)

---

**Status:** ✅ Phase 1 Complete - Ready for Testing  
**Next Phase:** Phase 2 - Enhance Technical Prompt Generation

