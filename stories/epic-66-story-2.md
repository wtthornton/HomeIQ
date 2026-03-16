# Story 66.2 -- Architecture Decision Record — Single Agent Design

<!-- docsmcp:start:user-story -->

> **As a** architect, **I want** an ADR explaining why HomeIQ limits true agent behavior to one service, **so that** future decisions about adding agent capabilities are informed by documented trade-offs

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that future decisions about adding agent capabilities are informed by a documented ADR covering the trade-offs of the intentional single-agent architecture.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Write ADR documenting why HomeIQ intentionally limits true agent behavior to ha-ai-agent-service. Cover: context (cost, latency, testability, predictability), decision, consequences, and conditions under which the decision should be revisited.

See [Epic 66](stories/epic-66-ai-agent-classification.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `docs/architecture/adr-single-agent-architecture.md`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Write ADR with context/decision/consequences sections (`docs/architecture/adr-single-agent-architecture.md`)
- [ ] Add cross-reference to classification doc (`docs/architecture/ai-agent-classification.md`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] ADR follows standard ADR format (Context/Decision/Status/Consequences)
- [ ] Covers cost and latency and testability and predictability trade-offs
- [ ] Documents conditions for revisiting the decision
- [ ] Cross-referenced from classification doc

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 66](stories/epic-66-ai-agent-classification.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_adr_follows_standard_adr_format_contextdecisionstatusconsequences` -- ADR follows standard ADR format (Context/Decision/Status/Consequences)
2. `test_ac2_covers_cost_latency_testability_predictability_tradeoffs` -- Covers cost and latency and testability and predictability trade-offs
3. `test_ac3_documents_conditions_revisiting_decision` -- Documents conditions for revisiting the decision
4. `test_ac4_crossreferenced_from_classification_doc` -- Cross-referenced from classification doc

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (75%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (59%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

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
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
