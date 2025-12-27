# Story 12.4: Event Detector Team Integration ⚠️ CRITICAL BUG FIX

**Epic**: Epic 12 - Sports Data InfluxDB Persistence  
**Status**: 🔄 READY FOR IMPLEMENTATION  
**Priority**: CRITICAL  
**Estimated Effort**: 0.5 days  
**Created**: October 19, 2025

---

## Problem Statement

Event detector infrastructure exists but can't monitor games because:

- **Event Detector**: Calls `get_live_games()` with empty team lists
- **No Teams**: No teams = No games monitored = No score change detection
- **Webhook System**: Exists but can't trigger events
- **Result**: Users cannot trigger HA automations when teams score

## Acceptance Criteria

- [ ] Event detector monitors user's selected teams
- [ ] Score changes detected within 15 seconds
- [ ] Webhooks fired on score changes
- [ ] Game start/end events detected
- [ ] Event detection works with multiple teams
- [ ] Event detector logs show team monitoring activity
- [ ] Webhook delivery verified with test registrations

## Technical Implementation

### Current Problem
```python
# Event Detector (broken)
nfl_games = await self.sports_client.get_live_games('nfl', [])  # Empty list!
nhl_games = await self.sports_client.get_live_games('nhl', [])  # Empty list!

# Result: No games monitored, no events detected
```

### Fixed Implementation
```python
# Event Detector (fixed)
async def _get_user_teams(self):
    """Get user's selected teams from database"""
    # Query database for user's selected teams
    # Return team lists for monitoring

async def _check_for_events(self):
    """Check live games for state changes"""
    # Get user's selected teams
    user_teams = await self._get_user_teams()
    
    # Monitor NFL games with user's teams
    nfl_games = await self.sports_client.get_live_games('nfl', user_teams.nfl_teams)
    
    # Monitor NHL games with user's teams
    nhl_games = await self.sports_client.get_live_games('nhl', user_teams.nhl_teams)
    
    # Process games for events
    all_games = nfl_games + nhl_games
    # ... existing event detection logic
```

### Team Service Integration
```python
class GameEventDetector:
    def __init__(self, sports_client, webhook_manager, team_service):
        self.sports_client = sports_client
        self.webhooks = webhook_manager
        self.team_service = team_service  # New dependency
        
    async def _get_user_teams(self):
        """Get teams for monitoring"""
        return await self.team_service.get_user_teams("default")
```

## Implementation Steps

1. **Add team service dependency to event detector**
2. **Update event detector to fetch user teams**
3. **Pass team lists to get_live_games() calls**
4. **Add logging for team monitoring activity**
5. **Test event detection with live games**
6. **Verify score change detection works**
7. **Test webhook delivery on score changes**

## Files to Modify

- `services/sports-data/src/event_detector.py`
- `services/sports-data/src/main.py` (dependency injection)
- `services/sports-data/src/team_service.py` (new file)

## Testing

- [ ] Event detector logs show team monitoring
- [ ] Score changes detected within 15 seconds
- [ ] Webhooks fired on score changes
- [ ] Game start/end events detected
- [ ] Event detection works with multiple teams
- [ ] No "No teams selected" logs
- [ ] Webhook delivery verified

## Dependencies

- Epic 11 Story 11.5: Team Persistence Implementation (must complete first)
- Epic 11 Story 11.7: Event Detector Team Integration (related work)
- Existing webhook system
- Live games data (VGK game currently live)

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Event detector monitors user's selected teams
- [ ] Score change detection working
- [ ] Webhook delivery verified
- [ ] Manual testing with live games
- [ ] No regression in existing functionality
- [ ] Documentation updated
