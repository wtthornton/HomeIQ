---
epic: production-deployment
priority: high
status: open
estimated_duration: 2 weeks
risk_level: high
source: phase-5-deployment-plan.md, rebuild-status.md
---

# Epic: Production Deployment (Phase 5 + Phase 6)

**Status:** Open
**Priority:** High (P1)
**Duration:** 2 weeks (5-day rollout + 5-day validation)
**Risk Level:** High — 50 microservices + 3 frontends deployed to production
**Predecessor:** Epics frontend-security-hardening, backend-completion (Story 6.5)
**Affects:** All 50 services + 3 frontends + infrastructure

## Context

Phase 5 is the staged production deployment of all HomeIQ services. All pre-deployment
artifacts exist (plan, health-check script, rollback procedures, go/no-go gates).
Phase 6 is the post-deployment validation window. Detailed plan in
`docs/planning/phase-5-deployment-plan.md`.

Target start: Week of March 5-9, 2026 (pending security hardening completion).

## Stories

### Story 1: Pre-Deployment Validation Gate

**Priority:** Critical | **Estimate:** 4h | **Risk:** Low

**All gates must pass before Day 1 deployment begins.**

**Acceptance Criteria:**
- [ ] All 33 health endpoints responding 200 OK
- [ ] 704+ Python tests pass (100%)
- [ ] Frontend test suites pass
- [ ] 3 Playwright E2E scenarios pass
- [ ] All 53 Docker images build successfully
- [ ] All 8 PostgreSQL domain schemas deployed
- [ ] All 13 Alembic migrations run (upgrade + downgrade verified)
- [ ] InfluxDB buckets verified (`automation_core`, `ml_engine`, `metrics`)
- [ ] Pre-deployment backup completed (PostgreSQL dump + InfluxDB export + git tag)
- [ ] Prometheus + Grafana operational
- [ ] `scripts/check-pg-stability.sh` PASS

---

### Story 2: Tier 1 Deployment — Core Infrastructure

**Priority:** Critical | **Estimate:** 4h | **Risk:** High

**Services:** InfluxDB, PostgreSQL, websocket-ingestion (8001), data-api (8006), admin-api (8004)

**Acceptance Criteria:**
- [ ] InfluxDB and PostgreSQL containers healthy
- [ ] websocket-ingestion receiving HA events (WebSocket connected)
- [ ] data-api serving queries with < 100ms p95 latency
- [ ] admin-api health endpoint responding
- [ ] Go/no-go gate: all Tier 1 services healthy for 30 minutes before proceeding

---

### Story 3: Tier 2 Deployment — Essential Services

**Priority:** High | **Estimate:** 4h | **Risk:** Medium

**Services:** health-dashboard, data-retention, 10 data-collectors (weather-api,
smart-meter, sports-api, air-quality, carbon-intensity, electricity-pricing,
calendar, log-aggregator + 2 others)

**Acceptance Criteria:**
- [ ] health-dashboard accessible at :3000
- [ ] data-retention running scheduled cleanups
- [ ] All data collectors reporting data (health endpoints green)
- [ ] Go/no-go gate: Tier 2 healthy for 15 minutes

---

### Story 4: Tier 3 Deployment — ML/AI Services

**Priority:** High | **Estimate:** 4h | **Risk:** Medium

**Services:** ai-core-service, openvino-service, ml-service, rag-service,
ai-training-service, device-intelligence-service, model-prep, nlp-fine-tuning,
ner-service, openai-service

**Acceptance Criteria:**
- [ ] All ML model files loaded successfully
- [ ] AI inference endpoints responding within latency targets
- [ ] OpenVINO acceleration working (if hardware available)
- [ ] Go/no-go gate: Tier 3 healthy for 15 minutes

---

### Story 5: Tiers 4-8 Deployment — Domain Services

**Priority:** High | **Estimate:** 1 day | **Risk:** Medium

**Services:** 24 services across automation-core, blueprints, energy-analytics,
device-management, pattern-analysis

**Acceptance Criteria:**
- [ ] All automation-core services healthy (ha-ai-agent, ai-automation, ai-query, etc.)
- [ ] Blueprint services operational
- [ ] Energy analytics collecting and forecasting
- [ ] Device management services healthy
- [ ] Pattern analysis services operational
- [ ] Cross-group communication verified (auth tokens working)

---

### Story 6: Tier 9 Deployment — Frontends & Observability

**Priority:** High | **Estimate:** 2h | **Risk:** Low

**Services:** health-dashboard (:3000), ai-automation-ui (:3001),
observability-dashboard (:8501), Jaeger (:16686)

**Acceptance Criteria:**
- [ ] All 3 custom frontends accessible and rendering
- [ ] Cross-app switcher navigation working between all apps
- [ ] Jaeger receiving traces from deployed services
- [ ] Grafana dashboards showing real metrics

---

### Story 7: Phase 6 — Post-Deployment Monitoring (48h window)

**Priority:** Critical | **Estimate:** 2 days (monitoring) | **Risk:** Low

**Acceptance Criteria:**
- [ ] All 50 services healthy continuously for 48 hours
- [ ] No error rate spikes (< 1% error rate across all services)
- [ ] API latency within targets (data-api < 100ms p95, dashboard < 2s load)
- [ ] Data integrity verified: InfluxDB zero data loss, PostgreSQL zero corruption
- [ ] Prometheus alerts not firing (or false-positive alerts tuned)
- [ ] Memory and CPU within resource limits (no container OOM kills)

---

### Story 8: Phase 6 — User Acceptance & Documentation

**Priority:** High | **Estimate:** 1 day | **Risk:** Low

**Acceptance Criteria:**
- [ ] Manual smoke test of key user flows (create automation, view dashboard, chat with agent)
- [ ] Performance baselines documented for all tiers
- [ ] Known issues documented in `docs/operations/known-issues.md`
- [ ] Rollback procedures verified (tested for at least one tier)
- [ ] `REBUILD_STATUS.md` updated to reflect Phase 5 + 6 complete
- [ ] `docs/planning/rebuild-status.md` updated with final status
