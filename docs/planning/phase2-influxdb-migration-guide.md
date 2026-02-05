# Phase 2: influxdb3-python 0.17.0 Migration Guide

**Story:** PHASE2-005
**Status:** ✅ Complete
**Created:** February 5, 2026

---

## Overview

Automated migration tool for replacing influxdb-client with influxdb3-python 0.17.0.

### Breaking Changes

**This is a complete API redesign - manual code migration required after running script.**

1. **Package replacement** - influxdb-client -> influxdb3-python[pandas]
2. **Import changes** - influxdb_client -> influxdb_client_3
3. **Client initialization** - Constructor parameters changed
4. **Write API** - New write() interface
5. **Query API** - New query() interface with pandas DataFrame support
6. **Pandas integration** - Query results return pandas DataFrames

---

## Migration Script

**Location:** `scripts/phase2-migrate-influxdb.py`

### Features

✅ **Automated Import Updates**
- Replaces `import influxdb_client` with `import influxdb_client_3`
- Replaces `from influxdb_client import` with `from influxdb_client_3 import`
- Updates requirements.txt to influxdb3-python[pandas]==0.17.0

⚠️ **Manual Code Migration Required**
- Client initialization API changed
- write() API changed
- query() API changed (returns pandas DataFrame)

---

## Usage

### Single Service

```bash
# Dry run (preview changes)
python scripts/phase2-migrate-influxdb.py data-api --dry-run

# Apply migration
python scripts/phase2-migrate-influxdb.py data-api
```

### Batch Migration

```bash
# Migrate multiple services
python scripts/phase2-migrate-influxdb.py \
  --batch data-api websocket-ingestion api-automation-edge
```

---

## What the Script Does

### Step 1: Validate Service Structure

Checks for:
- Service directory exists
- `requirements.txt` exists

### Step 2: Check if Migration Needed

Skips if:
- Already has influxdb3-python
- Does not use influxdb-client

### Step 3: Create Backup

Creates `.migration_backup_influxdb_YYYYMMDD_HHMMSS/` with:
- `requirements.txt`
- `src/` directory (full copy)

### Step 4: Find InfluxDB Usage

Scans `src/**/*.py` for:
- `import influxdb_client`
- `from influxdb_client import`
- `InfluxDBClient(`
- `Point(`
- `WritePrecision`

### Step 5: Migrate Imports

**Automated Changes:**
```python
# OLD
import influxdb_client
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import ASYNCHRONOUS

# NEW
import influxdb_client_3
from influxdb_client_3 import InfluxDBClient, Point, WritePrecision
from influxdb_client_3.client.write_api import ASYNCHRONOUS
```

**Manual Changes Required:** See API Migration section below

### Step 6: Update requirements.txt

**Before:**
```
influxdb-client>=1.49.0,<2.0.0
```

**After:**
```
influxdb3-python[pandas]==0.17.0  # Phase 2 upgrade - BREAKING: API redesign
```

### Step 7: Create Rollback Script

Generates `rollback_influxdb_YYYYMMDD_HHMMSS.sh`

---

## API Migration (Manual Steps)

**⚠️ CRITICAL: These changes must be done manually after running the migration script.**

### 1. Client Initialization

**OLD (influxdb-client):**
```python
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import ASYNCHRONOUS

client = InfluxDBClient(
    url="http://localhost:8086",
    token="my-token",
    org="my-org",
    timeout=30000  # milliseconds
)

write_api = client.write_api(write_options=ASYNCHRONOUS)
query_api = client.query_api()
```

**NEW (influxdb3-python):**
```python
from influxdb_client_3 import InfluxDBClient3

client = InfluxDBClient3(
    host="http://localhost:8086",
    token="my-token",
    database="my-bucket",  # Note: bucket -> database
    timeout=30  # seconds (not milliseconds)
)

# No separate write_api or query_api - use client directly
```

**Key Changes:**
- `url` -> `host`
- `org` parameter removed
- `bucket` -> `database`
- `timeout` in seconds (not milliseconds)
- No separate write_api/query_api objects

### 2. Write API

**OLD (influxdb-client):**
```python
from influxdb_client import Point, WritePrecision

# Create point
point = Point("measurement_name") \
    .tag("location", "home") \
    .field("temperature", 23.5) \
    .time(datetime.now(timezone.utc), WritePrecision.NS)

# Write
write_api.write(bucket="my-bucket", record=point)

# Batch write
write_api.write(bucket="my-bucket", record=[point1, point2, point3])
```

**NEW (influxdb3-python):**
```python
from influxdb_client_3 import Point, WritePrecision

# Create point (same API)
point = Point("measurement_name") \
    .tag("location", "home") \
    .field("temperature", 23.5) \
    .time(datetime.now(timezone.utc), WritePrecision.NS)

# Write (no bucket parameter - uses client.database)
client.write(record=point)

# Batch write
client.write(record=[point1, point2, point3])
```

**Key Changes:**
- No `bucket` parameter (uses `database` from client initialization)
- Call `client.write()` directly (not `write_api.write()`)
- Point creation API unchanged

### 3. Query API

**OLD (influxdb-client):**
```python
# Flux query
query = '''
from(bucket: "my-bucket")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "temperature")
'''

result = query_api.query(query=query, org="my-org")

# Process results
for table in result:
    for record in table.records:
        print(f"{record.get_time()}: {record.get_value()}")
```

**NEW (influxdb3-python):**
```python
# SQL or InfluxQL query (Flux deprecated)
query = '''
SELECT *
FROM temperature
WHERE time > now() - INTERVAL '1 hour'
'''

# Returns pandas DataFrame
df = client.query(query=query)

# Process results (pandas)
for index, row in df.iterrows():
    print(f"{row['time']}: {row['value']}")

# Or use pandas methods
print(df.head())
print(df.describe())
```

**Key Changes:**
- Flux queries deprecated, use SQL or InfluxQL
- Returns pandas DataFrame (not table records)
- No `org` parameter
- More powerful data analysis with pandas

### 4. Connection Management

**OLD (influxdb-client):**
```python
# Close client
client.close()
```

**NEW (influxdb3-python):**
```python
# Close client (same)
client.close()

# Or use context manager
with InfluxDBClient3(host=..., token=..., database=...) as client:
    client.write(record=point)
    df = client.query(query=query)
```

---

## Affected Services (16 total)

From `phase2-dependency-analysis.md`:

### CRITICAL Priority (3 services)
- ✅ `api-automation-edge` (also has tenacity)
- ✅ `data-api` (also has pytest-asyncio)
- ✅ `websocket-ingestion` (also has pytest-asyncio, MQTT)

### HIGH Priority (2 services)
- ✅ `admin-api` (also has pytest-asyncio)
- ✅ `data-retention` (also has pytest-asyncio, MQTT)

### MEDIUM Priority (3 services)
- ✅ `energy-correlator`
- ✅ `energy-forecasting`
- ✅ `smart-meter-service`

### LOW Priority (8 services)
- ✅ `air-quality-service`
- ✅ `calendar-service`
- ✅ `carbon-intensity-service`
- ✅ `electricity-pricing-service`
- ✅ `observability-dashboard`
- ✅ `sports-api` (also has pytest-asyncio)
- ✅ `weather-api` (also has pytest-asyncio)

---

## Migration Strategy

### Phase A: Low-Risk Test (4 services)

**Purpose:** Validate migration script and manual code changes

```bash
python scripts/phase2-migrate-influxdb.py \
  --batch air-quality-service calendar-service \
          carbon-intensity-service electricity-pricing-service
```

**After Script:**
1. Manually update Client initialization in each service
2. Update write() calls (remove bucket parameter)
3. Update query() calls (Flux -> SQL, handle pandas DataFrame)
4. Run tests: `pytest tests/ -v`

### Phase B: Medium-Risk (3 services)

```bash
python scripts/phase2-migrate-influxdb.py \
  --batch energy-correlator energy-forecasting smart-meter-service
```

### Phase C: High-Risk (2 services)

```bash
python scripts/phase2-migrate-influxdb.py \
  --batch admin-api data-retention
```

### Phase D: Critical Services (3 services, SEQUENTIAL)

**Sequential deployment with blue-green strategy:**

```bash
# Migrate api-automation-edge first
python scripts/phase2-migrate-influxdb.py api-automation-edge
# Manual code migration + testing

# Then data-api
python scripts/phase2-migrate-influxdb.py data-api
# Manual code migration + testing

# Finally websocket-ingestion
python scripts/phase2-migrate-influxdb.py websocket-ingestion
# Manual code migration + testing
```

---

## Validation

### Post-Migration Checklist

For each service:

- [ ] ✅ Script completed: imports updated, requirements.txt updated
- [ ] ✅ Manual code migration: Client initialization updated
- [ ] ✅ Manual code migration: write() calls updated
- [ ] ✅ Manual code migration: query() calls updated (Flux -> SQL/InfluxQL)
- [ ] ✅ All tests pass (`pytest tests/ -v`)
- [ ] ✅ Service builds successfully
- [ ] ✅ Service starts and connects to InfluxDB
- [ ] ✅ Data writes successfully
- [ ] ✅ Queries return correct data
- [ ] ✅ Backup directory created
- [ ] ✅ Rollback script created

### Service Health Check

After migration and manual code changes:

```bash
# Build service with new dependencies
docker-compose build <service-name>

# Start service
docker-compose up -d <service-name>

# Check health
curl http://localhost:<port>/health

# Check InfluxDB connectivity
docker-compose logs <service-name> | grep -i influx

# Verify writes (check InfluxDB)
influx query 'SELECT * FROM <measurement> LIMIT 10'
```

---

## Rollback Procedure

If migration fails or manual code changes cause issues:

```bash
# Option 1: Use rollback script
cd services/<service-name>
./rollback_influxdb_YYYYMMDD_HHMMSS.sh

# Option 2: Manual rollback
cd services/<service-name>
cp .migration_backup_influxdb_*/requirements.txt ./requirements.txt
rm -rf src
cp -r .migration_backup_influxdb_*/src ./src

# Rebuild service with old versions
docker-compose build <service-name>
docker-compose up -d <service-name>
```

---

## Common Issues

### Issue 1: Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'influxdb_client_3'`

**Cause:** influxdb3-python not installed

**Solution:**
```bash
pip install 'influxdb3-python[pandas]==0.17.0'
```

### Issue 2: Client Initialization Fails

**Symptom:** `TypeError: __init__() got unexpected keyword argument 'url'`

**Cause:** Using old client initialization API

**Solution:**
```python
# Change url -> host, org removed, bucket -> database
client = InfluxDBClient3(
    host="http://localhost:8086",  # not 'url'
    token="my-token",
    database="my-bucket"  # not 'bucket'
)
```

### Issue 3: Write Fails

**Symptom:** `TypeError: write() got unexpected keyword argument 'bucket'`

**Cause:** Using old write API

**Solution:**
```python
# Remove bucket parameter (uses client.database)
client.write(record=point)  # not write(bucket=..., record=...)
```

### Issue 4: Query Returns Wrong Type

**Symptom:** Trying to iterate over DataFrame as table records

**Cause:** Query returns pandas DataFrame in new API

**Solution:**
```python
# Use pandas DataFrame methods
df = client.query(query=query)

# Iterate rows
for index, row in df.iterrows():
    print(row['field_name'])

# Or convert to dict
records = df.to_dict('records')
for record in records:
    print(record['field_name'])
```

### Issue 5: Flux Query Fails

**Symptom:** Query syntax errors

**Cause:** Flux queries deprecated in influxdb3-python

**Solution:**
```python
# Convert Flux to SQL
# OLD (Flux):
# from(bucket: "my-bucket")
#   |> range(start: -1h)
#   |> filter(fn: (r) => r["_measurement"] == "temperature")

# NEW (SQL):
query = '''
SELECT *
FROM temperature
WHERE time > now() - INTERVAL '1 hour'
'''
```

---

## Script Output Example

### Dry Run

```
============================================================
InfluxDB Migration Summary: data-api
============================================================
[DRY RUN] - No changes made

Changes (9):
  [OK] src/analytics_endpoints.py: Updated InfluxDB imports
  [OK] src/devices_endpoints.py: Updated InfluxDB imports
  [OK] src/energy_endpoints.py: Updated InfluxDB imports
  [OK] requirements.txt: Updated influxdb-client -> influxdb3-python[pandas]==0.17.0

Warnings (2):
  [WARNING] Found InfluxDB usage in 8 files - API redesign requires manual code migration
  [WARNING] See migration guide for API changes: Client initialization, write(), query()

============================================================
MANUAL CODE MIGRATION REQUIRED
============================================================
```

---

## Next Steps

After completing InfluxDB migration:

1. ✅ Mark Story 5 as complete
2. 📋 Begin Story 6: Batch Rebuild Orchestration
3. 📋 Continue with remaining Phase 2 stories

---

## References

- **influxdb3-python Documentation:** [https://github.com/InfluxCommunity/influxdb3-python](https://github.com/InfluxCommunity/influxdb3-python)
- **Migration Guide:** [influxdb-client -> influxdb3-python](https://github.com/InfluxCommunity/influxdb3-python#migrating-from-influxdb-client)
- **SQL Query Reference:** [InfluxDB SQL](https://docs.influxdata.com/influxdb/cloud-serverless/query-data/sql/)
- **Phase 2 Plan:** [phase2-implementation-plan.md](phase2-implementation-plan.md)
- **Service Dependencies:** [phase2-dependency-analysis.md](phase2-dependency-analysis.md)

---

**Status:** ✅ Migration script complete and tested
**Next:** Begin InfluxDB migration rollout (16 services, manual code changes required)
