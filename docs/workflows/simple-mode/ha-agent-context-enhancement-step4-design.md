# Step 4: Component Design - HA AI Agent Context Enhancement

## DeviceStateContextService Design

### Service Interface

```python
class DeviceStateContextService:
    """
    Service for fetching and formatting current entity states for context inclusion.
    
    Fetches current states of entities mentioned in user prompts to help LLM
    make smarter automation decisions.
    """
    
    async def get_state_context(
        self,
        entity_ids: list[str] | None = None,
        user_prompt: str | None = None,
        skip_truncation: bool = False
    ) -> str:
        """
        Get formatted state context for specified entities.
        
        Args:
            entity_ids: Optional list of entity IDs to fetch states for
            user_prompt: Optional user prompt to extract entities from
            skip_truncation: If True, skip truncation (for debug display)
            
        Returns:
            Formatted context string with entity states, or empty string if no entities
        """
```

### Service Architecture

**Dependencies:**
- `Settings` - Application configuration
- `ContextBuilder` - For cache access
- `HomeAssistantClient` - Primary source for entity states
- `DataAPIClient` - Fallback if HA Client unavailable
- `EntityResolutionService` - For extracting entities from user prompt

**Caching:**
- Cache key: `device_state_context_{hash(entity_ids)}`
- TTL: 45 seconds (balances freshness vs. performance)
- Cache location: ContextCache table (via ContextBuilder)

**Error Handling:**
- Try HomeAssistantClient.get_states() first
- Fallback to DataAPIClient if HA Client fails
- Return empty string if both fail (graceful degradation)
- Log warnings, don't fail context building

### Format Specification

**Output Format:**
```
DEVICE STATES:
- entity_id_1: state (attribute: value, attribute2: value2)
- entity_id_2: state (attribute: value)
...
```

**Token Management:**
- Limit to 1000 tokens (~750 words)
- Format concisely (entity_id: state, key attributes only)
- Truncate if exceeds limit (keep most relevant entities)

**Attribute Selection:**
- Always include: state
- For lights: brightness, color_mode, rgb_color (if set), color_temp
- For climate: temperature, hvac_action, current_temperature
- For covers: position, current_position
- Skip verbose/unnecessary attributes

### Integration Points

#### ContextBuilder Integration
- Add `_device_state_context_service` attribute
- Initialize in `initialize()` method
- Add optional call in `build_context()` (only if entities mentioned)

#### PromptAssemblyService Integration
- Extract entities from user prompt using EntityResolutionService
- Call DeviceStateContextService.get_state_context(entity_ids)
- Include state context in message assembly
- Respect token budget (state context counts toward 16K limit)

### Performance Considerations
- Async state fetching (non-blocking)
- Cache reduces API calls (45 second TTL)
- Batch entity state filtering (fetch all, filter in memory)
- Graceful degradation ensures system remains functional

### Security & Privacy
- Only fetch states for entities mentioned in prompt
- Don't include all device states (privacy)
- Cache appropriately (short TTL)
- No sensitive data exposure
