# HomeIQ Architecture Transformation: Sports Data Simplified

## Executive Summary

For single-home HA setup: Remove sports-data service, use existing HACS integrations (Team Tracker, hass-nhlapi). HomeIQ Dashboard reads sports data from HA sensors. Simple, practical, follows Context7 principles.

**Goal**: HA = Integration Hub, HomeIQ = Visualization/Analytics Layer

## Current Problem

**Over-Engineering:**
- 2,500+ lines sports-data service (unnecessary complexity)
- Sends webhooks TO HA (HomeIQ shouldn't control triggers)
- Duplicates functionality available in HACS
- Service requires maintenance for non-core feature

**Better Approach:**
- Use proven HACS integrations (Team Tracker, hass-nhlapi)
- HomeIQ reads sports FROM HA sensors
- Delete sports-data service entirely
- Focus on what matters: home automation intelligence

## Simplified Solution

### Recommended Flow (Practical)
```
User installs Team Tracker (HACS) → HA manages sports → 
HomeIQ reads HA sensors → Dashboard displays sports
```

### Two Paths (User Choice)

**PATH A - Use Existing Integrations (RECOMMENDED)**
1. Delete sports-data service entirely
2. User installs Team Tracker or hass-nhlapi via HACS
3. HomeIQ Dashboard reads from HA sensors
4. Done - minimal code changes

**PATH B - Custom Integration (If Needed)**
1. Create simple homeiq-sports in same repo (no separate org)
2. User manually copies to custom_components/
3. HomeIQ Dashboard reads from HA sensors
4. Delete sports-data service

## Implementation (Choose Your Path)

### PATH A: Use Existing HACS Integrations (RECOMMENDED - 2-3 days)

**Why**: Leverage battle-tested integrations. Zero development overhead.

**Steps**:
1. **Delete sports-data** (5 minutes)
   - Remove from docker-compose.yml
   - Delete services/sports-data/

2. **Update Dashboard to read HA sensors** (1-2 days)
   - Modify `services/health-dashboard/src/hooks/useSportsData.ts`
   - Change from data-api to HA REST API
   - Parse HA sensor states

3. **Done** - User installs Team Tracker via HACS

**Code Change** (50 lines):
```typescript
// Before: useSportsData.ts
async function fetchSportsData() {
  return await apiClient.get('/api/sports/live-games');
}

// After: Read from HA
async function fetchSportsData() {
  const states = await haApi.get('/api/states');
  return states
    .filter(s => s.entity_id.includes('team_tracker') || 
                 s.entity_id.includes('nhl_'))
    .map(parseSensorData);
}
```

### PATH B: Simple Custom Integration (If A Not Sufficient - 1 week)

**Why**: Need custom features not in existing integrations.

**Structure**:
```
custom_components/
└── homeiq_sports/
    ├── __init__.py (20 lines)
    ├── manifest.json (config only)
    ├── sensor.py (300 lines)
    └── README.md
```

**What to Extract from sports-data**:
- ESPN API client (~300 lines from sports_api_client.py)
- Game data parsing
- Team filtering logic

**Skip These**:
- Config flow (use configuration.yaml)
- Data coordinator (not needed)
- Separate platforms folder
- Event platform (optional)

**Installation**: Manual (copy files, restart HA)

### PATH C: Keep Sports Tab Simple (Fallback)

**Minimalist Approach**:
1. Delete sports-data service
2. Remove Sports tab from dashboard
3. User uses HA frontend for sports
4. HomeIQ focuses on core intelligence

## File Changes Summary

### PATH A (Recommended)
**Modified**:
- `services/health-dashboard/src/hooks/useSportsData.ts` - HA API integration
- `services/health-dashboard/src/api/haClient.ts` - Add sensor read methods
- `docker-compose.yml` - Remove sports-data service

**Deleted**:
- `services/sports-data/` - Entire directory

**New**:
- Nothing (use existing HACS integrations)

### PATH B (Custom Integration)
**Modified**: Same as PATH A
**Deleted**: Same as PATH A
**New**:
- `custom_components/homeiq_sports/` (4 files, ~500 lines total)
- Installation instructions in README

### PATH C (Minimalist)
**Modified**: Remove Sports tab references from dashboard
**Deleted**: 
- `services/sports-data/` 
- Sports tab component
**New**: Nothing

## Technical Requirements

### HA API Integration
- Use existing long-lived access token
- Read sensor states via `/api/states`
- Filter by entity ID pattern (`team_tracker*`, `nhl_*`)
- Parse sensor attributes to game data structure

### Dependencies
- Home Assistant REST API (already in use)
- HA spawning (for HA access)
- No new dependencies required

### Data Migration
- InfluxDB sports data remains (historical read-only)
- No data loss (sensors will provide fresh data)
- Sports events still accessible via HA API

## Testing (Practical)

### PATH A Testing
- Install Team Tracker in HA
- Verify sensors appear
- Check Dashboard reads sensors correctly
- **Time**: 30 minutes

### PATH B Testing  
- Create custom integration files
- Copy to HA custom_components/
- Restart HA, verify sensors
- **Time**: 2 hours

## Timeline

### PATH A (Use Existing)
- Day 1: Delete sports-data, update Dashboard (4 hours)
- Day 2: Test with Team Tracker (2 hours)
- **Total: 6 hours**

### PATH B (Custom Integration)
- Days 1-3: Extract ESPN API code, create HA integration (16 hours)
- Day 4: Test and document (4 hours)
- **Total: 20 hours**

### PATH C (Remove Tab)
- 1 hour: Delete service and tab
- **Total: 1 hour**

## Success Criteria

### Must Have
- [ ] Sports-data service removed
- [ ] Dashboard reads HA sensors (PATH A/B) OR tab removed (PATH C)
- [ ] No broken dependencies
- [ ] Architecture principle satisfied (HA = integration hub)

### Nice to Have
- [ ] Sports data still displayed in Dashboard
- [ ] User can install via HACS
- [ ] Historical InfluxDB data accessible

## Recommendation

**Use PATH A** - Leverage existing Team Tracker integration:
- Proven, battle-tested
- Minimal code changes
- User installs via HACS (standard workflow)
- Supports NFL, NHL, NBA, MLB
- Active maintenance by community

**Consider PATH B** only if:
- Team Tracker doesn't meet your needs
- You need very specific features
- You want full control

**Consider PATH C** if:
- Sports data is low priority
- You want to focus on core intelligence features
- Simplification is main goal

## Decision Required

Which path do you want to take?
1. PATH A (Use Team Tracker) - RECOMMENDED
2. PATH B (Custom Integration)
3. PATH C (Remove Sports Tab)

## References

- [Team Tracker HACS](https://github.com/vasquatch2/team_tracker) - Multi-sport integration
- [NHL HACS Integration](https://github.com/JayBlackedOut/hass-nhlapi) - NHL only
- [HA REST API Docs](https://developers.home-assistant.io/docs/api/rest/)
