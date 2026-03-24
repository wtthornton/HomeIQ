# Phase 5: Production Deployment Plan

**Date:** February 27, 2026 | **Refreshed:** March 13, 2026
**Status:** READY FOR EXECUTION — fully refreshed Mar 13, scripts updated
**Target Start:** TBD (original: March 5-9, 2026 — window passed)
**Estimated Duration:** 5 days
**Overall Progress:** 83.3% complete (5/6 phases done — Day 1 pre-deployment validation GO)

> **2026-03-13 UPDATE — PLAN REFRESH REQUIRED:**
>
> This plan was written Feb 27 when the project had 19 epics and 50 services.
> As of Mar 13, the project has **56 completed epics** and **51+ containers**.
> Key changes since this plan was written:
>
> | Area | Feb 27 State | Mar 13 State |
> |------|-------------|-------------|
> | Epics complete | 19 | 56 (+37 more) |
> | Containers | 50 + 3 frontends | 51 services + 5 frontends (includes voice-gateway, ha-device-control) |
> | Healthy containers | 47/49 (2 HA-dependent) | 51/51 (all healthy, redeployed Mar 6) |
> | Frontend tests | 704 Python tests only | 662 frontend tests + 704 Python tests |
> | Security | Basic hardening | Epic 55 production hardening (rate limits, pool tuning, security headers) |
> | Observability | Prometheus + Grafana | Epic 56 structured logging, Prometheus metrics, tracing, alerts, ops scripts |
> | New services | — | voice-gateway (8041), ha-device-control (8040), scheduled tasks |
> | New libs | 6 shared libs | + homeiq-memory (institutional memory with pgvector) |
> | E2E tests | Basic Playwright | 13-story E2E expansion (Epic 49), visual regression, route-spec matrix |
>
> **Before executing, update:**
> 1. Service inventory in pre-deployment checks (add voice-gateway, ha-device-control)
> 2. Health endpoint table (now 51+ services)
> 3. Rollout tiers to include new domain services
> 4. Monitoring section to leverage Epic 56 structured logging + ops scripts
> 5. Timeline — schedule a new deployment window
>
> **2026-03-23 — Canonical scale:** [Service groups](../architecture/service-groups.md) documents **62** Compose definitions and **~58** running containers with `--profile production` (via `start-stack`). Counts elsewhere in this file may reflect older snapshots (e.g. 51+); use service-groups + `domains/*/compose.yml` as source of truth.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Pre-Deployment Validation (Day 1)](#pre-deployment-validation-day-1)
3. [Staged Rollout Strategy](#staged-rollout-strategy)
4. [Production Deployment (Day 2-3)](#production-deployment-day-2-3)
5. [Monitoring & Observability (Day 4-5)](#monitoring--observability-day-4-5)
6. [Rollback Procedures](#rollback-procedures)
7. [Success Criteria & Go/No-Go Gates](#success-criteria--gono-go-gates)
8. [Communication Plan](#communication-plan)
9. [Dependencies & Blockers](#dependencies--blockers)

---

## Executive Summary

### What We're Deploying

Phase 5 is the production deployment of **56 completed epics** across **51+ microservices**:

| Epics Completed | Services | Status | Notes |
|---|---|---|---|
| **Phase 1** — Library Foundation | 38 | ✅ READY | Core Python packages (SQLAlchemy 2.0.36+, FastAPI 0.115+, Pydantic 2.9+) |
| **Phase 2** — Standard Libraries | 40+ | ✅ READY | Testing frameworks, async patterns, async-HTTP, python-dotenv |
| **Phase 4** — Frontend & Testing | 2 frontends | ✅ READY | health-dashboard, ai-automation-ui (Vite 7, React 19, Tailwind 4) |
| **Phase 4b** — Frontend Redesign | 3 apps | ✅ READY | UI overhaul, design system, 29 tabs → 14 consolidated |
| **Sprints 2-4** — Quality + Docker + Migration | 51 services | ✅ READY | Lint cleanup, Docker hardening, 38/38 service migration, shared libs |
| **Sprints 5-6** — HA Enhancements | 2 new services | ✅ READY | voice-gateway (8041), ha-device-control (8040), scheduled tasks, event bus |
| **Sprint 7** — Memory Brain | 8 integrations | ✅ READY | homeiq-memory lib, pgvector, trust model, 8 services integrated |
| **Sprint 8** — Pattern Detection + ML | 10 detectors | ✅ READY | 8 new detectors, ML deps upgraded (transformers, openvino) |
| **Sprint 10** — Frontend Testing | 662 tests | ✅ READY | 3 apps tested: 268 HD + 285 AI UI + 109 obs-dashboard tests |
| **Sprint 19** — Production Hardening | All | ✅ READY | Rate limits, pool tuning, security headers, structured logging, Prometheus metrics, tracing, alerts |
| **PostgreSQL Migration** | 13 services | ✅ READY | Schema-per-domain, Alembic migrations |
| **Operational Readiness** | All | ✅ READY | Prometheus, Grafana, backups, runbooks, E2E tests |

### Key Metrics

- **Service Count:** ~58 production-profile containers (62 Compose definitions — [service-groups](../architecture/service-groups.md)); historical lines below may say “51+ services”
- **Tested Status:** Full-stack health per your last redeploy (e.g. 51/51 at Mar 6, 2026 snapshot — re-verify against current compose)
- **Test Coverage:** 662 frontend tests + 704+ Python tests, 70 Python files validated (ruff + bandit clean)
- **Docker:** 28 Dockerfiles hardened, UID 1001, multi-stage builds, all shared libs wired
- **Database:** PostgreSQL 17 ready, Alembic migrations for 13 services
- **Monitoring:** Prometheus v3.2.1 + Grafana 11.5.2 with 15 alert rules + Epic 56 structured logging
- **Security:** Epic 55 rate limits + security headers + Epic 1 frontend hardening
- **E2E:** 13-story Playwright expansion (Epic 49) with visual regression and route-spec matrix

### Timeline

```
Phase 5 Deployment Window: TBD (original Mar 5-9 passed — reschedule needed)
├─ Day 1: Pre-deployment validation & health checks
├─ Day 2: Staged rollout (Tier 1-2)
├─ Day 3: Full production deployment + validation
├─ Day 4-5: Monitoring & incident response
└─ Total: 5 business days
```

---

## Pre-Deployment Validation (Day 1)

### 1.1 Health Check Baseline

**Goal:** Verify all services are healthy before deployment

**48 Services with Health Endpoints Confirmed (+ 3 internal/dev-only):**

| Service | Port | Endpoint | Domain |
|---|---|---|---|
| websocket-ingestion | 8001 | /health | core-platform |
| data-api | 8006 | /health | core-platform |
| admin-api | 8004 | /health | core-platform |
| health-dashboard | 3000 | /health | core-platform |
| data-retention | 8080 | /health | core-platform |
| weather-api | 8009 | /health | data-collectors |
| sports-api | 8005 | /health | data-collectors |
| carbon-intensity | 8010 | /health | data-collectors |
| electricity-pricing | 8011 | /health | data-collectors |
| air-quality | 8012 | /health | data-collectors |
| calendar-service | 8013 | /health | data-collectors |
| smart-meter-service | 8014 | /health | data-collectors |
| log-aggregator | 8015 | /health | data-collectors |
| ai-core-service | 8018 | /health | ml-engine |
| device-intelligence-service | 8028 | /health | ml-engine |
| openvino-service | 8026 | /health | ml-engine |
| ml-service | 8025 | /health | ml-engine |
| ai-training-service | 8033 | /health | ml-engine |
| rag-service | 8027 | /health | ml-engine |
| openai-service | 8020 | /health | ml-engine |
| nlp-fine-tuning | — | (no port) | ml-engine | training-only, not a running service |
| ner-service | 8031 | expose only | ml-engine | internal only, no published port |
| model-prep | — | (no port) | ml-engine | dev profile only |
| automation-linter | 8016 | /health | automation-core |
| ha-ai-agent-service | 8030 | /health | automation-core |
| automation-trace-service | 8044 | /health | automation-core |
| ai-automation-service-new | 8036 | /health | automation-core |
| ai-query-service | 8035 | /health | automation-core |
| yaml-validation-service | 8037 | /health | automation-core |
| ha-device-control | 8046 | /health | automation-core |
| ai-code-executor | (internal only) | /health | automation-core |
| blueprint-suggestion-service | 8039 | /health | blueprints |
| blueprint-index | 8038 | /health | blueprints |
| automation-miner | 8029 | /health | blueprints |
| rule-recommendation-ml | 8040 | /api/v1/health | blueprints | (ext 8040 → int 8035) |
| energy-correlator | 8017 | /health | energy-analytics |
| energy-forecasting | 8042 | /api/v1/health | energy-analytics |
| proactive-agent-service | 8031 | /health | energy-analytics |
| device-health-monitor | 8019 | /health | device-management |
| device-database-client | 8022 | /health | device-management |
| device-recommender | 8023 | /health | device-management |
| device-setup-assistant | 8021 | /health | device-management |
| device-context-classifier | 8032 | /health | device-management |
| activity-recognition | 8043 | /health | device-management |
| activity-writer | 8045 | /health | device-management |
| ha-setup-service | 8024 | /health | device-management |
| ai-pattern-service | 8034 | /health | pattern-analysis |
| api-automation-edge | 8041 | /health | pattern-analysis |
| voice-gateway | 8047 | /health | frontends |

**Pre-Deployment Health Check Script:**

```bash
#!/bin/bash
# Run before Phase 5 deployment
# Location: scripts/pre-deployment-check.sh

SERVICES=(
  "websocket-ingestion:8001"
  "data-api:8006"
  "admin-api:8004"
  "health-dashboard:3000"
  # ... (all 33 services)
)

echo "Pre-Deployment Health Check - $(date)"
FAILED=0

for service in "${SERVICES[@]}"; do
  IFS=':' read -r name port <<< "$service"
  if curl -f -s http://localhost:$port/health > /dev/null 2>&1; then
    echo "✅ $name:$port"
  else
    echo "❌ $name:$port — FAILED"
    ((FAILED++))
  fi
done

echo ""
echo "Summary: $(($# - FAILED))/$# services healthy"
[ $FAILED -eq 0 ] && echo "✅ All services healthy — ready for deployment" || echo "❌ $FAILED services unhealthy — STOP deployment"

exit $FAILED
```

### 1.2 Test Suite Validation

**Automated Tests:**

```bash
# Python services: 704+ tests
pytest tests/ -v --tb=short

# Frontend services: 662+ tests (268 HD + 285 AI UI + 109 obs-dashboard)
cd domains/core-platform/health-dashboard && npm test
cd domains/frontends/ai-automation-ui && npm test
cd domains/frontends/observability-dashboard && pytest tests/ -v

# Integration tests: Cross-group validation
pytest tests/integration/ -v

# E2E tests (Playwright): 13+ scenarios (Epic 49 expansion)
npx playwright test
  - database-health (PostgreSQL + InfluxDB)
  - cross-service-data-flow
  - database-migration rollback
  - health-dashboard tabs (overview, services, devices, events, hygiene, validation)
  - ai-automation-ui pages (chat, deployed, patterns, suggestions, navigation)
  - visual regression baseline
  - route-spec matrix validation

# Success Criteria: 100% pass rate
```

**Acceptance Gate:** All test suites must pass. No flaky tests allowed.

### 1.3 Docker Build Validation

**Parallel Build:**

```bash
# Build all services in parallel (estimated: 25-30 min)
time docker buildx bake full

# Expected output:
# ✅ Full stack built (~58 prod-profile containers / 62 compose definitions)
# ✅ 5 frontends built (incl. voice-gateway, jaeger)
# ✅ No layer cache misses on critical layers
# ✅ Image registry push (if using private registry)
```

**Build Verification:**

```bash
# Verify all images present
docker images | grep homeiq | wc -l  # Should be 56

# Verify image sizes reasonable (no bloat)
docker images | grep homeiq | awk '{print $2, $7}' | sort

# Expected: Most services 150-400MB, ML services 500-800MB, frontends 50-100MB
```

### 1.4 Database Readiness

**PostgreSQL 17 Validation:**

```bash
# 1. Verify PostgreSQL container running
docker ps | grep postgres

# 2. Verify all 8 schemas exist
psql -U homeiq -d homeiq -c "\dn+" | grep schema_

# Expected schemas:
# - core (websocket, data-api, admin-api, data-retention)
# - automation (ha-ai-agent, ai-automation, ai-query, automation-trace)
# - agent (ha-ai-agent shared)
# - blueprints (blueprint services)
# - energy (energy-analytics services)
# - devices (device-management services)
# - patterns (ai-pattern, api-automation-edge)
# - rag (rag-service, context caching)

# 3. Run all Alembic upgrades
for service in domains/*/*/; do
  if [ -f "$service/alembic/alembic.ini" ]; then
    cd "$service"
    alembic upgrade head
    cd -
  fi
done

# 4. Verify data consistency
pytest tests/validation/check_schemas.py -v
pytest tests/validation/validate_data.py -v
```

**InfluxDB 2.8.0 Validation:**

```bash
# 1. Verify InfluxDB running
curl -f http://localhost:8086/health

# 2. Verify buckets exist
influx bucket list

# Expected buckets:
# - automation_core (ha-ai-agent, proactive-agent traces)
# - ml_engine (model metrics)
# - metrics (Prometheus)

# 3. Verify time-series data readable
influx query 'from(bucket:"automation_core") |> range(start: -7d) |> first()'
```

**Acceptance Gate:** Both databases operational with all data accessible.

### 1.5 Backup & Rollback Verification

**Create Deployment Snapshot:**

```bash
# 1. Tag current state in git
git tag -a deployment-phase5-pre-$(date +%Y%m%d) \
  -m "Pre-Phase 5 deployment snapshot"

# 2. Backup PostgreSQL
docker exec postgres pg_dump -U homeiq homeiq > \
  backups/phase5-pre-deployment-$(date +%Y%m%d_%H%M%S).sql

# 3. Backup InfluxDB
docker exec influxdb influx export \
  --file backups/phase5-pre-deployment-$(date +%Y%m%d_%H%M%S).ndjson

# 4. Document backup locations
cat > backups/MANIFEST-phase5-pre.md << EOF
# Phase 5 Pre-Deployment Backup
- Date: $(date)
- Git tag: deployment-phase5-pre-$(date +%Y%m%d)
- PostgreSQL dump: backups/phase5-pre-deployment-*.sql
- InfluxDB export: backups/phase5-pre-deployment-*.ndjson
- Restore command: psql homeiq < backups/phase5-pre-deployment-*.sql
EOF
```

**Verify Rollback Capability:**

```bash
# Test restore on staging (if available)
# OR verify backup integrity
for backup in backups/phase5-pre-deployment-*.sql; do
  file "$backup" | grep -q "ASCII text" && echo "✅ $backup valid" || echo "❌ $backup corrupt"
done
```

---

## Staged Rollout Strategy

### Deployment Tiers

HomeIQ services are grouped by criticality. Deploy in this order:

#### Tier 1: Infrastructure & Critical Core (First — 2 hours)

**Definition:** Services that ALL other services depend on

| Service | Port | Domain | Readiness | Notes |
|---|---|---|---|---|
| InfluxDB | 8086 | infrastructure | ✅ READY | Time-series DB, external service |
| PostgreSQL 17 | 5432 | infrastructure | ✅ READY | Metadata DB, Alembic ready |
| websocket-ingestion | 8001 | core-platform | ✅ READY | Event ingestion from HA |
| data-api | 8006 | core-platform | ✅ READY | Query hub for all services |
| admin-api | 8004 | core-platform | ✅ READY | System monitoring & control |

**Deployment Steps:**

```bash
# 1. Verify database containers running
docker ps | grep -E "postgres|influxdb" | wc -l  # Should be 2

# 2. Redeploy core-platform domain with new builds
docker compose -f domains/core-platform/compose.yml up -d --pull always

# 3. Wait for health endpoints to respond
for i in {1..30}; do
  if curl -f http://localhost:8001/health && \
     curl -f http://localhost:8006/health && \
     curl -f http://localhost:8004/health; then
    echo "✅ Tier 1 services healthy"
    break
  fi
  sleep 2
done

# 4. Run smoke tests
pytest tests/smoke/tier1_health.py -v
```

**Acceptance Gate:** All Tier 1 services healthy, database queries working

---

#### Tier 2: Data Collection & Core Features (Second — 1.5 hours)

**Definition:** Services that depend on Tier 1 but not heavily interdependent

| Service | Port | Domain | Readiness |
|---|---|---|---|
| health-dashboard | 3000 | core-platform | ✅ READY |
| data-retention | 8080 | core-platform | ✅ READY |
| weather-api | 8009 | data-collectors | ✅ READY |
| smart-meter-service | 8014 | data-collectors | ✅ READY |
| sports-api | 8005 | data-collectors | ✅ READY |
| calendar-service | 8013 | data-collectors | ✅ READY |
| carbon-intensity | 8010 | data-collectors | ✅ READY |
| electricity-pricing | 8011 | data-collectors | ✅ READY |
| air-quality | 8012 | data-collectors | ✅ READY |
| log-aggregator | 8015 | data-collectors | ✅ READY |

**Deployment:**

```bash
# 1. Update health-dashboard and data-retention
docker compose -f domains/core-platform/compose.yml up -d health-dashboard data-retention --pull always

# 2. Update all data-collectors
docker compose -f domains/data-collectors/compose.yml up -d --pull always

# 3. Health checks
for service in health-dashboard data-retention weather-api smart-meter-service sports-api calendar-service carbon-intensity electricity-pricing air-quality log-aggregator; do
  docker ps | grep $service | grep -q "healthy" && echo "✅ $service" || echo "❌ $service"
done
```

**Acceptance Gate:** All Tier 2 services responding to health checks

---

#### Tier 3: ML/AI Services (Third — 2 hours)

**Definition:** Services with compute-intensive workloads; can be slower to deploy

| Count | Services | Domain |
|---|---|---|
| 9 | openvino, ml-service, ner, openai, rag, ai-core, ai-training, device-intelligence, model-prep | ml-engine |

**Note on Phase 3 (ML Library Upgrades):**

> **Decision:** Deploy Phase 5 **WITHOUT waiting for Phase 3 (ML library upgrades)**.
>
> **Rationale:**
> - Phase 3 ML libraries (numpy, scikit-learn, pandas) are optional enhancements
> - Phase 1-4 are all **blocking prerequisites** for Phase 5
> - Phase 3 requires 2+ weeks production stability verification
> - ML services work with current pinned versions
> - Phase 3 can be executed post-Phase 5 in parallel sprint
>
> **Timeline:** Phase 3 scheduled for late March (after 3-week Phase 5 stability window)

**Deployment:**

```bash
# 1. Update ml-engine domain
docker compose -f domains/ml-engine/compose.yml up -d --pull always

# 2. Wait for ML services (may take 5-10 min due to model loading)
sleep 30
for service in openvino-service ml-service ai-core-service ai-training-service device-intelligence-service; do
  docker ps | grep $service
done

# 3. Health checks for ML services
for port in 8026 8025 8018 8033 8028; do
  curl -f -s http://localhost:$port/health > /dev/null && echo "✅ Port $port" || echo "❌ Port $port"
done
```

**Acceptance Gate:** ML services started; health checks passing

---

#### Tier 4-7: Specialized Services (Fourth onwards — 3 hours)

**Tier 4** — Automation Core (8 services)
```
docker compose -f domains/automation-core/compose.yml up -d --pull always
# ha-ai-agent, ai-automation, ai-query, yaml-validation, linter, code-executor, traces, ha-device-control
```

**Tier 5** — Blueprints (4 services)
```
docker compose -f domains/blueprints/compose.yml up -d --pull always
# blueprint-index, blueprint-suggestion, rule-recommendation, automation-miner
```

**Tier 6** — Energy Analytics (3 services)
```
docker compose -f domains/energy-analytics/compose.yml up -d --pull always
# energy-correlator, energy-forecasting, proactive-agent
```

**Tier 7** — Device Management (8 services)
```
docker compose -f domains/device-management/compose.yml up -d --pull always
# device-health, classifier, setup, db-client, recommender, activity, activity-writer, ha-setup
```

**Tier 8** — Pattern Analysis (2 services)
```
docker compose -f domains/pattern-analysis/compose.yml up -d --pull always
# ai-pattern, api-automation-edge
```

**Tier 9** — Frontends (5 services)
```
docker compose -f domains/frontends/compose.yml up -d --pull always
# jaeger, observability-dashboard, ai-automation-ui, voice-gateway, health-dashboard-frontend
```

---

### Deployment Checklist (Day 2)

```yaml
Pre-Deployment (Day 1 Validation PASSED):
  ✅ All health checks passing
  ✅ All tests passing
  ✅ Docker builds successful
  ✅ Database schemas verified
  ✅ Backups created

Tier 1 Deployment (Hour 1):
  [ ] Create git tag: deployment-phase5-tier1-$(date +%Y%m%d)
  [ ] Deploy InfluxDB, PostgreSQL (verify running)
  [ ] Deploy websocket-ingestion, data-api, admin-api
  [ ] Run health checks: 3/3 healthy
  [ ] Run smoke tests: ALL PASS
  [ ] Verify data flows: HA → websocket → InfluxDB
  [ ] Sign-off: Tier 1 stable

Tier 2 Deployment (Hour 2):
  [ ] Create git tag: deployment-phase5-tier2-$(date +%Y%m%d)
  [ ] Deploy health-dashboard, data-retention
  [ ] Deploy all data-collectors (10 services)
  [ ] Run health checks: 12/12 healthy
  [ ] Verify dashboard loading
  [ ] Verify external API connectivity (weather, sports, etc.)
  [ ] Sign-off: Tier 2 stable

Tier 3 Deployment (Hour 3-4):
  [ ] Create git tag: deployment-phase5-tier3-$(date +%Y%m%d)
  [ ] Deploy ml-engine (9 services)
  [ ] Wait for model loading (5-10 min)
  [ ] Run health checks: 9/9 healthy
  [ ] Test AI inference endpoints
  [ ] Sign-off: Tier 3 stable

Tier 4-8 Deployment (Hour 5):
  [ ] Deploy automation-core (8 services, incl. ha-device-control)
  [ ] Deploy blueprints (4 services)
  [ ] Deploy energy-analytics (3 services)
  [ ] Deploy device-management (8 services)
  [ ] Deploy pattern-analysis (2 services)
  [ ] Run health checks: 25/25 healthy
  [ ] Sign-off: Tiers 4-8 stable

Tier 9 Deployment (Hour 6):
  [ ] Deploy frontends (5 services incl. voice-gateway, Jaeger)
  [ ] Verify observability-dashboard loading
  [ ] Verify ai-automation-ui loading
  [ ] Verify health-dashboard loading
  [ ] Verify voice-gateway responsive
  [ ] Sign-off: All frontends operational

Post-Deployment (Hour 7):
  [ ] Run full integration test suite
  [ ] Run E2E tests (13+ Playwright scenarios)
  [ ] Manual smoke testing
  [ ] Verify no error spikes (check structured logs from Epic 56)
  [ ] Commit deployment manifest to docs/

Day 2 Sign-off: ✅ Deployment complete, all 51+ services healthy
```

---

## Production Deployment (Day 2-3)

### Day 2: Off-Peak Deployment Window

**Timing:** Tuesday-Thursday, 9 PM - 6 AM (9 hours off-peak)

**Why Off-Peak?**
- Minimal user impact if rollback needed
- HA automation events are typically lower volume at night
- 9-hour window provides comfortable deployment buffer
- Can continue into early morning if needed

**Pre-Deployment (8 PM):**

```bash
# 1. Final health check
scripts/pre-deployment-health-check.sh

# 2. Notify stakeholders
# "Phase 5 deployment starting at 9 PM. Expected completion: 6 AM"

# 3. Start monitoring
cd monitoring && ./build-dashboard.sh
tail -f logs/deployment_phase5.log

# 4. Position on-call engineer
# - Terminal 1: Docker logs aggregator
# - Terminal 2: Deployment script runner
# - Terminal 3: Monitoring dashboard
```

**Deployment (9 PM - 6 AM):**

Execute the tier-by-tier rollout above. Expected duration: 3-4 hours with validation.

**Post-Deployment (6 AM):**

```bash
# 1. Full health check
scripts/post-deployment-health-check.sh > deployment-report-$(date +%Y%m%d).txt

# 2. Verify data integrity
pytest tests/validation/check_data_integrity.py -v

# 3. Run smoke tests
pytest tests/smoke/ -v --tb=short

# 4. Notify team
# "Phase 5 deployment complete. All 51+ services healthy. Monitoring active."
```

### Day 3: Validation & Cutover

**Validation Checklist:**

```yaml
Morning (9 AM):
  ✅ All 51+ services healthy
  ✅ All frontends loading correctly
  ✅ Data flows working (HA → ingestion → influxdb → data-api)
  ✅ No error spikes in logs
  ✅ No repeated restart loops
  ✅ InfluxDB queries returning data
  ✅ PostgreSQL queries working

Mid-Day (12 PM):
  ✅ 4-hour stability window: no new errors
  ✅ User workflows tested (automation creation, device control, etc.)
  ✅ API load tests passed
  ✅ Dashboard responsiveness acceptable

End of Day (5 PM):
  ✅ 24-hour monitoring review: no concerning trends
  ✅ Performance metrics within baseline
  ✅ Team sign-off: ready for normal operations
  ✅ Commit deployment manifest
```

**Go/No-Go Decision:**

| Metric | Go Threshold | Status | Decision |
|---|---|---|---|
| Services Healthy | 100% (51/51+) | ✅ | GO |
| Test Pass Rate | 100% | ✅ | GO |
| Error Rate | <0.5% | ✅ | GO |
| Response Time | <baseline+10% | ✅ | GO |
| No Critical Alerts | 0 triggered | ✅ | GO |

**Decision:** PROCEED TO PHASE 6 OR STOP

---

## Monitoring & Observability (Day 4-5)

### Real-Time Monitoring Dashboard

**Prometheus + Grafana Setup:**

```bash
# 1. Verify Prometheus scraping all 51+ services
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets | length'
# Expected: 51+

# 2. Verify Grafana dashboards
# - HomeIQ Service Health (15 alert rules)
# - PostgreSQL Performance (8 monitoring views)
# - InfluxDB Metrics
# - Jaeger Distributed Tracing
# - Custom E2E dashboard

# 3. Verify Epic 56 observability tooling
# - Structured JSON logging (all services)
# - Prometheus /metrics endpoints (service-level metrics)
# - OpenTelemetry tracing spans
# - Ops scripts: scripts/ops-health-check.sh, scripts/ops-log-analyzer.sh

# 4. Configure alert routing (PagerDuty, Slack, etc.)
```

### Critical Alerts (24x7 Monitoring)

| Alert | Threshold | Action |
|---|---|---|
| **Service Down** | Service unreachable >2 min | Page on-call engineer |
| **Error Rate High** | >5% errors in 5 min | Investigate, consider rollback |
| **Response Time Spike** | >2x baseline | Check for resource issues |
| **Database Connection Failed** | Any failed query in critical path | Check PostgreSQL/InfluxDB health |
| **Memory Exhaustion** | >85% on any container | Restart service or scale |
| **Disk Space Low** | <5% free on volumes | Archive old data, expand volumes |

### Success Metrics (Day 4-5)

**Track these continuously:**

```yaml
Availability:
  - All 51+ services: 99.9% uptime target
  - Tier 1 services: 99.99% uptime target

Performance:
  - API response time: <100ms p95
  - Dashboard load time: <2 sec
  - AI inference: <5 sec (varies by model)

Error Rates:
  - System errors: <0.5%
  - API 4xx errors: <1%
  - API 5xx errors: <0.1%

Data Integrity:
  - InfluxDB: 0 data loss
  - PostgreSQL: 0 data corruption
  - No orphaned records

User Impact:
  - Zero critical incidents
  - Zero data loss incidents
  - Zero unplanned restarts
```

### Incident Response Playbook

**If Error Rate Spikes (>5%):**

```bash
# 1. Identify affected service
docker logs <service-name> | tail -100 | grep ERROR

# 2. Check resource usage
docker stats <service-name>

# 3. Check recent code changes
git log --oneline -10

# 4. Decision: Fix or Rollback?
# If fixable: restart service → monitor for 5 min
# If not: INITIATE ROLLBACK (see below)
```

**If Database Becomes Unreachable:**

```bash
# 1. Check Docker container
docker ps | grep -E "postgres|influxdb"

# 2. Check logs
docker logs postgres | tail -50
docker logs influxdb | tail -50

# 3. If PostgreSQL crashed:
docker restart postgres
# Verify with: psql -U homeiq -d homeiq -c "SELECT 1"

# 4. If InfluxDB crashed:
docker restart influxdb
# Verify with: curl -f http://localhost:8086/health

# 5. If unrecoverable: INITIATE ROLLBACK
```

**If Single Service Crashes (Tier 3+):**

```bash
# 1. Restart service
docker compose -f domains/<domain>/compose.yml up -d <service>

# 2. Wait for health check
sleep 5 && curl -f http://localhost:<port>/health

# 3. Monitor logs for 2 minutes
docker logs <service> --follow --tail=20

# 4. If stable: continue monitoring
# If unstable: ROLLBACK just that service (see Rollback section)
```

---

## Rollback Procedures

### Tiered Rollback Strategy

**Scope 1: Single Service Rollback** (Low Risk)

```bash
# If only one service unhealthy (e.g., ai-core-service crashes)
# Time to execute: 2-5 minutes

# 1. Stop unhealthy service
docker compose -f domains/ml-engine/compose.yml down ai-core-service

# 2. Revert to previous image
git checkout HEAD~1 -- domains/ml-engine/Dockerfile
docker buildx bake ai-core-service

# 3. Restart service
docker compose -f domains/ml-engine/compose.yml up -d ai-core-service

# 4. Verify health
curl -f http://localhost:8018/health

# 5. Document incident
echo "Rolled back ai-core-service at $(date)" >> deployment-incidents.log
```

**Scope 2: Domain Rollback** (Medium Risk)

```bash
# If entire domain unhealthy (e.g., all ml-engine services crash)
# Time to execute: 5-15 minutes

# 1. Stop entire domain
docker compose -f domains/ml-engine/compose.yml down

# 2. Revert docker-compose.yml changes
git checkout HEAD~1 -- domains/ml-engine/compose.yml
git checkout HEAD~1 -- domains/ml-engine/*/Dockerfile

# 3. Rebuild all services in domain
docker buildx bake ml-engine

# 4. Restart domain
docker compose -f domains/ml-engine/compose.yml up -d

# 5. Verify all services
for service in openvino ml-service ai-core-service ai-training-service device-intelligence-service; do
  curl -f http://localhost:$(docker port $service 2>/dev/null | grep -oP '8\d{3}' | head -1)/health || echo "FAILED: $service"
done

# 6. Document incident
echo "Rolled back ml-engine domain at $(date)" >> deployment-incidents.log
```

**Scope 3: Full System Rollback** (High Risk - Last Resort)

```bash
# If multiple domains or database failures
# Time to execute: 15-30 minutes
# APPROVAL REQUIRED: Technical Lead + DevOps

# 1. Stop entire deployment
docker compose down

# 2. Restore from pre-deployment backup
git checkout deployment-phase5-pre-$(date +%Y%m%d)

# 3. Restore databases
# PostgreSQL
psql -U homeiq homeiq < backups/phase5-pre-deployment-*.sql

# InfluxDB
docker exec influxdb influx restore \
  /backups/phase5-pre-deployment-*.ndjson

# 4. Restart entire stack
docker compose up -d

# 5. Wait for all services to be healthy (10-15 min)
watch -n 5 'docker ps | grep healthy | wc -l'  # Should reach 51+

# 6. Run full health check
scripts/pre-deployment-health-check.sh

# 7. Notify all stakeholders
# "Full rollback to pre-Phase 5 state completed at $(date)"
# Share incident report, root cause analysis
```

### Rollback Decision Matrix

| Indicator | Action |
|---|---|
| 1 service unhealthy | Restart service, monitor 5 min |
| 2-3 services unhealthy | Restart domain, monitor 10 min |
| 5+ services unhealthy | **INITIATE FULL ROLLBACK** |
| Database unreachable | **INITIATE FULL ROLLBACK** |
| Error rate >10% for >10 min | **INITIATE FULL ROLLBACK** |
| Data corruption detected | **INITIATE FULL ROLLBACK** |

---

## Success Criteria & Go/No-Go Gates

### Gate 1: Pre-Deployment Validation ✅

**Must Pass Before Day 2 Deployment:**

- [ ] All 44+ health endpoints responding
- [ ] 1366+ tests passing (704 Python + 662 frontend, 100% pass rate)
- [ ] Docker builds successful for all 56 containers
- [ ] PostgreSQL 17 with all 8 schemas deployed
- [ ] InfluxDB 2.8.0 with all buckets created
- [ ] Alembic migrations run on all services
- [ ] Pre-deployment backups created and verified
- [ ] Monitoring dashboard operational

**Go Decision:** All boxes checked ✅ → PROCEED TO TIER 1

---

### Gate 2: Tier 1 Critical Services ✅

**Must Complete Successfully:**

- [ ] websocket-ingestion responding to /health
- [ ] data-api responding to /health + queries working
- [ ] admin-api responding to /health
- [ ] InfluxDB receiving data from websocket
- [ ] PostgreSQL serving queries from all services
- [ ] No error spikes in logs (error rate <0.5%)
- [ ] Smoke tests passing for Tier 1

**Go Decision:** All criteria met ✅ → PROCEED TO TIER 2

---

### Gate 3: Tier 2 Services ✅

**Must Complete Successfully:**

- [ ] health-dashboard loading on port 3000
- [ ] data-retention service healthy
- [ ] All 10 data-collectors responding to /health
- [ ] External API integrations working (weather, sports, etc.)
- [ ] No cascading failures from Tier 1
- [ ] Health check suite: 12/12 passing

**Go Decision:** All criteria met ✅ → PROCEED TO TIER 3

---

### Gate 4: Full System Health (48 Hours) ✅

**Must Meet After Tier 9 Deployment:**

| Metric | Target | Actual | Status |
|---|---|---|---|
| Services Healthy | 51/51+ | _ | [ ] |
| Error Rate | <0.5% | _ | [ ] |
| Response Time p95 | <baseline+10% | _ | [ ] |
| Uptime | 100% | _ | [ ] |
| Test Pass Rate | 100% | _ | [ ] |
| No restarts | 0 unplanned | _ | [ ] |
| Data integrity | 100% | _ | [ ] |

**Go Decision:** All metrics pass ✅ → COMPLETE PHASE 5

---

## Communication Plan

### Pre-Deployment (72 Hours Prior)

**Message to Team:**

```
Subject: Phase 5 Production Deployment - [TBD Week]

Hi team,

Phase 5 (Production Deployment) is scheduled for:
- Date: [TBD Day 1-3]
- Window: 9 PM - 6 AM (off-peak)
- Services: Full stack (~58 prod-profile / 62 compose — [service-groups](../architecture/service-groups.md))
- Expected Duration: 3-4 hours deployment, 24-48 hours validation

What's being deployed (56 epics, 357 stories):
✅ Phase 1-4 library upgrades (SQLAlchemy 2.0, FastAPI 0.115+, Pydantic 2.9+)
✅ Frontend redesign (29 tabs → 14 consolidated pages, React 19, Vite 7, Tailwind 4)
✅ PostgreSQL migration (PostgreSQL 17, schema-per-domain)
✅ Memory Brain (homeiq-memory lib, pgvector, trust model, 8 services integrated)
✅ Pattern Detection Expansion (8 new detectors, ML models: LSTM, Isolation Forest, FP-Growth)
✅ Production Hardening (rate limits, pool tuning, security headers, structured logging)
✅ Observability (Prometheus metrics, OpenTelemetry tracing, Grafana alerts, ops scripts)
✅ 1366+ tests (704 Python + 662 frontend + 13 E2E Playwright scenarios)

Impact:
- Minimal impact on HA automations (deployed during off-peak hours)
- Improved performance, security, and observability
- Zero data loss expected (comprehensive backups in place)

Rollback Plan:
- Full rollback capability to pre-deployment state
- Single service rollback available in <5 min
- Full system rollback in <30 min if needed

Please:
1. Review Phase 5 plan: docs/planning/phase-5-deployment-plan.md
2. Confirm your availability for on-call support
3. Notify your team of the deployment window

Questions? Reach out to [DevOps Lead]
```

### During Deployment (Real-Time Updates)

**Slack Channel: #homeiq-deployment**

```
9:00 PM: Tier 1 deployment starting (websocket, data-api, admin-api)
9:15 PM: ✅ Tier 1 health checks passing
9:30 PM: Tier 2 deployment starting (data-collectors, health-dashboard)
9:50 PM: ✅ Tier 2 health checks passing
10:00 PM: Tier 3 deployment starting (ML services)
10:15 PM: Waiting for model loading... (normal, estimated 5-10 min)
10:25 PM: ✅ Tier 3 health checks passing
10:30 PM: Tiers 4-8 deployment starting
10:50 PM: ✅ Tiers 4-8 health checks passing
11:00 PM: Tier 9 deployment starting (frontends)
11:15 PM: ✅ All frontends responsive
11:20 PM: ✅ DEPLOYMENT COMPLETE — all 51+ services healthy
11:30 PM: Integration tests running...
11:45 PM: ✅ E2E tests passed
12:00 AM: ✅ Phase 5 deployment successful

Monitoring continues through Day 3 and Day 4-5
```

### Post-Deployment (Team Notification)

**Day 3 Morning Announcement:**

```
Subject: Phase 5 Deployment Complete ✅

Full stack deployed successfully (see [service-groups](../architecture/service-groups.md) for current counts).

Deployment Results:
✅ Duration: 2.5 hours (on schedule)
✅ Services Healthy: 51/51+ (100%)
✅ Tests Passing: 1366+ (704 Python + 662 frontend) (100%)
✅ Error Rate: <0.1% (excellent)
✅ Zero data loss
✅ Zero unplanned restarts

Key Improvements:
- 15% faster database queries (PostgreSQL with connection pooling)
- 8% reduction in error rates (library upgrades)
- Structured JSON logging + Prometheus metrics + OpenTelemetry tracing (Epic 56)
- Rate limiting + security headers + pool tuning (Epic 55)
- Memory Brain: institutional memory with pgvector, trust model, 8 services integrated
- 8 new pattern detectors with ML models (LSTM, Isolation Forest, FP-Growth)
- 3-tier testing coverage (unit/integration/E2E — 1366+ tests)
- Automated disaster recovery playbooks

Monitoring:
- Real-time dashboard: http://localhost:3000 (health-dashboard)
- Observability: http://localhost:8501 (observability-dashboard)
- Distributed traces: http://localhost:16686 (Jaeger)
- Metrics: http://localhost:3001 (ai-automation-ui)

Next: Phase 6 post-deployment validation (3 days)

Thank you for your patience during the deployment window!
```

---

## Dependencies & Blockers

### External Dependencies

| Dependency | Status | Impact | Mitigation |
|---|---|---|---|
| **Phase 1-4 Completion** | ✅ COMPLETE | BLOCKING | All complete, no blockers |
| **Docker Infrastructure** | ✅ READY | BLOCKING | Docker 29.1.3, Compose 2.40.3 verified |
| **PostgreSQL 17** | ✅ READY | BLOCKING | Container ready, schemas created |
| **InfluxDB 2.8.0** | ✅ READY | BLOCKING | Container ready, buckets created |
| **Network Connectivity** | ✅ READY | BLOCKING | homeiq-network bridge created |
| **Disk Space** | ✅ 50+ GB | BLOCKING | Verified, expansion available if needed |
| **Home Assistant** | ✅ (assumed) | OPTIONAL | Gracefully degrades if unavailable |

### Deployment Window Conflicts

**Check Before Scheduling:**

```bash
# 1. Verify no other deployments scheduled
# Check team calendar, release calendar

# 2. Verify no major events in Home Assistant
# Check HA update schedule, family events

# 3. Verify on-call coverage
# Confirm DevOps, Backend, Frontend on-call available
```

### Phase 3 (ML Library Upgrades) - Independent

**Status:** Deferred, NOT a blocker for Phase 5

- Phase 3 libraries (numpy, scikit-learn, pandas) are optional
- Phase 5 can deploy with current ML library versions
- Phase 3 execution scheduled for late March (post-stability window)
- ML services tested and verified working with current versions

**Decision:** Deploy Phase 5 → Monitor for 3 weeks → Execute Phase 3 in parallel sprint

---

## Appendix: Pre-Deployment Checklist

```yaml
72 Hours Before Deployment:
  [ ] Schedule deployment window (off-peak)
  [ ] Notify all stakeholders
  [ ] Confirm on-call coverage
  [ ] Review Phase 5 plan with team
  [ ] Verify backup infrastructure ready

24 Hours Before Deployment:
  [ ] Run full test suite: 1366+ tests (704 Python + 662 frontend)
  [ ] Verify Docker builds: 56 containers
  [ ] Check database schemas: 8 PostgreSQL schemas
  [ ] Verify InfluxDB buckets
  [ ] Run pre-deployment health check
  [ ] Create git tags for rollback

6 Hours Before Deployment:
  [ ] Final infrastructure verification
  [ ] Confirm monitoring dashboard operational
  [ ] Position on-call team
  [ ] Create deployment war room (Slack/Discord)
  [ ] Brief team on rollback procedures

Deployment Day (T-1 Hour):
  [ ] All health checks passing
  [ ] Backups created and verified
  [ ] Git tags pushed
  [ ] Monitoring dashboard live
  [ ] Team assembled and ready

Post-Deployment:
  [ ] All services healthy (100%)
  [ ] Tests passing (100%)
  [ ] Error rate <0.5%
  [ ] Backups verified
  [ ] Incident log clean
  [ ] Team debriefing scheduled
```

---

## Deployment Scripts Reference

All deployment automation scripts are located in `scripts/`:

| Script | Purpose |
|---|---|
| `scripts/pre-deployment-check.sh` | Pre-deployment validation gate (health, tests, Docker, databases) |
| `scripts/deploy-tier1.sh` | Tier 1: Core infrastructure (InfluxDB, PostgreSQL, websocket, data-api, admin-api) |
| `scripts/deploy-tier2.sh` | Tier 2: Essential services (health-dashboard, data-retention, data-collectors) |
| `scripts/deploy-tier3.sh` | Tier 3: ML/AI services (extended timeout for model loading) |
| `scripts/deploy-tiers4-8.sh` | Tiers 4-8: Domain services (automation, blueprints, energy, devices, patterns) |
| `scripts/deploy-tier9.sh` | Tier 9: Frontends & observability (Jaeger, dashboards, UI) |
| `scripts/post-deployment-monitor.sh` | Phase 6: 48-hour continuous monitoring with alerts |
| `scripts/deployment/common.sh` | Shared functions (logging, health checks, gate checks, rollback) |

### Port Corrections (March 2, 2026)

The following ports were corrected from the original plan to match actual `compose.yml` mappings:

- `automation-trace-service`: 8031 -> **8044** (external port mapping: 8044:8020)
- `energy-forecasting`: 8024 -> **8042** (external port mapping: 8042:8037, health: `/api/v1/health`)
- `activity-writer`: 8033 -> **8045** (external port mapping: 8045:8035)
- `ha-setup-service`: 8034 -> **8024** (external port mapping: 8024:8020)
- `ai-code-executor`: 8032 -> **internal only** (uses `expose`, no published port)

### Services Added Since Original Plan (Mar 13 Refresh)

The original plan listed 33 services. The following were added to the health table:

- `rag-service` (port 8027, ml-engine)
- `openai-service` (port 8020, ml-engine)
- `ai-automation-service-new` (port 8036, automation-core)
- `ai-query-service` (port 8035, automation-core)
- `yaml-validation-service` (port 8037, automation-core)
- `ha-device-control` (port 8040, automation-core) — **NEW: Sprint 5, Epic 25**
- `rule-recommendation-ml` (port 8040, blueprints — health: `/api/v1/health`)
- `proactive-agent-service` (port 8031, energy-analytics)
- `activity-recognition` (port 8043, device-management)
- `ai-pattern-service` (port 8034, pattern-analysis)
- `api-automation-edge` (port 8041, pattern-analysis)
- `voice-gateway` (port 8041, frontends) — **NEW: Sprint 6, Epic 26**

Total services with health endpoints: **48** (up from 33 in original plan, + 3 internal/dev-only).

---

**Status:** REFRESHED — Ready for scheduling
**Approved By:** [To be signed]
**Last Updated:** March 13, 2026
**Next Review:** [Schedule deployment window]
**Refresh Notes:** Updated from 19→59 epics, 33→48 health endpoints (+ 3 internal), 50→51+ services, corrected ports (ha-device-control 8046, voice-gateway 8047), added 6 missing services to scripts, integrated Epic 55-58 hardening.
