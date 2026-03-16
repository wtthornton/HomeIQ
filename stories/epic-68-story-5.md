# Story 68.5 -- Feedback Loop — Outcome Recording

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** every suggestion outcome recorded in Memory Brain, **so that** the confidence scoring improves over time from real user behavior

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that every suggestion outcome is recorded in Memory Brain, enabling the confidence scoring engine to improve over time from real user behavior.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Record every suggestion outcome in Memory Brain: accepted, rejected, auto-executed, auto-executed-undone. Update preference scores per action type, time slot, and context.

See [Epic 68](stories/epic-68-proactive-agent-upgrade.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/energy-analytics/proactive-agent-service/src/services/outcome_recorder.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create OutcomeRecorder class (`domains/energy-analytics/proactive-agent-service/src/services/outcome_recorder.py`)
- [ ] Implement memory save with outcome metadata (`domains/energy-analytics/proactive-agent-service/src/services/outcome_recorder.py`)
- [ ] Add retry/queue for Memory Brain unavailability (`domains/energy-analytics/proactive-agent-service/src/services/outcome_recorder.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Records accepted/rejected/auto-executed/undone outcomes
- [ ] Updates preference scores per action type and time slot
- [ ] Uses homeiq-memory TTL (preference 60d and outcome 30d)
- [ ] Handles Memory Brain unavailability without data loss

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 68](stories/epic-68-proactive-agent-upgrade.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_records_acceptedrejectedautoexecutedundone_outcomes` -- Records accepted/rejected/auto-executed/undone outcomes
2. `test_ac2_updates_preference_scores_per_action_type_time_slot` -- Updates preference scores per action type and time slot
3. `test_ac3_uses_homeiqmemory_ttl_preference_60d_outcome_30d` -- Uses homeiq-memory TTL (preference 60d and outcome 30d)
4. `test_ac4_handles_memory_brain_unavailability_without_data_loss` -- Handles Memory Brain unavailability without data loss

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (72%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
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
