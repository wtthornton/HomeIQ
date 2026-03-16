# Story 68.3 -- Confidence & Risk Scoring Engine

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** a scoring engine that evaluates proposed actions on confidence and risk, **so that** the system can decide whether to auto-execute or suggest for approval

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that the proactive agent can objectively evaluate proposed actions on confidence and risk axes, enabling safe autonomous execution decisions.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Implement a scoring engine with confidence (0-100) and risk (low/medium/high/critical). Define configurable thresholds: auto-execute (confidence>85, risk=low), suggest (confidence>50 or risk=medium), suppress (confidence<30).

See [Epic 68](stories/epic-68-proactive-agent-upgrade.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/energy-analytics/proactive-agent-service/src/services/scoring_engine.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create ConfidenceRiskScorer class (`domains/energy-analytics/proactive-agent-service/src/services/scoring_engine.py`)
- [ ] Implement confidence scoring algorithm (`domains/energy-analytics/proactive-agent-service/src/services/scoring_engine.py`)
- [ ] Implement risk classification logic (`domains/energy-analytics/proactive-agent-service/src/services/scoring_engine.py`)
- [ ] Add configurable thresholds (`domains/energy-analytics/proactive-agent-service/src/config.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Confidence score 0-100 based on historical acceptance and context match
- [ ] Risk classification based on action type and reversibility
- [ ] Thresholds: auto-execute and suggest and suppress
- [ ] Thresholds configurable per user

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 68](stories/epic-68-proactive-agent-upgrade.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_confidence_score_0100_based_on_historical_acceptance_context_match` -- Confidence score 0-100 based on historical acceptance and context match
2. `test_ac2_risk_classification_based_on_action_type_reversibility` -- Risk classification based on action type and reversibility
3. `test_ac3_thresholds_autoexecute_suggest_suppress` -- Thresholds: auto-execute and suggest and suppress
4. `test_ac4_thresholds_configurable_per_user` -- Thresholds configurable per user

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (66%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
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
- [ ] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
