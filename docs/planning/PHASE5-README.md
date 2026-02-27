# Phase 5: Production Deployment — Complete Package

**Status:** Ready for Execution | **Target Date:** Week of March 5, 2026

This directory contains all documentation and tools needed to deploy Phase 5 (production deployment of all completed work from Phases 0-4b).

---

## Quick Links

| Document | Purpose | Audience |
|---|---|---|
| **[phase-5-deployment-plan.md](./phase-5-deployment-plan.md)** | Comprehensive 6,500-word deployment plan | Engineers, DevOps, Technical Lead |
| **[phase-5-quick-reference.md](./phase-5-quick-reference.md)** | 5-minute quick reference with key commands | Operations Team, On-Call |
| **[../scripts/deploy-phase-5.sh](../../scripts/deploy-phase-5.sh)** | Automated deployment script | DevOps Engineer |
| **[rebuild-status.md](./rebuild-status.md)** | Current rebuild phase status (Phases 0-4 complete) | Management, Team Lead |

---

## What's Being Deployed

### Services: 50 Microservices + 3 Frontends

| Group | Count | Services | Status |
|---|---|---|---|
| **Core Platform** | 6 | websocket-ingestion, data-api, admin-api, health-dashboard, data-retention, ha-simulator | ✅ Ready |
| **Data Collectors** | 8 | weather, smart-meter, sports, air-quality, carbon, electricity, calendar, log-aggregator | ✅ Ready |
| **ML Engine** | 9 | openvino, ml, ner, openai, rag, ai-core, training, device-intel, model-prep | ✅ Ready |
| **Automation Core** | 7 | ha-ai-agent, ai-automation, query, yaml-validation, linter, code-executor, traces | ✅ Ready |
| **Blueprints** | 4 | blueprint-index, suggestion, rule-recommendation, automation-miner | ✅ Ready |
| **Energy Analytics** | 3 | energy-correlator, energy-forecasting, proactive-agent | ✅ Ready |
| **Device Management** | 8 | health-monitor, classifier, setup, db-client, recommender, activity, activity-writer, ha-setup | ✅ Ready |
| **Pattern Analysis** | 2 | ai-pattern, api-automation-edge | ✅ Ready |
| **Frontends** | 3 | health-dashboard, ai-automation-ui, observability-dashboard | ✅ Ready |

**Total:** 50 services + 3 frontends = **53 deployable units**

### Library Upgrades Included

| Library | From | To | Impact |
|---|---|---|---|
| **SQLAlchemy** | 1.4.x | 2.0.36+ | Core database ORM |
| **FastAPI** | 0.115+ | 0.119+ | API framework |
| **Pydantic** | 2.5+ | 2.9+ | Data validation |
| **asyncpg** | Various | 0.30+ | PostgreSQL async driver |
| **pytest** | 8.1+ | 8.3+ | Testing framework |
| **aiohttp** | 3.9+ | 3.9+ | Async HTTP client |

### Features Deployed

- ✅ **Frontend Redesign** (Phase 4b): 29 tabs → 14 consolidated pages, new design system
- ✅ **SQLite → PostgreSQL Migration** (Epics): Schema-per-domain pattern, Alembic migrations
- ✅ **Agent Evaluation Framework** (Epics): 4 agents, 20 evaluators, 5-level pyramid
- ✅ **Activity Recognition Integration** (Epics): Cross-agent context
- ✅ **Deploy Pipeline Fixes** (Epics): Hardware-aware templates, LLM improvements
- ✅ **Operational Readiness** (Epics): Prometheus, Grafana, backups, runbooks, E2E tests

---

## Deployment Timeline

### Pre-Deployment (Day 1)
- Health check baseline (33 services with /health endpoints)
- Test suite validation (704+ tests)
- Docker build verification (53 services)
- Database readiness checks (PostgreSQL 17 + InfluxDB)
- Backup creation and verification

### Deployment (Day 2-3)

**Off-Peak Window: 9 PM - 6 AM (3-4 hours)**

| Time | Tier | Services | Count |
|---|---|---|---|
| **Hour 1** | Tier 1 | websocket-ingestion, data-api, admin-api | 3 |
| **Hour 2** | Tier 2 | health-dashboard, data-retention, data-collectors | 12 |
| **Hour 3-4** | Tier 3 | ML/AI services (openvino, ml-service, ai-core, etc.) | 9 |
| **Hour 5** | Tiers 4-8 | automation, blueprints, energy, devices, patterns | 24 |
| **Hour 6** | Tier 9 | frontends (dashboards, Jaeger) | 3 |

### Validation (Day 3)
- Full health check (50/50 services)
- Integration tests (all pass)
- E2E tests (Playwright)
- Error rate verification (<0.5%)
- Manual user workflow testing

### Monitoring (Day 4-5)
- Continuous monitoring (24x7)
- Alert thresholds enforcement
- Performance baseline verification
- Zero data loss confirmation
- Team sign-off

---

## Success Criteria

### Critical Gates (Must Pass to Proceed)

**Gate 1: Pre-Deployment Validation**
- [ ] All health checks passing
- [ ] 704+ tests passing (100%)
- [ ] Docker builds successful
- [ ] Database schemas verified
- [ ] Backups created

**Gate 2: Tier 1 Critical Services**
- [ ] websocket-ingestion healthy
- [ ] data-api queries working
- [ ] admin-api responding
- [ ] No error spikes
- [ ] Smoke tests passing

**Gate 3: Tier 2 Services**
- [ ] 12 data services healthy
- [ ] External APIs connected
- [ ] Dashboard loading
- [ ] No cascading failures

**Gate 4: Full System Health (48 hours)**
- [ ] All 50 services healthy (100%)
- [ ] Error rate <0.5%
- [ ] Response time within baseline
- [ ] Zero unplanned restarts
- [ ] Data integrity verified

---

## Rollback Procedures

### Single Service (2-5 minutes)
```bash
docker compose -f domains/<domain>/compose.yml up -d <service>
```

### Domain (5-15 minutes)
```bash
git checkout HEAD~1 -- domains/<domain>/
docker buildx bake <domain>
docker compose -f domains/<domain>/compose.yml up -d
```

### Full System (15-30 minutes, REQUIRES APPROVAL)
```bash
docker compose down
git checkout deployment-phase5-pre-$(date +%Y%m%d)
psql homeiq < backups/phase5-pre-deployment-*.sql
docker compose up -d
```

---

## Deployment Script Usage

### Automated Deployment

```bash
# Make script executable
chmod +x scripts/deploy-phase-5.sh

# Deploy specific tier
./scripts/deploy-phase-5.sh tier1      # Deploy Tier 1 only
./scripts/deploy-phase-5.sh tier2      # Deploy through Tier 2
./scripts/deploy-phase-5.sh all        # Full deployment + validation

# Script outputs
# - Real-time logs to terminal with color-coded status
# - Persistent logs to: deployment_phase5_YYYYMMDD_HHMMSS.log
# - Git tags created at each tier for rollback capability
```

### Manual Deployment (If Preferred)

See [phase-5-quick-reference.md](./phase-5-quick-reference.md) for step-by-step commands.

---

## Monitoring During Deployment

### Real-Time Dashboards

```
Prometheus: http://localhost:9090
Grafana: http://localhost:3001
Jaeger Traces: http://localhost:16686
Health Dashboard: http://localhost:3000
```

### Key Metrics to Watch

| Metric | Target | Alert |
|---|---|---|
| Services Healthy | 50/50 | <50/50 = problem |
| Error Rate | <0.5% | >5% = escalate |
| Response Time | <100ms p95 | >2x baseline = investigate |
| Uptime | 99.9%+ | Any service down >2 min |
| Database Queries | Working | Any failed query = CRITICAL |

---

## Key Decision: Phase 3 (ML Library Upgrades) is NOT a Blocker

**Phase 5 deploys successfully WITHOUT Phase 3:**

- Phase 1-4 are complete blocking prerequisites ✅
- ML services work with current pinned library versions ✅
- Phase 3 requires 2+ weeks production stability verification ⏳
- Phase 3 scheduled for late March (post-Phase 5 in parallel sprint) 📅

**Rationale:**
- numpy, scikit-learn, pandas upgrades are optional enhancements
- No code changes needed if libraries stay pinned
- Reduces deployment risk by deferring large library upgrades
- Allows more thorough testing of Phase 1-4 changes first

---

## Communication

### Pre-Deployment (72 Hours Before)
- [ ] Team notification (see template in main plan)
- [ ] Confirm on-call coverage
- [ ] Schedule war room
- [ ] Verify rollback team available

### During Deployment
- [ ] Real-time Slack updates (#homeiq-deployment channel)
- [ ] Status updates every 30 minutes minimum
- [ ] Immediate escalation for any failures

### Post-Deployment
- [ ] All-hands announcement
- [ ] Share deployment report
- [ ] Schedule post-mortem (if any issues)
- [ ] Move to Phase 6 post-deployment validation

---

## Files Modified/Created for Phase 5

### Documentation (Main Deliverables)
- ✅ `docs/planning/phase-5-deployment-plan.md` (6,500+ words)
- ✅ `docs/planning/phase-5-quick-reference.md` (Quick commands)
- ✅ `docs/planning/PHASE5-README.md` (This file)

### Automation Scripts
- ✅ `scripts/deploy-phase-5.sh` (Automated deployment)
- ✅ `scripts/pre-deployment-health-check.sh` (Health baseline)
- ✅ `scripts/post-deployment-health-check.sh` (Validation)

### Configuration
- ✅ `docker-compose.yml` (All 9 domains included)
- ✅ `docker-bake.hcl` (Parallel builds configured)
- ✅ `domains/*/compose.yml` (Domain-specific configs)

---

## Deployment Checklist

### Before Starting
- [ ] Read full plan: `docs/planning/phase-5-deployment-plan.md`
- [ ] Review quick reference: `docs/planning/phase-5-quick-reference.md`
- [ ] Notify stakeholders (72 hours before)
- [ ] Confirm on-call team assembled
- [ ] Verify backup systems operational

### Day 1: Validation
- [ ] Run pre-deployment health checks
- [ ] Execute test suite (704+ tests)
- [ ] Build Docker images (53 services)
- [ ] Verify databases ready
- [ ] Create backups and git tags

### Day 2: Deployment
- [ ] Execute deployment script or manual commands
- [ ] Monitor each tier health checks
- [ ] Verify no cascading failures
- [ ] Document any issues

### Day 3-5: Validation & Monitoring
- [ ] Run integration tests
- [ ] Run E2E tests
- [ ] Verify error rates acceptable
- [ ] Continuous 24x7 monitoring
- [ ] Team sign-off

---

## Success Definition

**Deployment is successful when:**
1. ✅ All 50 services healthy (responding to /health)
2. ✅ All 704+ tests passing
3. ✅ Error rate <0.5%
4. ✅ Zero data loss
5. ✅ Zero unplanned restarts in first 24 hours
6. ✅ Response times within baseline
7. ✅ Team sign-off obtained

---

## Support & Escalation

| Issue | Action |
|---|---|
| Single service unhealthy | Restart service, check logs |
| Multiple services down | Restart domain |
| Database error | Check PostgreSQL/InfluxDB health immediately |
| Error rate spike | Investigate root cause, consider rollback |
| Complete failure | Execute full system rollback |

**Escalation Path:**
1. On-Call Engineer
2. Deployment Lead
3. Technical Lead
4. Engineering Manager

---

## Next Steps After Phase 5

After Phase 5 is complete and production-stable:

**Phase 6: Post-Deployment Validation (3 days)**
- Comprehensive health checks
- Performance baseline verification
- User acceptance testing
- Optimization recommendations

**Phase 3: ML Library Upgrades (Late March)**
- Optional numpy, scikit-learn, pandas upgrades
- Can be done in parallel with normal operations
- Requires Phase 1-4 stability verification (2+ weeks)

---

## Questions?

Refer to:
- **Full details:** `docs/planning/phase-5-deployment-plan.md`
- **Quick commands:** `docs/planning/phase-5-quick-reference.md`
- **Automation:** `scripts/deploy-phase-5.sh --help`
- **Team:** Contact [Deployment Lead] or [Technical Lead]

---

**Phase 5 Status:** ✅ READY FOR EXECUTION

**Last Updated:** February 27, 2026
**Next Review:** March 5, 2026 (Deployment day)
