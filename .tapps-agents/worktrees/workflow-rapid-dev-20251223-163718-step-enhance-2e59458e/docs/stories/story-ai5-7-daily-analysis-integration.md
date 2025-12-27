# Story AI5.7: Daily Analysis Integration

**Story ID**: AI5.7  
**Title**: Daily Analysis Integration  
**Epic**: AI-5  
**Phase**: 2  
**Priority**: High  
**Estimated Points**: 5  
**Dependencies**: AI5.3, AI5.4, AI5.5  
**Created**: December 19, 2024  
**Last Updated**: December 19, 2024  

## User Story

As a **system**, I want the daily analysis scheduler to use the unified suggestion engine so that both automated and user-initiated suggestions use the same intelligence logic.

## Acceptance Criteria

- [ ] Daily analysis scheduler uses `UnifiedSuggestionEngine` for contextual opportunities
- [ ] Existing weather opportunity detection continues to work
- [ ] New energy and event opportunities are included in daily analysis
- [ ] Daily analysis performance remains unchanged
- [ ] All existing daily analysis functionality continues to work
- [ ] Configuration allows enabling/disabling contextual features for batch processing

## Technical Requirements

- **Integration**: Replace direct contextual pattern calls with `UnifiedSuggestionEngine`
- **Performance**: Maintain existing daily analysis performance
- **Configuration**: Support batch-level contextual feature toggles
- **Backward Compatibility**: Existing daily analysis output format unchanged
- **Error Handling**: Graceful degradation if contextual features fail

## Implementation Details

### Files to Modify
- `services/ai-automation-service/src/scheduler/daily_analysis.py`
- `services/ai-automation-service/src/main.py`

### Integration Changes

```python
# In daily_analysis.py
from ..intelligence.unified_suggestion_engine import UnifiedSuggestionEngine

async def run_daily_analysis(self):
    # ... existing phases ...
    
    # Phase 3c: Synergy Detection (Epic AI-3) - Updated
    logger.info("  → Part B: Contextual opportunity detection (Epic AI-3)...")
    
    try:
        # Initialize unified engine for batch processing
        unified_engine = UnifiedSuggestionEngine(
            data_api_client=data_client,
            influxdb_client=data_client.influxdb_client,
            openai_client=openai_client,
            config=ContextualConfig(
                enable_weather=True,
                enable_energy=True,
                enable_events=True,
                batch_mode=True
            )
        )
        
        # Get contextual opportunities using unified engine
        contextual_suggestions = await unified_engine.generate_suggestions(
            include_contextual=True,
            contextual_config={
                'weather_lookback_days': 7,
                'energy_lookback_days': 7,
                'event_lookback_days': 7
            }
        )
        
        # Convert to synergies format for backward compatibility
        synergies = []
        for suggestion in contextual_suggestions:
            if suggestion.get('context') in ['weather_aware', 'energy_aware', 'event_aware']:
                synergies.append({
                    'synergy_id': suggestion['suggestion_id'],
                    'synergy_type': suggestion['context'],
                    'devices': suggestion['devices_involved'],
                    'relationship': suggestion.get('trigger_summary', 'contextual_automation'),
                    'impact_score': suggestion['confidence'],
                    'complexity': 'medium',
                    'confidence': suggestion['confidence'],
                    'opportunity_metadata': {
                        'description': suggestion['description'],
                        'action_summary': suggestion['action_summary']
                    }
                })
        
        # Add to synergies list
        synergies.extend(contextual_suggestions)
        
        logger.info(f"     ✅ Found {len(synergies)} contextual opportunities")
        
    except Exception as e:
        logger.warning(f"     ⚠️ Contextual opportunity detection failed: {e}")
        synergies = []
```

## Definition of Done

- [ ] Daily analysis scheduler refactored to use unified service
- [ ] Performance requirements met
- [ ] All contextual detectors working in batch mode
- [ ] Configuration system working
- [ ] Error handling implemented
- [ ] Integration tests written and passing
- [ ] Daily analysis testing completed

## Testing

### Unit Tests
- Test unified engine integration in daily analysis
- Test synergy format conversion
- Test configuration system
- Test error handling

### Integration Tests
- Test complete daily analysis workflow
- Test performance requirements
- Test backward compatibility

### System Tests
- Test daily analysis with all contextual features
- Test error scenarios and recovery
- Test configuration changes

## Risks

- **Performance Impact**: Unified service may slow down daily analysis
- **Integration Complexity**: May require significant changes to daily analysis
- **Backward Compatibility**: May break existing synergy format

## Mitigation

- **Performance**: Optimize for batch processing and add caching
- **Integration**: Incremental refactoring with thorough testing
- **Backward Compatibility**: Maintain existing synergy format
