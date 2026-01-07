# Step 3: Architecture Design - HA AI Agent Context Enhancement

## System Architecture

### Current Architecture
```
ContextBuilder
  ├─ EntityInventoryService
  ├─ DevicesSummaryService
  ├─ AreasService
  ├─ ServicesSummaryService
  ├─ HelpersScenesService
  └─ EntityAttributesService
```

### Enhanced Architecture (Phase 1)
```
ContextBuilder
  ├─ EntityInventoryService
  ├─ DevicesSummaryService
  ├─ AreasService
  ├─ ServicesSummaryService
  ├─ HelpersScenesService
  ├─ EntityAttributesService
  └─ DeviceStateContextService (NEW)
      ├─ EntityResolutionService (extract entities from prompt)
      ├─ DataAPIClient (fetch states)
      └─ Caching (30-60s TTL)
```

### Data Flow (Phase 1: Device State Context)

```
User Prompt
  ↓
PromptAssemblyService.assemble_messages()
  ├─ Extract entities from prompt (EntityResolutionService)
  ├─ Call DeviceStateContextService.get_state_context(entity_ids)
  │   ├─ Check cache
  │   ├─ Fetch states via DataAPIClient or HA Client
  │   └─ Format and cache
  └─ Include in context section
```

## Component Design

### DeviceStateContextService

**Responsibilities:**
- Extract entity IDs from user prompt (or accept as parameter)
- Fetch current entity states
- Format states for context inclusion
- Cache states with appropriate TTL

**Dependencies:**
- DataAPIClient (primary - for entity states)
- HomeAssistantClient (fallback - if Data API unavailable)
- EntityResolutionService (for extracting entities from prompt)
- ContextBuilder (for cache access)

**Interface:**
```python
class DeviceStateContextService:
    async def get_state_context(
        self, 
        entity_ids: list[str] | None = None,
        user_prompt: str | None = None,
        skip_truncation: bool = False
    ) -> str
```

**Integration Points:**
- Called from PromptAssemblyService when assembling messages
- Optional context section (only if entities mentioned)
- Respects token budget (truncates if needed)

## Implementation Details

### Phase 1: Device State Context Service

**Location:** `services/ha-ai-agent-service/src/services/device_state_context_service.py`

**Key Features:**
- Async state fetching
- Caching (30-60 second TTL)
- Graceful degradation
- Token-aware formatting

**Caching Strategy:**
- Cache key: `device_state_context_{entity_ids_hash}`
- TTL: 30-60 seconds (states change frequently)
- Invalidate on state changes (future enhancement)

**Error Handling:**
- If Data API unavailable → try HA Client
- If HA Client unavailable → return empty context
- Log warnings, don't fail entire context building

**Token Management:**
- Limit to 1000 tokens for state context
- Format concisely (entity_id: state, attributes)
- Truncate if exceeds limit

## Integration with Existing System

### ContextBuilder Changes
- Add DeviceStateContextService initialization
- Add optional state context section
- Maintain backward compatibility (state context is optional)

### PromptAssemblyService Changes
- Extract entities from user prompt
- Call DeviceStateContextService if entities mentioned
- Include state context in message assembly
- Respect token budget (state context counts toward limit)

## Performance Considerations
- State fetching is async (non-blocking)
- Caching reduces API calls
- Short TTL balances freshness vs. performance
- Graceful degradation ensures system remains functional

## Security & Privacy
- Only fetch states for entities mentioned in prompt
- Don't include all device states (privacy)
- Cache appropriately (short TTL)
