# Story 67.6 -- Integration Tests

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** end-to-end tests covering all retry loop scenarios, **so that** the validation loop is verified against real service instances

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that the validation loop is verified end-to-end against real service instances, ensuring retry and degradation logic works in production-like conditions.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

End-to-end tests covering: pass-on-first-try, pass-on-second-try, all-retries-exhausted, linter-down graceful degradation. Use real automation-linter and yaml-validation-service instances.

See [Epic 67](stories/epic-67-automation-validation-loop.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `tests/integration/test_validation_loop_e2e.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Write pass-on-first-try integration test (`tests/integration/test_validation_loop_e2e.py`)
- [ ] Write pass-on-second-try integration test (`tests/integration/test_validation_loop_e2e.py`)
- [ ] Write all-retries-exhausted test (`tests/integration/test_validation_loop_e2e.py`)
- [ ] Write linter-down degradation test (`tests/integration/test_validation_loop_e2e.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Test: pass-on-first-try returns immediately
- [ ] Test: pass-on-second-try proves error feedback works
- [ ] Test: all-retries-exhausted returns best attempt with errors
- [ ] Test: linter-down triggers graceful degradation
- [ ] Tests use real service instances not mocks

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 67](stories/epic-67-automation-validation-loop.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_test_passonfirsttry_returns_immediately` -- Test: pass-on-first-try returns immediately
2. `test_ac2_test_passonsecondtry_proves_error_feedback_works` -- Test: pass-on-second-try proves error feedback works
3. `test_ac3_test_allretriesexhausted_returns_best_attempt_errors` -- Test: all-retries-exhausted returns best attempt with errors
4. `test_ac4_test_linterdown_triggers_graceful_degradation` -- Test: linter-down triggers graceful degradation
5. `test_ac5_tests_use_real_service_instances_not_mocks` -- Tests use real service instances not mocks

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
