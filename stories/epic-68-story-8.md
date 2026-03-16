# Story 68.8 -- Integration Tests & Safety Validation

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** end-to-end tests proving safety guardrails and preference learning work, **so that** autonomous execution is verified safe before deployment

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that autonomous execution, safety guardrails, and preference learning are verified end-to-end before deployment.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

E2E tests: auto-execution of low-risk action, suggestion surfacing for medium-risk, safety guardrail blocks lock/alarm, preference learning over 5 iterations, undo reversal, quiet hours suppression.

See [Epic 68](stories/epic-68-proactive-agent-upgrade.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `tests/integration/test_proactive_agent_e2e.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Write auto-execution integration test (`tests/integration/test_proactive_agent_e2e.py`)
- [ ] Write safety guardrail tests (`tests/integration/test_proactive_agent_e2e.py`)
- [ ] Write preference learning test (`tests/integration/test_proactive_agent_e2e.py`)
- [ ] Write undo and quiet hours tests (`tests/integration/test_proactive_agent_e2e.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Test: low-risk high-confidence auto-executes
- [ ] Test: medium-risk surfaces as suggestion
- [ ] Test: lock/alarm/camera blocked from auto-execution
- [ ] Test: confidence improves over 5 iterations
- [ ] Test: undo reverses autonomous action
- [ ] Test: quiet hours suppress all autonomous actions

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 68](stories/epic-68-proactive-agent-upgrade.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_test_lowrisk_highconfidence_autoexecutes` -- Test: low-risk high-confidence auto-executes
2. `test_ac2_test_mediumrisk_surfaces_as_suggestion` -- Test: medium-risk surfaces as suggestion
3. `test_ac3_test_lockalarmcamera_blocked_from_autoexecution` -- Test: lock/alarm/camera blocked from auto-execution
4. `test_ac4_test_confidence_improves_over_5_iterations` -- Test: confidence improves over 5 iterations
5. `test_ac5_test_undo_reverses_autonomous_action` -- Test: undo reverses autonomous action
6. `test_ac6_test_quiet_hours_suppress_all_autonomous_actions` -- Test: quiet hours suppress all autonomous actions

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (69%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
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
