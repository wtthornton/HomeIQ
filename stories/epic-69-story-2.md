# Story 69.2 -- Adaptive Model Router

<!-- docsmcp:start:user-story -->

> **As a** operator, **I want** automatic model selection based on complexity and eval scores, **so that** simple requests use cheaper models while complex ones get full capability

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that model selection is dynamic based on complexity and eval scores, reducing costs for simple queries while maintaining quality.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Implement a ModelRouter selecting the OpenAI model per-request. Auto-upgrade to expensive model when eval scores drop below threshold. Store decisions in InfluxDB. Expose routing table via API.

See [Epic 69](stories/epic-69-agent-eval-feedback-loop.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ha-ai-agent-service/src/services/model_router.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create ModelRouter class (`domains/automation-core/ha-ai-agent-service/src/services/model_router.py`)
- [ ] Implement eval-score-based auto-upgrade (`domains/automation-core/ha-ai-agent-service/src/services/model_router.py`)
- [ ] Store routing decisions in InfluxDB (`domains/automation-core/ha-ai-agent-service/src/services/model_router.py`)
- [ ] Add GET /api/model-routing endpoint (`domains/automation-core/ha-ai-agent-service/src/api/routing_endpoints.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] ModelRouter selects model per-request based on complexity
- [ ] Auto-upgrades when eval scores drop below threshold (default 70)
- [ ] Routing decisions stored in InfluxDB
- [ ] GET /api/model-routing exposes routing table
- [ ] Fallback to expensive model on routing errors

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 69](stories/epic-69-agent-eval-feedback-loop.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_modelrouter_selects_model_perrequest_based_on_complexity` -- ModelRouter selects model per-request based on complexity
2. `test_ac2_autoupgrades_eval_scores_drop_below_threshold_default_70` -- Auto-upgrades when eval scores drop below threshold (default 70)
3. `test_ac3_routing_decisions_stored_influxdb` -- Routing decisions stored in InfluxDB
4. `test_ac4_get_apimodelrouting_exposes_routing_table` -- GET /api/model-routing exposes routing table
5. `test_ac5_fallback_expensive_model_on_routing_errors` -- Fallback to expensive model on routing errors

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (68%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (58%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

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
