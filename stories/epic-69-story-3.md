# Story 69.3 -- Eval-Routing Correlation Analysis

<!-- docsmcp:start:user-story -->

> **As a** operator, **I want** to see how model routing decisions correlate with evaluation outcomes, **so that** I can verify the routing strategy is working and tune thresholds

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that operators can verify the routing strategy is working by seeing how model choices correlate with evaluation outcomes.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Build a correlation pipeline joining routing decisions with eval outcomes. Track score by model, by complexity tier, cost per interaction. Surface as model comparison chart in health-dashboard.

See [Epic 69](stories/epic-69-agent-eval-feedback-loop.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ha-ai-agent-service/src/services/routing_analytics.py`
- `domains/core-platform/health-dashboard/src/components/agent-eval/ModelComparisonChart.tsx`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create InfluxDB query for routing-eval correlation (`domains/automation-core/ha-ai-agent-service/src/services/routing_analytics.py`)
- [ ] Add model comparison chart to health-dashboard (`domains/core-platform/health-dashboard/src/components/agent-eval/ModelComparisonChart.tsx`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Joins routing decisions with eval outcomes in InfluxDB
- [ ] Tracks eval score by model and by complexity tier
- [ ] Calculates cost per successful interaction
- [ ] Model comparison chart in health-dashboard

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 69](stories/epic-69-agent-eval-feedback-loop.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_joins_routing_decisions_eval_outcomes_influxdb` -- Joins routing decisions with eval outcomes in InfluxDB
2. `test_ac2_tracks_eval_score_by_model_by_complexity_tier` -- Tracks eval score by model and by complexity tier
3. `test_ac3_calculates_cost_per_successful_interaction` -- Calculates cost per successful interaction
4. `test_ac4_model_comparison_chart_healthdashboard` -- Model comparison chart in health-dashboard

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (74%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (67%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

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
