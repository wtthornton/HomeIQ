# Story 67.2 -- Retry Loop in YAML Generation Pipeline

<!-- docsmcp:start:user-story -->

> **As a** user, **I want** the YAML generation service to automatically retry when validation fails, **so that** I receive valid automation YAML without manual error fixing

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that YAML generation automatically retries with error context when validation fails, dramatically improving first-attempt success rates.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Wrap the existing yaml_generation_service.generate() call in a retry loop. On validation failure, construct an error-context prompt with the original request + generated YAML + validation errors, and call the LLM again. Max retries configurable (default 3). Track attempt number in response metadata.

See [Epic 67](stories/epic-67-automation-validation-loop.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ai-automation-service-new/src/services/yaml_generation_service.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add retry loop wrapper around generate() (`domains/automation-core/ai-automation-service-new/src/services/yaml_generation_service.py`)
- [ ] Add max_retries to config (`domains/automation-core/ai-automation-service-new/src/config.py`)
- [ ] Add attempt metadata to response model (`domains/automation-core/ai-automation-service-new/src/models/generation_response.py`)
- [ ] Write integration tests for retry scenarios (`tests/integration/test_yaml_retry_loop.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] yaml_generation_service.generate() wrapped in retry loop
- [ ] Max retries configurable via config (default 3)
- [ ] First passing result returned immediately
- [ ] Attempt number tracked in response metadata
- [ ] Original request preserved across retries

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 67](stories/epic-67-automation-validation-loop.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_yamlgenerationservicegenerate_wrapped_retry_loop` -- yaml_generation_service.generate() wrapped in retry loop
2. `test_ac2_max_retries_configurable_via_config_default_3` -- Max retries configurable via config (default 3)
3. `test_ac3_first_passing_result_returned_immediately` -- First passing result returned immediately
4. `test_ac4_attempt_number_tracked_response_metadata` -- Attempt number tracked in response metadata
5. `test_ac5_original_request_preserved_across_retries` -- Original request preserved across retries

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (74%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (63%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

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
