# Story AI5.2: Add Energy and Event Context to Ask AI

**Story ID**: AI5.2  
**Title**: Add Energy and Event Context to Ask AI  
**Epic**: AI-5  
**Priority**: High  
**Estimated Points**: 2  
**Story Type**: Feature  
**Dependencies**: AI5.1  
**Vertical Slice**: Users get energy-aware and event-aware automation suggestions when querying about high-power devices and entertainment systems  
**AI Agent Scope**: 2-4 hours - Add energy and event context detection and integration to existing Ask AI router  
**Created**: December 19, 2024  
**Last Updated**: December 19, 2024  

## User Story

As a **user**, I want my Ask AI queries about high-power devices and entertainment systems to include energy-aware and event-aware suggestions so that I get intelligent recommendations based on energy pricing and events.

## Acceptance Criteria

### Functional Requirements
- [ ] Ask AI router detects high-power devices in user queries
- [ ] Ask AI router detects entertainment devices in user queries
- [ ] Energy context is automatically included for high-power device queries
- [ ] Event context is automatically included for entertainment device queries
- [ ] Energy and event suggestions are generated using existing detectors
- [ ] Suggestions are formatted to match existing Ask AI suggestion format
- [ ] Suggestions are clearly labeled as "energy-aware" or "event-aware"

### Technical Requirements
- [ ] Code follows Python best practices
- [ ] Contextual analysis adds <50ms to query response time
- [ ] Error handling implemented for detector failures
- [ ] Unit tests written with >90% coverage
- [ ] Integration tests cover Ask AI router with all contextual types

## Implementation Details

### Files to Modify
- `services/ai-automation-service/src/api/ask_ai_router.py`

### Key Implementation Points
- **Detection Logic**: Identify high-power devices and entertainment devices
- **Energy Integration**: Use existing `EnergyOpportunityDetector`
- **Event Integration**: Use existing `EventOpportunityDetector`
- **Suggestion Format**: Convert opportunities to Ask AI suggestion format
- **Performance**: Minimal impact on existing query performance
- **Error Handling**: Graceful fallback if detectors fail

### Simple Integration Approach
```python
# In ask_ai_router.py - add to generate_suggestions_from_query function
async def generate_suggestions_from_query(query: str, entities: List[Dict], user_id: str):
    suggestions = []
    
    # Add energy context for high-power devices
    high_power_entities = [e for e in entities if is_high_power_device(e)]
    if high_power_entities:
        try:
            from ..contextual_patterns import EnergyOpportunityDetector
            energy_detector = EnergyOpportunityDetector(
                influxdb_client=data_client.influxdb_client,
                data_api_client=data_client
            )
            energy_opportunities = await energy_detector.detect_opportunities()
            
            for opportunity in energy_opportunities:
                suggestions.append({
                    'suggestion_id': f'energy-{uuid.uuid4().hex[:8]}',
                    'description': opportunity['opportunity_metadata']['rationale'],
                    'trigger_summary': opportunity['opportunity_metadata']['trigger_name'],
                    'action_summary': opportunity['opportunity_metadata']['suggested_action'],
                    'devices_involved': opportunity['devices'],
                    'confidence': opportunity['confidence'],
                    'context': 'energy_aware',
                    'status': 'draft'
                })
        except Exception as e:
            logger.warning(f"Energy context failed: {e}")
    
    # Add event context for entertainment devices
    entertainment_entities = [e for e in entities if is_entertainment_device(e)]
    if entertainment_entities:
        try:
            from ..contextual_patterns import EventOpportunityDetector
            event_detector = EventOpportunityDetector(data_api_client=data_client)
            event_opportunities = await event_detector.detect_opportunities()
            
            for opportunity in event_opportunities:
                suggestions.append({
                    'suggestion_id': f'event-{uuid.uuid4().hex[:8]}',
                    'description': opportunity['opportunity_metadata']['rationale'],
                    'trigger_summary': opportunity['opportunity_metadata']['trigger_name'],
                    'action_summary': opportunity['opportunity_metadata']['suggested_action'],
                    'devices_involved': opportunity['devices'],
                    'confidence': opportunity['confidence'],
                    'context': 'event_aware',
                    'status': 'draft'
                })
        except Exception as e:
            logger.warning(f"Event context failed: {e}")
    
    # Continue with existing OpenAI-based suggestions
    # ... existing code ...
    
    return suggestions

def is_high_power_device(entity: Dict) -> bool:
    """Check if entity is a high-power device"""
    entity_id = entity.get('entity_id', '').lower()
    high_power_keywords = [
        'dishwasher', 'washer', 'dryer', 'water_heater',
        'ev_charger', 'pool_pump', 'ac_unit', 'heat_pump'
    ]
    return any(keyword in entity_id for keyword in high_power_keywords)

def is_entertainment_device(entity: Dict) -> bool:
    """Check if entity is an entertainment device"""
    entity_id = entity.get('entity_id', '').lower()
    entertainment_keywords = [
        'tv', 'media_player', 'living_room', 'theater',
        'sound', 'speaker', 'receiver', 'projector'
    ]
    return any(keyword in entity_id for keyword in entertainment_keywords)
```

## Definition of Done

- [ ] High-power device detection implemented
- [ ] Entertainment device detection implemented
- [ ] Energy context integration working
- [ ] Event context integration working
- [ ] Performance requirements met
- [ ] Suggestions properly formatted
- [ ] Error handling implemented
- [ ] Unit tests written and passing
- [ ] User acceptance testing completed

## Testing

### Unit Tests
- Test device type detection
- Test energy context integration
- Test event context integration
- Test suggestion formatting
- Test error handling

### Integration Tests
- Test Ask AI router with all contextual types
- Test performance requirements
- Test error scenarios

### User Acceptance Testing
- Test high-power device queries include energy suggestions
- Test entertainment device queries include event suggestions
- Test suggestions are clearly labeled
- Test response time requirements met

## Risks

- **Performance Impact**: Multiple contextual detectors may add latency
- **Error Handling**: Detectors may fail
- **Integration Complexity**: May require changes to existing code

## Mitigation

- **Performance**: Use 1-day lookback and caching
- **Error Handling**: Graceful fallback to existing suggestions
- **Integration**: Minimal changes to existing code structure
