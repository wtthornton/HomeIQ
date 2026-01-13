# Proactive Context Data Analysis & Recommendations

**Date:** January 12, 2026  
**Issue:** Context data in proactive suggestions showing empty fields for sports, energy, and historical patterns  
**Service:** `proactive-agent-service` (Port 8031)  
**UI Location:** `http://localhost:3001/proactive` → Pattern → "Context Details" section

## Executive Summary

The proactive suggestions UI displays context details (weather, sports, energy, historical patterns), but several fields are empty:

| Context Type | Issue | Impact | Priority |
|-------------|-------|--------|----------|
| **Sports** | No insights when no games scheduled | Low - data available but insights missing | P2 |
| **Energy** | Never queries InfluxDB for carbon intensity | High - entire energy context unavailable | P1 |
| **Historical Patterns** | Returns `available: False` immediately if no events | Medium - should show query info even when empty | P3 |

**Root Causes:**
1. **Energy**: `CarbonIntensityClient` always returns `None` - never queries data-api/InfluxDB
2. **Sports**: Insights only generated when games exist - no fallback insights
3. **Historical**: Returns `available: False` immediately - doesn't show diagnostic info

**Quick Wins:**
- Add insights for sports when no games (5 min fix)
- Improve historical patterns error messages (10 min fix)
- Implement carbon intensity query (30-60 min - requires data-api endpoint)

## Problem Summary

The proactive suggestions UI (`http://localhost:3001/proactive`) displays context details, but many fields are empty:

- **Sports**: `upcoming_games: []`, `insights: []` (even though `available: true`)
- **Energy**: `trends: null`, no forecast data (even though `available: false` but should be populated)
- **Historical Patterns**: `events: []`, `patterns: []`, `insights: []` (even though `available: false` but should try to fetch)

## Root Cause Analysis

### 1. Sports Data Issues

**Location:** `services/proactive-agent-service/src/services/context_analysis_service.py:169-213`

**Problems:**
- `analyze_sports()` returns `available: True` even when no games are found
- Insights are only generated when games exist (`if live_games:` or `if upcoming_games:`)
- No fallback insights when sports data is available but no games scheduled
- Sports client may be returning empty arrays silently (graceful degradation)

**Code Issues:**
```python
# Line 198-203: Returns available=True even with empty arrays
return {
    "available": True,  # ❌ Should be False if no games AND no data source
    "live_games": live_games[:10],
    "upcoming_games": upcoming_games[:10],
    "insights": insights,  # Empty if no games
}
```

### 2. Energy Data Issues

**Location:** `services/proactive-agent-service/src/services/context_analysis_service.py:215-257`

**Problems:**
- `CarbonIntensityClient.get_current_intensity()` always returns `None` (line 58 in client)
- No actual query to data-api for carbon intensity data from InfluxDB
- `trends` is hardcoded to `None` with comment "Future: analyze trends from InfluxDB"
- No forecast data structure at all

**Code Issues:**
```python
# services/proactive-agent-service/src/clients/carbon_intensity_client.py:43-61
async def get_current_intensity(self) -> dict[str, Any] | None:
    try:
        # Carbon intensity service may not have a direct API endpoint
        # In that case, we'll query via data-api for InfluxDB data
        # For now, return None gracefully
        logger.debug("Carbon intensity data is stored in InfluxDB, query via data-api")
        return None  # ❌ Never actually queries data-api
```

### 3. Historical Patterns Issues

**Location:** `services/proactive-agent-service/src/services/context_analysis_service.py:259-320`

**Problems:**
- `analyze_historical_patterns()` returns `available: False` when no events found
- Should query data-api for events, but may be failing silently
- Pattern detection only works if events exist
- No insights generated when no patterns detected

**Code Issues:**
```python
# Line 291-298: Returns available=False immediately if no events
if not events:
    logger.debug("No historical events found")
    return {
        "available": False,  # ❌ Should still try to query and show what was attempted
        "events": [],
        "patterns": [],
        "insights": [],
    }
```

## Recommendations

### Priority 1: Fix Energy Data Fetching

**Issue:** Carbon intensity client never queries data-api for InfluxDB data.

**Current State:**
- `carbon-intensity` service (port 8010) writes carbon intensity data to InfluxDB
- Data is stored in `home_assistant_events` bucket with measurement `carbon_intensity`
- `CarbonIntensityClient.get_current_intensity()` always returns `None` (placeholder)
- No data-api endpoint exists for carbon intensity (only power consumption endpoints exist)

**Fix Options:**

**Option A: Query InfluxDB directly via data-api (Recommended)**
1. Add carbon intensity endpoint to data-api:
   ```python
   # services/data-api/src/energy_endpoints.py
   @router.get("/carbon-intensity/current")
   async def get_current_carbon_intensity():
       """Get current carbon intensity from InfluxDB"""
       # Query InfluxDB for latest carbon_intensity measurement
       # Return: { "intensity": float, "timestamp": datetime, "forecast": [...] }
   ```

2. Update carbon intensity client to query data-api:
   ```python
   # services/proactive-agent-service/src/clients/carbon_intensity_client.py
   async def get_current_intensity(self) -> dict[str, Any] | None:
       """Get current carbon intensity from data-api (InfluxDB)."""
       try:
           response = await self.client.get(
               f"{self.data_api_base_url}/api/v1/energy/carbon-intensity/current"
           )
           response.raise_for_status()
           return response.json()
       except Exception as e:
           logger.warning(f"Error fetching carbon intensity: {str(e)}")
           return None
   ```

**Option B: Query carbon-intensity service directly**
- Check if carbon-intensity service has a `/current` or `/health` endpoint
- If yes, query it directly instead of going through data-api

**Also implement trends analysis:**
```python
# In context_analysis_service.py analyze_energy()
# Query historical carbon intensity data for trends
trends = await self._analyze_energy_trends()  # Query last 24 hours from data-api
```

### Priority 2: Improve Sports Data Insights

**Issue:** No insights when no games are scheduled.

**Fix:** Generate contextual insights even when no games:

```python
# services/proactive-agent-service/src/services/context_analysis_service.py
async def analyze_sports(self) -> dict[str, Any]:
    # ... existing code ...
    
    insights = []
    if live_games:
        insights.append(f"{len(live_games)} game(s) currently live - consider viewing automation")
    elif upcoming_games:
        next_game = upcoming_games[0] if upcoming_games else None
        if next_game:
            insights.append(
                f"Upcoming game scheduled - consider pre-game automation (lights, temperature)"
            )
    else:
        # ✅ NEW: Generate insights even when no games
        insights.append("No games scheduled - sports automations can be set up for future games")
        insights.append("Team Tracker sensors detected - automations will trigger automatically when games start")
    
    # Determine availability based on whether sports-api is accessible
    # (not just whether games exist)
    available = await self._check_sports_api_available()
    
    return {
        "available": available,
        "live_games": live_games[:10],
        "upcoming_games": upcoming_games[:10],
        "insights": insights,
    }
```

### Priority 3: Enhance Historical Patterns Query

**Issue:** Returns `available: False` immediately if no events, doesn't show what was attempted.

**Fix:** Better error handling and diagnostic information:

```python
# services/proactive-agent-service/src/services/context_analysis_service.py
async def analyze_historical_patterns(
    self, days_back: int = 7, limit: int = 100
) -> dict[str, Any]:
    # ... existing code ...
    
    try:
        events = await self.data_api_client.get_events(
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            limit=limit,
        )
        
        # ✅ NEW: Better handling when no events
        if not events:
            logger.debug(f"No historical events found in last {days_back} days")
            return {
                "available": True,  # Data source is available, just no events
                "events": [],
                "patterns": [],
                "insights": [
                    f"No events found in last {days_back} days - patterns will appear as usage increases"
                ],
                "query_info": {
                    "days_back": days_back,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                }
            }
        
        # ... rest of pattern detection ...
        
    except Exception as e:
        logger.error(f"Error analyzing historical patterns: {str(e)}", exc_info=True)
        return {
            "available": False,
            "error": str(e),
            "events": [],
            "patterns": [],
            "insights": [f"Unable to fetch historical data: {str(e)}"],
        }
```

### Priority 4: Add Data-API Endpoints (If Missing)

**Check if these endpoints exist in data-api:**
- `/api/v1/energy/carbon-intensity/current` - Current carbon intensity
- `/api/v1/energy/carbon-intensity/history` - Historical trends
- `/api/v1/energy/carbon-intensity/forecast` - Forecast data

**If missing, implement them in data-api service.**

### Priority 5: Improve Error Visibility

**Issue:** Errors are logged but not visible in UI context data.

**Fix:** Include error information in context response:

```python
# Add error field to all context responses
return {
    "available": False,
    "error": str(e),  # ✅ Include error message
    "error_type": type(e).__name__,  # ✅ Include error type
    # ... rest of fields ...
}
```

## Implementation Plan

### Phase 1: Quick Wins (1-2 hours)
1. ✅ Fix carbon intensity client to query data-api
2. ✅ Add insights for sports when no games scheduled
3. ✅ Improve historical patterns error messages

### Phase 2: Data-API Integration (2-4 hours)
1. ✅ Verify/implement carbon intensity endpoints in data-api
2. ✅ Implement trends analysis for energy data
3. ✅ Add forecast data structure for energy

### Phase 3: Enhanced Diagnostics (1-2 hours)
1. ✅ Add error visibility in context responses
2. ✅ Add query metadata (time ranges, filters used)
3. ✅ Improve logging for debugging

## Testing Checklist

- [ ] Sports data shows insights even when no games scheduled
- [ ] Energy data shows current intensity from InfluxDB
- [ ] Energy trends are calculated from historical data
- [ ] Historical patterns show query info even when no events
- [ ] Error messages are visible in UI context details
- [ ] All context sources show diagnostic information

## Related Files

- `services/proactive-agent-service/src/services/context_analysis_service.py` - Main analysis service
- `services/proactive-agent-service/src/clients/carbon_intensity_client.py` - Energy client
- `services/proactive-agent-service/src/clients/sports_data_client.py` - Sports client
- `services/proactive-agent-service/src/clients/data_api_client.py` - Historical data client
- `services/data-api/src/` - Data API endpoints (verify/implement energy endpoints)

## Notes

- Context data is stored in `context_metadata` field of suggestions (see `suggestion_pipeline_service.py:236`)
- UI displays this data in the "Context Details" collapsible section
- All clients use graceful degradation (return empty arrays/None on error)
- Need to balance between showing errors vs. graceful degradation
