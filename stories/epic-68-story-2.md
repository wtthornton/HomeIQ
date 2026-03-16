# Story 68.2 -- Memory Brain Integration — Preference Recall

<!-- docsmcp:start:user-story -->

> **As a** smart home user, **I want** the system to remember my preferences and past decisions, **so that** suggestions improve over time and match my habits

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that the proactive agent queries user preference history from Memory Brain before generating suggestions, enabling personalized and improving recommendations.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Integrate homeiq-memory to query user preference history before generating suggestions. Recall past contexts, acceptance/rejection rates, and explicit preferences. Inject into LLM reasoning prompt.

See [Epic 68](stories/epic-68-proactive-agent-upgrade.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/energy-analytics/proactive-agent-service/src/services/preference_recall.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create PreferenceRecaller class using homeiq-memory client (`domains/energy-analytics/proactive-agent-service/src/services/preference_recall.py`)
- [ ] Build preference context injection for LLM prompt (`domains/energy-analytics/proactive-agent-service/src/services/reason.py`)
- [ ] Add circuit breaker for Memory Brain calls (`domains/energy-analytics/proactive-agent-service/src/services/preference_recall.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Queries Memory Brain for similar past contexts before reasoning
- [ ] Retrieves acceptance/rejection rates per action type
- [ ] Injects preference context into LLM reasoning prompt
- [ ] Handles Memory Brain unavailability gracefully

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 68](stories/epic-68-proactive-agent-upgrade.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_queries_memory_brain_similar_past_contexts_before_reasoning` -- Queries Memory Brain for similar past contexts before reasoning
2. `test_ac2_retrieves_acceptancerejection_rates_per_action_type` -- Retrieves acceptance/rejection rates per action type
3. `test_ac3_injects_preference_context_into_llm_reasoning_prompt` -- Injects preference context into LLM reasoning prompt
4. `test_ac4_handles_memory_brain_unavailability_gracefully` -- Handles Memory Brain unavailability gracefully

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (72%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (62%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- List stories or external dependencies that must complete first...

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can be developed and delivered independently
- [ ] **N**egotiable -- Details can be refined during implementation
- [x] **V**aluable -- Delivers value to a user or the system
- [x] **E**stimable -- Team can estimate the effort
- [ ] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
