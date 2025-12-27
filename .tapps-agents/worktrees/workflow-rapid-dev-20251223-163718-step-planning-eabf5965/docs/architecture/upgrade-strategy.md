# Docker Container & Database Upgrade Strategy

**Last Updated:** November 25, 2025  
**Status:** Production Ready  
**Scope:** Local Docker deployment (single-home NUC)

---

## Overview

This document provides a comprehensive upgrade strategy for databases and key containers in the HomeIQ local Docker deployment. It covers:

- **InfluxDB** (time-series database)
- **SQLite** (metadata databases)
- **Application containers** (29 microservices)
- **Zero-downtime upgrades** where possible
- **Backup and rollback procedures**

---

## Key Containers & Databases

### Critical Databases

| Database | Type | Location | Purpose | Upgrade Risk |
|----------|------|----------|---------|--------------|
| **InfluxDB** | Time-series | `influxdb_data` volume | Events, metrics, sports | 🟡 MEDIUM |
| **metadata.db** | SQLite | `sqlite_data` volume | Devices, entities (data-api) | 🟢 LOW |
| **ai_automation.db** | SQLite | Container volume | Patterns, suggestions (ai-automation-service) | 🟡 MEDIUM |
| **webhooks.db** | SQLite | Container volume | Webhooks (sports-data) | 🟢 LOW |

### Critical Containers

| Container | Purpose | Upgrade Risk | Dependencies |
|-----------|---------|--------------|--------------|
| **influxdb** | Time-series database | 🟡 MEDIUM | None |
| **data-api** | Metadata API | 🟡 MEDIUM | InfluxDB, SQLite |
| **websocket-ingestion** | Event ingestion | 🟡 MEDIUM | InfluxDB, data-api |
| **ai-automation-service** | AI automation | 🔴 HIGH | InfluxDB, SQLite, multiple services |

---

## Pre-Upgrade Checklist

### 1. Backup All Data

**CRITICAL: Always backup before upgrades**

```bash
# Backup InfluxDB
docker exec homeiq-influxdb influx backup /backup/influxdb-$(date +%Y%m%d-%H%M%S)

# Backup SQLite databases
docker exec homeiq-data-api sqlite3 /app/data/metadata.db ".backup /backup/metadata-$(date +%Y%m%d-%H%M%S).db"
docker exec homeiq-ai-automation-service sqlite3 /app/data/ai_automation.db ".backup /backup/ai_automation-$(date +%Y%m%d-%H%M%S).db"

# Backup Docker volumes (if needed)
docker run --rm -v homeiq_influxdb_data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/influxdb-volume-$(date +%Y%m%d-%H%M%S).tar.gz /data
docker run --rm -v homeiq_sqlite_data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/sqlite-volume-$(date +%Y%m%d-%H%M%S).tar.gz /data
```

### 2. Verify Current Versions

```bash
# Check InfluxDB version
docker exec homeiq-influxdb influx version

# Check container versions
docker-compose ps

# Check database schemas
docker exec homeiq-data-api sqlite3 /app/data/metadata.db ".schema" > backups/schema-metadata-$(date +%Y%m%d).sql
docker exec homeiq-ai-automation-service sqlite3 /app/data/ai_automation.db ".schema" > backups/schema-ai-automation-$(date +%Y%m%d).sql
```

### 3. Review Upgrade Notes

- Check `CHANGELOG.md` for breaking changes
- Review migration scripts in `services/*/alembic/versions/`
- Check Docker image release notes

### 4. Test in Development First

**Always test upgrades in development environment before production**

```bash
# Use docker-compose.dev.yml for testing
docker-compose -f docker-compose.dev.yml up -d
# ... perform upgrade ...
# ... test functionality ...
```

---

## Database Upgrade Procedures

### InfluxDB Upgrade

**Current Version:** 2.7  
**Upgrade Path:** 2.7 → 2.8 → 3.0 (when available)

#### Step 1: Backup InfluxDB

```bash
# Create backup directory
mkdir -p backups/influxdb

# Backup InfluxDB data
docker exec homeiq-influxdb influx backup /backup/influxdb-$(date +%Y%m%d-%H%M%S)

# Export configuration
docker exec homeiq-influxdb influx config export > backups/influxdb-config-$(date +%Y%m%d).json
```

#### Step 2: Stop Dependent Services

```bash
# Stop services that depend on InfluxDB
docker-compose stop websocket-ingestion data-api ai-automation-service
docker-compose stop weather-api carbon-intensity-service electricity-pricing-service
docker-compose stop air-quality-service smart-meter-service calendar-service
```

#### Step 3: Upgrade InfluxDB Container

```bash
# Update docker-compose.yml with new version
# image: influxdb:2.8  # Update version tag

# Pull new image
docker-compose pull influxdb

# Stop InfluxDB
docker-compose stop influxdb

# Start with new version
docker-compose up -d influxdb

# Wait for health check
docker-compose ps influxdb  # Should show "healthy"
```

#### Step 4: Verify Upgrade

```bash
# Check version
docker exec homeiq-influxdb influx version

# Test connection
docker exec homeiq-influxdb influx ping

# Verify data integrity
docker exec homeiq-influxdb influx query 'from(bucket:"home_assistant_events") |> range(start: -1h) |> count()'
```

#### Step 5: Restart Dependent Services

```bash
# Start services in dependency order
docker-compose up -d influxdb
docker-compose up -d data-api
docker-compose up -d websocket-ingestion
docker-compose up -d ai-automation-service
docker-compose up -d weather-api carbon-intensity-service electricity-pricing-service
docker-compose up -d air-quality-service smart-meter-service calendar-service
```

#### Rollback Procedure

```bash
# Stop InfluxDB
docker-compose stop influxdb

# Restore backup
docker exec homeiq-influxdb influx restore /backup/influxdb-YYYYMMDD-HHMMSS

# Revert docker-compose.yml to previous version
# image: influxdb:2.7

# Start with old version
docker-compose up -d influxdb
```

---

### SQLite Database Upgrades

**Upgrade Method:** Alembic migrations (for ai-automation-service) or manual SQL (for data-api)

#### ai-automation-service Database

**Location:** `/app/data/ai_automation.db` in container  
**Migration Tool:** Alembic

```bash
# Step 1: Backup database
docker exec homeiq-ai-automation-service sqlite3 /app/data/ai_automation.db ".backup /backup/ai_automation-$(date +%Y%m%d-%H%M%S).db"

# Step 2: Stop service (if needed for migration)
docker-compose stop ai-automation-service

# Step 3: Run migration
docker-compose run --rm ai-automation-service alembic upgrade head

# Step 4: Verify migration
docker-compose run --rm ai-automation-service alembic current

# Step 5: Start service
docker-compose up -d ai-automation-service

# Step 6: Verify functionality
curl http://localhost:8024/health
```

#### data-api Database (metadata.db)

**Location:** `/app/data/metadata.db` in container  
**Migration Tool:** Alembic

```bash
# Step 1: Backup database
docker exec homeiq-data-api sqlite3 /app/data/metadata.db ".backup /backup/metadata-$(date +%Y%m%d-%H%M%S).db"

# Step 2: Stop service
docker-compose stop data-api

# Step 3: Run migration
docker-compose run --rm data-api alembic upgrade head

# Step 4: Verify migration
docker-compose run --rm data-api alembic current

# Step 5: Start service
docker-compose up -d data-api

# Step 6: Verify functionality
curl http://localhost:8006/health
curl http://localhost:8006/api/devices?limit=5
```

#### Rollback Procedure

```bash
# Stop service
docker-compose stop ai-automation-service  # or data-api

# Restore backup
docker exec homeiq-ai-automation-service sqlite3 /app/data/ai_automation.db < /backup/ai_automation-YYYYMMDD-HHMMSS.db

# Rollback migration (if using Alembic)
docker-compose run --rm ai-automation-service alembic downgrade -1

# Start service
docker-compose up -d ai-automation-service
```

---

## Container Upgrade Procedures

### Zero-Downtime Upgrade Strategy

**For stateless services:** Rolling updates  
**For stateful services:** Blue-green deployment or scheduled maintenance window

### Application Container Upgrade

#### Step 1: Backup & Preparation

```bash
# Backup databases (see Database Upgrade Procedures above)
# Verify current version
docker-compose ps

# Pull new images
docker-compose pull <service-name>
```

#### Step 2: Upgrade Strategy by Service Type

**Stateless Services (can upgrade without downtime):**

```bash
# Example: health-dashboard, admin-api
docker-compose up -d --no-deps --build <service-name>
```

**Stateful Services (require coordination):**

```bash
# Example: ai-automation-service, data-api
# 1. Stop service
docker-compose stop <service-name>

# 2. Run database migrations (if needed)
docker-compose run --rm <service-name> alembic upgrade head

# 3. Rebuild and start
docker-compose up -d --build <service-name>

# 4. Verify health
curl http://localhost:<port>/health
```

#### Step 3: Verify Upgrade

```bash
# Check container status
docker-compose ps

# Check logs for errors
docker-compose logs <service-name> | tail -50

# Test functionality
curl http://localhost:<port>/health
curl http://localhost:<port>/api/...  # Test key endpoints
```

#### Step 4: Monitor

```bash
# Monitor logs for 5-10 minutes
docker-compose logs -f <service-name>

# Check resource usage
docker stats <container-name>

# Verify no errors in health dashboard
curl http://localhost:3000
```

---

## Full System Upgrade Procedure

### Complete System Upgrade (All Services)

**Recommended:** Perform during maintenance window (2-4 hours)

#### Phase 1: Preparation (30 minutes)

```bash
# 1. Create comprehensive backup
./scripts/backup-all.sh  # Create this script

# 2. Document current state
docker-compose ps > backups/system-state-$(date +%Y%m%d).txt
docker-compose config > backups/docker-compose-$(date +%Y%m%d).yml

# 3. Review upgrade notes
cat CHANGELOG.md
```

#### Phase 2: Database Upgrades (30-60 minutes)

```bash
# 1. Upgrade InfluxDB (see InfluxDB Upgrade section)
# 2. Upgrade SQLite databases (see SQLite Upgrade section)
# 3. Verify all databases
```

#### Phase 3: Core Services (30-60 minutes)

```bash
# Upgrade in dependency order:
# 1. InfluxDB (already done)
# 2. data-api
docker-compose up -d --build data-api

# 3. websocket-ingestion
docker-compose up -d --build websocket-ingestion

# 4. ai-automation-service
docker-compose stop ai-automation-service
docker-compose run --rm ai-automation-service alembic upgrade head
docker-compose up -d --build ai-automation-service
```

#### Phase 4: Supporting Services (30-60 minutes)

```bash
# Upgrade external data services
docker-compose up -d --build weather-api
docker-compose up -d --build carbon-intensity-service
docker-compose up -d --build electricity-pricing-service
docker-compose up -d --build air-quality-service
docker-compose up -d --build calendar-service
docker-compose up -d --build smart-meter-service
```

#### Phase 5: Frontend & Admin (15 minutes)

```bash
# Upgrade dashboards
docker-compose up -d --build health-dashboard
docker-compose up -d --build ai-automation-ui
docker-compose up -d --build admin-api
```

#### Phase 6: Verification (30 minutes)

```bash
# 1. Check all services healthy
docker-compose ps

# 2. Test key endpoints
./scripts/test-services.sh  # Create this script

# 3. Verify data integrity
# - Check event ingestion
# - Check API responses
# - Check dashboard functionality

# 4. Monitor for 15-30 minutes
docker-compose logs -f
```

---

## Automated Upgrade Scripts

### Backup Script (`scripts/backup-all.sh`)

```bash
#!/bin/bash
# Backup all databases and configurations

BACKUP_DIR="backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup InfluxDB
docker exec homeiq-influxdb influx backup "$BACKUP_DIR/influxdb" || echo "InfluxDB backup failed"

# Backup SQLite databases
docker exec homeiq-data-api sqlite3 /app/data/metadata.db ".backup $BACKUP_DIR/metadata.db" || echo "metadata.db backup failed"
docker exec homeiq-ai-automation-service sqlite3 /app/data/ai_automation.db ".backup $BACKUP_DIR/ai_automation.db" || echo "ai_automation.db backup failed"

# Backup Docker volumes
docker run --rm -v homeiq_influxdb_data:/data -v "$(pwd)/$BACKUP_DIR:/backup" alpine tar czf /backup/influxdb-volume.tar.gz /data
docker run --rm -v homeiq_sqlite_data:/data -v "$(pwd)/$BACKUP_DIR:/backup" alpine tar czf /backup/sqlite-volume.tar.gz /data

# Backup configurations
docker-compose config > "$BACKUP_DIR/docker-compose.yml"
docker-compose ps > "$BACKUP_DIR/container-status.txt"

echo "Backup complete: $BACKUP_DIR"
```

### Upgrade Script (`scripts/upgrade-service.sh`)

```bash
#!/bin/bash
# Upgrade a single service with safety checks

SERVICE=$1
if [ -z "$SERVICE" ]; then
    echo "Usage: $0 <service-name>"
    exit 1
fi

echo "Upgrading $SERVICE..."

# Backup
./scripts/backup-all.sh

# Pull new image
docker-compose pull "$SERVICE"

# Check if service has database migrations
if docker-compose run --rm "$SERVICE" test -f alembic.ini 2>/dev/null; then
    echo "Running database migrations..."
    docker-compose stop "$SERVICE"
    docker-compose run --rm "$SERVICE" alembic upgrade head
fi

# Rebuild and start
docker-compose up -d --build "$SERVICE"

# Wait for health check
sleep 10

# Verify
if curl -f "http://localhost:$(docker-compose port "$SERVICE" | cut -d: -f2)/health" > /dev/null 2>&1; then
    echo "✅ $SERVICE upgraded successfully"
else
    echo "❌ $SERVICE health check failed - check logs"
    docker-compose logs "$SERVICE" | tail -50
    exit 1
fi
```

---

## Rollback Procedures

### Quick Rollback (Last 24 Hours)

```bash
# 1. Stop service
docker-compose stop <service-name>

# 2. Restore from backup
# (See backup restoration in Database Upgrade Procedures)

# 3. Revert docker-compose.yml
git checkout HEAD~1 docker-compose.yml  # Or manually edit

# 4. Rebuild and start
docker-compose up -d --build <service-name>
```

### Full System Rollback

```bash
# 1. Stop all services
docker-compose down

# 2. Restore volumes from backup
docker volume rm homeiq_influxdb_data homeiq_sqlite_data
docker run --rm -v homeiq_influxdb_data:/data -v "$(pwd)/backups/YYYYMMDD-HHMMSS:/backup" alpine tar xzf /backup/influxdb-volume.tar.gz -C /
docker run --rm -v homeiq_sqlite_data:/data -v "$(pwd)/backups/YYYYMMDD-HHMMSS:/backup" alpine tar xzf /backup/sqlite-volume.tar.gz -C /

# 3. Restore docker-compose.yml
cp backups/YYYYMMDD-HHMMSS/docker-compose.yml docker-compose.yml

# 4. Start services
docker-compose up -d
```

---

## Testing Procedures

### Pre-Upgrade Testing

```bash
# 1. Test in development environment
docker-compose -f docker-compose.dev.yml up -d
# ... perform upgrade ...
# ... test functionality ...

# 2. Run integration tests
pytest tests/integration/

# 3. Test key workflows
# - Event ingestion
# - API queries
# - Dashboard functionality
```

### Post-Upgrade Testing

```bash
# 1. Health checks
curl http://localhost:8006/health  # data-api
curl http://localhost:8001/health  # websocket-ingestion
curl http://localhost:8024/health  # ai-automation-service

# 2. Functional tests
curl http://localhost:8006/api/devices?limit=5
curl http://localhost:8006/api/events?limit=10

# 3. Verify data integrity
# - Check event counts
# - Check device counts
# - Verify recent events ingested
```

---

## Maintenance Windows

### Recommended Schedule

- **Weekly:** Application container updates (low risk)
- **Monthly:** Database maintenance and optimization
- **Quarterly:** Major version upgrades (InfluxDB, etc.)

### Maintenance Window Procedure

1. **Notify users** (if applicable) - 24 hours before
2. **Create backup** - 1 hour before
3. **Perform upgrade** - During window
4. **Verify functionality** - 30 minutes after
5. **Monitor** - 24 hours after

---

## Version Pinning Strategy

### Docker Images

**Pin to specific versions for stability:**

```yaml
services:
  influxdb:
    image: influxdb:2.7  # Pin to specific version
    # NOT: influxdb:latest
```

### Database Migrations

**Always test migrations before applying:**

```bash
# Test migration in development first
docker-compose -f docker-compose.dev.yml run --rm ai-automation-service alembic upgrade head

# Verify migration
docker-compose -f docker-compose.dev.yml run --rm ai-automation-service alembic current
```

---

## Emergency Procedures

### Database Corruption

```bash
# 1. Stop affected service
docker-compose stop <service-name>

# 2. Restore from backup
# (See backup restoration procedures)

# 3. Verify data integrity
docker exec <container> sqlite3 /app/data/<db>.db "PRAGMA integrity_check;"

# 4. Restart service
docker-compose up -d <service-name>
```

### Container Failure

```bash
# 1. Check logs
docker-compose logs <service-name>

# 2. Restart service
docker-compose restart <service-name>

# 3. If still failing, rollback
# (See rollback procedures)
```

---

## Best Practices

1. **Always backup before upgrades**
2. **Test in development first**
3. **Upgrade databases before applications**
4. **Upgrade in dependency order**
5. **Monitor after upgrades**
6. **Keep upgrade logs**
7. **Document any manual steps**
8. **Have rollback plan ready**

---

## References

- [InfluxDB Upgrade Guide](https://docs.influxdata.com/influxdb/v2.7/upgrade/)
- [Docker Compose Upgrade Guide](https://docs.docker.com/compose/production/)
- [Alembic Migration Guide](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [SQLite Backup & Restore](https://www.sqlite.org/backup.html)

---

**Last Updated:** November 25, 2025  
**Maintained By:** DevOps Team  
**Review Frequency:** Quarterly

