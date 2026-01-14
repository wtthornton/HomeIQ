# Team Tracker Reconnection Plan

**Date**: January 16, 2026  
**Issue**: Team Tracker integration showing "Not Installed" despite being installed in Home Assistant  
**Error**: "Failed to load preferences: {"detail":"Not Found"}" (separate issue but visible on same page)

## Problem Analysis

### Issue 1: Team Tracker Not Detected
- **Symptom**: Settings page shows "Not Installed" and "0 teams configured"
- **Expected**: Should detect Team Tracker sensors from Home Assistant
- **User Confirmation**: Team Tracker is installed in Home Assistant

### Issue 2: Preferences Endpoint 404 (Separate Issue)
- **Symptom**: Error message "Failed to load preferences: {"detail":"Not Found"}"
- **Location**: Same Settings page, different component (`PreferenceSettings.tsx`)
- **Note**: This is handled gracefully (returns defaults), but shows error message

## Architecture Flow

```
UI (Settings.tsx)
  ↓
TeamTrackerSettings.tsx
  ↓ fetchStatus()
  ↓ GET /api/device-intelligence/team-tracker/status
  ↓
Nginx Proxy (nginx.conf:19-24)
  ↓ location /api/device-intelligence/(.*)
  ↓ proxy_pass http://device-intelligence-service:8019/api/$1
  ↓
Device Intelligence Service (port 8019)
  ↓ router prefix: /api/team-tracker
  ↓ GET /api/team-tracker/status
  ↓
Team Tracker Router (team_tracker_router.py)
  ↓ Query database for TeamTrackerIntegration status
  ↓
[If detecting]
  ↓ POST /api/team-tracker/detect
  ↓
DataAPIClient
  ↓ fetch_entities(domain="sensor")
  ↓ GET /api/data/entities?domain=sensor
  ↓
Data API Service (port 8006)
  ↓ Query DeviceEntity table (SQLite)
  ↓ Filter for Team Tracker entities
  ↓
Return detected entities
```

## Root Cause Analysis

### Potential Issues

1. **Service Not Running**
   - Device intelligence service may not be running
   - Port mismatch (nginx expects 8019, service may be on 8028)
   - Service health check fails

2. **Data API Connectivity**
   - Device intelligence service can't reach data-api service
   - Data-api not syncing entities from Home Assistant
   - Entities not in DeviceEntity table

3. **Detection Logic Issues**
   - Platform matching not finding Team Tracker entities
   - Entity ID patterns not matching
   - Case sensitivity issues

4. **Database State**
   - TeamTrackerIntegration record doesn't exist
   - Status stuck at "not_installed"
   - Last detection failed but wasn't retried

5. **Preferences API (Separate)**
   - Preferences endpoint not implemented in current service
   - Routing issue (preferences may need different service)

## Investigation Steps

### Step 1: Verify Service Health
```bash
# Check device-intelligence-service health
curl http://localhost:8019/health
# Or via nginx
curl http://localhost:3001/api/device-intelligence/health

# Check service logs
docker logs device-intelligence-service
```

### Step 2: Test Team Tracker API Directly
```bash
# Test status endpoint
curl -H "Authorization: Bearer hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR" \
  http://localhost:3001/api/device-intelligence/team-tracker/status

# Test detection endpoint
curl -X POST -H "Authorization: Bearer hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR" \
  http://localhost:3001/api/device-intelligence/team-tracker/detect

# Check debug endpoint for platform values
curl -H "Authorization: Bearer hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR" \
  http://localhost:3001/api/device-intelligence/team-tracker/debug/platforms
```

### Step 3: Verify Data API Connection
```bash
# Check data-api service
curl http://localhost:8006/health

# Test entities endpoint
curl -H "Authorization: Bearer hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR" \
  "http://localhost:8006/api/data/entities?domain=sensor&limit=100"

# Search for Team Tracker entities
curl -H "Authorization: Bearer hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR" \
  "http://localhost:8006/api/data/entities?domain=sensor&platform=teamtracker"
```

### Step 4: Check Home Assistant Directly
```bash
# List all sensors
curl -H "Authorization: Bearer <HA_TOKEN>" \
  http://192.168.1.86:8123/api/states | \
  jq '.[] | select(.entity_id | contains("team_tracker"))'

# Check specific Team Tracker sensor
curl -H "Authorization: Bearer <HA_TOKEN>" \
  http://192.168.1.86:8123/api/states/sensor.vgk_team_tracker
```

### Step 5: Review Detection Logic
- Check platform matching in `team_tracker_router.py` lines 153-202
- Verify entity_id patterns match actual Team Tracker sensors
- Check case sensitivity in matching

## Fix Strategy

### Fix 1: Service Connectivity (Priority: HIGH)
**If service is not running or unreachable:**
1. Verify docker-compose.yml has device-intelligence-service
2. Check service is running: `docker ps | grep device-intelligence`
3. Verify port mapping (should be 8019 or match nginx config)
4. Check service logs for startup errors
5. Verify database initialization

### Fix 2: Data API Sync (Priority: HIGH)
**If entities not in data-api:**
1. Verify websocket-ingestion is syncing entities to DeviceEntity table
2. Check data-api has Team Tracker entities in database
3. Verify entity sync includes platform field
4. Check if Team Tracker sensors have correct platform value ("teamtracker" or "team_tracker")

### Fix 3: Detection Logic Enhancement (Priority: MEDIUM)
**If detection logic not matching:**
1. Improve platform matching (current code already checks multiple variations)
2. Add more entity_id pattern variations if needed
3. Add logging to show which entities are checked and why they match/don't match
4. Consider querying Home Assistant directly as fallback

### Fix 4: Database State Reset (Priority: MEDIUM)
**If database state is stale:**
1. Reset TeamTrackerIntegration record
2. Clear old detection failures
3. Force re-detection

### Fix 5: Preferences Endpoint (Priority: LOW - Separate Issue)
**Fix preferences 404:**
1. Verify preferences endpoint exists in ai-automation-service
2. Check routing configuration
3. Update error handling to be less prominent (already handled gracefully)

## Implementation Plan

### Phase 1: Diagnosis (Day 1)
- [x] Review all code and architecture
- [ ] Run service health checks
- [ ] Test API endpoints directly
- [ ] Check data-api for Team Tracker entities
- [ ] Verify Home Assistant has Team Tracker sensors

### Phase 2: Fix Service Issues (Day 1)
- [ ] Fix service connectivity if needed
- [ ] Fix data-api sync if entities missing
- [ ] Update nginx routing if misconfigured
- [ ] Fix port mismatches

### Phase 3: Enhance Detection (Day 2)
- [ ] Improve detection logging
- [ ] Add fallback to query Home Assistant directly
- [ ] Enhance platform/entity_id matching if needed
- [ ] Add diagnostic endpoints

### Phase 4: Testing & Validation (Day 2)
- [ ] Test detection with actual Team Tracker sensors
- [ ] Verify status updates correctly
- [ ] Test "Detect Teams" button
- [ ] Verify teams appear in UI
- [ ] Test sync from HA functionality

### Phase 5: Fix Preferences (Day 2 - Lower Priority)
- [ ] Identify why preferences endpoint returns 404
- [ ] Fix routing or implement endpoint
- [ ] Update error handling

## Testing Checklist

- [ ] Service health check returns 200
- [ ] Status endpoint returns current integration status
- [ ] Detect endpoint finds Team Tracker entities
- [ ] Detection updates database correctly
- [ ] UI shows correct status after detection
- [ ] Teams list shows detected teams
- [ ] Sync from HA updates team details
- [ ] Debug endpoint shows platform values
- [ ] Preferences endpoint works (separate fix)

## Files to Review

1. **services/device-intelligence-service/src/api/team_tracker_router.py**
   - Detection logic (lines 137-355)
   - Status endpoint (lines 87-134)
   - Platform matching (lines 153-202)

2. **services/ai-automation-ui/src/components/TeamTrackerSettings.tsx**
   - UI component for Team Tracker settings
   - API calls and error handling

3. **services/ai-automation-ui/src/config/api.ts**
   - API endpoint configuration
   - DEVICE_INTELLIGENCE base URL

4. **services/ai-automation-ui/nginx.conf**
   - Nginx proxy configuration (lines 19-24)
   - Routing to device-intelligence-service

5. **services/device-intelligence-service/src/main.py**
   - Router registration (line 164)
   - Service setup

6. **services/device-intelligence-service/src/clients/data_api_client.py**
   - DataAPIClient implementation
   - Entity fetching logic

## Debugging Commands

```bash
# PowerShell - Check service health
Invoke-RestMethod -Uri "http://localhost:8019/health"

# PowerShell - Test status endpoint
Invoke-RestMethod -Uri "http://localhost:3001/api/device-intelligence/team-tracker/status" `
  -Headers @{Authorization="Bearer hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"}

# PowerShell - Test detection
Invoke-RestMethod -Uri "http://localhost:3001/api/device-intelligence/team-tracker/detect" `
  -Method Post `
  -Headers @{Authorization="Bearer hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"}

# PowerShell - Check debug platforms
Invoke-RestMethod -Uri "http://localhost:3001/api/device-intelligence/team-tracker/debug/platforms" `
  -Headers @{Authorization="Bearer hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"}

# PowerShell - Check data-api entities
Invoke-RestMethod -Uri "http://localhost:8006/api/data/entities?domain=sensor&limit=10" `
  -Headers @{Authorization="Bearer hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"}
```

## Next Steps

1. **Immediate**: Run health checks and test API endpoints to identify the failure point
2. **Short-term**: Fix service connectivity or data sync issues
3. **Medium-term**: Enhance detection logic and add better error messages
4. **Long-term**: Add comprehensive monitoring and automatic re-detection

## Success Criteria

- Team Tracker status shows "Installed" when sensors exist
- "Detect Teams" button successfully finds Team Tracker entities
- Detected teams appear in the teams list
- Status updates reflect current state from Home Assistant
- Preferences endpoint works (separate fix)
