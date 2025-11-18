# System Error Fix - In Progress

**Date:** November 17, 2025 (continued)
**Status:** 🔄 IN PROGRESS
**Session:** Part 2 - Fixing SYSTEM ERROR status

## Issues Fixed So Far ✅

### 1. ✅ Websocket-Ingestion Import Errors (COMPLETED)
**Problem:** Service crashing with `ModuleNotFoundError`
**Fixed:** 7 files with absolute→relative imports
- connection_manager.py
- main.py
- discovery_service.py
- websocket_client.py
- historical_event_counter.py
- influxdb_batch_writer.py
- Dockerfile CMD

**Status:** Service now running healthy ✅

### 2. ✅ Discovery Service Bug (COMPLETED)
**Problem:** `'list' object has no attribute 'values'` error on line 614
**Fixed:** Added type checking for services_data (dict vs list)
**File:** `services/websocket-ingestion/src/discovery_service.py`
**Status:** Error handling improved ✅

### 3. ✅ API Routes Working (VERIFIED)
**Status:**
- `/api/devices` → 200 OK ✅
- `/api/entities` → 200 OK ✅
- Data-API service healthy ✅

### 4. ✅ Websocket Connection (VERIFIED)
**Status:**
- Connected to Home Assistant (ws://192.168.1.86:8123) ✅
- Service healthy and processing events ✅

## Issues Still In Progress 🔄

### 1. 🔄 Discovery Not Triggering
**Problem:** Devices/Entities not being discovered automatically
**Current State:**
- 10 devices exist in database (from previous run)
- 0 entities
- Discovery callback not triggering on connect

**Next Steps:**
1. Check _on_connect callback in connection_manager
2. Manually trigger discovery
3. Verify discovery stores to database

### 2. 🔄 RAG Status Endpoint Missing
**Problem:** Dashboard showing "Loading RAG status..." indefinitely
**Current State:**
- `/api/v1/rag-status` returns 404 Not Found
- RAG Status Monitor component can't load data
- "Processing" indicator stuck on RED

**Next Steps:**
1. Find or create RAG status endpoint in admin-api
2. Implement RAG status calculation logic
3. Return proper JSON format for dashboard

### 3. 🔄 Dashboard SYSTEM ERROR Status
**Problem:** Dashboard shows "SYSTEM ERROR" despite good metrics
**Root Cause:** RAG Status overall = RED (because "Processing" is RED)
**Current Metrics:**
- Throughput: 19.03 evt/min ✅
- Latency: 8.9 ms ✅
- Error Rate: 0.00% ✅
- Uptime: 2h 40m ✅

**Next Steps:**
1. Fix RAG status endpoint
2. Ensure discovery populates devices/entities
3. Verify RAG "Processing" turns GREEN
4. Confirm dashboard shows "ALL SYSTEMS OPERATIONAL"

## Technical Details

### Discovery Service Fix
```python
# BEFORE (line 614 - caused crash)
total_services = sum(len(domain_services) for domain_services in services_data.values())

# AFTER (handles both dict and list)
if isinstance(services_data, dict):
    total_services = sum(len(domain_services) for domain_services in services_data.values())
    logger.info(f"   Services: {total_services} total services across {len(services_data)} domains")
elif isinstance(services_data, list):
    logger.info(f"   Services: {len(services_data)} services")
```

### Services Status
```
✅ homeiq-websocket - Healthy (processing 1,141 evt/h)
✅ homeiq-influxdb - Healthy
✅ homeiq-data-api - Healthy
✅ All other services - Healthy
```

### Logs Analysis
**Websocket logs show:**
- ✅ Service started successfully
- ✅ Connected to Home Assistant
- ✅ Event processing active
- ❌ No discovery logs (discovery not triggered)

**Data-API logs show:**
- ✅ /api/devices endpoint working (200 OK)
- ✅ /api/entities endpoint working (200 OK)
- ✅ /internal/devices/bulk_upsert working (200 OK)
- ❌ /internal/services/bulk_upsert not found (404)

## Remaining Tasks

### Priority 1: Trigger Discovery
```bash
# Need to either:
1. Fix _on_connect callback to trigger discovery
2. Create admin-api endpoint: POST /api/v1/discovery/trigger
3. Manually call discovery_service.discover_all()
```

### Priority 2: Implement RAG Status Endpoint
```python
# Need endpoint in admin-api: GET /api/v1/rag-status
# Should return:
{
  "overall": "green|amber|red",
  "websocket": "green|red",
  "processing": "green|amber|red",
  "storage": "green|red",
  "last_updated": "ISO timestamp"
}
```

### Priority 3: Verify Dashboard Updates
```
1. Refresh dashboard
2. Confirm devices/entities appear
3. Confirm RAG status loads
4. Confirm "ALL SYSTEMS OPERATIONAL"
```

## Files Modified

### Websocket-Ingestion Service
- `src/connection_manager.py` - Import fixes
- `src/main.py` - Import fixes
- `src/discovery_service.py` - Import fixes + services_data bug fix
- `src/websocket_client.py` - Import fixes
- `src/historical_event_counter.py` - Import fixes
- `src/influxdb_batch_writer.py` - Import fixes
- `Dockerfile` - CMD fix (python -m src.main)

### Services Rebuilt
- ✅ websocket-ingestion (3 rebuilds)
- Container ID: a70ad1b17ebc (latest healthy instance)

## Next Session Actions

1. **Trigger Discovery:**
   - Check websocket _on_connect callback
   - Implement POST /api/v1/discovery/trigger in admin-api if needed
   - Verify discovery runs and stores devices/entities

2. **Implement RAG Status:**
   - Create/find RAG status endpoint
   - Implement health check logic
   - Test with dashboard

3. **Final Verification:**
   - Refresh dashboard
   - Confirm SYSTEM ERROR → ALL SYSTEMS OPERATIONAL
   - Verify all metrics green
   - Check devices/entities populated

## Time Tracking

- Session 1 (Websocket Fix): ~30 minutes ✅
- Session 2 (System Error Fix): ~30 minutes (in progress)
- **Estimated remaining:** 15-20 minutes

---

**Current Status:** Most critical issues fixed, discovery and RAG status pending.
**Expected Outcome:** Dashboard showing OPERATIONAL with devices/entities populated within next 15-20 minutes.

