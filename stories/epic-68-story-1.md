# Story 68.1 -- Observe-Reason-Act Agent Loop

<!-- docsmcp:start:user-story -->

> **As a** smart home user, **I want** my home to proactively take helpful actions based on current state, **so that** I don't have to manually trigger automations for predictable situations

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that proactive-agent-service evolves from a passive cron-triggered suggestion generator into an autonomous observe-reason-act loop capable of routing actions based on confidence and risk.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Replace the current cron-trigger → single-LLM-call → delegate pattern with an observe-reason-act loop. Observe: aggregate current home state. Reason: LLM evaluates with structured output. Act: route based on confidence/risk thresholds.

See [Epic 68](stories/epic-68-proactive-agent-upgrade.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/energy-analytics/proactive-agent-service/src/services/agent_loop.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create ObserveReasonActLoop class (`domains/energy-analytics/proactive-agent-service/src/services/agent_loop.py`)
- [ ] Implement observe phase with state aggregation (`domains/energy-analytics/proactive-agent-service/src/services/observe.py`)
- [ ] Implement reason phase with structured LLM output (`domains/energy-analytics/proactive-agent-service/src/services/reason.py`)
- [ ] Implement act phase with routing logic (`domains/energy-analytics/proactive-agent-service/src/services/act.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Observe phase aggregates entity state and weather and energy and time
- [ ] Reason phase calls LLM with structured output schema
- [ ] LLM returns action and confidence and risk_level and reasoning
- [ ] Act phase routes based on confidence/risk thresholds
- [ ] Loop runs on configurable schedule (default 15 minutes)

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 68](stories/epic-68-proactive-agent-upgrade.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_observe_phase_aggregates_entity_state_weather_energy_time` -- Observe phase aggregates entity state and weather and energy and time
2. `test_ac2_reason_phase_calls_llm_structured_output_schema` -- Reason phase calls LLM with structured output schema
3. `test_ac3_llm_returns_action_confidence_risklevel_reasoning` -- LLM returns action and confidence and risk_level and reasoning
4. `test_ac4_act_phase_routes_based_on_confidencerisk_thresholds` -- Act phase routes based on confidence/risk thresholds
5. `test_ac5_loop_runs_on_configurable_schedule_default_15_minutes` -- Loop runs on configurable schedule (default 15 minutes)

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (70%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
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
- [ ] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
