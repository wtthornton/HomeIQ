# Phase 2: Testing & Validation Guide

**Story:** PHASE2-007
**Status:** ✅ Complete
**Created:** February 5, 2026

---

## Overview

Comprehensive testing and validation procedures for Phase 2 library upgrades across 35 services.

### Validation Levels

1. **Pre-Migration Validation** - Verify readiness before migration
2. **Migration Validation** - Verify migration scripts work correctly
3. **Post-Migration Validation** - Verify services work after migration
4. **Integration Validation** - Verify system-wide functionality
5. **Rollback Validation** - Verify rollback procedures work

---

## Pre-Migration Validation

### Checklist

Run these checks **before** starting Phase 2 migrations:

- [ ] ✅ All Phase 1 services are healthy
- [ ] ✅ All migration scripts tested with dry-runs
- [ ] ✅ Backup of critical data created
- [ ] ✅ InfluxDB backups created
- [ ] ✅ Git repository is clean (all changes committed)
- [ ] ✅ Team notified of planned migration window
- [ ] ✅ Monitoring systems operational
- [ ] ✅ Rollback procedures documented and ready

### Pre-Migration Health Check

```bash
# Check all services are running
docker-compose ps

# Check service health endpoints
./scripts/check-all-health.sh

# Verify InfluxDB connectivity
curl http://localhost:8086/health

# Check Git status
git status

# Verify Docker BuildKit enabled
docker buildx version
```

---

## Migration Validation

### Phase A Validation (Low-Risk Test)

**Purpose:** Validate migration scripts work correctly before proceeding

**Test Services:** automation-miner, blueprint-index, ha-setup-service, ha-simulator

#### Step 1: Dry-Run Validation

```bash
# Test orchestrator dry-run
python scripts/phase2-batch-orchestrator.py --phase a --dry-run

# Expected output:
# - No errors
# - All services detected
# - All migrations identified correctly
# - No actual changes made
```

#### Step 2: Execute Phase A

```bash
# Run Phase A migrations
python scripts/phase2-batch-orchestrator.py --phase a
```

#### Step 3: Validate Phase A Results

```bash
# Check results JSON
cat phase2_results_*.json | jq '.["automation-miner"]'

# Expected:
# {
#   "name": "automation-miner",
#   "priority": "LOW",
#   "migrations": {
#     "pytest-asyncio": true
#   },
#   "overall_success": true
# }

# Verify services build
docker-compose build automation-miner blueprint-index ha-setup-service ha-simulator

# Verify services start
docker-compose up -d automation-miner blueprint-index ha-setup-service ha-simulator

# Check health
curl http://localhost:8001/health  # automation-miner
curl http://localhost:8002/health  # blueprint-index
```

#### Step 4: Run Service Tests

```bash
# Run tests for each migrated service
cd services/automation-miner && pytest tests/ -v
cd services/blueprint-index && pytest tests/ -v
cd services/ha-setup-service && pytest tests/ -v
cd services/ha-simulator && pytest tests/ -v
```

**Success Criteria for Phase A:**
- [ ] ✅ All 10 services migrated successfully
- [ ] ✅ All services build without errors
- [ ] ✅ All services start successfully
- [ ] ✅ All health endpoints return 200 OK
- [ ] ✅ All service tests pass (100%)
- [ ] ✅ No errors in service logs

**If Phase A fails:** Stop and investigate before proceeding to Phase B.

---

### Phase B-D Validation

Apply same validation process for each phase:

1. **Dry-run first**
2. **Execute phase**
3. **Validate results JSON**
4. **Verify builds**
5. **Verify service health**
6. **Run service tests**
7. **Check logs for errors**

---

## Post-Migration Validation

### Service-Level Validation

For each migrated service:

#### 1. Build Validation

```bash
# Build service
docker-compose build <service-name>

# Expected:
# - No build errors
# - All dependencies installed
# - New library versions detected
```

#### 2. Startup Validation

```bash
# Start service
docker-compose up -d <service-name>

# Wait for startup
sleep 10

# Check running
docker-compose ps | grep <service-name>

# Expected: Status = Up
```

#### 3. Health Endpoint Validation

```bash
# Check health
curl http://localhost:<port>/health

# Expected:
# {
#   "status": "healthy",
#   "service": "<service-name>",
#   "version": "...",
#   "dependencies": {
#     "influxdb": "connected",  # if applicable
#     ...
#   }
# }
```

#### 4. Log Validation

```bash
# Check logs for errors
docker-compose logs --tail=100 <service-name> | grep -i error

# Expected: No ERROR level logs (or only expected errors)
```

#### 5. Functionality Validation

**For pytest-asyncio migrations:**
```bash
# Run async tests
cd services/<service-name>
pytest tests/ -v -k "async"

# Expected: All async tests pass
```

**For tenacity migrations:**
```bash
# Test retry logic (if testable)
# Verify retry decorators work correctly
```

**For MQTT migrations:**
```bash
# Check MQTT connectivity (if service uses MQTT)
# Verify MQTT client initialization
```

**For InfluxDB migrations:**
```bash
# Test InfluxDB writes
curl -X POST http://localhost:<port>/api/test-write

# Verify data in InfluxDB
influx query 'SELECT * FROM test_measurement LIMIT 10'

# Test InfluxDB queries
curl http://localhost:<port>/api/test-query

# Expected: Query returns data successfully
```

---

## Integration Validation

### System-Wide Tests

After all phases complete, run integration tests:

#### 1. Service Communication

```bash
# Test service-to-service communication
./scripts/test-service-communication.sh

# Expected: All services can communicate
```

#### 2. Data Pipeline

```bash
# Test data flow from websocket-ingestion -> InfluxDB -> data-api
# 1. Send test event to websocket-ingestion
curl -X POST http://localhost:8080/api/test-event

# 2. Wait for processing
sleep 5

# 3. Query via data-api
curl http://localhost:8090/api/events?limit=1

# Expected: Test event appears in query results
```

#### 3. End-to-End Workflows

```bash
# Test critical workflows:
# - Event ingestion -> processing -> storage -> query
# - API automation trigger -> execution -> result
# - Data retention -> cleanup -> archive

./scripts/test-e2e-workflows.sh
```

#### 4. Performance Validation

```bash
# Compare performance before/after migration
# - Query latency
# - Write throughput
# - CPU/memory usage

./scripts/compare-performance.sh
```

---

## Rollback Validation

### Test Rollback Procedures

**Important:** Test rollback on a non-critical service first.

#### 1. Select Test Service

```bash
# Use a low-risk service for testing
TEST_SERVICE="air-quality-service"
```

#### 2. Record Current State

```bash
# Check current version
docker-compose exec $TEST_SERVICE python -c "import influxdb_client_3; print(influxdb_client_3.__version__)"

# Save current health status
curl http://localhost:<port>/health > health_before_rollback.json
```

#### 3. Execute Rollback

```bash
cd services/$TEST_SERVICE

# List rollback scripts
ls -la rollback_*.sh

# Execute rollback (most recent)
./rollback_influxdb_*.sh

# Expected output:
# [OK] Restored requirements.txt
# [OK] Restored src directory
# [OK] Rollback complete
```

#### 4. Verify Rollback

```bash
# Rebuild with old versions
docker-compose build $TEST_SERVICE

# Restart service
docker-compose up -d $TEST_SERVICE

# Verify old version
docker-compose exec $TEST_SERVICE python -c "import influxdb_client; print(influxdb_client.__version__)"

# Expected: Old version (e.g., 1.49.0)

# Check health
curl http://localhost:<port>/health

# Compare with before rollback
diff health_before_rollback.json <(curl -s http://localhost:<port>/health)

# Expected: Service healthy, same functionality
```

#### 5. Re-Migrate After Test

```bash
# Re-run migration to restore Phase 2 state
python scripts/phase2-migrate-influxdb.py $TEST_SERVICE
```

**Rollback Test Success Criteria:**
- [ ] ✅ Rollback script executes without errors
- [ ] ✅ Old library versions restored
- [ ] ✅ Service builds successfully
- [ ] ✅ Service starts successfully
- [ ] ✅ Health endpoint returns healthy
- [ ] ✅ Service functionality unchanged
- [ ] ✅ Re-migration works after rollback

---

## Failure Scenarios & Recovery

### Scenario 1: Migration Script Fails

**Symptoms:**
- Script exits with error code
- Service marked as failed in results JSON
- Error logged

**Recovery:**
1. Check error message in results JSON or logs
2. Review migration script output
3. Fix underlying issue (e.g., missing dependency, syntax error)
4. Re-run migration for that service
5. Verify success

**Example:**
```bash
# Check error
cat phase2_results_*.json | jq '.["failed-service"]'

# Re-run specific migration
python scripts/phase2-migrate-influxdb.py failed-service

# Verify
docker-compose build failed-service
docker-compose up -d failed-service
curl http://localhost:<port>/health
```

### Scenario 2: Service Fails to Build

**Symptoms:**
- Docker build exits with error
- Dependency installation fails
- Import errors

**Recovery:**
1. Check build logs
2. Verify requirements.txt syntax
3. Check for conflicting dependencies
4. Rollback if needed
5. Fix and retry

**Example:**
```bash
# Check build logs
docker-compose build failed-service 2>&1 | tee build_error.log

# Common issues:
# - Syntax error in requirements.txt
# - Version conflict
# - Missing dependency

# Rollback
cd services/failed-service
./rollback_*.sh

# Fix requirements.txt
vim requirements.txt

# Retry build
docker-compose build failed-service
```

### Scenario 3: Service Fails Health Check

**Symptoms:**
- Service starts but health endpoint returns 500
- Service crashes on startup
- Dependency connection errors

**Recovery:**
1. Check service logs
2. Verify all dependencies are migrated correctly
3. Check for API changes requiring manual code updates
4. Fix code and rebuild

**Example:**
```bash
# Check logs
docker-compose logs --tail=100 failed-service

# Common issues for InfluxDB migration:
# - Old client initialization API used
# - Missing database parameter
# - Flux query instead of SQL

# Fix code (manual)
vim services/failed-service/src/influxdb_client.py

# Rebuild and restart
docker-compose build failed-service
docker-compose up -d failed-service
```

### Scenario 4: Tests Fail After Migration

**Symptoms:**
- pytest exits with failures
- Test coverage drops
- Integration tests fail

**Recovery:**
1. Identify failing tests
2. Check if tests need updates for new APIs
3. Fix test code
4. Re-run tests

**Example:**
```bash
# Run tests with verbose output
cd services/failed-service
pytest tests/ -v --tb=short

# Common issues:
# - Test fixtures need @pytest.mark.asyncio
# - Mock objects need updating for new API
# - Async context managers changed

# Fix tests
vim tests/test_something.py

# Re-run
pytest tests/ -v
```

---

## Success Metrics

### Target Metrics

**Migration Success Rate:**
- ✅ Target: 95%+ services migrate successfully
- ⚠️ Warning: <90% success rate
- ❌ Failure: <80% success rate

**Test Pass Rate:**
- ✅ Target: 100% tests pass after migration
- ⚠️ Warning: <95% pass rate
- ❌ Failure: <90% pass rate

**Zero Production Incidents:**
- ✅ Target: 0 critical incidents
- ⚠️ Warning: 1 non-critical incident
- ❌ Failure: Any critical incident

**Service Health:**
- ✅ Target: All services healthy after migration
- ⚠️ Warning: 1-2 services degraded
- ❌ Failure: Any critical service unhealthy

### Monitoring

**During Migration (Real-Time):**
- Service health endpoints
- Docker container status
- Migration script output
- Error logs

**Post-Migration (24-48 hours):**
- Service uptime
- Error rates
- Response times
- Resource usage (CPU, memory)
- InfluxDB write/query latency
- Test execution times

---

## Final Validation Checklist

After all phases complete:

### Infrastructure
- [ ] ✅ All 35 services migrated successfully
- [ ] ✅ All services building without errors
- [ ] ✅ All services running (docker-compose ps)
- [ ] ✅ All health endpoints returning 200 OK
- [ ] ✅ All service tests passing (100%)

### Breaking Changes
- [ ] ✅ pytest-asyncio: All async tests have @pytest.mark.asyncio
- [ ] ✅ pytest-asyncio: No asyncio_mode = auto in pytest.ini
- [ ] ✅ tenacity: All @retry decorators have reraise=True
- [ ] ✅ MQTT: aiomqtt and paho-mqtt installed correctly
- [ ] ✅ InfluxDB: Client initialization updated (manual check)
- [ ] ✅ InfluxDB: write() calls updated (manual check)
- [ ] ✅ InfluxDB: query() calls updated to SQL (manual check)

### Data Integrity
- [ ] ✅ InfluxDB data intact (no data loss)
- [ ] ✅ SQLite databases intact
- [ ] ✅ Configuration files unchanged
- [ ] ✅ Historical data accessible

### Integration
- [ ] ✅ Service-to-service communication works
- [ ] ✅ Event ingestion pipeline works
- [ ] ✅ API automation works
- [ ] ✅ Data queries return correct results
- [ ] ✅ WebSocket connections stable

### Performance
- [ ] ✅ Query latency within acceptable range
- [ ] ✅ Write throughput maintained
- [ ] ✅ CPU usage normal
- [ ] ✅ Memory usage normal
- [ ] ✅ No resource leaks detected

### Rollback Readiness
- [ ] ✅ Rollback scripts tested on test service
- [ ] ✅ Rollback procedures documented
- [ ] ✅ Backups verified and accessible
- [ ] ✅ Team trained on rollback process

---

## Documentation Updates

After successful migration:

### 1. Update Service READMEs

For each migrated service:

```markdown
## Phase 2 Library Updates (February 2026)

Updated libraries:
- pytest-asyncio: 0.23.0 -> 1.3.0 (BREAKING: @pytest.mark.asyncio required)
- tenacity: 8.x -> 9.1.2 (BREAKING: reraise default changed)
- aiomqtt: 2.4.0 (migrated from asyncio-mqtt)
- influxdb3-python: 0.17.0 (migrated from influxdb-client, API redesign)

Breaking changes documented in: docs/planning/phase2-*.md
```

### 2. Update Main README

Update project README with Phase 2 status:

```markdown
## Recent Updates

### Phase 2: Standard Library Updates (February 2026) ✅

Successfully upgraded 35 services across 5 breaking changes:
- pytest-asyncio 1.3.0
- tenacity 9.1.2
- asyncio-mqtt -> aiomqtt 2.4.0
- influxdb3-python 0.17.0
- python-dotenv 1.2.1

Migration success rate: 95%+ (target achieved)

See: docs/planning/phase2-implementation-plan.md
```

### 3. Update CHANGELOG

```markdown
## [2026.02] - Phase 2: Standard Library Updates

### Changed
- Upgraded pytest-asyncio to 1.3.0 across 20 services
- Upgraded tenacity to 9.1.2 across 10 services
- Migrated asyncio-mqtt to aiomqtt 2.4.0 (3 services)
- Migrated influxdb-client to influxdb3-python 0.17.0 (16 services)
- Upgraded python-dotenv to 1.2.1 (non-breaking)

### Breaking Changes
- pytest-asyncio: @pytest.mark.asyncio now required for async tests
- tenacity: reraise parameter default changed from True to False
- MQTT: Complete library replacement (asyncio-mqtt -> aiomqtt)
- InfluxDB: Complete API redesign (client, write, query interfaces)

### Migration
- Automated migration scripts created for all breaking changes
- Phased rollout (A->B->C->D) from low-risk to critical services
- 95%+ success rate achieved
- Zero production incidents

See: docs/planning/phase2-*.md for detailed migration guides
```

---

## Completion Criteria

Phase 2 is considered **complete** when:

1. ✅ All 35 services successfully migrated
2. ✅ All services building and running
3. ✅ All service tests passing (100%)
4. ✅ All integration tests passing
5. ✅ No critical errors in logs
6. ✅ Performance metrics within acceptable range
7. ✅ Rollback procedures tested and verified
8. ✅ Documentation updated
9. ✅ Team trained on new library versions
10. ✅ Monitoring shows stable system (24-48 hours)

---

## Next Steps

After Phase 2 completion:

1. ✅ Monitor services for 24-48 hours
2. ✅ Conduct post-mortem review
3. ✅ Document lessons learned
4. ✅ Plan Phase 3 (if applicable)
5. ✅ Celebrate success! 🎉

---

## References

- **Phase 2 Plan:** [phase2-implementation-plan.md](phase2-implementation-plan.md)
- **Dependency Analysis:** [phase2-dependency-analysis.md](phase2-dependency-analysis.md)
- **Orchestrator Guide:** [phase2-orchestrator-guide.md](phase2-orchestrator-guide.md)
- **Migration Guides:**
  - [pytest-asyncio](phase2-pytest-asyncio-migration-guide.md)
  - [tenacity](phase2-tenacity-migration-guide.md)
  - [MQTT](phase2-mqtt-migration-guide.md)
  - [InfluxDB](phase2-influxdb-migration-guide.md)

---

**Status:** ✅ Testing & Validation procedures complete
**Ready:** Phase 2 ready for production execution
