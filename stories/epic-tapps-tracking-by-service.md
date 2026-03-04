---
epic: tapps-tracking-by-service
priority: high
status: complete
estimated_duration: 3-4 weeks
risk_level: low
source: docs/TAPPS_TOOL_PRIORITY.md, TappsMCP pipeline
type: quality
---

# Epic: TAPPS Quality Pipeline Tracking by Service

**Status:** Complete
**Priority:** High (P1)
**Duration:** 3–4 weeks
**Risk Level:** Low
**Source:** [TAPPS Tool Priority](docs/TAPPS_TOOL_PRIORITY.md), TappsMCP pipeline
**Affects:** All 9 domain groups (50 services) + libs (5 packages)

## Context

HomeIQ uses TappsMCP for quality gates, scoring, and security scanning. To improve visibility and accountability, we need **per-service tracking** of TAPPS adoption and quality baselines. This epic establishes a tracking framework and breaks down baseline capture and reporting **by service** (by domain group), so each area has clear ownership and targets.

**Goals:**
- Establish a single place to record per-service TAPPS baseline (score, gate pass/fail, last run).
- Run `tapps_validate_changed` (or per-directory scoring) per domain and record results.
- Enforce Tier 1 services (websocket-ingestion, data-api, admin-api, health-dashboard) at score ≥80; others at ≥70.
- Produce a rollup view (e.g. `docs/` or `implementation/`) for at-a-glance status.

**Reference:** [Service Groups](docs/architecture/service-groups.md) — 9 domains, 50 services.

---

## Stories

### Story 0: Tracking Framework and Baseline Format

**Priority:** High | **Estimate:** 4h | **Risk:** Low

**Problem:** No standard place or format to record TAPPS results per service. We need a repeatable way to run TAPPS per domain and persist baselines.

**Acceptance Criteria:**
- [ ] Define baseline format: service name, domain, score (or min/mean), gate pass/fail, security issues count, last run date, optional file path list. (e.g. JSON or Markdown table in `implementation/verification/` or `reports/quality/`.)
- [ ] Document how to run TAPPS for a single domain (e.g. `tapps_validate_changed` with scope limited to `domains/<domain>/` or per-service `tapps_quick_check` on each Python file).
- [ ] Add one sample baseline file (one domain) as template; link from [docs/TAPPS_TOOL_PRIORITY.md](docs/TAPPS_TOOL_PRIORITY.md) or docs/README.md.
- [ ] Optional: Add a small script or GitHub Action that runs TAPPS per domain and appends to baseline (so Stories 1–10 can consume it).

---

### Story 1: core-platform (6 services)

**Priority:** High | **Estimate:** 6h | **Risk:** Low

**Scope:** `domains/core-platform/` — influxdb (config only), data-api, websocket-ingestion, admin-api, health-dashboard (Python tooling if any), data-retention.

**Problem:** Tier 1 services (data-api, websocket-ingestion, admin-api, health-dashboard) must meet score ≥80 and pass quality gate. No baseline is recorded today.

**Acceptance Criteria:**
- [ ] Run TAPPS (e.g. `tapps_validate_changed` scoped to `domains/core-platform/` or equivalent per-service checks) for all Python-bearing services in core-platform.
- [ ] Record baseline: per-service score, gate pass/fail, security issue count in the tracking format from Story 0.
- [ ] For Tier 1 services (data-api, websocket-ingestion, admin-api, health-dashboard): achieve or document path to score ≥80; fix any blocking security findings.
- [ ] Update tracking artifact (e.g. `implementation/verification/TAPPS_BASELINE.md` or JSON) with core-platform section.

---

### Story 2: data-collectors (8 services)

**Priority:** Medium | **Estimate:** 5h | **Risk:** Low

**Scope:** `domains/data-collectors/` — weather-api, smart-meter-service, sports-api, air-quality-service, carbon-intensity-service, electricity-pricing-service, calendar-service, log-aggregator.

**Problem:** Data collectors are stateless and numerous; we need a recorded baseline and gate pass for each.

**Acceptance Criteria:**
- [ ] Run TAPPS for `domains/data-collectors/` (or each service dir); record per-service score, gate pass/fail, security count.
- [ ] Fix or document any gate failures; target score ≥70 per service.
- [ ] Update tracking artifact with data-collectors section.

---

### Story 3: ml-engine (10 services)

**Priority:** High | **Estimate:** 8h | **Risk:** Low

**Scope:** `domains/ml-engine/` — ai-core-service, openvino-service, ml-service, ner-service, openai-service, rag-service, ai-training-service, device-intelligence-service, nlp-fine-tuning, model-prep.

**Problem:** ML services have heavier dependencies and complexity; baseline and security scan are critical.

**Acceptance Criteria:**
- [ ] Run TAPPS for `domains/ml-engine/`; record per-service baseline (score, gate, security).
- [ ] Run `tapps_security_scan` on auth/API-facing modules (e.g. openai-service, ai-core-service); address or document findings.
- [ ] Target score ≥70; update tracking artifact with ml-engine section.

---

### Story 4: automation-core (7 services)

**Priority:** High | **Estimate:** 8h | **Risk:** Low

**Scope:** `domains/automation-core/` — ha-ai-agent-service, ai-automation-service-new, ai-query-service, automation-linter, yaml-validation-service, ai-code-executor, automation-trace-service.

**Problem:** Automation-core is the most actively developed domain; keeping a baseline and gate pass here prevents regressions.

**Acceptance Criteria:**
- [ ] Run TAPPS for `domains/automation-core/`; record per-service baseline.
- [ ] Fix or document gate failures; target score ≥70 (consider ≥80 for ha-ai-agent-service and ai-automation-service-new as critical paths).
- [ ] Update tracking artifact with automation-core section.

---

### Story 5: blueprints (4 services)

**Priority:** Medium | **Estimate:** 4h | **Risk:** Low

**Scope:** `domains/blueprints/` — blueprint-index, blueprint-suggestion-service, rule-recommendation-ml, automation-miner.

**Acceptance Criteria:**
- [ ] Run TAPPS for `domains/blueprints/`; record per-service baseline (score, gate, security).
- [ ] Resolve or document any Bandit/security findings (e.g. B104/B112 as in Epic 9); target score ≥70.
- [ ] Update tracking artifact with blueprints section.

---

### Story 6: energy-analytics (3 services)

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

**Scope:** `domains/energy-analytics/` — energy-correlator, energy-forecasting, proactive-agent-service.

**Acceptance Criteria:**
- [ ] Run TAPPS for `domains/energy-analytics/`; record per-service baseline.
- [ ] Fix or document gate failures; target score ≥70.
- [ ] Update tracking artifact with energy-analytics section.

---

### Story 7: device-management (8 services)

**Priority:** Medium | **Estimate:** 5h | **Risk:** Low

**Scope:** `domains/device-management/` — device-health-monitor, device-context-classifier, device-setup-assistant, device-database-client, device-recommender, activity-recognition, activity-writer, ha-setup-service.

**Acceptance Criteria:**
- [ ] Run TAPPS for `domains/device-management/`; record per-service baseline.
- [ ] Target score ≥70; update tracking artifact with device-management section.

---

### Story 8: pattern-analysis (2 services)

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

**Scope:** `domains/pattern-analysis/` — ai-pattern-service, api-automation-edge.

**Acceptance Criteria:**
- [ ] Run TAPPS for `domains/pattern-analysis/`; record per-service baseline.
- [ ] Target score ≥70; update tracking artifact with pattern-analysis section.

---

### Story 9: frontends (4 services)

**Priority:** Medium | **Estimate:** 4h | **Risk:** Low

**Scope:** `domains/frontends/` — ai-automation-ui, observability-dashboard, health-dashboard, jaeger. (Only Python-bearing services or configs are in scope for TAPPS; e.g. observability-dashboard Streamlit app, any backend helpers.)

**Problem:** Frontends are mostly TypeScript/React; TAPPS applies to Python parts (Streamlit, scripts, tooling).

**Acceptance Criteria:**
- [ ] Run TAPPS for Python code under `domains/frontends/` (e.g. observability-dashboard, any shared Python); record baseline per service that has Python.
- [ ] If a service has no Python, record “N/A (TypeScript)” in tracking artifact.
- [ ] Update tracking artifact with frontends section.

---

### Story 10: Shared libraries (libs)

**Priority:** High | **Estimate:** 6h | **Risk:** Low

**Scope:** `libs/` — homeiq-resilience, homeiq-data, homeiq-patterns, homeiq-ha, homeiq-observability.

**Problem:** Libs are used by many services; their quality bar should be high (≥80 preferred). Epic 9 already improved homeiq-ha; we need a recorded baseline for all libs and ongoing tracking.

**Acceptance Criteria:**
- [ ] Run TAPPS for each lib under `libs/`; record per-package baseline (score, gate, security).
- [ ] Target score ≥80 for libs (or ≥70 with documented exception); fix or document gate failures.
- [ ] Update tracking artifact with libs section.

---

### Story 11: Rollup Report and Docs

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

**Problem:** Baselines are stored per domain; we need a single rollup for status checks and linking from docs.

**Acceptance Criteria:**
- [ ] Create a rollup view (e.g. `implementation/verification/TAPPS_BASELINE.md` or `reports/quality/TAPPS_ROLLUP.md`) that aggregates all domain + lib baselines: table with domain, service count, pass/fail count, min/mean score, last run date.
- [ ] Add “TAPPS baseline” or “Quality baseline” link to [docs/README.md](docs/README.md) and [docs/TAPPS_TOOL_PRIORITY.md](docs/TAPPS_TOOL_PRIORITY.md).
- [ ] Document how to refresh the rollup (re-run Story 0 script or per-domain runs, then regenerate rollup).

---

## Summary by Domain

| Story | Domain / Scope        | Services | Est. |
|-------|------------------------|----------|------|
| 0     | Tracking framework     | —        | 4h   |
| 1     | core-platform          | 6        | 6h   |
| 2     | data-collectors        | 8        | 5h   |
| 3     | ml-engine              | 10       | 8h   |
| 4     | automation-core        | 7        | 8h   |
| 5     | blueprints             | 4        | 4h   |
| 6     | energy-analytics       | 3        | 3h   |
| 7     | device-management      | 8        | 5h   |
| 8     | pattern-analysis       | 2        | 2h   |
| 9     | frontends              | 4        | 4h   |
| 10    | libs                   | 5        | 6h   |
| 11    | Rollup report & docs   | —        | 3h   |
| **Total** |                       | **50 + 5** | **~58h** |

---

## Dependencies

- **Story 0** must be done first (defines format and how to run).
- **Stories 1–10** can be parallelized by domain after Story 0.
- **Story 11** depends on at least one baseline from each domain + libs (Stories 1–10).

## Related

- [TAPPS Tool Priority](docs/TAPPS_TOOL_PRIORITY.md)
- [Epic 9: TAPPS Quality Gate Compliance](epic-tapps-quality-gate-compliance.md)
- [Service Groups](docs/architecture/service-groups.md)
