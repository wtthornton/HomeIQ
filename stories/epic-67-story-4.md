# Story 67.4 -- Graceful Degradation & Circuit Breaker

<!-- docsmcp:start:user-story -->

> **As a** operator, **I want** YAML generation to continue working when validation services are down, **so that** linter/validator outages don't block automation creation

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that YAML generation continues working when validation services are down, avoiding cascading failures from linter/validator outages.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

When automation-linter or yaml-validation-service is unreachable, skip validation and return the raw LLM output with a warning flag (validated: false). Use existing CircuitBreaker from homeiq-resilience. Log AI FALLBACK: prefix.

See [Epic 67](stories/epic-67-automation-validation-loop.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ai-automation-service-new/src/clients/validation_client.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add circuit breaker fallback logic (`domains/automation-core/ai-automation-service-new/src/clients/validation_client.py`)
- [ ] Add validated flag to response model (`domains/automation-core/ai-automation-service-new/src/models/generation_response.py`)
- [ ] Add AI FALLBACK: logging (`domains/automation-core/ai-automation-service-new/src/services/yaml_generation_service.py`)
- [ ] Write tests for degraded scenarios (`tests/unit/test_validation_degradation.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] When linter is down validation is skipped with validated=false flag
- [ ] When validator is down validation is skipped with validated=false flag
- [ ] CircuitBreaker from homeiq-resilience used (3 failures 60s recovery)
- [ ] AI FALLBACK: log prefix used for monitoring

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 67](stories/epic-67-automation-validation-loop.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_linter_down_validation_skipped_validatedfalse_flag` -- When linter is down validation is skipped with validated=false flag
2. `test_ac2_validator_down_validation_skipped_validatedfalse_flag` -- When validator is down validation is skipped with validated=false flag
3. `test_ac3_circuitbreaker_from_homeiqresilience_used_3_failures_60s_recovery` -- CircuitBreaker from homeiq-resilience used (3 failures 60s recovery)
4. `test_ac4_ai_fallback_log_prefix_used_monitoring` -- AI FALLBACK: log prefix used for monitoring

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (74%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (70%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

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
