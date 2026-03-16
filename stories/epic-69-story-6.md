# Story 69.6 -- Cost Tracking & Reporting

<!-- docsmcp:start:user-story -->

> **As a** operator, **I want** OpenAI cost tracking per model per agent per day, **so that** I can measure savings from adaptive routing and catch cost spikes

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that OpenAI costs are tracked and compared against baseline, proving the ROI of adaptive routing.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Track costs per model per agent per day. Compare baseline vs adaptive cost. Surface monthly savings in health-dashboard. Alert on cost spikes >50% above 7-day average.

See [Epic 69](stories/epic-69-agent-eval-feedback-loop.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ha-ai-agent-service/src/services/cost_tracker.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create CostTracker class (`domains/automation-core/ha-ai-agent-service/src/services/cost_tracker.py`)
- [ ] Add cost dashboard widget (`domains/core-platform/health-dashboard/src/components/agent-eval/CostTracker.tsx`)
- [ ] Implement cost spike alerting (`domains/automation-core/ha-ai-agent-service/src/services/cost_tracker.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Tracks cost per model per agent per day
- [ ] Baseline vs adaptive cost comparison
- [ ] Monthly savings estimate in health-dashboard
- [ ] Alert on cost spike >50% above 7-day average

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 69](stories/epic-69-agent-eval-feedback-loop.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_tracks_cost_per_model_per_agent_per_day` -- Tracks cost per model per agent per day
2. `test_ac2_baseline_vs_adaptive_cost_comparison` -- Baseline vs adaptive cost comparison
3. `test_ac3_monthly_savings_estimate_healthdashboard` -- Monthly savings estimate in health-dashboard
4. `test_ac4_alert_on_cost_spike_50_above_7day_average` -- Alert on cost spike >50% above 7-day average

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (65%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
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
