# Team Tracker Data Sync & TappsCodingAgents Knowledge Plan

**Date**: January 16, 2026  
**Status**: In Progress  
**Goal**: Ensure Team Tracker data loads into database and add to TappsCodingAgents knowledge base

## Data Flow Verification

### Current Flow
```
Home Assistant (Team Tracker Integration)
  ↓ Entity Registry
  ↓ WebSocket Events
  ↓
websocket-ingestion Service
  ↓ Discovery Service
  ↓ /internal/entities/bulk_upsert
  ↓
data-api Service
  ↓ DeviceEntity Table (SQLite)
  ↓ platform="teamtracker" OR entity_id contains "team_tracker"
  ↓
device-intelligence-service
  ↓ DataAPIClient.fetch_entities(domain="sensor")
  ↓ Filter for Team Tracker
  ↓
TeamTrackerTeam Table (device-intelligence-service SQLite)
```

### Verification Points

1. **Entity Sync** ✅ CONFIRMED
   - `services/data-api/src/devices_endpoints.py:1339` includes `platform=entity_data.get('platform', 'unknown')`
   - Platform field is stored in DeviceEntity table
   - Sync happens via `/internal/entities/bulk_upsert` endpoint

2. **Team Tracker Detection**
   - Platform matching: `platform="teamtracker"` or variations
   - Entity ID matching: `entity_id contains "team_tracker"`
   - Detection logic in `services/device-intelligence-service/src/api/team_tracker_router.py:153-202`

3. **Database Storage**
   - DeviceEntity table (data-api): Entity metadata with platform field
   - TeamTrackerTeam table (device-intelligence-service): Detected teams

## TappsCodingAgents Knowledge Base Status

### Current Status: ⚠️ PARTIAL

**Team Tracker References Found:**
- ✅ Mentioned in tech-stack.md files (5 files)
- ✅ Mentioned in architecture documentation
- ❌ No dedicated knowledge base file
- ❌ No Team Tracker expert knowledge
- ❌ Not in Context7 cache

**Files with Team Tracker References:**
1. `.tapps-agents/knowledge/time-series-analytics/tech-stack.md`
2. `.tapps-agents/knowledge/microservices-architecture/tech-stack.md`
3. `.tapps-agents/knowledge/iot-home-automation/tech-stack.md`
4. `.tapps-agents/knowledge/home-assistant/tech-stack.md`
5. `.tapps-agents/knowledge/frontend-ux/tech-stack.md`

**Content**: Only mentions Team Tracker as part of tech stack, no implementation details

## Action Items

### Phase 1: Verify Data Sync (Priority: HIGH)

1. **Check Entity Sync**
   - Verify websocket-ingestion is syncing entities with platform field
   - Check if Team Tracker entities exist in DeviceEntity table
   - Verify platform value is "teamtracker" or "team_tracker"

2. **Test Detection**
   - Run detection endpoint: `POST /api/team-tracker/detect`
   - Check if entities are found
   - Verify TeamTrackerTeam records are created

3. **Database Query**
   - Query DeviceEntity table for Team Tracker entities
   - Verify platform and entity_id values

### Phase 2: Add TappsCodingAgents Knowledge (Priority: MEDIUM)

1. **Create Team Tracker Knowledge Base**
   - Location: `.tapps-agents/knowledge/home-assistant/team-tracker.md`
   - Content: Team Tracker integration guide, entity patterns, detection logic

2. **Update Home Assistant Expert**
   - Add Team Tracker to expert-home-assistant knowledge
   - Include detection patterns and troubleshooting

3. **Add to Context7 Cache (Optional)**
   - If Team Tracker has library docs, add to Context7 cache
   - Currently uses HACS integration, may not have separate library

### Phase 3: Create Diagnostic Script (Priority: MEDIUM)

1. **Database Verification Script**
   - Check DeviceEntity table for Team Tracker entities
   - Verify platform values
   - List detected teams

2. **Sync Status Script**
   - Check when entities were last synced
   - Verify sync frequency
   - Check for sync errors

## Implementation

### Step 1: Create Team Tracker Knowledge Base

**File**: `.tapps-agents/knowledge/home-assistant/team-tracker.md`

**Content Should Include:**
- Team Tracker integration overview
- Entity ID patterns
- Platform value patterns
- Detection logic
- Troubleshooting guide
- API endpoints
- Database schema

### Step 2: Update Home Assistant Expert Knowledge

**File**: `.tapps-agents/knowledge/home-assistant/` (add Team Tracker section)

### Step 3: Create Diagnostic Script

**File**: `scripts/diagnose-team-tracker.py`

**Should Check:**
- DeviceEntity table for Team Tracker entities
- Platform values
- Entity ID patterns
- Last sync time
- TeamTrackerTeam records

## Verification Commands

### PowerShell - Check Data API Entities
```powershell
# Check for Team Tracker entities
Invoke-RestMethod -Uri "http://localhost:8006/api/data/entities?domain=sensor&platform=teamtracker&limit=100" `
  -Headers @{Authorization="Bearer hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"}

# Check all sensor entities (look for team_tracker in entity_id)
Invoke-RestMethod -Uri "http://localhost:8006/api/data/entities?domain=sensor&limit=1000" `
  -Headers @{Authorization="Bearer hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"} | 
  ConvertTo-Json -Depth 10 | 
  Select-String -Pattern "team.*tracker" -CaseSensitive:$false
```

### PowerShell - Test Detection
```powershell
# Test Team Tracker detection
Invoke-RestMethod -Uri "http://localhost:3001/api/device-intelligence/team-tracker/detect" `
  -Method Post `
  -Headers @{Authorization="Bearer hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"}

# Check debug platforms
Invoke-RestMethod -Uri "http://localhost:3001/api/device-intelligence/team-tracker/debug/platforms" `
  -Headers @{Authorization="Bearer hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"}
```

## Success Criteria

- [ ] Team Tracker entities are in DeviceEntity table with correct platform value
- [ ] Detection endpoint finds Team Tracker entities
- [ ] TeamTrackerTeam records are created
- [ ] Team Tracker knowledge base file created
- [ ] Home Assistant expert updated with Team Tracker knowledge
- [ ] Diagnostic script created and working

## Next Steps

1. Create Team Tracker knowledge base file
2. Update Home Assistant expert knowledge
3. Create diagnostic script
4. Run verification commands
5. Test detection end-to-end
