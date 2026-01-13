# Proactive Context Data - Testing Guide

**Date:** January 12, 2026  
**Purpose:** Guide for testing the proactive context data fixes

## Quick Test

### 1. Restart Services

```bash
# Restart the modified services
docker compose restart proactive-agent-service data-api
```

### 2. Test Context Analysis Directly

Use the debug endpoint to see context data without creating suggestions:

```bash
# PowerShell
Invoke-RestMethod -Uri "http://localhost:8031/api/v1/suggestions/debug/context" | ConvertTo-Json -Depth 10

# Or curl (if available)
curl http://localhost:8031/api/v1/suggestions/debug/context | jq
```

**Expected Output:**
- `sports.insights` should contain messages even when `upcoming_games` and `live_games` are empty
- `historical_patterns.insights` should contain query info even when `events` is empty
- `energy.current_intensity` should contain actual data (if carbon-intensity-service is running)
- `energy.trends` should contain 24h average/min/max and trend direction

### 3. Test Carbon Intensity Endpoints

```bash
# Test current intensity
Invoke-RestMethod -Uri "http://localhost:8006/api/v1/energy/carbon-intensity/current"

# Test trends
Invoke-RestMethod -Uri "http://localhost:8006/api/v1/energy/carbon-intensity/trends"
```

**Expected:**
- If carbon-intensity-service is running and has data: Returns carbon intensity data
- If no data: Returns 404 (gracefully handled by client)

### 4. View in UI

1. Navigate to `http://localhost:3001/proactive`
2. Find a suggestion (or trigger one: `POST /api/v1/suggestions/trigger`)
3. Expand "Context Details" section
4. Verify:
   - Sports shows insights even with no games
   - Historical patterns shows query info
   - Energy shows carbon intensity data and trends (if available)

## Detailed Test Cases

### Test Case 1: Sports Insights with No Games

**Setup:**
- Ensure no live or upcoming games (or mock empty response)

**Expected:**
```json
{
  "sports": {
    "available": true,
    "live_games": [],
    "upcoming_games": [],
    "insights": [
      "No games scheduled - sports automations can be set up for future games",
      "Team Tracker sensors detected - automations will trigger automatically when games start"
    ]
  }
}
```

### Test Case 2: Historical Patterns with No Events

**Setup:**
- Ensure no events in last 7 days (or mock empty response)

**Expected:**
```json
{
  "historical_patterns": {
    "available": true,
    "events": [],
    "patterns": [],
    "insights": [
      "No events found in last 7 days - patterns will appear as usage increases"
    ],
    "query_info": {
      "days_back": 7,
      "start_time": "...",
      "end_time": "..."
    }
  }
}
```

### Test Case 3: Energy Data with Carbon Intensity Service Running

**Setup:**
- Ensure carbon-intensity-service is running
- Ensure carbon_data bucket exists in InfluxDB
- Ensure carbon-intensity-service has written data

**Expected:**
```json
{
  "energy": {
    "available": true,
    "current_intensity": {
      "intensity": 250.5,
      "renewable_percentage": 45.2,
      "fossil_percentage": 54.8,
      "forecast_1h": 240.0,
      "forecast_24h": 230.0,
      "timestamp": "...",
      "region": "CAISO_NORTH",
      "grid_operator": "CAISO"
    },
    "trends": {
      "average_24h": 245.3,
      "min_24h": 180.0,
      "max_24h": 320.0,
      "trend": "decreasing"
    },
    "insights": [
      "High carbon intensity - consider delaying energy-intensive tasks",
      "Carbon intensity trending downward - good time for energy tasks"
    ]
  }
}
```

### Test Case 4: Energy Data without Carbon Intensity Service

**Setup:**
- Stop carbon-intensity-service or ensure no data in InfluxDB

**Expected:**
```json
{
  "energy": {
    "available": false,
    "current_intensity": null,
    "trends": null,
    "insights": []
  }
}
```

**Note:** Should gracefully degrade without errors.

## Troubleshooting

### Issue: Carbon Intensity Returns 404

**Possible Causes:**
1. Carbon-intensity-service not running
2. Carbon_data bucket doesn't exist in InfluxDB
3. No data written to InfluxDB yet

**Solutions:**
1. Check carbon-intensity-service logs: `docker compose logs carbon-intensity-service`
2. Verify bucket exists: Check InfluxDB UI or query buckets
3. Wait for carbon-intensity-service to write data (runs on schedule)

### Issue: Sports Insights Still Empty

**Check:**
1. Verify the code change was applied (check `context_analysis_service.py` line ~197)
2. Check logs for errors in `analyze_sports()`
3. Verify sports client is working: Check `sports_client.get_live_games()` and `get_upcoming_games()`

### Issue: Historical Patterns Shows `available: false`

**Check:**
1. Verify the code change was applied (check `context_analysis_service.py` line ~296)
2. Check data-api is accessible: `Invoke-RestMethod -Uri "http://localhost:8006/health"`
3. Check data-api events endpoint: `Invoke-RestMethod -Uri "http://localhost:8006/events?limit=10"`

## Verification Checklist

- [ ] Services restarted successfully
- [ ] Debug endpoint returns context data
- [ ] Sports insights appear even with no games
- [ ] Historical patterns shows query info when empty
- [ ] Energy data fetches from InfluxDB (if service running)
- [ ] Energy trends calculated correctly
- [ ] Error messages appear in context details when services unavailable
- [ ] UI displays all context data correctly

## Related Files

- Implementation: `implementation/PROACTIVE_CONTEXT_DATA_FIXES_COMPLETE.md`
- Analysis: `implementation/analysis/PROACTIVE_CONTEXT_DATA_ANALYSIS.md`
