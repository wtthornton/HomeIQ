# Story 68.6 -- User Configuration & Safety Guardrails

<!-- docsmcp:start:user-story -->

> **As a** smart home user, **I want** to configure what the system can do autonomously, **so that** I maintain control over automated actions in my home

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that users maintain control over autonomous actions through configurable thresholds, exclusions, and quiet hours.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Add user-facing configuration: enable/disable autonomous execution, confidence threshold, excluded device categories, quiet hours. Store in PostgreSQL. Expose via admin-api.

See [Epic 68](stories/epic-68-proactive-agent-upgrade.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/core-platform/admin-api/src/preferences_endpoints.py`
- `domains/energy-analytics/proactive-agent-service/src/config.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create user_preferences table migration (`domains/core-platform/data-api/alembic/versions/012_user_preferences.py`)
- [ ] Create UserPreferences model (`domains/core-platform/data-api/src/models/user_preferences.py`)
- [ ] Add admin-api endpoints for preferences (`domains/core-platform/admin-api/src/preferences_endpoints.py`)
- [ ] Wire preferences into proactive-agent config (`domains/energy-analytics/proactive-agent-service/src/config.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Enable/disable autonomous execution toggle
- [ ] Configurable confidence threshold (default 85)
- [ ] Excluded device categories (default: locks alarms cameras)
- [ ] Quiet hours configuration
- [ ] Stored in PostgreSQL user_preferences table
- [ ] Exposed via admin-api REST endpoints

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 68](stories/epic-68-proactive-agent-upgrade.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_enabledisable_autonomous_execution_toggle` -- Enable/disable autonomous execution toggle
2. `test_ac2_configurable_confidence_threshold_default_85` -- Configurable confidence threshold (default 85)
3. `test_ac3_excluded_device_categories_default_locks_alarms_cameras` -- Excluded device categories (default: locks alarms cameras)
4. `test_ac4_quiet_hours_configuration` -- Quiet hours configuration
5. `test_ac5_stored_postgresql_userpreferences_table` -- Stored in PostgreSQL user_preferences table
6. `test_ac6_exposed_via_adminapi_rest_endpoints` -- Exposed via admin-api REST endpoints

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (73%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (62%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

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
