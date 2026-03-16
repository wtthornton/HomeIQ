# Story 66.1 -- Service Classification Audit & Tier Document

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** a single reference document classifying all 51 HomeIQ services by AI tier, **so that** I can quickly understand which services use LLMs, ML models, or no AI without reading source code

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that developers have a single reference document classifying all 51 HomeIQ services by AI tier, eliminating the need to read source code to understand which services use LLMs, ML models, or no AI.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Create docs/architecture/ai-agent-classification.md with 4-tier classification (True Agent, LLM Wrapper, ML Inference, Non-AI) for all 51 services. Include evidence table with columns: Service, Domain, Port, Tier, LLM/Model, Agent Loop, Tool Use, Key File.

See [Epic 66](stories/epic-66-ai-agent-classification.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `docs/architecture/ai-agent-classification.md`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Audit all 51 services for LLM/ML/agent patterns (`docs/architecture/ai-agent-classification.md`)
- [ ] Create 4-tier classification table (`docs/architecture/ai-agent-classification.md`)
- [ ] Add per-service evidence references to source files (`docs/architecture/ai-agent-classification.md`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Document covers all 51 services
- [ ] Each service has tier label with evidence
- [ ] Table includes columns for Service/Domain/Port/Tier/LLM-Model/Agent-Loop/Tool-Use/Key-File
- [ ] Document follows existing docs/architecture/ conventions

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 66](stories/epic-66-ai-agent-classification.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_document_covers_all_51_services` -- Document covers all 51 services
2. `test_ac2_each_service_tier_label_evidence` -- Each service has tier label with evidence
3. `test_ac3_table_includes_columns` -- Table includes columns for Service/Domain/Port/Tier/LLM-Model/Agent-Loop/Tool-Use/Key-File
4. `test_ac4_document_follows_existing_docsarchitecture_conventions` -- Document follows existing docs/architecture/ conventions

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (82%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (69%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

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
