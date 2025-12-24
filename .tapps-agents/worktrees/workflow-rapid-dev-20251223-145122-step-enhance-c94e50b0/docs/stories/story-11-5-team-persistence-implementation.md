# Story 11.5: Team Persistence Implementation ⚠️ CRITICAL BUG FIX

**Epic**: Epic 11 - Sports Data Integration  
**Status**: 🔄 READY FOR IMPLEMENTATION  
**Priority**: CRITICAL  
**Estimated Effort**: 1 day  
**Created**: October 19, 2025

---

## Problem Statement

Team selections don't persist across service restarts, breaking the entire Sports API functionality:

- **POST `/api/v1/user/teams`**: Only logs teams, doesn't save them
- **GET `/api/v1/user/teams`**: Reads from environment variables, not user data
- **Event Detector**: Has no teams to monitor after restart
- **Result**: Users cannot trigger HA automations when teams score

## Acceptance Criteria

- [ ] Team selections persist across Docker restarts
- [ ] POST `/api/v1/user/teams` actually saves to database
- [ ] GET `/api/v1/user/teams` reads from database
- [ ] Event detector uses persisted team selections
- [ ] No data loss on service restart
- [ ] Team selection works with multiple users
- [ ] Database migration handles existing data

## Technical Implementation

### Database Schema
```sql
CREATE TABLE user_team_preferences (
    user_id VARCHAR(50) PRIMARY KEY,
    nfl_teams JSON NOT NULL DEFAULT '[]',
    nhl_teams JSON NOT NULL DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Changes
```python
# POST /api/v1/user/teams
async def save_user_selected_teams(teams: UserTeams):
    # Save to SQLite database
    # Update environment variables for backward compatibility
    # Return success confirmation

# GET /api/v1/user/teams  
async def get_user_selected_teams(user_id: str):
    # Read from SQLite database
    # Fallback to environment variables if not found
    # Return team preferences
```

### Event Detector Integration
```python
# Update event detector to fetch teams from database
async def _get_user_teams(self):
    # Query database for user's selected teams
    # Return team lists for monitoring
```

## Implementation Steps

1. **Add SQLite table for team preferences**
2. **Update POST endpoint to save to database**
3. **Update GET endpoint to read from database**
4. **Add database migration for existing data**
5. **Update event detector to use persisted teams**
6. **Test team persistence across restarts**
7. **Add error handling for database failures**

## Dependencies

- SQLite database (already available in sports-data service)
- Existing team selection API endpoints
- Event detector integration (Story 11.7)

## Testing

- [ ] Team selection persists across Docker restart
- [ ] Multiple users can have different team selections
- [ ] Database migration works with existing data
- [ ] Error handling works when database is unavailable
- [ ] Event detector monitors correct teams after restart

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests for database operations
- [ ] Integration tests for API endpoints
- [ ] Manual testing across service restarts
- [ ] Documentation updated
- [ ] No regression in existing functionality
