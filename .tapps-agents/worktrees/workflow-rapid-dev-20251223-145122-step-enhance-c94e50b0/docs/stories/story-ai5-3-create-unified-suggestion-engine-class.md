# Story AI5.3: Create UnifiedSuggestionEngine Class

**Story ID**: AI5.3  
**Title**: Create UnifiedSuggestionEngine Class  
**Epic**: AI-5  
**Phase**: 2  
**Priority**: High  
**Estimated Points**: 2  
**Story Type**: Foundation  
**Dependencies**: AI5.1, AI5.2  
**Vertical Slice**: Core unified service class that can be used by both Ask AI router and daily analysis  
**AI Agent Scope**: 2-4 hours - Create basic class structure with dependency injection and configuration  
**Created**: December 19, 2024  
**Last Updated**: December 19, 2024  

## User Story

As a **developer**, I want to create a unified suggestion engine class so that both Ask AI router and daily analysis can use the same contextual intelligence logic.

## Acceptance Criteria

### Functional Requirements
- [ ] `UnifiedSuggestionEngine` class created in `src/intelligence/unified_suggestion_engine.py`
- [ ] Class accepts dependency injection for DataAPI, InfluxDB, and OpenAI clients
- [ ] Class provides basic `generate_suggestions` method signature
- [ ] Class supports configuration for contextual feature toggles
- [ ] Class includes proper error handling and logging

### Technical Requirements
- [ ] Code follows Python best practices
- [ ] Class uses dependency injection pattern
- [ ] Error handling covers all failure scenarios
- [ ] Logging implemented for debugging and monitoring
- [ ] Unit tests written with >90% coverage

## Implementation Details

### Files to Create
- `services/ai-automation-service/src/intelligence/__init__.py`
- `services/ai-automation-service/src/intelligence/unified_suggestion_engine.py`
- `services/ai-automation-service/src/intelligence/config.py`
- `services/ai-automation-service/tests/test_unified_suggestion_engine.py`

### Class Structure

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
    
    async def generate_suggestions(
        self,
        user_query: Optional[str] = None,
        entities: Optional[List[Dict]] = None,
        include_contextual: bool = True,
        contextual_config: Optional[Dict] = None
    ) -> List[Dict]:
        """Generate suggestions using unified contextual intelligence"""
        # Basic implementation - will be enhanced in later stories
        return []
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
- Test dependency injection
- Test configuration system
- Test error handling scenarios
- Test basic method signatures

### Integration Tests
- Test with mock clients
- Test configuration loading
- Test error scenarios

## Risks

- **Complexity**: Service may become too complex
- **Dependencies**: Many dependencies to manage
- **Configuration**: Configuration system may be complex

## Mitigation

- **Complexity**: Keep methods focused and simple
- **Dependencies**: Use dependency injection and interfaces
- **Configuration**: Start with simple configuration, enhance iteratively
