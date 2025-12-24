# Story AI5.1: Add Weather Context to Ask AI

**Story ID**: AI5.1  
**Title**: Add Weather Context to Ask AI  
**Epic**: AI-5  
**Priority**: High  
**Estimated Points**: 2  
**Story Type**: Feature  
**Dependencies**: None  
**Vertical Slice**: Users get weather-aware automation suggestions when querying about climate devices  
**AI Agent Scope**: 2-4 hours - Add weather context detection and integration to existing Ask AI router  
**Created**: December 19, 2024  
**Last Updated**: December 19, 2024  

## User Story

As a **user**, I want my Ask AI queries about climate devices to include weather-aware suggestions so that I get intelligent recommendations based on current weather conditions.

## Acceptance Criteria

### Functional Requirements
- [ ] Ask AI router detects climate-related entities in user queries
- [ ] Weather context is automatically included for climate device queries
- [ ] Weather suggestions are generated using existing `WeatherOpportunityDetector`
- [ ] Weather suggestions are formatted to match existing Ask AI suggestion format
- [ ] Weather suggestions are clearly labeled as "weather-aware"

### Technical Requirements
- [ ] Code follows Python best practices
- [ ] Weather context adds <50ms to query response time
- [ ] Error handling implemented for weather detector failures
- [ ] Unit tests written with >90% coverage
- [ ] Integration tests cover Ask AI router with weather context

## Implementation Details

### Files to Modify
- `services/ai-automation-service/src/api/ask_ai_router.py`

### Key Implementation Points
- **Detection Logic**: Identify climate entities (`climate.*` domain)
- **Weather Integration**: Use existing `WeatherOpportunityDetector` with 1-day lookback
- **Suggestion Format**: Convert weather opportunities to Ask AI suggestion format
- **Performance**: Minimal impact on existing query performance
- **Error Handling**: Graceful fallback if weather context fails

### Simple Integration Approach
```python
# In ask_ai_router.py - add to generate_suggestions_from_query function
async def generate_suggestions_from_query(query: str, entities: List[Dict], user_id: str):
    suggestions = []
    
    # Add weather context for climate devices
    climate_entities = [e for e in entities if e.get('domain') == 'climate']
    if climate_entities:
        try:
            from ..contextual_patterns import WeatherOpportunityDetector
            weather_detector = WeatherOpportunityDetector(
                influxdb_client=data_client.influxdb_client,
                data_api_client=data_client
            )
            weather_opportunities = await weather_detector.detect_opportunities(days=1)
            
            for opportunity in weather_opportunities:
                suggestions.append({
                    'suggestion_id': f'weather-{uuid.uuid4().hex[:8]}',
                    'description': opportunity['opportunity_metadata']['rationale'],
                    'trigger_summary': opportunity['opportunity_metadata']['trigger_name'],
                    'action_summary': opportunity['opportunity_metadata']['suggested_action'],
                    'devices_involved': opportunity['devices'],
                    'confidence': opportunity['confidence'],
                    'context': 'weather_aware',
                    'status': 'draft'
                })
        except Exception as e:
            logger.warning(f"Weather context failed: {e}")
    
    # Continue with existing OpenAI-based suggestions
    # ... existing code ...
    
    return suggestions
```

## Definition of Done

- [ ] Climate entity detection implemented
- [ ] Weather context integration working
- [ ] Performance requirements met
- [ ] Weather suggestions properly formatted
- [ ] Error handling implemented
- [ ] Unit tests written and passing
- [ ] User acceptance testing completed

## Testing

### Unit Tests
- Test climate entity detection
- Test weather context integration
- Test suggestion formatting
- Test error handling

### Integration Tests
- Test Ask AI router with weather context
- Test performance requirements
- Test error scenarios

### User Acceptance Testing
- Test climate device queries include weather suggestions
- Test weather suggestions are clearly labeled
- Test response time requirements met

## Risks

- **Performance Impact**: Weather context may add latency
- **Error Handling**: Weather detector may fail
- **Integration Complexity**: May require changes to existing code

## Mitigation

- **Performance**: Use 1-day lookback instead of 7-day
- **Error Handling**: Graceful fallback to existing suggestions
- **Integration**: Minimal changes to existing code structure
