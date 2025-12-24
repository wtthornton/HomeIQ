# Story AI5.3: Add Contextual Configuration

**Story ID**: AI5.3  
**Title**: Add Contextual Configuration  
**Epic**: AI-5  
**Priority**: Medium  
**Estimated Points**: 1  
**Story Type**: Foundation  
**Dependencies**: AI5.1, AI5.2  
**Vertical Slice**: System administrators can configure contextual features and monitor their performance  
**AI Agent Scope**: 2-4 hours - Add configuration system and monitoring to existing Ask AI router  
**Created**: December 19, 2024  
**Last Updated**: December 19, 2024  

## User Story

As a **system administrator**, I want to configure contextual features and monitor their performance so that I can enable/disable them and troubleshoot issues.

## Acceptance Criteria

### Functional Requirements
- [ ] Configuration options to enable/disable individual contextual features
- [ ] Environment variable support for contextual settings
- [ ] Contextual suggestion metrics in health endpoint
- [ ] Logging for contextual decision-making
- [ ] Default configuration enables all contextual features

### Technical Requirements
- [ ] Code follows Python best practices
- [ ] Configuration system is simple and maintainable
- [ ] Health metrics include contextual suggestion counts
- [ ] Logging includes contextual decision-making information
- [ ] Unit tests written with >90% coverage

## Implementation Details

### Files to Modify
- `services/ai-automation-service/src/config.py`
- `services/ai-automation-service/src/api/health.py`
- `services/ai-automation-service/infrastructure/env.ai-automation`

### Simple Configuration Approach
```python
# In config.py - add to Settings class
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Contextual Intelligence Configuration
    enable_weather_context: bool = Field(default=True, description="Enable weather context in Ask AI")
    enable_energy_context: bool = Field(default=True, description="Enable energy context in Ask AI")
    enable_event_context: bool = Field(default=True, description="Enable event context in Ask AI")
    
    # Performance settings
    contextual_lookback_days: int = Field(default=1, description="Days of data to analyze for contextual suggestions")
    contextual_timeout_seconds: int = Field(default=10, description="Timeout for contextual analysis")
    
    class Config:
        env_file = "infrastructure/env.ai-automation"
        env_prefix = "CONTEXTUAL_"
```

### Health Metrics Integration
```python
# In health.py - add to health check
@router.get("/health")
async def health_check():
    # ... existing health check ...
    
    # Contextual intelligence metrics
    contextual_metrics = {
        "weather_context_enabled": settings.enable_weather_context,
        "energy_context_enabled": settings.enable_energy_context,
        "event_context_enabled": settings.enable_event_context,
        "weather_suggestions_generated": get_contextual_suggestion_count("weather"),
        "energy_suggestions_generated": get_contextual_suggestion_count("energy"),
        "event_suggestions_generated": get_contextual_suggestion_count("event"),
        "contextual_errors": get_contextual_error_count()
    }
    
    return {
        # ... existing health data ...
        "contextual_intelligence": contextual_metrics
    }
```

### Ask AI Router Integration
```python
# In ask_ai_router.py - add configuration checks
async def generate_suggestions_from_query(query: str, entities: List[Dict], user_id: str):
    suggestions = []
    
    # Add weather context if enabled
    if settings.enable_weather_context:
        climate_entities = [e for e in entities if e.get('domain') == 'climate']
        if climate_entities:
            # ... weather context logic ...
    
    # Add energy context if enabled
    if settings.enable_energy_context:
        high_power_entities = [e for e in entities if is_high_power_device(e)]
        if high_power_entities:
            # ... energy context logic ...
    
    # Add event context if enabled
    if settings.enable_event_context:
        entertainment_entities = [e for e in entities if is_entertainment_device(e)]
        if entertainment_entities:
            # ... event context logic ...
    
    # Continue with existing OpenAI-based suggestions
    # ... existing code ...
    
    return suggestions
```

## Definition of Done

- [ ] Configuration system implemented
- [ ] Environment variable support working
- [ ] Health metrics updated
- [ ] Logging implemented
- [ ] Default configuration set
- [ ] Ask AI router uses configuration
- [ ] Unit tests written and passing
- [ ] Integration tests completed

## Testing

### Unit Tests
- Test configuration loading
- Test environment variable parsing
- Test default values
- Test health metrics
- Test Ask AI router configuration integration

### Integration Tests
- Test configuration in Ask AI router
- Test health endpoint with contextual metrics
- Test logging functionality
- Test enable/disable functionality

## Risks

- **Configuration Complexity**: May be confusing for users
- **Performance Impact**: Health metrics may add overhead
- **Logging Overhead**: May generate too many logs

## Mitigation

- **Configuration**: Use sensible defaults and clear documentation
- **Performance**: Cache health metrics
- **Logging**: Use appropriate log levels
