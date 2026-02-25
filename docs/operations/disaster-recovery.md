# Disaster Recovery Procedures

**Version:** 1.0
**Last Updated:** 2026-02-24
**Maintainer:** HomeIQ Platform Team

---

## Overview

This document defines the disaster recovery (DR) procedures for the HomeIQ platform. It covers backup verification, restoration procedures, failover strategies, data reconciliation, and communication protocols.

### Recovery Objectives

| Metric | Target | Notes |
|--------|--------|-------|
| **RPO** (Recovery Point Objective) | 24 hours | Daily backups at 02:00 UTC |
| **RTO** (Recovery Time Objective) | 1 hour | For Tier 1 services |
| **MTTR** (Mean Time to Repair) | 30 minutes | With runbook procedures |

### Service Tiers

| Tier | Services | Recovery Priority |
|------|----------|-------------------|
| **Tier 1 (Critical)** | websocket-ingestion, data-api, InfluxDB, admin-api, health-dashboard | Restore first, within 30 minutes |
| **Tier 2 (Essential)** | PostgreSQL, data-retention, ha-setup-service, weather-api, smart-meter-service | Restore second, within 1 hour |
| **Tier 3 (AI/ML)** | ai-core-service, device-intelligence, openvino-service, ml-service | Restore third, within 4 hours |
| **Tier 4+** | All other services | Restore as capacity allows |

---

## Backup Verification Schedule

### Automated Verification

The backup scheduler container (`infrastructure/backup/`) performs daily backups with a built-in health check that verifies the last backup timestamp is within 25 hours.

### Manual Verification (Weekly)

Run the automated test every week to verify end-to-end backup/restore integrity:

```bash
./scripts/test-backup-restore.sh
```

This script:
1. Creates a temporary PostgreSQL container
2. Seeds it with representative data
3. Runs `backup-postgres.sh`
4. Wipes the database
5. Runs `restore-postgres.sh`
6. Validates row counts and data integrity
7. Tests per-schema restore isolation
8. Cleans up all test resources

### Monthly Verification Checklist

- [ ] Run `./scripts/test-backup-restore.sh` -- all tests pass
- [ ] Verify backup file sizes are reasonable (not suspiciously small)
- [ ] Verify backup retention (files older than 30 days are deleted)
- [ ] Spot-check one backup by listing contents: `./scripts/restore-postgres.sh <file> --list`
- [ ] Review backup scheduler logs: `docker logs homeiq-backup-scheduler --tail 100`
- [ ] Verify InfluxDB backup exists: check `backups/` directory for recent InfluxDB archives
- [ ] Document verification in `docs/TAPPS_RUNLOG.md`

### Backup Storage Locations

| Data Store | Backup Location | Format | Retention |
|------------|----------------|--------|-----------|
| PostgreSQL (full) | `backups/postgres/homeiq_full_*.dump` | pg_dump custom | 30 days |
| PostgreSQL (per-schema) | `backups/postgres/homeiq_{schema}_*.dump` | pg_dump custom | 30 days |
| InfluxDB | Container volume or `backups/influxdb/` | InfluxDB native backup | 30 days |
| SQLite (legacy) | `backups/` via `backup-all.sh` | Raw .db copy | Until migration complete |
| Docker volumes | `backups/` via `backup-all.sh` | tar.gz | Manual |

---

## Restore Procedures

### PostgreSQL Full Restore

**When to use:** Complete database loss, corrupted database, or migration from backup.

```bash
# 1. Stop all services that depend on PostgreSQL
docker compose stop data-api admin-api ha-ai-agent-service ai-automation-service-new

# 2. Verify backup file
./scripts/restore-postgres.sh backups/postgres/homeiq_full_YYYYMMDD_HHMMSS.dump --list

# 3. Restore (will prompt for confirmation)
./scripts/restore-postgres.sh backups/postgres/homeiq_full_YYYYMMDD_HHMMSS.dump

# 4. Verify restoration
docker exec homeiq-postgres psql -U homeiq -d homeiq -c "
SELECT schemaname, COUNT(*) as tables, SUM(n_live_tup) as rows
FROM pg_stat_user_tables
WHERE schemaname IN ('core','automation','agent','blueprints','energy','devices','patterns','rag')
GROUP BY schemaname
ORDER BY schemaname;
"

# 5. Restart dependent services
docker compose up -d data-api admin-api ha-ai-agent-service ai-automation-service-new

# 6. Verify services are healthy
./scripts/check-service-health.sh
```

### PostgreSQL Per-Schema Restore

**When to use:** Corruption or data loss in a single domain schema.

```bash
# Restore only the affected schema (other schemas remain untouched)
./scripts/restore-postgres.sh backups/postgres/homeiq_energy_YYYYMMDD_HHMMSS.dump --schema energy

# Restart only the services that use that schema
docker compose restart energy-correlator energy-forecasting proactive-agent-service
```

### InfluxDB Restore

**When to use:** Time-series data loss or InfluxDB corruption.

```bash
# 1. Stop websocket-ingestion (the primary writer)
docker compose stop websocket-ingestion

# 2. Run the InfluxDB restore script
./scripts/restore-influxdb.sh backups/influxdb/YYYYMMDD_HHMMSS/

# 3. Restart ingestion
docker compose up -d websocket-ingestion

# 4. Verify data is flowing
curl -s http://localhost:8001/health | python -m json.tool
```

### Full System Restore

**When to use:** Complete system failure, new hardware, or disaster recovery site setup.

```bash
# 1. Ensure Docker is running and .env is configured
cp infrastructure/env.example .env
# Edit .env with correct values

# 2. Start infrastructure containers first
docker compose up -d postgres influxdb

# 3. Wait for databases to be ready
sleep 30

# 4. Restore PostgreSQL
./scripts/restore-postgres.sh backups/postgres/homeiq_full_YYYYMMDD_HHMMSS.dump --force

# 5. Restore InfluxDB
./scripts/restore-influxdb.sh backups/influxdb/YYYYMMDD_HHMMSS/

# 6. Start all services (respecting dependency order)
docker compose up -d

# 7. Verify system health
./scripts/check-service-health.sh

# 8. Verify data-api can reach both databases
curl -s http://localhost:8006/health | python -m json.tool
curl -s http://localhost:8004/api/v1/health | python -m json.tool
```

---

## Failover Procedures

### PostgreSQL Down -- SQLite Fallback

During the migration period, services can fall back to SQLite if PostgreSQL becomes unavailable.

**Automatic failover (if implemented in the service):**

Services using `homeiq-data` library check PostgreSQL on startup. If unavailable, they fall back to the local SQLite database.

**Manual failover:**

```bash
# 1. Verify PostgreSQL is actually down
docker exec homeiq-postgres pg_isready -U homeiq || echo "PostgreSQL is DOWN"

# 2. Set environment variables to force SQLite mode
# In the service's environment or .env file:
DATABASE_BACKEND=sqlite
SQLITE_DATABASE_PATH=/app/data/metadata.db

# 3. Restart affected services
docker compose restart data-api admin-api

# 4. Verify services are healthy in SQLite mode
curl -s http://localhost:8006/health | python -m json.tool
# Should show database_backend: "sqlite" or similar indicator
```

**Limitations of SQLite fallback:**
- No cross-schema queries
- No concurrent write support (single-writer lock)
- Data written during failover must be reconciled (see next section)
- Some advanced PostgreSQL features (JSONB operators, array types) are unavailable

### InfluxDB Down -- Degraded Mode

If InfluxDB is unavailable:

1. websocket-ingestion will buffer events in memory (configurable limit)
2. data-api will return cached/stale data or errors for time-series queries
3. health-dashboard will show InfluxDB as "disconnected"

```bash
# Check InfluxDB status
curl -s http://localhost:8086/health

# If InfluxDB container crashed, restart it
docker compose up -d influxdb

# Wait for recovery
sleep 10

# Verify websocket-ingestion reconnected
curl -s http://localhost:8001/health | python -m json.tool
```

---

## Data Reconciliation After Failover

### PostgreSQL Restored After SQLite Failover

If services wrote to SQLite during a PostgreSQL outage, data reconciliation is needed:

```bash
# 1. Identify the failover window
# Check service logs for when SQLite mode was activated and deactivated
docker logs homeiq-data-api 2>&1 | grep -i "sqlite\|fallback\|failover"

# 2. Export data written during failover from SQLite
docker exec homeiq-data-api sqlite3 /app/data/metadata.db \
    ".dump" > /tmp/failover_data.sql

# 3. Review the exported data
# Look for INSERT/UPDATE statements with timestamps during the failover window

# 4. Apply missing data to PostgreSQL
# This is manual and schema-specific -- use INSERT ON CONFLICT DO UPDATE
# to avoid duplicates

# 5. Verify data consistency
# Compare row counts between SQLite and PostgreSQL for the affected time range

# 6. Switch services back to PostgreSQL
# Remove DATABASE_BACKEND=sqlite from environment
docker compose restart data-api admin-api
```

### InfluxDB Restored After Outage

Data buffered during the InfluxDB outage may be lost depending on buffer configuration:

```bash
# 1. Check websocket-ingestion for dropped events
docker logs homeiq-websocket-ingestion 2>&1 | grep -i "buffer\|drop\|overflow"

# 2. If events were dropped, check the gap in InfluxDB
# Query for the last data point before the outage and the first after recovery
curl -s 'http://localhost:8086/api/v2/query' \
    -H 'Authorization: Token homeiq-token' \
    -H 'Content-Type: application/vnd.flux' \
    -d 'from(bucket:"homeiq") |> range(start:-1d) |> first() |> yield(name:"first")'

# 3. If gap is unacceptable, data must be backfilled from Home Assistant history
# This depends on Home Assistant's own data retention settings
```

---

## Communication Procedures During Outages

### Severity Levels

| Level | Criteria | Response |
|-------|----------|----------|
| **SEV-1** | Tier 1 services down, no data flowing | Immediate response, all hands |
| **SEV-2** | Tier 2 services down or degraded, data partially flowing | Response within 1 hour |
| **SEV-3** | Tier 3+ services down, core functionality unaffected | Response within 4 hours |
| **SEV-4** | Monitoring gap, non-critical feature unavailable | Next business day |

### Outage Response Checklist

1. **Detect**: Automated alerts or health check failure
2. **Assess**: Determine severity level and affected services
   ```bash
   ./scripts/check-service-health.sh --json
   ```
3. **Communicate**: Post status in the designated channel
4. **Mitigate**: Apply immediate fix or failover
5. **Restore**: Follow the appropriate restore procedure above
6. **Verify**: Run health checks and E2E tests
   ```bash
   ./scripts/check-service-health.sh
   npx playwright test tests/e2e/system-health.spec.ts
   npx playwright test tests/e2e/database-health.spec.ts
   ```
7. **Document**: Update `docs/TAPPS_RUNLOG.md` with:
   - Incident timeline
   - Root cause
   - Actions taken
   - Follow-up tasks

### Status Update Template

```
INCIDENT: [Brief description]
SEVERITY: SEV-[1/2/3/4]
STATUS: [Investigating / Mitigating / Resolved]
IMPACT: [What is affected]
STARTED: [Timestamp UTC]
UPDATED: [Timestamp UTC]
NEXT UPDATE: [Timestamp UTC]
ACTIONS:
  - [What has been done]
  - [What is being done]
  - [What will be done next]
```

---

## Disaster Recovery Drills

### Quarterly DR Drill Procedure

1. **Pre-drill**: Notify team, ensure recent backup exists
2. **Simulate failure**: Stop PostgreSQL container
3. **Verify detection**: Confirm alerts fire within 2 minutes
4. **Execute failover**: Follow failover procedure (SQLite fallback)
5. **Restore**: Follow PostgreSQL restore procedure
6. **Validate**: Run health checks and E2E tests
7. **Measure**: Record RTO and RPO achieved
8. **Document**: Update this runbook with lessons learned

### Success Criteria

- [ ] Failure detected by monitoring within 2 minutes
- [ ] Failover completed within 15 minutes
- [ ] Full restore completed within 1 hour (RTO target)
- [ ] Data loss is within 24 hours (RPO target)
- [ ] All Tier 1 services healthy after restoration
- [ ] E2E tests pass after restoration

---

## Related Documentation

- [PostgreSQL Runbook](postgresql-runbook.md)
- [Monitoring Setup](monitoring-setup.md)
- [Service Health Checks](service-health-checks.md)
- [Backup Scripts](../../scripts/backup-postgres.sh)
- [Restore Scripts](../../scripts/restore-postgres.sh)
- [Backup Test](../../scripts/test-backup-restore.sh)
