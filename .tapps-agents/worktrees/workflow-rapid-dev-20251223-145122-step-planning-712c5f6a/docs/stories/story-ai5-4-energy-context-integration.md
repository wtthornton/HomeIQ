# Story AI5.4: Energy Context Integration

**Story ID**: AI5.4  
**Title**: Energy Context Integration  
**Epic**: AI-5  
**Phase**: 2  
**Priority**: Medium  
**Estimated Points**: 5  
**Dependencies**: AI5.3  
**Created**: December 19, 2024  
**Last Updated**: December 19, 2024  

## User Story

As a **user**, I want my queries about high-power devices to include energy-aware suggestions so that I can optimize my electricity usage and costs.

## Acceptance Criteria

- [ ] Energy context is automatically detected for high-power device queries
- [ ] Energy opportunities are converted to user-friendly suggestion format
- [ ] Energy suggestions include cost savings estimates
- [ ] Energy context respects configuration settings
- [ ] Energy suggestions are properly ranked with other suggestions
- [ ] Energy context works for devices like EV chargers, pool pumps, water heaters

## Technical Requirements

- **Detection Logic**: Identify high-power devices and energy-related keywords
- **Energy Integration**: Use existing `EnergyOpportunityDetector`
- **Suggestion Format**: Convert energy opportunities to standard suggestion format
- **Configuration**: Respect `enable_energy_context` setting
- **Performance**: Energy context adds <50ms to query response time

## Implementation Details

### Files to Modify
- `services/ai-automation-service/src/intelligence/unified_suggestion_engine.py`
- `services/ai-automation-service/src/intelligence/config.py`

### Detection Logic

```python
def _is_high_power_device(entity: Dict) -> bool:
    """Check if entity is a high-power device"""
    entity_id = entity.get('entity_id', '').lower()
    high_power_keywords = [
        'dishwasher', 'washer', 'dryer', 'water_heater',
        'ev_charger', 'pool_pump', 'ac_unit', 'heat_pump'
    ]
    return any(keyword in entity_id for keyword in high_power_keywords)

def _has_energy_keywords(query: str) -> bool:
    """Check if query contains energy-related keywords"""
    energy_keywords = [
        'energy', 'electricity', 'power', 'cost', 'bill',
        'peak', 'off-peak', 'pricing', 'savings'
    ]
    return any(keyword in query.lower() for keyword in energy_keywords)
```

## Definition of Done

- [ ] High-power device detection implemented
- [ ] Energy keyword detection implemented
- [ ] Energy opportunity conversion to suggestions working
- [ ] Configuration integration complete
- [ ] Performance requirements met
- [ ] Integration tests written and passing
- [ ] User acceptance testing completed

## Testing

### Unit Tests
- Test high-power device detection
- Test energy keyword detection
- Test suggestion conversion
- Test configuration integration

### Integration Tests
- Test with real energy data
- Test performance requirements
- Test error handling

## Risks

- **Data Availability**: Energy pricing data may not be available
- **Performance**: Energy context may add latency
- **Accuracy**: Energy suggestions may not be accurate

## Mitigation

- **Data Availability**: Graceful fallback if no energy data
- **Performance**: Use caching and optimization
- **Accuracy**: Use conservative estimates and disclaimers
