# Story 66.3 -- New Service Classification Decision Tree

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** a visual decision tree for classifying new services into AI tiers, **so that** new services are consistently classified without tribal knowledge

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 1 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that new services are consistently classified into AI tiers using a visual decision tree, removing reliance on tribal knowledge.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Add a decision tree flowchart (Mermaid) to the classification doc that helps developers classify new services: Does it call an LLM? → Does it iterate on LLM output? → Does it invoke tools autonomously? → Assign tier.

See [Epic 66](stories/epic-66-ai-agent-classification.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `docs/architecture/ai-agent-classification.md`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Design Mermaid decision tree flowchart (`docs/architecture/ai-agent-classification.md`)
- [ ] Add to classification doc with explanation (`docs/architecture/ai-agent-classification.md`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Mermaid flowchart renders correctly in GitHub markdown
- [ ] Covers all 4 tiers with clear branching questions
- [ ] Integrated into ai-agent-classification.md

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 66](stories/epic-66-ai-agent-classification.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_mermaid_flowchart_renders_correctly_github_markdown` -- Mermaid flowchart renders correctly in GitHub markdown
2. `test_ac2_covers_all_4_tiers_clear_branching_questions` -- Covers all 4 tiers with clear branching questions
3. `test_ac3_integrated_into_aiagentclassificationmd` -- Integrated into ai-agent-classification.md

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (73%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (61%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

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
