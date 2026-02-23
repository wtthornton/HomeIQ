---
epic: agent-eval-observability
priority: medium
status: planned
estimated_duration: 3-4 weeks
risk_level: medium
source: Tango Workspace Reservation Agent Evaluation Framework (Pattern D — Phase 4)
---

# Epic: Agent Evaluation Observability & Monitoring

**Status:** Planned
**Priority:** Medium
**Duration:** 3–4 weeks
**Risk Level:** Medium
**Reference:** Tango Workspace Reservation Agent Evaluation Framework PDF (Priority & Monitoring, Summary Matrix)

## Overview

Build the observability layer for the Agent Evaluation Framework — a monitoring dashboard, scheduled evaluation runs, historical trend tracking, and alerting integration. This makes evaluation a continuous operational practice rather than a one-time assessment. The health-dashboard (port 3000) is extended with an Agent Evaluation tab showing the Summary Matrix, trends, and alerts for all agents.

**This epic delivers:**
1. Scheduled evaluation pipeline (daily/weekly/monthly per priority matrix)
2. Historical score storage and trend analysis
3. Health-dashboard UI for evaluation results
4. Alert integration for threshold violations
5. API endpoints for programmatic access to evaluation data

## Code Location & Sharing Strategy

This epic spans **3 locations** — shared backend, data-api service, and health-dashboard:

```
SHARED BACKEND (libs/homeiq-patterns/src/homeiq_patterns/evaluation/) — scheduler, store, alerts:
├── scheduler.py                          ← EvaluationScheduler (runs eval pipelines)
├── store.py                              ← EvaluationStore (InfluxDB + SQLite writes)
└── alerts.py                             ← AlertEngine (threshold checking + lifecycle)

DATA-API SERVICE (domains/core-platform/data-api/src/) — API endpoints:
├── evaluation_endpoints.py               ← NEW FastAPI router for /api/v1/evaluations/*
│                                            (follows existing pattern: health_endpoints.py,
│                                             metrics_endpoints.py, sports_endpoints.py)
└── main.py                               ← register evaluation router (1 line)

HEALTH-DASHBOARD (domains/core-platform/health-dashboard/src/components/) — React UI:
├── evaluation/                           ← NEW subdirectory (62 components already exist
│   │                                        in components/ — use subdirectory to organize)
│   ├── AgentEvaluationTab.tsx            ← main tab container
│   ├── SummaryMatrix.tsx                 ← 5-level pyramid display
│   ├── ScoreTrendChart.tsx               ← line charts over time
│   ├── SessionTraceViewer.tsx            ← session detail viewer
│   └── EvalAlertBanner.tsx               ← alert banner (existing AlertBanner.tsx pattern)
```

**Follows existing conventions:**
- `data-api` already has `*_endpoints.py` pattern (`health_endpoints.py`, `sports_endpoints.py`, etc.)
- `health-dashboard` already has 62+ components; new evaluation components go in a subdirectory
- InfluxDB writes follow existing `influxdb_query_client.py` patterns in `shared/`
- SQLite storage follows existing `database.py` pattern in `data-api`

## Objectives

1. Automate evaluation runs on a configurable schedule matching each agent's priority matrix
2. Store evaluation history in InfluxDB (time-series scores) and SQLite (session details, reports)
3. Extend the existing health-dashboard with an Agent Evaluation section
4. Surface threshold violations as alerts visible in the dashboard and via notifications
5. Provide API endpoints for evaluation data so external tools can consume results

## Success Criteria

- [ ] Evaluation scheduler runs evaluations at configured frequency (daily P0, weekly P1, monthly P2)
- [ ] Historical scores stored with timestamps — supports trend queries (last 7 days, 30 days, 90 days)
- [ ] Health-dashboard shows Summary Matrix per agent with color-coded pass/fail
- [ ] Score trends visualized as line charts per evaluator over time
- [ ] Threshold violations generate alerts visible in dashboard
- [ ] API endpoints: `GET /api/v1/evaluations/{agent}`, `GET /api/v1/evaluations/{agent}/trends`
- [ ] At least 2 weeks of historical data collected before declaring operational

---

## User Stories

### Story 1: Evaluation Scheduler Service

**As a** platform operator
**I want** a scheduler that automatically runs evaluations against recent sessions at configurable intervals
**So that** evaluation scores are always current without manual intervention

**Acceptance Criteria:**
- [ ] `EvaluationScheduler` class in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/scheduler.py`
- [ ] Reads `priority_matrix` from each agent's `AgentEvalConfig` to determine frequency
- [ ] Schedules: P0 metrics daily (L1 Goal Success, L2 Tool Selection, L3 Category/Date), P1 weekly (L3 All Params, L4 Correctness/Faithfulness), P2 monthly (L4 Helpfulness/Conciseness), P3 monthly (L5 Safety)
- [ ] Each run: queries recent `SessionTrace` objects from storage, runs configured evaluators, stores results
- [ ] Configurable batch size: how many sessions to evaluate per run (default: 20 most recent)
- [ ] Supports manual trigger: `POST /api/v1/evaluations/{agent}/trigger`
- [ ] Graceful handling of empty session stores (skip with warning, don't fail)
- [ ] Logs run metadata: start time, sessions evaluated, evaluators run, duration, alerts triggered
- [ ] Unit tests for scheduler logic with mock session stores

**Story Points:** 5
**Dependencies:** Epic: Agent-Specific Eval Configs (all agents instrumented)
**Affected Services:** libs/homeiq-patterns/src/homeiq_patterns/evaluation, data-api (8006)

---

### Story 2: Evaluation History Storage

**As a** platform operator
**I want** evaluation results stored with timestamps so I can query historical trends
**So that** I can see whether agent quality is improving or degrading over time

**Acceptance Criteria:**
- [ ] `EvaluationStore` class in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/store.py`
- [ ] Time-series scores written to InfluxDB:
  - Measurement: `agent_evaluation`
  - Tags: `agent_name`, `evaluator_name`, `level` (L1-L5)
  - Fields: `score` (float), `label` (string), `passed` (bool)
  - Timestamp: evaluation run time
- [ ] Session-level details stored in SQLite (via data-api):
  - Table: `evaluation_results` — `id`, `session_id`, `agent_name`, `evaluator_name`, `level`, `score`, `label`, `explanation`, `timestamp`
  - Table: `evaluation_runs` — `id`, `agent_name`, `run_timestamp`, `sessions_evaluated`, `total_evaluations`, `alerts_triggered`
- [ ] Retention: InfluxDB scores kept for 90 days, SQLite details kept for 30 days
- [ ] Query methods: `get_scores(agent, evaluator, start, end)`, `get_trends(agent, period)`, `get_latest_report(agent)`
- [ ] Unit tests for storage write and query operations

**Story Points:** 5
**Dependencies:** Story 1 (Scheduler produces results to store)
**Affected Services:** data-api (8006), InfluxDB (8086)

---

### Story 3: Evaluation API Endpoints

**As a** developer or monitoring tool
**I want** REST API endpoints to query evaluation results, trends, and alerts
**So that** I can integrate evaluation data into existing dashboards, alerting systems, or CI/CD pipelines

**Acceptance Criteria:**
- [ ] Evaluation API added to data-api service (8006) or as standalone FastAPI router
- [ ] Endpoints:
  - `GET /api/v1/evaluations` — list all agents with latest scores
  - `GET /api/v1/evaluations/{agent}` — latest full `EvaluationReport` for an agent
  - `GET /api/v1/evaluations/{agent}/history` — paginated historical results (params: `start_date`, `end_date`, `evaluator`, `level`)
  - `GET /api/v1/evaluations/{agent}/trends` — aggregated score trends (params: `period=7d|30d|90d`, `evaluator`)
  - `GET /api/v1/evaluations/{agent}/alerts` — active threshold violations
  - `POST /api/v1/evaluations/{agent}/trigger` — manual evaluation trigger
- [ ] All endpoints return JSON matching `EvaluationReport` / `BatchReport` models
- [ ] Pagination support for history endpoint (default: 50 per page)
- [ ] Health check: `GET /api/v1/evaluations/health` — scheduler status, last run times
- [ ] Unit tests for all endpoints

**Story Points:** 5
**Dependencies:** Story 2 (Store to query from)
**Affected Services:** data-api (8006) or new evaluation-api service

---

### Story 4: Health Dashboard — Agent Evaluation Tab

**As a** platform operator viewing the health dashboard
**I want** an Agent Evaluation tab that shows the Summary Matrix for each agent with color-coded pass/fail indicators
**So that** I can see agent quality at a glance alongside system health

**Acceptance Criteria:**
- [ ] New tab "Agent Evaluation" in health-dashboard (React, port 3000)
- [ ] Agent selector: dropdown or tabs for each registered agent
- [ ] Summary Matrix view per agent matching Tango format:
  - Level 1 (Outcome): Goal Success Rate with pass/fail indicator
  - Level 2 (Path): Tool Selection, Tool Sequence with pass/fail
  - Level 3 (Details): Parameter accuracy metrics with pass/fail
  - Level 4 (Quality): Score bars for each quality evaluator (0-1 scale)
  - Level 5 (Safety): Pass/fail indicators
- [ ] Color coding: green (>= threshold), yellow (within 5% of threshold), red (< threshold)
- [ ] Last evaluation timestamp shown per agent
- [ ] Click any metric to see detailed evaluation history for that evaluator
- [ ] Data sourced from evaluation API endpoints (Story 3)
- [ ] Responsive layout consistent with existing health-dashboard design

**Story Points:** 5
**Dependencies:** Story 3 (API endpoints)
**Affected Services:** health-dashboard (3000)

---

### Story 5: Health Dashboard — Score Trend Charts

**As a** platform operator
**I want** line charts showing evaluation score trends over time for each evaluator
**So that** I can see whether agent quality is improving or degrading and correlate changes with deployments

**Acceptance Criteria:**
- [ ] Trend chart component in health-dashboard
- [ ] X-axis: time (configurable: 7 days, 30 days, 90 days)
- [ ] Y-axis: score (0-1 or 0-100%)
- [ ] Multiple evaluators plotted on same chart with legend
- [ ] Threshold line shown as horizontal dashed line for each metric
- [ ] Hover tooltip shows: date, evaluator name, score, label, sessions evaluated
- [ ] Chart library: use existing health-dashboard charting library (recharts or similar)
- [ ] Filter by level (L1-L5) or individual evaluator
- [ ] Data sourced from `GET /api/v1/evaluations/{agent}/trends`
- [ ] Handles missing data points gracefully (gaps in chart, not interpolated)

**Story Points:** 5
**Dependencies:** Story 4 (Dashboard tab exists), Story 3 (API endpoints)
**Affected Services:** health-dashboard (3000)

---

### Story 6: Alert System for Threshold Violations

**As a** platform operator
**I want** alerts triggered when evaluation scores drop below configured thresholds
**So that** I'm notified immediately when an agent's quality degrades and can investigate before users are impacted

**Acceptance Criteria:**
- [ ] `AlertEngine` class in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/alerts.py`
- [ ] Checks scores against `thresholds` from `AgentEvalConfig` after each evaluation run
- [ ] `Alert` model: `agent_name`, `evaluator_name`, `level`, `metric`, `threshold`, `actual_score`, `priority`, `timestamp`, `status` (active | acknowledged | resolved)
- [ ] Alert lifecycle: created when threshold violated → active until score recovers or acknowledged
- [ ] Deduplication: same alert not created repeatedly for the same ongoing violation
- [ ] Alert display in health-dashboard: banner at top of Agent Evaluation tab with count badge
- [ ] Alert list view: sortable by priority, agent, level, timestamp
- [ ] Alert acknowledgement: operator can mark alert as acknowledged with note
- [ ] Optional: webhook/notification integration point (extensible — future story)
- [ ] Alert history queryable via API: `GET /api/v1/evaluations/{agent}/alerts?status=active`
- [ ] Unit tests for alert creation, deduplication, lifecycle

**Story Points:** 5
**Dependencies:** Story 2 (Score storage), Story 3 (API endpoints)
**Affected Services:** libs/homeiq-patterns/src/homeiq_patterns/evaluation, health-dashboard (3000)

---

### Story 7: Session Trace Viewer

**As a** platform operator investigating a low evaluation score
**I want** to view the full session trace (user messages, agent responses, tool calls) for any evaluated session
**So that** I can understand exactly what went wrong and debug the agent's behavior

**Acceptance Criteria:**
- [ ] Session Trace viewer component in health-dashboard
- [ ] Accessible from: evaluation results table (click session ID to view trace)
- [ ] Displays:
  - Conversation timeline: user messages and agent responses in order
  - Tool calls: tool name, parameters (collapsible JSON), result (collapsible), latency
  - Evaluation results: per-turn evaluator scores with explanations
- [ ] Syntax highlighting for YAML content in tool call params/results
- [ ] Evaluator explanation shown inline next to the relevant turn/tool call
- [ ] Copy session trace as JSON for external analysis
- [ ] Data sourced from SQLite session store + evaluation results
- [ ] Responsive layout — handles long sessions without performance issues

**Story Points:** 5
**Dependencies:** Story 4 (Dashboard tab), Epic: Agent-Specific Configs (Story 4 — SessionTracer storing traces)
**Affected Services:** health-dashboard (3000)

---

### Story 8: Documentation and Operational Runbook

**As a** platform operator
**I want** documentation explaining how to operate the evaluation system — interpreting scores, responding to alerts, adding new agents, and troubleshooting
**So that** anyone on the team can manage agent quality monitoring independently

**Acceptance Criteria:**
- [ ] Operational runbook: `docs/operations/agent-evaluation-runbook.md`
- [ ] Sections:
  - Overview: what the evaluation framework measures and why
  - Dashboard guide: how to read the Summary Matrix, trends, and alerts
  - Alert response: for each priority level, what to do when an alert fires
  - Adding a new agent: step-by-step guide (create config, add SessionTracer, run baseline)
  - Troubleshooting: common issues (no sessions captured, LLM judge failures, stale data)
  - Threshold tuning: how to adjust thresholds based on operational experience
- [ ] Updated `docs/deployment/DEPLOYMENT_RUNBOOK.md` with evaluation service references
- [ ] Updated `libs/homeiq-patterns/src/homeiq_patterns/evaluation/README.md` with operational links

**Story Points:** 2
**Dependencies:** Stories 1-7
**Affected Services:** None (documentation only)

---

## Dependencies

```
Epic: Agent-Specific Eval Configs ──> All stories in this epic

Story 1 (Scheduler) ──> Story 2 (History Storage)
Story 2 (Storage)   ──> Story 3 (API Endpoints)
Story 3 (API)       ──┬──> Story 4 (Dashboard Summary Matrix)
                      ├──> Story 5 (Trend Charts)
                      └──> Story 6 (Alert System)
Story 4 (Dashboard) ──> Story 7 (Session Trace Viewer)
Stories 1-7 ──────────> Story 8 (Documentation)
```

## Suggested Execution Order

1. **Story 1** – Evaluation Scheduler (produces evaluation results)
2. **Story 2** – History Storage (persists results for queries)
3. **Stories 3, 6** – API Endpoints and Alert System (can be parallelized)
4. **Story 4** – Dashboard Summary Matrix tab
5. **Stories 5, 7** – Trend Charts and Session Trace Viewer (can be parallelized)
6. **Story 8** – Documentation and Runbook

## Implementation Artifacts

| Artifact | Path | Shared? |
|----------|------|---------|
| **Shared Backend** | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/` | 100% Shared |
| Evaluation Scheduler | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/scheduler.py` | 100% Shared |
| Evaluation Store | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/store.py` | 100% Shared |
| Alert Engine | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/alerts.py` | 100% Shared |
| **Data API (1 new file + 1 line wiring)** | `domains/core-platform/data-api/src/` | Service-specific |
| Evaluation Endpoints | `domains/core-platform/data-api/src/evaluation_endpoints.py` | data-api only |
| Main.py router registration | `domains/core-platform/data-api/src/main.py` | 1 line added |
| **Dashboard (5 new components)** | `domains/core-platform/health-dashboard/src/components/evaluation/` | health-dashboard only |
| AgentEvaluationTab | `domains/core-platform/health-dashboard/src/components/evaluation/AgentEvaluationTab.tsx` | health-dashboard only |
| SummaryMatrix | `domains/core-platform/health-dashboard/src/components/evaluation/SummaryMatrix.tsx` | health-dashboard only |
| ScoreTrendChart | `domains/core-platform/health-dashboard/src/components/evaluation/ScoreTrendChart.tsx` | health-dashboard only |
| SessionTraceViewer | `domains/core-platform/health-dashboard/src/components/evaluation/SessionTraceViewer.tsx` | health-dashboard only |
| EvalAlertBanner | `domains/core-platform/health-dashboard/src/components/evaluation/EvalAlertBanner.tsx` | health-dashboard only |
| **Documentation** | | |
| Operational Runbook | `docs/operations/agent-evaluation-runbook.md` | Docs |
| **Unit Tests** | `libs/homeiq-patterns/tests/test_evaluation/` | 100% Shared |
| Scheduler Tests | `libs/homeiq-patterns/tests/test_evaluation/test_scheduler.py` | 100% Shared |
| Store Tests | `libs/homeiq-patterns/tests/test_evaluation/test_store.py` | 100% Shared |
| Alert Tests | `libs/homeiq-patterns/tests/test_evaluation/test_alerts.py` | 100% Shared |

## References

- Tango Workspace Reservation Agent Evaluation Framework (PDF — Priority & Monitoring section)
- [Epic: Agent Evaluation Foundation](epic-agent-evaluation-foundation.md) (Phase 1 — framework)
- [Epic: Built-in Evaluator Library](epic-builtin-evaluator-library.md) (Phase 2 — evaluators)
- [Epic: Agent-Specific Evaluation Configs](epic-agent-specific-eval-configs.md) (Phase 3 — configs)
- [Health Dashboard](../domains/core-platform/health-dashboard/) (existing dashboard to extend)
- [Data API](../domains/core-platform/data-api/) (existing API to extend)
