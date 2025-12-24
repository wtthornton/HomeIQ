# Story AI21.6: Suggestion Generation Pipeline

**Epic:** AI-21 - Proactive Conversational Agent Service  
**Status:** 🚧 In Progress  
**Points:** 8  
**Effort:** 12-15 hours  
**Created:** December 2025

---

## User Story

**As a** developer,  
**I want** a suggestion generation pipeline,  
**so that** I can orchestrate the full flow from context analysis to suggestion storage.

---

## Business Value

- Orchestrates complete suggestion generation flow
- Integrates all components (context, prompts, agent, storage)
- Enables automated proactive suggestions
- Foundation for scheduled batch processing

---

## Acceptance Criteria

1. ✅ SuggestionPipelineService class
2. ✅ Full orchestration flow (context → prompts → agent → storage)
3. ✅ Error handling and recovery
4. ✅ Quality scoring and filtering
5. ✅ Batch processing support
6. ✅ Progress tracking
7. ✅ Unit tests

---

## Tasks

1. Create `SuggestionPipelineService` class
2. Implement `generate_suggestions()` method
3. Integrate ContextAnalysisService
4. Integrate PromptGenerationService
5. Integrate HAAgentClient
6. Integrate SuggestionStorageService
7. Add error handling and retry logic
8. Add quality scoring
9. Write unit tests

---

## Technical Notes

- Pipeline orchestrates: Context Analysis → Prompt Generation → Agent Communication → Storage
- Quality threshold: 0.6 (configurable)
- Max suggestions per batch: 10 (configurable)
- Error handling: Graceful degradation, continue on individual failures

