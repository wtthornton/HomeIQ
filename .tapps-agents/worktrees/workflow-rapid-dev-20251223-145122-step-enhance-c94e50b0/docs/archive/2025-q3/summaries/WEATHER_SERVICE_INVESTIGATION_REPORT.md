# Weather Service Investigation Report

**Date:** October 10, 2025  
**Status:** Investigation Complete - Action Items Identified

## Executive Summary

Investigation revealed that the system has **two separate weather service implementations**:
1. **Integrated Weather Enrichment** (in `websocket-ingestion` service) - **WORKING ✓**
2. **Standalone Weather API Service** (`weather-api` container) - **BROKEN ✗**

The dashboard shows healthy weather metrics because it's using the **integrated enrichment service**, not the standalone weather-api container.

---

## Investigation Findings

### 1. Current System Architecture

#### Weather Integration Approach #1: Embedded Enrichment (ACTIVE)
- **Location:** `services/websocket-ingestion/src/weather_enrichment.py`
- **Status:** ✓ **Working and Healthy**
- **How it works:**
  - Weather enrichment is **embedded directly** into the `websocket-ingestion` service
  - Uses `OpenWeatherMapClient` to fetch weather data
  - Implements `WeatherCache` for efficient caching
  - Enriches events **inline** before sending to enrichment pipeline

**Evidence of Success:**
```powershell
# Health check shows it's working:
is_enabled             : True
total_events_processed : 335
successful_enrichments : 335
failed_enrichments     : 0
cache_hits             : 330
cache_misses           : 5
success_rate           : 100.0
cache_hit_rate         : 98.51
```

**Configuration (in `websocket-ingestion` container):**
```bash
WEATHER_API_KEY=01342fef09a0a14c6a9bf6447d5934fd
WEATHER_API_URL=https://api.openweathermap.org/data/2.5
WEATHER_DEFAULT_LOCATION=London,UK
WEATHER_ENRICHMENT_ENABLED=true
WEATHER_CACHE_MINUTES=15
WEATHER_RATE_LIMIT_PER_MINUTE=50
WEATHER_RATE_LIMIT_PER_DAY=900
WEATHER_REQUEST_TIMEOUT=10
```

#### Weather Integration Approach #2: Standalone Service (BROKEN)
- **Location:** `services/weather-api/` (separate Docker container)
- **Container Name:** `homeiq-weather`
- **Status:** ✗ **Crash Loop - Module Import Error**
- **Error:** `ModuleNotFoundError: No module named 'src'`

**Docker Compose Configuration:**
```yaml
weather-api:
  build:
    context: .
    dockerfile: services/weather-api/Dockerfile
  container_name: homeiq-weather
  restart: unless-stopped
  environment:
    - WEATHER_API_KEY=${WEATHER_API_KEY:-}
    - ENABLE_WEATHER_API=${ENABLE_WEATHER_API:-false}  # ← Disabled by default
  # Note: No exposed ports in docker-compose.yml
```

**Root Cause:**
1. **Dockerfile CMD Issue:** `CMD ["python", "-m", "src.main"]` expects Python module structure
2. **Module Structure Problem:** The `src/` directory is not set up as a proper Python package
3. **No Port Exposure:** Even if it ran, no ports are exposed in docker-compose.yml
4. **Disabled by Default:** `ENABLE_WEATHER_API=false` suggests it's not actively used

---

### 2. Why Dashboard Shows Weather as "Healthy"

The dashboard displays weather metrics from the **embedded enrichment service** in `websocket-ingestion`, NOT from the standalone `weather-api` container.

**Data Flow:**
```
Home Assistant Events
  ↓
websocket-ingestion service
  ↓ (embedded weather enrichment)
OpenWeatherMap API → Weather Cache → Enriched Events
  ↓
enrichment-pipeline → InfluxDB
  ↓
admin-api → Dashboard
```

The standalone `weather-api` container is **not in the data flow** at all.

---

### 3. OpenWeatherMap Location Format

Based on Context7 KB research of OpenWeatherMap API documentation:

**Correct Format:** `{city name},{state code},{country code}`

**For Las Vegas, Nevada, USA:**
- **Recommended:** `Las Vegas,NV,US`
- **Alternative (coordinates):** `lat=36.17497&lon=-115.13722`
- **Alternative (ZIP):** `89101,US`

**Current Configuration:** `London,UK` (needs to be changed)

---

## Recommendations

### OPTION 1: Remove Redundant Standalone Service (RECOMMENDED)

**Rationale:**
- The embedded enrichment approach is working perfectly
- Standalone service is broken and unused
- Having two implementations causes confusion
- Removes maintenance burden

**Actions:**
1. Remove `weather-api` service from `docker-compose.yml`
2. Delete `services/weather-api/` directory (or archive it)
3. Update documentation to reflect embedded approach
4. Update default location to Las Vegas

**Pros:**
- ✓ Simplifies architecture
- ✓ Eliminates confusion
- ✓ Reduces Docker container count
- ✓ No risk to working system

**Cons:**
- ✗ Loses potential future flexibility
- ✗ May have been planned for different use case

### OPTION 2: Fix Standalone Service

**Rationale:**
- Preserve architectural separation
- May have been intended for different use case
- Provides standalone weather API endpoint

**Actions:**
1. Fix Python module import error in Dockerfile
2. Add `__init__.py` files to make `src/` a proper package
3. Expose port 8001 in docker-compose.yml (conflicts with websocket-ingestion!)
4. Change port to 8005 or similar
5. Set `ENABLE_WEATHER_API=true`
6. Determine actual purpose and integration point

**Pros:**
- ✓ Preserves architectural flexibility
- ✓ Provides standalone weather endpoint
- ✓ May be useful for future features

**Cons:**
- ✗ More complex architecture
- ✗ Duplicate functionality
- ✗ Additional maintenance burden
- ✗ Not currently integrated with any service

### OPTION 3: Keep Both (Current State)

**Rationale:**
- Avoid making changes
- Let broken service restart indefinitely

**Actions:**
- None (maintain status quo)

**Pros:**
- ✓ No changes needed

**Cons:**
- ✗ Confusing architecture
- ✗ Broken service consuming resources
- ✗ Unclear which service is responsible for what

---

## Recommended Action Plan

### Phase 1: Update Weather Location (IMMEDIATE)
- ✓ Change default location to Las Vegas
- ✓ Test weather enrichment with new location
- ✓ Verify dashboard displays correct data

### Phase 2: Architectural Cleanup (RECOMMENDED)
- ✓ Remove standalone `weather-api` service from docker-compose.yml
- ✓ Document that weather enrichment is embedded in websocket-ingestion
- ✓ Update architecture documentation
- ✓ Archive `services/weather-api/` for future reference (optional)

### Phase 3: Documentation (REQUIRED)
- ✓ Update architecture diagrams
- ✓ Update deployment documentation
- ✓ Update developer guide
- ✓ Add weather service configuration guide

---

## Technical Details

### OpenWeatherMap API Call Format

Based on Context7 KB documentation research:

**Current Weather API (2.5):**
```bash
# By city name (deprecated but still works)
GET https://api.openweathermap.org/data/2.5/weather?q=Las Vegas,NV,US&appid={API_KEY}

# By coordinates (recommended)
GET https://api.openweathermap.org/data/2.5/weather?lat=36.17497&lon=-115.13722&appid={API_KEY}

# By city ID
GET https://api.openweathermap.org/data/2.5/weather?id=5506956&appid={API_KEY}
```

**Parameters:**
- `q`: City name, state code, country code (comma-separated)
- `lat` / `lon`: Geographical coordinates
- `id`: OpenWeatherMap city ID
- `appid`: API key (required)
- `units`: standard, metric, or imperial (optional)
- `lang`: Language code (optional)

**ISO 3166 Codes:**
- Country: US (United States)
- State: NV (Nevada)

---

## Conclusion

The system has **working weather integration** through the embedded enrichment service. The standalone `weather-api` container is broken and unused. 

**Recommended Next Steps:**
1. ✓ Update default location to Las Vegas
2. ✓ Remove standalone weather-api service
3. ✓ Update documentation

This will result in a **cleaner, more maintainable architecture** with no impact to functionality.

---

## Appendix: Service Status

### Working Services ✓
- `homeiq-influxdb` - Up 30 minutes (healthy)
- `homeiq-enrichment` - Up 30 minutes (healthy)
- `homeiq-websocket` - Up 19 minutes (healthy)
- `homeiq-admin` - Up 12 minutes (healthy)
- `homeiq-dashboard` - Up 9 minutes (healthy)

### Broken Services ✗
- `homeiq-weather` - **Restarting (1) 44 seconds ago** - ModuleNotFoundError
- `homeiq-data-retention` - **Restarting (1) 37 seconds ago** - Separate issue

### Weather Metrics (from working embedded service)
- Total Events Processed: 335
- Successful Enrichments: 335
- Failed Enrichments: 0
- Cache Hit Rate: 98.51%
- API Calls: 5
- Success Rate: 100%

