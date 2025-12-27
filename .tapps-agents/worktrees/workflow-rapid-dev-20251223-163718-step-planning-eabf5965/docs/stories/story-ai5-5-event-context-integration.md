# Story AI5.5: Event Context Integration

**Story ID**: AI5.5  
**Title**: Event Context Integration  
**Epic**: AI-5  
**Phase**: 2  
**Priority**: Medium  
**Estimated Points**: 5  
**Dependencies**: AI5.3  
**Created**: December 19, 2024  
**Last Updated**: December 19, 2024  

## User Story

As a **user**, I want my queries about entertainment devices to include event-aware suggestions so that I can automate my home for sports games and special events.

## Acceptance Criteria

- [ ] Event context is automatically detected for entertainment device queries
- [ ] Event opportunities are converted to user-friendly suggestion format
- [ ] Event suggestions include sports schedule and calendar integration
- [ ] Event context respects configuration settings
- [ ] Event suggestions are properly ranked with other suggestions
- [ ] Event context works for TV, media players, and lighting systems

## Technical Requirements

- **Detection Logic**: Identify entertainment devices and event-related keywords
- **Event Integration**: Use existing `EventOpportunityDetector`
- **Suggestion Format**: Convert event opportunities to standard suggestion format
- **Configuration**: Respect `enable_event_context` setting
- **Performance**: Event context adds <50ms to query response time

## Implementation Details

### Files to Modify
- `services/ai-automation-service/src/intelligence/unified_suggestion_engine.py`
- `services/ai-automation-service/src/intelligence/config.py`

### Detection Logic

```python
def _is_entertainment_device(entity: Dict) -> bool:
    """Check if entity is an entertainment device"""
    entity_id = entity.get('entity_id', '').lower()
    entertainment_keywords = [
        'tv', 'media_player', 'living_room', 'theater',
        'sound', 'speaker', 'receiver', 'projector'
    ]
    return any(keyword in entity_id for keyword in entertainment_keywords)

def _has_event_keywords(query: str) -> bool:
    """Check if query contains event-related keywords"""
    event_keywords = [
        'game', 'sports', 'movie', 'show', 'event',
        'party', 'celebration', 'holiday', 'schedule'
    ]
    return any(keyword in query.lower() for keyword in event_keywords)
```

## Definition of Done

- [ ] Entertainment device detection implemented
- [ ] Event keyword detection implemented
- [ ] Event opportunity conversion to suggestions working
- [ ] Configuration integration complete
- [ ] Performance requirements met
- [ ] Integration tests written and passing
- [ ] User acceptance testing completed

## Testing

### Unit Tests
- Test entertainment device detection
- Test event keyword detection
- Test suggestion conversion
- Test configuration integration

### Integration Tests
- Test with real event data
- Test performance requirements
- Test error handling

## Risks

- **Data Availability**: Event data may not be available
- **Performance**: Event context may add latency
- **Relevance**: Event suggestions may not be relevant

## Mitigation

- **Data Availability**: Graceful fallback if no event data
- **Performance**: Use caching and optimization
- **Relevance**: Use conservative filtering and user feedback
