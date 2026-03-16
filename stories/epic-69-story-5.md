# Story 69.5 -- Automated Regression Investigation

<!-- docsmcp:start:user-story -->

> **As a** operator, **I want** automated investigation reports when eval alerts fire, **so that** I can quickly diagnose what caused agent quality to degrade

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that eval alert investigations are automated, reducing mean-time-to-diagnose for agent quality regressions.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

When an eval alert fires, collect 5 lowest-scoring traces, common patterns in failures, model/routing changes. Package as investigation report in health-dashboard.

See [Epic 69](stories/epic-69-agent-eval-feedback-loop.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/automation-core/ha-ai-agent-service/src/services/regression_investigator.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create RegressionInvestigator class (`domains/automation-core/ha-ai-agent-service/src/services/regression_investigator.py`)
- [ ] Implement trace collection and pattern analysis (`domains/automation-core/ha-ai-agent-service/src/services/regression_investigator.py`)
- [ ] Add report view to health-dashboard (`domains/core-platform/health-dashboard/src/components/agent-eval/InvestigationReport.tsx`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Collects 5 lowest-scoring traces from alert window
- [ ] Identifies common patterns in failing traces
- [ ] Notes model/routing changes during alert window
- [ ] Report accessible from alert in health-dashboard

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 69](stories/epic-69-agent-eval-feedback-loop.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_collects_5_lowestscoring_traces_from_alert_window` -- Collects 5 lowest-scoring traces from alert window
2. `test_ac2_identifies_common_patterns_failing_traces` -- Identifies common patterns in failing traces
3. `test_ac3_notes_modelrouting_changes_during_alert_window` -- Notes model/routing changes during alert window
4. `test_ac4_report_accessible_from_alert_healthdashboard` -- Report accessible from alert in health-dashboard

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (78%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
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
