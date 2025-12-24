# Story AI5.6: Ask AI Router Refactoring

**Story ID**: AI5.6  
**Title**: Ask AI Router Refactoring  
**Epic**: AI-5  
**Phase**: 2  
**Priority**: High  
**Estimated Points**: 5  
**Dependencies**: AI5.3, AI5.4, AI5.5  
**Created**: December 19, 2024  
**Last Updated**: December 19, 2024  

## User Story

As a **user**, I want my Ask AI queries to use the unified contextual intelligence service so that I get consistent, high-quality suggestions with all contextual awareness.

## Acceptance Criteria

- [ ] Ask AI router uses `UnifiedSuggestionEngine` for all queries
- [ ] Contextual suggestions are seamlessly integrated with OpenAI-based suggestions
- [ ] Query response time remains under 2 seconds
- [ ] Contextual suggestions are clearly labeled and differentiated
- [ ] Users can see which contextual sources contributed to suggestions
- [ ] Configuration allows enabling/disabling contextual features per query

## Technical Requirements

- **Integration**: Replace existing suggestion generation with `UnifiedSuggestionEngine`
- **Performance**: Maintain existing response time requirements
- **Format**: Ensure contextual suggestions match existing suggestion format
- **Configuration**: Support query-level contextual feature toggles
- **Backward Compatibility**: Existing API contracts remain unchanged

## Implementation Details

### Files to Modify
- `services/ai-automation-service/src/api/ask_ai_router.py`
- `services/ai-automation-service/src/main.py`

### Refactoring Changes

```python
# In ask_ai_router.py
from ..intelligence.unified_suggestion_engine import UnifiedSuggestionEngine

# Initialize unified service
_unified_engine = None

def set_unified_engine(engine: UnifiedSuggestionEngine):
    global _unified_engine
    _unified_engine = engine

async def generate_suggestions_from_query(
    query: str, 
    entities: List[Dict[str, Any]], 
    user_id: str
) -> List[Dict[str, Any]]:
    """Generate suggestions using unified contextual intelligence"""
    
    if not _unified_engine:
        raise HTTPException(status_code=500, detail="Unified engine not initialized")
    
    # Use unified engine for all suggestion generation
    suggestions = await _unified_engine.generate_suggestions(
        user_query=query,
        entities=entities,
        include_contextual=True,
        contextual_config={
            'enable_weather': True,
            'enable_energy': True,
            'enable_events': True
        }
    )
    
    return suggestions
```

## Definition of Done

- [ ] Ask AI router refactored to use unified service
- [ ] Performance requirements met
- [ ] API contracts unchanged
- [ ] Contextual suggestions properly integrated
- [ ] Configuration system working
- [ ] Integration tests written and passing
- [ ] User acceptance testing completed

## Testing

### Unit Tests
- Test unified engine integration
- Test suggestion format consistency
- Test configuration system
- Test error handling

### Integration Tests
- Test complete Ask AI workflow
- Test performance requirements
- Test API contract compatibility

### User Acceptance Testing
- Test contextual suggestions in Ask AI
- Test suggestion quality and relevance
- Test response time requirements

## Risks

- **Performance Impact**: Unified service may be slower
- **Integration Complexity**: May require significant changes
- **Backward Compatibility**: May break existing functionality

## Mitigation

- **Performance**: Optimize unified service and add caching
- **Integration**: Incremental refactoring with thorough testing
- **Backward Compatibility**: Maintain existing API contracts
