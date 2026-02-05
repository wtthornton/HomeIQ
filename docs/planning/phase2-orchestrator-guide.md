# Phase 2: Batch Orchestration Guide

**Story:** PHASE2-006
**Status:** ✅ Complete
**Created:** February 5, 2026

---

## Overview

Unified orchestration system that coordinates all Phase 2 migrations across 35 services and 5 breaking changes.

### Capabilities

✅ **Multi-Migration Coordination**
- Coordinates pytest-asyncio, tenacity, MQTT, and InfluxDB migrations
- Handles services with multiple breaking changes (up to 3)
- Sequential execution per service

✅ **Phased Rollout**
- Phase A: Low-risk test group (10 services)
- Phase B: Medium-risk services (14 services)
- Phase C: High-risk services (4 services)
- Phase D: Critical services (3 services, sequential)

✅ **Risk Management**
- Parallel execution for low/medium risk
- Sequential with manual validation for critical
- Automatic rollback on >20% failure rate
- Progress tracking and reporting

---

## Usage

### Run All Phases

```bash
# Dry run (preview all changes)
python scripts/phase2-batch-orchestrator.py --dry-run

# Execute all phases
python scripts/phase2-batch-orchestrator.py --phase all
```

### Run Specific Phase

```bash
# Run Phase A only (low-risk test)
python scripts/phase2-batch-orchestrator.py --phase a

# Run Phase B only (medium-risk)
python scripts/phase2-batch-orchestrator.py --phase b

# Run Phase C only (high-risk)
python scripts/phase2-batch-orchestrator.py --phase c

# Run Phase D only (critical, sequential)
python scripts/phase2-batch-orchestrator.py --phase d
```

---

## Phase Breakdown

### Phase A: Low-Risk Test Group (10 services)

**Purpose:** Validate migration scripts work correctly

**Services:**
- pytest-asyncio: automation-miner, blueprint-index, ha-setup-service, ha-simulator
- tenacity: rag-service, ai-automation-service-new
- influxdb: air-quality-service, calendar-service, carbon-intensity-service, electricity-pricing-service

**Execution:** Parallel

**Expected Duration:** 15-30 minutes

### Phase B: Medium-Risk Services (14 services)

**Purpose:** Migrate medium-priority services with multiple dependencies

**Services:**
- Multiple migrations: ai-pattern-service (pytest+tenacity), device-intelligence-service (pytest+tenacity), openvino-service (pytest+tenacity), proactive-agent-service (pytest+tenacity), ha-ai-agent-service (pytest+tenacity), sports-api (pytest+influxdb), weather-api (pytest+influxdb)
- Single migrations: ai-query-service, ai-training-service, blueprint-suggestion-service, energy-correlator, energy-forecasting, smart-meter-service, observability-dashboard

**Execution:** Parallel

**Expected Duration:** 30-45 minutes

### Phase C: High-Risk Services (4 services)

**Purpose:** Migrate high-priority services

**Services:**
- ai-core-service (pytest + tenacity)
- ml-service (pytest + tenacity)
- admin-api (pytest + influxdb)
- data-retention (pytest + mqtt + influxdb) - 3 breaking changes!

**Execution:** Parallel

**Expected Duration:** 20-30 minutes

### Phase D: Critical Services (3 services, SEQUENTIAL)

**Purpose:** Zero-downtime migration of critical path services

**Services:**
1. api-automation-edge (tenacity + influxdb)
2. data-api (pytest + influxdb)
3. websocket-ingestion (pytest + mqtt + influxdb) - 3 breaking changes!

**Execution:** Sequential with manual validation between services

**Expected Duration:** 45-60 minutes (including validation time)

---

## Service Migration Details

### Services by Breaking Change Count

**3 Breaking Changes (2 services):**
- websocket-ingestion (pytest + mqtt + influxdb) - Phase D
- data-retention (pytest + mqtt + influxdb) - Phase C

**2 Breaking Changes (11 services):**
- ai-pattern-service, device-intelligence-service, openvino-service, proactive-agent-service, ha-ai-agent-service (pytest + tenacity)
- ai-core-service, ml-service (pytest + tenacity)
- admin-api, sports-api, weather-api (pytest + influxdb)
- api-automation-edge, data-api (various combinations)

**1 Breaking Change (22 services):**
- Various services with single migration

---

## Orchestration Flow

### For Each Service

```
1. Validate service exists
2. Run migrations in sequence:
   - pytest-asyncio (if needed)
   - tenacity (if needed)
   - MQTT (if needed)
   - InfluxDB (if needed)
3. Collect results
4. Continue to next service
```

### For Each Migration

```
1. Call migration script with service path
2. Wait for completion (5 min timeout)
3. Check exit code
4. Log results
5. Return success/failure
```

### Phase-Level Logic

**Parallel Phases (A, B, C):**
```
- Process all services in phase
- Track success/failure
- If >20% fail: stop and rollback
- Otherwise: continue to next phase
```

**Sequential Phase (D):**
```
- Process services one at a time
- After each service:
  - Check success
  - Prompt for manual validation
  - Wait for user confirmation
  - Continue or abort
```

---

## Results and Reporting

### Real-Time Output

```
================================================================================
Phase 2: Batch Rebuild Orchestration
================================================================================
Phases to run: A, B, C, D
Total services: 35

================================================================================
PHASE A
================================================================================
Phase A: 10 services
Migrating: automation-miner (LOW, 1 migrations)
  Running: pytest-asyncio migration
  [OK] pytest-asyncio migration completed
[OK] automation-miner migrated successfully

...

--------------------------------------------------------------------------------
Phase Summary: 10 success, 0 failed
--------------------------------------------------------------------------------
Phase A completed successfully
```

### Final Summary

```
================================================================================
Phase 2 Batch Orchestration Summary
================================================================================

Total Services: 35
Successful: 34
Failed: 1
Duration: 142.5s

By Priority:
  CRITICAL: 3/3 successful
  HIGH: 6/6 successful
  MEDIUM: 15/15 successful
  LOW: 10/11 successful

By Migration Type:
  pytest-asyncio: 19/20 successful
  tenacity: 10/10 successful
  mqtt: 2/2 successful
  influxdb: 15/16 successful

Failed Services:
  some-service: influxdb

Results exported to: phase2_results_20260205_133000.json
================================================================================
```

### JSON Results Export

Results are automatically exported to `phase2_results_YYYYMMDD_HHMMSS.json`:

```json
{
  "automation-miner": {
    "name": "automation-miner",
    "priority": "LOW",
    "migrations": {
      "pytest-asyncio": true
    },
    "overall_success": true
  },
  "websocket-ingestion": {
    "name": "websocket-ingestion",
    "priority": "CRITICAL",
    "migrations": {
      "pytest-asyncio": true,
      "mqtt": true,
      "influxdb": true
    },
    "overall_success": true
  }
}
```

---

## Error Handling

### Migration Script Failure

**Behavior:**
- Log error details
- Mark service as failed
- Continue with next service (parallel phases)
- Stop immediately (sequential Phase D)

### >20% Failure Rate

**Behavior:**
- Stop phase execution
- Log summary
- Exit with error code
- Rollback instructions provided

### Timeout

**Behavior:**
- Each migration has 5-minute timeout
- Timeout treated as failure
- Service marked as failed
- Continue orchestration

---

## Manual Steps Required

### Before Running

1. ✅ Ensure all migration scripts are tested
2. ✅ Backup critical data
3. ✅ Review service dependencies
4. ✅ Schedule during off-peak hours (for production)

### During Phase D (Critical Services)

1. Run migration for service
2. **Manual validation required:**
   - Check service health: `curl http://localhost:<port>/health`
   - Check logs: `docker-compose logs <service>`
   - Verify data writes to InfluxDB
   - Test key endpoints
3. Press Enter to continue or Ctrl+C to abort

### After All Phases

1. Review results JSON file
2. Verify all services are healthy
3. Run integration tests
4. Monitor production metrics

---

## Rollback

### Automatic Rollback (Phase Failure)

If a phase fails with >20% failure rate:

```bash
# Rollback scripts are created per service
cd services/<failed-service>
./rollback_<migration-type>_YYYYMMDD_HHMMSS.sh
```

### Manual Rollback (Individual Service)

```bash
# Use service-specific rollback script
cd services/<service-name>

# Check for rollback scripts
ls -la rollback_*.sh

# Execute rollback
./rollback_pytest_asyncio_*.sh
./rollback_tenacity_*.sh
./rollback_mqtt_*.sh
./rollback_influxdb_*.sh

# Rebuild service
docker-compose build <service-name>
docker-compose up -d <service-name>
```

---

## Best Practices

1. **Always dry-run first**
   ```bash
   python scripts/phase2-batch-orchestrator.py --dry-run --phase all
   ```

2. **Run phases incrementally**
   ```bash
   # Test Phase A first
   python scripts/phase2-batch-orchestrator.py --phase a
   # Validate results before continuing
   python scripts/phase2-batch-orchestrator.py --phase b
   ```

3. **Monitor during execution**
   - Watch logs in real-time
   - Check service health after each phase
   - Review results JSON after completion

4. **For production deployments**
   - Schedule during off-peak hours
   - Have rollback plan ready
   - Monitor critical metrics
   - Keep team on standby for Phase D

---

## Next Steps

After orchestration completes:

1. ✅ Review results JSON
2. ✅ Run Story 7: Testing & Validation Suite
3. ✅ Deploy to production (if all tests pass)
4. ✅ Monitor services for 24-48 hours

---

## References

- **Phase 2 Plan:** [phase2-implementation-plan.md](phase2-implementation-plan.md)
- **Dependency Analysis:** [phase2-dependency-analysis.md](phase2-dependency-analysis.md)
- **Migration Scripts:**
  - [pytest-asyncio guide](phase2-pytest-asyncio-migration-guide.md)
  - [tenacity guide](phase2-tenacity-migration-guide.md)
  - [MQTT guide](phase2-mqtt-migration-guide.md)
  - [InfluxDB guide](phase2-influxdb-migration-guide.md)

---

**Status:** ✅ Orchestrator complete and ready for execution
**Next:** Story 7: Testing & Validation Suite
