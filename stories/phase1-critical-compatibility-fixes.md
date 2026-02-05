---
epic: homeiq-rebuild
phase: Phase 1
priority: critical
status: in-progress
estimated_duration: 1 week
risk_level: medium
---

# Epic: Phase 1 - Critical Compatibility Fixes

**Status:** 🚀 In Progress
**Priority:** 🔴 Critical
**Duration:** 1 week (5 days)
**Risk Level:** Medium
**Dependencies:** Phase 0 complete ✅

## Overview

Update critical libraries across 30+ Python services and 2 Node.js frontend services to ensure compatibility, security, and stability. This phase focuses on high-risk library updates that affect core functionality.

## Objectives

1. **Standardize Core Libraries** - Ensure consistent versions across all services
2. **Update Critical Dependencies** - SQLAlchemy 2.0.46, aiosqlite 0.22.1, FastAPI 0.119.0+
3. **Zero-Downtime Deployment** - Sequential rebuild with health validation
4. **Maintain Service Availability** - 44/45 services must remain healthy
5. **Enable Phase 2** - Prepare for database and async library updates

## Success Criteria

- ✅ All rebuilt services show "healthy" status
- ✅ No errors in service logs (last 100 lines)
- ✅ API endpoints respond correctly (< 500ms)
- ✅ Frontend dashboards load successfully (< 3s)
- ✅ No service restarts in 1 hour post-deployment
- ✅ InfluxDB receiving data (verified via Jaeger traces)
- ✅ Performance regression < 10% from baseline

## Current State Analysis

### Requirements Base (requirements-base.txt)

**Current Versions:**
- SQLAlchemy: 2.0.45
- aiosqlite: 0.21.0
- FastAPI: 0.128.0
- Pydantic: 2.12.5
- httpx: 0.28.1
- pytest-asyncio: 1.3.0

**Target Versions (Phase 1):**
- SQLAlchemy: 2.0.45 → **2.0.46** ⬆️
- aiosqlite: 0.21.0 → **0.22.1** ⬆️
- FastAPI: 0.128.0 → **0.119.0+** (keep current or latest)
- Pydantic: 2.12.5 (✅ already v2, keep current)
- httpx: 0.28.1+ (✅ keep current)

### Service-Specific Updates Required

**Already Updated (✅):**
- automation-linter: FastAPI 0.119.0 ✅
- calendar-service: pydantic-settings 2.12.0 ✅

**Needs Review:**
- 41 other Python services (check if using base requirements)
- 2 Node.js services (health-dashboard, ai-automation-ui)

## User Stories

### Story 1: Update Base Requirements File

**As a** DevOps engineer
**I want** to update requirements-base.txt with Phase 1 library versions
**So that** all services inherit the updated dependencies

**Acceptance Criteria:**
1. ✅ SQLAlchemy updated to 2.0.46
2. ✅ aiosqlite updated to 0.22.1
3. ✅ Version ranges properly configured
4. ✅ Comments updated with Phase 1 notes
5. ✅ No breaking changes introduced

**Story Points:** 2
**Priority:** Critical
**Estimated Effort:** 1 hour

**Tasks:**
- [ ] Review current requirements-base.txt
- [ ] Update SQLAlchemy version constraint
- [ ] Update aiosqlite version constraint
- [ ] Verify FastAPI/Pydantic are already at target versions
- [ ] Add Phase 1 update comments
- [ ] Commit changes with descriptive message

---

### Story 2: Validate Service Requirements Compatibility

**As a** DevOps engineer
**I want** to validate that all service requirements files are compatible with Phase 1 updates
**So that** I can identify services that need specific attention

**Acceptance Criteria:**
1. ✅ All 43 Python service requirements files reviewed
2. ✅ Services using `-r ../../requirements-base.txt` identified
3. ✅ Services with pinned versions documented
4. ✅ Potential conflicts identified and documented
5. ✅ Update strategy defined for each service category

**Story Points:** 3
**Priority:** High
**Estimated Effort:** 2 hours

**Tasks:**
- [ ] Scan all services/*/requirements.txt files
- [ ] Identify services extending requirements-base.txt
- [ ] Document services with pinned SQLAlchemy/aiosqlite versions
- [ ] Check for conflicting version constraints
- [ ] Create compatibility matrix
- [ ] Generate service update checklist

---

### Story 3: Rebuild Infrastructure Services

**As a** DevOps engineer
**I want** to restart infrastructure services (InfluxDB, Jaeger)
**So that** they are in a clean state before service rebuilds

**Acceptance Criteria:**
1. ✅ InfluxDB restarted successfully
2. ✅ Jaeger restarted successfully
3. ✅ Both services healthy within 2 minutes
4. ✅ Health check endpoints responding
5. ✅ No data loss during restart
6. ✅ Monitoring captures restart events

**Story Points:** 1
**Priority:** High
**Estimated Effort:** 30 minutes

**Tasks:**
- [ ] Source BuildKit configuration (`.env.buildkit`)
- [ ] Start monitoring dashboard (`cd monitoring && ./build-dashboard.sh`)
- [ ] Restart InfluxDB: `docker-compose restart influxdb`
- [ ] Wait for healthy status (30s)
- [ ] Restart Jaeger: `docker-compose restart jaeger`
- [ ] Wait for healthy status (30s)
- [ ] Verify health endpoints (curl tests)
- [ ] Check logs for errors

---

### Story 4: Rebuild Core Services Sequentially

**As a** DevOps engineer
**I want** to rebuild core services (data-api, websocket-ingestion, admin-api, data-retention) sequentially
**So that** I can validate each service before proceeding

**Acceptance Criteria:**
1. ✅ data-api rebuilt and healthy
2. ✅ websocket-ingestion rebuilt and healthy
3. ✅ admin-api rebuilt and healthy
4. ✅ data-retention rebuilt and healthy
5. ✅ All services pass health checks
6. ✅ API endpoints responding correctly
7. ✅ No errors in service logs
8. ✅ Data flow verified (HA → websocket → InfluxDB → data-api)

**Story Points:** 8
**Priority:** Critical
**Estimated Effort:** 4 hours

**Rebuild Sequence:**

#### 4.1. data-api (Port 8006)
```bash
# Build
docker-compose build --no-cache data-api

# Deploy
docker-compose up -d data-api

# Wait and validate
sleep 20
docker ps --filter name=data-api --format "{{.Status}}"
curl -f http://localhost:8006/health

# Check logs
docker logs homeiq-data-api --tail 50 | grep -i error
```

**Validation:**
- Health check passes
- API responds < 500ms
- No errors in logs
- InfluxDB queries working

#### 4.2. websocket-ingestion (Port 8001)
```bash
# Build
docker-compose build --no-cache websocket-ingestion

# Deploy
docker-compose up -d websocket-ingestion

# Wait and validate (extra time for WebSocket connection)
sleep 30
docker ps --filter name=websocket --format "{{.Status}}"
curl -f http://localhost:8001/health

# Verify WebSocket connection to Home Assistant
docker logs homeiq-websocket --tail 50 | grep -i "connected\|error"
```

**Validation:**
- Health check passes (fixed in Phase 0)
- WebSocket connection to HA established
- Events being ingested
- InfluxDB writes confirmed

#### 4.3. admin-api (Port 8004)
```bash
# Build
docker-compose build --no-cache admin-api

# Deploy
docker-compose up -d admin-api

# Wait and validate
sleep 20
docker ps --filter name=admin --format "{{.Status}}"
curl -f http://localhost:8004/health

# Check logs
docker logs homeiq-admin-api --tail 50 | grep -i error
```

**Validation:**
- Health check passes
- Admin endpoints accessible
- Service monitoring functional
- No errors in logs

#### 4.4. data-retention (Port 8080)
```bash
# Build
docker-compose build --no-cache data-retention

# Deploy
docker-compose up -d data-retention

# Wait and validate
sleep 30
docker ps --filter name=data-retention --format "{{.Status}}"
curl -f http://localhost:8080/health
```

**Validation:**
- Health check passes
- Retention policies active
- No errors in logs

**Tasks:**
- [ ] Rebuild data-api with validation
- [ ] Rebuild websocket-ingestion with validation
- [ ] Rebuild admin-api with validation
- [ ] Rebuild data-retention with validation
- [ ] Verify data flow end-to-end
- [ ] Monitor for 1 hour (no restarts)

---

### Story 5: Rebuild External Integration Services

**As a** DevOps engineer
**I want** to rebuild all external integration services in parallel batches
**So that** they inherit Phase 1 library updates efficiently

**Acceptance Criteria:**
1. ✅ All 8 external integration services rebuilt
2. ✅ All services show healthy status
3. ✅ External API integrations verified
4. ✅ Data flowing to InfluxDB
5. ✅ No errors in service logs
6. ✅ Performance within baseline ±10%

**Story Points:** 5
**Priority:** High
**Estimated Effort:** 2 hours

**Services (8):**
1. weather-api (Port 8009)
2. sports-api (Port 8005)
3. carbon-intensity (Port 8010)
4. electricity-pricing (Port 8011)
5. air-quality (Port 8012)
6. calendar-service (Port 8013) - Already has pydantic-settings 2.12.0 ✅
7. smart-meter-service (Port 8014)
8. log-aggregator (Port 8015)

**Batch Rebuild Strategy:**
```bash
# Build all in parallel (faster)
SERVICES="weather-api sports-api carbon-intensity electricity-pricing air-quality calendar-service smart-meter-service log-aggregator"

for service in $SERVICES; do
  echo "Building $service..."
  docker-compose build --no-cache $service &
done

# Wait for all builds
wait

# Deploy all
docker-compose up -d $SERVICES

# Wait for health checks
sleep 60

# Verify all healthy
docker ps --filter name="weather|sports|carbon|electricity|air-quality|calendar|smart-meter|log-aggregator" --format "table {{.Names}}\t{{.Status}}"
```

**Individual Validation:**
```bash
# Test each service endpoint
curl -f http://localhost:8009/api/v1/weather/current
curl -f http://localhost:8005/api/v1/sports/upcoming
curl -f http://localhost:8010/api/v1/carbon/current
curl -f http://localhost:8011/api/v1/pricing/current
curl -f http://localhost:8012/api/v1/air-quality/current
curl -f http://localhost:8013/health
curl -f http://localhost:8014/health
curl -f http://localhost:8015/health
```

**Tasks:**
- [ ] Build all 8 services in parallel
- [ ] Deploy all services simultaneously
- [ ] Validate health checks for all services
- [ ] Test API endpoints individually
- [ ] Check logs for errors
- [ ] Verify data in InfluxDB

---

### Story 6: Rebuild AI/ML Services (Phase 1 Subset)

**As a** DevOps engineer
**I want** to rebuild AI/ML services that use SQLAlchemy/aiosqlite
**So that** they benefit from Phase 1 database library updates

**Acceptance Criteria:**
1. ✅ Core AI services rebuilt successfully
2. ✅ All services show healthy status
3. ✅ AI/ML functionality validated
4. ✅ Model inference working
5. ✅ No errors in service logs

**Story Points:** 5
**Priority:** Medium
**Estimated Effort:** 2 hours

**Services (subset using database):**
- ai-core-service (Port 8018)
- ai-pattern-service (Port 8034)
- ai-automation-service-new (Port 8036)
- ai-query-service (Port 8035)
- ai-training-service (Port 8033)

**Note:** Full ML library upgrades (NumPy 2.x, Pandas 3.0) are in Phase 3. This story only rebuilds with Phase 1 base library updates.

**Tasks:**
- [ ] Build AI services in parallel
- [ ] Deploy with extended wait times (60s each)
- [ ] Validate health checks
- [ ] Test AI functionality (query service)
- [ ] Check model loading and inference
- [ ] Monitor resource usage

---

### Story 7: Rebuild Device Management Services

**As a** DevOps engineer
**I want** to rebuild device management services
**So that** they inherit Phase 1 library updates

**Acceptance Criteria:**
1. ✅ All 7 device services rebuilt
2. ✅ All services show healthy status
3. ✅ Device intelligence functional
4. ✅ Health monitoring active
5. ✅ No errors in service logs

**Story Points:** 3
**Priority:** Medium
**Estimated Effort:** 1.5 hours

**Services (7):**
1. device-intelligence-service (Port 8028)
2. device-health-monitor (Port 8019)
3. device-context-classifier (Port 8032)
4. device-database-client (Port 8022)
5. device-recommender (Port 8023)
6. device-setup-assistant (Port 8021)
7. ha-setup-service (Port 8024)

**Tasks:**
- [ ] Build all 7 services in parallel
- [ ] Deploy simultaneously
- [ ] Validate health checks
- [ ] Test device intelligence APIs
- [ ] Verify database client connectivity
- [ ] Check logs for errors

---

### Story 8: Rebuild Automation Services

**As a** DevOps engineer
**I want** to rebuild automation services
**So that** they inherit Phase 1 library updates

**Acceptance Criteria:**
1. ✅ All 6 automation services rebuilt
2. ✅ All services show healthy status
3. ✅ YAML validation working
4. ✅ Blueprint services functional
5. ✅ No errors in service logs

**Story Points:** 3
**Priority:** Medium
**Estimated Effort:** 1.5 hours

**Services (6):**
1. automation-linter (Port 8016) - Already has FastAPI 0.119.0 ✅
2. automation-miner (Port 8029)
3. blueprint-index (Port 8038)
4. blueprint-suggestion-service (Port 8039)
5. yaml-validation-service (Port 8037)
6. api-automation-edge (Port 8041)

**Tasks:**
- [ ] Build all 6 services in parallel
- [ ] Deploy simultaneously
- [ ] Validate health checks
- [ ] Test automation linter
- [ ] Verify YAML validation
- [ ] Test blueprint services
- [ ] Check logs for errors

---

### Story 9: Rebuild Analytics Services

**As a** DevOps engineer
**I want** to rebuild analytics services
**So that** they inherit Phase 1 library updates

**Acceptance Criteria:**
1. ✅ Both analytics services rebuilt
2. ✅ Both services show healthy status
3. ✅ Energy correlation working
4. ✅ ML recommendations functional
5. ✅ No errors in service logs

**Story Points:** 2
**Priority:** Medium
**Estimated Effort:** 1 hour

**Services (2):**
1. energy-correlator (Port 8017)
2. rule-recommendation-ml (Port 8040)

**Tasks:**
- [ ] Build both services in parallel
- [ ] Deploy simultaneously
- [ ] Validate health checks
- [ ] Test energy correlation API
- [ ] Test rule recommendation API
- [ ] Check logs for errors

---

### Story 10: Update and Rebuild Frontend Services

**As a** DevOps engineer
**I want** to update Node.js dependencies and rebuild frontend services
**So that** they have latest build tools and security patches

**Acceptance Criteria:**
1. ✅ Node.js dependencies updated
2. ✅ Both frontend services rebuilt
3. ✅ Both services show healthy status
4. ✅ UI loads without errors
5. ✅ No console errors in browser
6. ✅ Performance maintained (< 3s load time)

**Story Points:** 3
**Priority:** High
**Estimated Effort:** 1.5 hours

**Services (2):**
1. health-dashboard (Port 3000)
2. ai-automation-ui (Port 3001)

**Node.js Updates:**
```json
{
  "@vitejs/plugin-react": "5.1.2",
  "typescript-eslint": "8.53.0",
  "vitest": "4.0.17",
  "@playwright/test": "1.58.1",
  "happy-dom": "20.5.0",
  "msw": "2.12.8"
}
```

**Update Process:**
```bash
# Health Dashboard
cd services/health-dashboard
npm install @vitejs/plugin-react@5.1.2 typescript-eslint@8.53.0
npm install vitest@4.0.17 @playwright/test@1.58.1 happy-dom@20.5.0 msw@2.12.8
cd ../..

# AI Automation UI
cd services/ai-automation-ui
npm install @vitejs/plugin-react@5.1.2 typescript-eslint@8.53.0
npm install vitest@4.0.17 @playwright/test@1.58.1 happy-dom@20.5.0 msw@2.12.8
cd ../..

# Rebuild Docker images
docker-compose build --no-cache health-dashboard ai-automation-ui

# Deploy
docker-compose up -d health-dashboard ai-automation-ui

# Wait and validate
sleep 30
curl -f http://localhost:3000
curl -f http://localhost:3001
```

**Browser Validation:**
- Open http://localhost:3000 (health dashboard)
- Check console for errors
- Verify all widgets load
- Open http://localhost:3001 (AI automation UI)
- Check console for errors
- Verify UI functionality

**Tasks:**
- [ ] Update package.json for health-dashboard
- [ ] Update package.json for ai-automation-ui
- [ ] Run npm install for both services
- [ ] Rebuild Docker images
- [ ] Deploy both services
- [ ] Test UI loading and functionality
- [ ] Check browser console for errors
- [ ] Verify performance (< 3s load time)

---

### Story 11: Comprehensive Phase 1 Validation

**As a** DevOps engineer
**I want** to run comprehensive validation tests across all services
**So that** I can confirm Phase 1 success criteria are met

**Acceptance Criteria:**
1. ✅ All 44+ services show "healthy" status
2. ✅ No errors in service logs (last 100 lines)
3. ✅ All API endpoints respond < 500ms
4. ✅ Frontend dashboards load < 3s
5. ✅ No service restarts in 1 hour
6. ✅ InfluxDB receiving data (verified)
7. ✅ Performance regression < 10%
8. ✅ All unit tests pass
9. ✅ All integration tests pass

**Story Points:** 5
**Priority:** Critical
**Estimated Effort:** 3 hours

**Validation Tests:**

#### 11.1. Service Health Check
```bash
# Check all services
docker ps --format "table {{.Names}}\t{{.Status}}" | grep homeiq

# Identify unhealthy services
docker ps --filter health=unhealthy

# Should output: no containers
```

#### 11.2. API Endpoint Tests
```bash
# Core services
curl -w "%{time_total}s\n" -f http://localhost:8006/health  # data-api
curl -w "%{time_total}s\n" -f http://localhost:8001/health  # websocket
curl -w "%{time_total}s\n" -f http://localhost:8004/health  # admin-api
curl -w "%{time_total}s\n" -f http://localhost:8080/health  # data-retention

# All responses should be < 0.5s
```

#### 11.3. Frontend Load Tests
```bash
# Health dashboard
time curl -f http://localhost:3000 > /dev/null

# AI automation UI
time curl -f http://localhost:3001 > /dev/null

# Both should be < 3s
```

#### 11.4. Data Flow Validation
```bash
# Check InfluxDB for recent data
docker exec homeiq-influxdb influx query '
from(bucket: "home_assistant_events")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "home_assistant_events")
  |> count()
'

# Should show events in last hour
```

#### 11.5. Log Error Check
```bash
# Aggregate errors from all services
cd monitoring
./aggregate-errors.sh

# Review aggregated errors
cat ../logs/rebuild_20260204/phase1/errors/all_errors_*.log
```

#### 11.6. Stability Test (1 hour)
```bash
# Monitor for 1 hour
watch -n 300 'docker ps --format "table {{.Names}}\t{{.Status}}" | grep homeiq'

# Should show no restarts (uptime should increase)
```

#### 11.7. Performance Baseline Comparison
```bash
# Run performance tests
npm run test:performance

# Compare with baseline from Phase 0
# Regression should be < 10%
```

#### 11.8. Unit Tests
```bash
# Run Python unit tests
npm run test:unit:python

# All tests should pass
```

#### 11.9. Integration Tests
```bash
# Run integration tests
npm run test:integration

# All tests should pass
```

**Tasks:**
- [ ] Check all service health statuses
- [ ] Test all API endpoints with timing
- [ ] Test frontend load times
- [ ] Verify data flow to InfluxDB
- [ ] Aggregate and review error logs
- [ ] Run 1-hour stability test
- [ ] Compare performance with baseline
- [ ] Run all unit tests
- [ ] Run all integration tests
- [ ] Generate validation report

---

### Story 12: Generate Phase 1 Completion Report

**As a** DevOps engineer
**I want** to generate a comprehensive Phase 1 completion report
**So that** stakeholders can review results and approve Phase 2

**Acceptance Criteria:**
1. ✅ Report includes all validation results
2. ✅ Service update matrix documented
3. ✅ Performance metrics included
4. ✅ Issues and resolutions documented
5. ✅ Recommendations for Phase 2 included
6. ✅ Sign-off checklist provided

**Story Points:** 2
**Priority:** High
**Estimated Effort:** 1 hour

**Report Sections:**
1. Executive Summary
2. Service Update Matrix (before/after versions)
3. Validation Results (all tests)
4. Performance Metrics (baseline comparison)
5. Issues Encountered and Resolutions
6. Lessons Learned
7. Recommendations for Phase 2
8. Sign-off Checklist

**Report Location:** `docs/planning/phase1-completion-report.md`

**Tasks:**
- [ ] Collect validation results
- [ ] Generate service update matrix
- [ ] Compile performance metrics
- [ ] Document issues and resolutions
- [ ] Write lessons learned
- [ ] Create Phase 2 recommendations
- [ ] Generate sign-off checklist
- [ ] Save report to docs/planning/

---

## Implementation Timeline

| Day | Stories | Focus | Duration |
|-----|---------|-------|----------|
| **Day 1** | 1-3 | Setup & Infrastructure | 3.5 hours |
| **Day 2** | 4 | Core Services | 4 hours |
| **Day 3** | 5-7 | Integration & AI Services | 5.5 hours |
| **Day 4** | 8-10 | Automation, Analytics, Frontend | 4 hours |
| **Day 5** | 11-12 | Validation & Reporting | 4 hours |

**Total Effort:** ~21 hours (~1 week with buffer)

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Service fails to rebuild | Medium | High | Rollback to Phase 0 backup |
| Health check failures | Medium | High | Extended wait times, manual verification |
| Performance regression | Low | Medium | Performance baseline comparison |
| Data loss | Low | Critical | Phase 0 backup available |
| Breaking changes | Medium | High | Sequential rebuild with validation |

## Rollback Plan

If critical issues arise:

```bash
# Stop affected service(s)
docker-compose stop {service}

# Restore pre-rebuild image
docker tag homeiq-{service}:latest homeiq-{service}:failed-phase1
docker tag homeiq-{service}:pre-rebuild homeiq-{service}:latest

# Restart service
docker-compose up -d {service}

# Verify health
docker ps --filter name={service}
curl -f http://localhost:{port}/health
```

**Full Rollback:**
Refer to Phase 0 backup: `backups/phase0_20260204_111804/MANIFEST.md`

## Monitoring During Phase 1

**Start Monitoring:**
```bash
cd monitoring
./start-all.sh
```

**View Dashboard:**
```bash
cd monitoring
./build-dashboard.sh
```

**Monitor Logs:**
```bash
# Phase 1 logs
tail -f logs/rebuild_20260204/phase1/build/*.log
tail -f logs/rebuild_20260204/phase1/health/*.log
tail -f logs/rebuild_20260204/phase1/errors/*.log
```

**Aggregate Errors:**
```bash
cd monitoring
./aggregate-errors.sh
```

## Documentation Updates

After Phase 1 completion:

1. ✅ Update `requirements-base.txt` comments
2. ✅ Update `REBUILD_STATUS.md`
3. ✅ Update `docs/planning/rebuild-status.md`
4. ✅ Generate `docs/planning/phase1-completion-report.md`
5. ✅ Update service dependency documentation
6. ✅ Tag Docker images as `phase1-complete`

## Next Phase Prerequisites

Before starting Phase 2:

1. ✅ All Phase 1 success criteria met
2. ✅ Phase 1 completion report reviewed and approved
3. ✅ All services stable for 24 hours
4. ✅ Performance validated against baseline
5. ✅ Team briefed on Phase 2 requirements

---

**Epic Owner:** DevOps Team
**Reviewers:** Technical Lead, Product Owner
**Created:** February 4, 2026
**Target Completion:** February 11, 2026
