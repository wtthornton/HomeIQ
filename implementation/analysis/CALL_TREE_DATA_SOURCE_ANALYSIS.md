# Call Tree Data Source Analysis

**Created:** 2025-12-06  
**Purpose:** Analyze whether the system uses local/cached data vs direct Home Assistant API calls

## Critical Finding: Mixed Data Sources

The system is currently using a **MIXED approach** - some data comes from local/cached sources (data-api) while other data comes from direct HA API calls. This is inefficient and should be optimized.

## Current Data Flow Analysis

### ✅ Using Local/Cached Data (Efficient)

1. **Entities** - `data_api_client.fetch_entities()`
   - Source: `data-api` service (Port 8006)
   - Data: Stored in InfluxDB/SQLite (from websocket-ingestion)
   - Status: ✅ **OPTIMAL** - Using local cached data
   - Location: `devices_summary_service.py:100`

### ❌ Using Direct HA API Calls (Inefficient)

1. **Devices Registry** - `ha_client.get_device_registry()`
   - Source: Direct Home Assistant WebSocket/REST API
   - Data: Live from HA (192.168.1.86:8123)
   - Status: ❌ **INEFFICIENT** - Direct API call on every context build
   - Location: `devices_summary_service.py:76`
   - Impact: Adds ~100-500ms latency per request

2. **Areas Registry** - `ha_client.get_area_registry()`
   - Source: Direct Home Assistant WebSocket/REST API
   - Data: Live from HA (192.168.1.86:8123)
   - Status: ❌ **INEFFICIENT** - Direct API call on every context build
   - Location: 
     - `devices_summary_service.py:88`
     - `areas_service.py:66`
   - Impact: Adds ~50-200ms latency per request

3. **Services** - `ha_client.get_services()` (via services_summary_service)
   - Source: Direct Home Assistant REST API
   - Status: ❌ **INEFFICIENT** - Direct API call
   - Impact: Adds ~50-200ms latency per request

4. **Helpers & Scenes** - `ha_client.get_helpers()` / `ha_client.get_scenes()`
   - Source: Direct Home Assistant REST API
   - Status: ❌ **INEFFICIENT** - Direct API calls
   - Impact: Adds ~100-300ms latency per request

## Performance Impact

### Current Behavior (Every Context Build)

When `context_builder.build_complete_system_prompt()` is called:

1. **Cache Check** (if cache exists and < 5 minutes old) → ✅ Fast (~1ms)
2. **If Cache Miss or Refresh:**
   - Direct HA API call for devices → ❌ ~100-500ms
   - Direct HA API call for areas → ❌ ~50-200ms
   - Direct HA API call for services → ❌ ~50-200ms
   - Direct HA API call for helpers/scenes → ❌ ~100-300ms
   - **Total Direct HA API Latency: ~300-1200ms per context build**

### Optimized Behavior (Using Local Data)

If all data came from data-api (local/cached):

1. **Cache Check** (if cache exists and < 5 minutes old) → ✅ Fast (~1ms)
2. **If Cache Miss or Refresh:**
   - Local query for devices → ✅ ~5-20ms
   - Local query for areas → ✅ ~5-20ms
   - Local query for services → ✅ ~5-20ms
   - Local query for helpers/scenes → ✅ ~5-20ms
   - **Total Local Query Latency: ~20-80ms per context build**

**Potential Performance Improvement: 15-60x faster** (300-1200ms → 20-80ms)

## Call Tree Update

### Current Flow (Inefficient)

```
context_builder.build_complete_system_prompt()
│
├─ devices_summary_service.get_summary()
│  ├─ Check cache → If miss:
│  ├─ ❌ ha_client.get_device_registry() [DIRECT HA API CALL]
│  ├─ ❌ ha_client.get_area_registry() [DIRECT HA API CALL]
│  └─ ✅ data_api_client.fetch_entities() [LOCAL/CACHED]
│
├─ areas_service.get_areas_list()
│  ├─ Check cache → If miss:
│  └─ ❌ ha_client.get_area_registry() [DIRECT HA API CALL]
│
├─ services_summary_service.get_summary()
│  ├─ Check cache → If miss:
│  └─ ❌ ha_client.get_services() [DIRECT HA API CALL]
│
└─ helpers_scenes_service.get_summary()
   ├─ Check cache → If miss:
   └─ ❌ ha_client.get_helpers() / get_scenes() [DIRECT HA API CALLS]
```

### Optimized Flow (Recommended)

```
context_builder.build_complete_system_prompt()
│
├─ devices_summary_service.get_summary()
│  ├─ Check cache → If miss:
│  ├─ ✅ data_api_client.get_devices() [LOCAL/CACHED]
│  ├─ ✅ data_api_client.get_areas() [LOCAL/CACHED]
│  └─ ✅ data_api_client.fetch_entities() [LOCAL/CACHED]
│
├─ areas_service.get_areas_list()
│  ├─ Check cache → If miss:
│  └─ ✅ data_api_client.get_areas() [LOCAL/CACHED]
│
├─ services_summary_service.get_summary()
│  ├─ Check cache → If miss:
│  └─ ✅ data_api_client.get_services() [LOCAL/CACHED]
│
└─ helpers_scenes_service.get_summary()
   ├─ Check cache → If miss:
   └─ ✅ data_api_client.get_helpers() / get_scenes() [LOCAL/CACHED]
```

## Recommendations

### Immediate Actions

1. **Check data-api capabilities** - Verify if data-api already has endpoints for:
   - Devices registry
   - Areas registry
   - Services
   - Helpers & Scenes

2. **If data-api has these endpoints:**
   - Update `devices_summary_service.py` to use `data_api_client` instead of `ha_client`
   - Update `areas_service.py` to use `data_api_client` instead of `ha_client`
   - Update `services_summary_service.py` to use `data_api_client` instead of `ha_client`
   - Update `helpers_scenes_service.py` to use `data_api_client` instead of `ha_client`

3. **If data-api doesn't have these endpoints:**
   - Add endpoints to data-api to serve this data from local storage
   - Data should be synced from HA via websocket-ingestion or a background sync service

### Long-term Optimization

1. **Background Sync Service** - Create a service that periodically syncs:
   - Device registry → data-api
   - Area registry → data-api
   - Services → data-api
   - Helpers & Scenes → data-api

2. **WebSocket Event Handling** - Extend websocket-ingestion to capture:
   - Device registry changes
   - Area registry changes
   - Service changes
   - Helper/Scene changes

3. **Cache Strategy** - Improve caching:
   - Increase cache TTL for static data (devices, areas)
   - Use event-driven cache invalidation
   - Implement multi-level caching (memory + database)

## Files to Review

1. `services/ha-ai-agent-service/src/services/devices_summary_service.py`
   - Line 76: `ha_client.get_device_registry()` → Should use data-api
   - Line 88: `ha_client.get_area_registry()` → Should use data-api

2. `services/ha-ai-agent-service/src/services/areas_service.py`
   - Line 66: `ha_client.get_area_registry()` → Should use data-api

3. `services/ha-ai-agent-service/src/services/services_summary_service.py`
   - Check if using `ha_client.get_services()` → Should use data-api

4. `services/ha-ai-agent-service/src/services/helpers_scenes_service.py`
   - Check if using `ha_client.get_helpers()` / `get_scenes()` → Should use data-api

5. `services/data-api/` - Check available endpoints
   - Need: `/api/devices`, `/api/areas`, `/api/services`, `/api/helpers`, `/api/scenes`

## Performance Metrics to Track

After optimization, track:
- Context build time (should drop from ~300-1200ms to ~20-80ms)
- Cache hit rate (should increase)
- Direct HA API call count (should drop to near zero)
- Total request latency (should improve significantly)

