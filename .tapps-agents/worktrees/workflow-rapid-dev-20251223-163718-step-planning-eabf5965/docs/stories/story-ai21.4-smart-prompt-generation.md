# Story AI21.4: Smart Prompt Generation

**Epic:** AI-21 - Proactive Conversational Agent Service  
**Status:** 🚧 In Progress  
**Points:** 5  
**Effort:** 8-10 hours  
**Created:** December 2025

---

## User Story

**As a** developer,  
**I want** a prompt generation service,  
**so that** I can create context-aware prompts for the HA AI Agent.

---

## Business Value

- Creates natural language prompts from context analysis
- Enables proactive automation suggestions
- Improves suggestion relevance through context-aware prompts
- Foundation for conversational automation creation

---

## Acceptance Criteria

1. ✅ PromptGenerationService class
2. ✅ Context-aware prompt building (weather + sports + energy + patterns)
3. ✅ Natural language prompt formatting
4. ✅ Multi-context prompt assembly
5. ✅ Prompt template system
6. ✅ Prompt quality scoring
7. ✅ Example prompt formats:
   - "It's going to be 95°F tomorrow. Should I create an automation to pre-cool your home?"
   - "Your team plays at 7 PM tonight. Should I create an automation to dim lights during the game?"
   - "Carbon intensity is low right now. Should I schedule your EV charging?"
8. ✅ Unit tests for prompt generation

---

## Tasks

- [x] Create PromptGenerationService class
- [x] Implement prompt template system
- [x] Implement context-aware prompt building
- [x] Add natural language formatting
- [x] Add prompt quality scoring
- [x] Write unit tests

---

## File List

- `services/proactive-agent-service/src/services/prompt_generation_service.py` (NEW)
- `services/proactive-agent-service/tests/test_prompt_generation_service.py` (NEW)

---

## Implementation Notes

- Uses context analysis results from Story AI21.2
- Template-based approach for maintainability
- Natural language formatting for conversational feel
- Quality scoring to filter poor prompts

---

## QA Results

_To be completed after implementation_

