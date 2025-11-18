# Device Deployment Verification Plan

**Date:** November 17, 2025  
**Status:** Critical Issues Found - Action Required

## Executive Summary

After hours of work on device names, we've identified **critical deployment issues** that prevent devices from being correctly discovered, stored, and used in the system.

## Critical Issues Found

### 1. ❌ Discovery Service Cannot Connect to Data-API
**Problem:** The discovery service is trying to connect to `data-api:8006` but the connection is failing.

**Evidence:**
```
❌ Error posting devices to data-api: Cannot connect to host data-api:8006
❌ Error posting entities to data-api: Cannot connect to host data-api:8006
```

**Root Cause:** 
- Discovery service uses default: `http://homeiq-data-api:8006`
- But docker-compose service name is `data-api`
- Network connectivity exists (ping works), but HTTP connection fails

**Fix Required:**
- Set `DATA_API_URL` environment variable in websocket-ingestion service
- Or update discovery_service.py to use correct default hostname

### 2. ❌ No Entities in Database
**Problem:** The SQLite database has 0 entities, meaning discovery has never successfully stored entities.

**Evidence:**
- Database exists and is readable
- Entities table exists
- But COUNT(*) FROM entities = 0
- Discovery returns: `{"devices_discovered": 0, "entities_discovered": 0}`

**Impact:** Without entities in the database, device names cannot be enriched/enhanced.

### 3. ❌ Missing Event Enrichment Code
**Problem:** No code found that enriches events with device names from SQLite database.

**Evidence:**
- Events are written directly to InfluxDB via `influxdb_batch_writer.py`
- No code queries data-api for entity friendly names
- No normalization/enrichment step before writing events

**Impact:** Even if entities were in the database, events wouldn't be enriched with device names.

### 4. ⚠️ Docker Compose Command Mismatch (FIXED)
**Status:** Fixed
- Was: `command: ["python", "src/websocket_fallback_enhanced.py"]` (archived file)
- Now: `command: ["python", "-m", "src.main"]` (correct entry point)

## Verification Test Results

### ✅ Passing Tests
1. Services are healthy (data-api, websocket-ingestion)
2. Database exists and is readable
3. Discovery service endpoint is accessible

### ❌ Failing Tests
1. **No entities in database** - Discovery never successfully stored entities
2. **Data API endpoints return 404** - Need to verify correct endpoint paths
3. **Event enrichment missing** - No code to enrich events with device names

## Action Plan

### Phase 1: Fix Discovery Service Connection (IMMEDIATE)

1. **Set DATA_API_URL environment variable:**
   ```yaml
   # In docker-compose.dev.yml websocket-ingestion service
   environment:
     - DATA_API_URL=http://data-api:8006  # Add this line
   ```

2. **Or update discovery_service.py default:**
   ```python
   # Line 479 in discovery_service.py
   data_api_url = os.getenv('DATA_API_URL', 'http://data-api:8006')  # Change default
   ```

3. **Restart websocket-ingestion:**
   ```bash
   docker-compose -f docker-compose.dev.yml restart websocket-ingestion
   ```

4. **Trigger discovery manually:**
   ```bash
   curl -X POST http://localhost:8001/api/v1/discovery/trigger
   ```

5. **Verify entities are stored:**
   ```bash
   python scripts/check_device_names.py
   ```

### Phase 2: Verify Discovery Works (CRITICAL)

1. **Check Home Assistant connection:**
   - Verify HA simulator is running and accessible
   - Check websocket-ingestion logs for connection status
   - Verify HA_TOKEN is set correctly

2. **Trigger discovery and check logs:**
   ```bash
   docker logs homeiq-websocket -f
   # Trigger discovery in another terminal
   curl -X POST http://localhost:8001/api/v1/discovery/trigger
   ```

3. **Verify entities are discovered:**
   - Check logs for "✅ Discovered X entities"
   - Check logs for "✅ Stored X entities to SQLite"
   - Verify no connection errors

4. **Verify entities in database:**
   ```bash
   python scripts/check_device_names.py
   python scripts/e2e_device_verification.py
   ```

### Phase 3: Implement Event Enrichment (REQUIRED)

**Current State:**
- Events flow: HA → websocket-ingestion → InfluxDB (direct)
- No enrichment step queries SQLite for device names

**Required Implementation:**

1. **Add enrichment step before writing to InfluxDB:**
   - Query data-api for entity friendly_name by entity_id
   - Add friendly_name to event data
   - Store in InfluxDB with enriched data

2. **Location:** `services/websocket-ingestion/src/influxdb_batch_writer.py`
   - Add enrichment method that queries data-api
   - Call enrichment before creating InfluxDB points

3. **Alternative:** Add enrichment in `event_processor.py` or `main.py`
   - Enrich events after processing but before batching
   - Cache entity lookups to avoid repeated queries

### Phase 4: End-to-End Verification

1. **Run full E2E test:**
   ```bash
   python scripts/e2e_device_verification.py
   ```

2. **Verify device names in InfluxDB:**
   - Query InfluxDB for recent events
   - Check if friendly_name field is populated
   - Verify device names match expected values

3. **Check AI automation service:**
   - Verify AI service can query entities correctly
   - Test device name resolution in automation requests

## Testing Checklist

- [ ] Discovery service connects to data-api successfully
- [ ] Entities are discovered from Home Assistant
- [ ] Entities are stored in SQLite database
- [ ] Device name fields (friendly_name, name_by_user) are populated
- [ ] Events are enriched with device names before writing to InfluxDB
- [ ] InfluxDB events contain friendly_name field
- [ ] AI automation service can resolve device names correctly
- [ ] E2E test suite passes all tests

## Files Modified

1. `docker-compose.dev.yml` - Fixed command (DONE)
2. `services/websocket-ingestion/src/discovery_service.py` - Fix DATA_API_URL default (TODO)
3. `services/websocket-ingestion/src/influxdb_batch_writer.py` - Add enrichment (TODO)
4. `scripts/e2e_device_verification.py` - Created E2E test (DONE)

## Next Steps

1. **IMMEDIATE:** Fix DATA_API_URL connection issue
2. **CRITICAL:** Verify discovery stores entities successfully
3. **REQUIRED:** Implement event enrichment with device names
4. **VERIFY:** Run E2E tests to confirm everything works

## Notes

- The database exists but is empty - discovery has never successfully stored entities
- Network connectivity works (ping succeeds) but HTTP connections fail
- This suggests a hostname/port mismatch or service not listening on expected interface
- Need to verify data-api is listening on correct interface and port

