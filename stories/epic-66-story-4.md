# Story 66.4 -- Cross-Reference Integration

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** existing architecture docs to link to the new classification document, **so that** the classification is discoverable from multiple entry points

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 1 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that the AI classification document is discoverable from multiple existing architecture docs, ensuring developers find it regardless of entry point.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Update service-groups.md, TECH_STACK.md, and LLM_ML_MODELS_02222026.md to link to the new classification doc. Add AI tier column to existing service tables where applicable.

See [Epic 66](stories/epic-66-ai-agent-classification.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `docs/architecture/service-groups.md`
- `TECH_STACK.md`
- `implementation/LLM_ML_MODELS_02222026.md`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add links and AI tier column to service-groups.md (`docs/architecture/service-groups.md`)
- [ ] Add link to TECH_STACK.md (`TECH_STACK.md`)
- [ ] Add link to LLM model inventory (`implementation/LLM_ML_MODELS_02222026.md`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] service-groups.md links to classification doc
- [ ] TECH_STACK.md links to classification doc
- [ ] LLM_ML_MODELS_02222026.md links to classification doc
- [ ] AI tier column added to existing service tables

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 66](stories/epic-66-ai-agent-classification.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_servicegroupsmd_links_classification_doc` -- service-groups.md links to classification doc
2. `test_ac2_techstackmd_links_classification_doc` -- TECH_STACK.md links to classification doc
3. `test_ac3_llmmlmodels02222026md_links_classification_doc` -- LLM_ML_MODELS_02222026.md links to classification doc
4. `test_ac4_ai_tier_column_added_existing_service_tables` -- AI tier column added to existing service tables

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (74%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (60%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

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
