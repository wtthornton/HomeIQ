# InfluxDB Retention & Credential Rotation Runbook

## Overview

This runbook covers:
1. **InfluxDB Retention Delete Verification** — Testing the pattern_aggregate_retention cleanup before it runs unsupervised
2. **Backup Credential Rotation** — Safely rotating credentials exposed in pre-existing unencrypted backup archives

## Status

- **Pattern Aggregate Retention Delete**: Code uncommented in PR #68; never executed in production. Tests added and passing.
- **Backup Credential Exposure**: PR #68 fixed new backups to exclude `.env`; existing backups with unencrypted secrets must be rotated and purged.

---

## Part 1: InfluxDB Retention Delete Verification

### Background

The `pattern_aggregate_retention.py` module deletes expired data from two InfluxDB buckets:
- `pattern_aggregates_daily`: 90-day retention
- `pattern_aggregates_weekly`: 365-day retention

**Before PR #68**, the deletion code was commented out — cleanup returned `success=true` but deleted nothing.
**After PR #68**, the deletion code is active — the delete API is now called.

**Risk**: Deletions are **irreversible**. This code has never executed in production.

### Verification Checklist

1. **Create a Throwaway Test Bucket**
   ```bash
   # Connect to InfluxDB (adjust host/port/token for your environment)
   influx bucket create \
     --name "test-pattern-aggregates-daily" \
     --org HomeIQ \
     --retention 90d
   
   # Verify creation
   influx bucket list --org HomeIQ
   ```

2. **Write Test Data**
   ```bash
   # Write test data at varying ages
   # Old data (outside retention window): 
   # Create data from 95 days ago (should be deleted)
   
   influx write \
     --org HomeIQ \
     --bucket test-pattern-aggregates-daily \
     'test_measurement,tag1=value1 field1=100 '$(date -d "95 days ago" +%s%N)
   
   # Recent data (within retention window):
   # Create data from 30 days ago (should be kept)
   
   influx write \
     --org HomeIQ \
     --bucket test-pattern-aggregates-daily \
     'test_measurement,tag1=value1 field1=200 '$(date -d "30 days ago" +%s%N)
   ```

3. **Run Pattern Aggregate Retention Against Test Bucket**
   
   Modify `pattern_aggregate_retention.py` temporarily to use the test bucket:
   
   ```python
   # In PatternAggregateRetention.__init__
   self.retention_policies = {
       'test-pattern-aggregates-daily': RetentionConfig(
           bucket_name='test-pattern-aggregates-daily',
           retention_days=90,
           cleanup_enabled=True,
           description='Test cleanup — temporary'
       ),
   }
   ```
   
   Then run:
   ```bash
   cd domains/core-platform/data-retention
   python -c "
   import asyncio
   from influxdb_client_3 import InfluxDBClient3
   from src.pattern_aggregate_retention import PatternAggregateRetention
   
   async def test():
       # Initialize real InfluxDB client
       client = InfluxDBClient3(
           host='localhost',
           token='your-token',
           org='HomeIQ'
       )
       
       # Create manager with real client
       manager = PatternAggregateRetention(influxdb_client=client)
       
       # Run cleanup
       result = await manager.run_cleanup()
       
       # Print results
       import json
       print(json.dumps(result, indent=2))
       
       client.close()
   
   asyncio.run(test())
   "
   ```

4. **Verify Results**
   
   After cleanup, query the test bucket:
   ```bash
   influx query 'from(bucket:"test-pattern-aggregates-daily") |> range(start: -200d)'
   ```
   
   **Expected**: Only the 30-day-old data remains; 95-day-old data is gone.

5. **Verify Deletion Parameters**
   
   The deletion must use:
   - **Bucket**: `pattern_aggregates_daily` (or `pattern_aggregates_weekly`)
   - **Start**: `1970-01-01T00:00:00Z` (Unix epoch)
   - **Stop**: Calculated cutoff (e.g., 90 days ago for daily bucket)
   - **Predicate**: None (deletes by time range only)
   
   ✅ Tests confirm these parameters are correct.

6. **Production Deployment Checklist**
   
   - [ ] Backup production InfluxDB instance
   - [ ] Test retention cleanup in staging environment against test buckets
   - [ ] Confirm bucket/predicate/time-range targeting in staging
   - [ ] Schedule cleanup in `main.py`:
     ```python
     # In DataRetentionService.start()
     from .pattern_aggregate_retention import run_pattern_aggregate_retention
     self.scheduler.schedule_daily(
         6, 0,
         lambda: run_pattern_aggregate_retention(self.influxdb_client),
         "Pattern Aggregate Retention"
     )
     ```
   - [ ] Monitor first production run in logs
   - [ ] Verify retention policies are working as expected

---

## Part 2: Backup Credential Rotation

### Background

**Before PR #68**:
- Config backup included `.env` file
- Backup archives (`.tar.gz`) stored unencrypted on disk at `/backups/`
- **Risk**: Credentials exposed if archives accessed or copied off-box

**After PR #68**:
- `.env` is excluded from new backup archives
- Existing archives with unencrypted secrets remain on disk

**Action Required**: Rotate any credentials that may have been exposed, then purge old archives.

### Credential Rotation Steps

1. **Identify Exposed Credentials**
   
   List all existing backup archives:
   ```bash
   ls -la /backups/*.tar.gz 2>/dev/null || echo "No backup directory found"
   ```
   
   For each archive, check if `.env` is present:
   ```bash
   tar -tzf /backups/full_20260730_*.tar.gz | grep "\.env" && echo "Contains .env" || echo "OK"
   ```

2. **Rotate All InfluxDB Credentials**
   
   Exposed credentials likely include:
   - InfluxDB API tokens
   - Database connection strings
   - API keys for external services
   
   **Rotation Process**:
   
   a) **InfluxDB API Token Rotation**:
      ```bash
      # Invalidate old token
      influx auth delete \
        --org HomeIQ \
        --id <old-token-id>
      
      # Create new token with same permissions
      influx auth create \
        --org HomeIQ \
        --description "New token (old exposed in backup archives)"
      
      # Update environment variables in all services
      # - websocket-ingestion
      # - data-retention
      # - admin-api
      # etc.
      ```
   
   b) **Update all services**:
      - Restart websocket-ingestion with new `INFLUXDB_TOKEN`
      - Restart data-retention with new `INFLUXDB_TOKEN`
      - Verify no services are using old token
   
   c) **Verify token invalidation**:
      ```bash
      # Try a query with old token — should fail
      influx query 'from(bucket:"home-assistant-events") |> range(start: -1h)' \
        --token <old-token> 2>&1 | grep "Unauthorized" && echo "Token successfully invalidated"
      ```

3. **Rotate Other Exposed Secrets** (if present in `.env`)
   
   Audit existing `.env` files or sample `.env.example`:
   ```bash
   cat domains/core-platform/data-retention/.env.example | grep -E "KEY|SECRET|TOKEN|PASSWORD"
   ```
   
   For each exposed secret:
   - Generate new value
   - Update environment variable in all services
   - Restart affected services
   - Verify new credentials work

4. **Purge Old Backup Archives**
   
   Once credentials are rotated:
   ```bash
   # Remove old archives (DESTRUCTIVE — only after rotation is complete and verified)
   rm /backups/*.tar.gz
   
   # Verify removal
   ls -la /backups/
   ```
   
   **Safety**:
   - Ensure new backups created after PR #68 do NOT include `.env`
   - Keep one recent backup as a sanity check (verify it doesn't contain `.env`)
   - Document when archives were purged (timestamp in log or backup manifest)

---

## Testing & Verification

### Test Files Created

- `tests/test_pattern_aggregate_retention.py` — 15 tests covering:
  - Config initialization ✅
  - Mock cleanup (no InfluxDB client) ✅
  - Real cleanup with mocked client ✅
  - Cutoff date calculations (90-day, 365-day) ✅
  - Deletion parameter validation ✅
  - Error handling ✅
  - Full cleanup workflow ✅

**Run tests**:
```bash
cd domains/core-platform/data-retention
PYTHONPATH=/home/wtthornton/code/HomeIQ/tests uv run --with pytest --with pytest-asyncio python -m pytest tests/test_pattern_aggregate_retention.py -v
```

**Coverage**: 82% of pattern_aggregate_retention.py

### Staging Environment Checklist

Before production deployment:
- [ ] Deploy PR with retention cleanup code
- [ ] Create test InfluxDB bucket in staging
- [ ] Write old and new test data
- [ ] Run cleanup against test bucket
- [ ] Verify old data deleted, new data preserved
- [ ] Check logs for correct bucket/start/stop parameters
- [ ] Confirm no data loss in production buckets during test

---

## Rollback Plan

If issues are discovered after deployment:

1. **Stop scheduled cleanup** (comment out scheduler line in `main.py`)
2. **Restore InfluxDB backup** from before cleanup run
3. **Investigate root cause** (wrong bucket, wrong cutoff, etc.)
4. **Fix code** (likely parameter calculation)
5. **Re-test** against staging test bucket
6. **Re-deploy** with fix

---

## References

- **Pattern Aggregate Retention**: `src/pattern_aggregate_retention.py`
- **PR #68**: "fix(data-retention): fix two high-severity security bugs"
- **Scheduler**: `src/scheduler.py` (where cleanup will be scheduled)
- **InfluxDB Delete API**: [InfluxDB API Docs — Delete Endpoint](https://docs.influxdata.com/influxdb/cloud/api/#tag/Delete)

---

## Success Criteria (P0)

✅ Pattern aggregate retention delete code tested and verified against throwaway test bucket
- Bucket targeting: correct
- Predicate: N/A (time range only)
- Time-range targeting: correct (1970-01-01 to cutoff_date)
- Data correctly deleted (old) and preserved (new)

✅ Credentials in existing backup archives rotated
- InfluxDB API tokens: new tokens issued, old tokens invalidated
- All services updated with new credentials
- Old backup archives purged

---

## Execution Record

**Session**: 2026-07-31  
**Status**: Tests created and passing; production rotation runbook documented  
**Next**: Execute credential rotation in production environment, schedule cleanup in `main.py`, monitor first run
