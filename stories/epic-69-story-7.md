# Story 69.7 -- Admin Configuration & Safety

<!-- docsmcp:start:user-story -->

> **As a** operator, **I want** admin API endpoints to configure routing rules and lock models, **so that** I can override adaptive routing during incidents or tune thresholds

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 1 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that operators can override adaptive routing during incidents and tune thresholds without code changes.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Expose routing configuration via admin-api: per-agent model overrides, complexity thresholds, eval score floors, alert thresholds. Lock-to-model option. Audit trail for changes.

See [Epic 69](stories/epic-69-agent-eval-feedback-loop.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/core-platform/admin-api/src/routing_config_endpoints.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add routing config endpoints to admin-api (`domains/core-platform/admin-api/src/routing_config_endpoints.py`)
- [ ] Create routing config model (`domains/core-platform/admin-api/src/models/routing_config.py`)
- [ ] Add audit logging for config changes (`domains/core-platform/admin-api/src/routing_config_endpoints.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Per-agent model override via admin-api
- [ ] Complexity threshold configuration
- [ ] Eval score floor configuration
- [ ] Lock-to-model option disables adaptive routing
- [ ] All config changes logged in audit trail

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 69](stories/epic-69-agent-eval-feedback-loop.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_peragent_model_override_via_adminapi` -- Per-agent model override via admin-api
2. `test_ac2_complexity_threshold_configuration` -- Complexity threshold configuration
3. `test_ac3_eval_score_floor_configuration` -- Eval score floor configuration
4. `test_ac4_locktomodel_option_disables_adaptive_routing` -- Lock-to-model option disables adaptive routing
5. `test_ac5_all_config_changes_logged_audit_trail` -- All config changes logged in audit trail

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (75%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (58%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

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
