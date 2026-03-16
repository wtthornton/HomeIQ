# Story 69.4 -- Eval Degradation Alerting

<!-- docsmcp:start:user-story -->

> **As a** operator, **I want** automated alerts when agent evaluation scores degrade, **so that** quality issues are caught before users notice degradation

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that agent quality degradation is caught automatically rather than relying on manual dashboard monitoring.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Alert when rolling 24h average drops >10% vs 7-day baseline, or any eval dimension drops below floor (50/100). Route to health-dashboard and optional webhook.

See [Epic 69](stories/epic-69-agent-eval-feedback-loop.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ha-ai-agent-service/src/services/eval_alert_monitor.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create EvalAlertMonitor class (`domains/automation-core/ha-ai-agent-service/src/services/eval_alert_monitor.py`)
- [ ] Implement rolling average comparison (`domains/automation-core/ha-ai-agent-service/src/services/eval_alert_monitor.py`)
- [ ] Add notification panel integration (`domains/core-platform/health-dashboard/src/components/agent-eval/EvalAlertPanel.tsx`)
- [ ] Add webhook dispatcher (`domains/automation-core/ha-ai-agent-service/src/services/eval_alert_monitor.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Alert triggers on >10% drop in 24h rolling average
- [ ] Alert triggers when any dimension drops below 50/100
- [ ] Payload includes agent name and dimension and score trend and trace IDs
- [ ] Routes to health-dashboard notification panel
- [ ] Optional webhook for Slack/email

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 69](stories/epic-69-agent-eval-feedback-loop.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_alert_triggers_on_10_drop_24h_rolling_average` -- Alert triggers on >10% drop in 24h rolling average
2. `test_ac2_alert_triggers_any_dimension_drops_below_50100` -- Alert triggers when any dimension drops below 50/100
3. `test_ac3_payload_includes_agent_name_dimension_score_trend_trace_ids` -- Payload includes agent name and dimension and score trend and trace IDs
4. `test_ac4_routes_healthdashboard_notification_panel` -- Routes to health-dashboard notification panel
5. `test_ac5_optional_webhook_slackemail` -- Optional webhook for Slack/email

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (72%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (60%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

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
