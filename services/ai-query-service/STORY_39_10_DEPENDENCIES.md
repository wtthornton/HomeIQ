# Story 39.10: Query Service Migration - Dependencies

## Completed Components

### Service Structure
- ✅ Query processor service (`services/query/processor.py`)
- ✅ Clarification service (`services/clarification/service.py`)
- ✅ Suggestion generator service (`services/suggestion/generator.py`)

### Router Updates
- ✅ Basic query router with placeholder endpoints
- ⏳ Full endpoint extraction from `ask_ai_router.py` (pending)

## Dependencies to Address

### Entity Extraction
- **UnifiedExtractionPipeline**: Needs to be copied or imported from ai-automation-service
- **AutomationContext**: Model definitions need to be available
- **HomeAssistantClient**: For entity extraction
- **DeviceIntelligenceClient**: For device intelligence data

### Clarification Services
- **ClarificationDetector**: Full implementation from `services/clarification/detector.py`
- **QuestionGenerator**: Full implementation from `services/clarification/question_generator.py`
- **ConfidenceCalculator**: Full implementation from `services/clarification/confidence_calculator.py`
- **AutoResolver**: For auto-resolving ambiguities
- **UncertaintyQuantifier**: For uncertainty quantification

### Suggestion Generation
- **generate_suggestions_from_query()**: Full function from `ask_ai_router.py` (1600+ lines)
- **RAGClient**: For RAG-based suggestion retrieval
- **UnifiedPromptBuilder**: For prompt building
- **EntityValidator**: For entity validation and enrichment
- **Pattern-based fallback**: Pattern querying logic

### Database Models
- **AskAIQuery**: Query model (shared database)
- **ClarificationSessionDB**: Clarification session model (shared database)
- **Pattern**: Pattern model for fallback suggestions

### Clients
- **HomeAssistantClient**: For HA API calls
- **DataAPIClient**: For data API calls
- **DeviceIntelligenceClient**: For device intelligence
- **OpenAIClient**: For OpenAI API calls

## Next Steps

1. **Copy UnifiedExtractionPipeline** to query service or create a shared module
2. **Extract full suggestion generation logic** from `generate_suggestions_from_query()`
3. **Copy clarification services** from ai-automation-service
4. **Set up client initialization** in main.py
5. **Update query router** with full endpoint implementations
6. **Add caching layer** for query results (optimization)
7. **Add performance monitoring** for <500ms P95 target

## Notes

- The query service uses a shared database, so models are accessible
- Many services can be imported from ai-automation-service initially, then migrated
- Focus on low-latency optimization: caching, parallel processing, timeout management

