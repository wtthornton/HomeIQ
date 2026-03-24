# Phase 5: Quick Reference Guide

**Status:** Ready for execution | **Target Date:** Week of March 5, 2026

**2026-03-23:** Canonical scale is **~58** production-profile containers / **62** Compose definitions — [service-groups](../architecture/service-groups.md). Prefer `./scripts/start-stack.sh` and **`--profile production`** on any manual `docker compose -f domains/...` commands below.

---

## 5-Minute Overview

**What:** Deploy full stack (~58 prod-profile containers + domain compose files) to production
**When:** Tuesday-Thursday, 9 PM - 6 AM (off-peak)
**Duration:** 3-4 hours deployment + 48 hours validation
**Risk:** LOW (comprehensive backups, tiered rollback, 4 go/no-go gates)

---

## Pre-Deployment (Day 1)

```bash
# 1. Run health checks (33 services)
scripts/pre-deployment-health-check.sh

# 2. Run all tests
pytest tests/ -v  # 704+ tests must pass

# 3. Build all services
time docker buildx bake full  # ~25-30 min

# 4. Verify databases
# PostgreSQL: 8 schemas, all Alembic migrations run
# InfluxDB: All buckets created

# 5. Create backups
git tag deployment-phase5-pre-$(date +%Y%m%d)
docker exec postgres pg_dump -U homeiq homeiq > backups/phase5-pre-*.sql
docker exec influxdb influx export --file backups/phase5-pre-*.ndjson

# ✅ Gate 1 Check: ALL PASS? → Proceed to Tier 1
```

---

## Tier-by-Tier Deployment

### Tier 1: Critical Infrastructure (Hour 1)

```bash
# 1. Deploy core-platform
docker compose -f domains/core-platform/compose.yml --profile production up -d --pull always

# 2. Health checks
curl -f http://localhost:8001/health  # websocket-ingestion
curl -f http://localhost:8006/health  # data-api
curl -f http://localhost:8004/health  # admin-api

# 3. Smoke test
pytest tests/smoke/tier1_health.py -v

# ✅ Gate 2 Check: 3/3 healthy? → Proceed to Tier 2
```

### Tier 2: Data Collection (Hour 2)

```bash
# 1. Deploy health-dashboard + data-retention
docker compose -f domains/core-platform/compose.yml --profile production up -d health-dashboard data-retention

# 2. Deploy all data-collectors
docker compose -f domains/data-collectors/compose.yml --profile production up -d

# 3. Health checks: 12/12 should be healthy
docker ps | grep -E "health-dashboard|data-retention|weather|smart-meter|sports|calendar|carbon|electricity|air-quality|log-aggregator"

# ✅ Gate 3 Check: 12/12 healthy? → Proceed to Tier 3
```

### Tier 3: ML/AI (Hour 3-4)

```bash
# 1. Deploy ml-engine
docker compose -f domains/ml-engine/compose.yml --profile production up -d

# 2. Wait for model loading (5-10 min - NORMAL)
sleep 30 && docker logs openvino-service | tail -20

# 3. Health checks: 9/9 should be healthy
for port in 8026 8025 8018 8033 8028; do
  curl -f http://localhost:$port/health && echo "✅ $port" || echo "❌ $port"
done
```

### Tiers 4-9: Remaining Services (Hour 5-6)

```bash
# Tier 4: Automation Core
docker compose -f domains/automation-core/compose.yml --profile production up -d

# Tier 5: Blueprints
docker compose -f domains/blueprints/compose.yml --profile production up -d

# Tier 6: Energy Analytics
docker compose -f domains/energy-analytics/compose.yml --profile production up -d

# Tier 7: Device Management
docker compose -f domains/device-management/compose.yml --profile production up -d

# Tier 8: Pattern Analysis
docker compose -f domains/pattern-analysis/compose.yml --profile production up -d

# Tier 9: Frontends
docker compose -f domains/frontends/compose.yml --profile production up -d

# ✅ Gate 4 Check: All production-profile services healthy? → Deployment complete
```

---

## Deployment Checklist

```
PRE-DEPLOYMENT (Day 1)
  ✅ Health checks: 33/33 passing
  ✅ Tests: 704+ passing
  ✅ Docker builds: 53 services
  ✅ Databases ready: PostgreSQL 17 + InfluxDB
  ✅ Backups created: Git tag + DB dumps

DEPLOYMENT (Day 2)
  ✅ Tier 1 (Hour 1): 3/3 critical services healthy
  ✅ Tier 2 (Hour 2): 12/12 data services healthy
  ✅ Tier 3 (Hour 3-4): 9/9 ML services healthy
  ✅ Tiers 4-9 (Hour 5-6): 26/26 remaining services healthy
  ✅ All production-profile services responding to /health

VALIDATION (Day 3)
  ✅ Integration tests: ALL PASS
  ✅ E2E Playwright tests: ALL PASS
  ✅ Error rate: <0.5%
  ✅ No critical alerts
  ✅ No repeated restart loops

MONITORING (Day 4-5)
  ✅ 24-hour continuous monitoring
  ✅ Performance metrics within baseline
  ✅ Zero data loss
  ✅ User workflows tested
  ✅ Team sign-off: READY FOR OPERATIONS
```

---

## If Something Goes Wrong

### Single Service Down? (e.g., ai-core-service)

```bash
# 1. Restart service (2-5 min)
docker compose -f domains/ml-engine/compose.yml --profile production up -d ai-core-service

# 2. Check health
curl -f http://localhost:8018/health

# 3. If still broken: Rollback that service
git checkout HEAD~1 -- domains/ml-engine/ai-core-service/Dockerfile
docker buildx bake ai-core-service
docker compose -f domains/ml-engine/compose.yml --profile production up -d ai-core-service
```

### Entire Domain Down? (e.g., all ml-engine)

```bash
# 1. Stop domain (5-15 min)
docker compose -f domains/ml-engine/compose.yml --profile production down

# 2. Revert changes
git checkout HEAD~1 -- domains/ml-engine/

# 3. Rebuild and restart
docker buildx bake ml-engine
docker compose -f domains/ml-engine/compose.yml --profile production up -d

# 4. Verify: All services healthy?
```

### Database Unreachable? (CRITICAL)

```bash
# 1. Check if containers running
docker ps | grep -E "postgres|influxdb"

# 2. If PostgreSQL down:
docker restart postgres
psql -U homeiq homeiq -c "SELECT 1"  # Verify connection

# 3. If InfluxDB down:
docker restart influxdb
curl -f http://localhost:8086/health  # Verify health

# 4. If unrecoverable:
# ⚠️ FULL SYSTEM ROLLBACK (see "Full System Rollback" below)
```

### Full System Rollback (Last Resort - <30 min)

```bash
# ⚠️ REQUIRES APPROVAL: Technical Lead + DevOps

# 1. Stop everything
docker compose down

# 2. Revert to pre-deployment state
git checkout deployment-phase5-pre-$(date +%Y%m%d)

# 3. Restore databases
psql -U homeiq homeiq < backups/phase5-pre-deployment-*.sql
docker exec influxdb influx restore /backups/phase5-pre-deployment-*.ndjson

# 4. Restart everything
docker compose up -d

# 5. Wait for recovery (10-15 min)
watch -n 5 'docker ps | grep healthy | wc -l'  # Should reach 50

# 6. Verify
scripts/pre-deployment-health-check.sh

# 7. Notify team: Rollback complete, root cause analysis in progress
```

---

## Success Metrics

| Metric | Target | Go Threshold |
|---|---|---|
| **Uptime** | 99.9% | ✅ 100% |
| **Services Healthy** | All prod-profile | ✅ All responding |
| **Error Rate** | <0.5% | ✅ <1% OK |
| **API Response Time** | <100ms p95 | ✅ <baseline+10% |
| **Test Pass Rate** | 100% | ✅ 704/704 |
| **Data Loss** | 0 | ✅ 0 |

---

## Rollback Timeline

| Scenario | Time | Action |
|---|---|---|
| Single service restart | 2-5 min | `docker restart <service>` |
| Single service rollback | 5-10 min | Rebuild + restart service |
| Domain rollback | 5-15 min | Revert + rebuild all in domain |
| **Full system rollback** | **15-30 min** | **Restore from backup** |

---

## Key Contacts & Escalation

```
DEPLOYMENT LEAD: [DevOps Engineer]
TECHNICAL LEAD: [Senior Engineer]
DATABASE ADMIN: [Database Specialist]
ON-CALL: [Person on duty during deployment]

ESCALATION PATH:
1. On-Call Engineer
2. Deployment Lead
3. Technical Lead
4. Engineering Manager
```

---

## Real-Time Monitoring

During deployment, keep these windows open:

```bash
# Terminal 1: Real-time logs
docker logs -f websocket-ingestion | grep -E "ERROR|CRITICAL"

# Terminal 2: Health dashboard
watch -n 2 'curl -s http://localhost:3000/health'

# Terminal 3: Service status
watch -n 2 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# Terminal 4: Prometheus metrics
# http://localhost:9090/graph?query=up

# Terminal 5: Grafana dashboards
# http://localhost:3001
```

---

## Deployment Window Reminder

```
🕐 9:00 PM - Tier 1 (websocket, data-api, admin-api)
🕐 10:00 PM - Tier 2 (health-dashboard, data-collectors)
🕐 11:00 PM - Tier 3 (ML services, wait for model loading)
🕐 12:00 AM - Tiers 4-8 (automation, blueprints, energy, devices, patterns)
🕐 1:00 AM - Tier 9 (frontends)
🕐 1:30 AM - Validation & sign-off
🕐 6:00 AM - Monitoring shift continues
```

---

## Post-Deployment Sign-Off

When all checks pass:

```markdown
✅ DEPLOYMENT COMPLETE

Date: [Date]
Duration: [HH:MM]
Services: all production-profile healthy
Tests: 704/704 passing
Errors: <0.5%

Approved by:
- [ ] Deployment Lead
- [ ] Technical Lead
- [ ] DevOps Lead

Ready for Phase 6: Post-Deployment Validation
```

---

**For detailed information, see:**
- Full Plan: `docs/planning/phase-5-deployment-plan.md`
- Rollback Procedures: See "Rollback Procedures" section in full plan
- Success Criteria: See "Success Criteria & Go/No-Go Gates" in full plan
