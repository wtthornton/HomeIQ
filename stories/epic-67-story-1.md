# Story 67.1 -- Validation Client Integration

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** a ValidationClient that calls automation-linter and yaml-validation-service, **so that** generated YAML can be validated inline before returning to users

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that ai-automation-service-new can call automation-linter and yaml-validation-service inline to validate generated YAML before returning it to users.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Create a ValidationClient in ai-automation-service-new that calls automation-linter POST /lint and yaml-validation-service POST /validate. Include circuit breaker wrapping and timeout (2s per call). Return structured ValidationResult with pass/fail, findings list, and severity.

See [Epic 67](stories/epic-67-automation-validation-loop.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ai-automation-service-new/src/clients/validation_client.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create ValidationClient class (`domains/automation-core/ai-automation-service-new/src/clients/validation_client.py`)
- [ ] Create ValidationResult dataclass (`domains/automation-core/ai-automation-service-new/src/models/validation_result.py`)
- [ ] Wire CircuitBreaker from homeiq-resilience (`domains/automation-core/ai-automation-service-new/src/clients/validation_client.py`)
- [ ] Write unit tests (`tests/unit/test_validation_client.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] ValidationClient calls POST /lint on automation-linter:8034
- [ ] ValidationClient calls POST /validate on yaml-validation-service:8041
- [ ] Circuit breaker wraps both calls (3 failures 60s recovery)
- [ ] Timeout of 2s per validation call
- [ ] Returns structured ValidationResult dataclass

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 67](stories/epic-67-automation-validation-loop.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_validationclient_calls_post_lint_on_automationlinter8034` -- ValidationClient calls POST /lint on automation-linter:8034
2. `test_ac2_validationclient_calls_post_validate_on_yamlvalidationservice8041` -- ValidationClient calls POST /validate on yaml-validation-service:8041
3. `test_ac3_circuit_breaker_wraps_both_calls_3_failures_60s_recovery` -- Circuit breaker wraps both calls (3 failures 60s recovery)
4. `test_ac4_timeout_2s_per_validation_call` -- Timeout of 2s per validation call
5. `test_ac5_returns_structured_validationresult_dataclass` -- Returns structured ValidationResult dataclass

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (66%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (64%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

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
