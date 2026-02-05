# Phase 2: Manual Work Required

**Created:** February 5, 2026
**Status:** ⏳ Pending

---

## Overview

Phase 2 automated migrations completed successfully for 30/31 services (96.8%). However, InfluxDB API redesign requires manual code changes in 13 services (observability-dashboard has no code usage).

---

## 1. InfluxDB API Manual Changes (13 Services)

### Services Confirmed Using InfluxDB in Code

Based on code analysis, the following services have InfluxDB client usage and need manual API updates:

#### CRITICAL Priority (3 services)
1. **api-automation-edge** - `src/observability/metrics.py`
2. **data-api** - `src/analytics_endpoints.py`
3. **websocket-ingestion** - `src/historical_event_counter.py`, `src/influxdb_batch_writer.py`, `src/influxdb_schema.py`

#### HIGH Priority (2 services)
4. **admin-api** - `src/devices_endpoints.py`, `src/influxdb_client.py`
5. **data-retention** - `src/backup_restore.py`, `src/materialized_views.py`

#### MEDIUM Priority (3 services)
6. **energy-correlator** - `src/correlator.py`, `src/influxdb_wrapper.py`
7. **energy-forecasting** - `src/data/energy_loader.py` ⚠️ **USES OLD API**
8. **smart-meter-service** - `src/main.py`

#### LOW Priority (5 services)
9. **air-quality-service** - `src/main.py`
10. **calendar-service** - `src/main.py`
11. **carbon-intensity-service** - `src/main.py`
12. **electricity-pricing-service** - `src/main.py`
13. **sports-api** - `src/main.py`
14. **weather-api** - `src/main.py`

#### No Code Changes Needed (1 service)
- **observability-dashboard** - No InfluxDB usage in code (only in requirements.txt)

### Required Changes by Service

#### energy-forecasting ⚠️ CRITICAL - Uses Old API
**File:** `src/data/energy_loader.py`

**Current Code:**
```python
from influxdb_client_3 import InfluxDBClient
client = InfluxDBClient(url=url, token=token, org=org)
query_api = client.query_api()
```

**Required Changes:**
```python
from influxdb_client_3 import InfluxDBClient3

# Change constructor
client = InfluxDBClient3(host=url, token=token, database=org)  # Note: org -> database

# Remove query_api - use client directly
# query_api = client.query_api()  # DELETE THIS

# Update query calls
# OLD: result = query_api.query(query=flux_query, org=org)
# NEW: df = client.query(query=sql_query)  # Returns pandas DataFrame
```

#### data-retention - Uses Old write_api
**File:** `src/backup_restore.py`

**Current Code:**
```python
await self.influxdb_client.write_api().write(...)
```

**Required Changes:**
```python
# Remove write_api() call
await self.influxdb_client.write(...)  # Direct call to client
```

#### All Other Services
Most services already have correct imports (`influxdb_client_3`, `InfluxDBClient3`). Verify:

1. **Client initialization** uses new API:
```python
client = InfluxDBClient3(host=..., token=..., database=...)
```

2. **Write calls** use client directly:
```python
client.write(record=point)  # No bucket parameter
```

3. **Query calls** return pandas DataFrames:
```python
df = client.query(query=sql_query)  # Returns pandas DataFrame
```

### Verification Checklist

For each service:
- [ ] Search for `InfluxDBClient(` (old API) → Replace with `InfluxDBClient3(`
- [ ] Search for `url=` parameter → Replace with `host=`
- [ ] Search for `org=` parameter → Remove or rename to `database=`
- [ ] Search for `bucket=` parameter → Remove (database set in client init)
- [ ] Search for `.write_api()` → Remove, use `client.write()` directly
- [ ] Search for `.query_api()` → Remove, use `client.query()` directly
- [ ] Search for Flux queries → Convert to SQL/InfluxQL
- [ ] Update result handling to use pandas DataFrame

---

## 2. Fix blueprint-suggestion-service (1 Service)

**Status:** ❌ Failed migration
**Error:** Service structure validation failed

### Investigation Steps

1. **Check service exists:**
```bash
ls -la services/blueprint-suggestion-service/
```

2. **Check requirements.txt exists:**
```bash
cat services/blueprint-suggestion-service/requirements.txt
```

3. **Check tests/ directory:**
```bash
ls -la services/blueprint-suggestion-service/tests/
```

4. **Re-run migration with verbose logging:**
```bash
python scripts/library-upgrade-pytest-asyncio-1.3.0.py blueprint-suggestion-service
```

### Likely Issues
- Service directory structure missing
- requirements.txt missing
- tests/ directory missing
- Permission issues

### Resolution
Fix identified issue and re-run:
```bash
python scripts/library-upgrade-pytest-asyncio-1.3.0.py blueprint-suggestion-service --skip-tests
```

---

## 3. Test Validation (30 Services)

All 30 successfully migrated services need test validation.

### Test Execution Plan

#### Phase A Services (10 services)
```bash
cd services/automation-miner && pytest tests/ -v
cd services/blueprint-index && pytest tests/ -v
cd services/ha-setup-service && pytest tests/ -v
cd services/ha-simulator && pytest tests/ -v
cd services/air-quality-service && pytest tests/ -v
cd services/calendar-service && pytest tests/ -v
cd services/carbon-intensity-service && pytest tests/ -v
cd services/electricity-pricing-service && pytest tests/ -v
cd services/rag-service && pytest tests/ -v
cd services/ai-automation-service-new && pytest tests/ -v
```

#### Phase B Services (13 services)
```bash
cd services/ai-pattern-service && pytest tests/ -v
cd services/device-intelligence-service && pytest tests/ -v
cd services/openvino-service && pytest tests/ -v
cd services/proactive-agent-service && pytest tests/ -v
cd services/ha-ai-agent-service && pytest tests/ -v
cd services/sports-api && pytest tests/ -v
cd services/weather-api && pytest tests/ -v
cd services/ai-query-service && pytest tests/ -v
cd services/ai-training-service && pytest tests/ -v
cd services/energy-correlator && pytest tests/ -v
cd services/energy-forecasting && pytest tests/ -v
cd services/smart-meter-service && pytest tests/ -v
cd services/observability-dashboard && pytest tests/ -v
```

#### Phase C Services (4 services)
```bash
cd services/ai-core-service && pytest tests/ -v
cd services/ml-service && pytest tests/ -v
cd services/admin-api && pytest tests/ -v
cd services/data-retention && pytest tests/ -v
```

#### Phase D Services (3 services)
```bash
cd services/api-automation-edge && pytest tests/ -v
cd services/data-api && pytest tests/ -v
cd services/websocket-ingestion && pytest tests/ -v
```

### Known Test Issues

Some services may have pre-existing test failures:
- **alembic import errors** - `ImportError: cannot import name 'command' from 'alembic'`
- Fix alembic version/dependency issues before running tests

---

## 4. Docker Build Validation (30 Services)

Build all migrated services to verify new dependencies install correctly.

### Build Commands

```bash
# Phase A (10 services)
docker-compose build automation-miner blueprint-index ha-setup-service ha-simulator \
  air-quality-service calendar-service carbon-intensity-service electricity-pricing-service \
  rag-service ai-automation-service-new

# Phase B (13 services)
docker-compose build ai-pattern-service device-intelligence-service openvino-service \
  proactive-agent-service ha-ai-agent-service sports-api weather-api \
  ai-query-service ai-training-service energy-correlator energy-forecasting \
  smart-meter-service observability-dashboard

# Phase C (4 services)
docker-compose build ai-core-service ml-service admin-api data-retention

# Phase D (3 services)
docker-compose build api-automation-edge data-api websocket-ingestion
```

### Verification
- [ ] All builds complete without errors
- [ ] New library versions installed (verify in build logs)
- [ ] No dependency conflicts

---

## 5. Service Health Validation

Start services and verify health endpoints.

### Health Check Commands

```bash
# Start all services
docker-compose up -d

# Check health endpoints
curl http://localhost:8001/health  # automation-miner
curl http://localhost:8002/health  # blueprint-index
# ... (add all service health endpoints)

# Check logs for errors
docker-compose logs --tail=100 | grep -i error
```

### Validation Criteria
- [ ] All services start successfully
- [ ] Health endpoints return 200 OK
- [ ] No critical errors in logs
- [ ] Services can communicate (service-to-service)

---

## 6. Integration Testing

Test critical workflows end-to-end.

### Test Workflows

1. **Event Ingestion Pipeline**
```bash
# Send test event to websocket-ingestion
curl -X POST http://localhost:8080/api/test-event

# Verify event stored in InfluxDB
influx query 'SELECT * FROM events LIMIT 10'

# Query via data-api
curl http://localhost:8090/api/events?limit=1
```

2. **API Automation Workflow**
```bash
# Trigger automation via api-automation-edge
curl -X POST http://localhost:8085/api/automations/test

# Verify execution logs
docker-compose logs api-automation-edge --tail=50
```

3. **Data Retention Workflow**
```bash
# Trigger retention policy
curl -X POST http://localhost:8095/api/retention/execute

# Verify data cleanup
influx query 'SELECT COUNT(*) FROM old_data'
```

---

## Execution Priority

### Phase 1: Critical Path (Before Any Deployment)
1. ✅ Fix **energy-forecasting** InfluxDB API (uses old API)
2. ✅ Fix **data-retention** write_api usage
3. ✅ Fix **blueprint-suggestion-service** (failed migration)
4. ⏳ Build **Phase D critical services** (api-automation-edge, data-api, websocket-ingestion)
5. ⏳ Test **Phase D critical services**

### Phase 2: High Priority Services
6. ⏳ Fix InfluxDB API in remaining HIGH priority services (admin-api)
7. ⏳ Build and test HIGH priority services

### Phase 3: Medium/Low Priority Services
8. ⏳ Fix InfluxDB API in MEDIUM priority services (energy-correlator, smart-meter-service)
9. ⏳ Fix InfluxDB API in LOW priority services (6 services)
10. ⏳ Build and test all remaining services

### Phase 4: Final Validation
11. ⏳ Integration testing (all workflows)
12. ⏳ Performance testing
13. ⏳ 24-hour monitoring (pre-production)

---

## Estimated Effort

| Task | Services | Estimated Time |
|------|----------|----------------|
| InfluxDB API fixes | 13 | 4-6 hours |
| Fix blueprint-suggestion-service | 1 | 30 minutes |
| Test validation | 30 | 2-3 hours |
| Docker builds | 30 | 1-2 hours |
| Integration testing | N/A | 2-3 hours |
| **Total** | | **10-15 hours** |

---

## References

- **InfluxDB Migration Guide:** [phase2-influxdb-migration-guide.md](phase2-influxdb-migration-guide.md)
- **Execution Summary:** [phase2-execution-summary.md](phase2-execution-summary.md)
- **Testing Guide:** [phase2-testing-validation-guide.md](phase2-testing-validation-guide.md)

---

**Status:** ⏳ Pending Manual Work
**Next:** Begin Phase 1 - Critical Path fixes
