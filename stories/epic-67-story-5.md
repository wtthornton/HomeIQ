# Story 67.5 -- Metrics & Observability

<!-- docsmcp:start:user-story -->

> **As a** operator, **I want** Prometheus metrics tracking YAML generation success rates and retry counts, **so that** I can monitor validation loop effectiveness and detect degradation

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 1 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that operators can monitor validation loop effectiveness through Prometheus metrics and detect quality degradation.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Add Prometheus metrics: yaml_generation_first_pass_rate, yaml_generation_retries_total, yaml_generation_latency_seconds (histogram with attempt label).

See [Epic 67](stories/epic-67-automation-validation-loop.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ai-automation-service-new/src/services/yaml_generation_service.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add Prometheus metrics to generation service (`domains/automation-core/ai-automation-service-new/src/services/yaml_generation_service.py`)
- [ ] Verify Prometheus scrape config includes service (`domains/core-platform/compose.yml`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] yaml_generation_first_pass_rate metric exposed
- [ ] yaml_generation_retries_total counter exposed
- [ ] yaml_generation_latency_seconds histogram with attempt label
- [ ] Metrics scraped by existing Prometheus config

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 67](stories/epic-67-automation-validation-loop.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_yamlgenerationfirstpassrate_metric_exposed` -- yaml_generation_first_pass_rate metric exposed
2. `test_ac2_yamlgenerationretriestotal_counter_exposed` -- yaml_generation_retries_total counter exposed
3. `test_ac3_yamlgenerationlatencyseconds_histogram_attempt_label` -- yaml_generation_latency_seconds histogram with attempt label
4. `test_ac4_metrics_scraped_by_existing_prometheus_config` -- Metrics scraped by existing Prometheus config

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (71%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
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
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
