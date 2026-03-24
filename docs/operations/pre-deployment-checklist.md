# Pre-Deployment Checklist

**Project:** HomeIQ Phase 5 Production Deployment
**Target Date:** Week of March 5, 2026
**Deployment Window:** Tuesday-Thursday, 9 PM - 6 AM (off-peak)

---

## Automated Validation

Run the pre-deployment validation script:

```bash
./scripts/pre-deployment-check.sh          # Full validation
./scripts/pre-deployment-check.sh --quick   # Health checks only
```

---

## 72 Hours Before Deployment

- [ ] Schedule deployment window (confirm off-peak timing)
- [ ] Notify all stakeholders via email/Slack
- [ ] Confirm on-call engineer coverage
- [ ] Review Phase 5 plan: `docs/planning/phase-5-deployment-plan.md`
- [ ] Verify backup infrastructure is ready

## 24 Hours Before Deployment

### Health Checks

- [ ] Run `./scripts/pre-deployment-check.sh` — all gates pass
- [ ] 33+ service health endpoints responding
- [ ] 2 HA-dependent services in expected degraded state (not more)

### Test Suite

- [ ] Python test suite: `pytest tests/ -v` — 704+ tests passing (100% pass rate)
- [ ] Frontend tests: `cd domains/core-platform/health-dashboard && npm test`
- [ ] Frontend tests: `cd domains/frontends/ai-automation-ui && npm test`
- [ ] Integration tests: `pytest tests/integration/ -v`
- [ ] E2E Playwright tests: `pytest tests/e2e/playwright/ -v`

### Docker

- [ ] Docker Compose config validates: `docker compose config --quiet`
- [ ] All 53 images build: `docker buildx bake full` (estimated 25-30 min)
- [ ] Image count verified: `docker images | grep homeiq | wc -l` (should be 53)
- [ ] Project group verification: `./scripts/domain.sh verify` — all containers in correct `homeiq-<domain>` groups

### Databases

- [ ] PostgreSQL 17 container running and accepting connections
- [ ] All 8 schemas exist: core, automation, agent, blueprints, energy, devices, patterns, rag
- [ ] Alembic migrations up to date on all 13 services
- [ ] InfluxDB 2.8.0 healthy: `curl -f http://localhost:8086/health`
- [ ] InfluxDB buckets verified

### Monitoring

- [ ] Prometheus scraping all targets: `curl http://localhost:9090/api/v1/targets`
- [ ] Grafana dashboards accessible on port 3002
- [ ] Alert rules configured (15 alert rules)

## 6 Hours Before Deployment

- [ ] Final infrastructure verification
- [ ] Monitoring dashboard confirmed operational
- [ ] On-call team positioned
- [ ] Deployment war room created (Slack #homeiq-deployment)
- [ ] Team briefed on rollback procedures

## T-1 Hour (Deployment Day)

- [ ] Final health check: `./scripts/pre-deployment-check.sh`
- [ ] Backups created and verified (see below)
- [ ] Git tags pushed
- [ ] Monitoring dashboard live
- [ ] Team assembled and ready

### Backup Verification

```bash
# 1. Git tag
git tag -a deployment-phase5-pre-$(date +%Y%m%d) \
  -m "Pre-Phase 5 deployment snapshot"

# 2. PostgreSQL backup
docker exec homeiq-postgres pg_dump -U homeiq homeiq > \
  backups/phase5-pre-deployment-$(date +%Y%m%d_%H%M%S).sql

# 3. InfluxDB backup
docker exec homeiq-influxdb influx export \
  --file /tmp/phase5-pre-deployment.ndjson

# 4. Verify backup integrity
file backups/phase5-pre-deployment-*.sql | grep -q "ASCII text"
```

---

## Deployment Execution Order

| Tier | Script | Services | Gate |
|---|---|---|---|
| **1** | `./scripts/deploy-tier1.sh` | InfluxDB, PostgreSQL, websocket, data-api, admin-api | 30-min health loop |
| **2** | `./scripts/deploy-tier2.sh` | health-dashboard, data-retention, 8 data-collectors | 15-min health loop |
| **3** | `./scripts/deploy-tier3.sh` | 7 ML/AI services (extended timeout for model loading) | Model verification |
| **4-8** | `./scripts/deploy-tiers4-8.sh` | 24 domain services across 5 groups | Per-tier health gate |
| **9** | `./scripts/deploy-tier9.sh` | Jaeger, observability-dashboard, ai-automation-ui | Frontend accessibility |

---

## Go/No-Go Decision Matrix

| Metric | Go Threshold | Action if Not Met |
|---|---|---|
| Services Healthy | 48+/50 (96%) | Investigate, fix, or defer |
| Test Pass Rate | 100% | Fix failing tests before deploying |
| Error Rate | <0.5% | Investigate root cause |
| Response Time | <baseline + 10% | Check resource constraints |
| Database Accessible | 100% | Do NOT proceed |
| Backups Created | Yes | Do NOT proceed |

---

## Post-Deployment

- [ ] All production-profile services healthy (100% — see [service-groups](../architecture/service-groups.md))
- [ ] All tests passing (100%)
- [ ] Error rate < 0.5%
- [ ] Backups verified post-deployment
- [ ] Incident log clean (no critical issues)
- [ ] Start monitoring: `./scripts/post-deployment-monitor.sh`
- [ ] Team debriefing scheduled

---

## Rollback Quick Reference

| Scenario | Command | Time |
|---|---|---|
| Single tier rollback | `./scripts/deploy-tierN.sh --rollback` | 2-5 min |
| Domain rollback | `./scripts/deploy-tiers4-8.sh --rollback N` | 5-15 min |
| Full system rollback | See `docs/planning/phase-5-deployment-plan.md` | 15-30 min |

---

## Troubleshooting: Container Grouping

Containers must appear under their correct `homeiq-<domain>` group in Docker Desktop.
If a container appears as a standalone (outside its group), it was started incorrectly.

**Diagnosis:**
```bash
./scripts/domain.sh verify
```

**Common cause:** Running `docker compose up` from the project root or running a single
service directly (e.g., `docker compose up ai-automation-ui`) outside its domain compose file.

**Fix:**
```bash
# 1. Remove the orphaned container
docker stop <container-name> && docker rm <container-name>

# 2. Restart via domain.sh (ensures correct project name)
./scripts/domain.sh start <domain> [service]

# Example: fix orphaned ai-automation-ui
docker stop homeiq-ai-automation-ui && docker rm homeiq-ai-automation-ui
./scripts/domain.sh start frontends ai-automation-ui
```

**Prevention:** Always use `./scripts/domain.sh` or `./scripts/start-stack.sh` to manage
services. Use `./scripts/start-stack.sh` or `.\scripts\start-stack.ps1` — never `docker compose up` from the project root. See [Deployment Quick Reference](../deployment/DEPLOYMENT_QUICK_REFERENCE.md).

---

**Approved By:** _______________
**Date:** _______________
