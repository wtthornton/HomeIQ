# Story 69.1 -- Request Complexity Classifier

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** a request complexity classifier that scores incoming requests, **so that** requests can be routed to the appropriate cost/quality model

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that incoming requests are classified by complexity, enabling cost-optimized model routing without degrading quality for complex queries.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Build a lightweight rule-based classifier scoring requests as low/medium/high complexity based on token count, entity count, tool hint, conversation depth. Route: low→gpt-5-mini, high→gpt-5.2-codex.

See [Epic 69](stories/epic-69-agent-eval-feedback-loop.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ha-ai-agent-service/src/services/complexity_classifier.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create ComplexityClassifier class (`domains/automation-core/ha-ai-agent-service/src/services/complexity_classifier.py`)
- [ ] Define classification rules and thresholds (`domains/automation-core/ha-ai-agent-service/src/services/complexity_classifier.py`)
- [ ] Wire into request pipeline before OpenAI call (`domains/automation-core/ha-ai-agent-service/src/api/chat_endpoints.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Classifies requests as low/medium/high complexity
- [ ] Uses token count and entity count and tool hint and conversation depth
- [ ] Rule-based heuristics (no ML)
- [ ] Added to ha-ai-agent-service request pipeline before OpenAI call
- [ ] Classification logged for correlation analysis

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 69](stories/epic-69-agent-eval-feedback-loop.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_classifies_requests_as_lowmediumhigh_complexity` -- Classifies requests as low/medium/high complexity
2. `test_ac2_uses_token_count_entity_count_tool_hint_conversation_depth` -- Uses token count and entity count and tool hint and conversation depth
3. `test_ac3_rulebased_heuristics_no_ml` -- Rule-based heuristics (no ML)
4. `test_ac4_added_haaiagentservice_request_pipeline_before_openai_call` -- Added to ha-ai-agent-service request pipeline before OpenAI call
5. `test_ac5_classification_logged_correlation_analysis` -- Classification logged for correlation analysis

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (68%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
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
