# Story AI5.3: Unified Suggestion Engine Foundation

**Story ID**: AI5.3  
**Title**: Unified Suggestion Engine Foundation  
**Epic**: AI-5  
**Phase**: 2  
**Priority**: High  
**Estimated Points**: 8  
**Dependencies**: AI5.1, AI5.2  
**Created**: December 19, 2024  
**Last Updated**: December 19, 2024  

## User Story

As a **developer**, I want to create a unified suggestion engine service so that both daily analysis and user queries can use the same contextual intelligence logic.

## Acceptance Criteria

- [ ] Create `UnifiedSuggestionEngine` class in `src/intelligence/unified_suggestion_engine.py`
- [ ] Service accepts both user query parameters and batch analysis parameters
- [ ] Service integrates with existing `DataAPIClient`, `InfluxDBClient`, and `OpenAIClient`
- [ ] Service provides configuration options for contextual feature toggles
- [ ] Service includes proper error handling and logging
- [ ] Service has comprehensive unit tests with >90% coverage

## Technical Requirements

- **Input Parameters**: 
  - `user_query` (optional): Natural language query string
  - `entities` (optional): List of extracted entities
  - `include_contextual` (bool): Whether to include contextual patterns
  - `contextual_config` (dict): Configuration for contextual features
- **Output**: List of suggestion dictionaries with consistent format
- **Dependencies**: Existing clients (DataAPI, InfluxDB, OpenAI)
- **Configuration**: Support for enabling/disabling individual contextual detectors

## Implementation Details

### Files to Create
- `services/ai-automation-service/src/intelligence/__init__.py`
- `services/ai-automation-service/src/intelligence/unified_suggestion_engine.py`
- `services/ai-automation-service/src/intelligence/config.py`
- `services/ai-automation-service/tests/test_unified_suggestion_engine.py`

### Service Architecture

```python
# src/intelligence/unified_suggestion_engine.py
class UnifiedSuggestionEngine:
    def __init__(
        self,
        data_api_client: DataAPIClient,
        influxdb_client: InfluxDBClient,
        openai_client: OpenAIClient,
        config: ContextualConfig
    ):
        self.data_api = data_api_client
        self.influxdb = influxdb_client
        self.openai = openai_client
        self.config = config
        
        # Initialize contextual detectors
        self.weather_detector = WeatherOpportunityDetector(...)
        self.energy_detector = EnergyOpportunityDetector(...)
        self.event_detector = EventOpportunityDetector(...)
    
    async def generate_suggestions(
        self,
        user_query: Optional[str] = None,
        entities: Optional[List[Dict]] = None,
        include_contextual: bool = True,
        contextual_config: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Unified suggestion generation that combines:
        - User query analysis (if provided)
        - Entity extraction (if provided)
        - Contextual pattern detection (weather, energy, events)
        - Historical pattern analysis
        """
        suggestions = []
        
        # 1. Process user query if provided
        if user_query and entities:
            query_suggestions = await self._process_user_query(user_query, entities)
            suggestions.extend(query_suggestions)
        
        # 2. Add contextual opportunities if enabled
        if include_contextual:
            contextual_suggestions = await self._get_contextual_opportunities(entities, contextual_config)
            suggestions.extend(contextual_suggestions)
        
        # 3. Merge and rank suggestions
        return await self._merge_and_rank_suggestions(suggestions)
```

## Definition of Done

- [ ] Service class created with proper initialization
- [ ] All dependencies injected via constructor
- [ ] Configuration system implemented
- [ ] Error handling covers all failure scenarios
- [ ] Logging implemented for debugging and monitoring
- [ ] Unit tests written and passing
- [ ] Code reviewed and approved
- [ ] Documentation updated

## Testing

### Unit Tests
- Test service initialization
- Test suggestion generation with different inputs
- Test contextual detector integration
- Test error handling scenarios
- Test configuration system

### Integration Tests
- Test with real clients (DataAPI, InfluxDB, OpenAI)
- Test performance requirements
- Test suggestion format consistency

## Risks

- **Complexity**: Service may become too complex
- **Performance**: May be slower than direct calls
- **Dependencies**: Many dependencies to manage

## Mitigation

- **Complexity**: Keep methods focused and simple
- **Performance**: Implement caching and optimization
- **Dependencies**: Use dependency injection and interfaces
