# Team Tracker Integration - Fix Plan

**Date:** January 2025  
**Status:** Planning  
**Issue:** Team Tracker detection failing with "Failed to detect Team Tracker entities" error

## Problem Summary

From the UI screenshot and code review, the following issues have been identified:

1. **Detection Failure**: "Detect Teams" button shows error: "Failed to detect Team Tracker entities"
2. **Status Display**: Shows "Not Installed" with 0 teams configured
3. **No Error Details**: Frontend shows generic error without actual failure reason

## Root Cause Analysis

### Issue 1: Platform Value Mismatch
**Location:** `services/device-intelligence-service/src/api/team_tracker_router.py:150`

The detection query searches for:
```python
select(DeviceEntity).where(DeviceEntity.platform == "teamtracker")
```

**Potential Problems:**
- Home Assistant might store platform as `"team_tracker"` (with underscore) instead of `"teamtracker"`
- Platform value might be case-sensitive
- Platform might be stored differently in the database

### Issue 2: Missing Error Handling
**Location:** `services/device-intelligence-service/src/api/team_tracker_router.py:136-213`

The `/detect` endpoint has no try/except blocks:
- Database errors will cause 500 responses
- No logging of actual error details
- Frontend receives generic error message

### Issue 3: Limited Detection Strategy
Current detection only checks:
- `platform == "teamtracker"` (exact match)

**Missing:**
- Fallback detection by entity_id pattern (`sensor.team_tracker_*`)
- Case-insensitive platform matching
- Alternative platform value variations

### Issue 4: Frontend Error Handling
**Location:** `services/ai-automation-ui/src/components/TeamTrackerSettings.tsx:214`

Frontend error handler:
```typescript
onError: () => toast.error('❌ Failed to detect Team Tracker entities')
```

**Problems:**
- No error message details shown to user
- No error logging for debugging
- Generic message doesn't help diagnose issue

## Fix Plan

### Phase 1: Enhanced Detection Logic

#### 1.1 Add Multiple Detection Strategies
**File:** `services/device-intelligence-service/src/api/team_tracker_router.py`

**Changes:**
1. Try multiple platform value variations:
   - `"teamtracker"` (current)
   - `"team_tracker"` (with underscore)
   - Case-insensitive matching
   
2. Add fallback detection by entity_id pattern:
   - Match entities where `entity_id LIKE 'sensor.team_tracker_%'`
   - Match entities where `entity_id LIKE 'sensor.teamtracker_%'`

3. Add domain check:
   - Ensure `domain == "sensor"` for Team Tracker entities

**Implementation:**
```python
from sqlalchemy import or_, func

# Try multiple platform variations
platform_variations = ["teamtracker", "team_tracker", "TeamTracker", "TEAMTRACKER"]

# Build query with multiple conditions
conditions = [
    DeviceEntity.platform.in_(platform_variations),
    DeviceEntity.domain == "sensor"
]

# Add entity_id pattern matching as fallback
entity_patterns = [
    DeviceEntity.entity_id.like("sensor.team_tracker_%"),
    DeviceEntity.entity_id.like("sensor.teamtracker_%")
]

query = select(DeviceEntity).where(
    or_(
        *conditions,
        *entity_patterns
    )
)
```

#### 1.2 Add Debug Logging
Log all detected entities and their platform values for troubleshooting:
```python
logger.info(f"Searching for Team Tracker entities with platform variations: {platform_variations}")
logger.debug(f"Found {len(team_sensors)} entities matching Team Tracker criteria")
for sensor in team_sensors:
    logger.debug(f"Team Tracker entity: {sensor.entity_id}, platform: {sensor.platform}, domain: {sensor.domain}")
```

### Phase 2: Error Handling

#### 2.1 Add Try/Except to Detect Endpoint
**File:** `services/device-intelligence-service/src/api/team_tracker_router.py`

**Changes:**
```python
@router.post("/detect")
async def detect_team_tracker_entities(
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """
    Detect Team Tracker sensor entities from Home Assistant.
    """
    try:
        logger.info("🔍 Detecting Team Tracker entities")
        
        # ... detection logic ...
        
        return {
            "detected_count": len(team_sensors),
            "detected_teams": detected_teams,
            "integration_status": integration.installation_status
        }
    except Exception as e:
        logger.error(f"❌ Error detecting Team Tracker entities: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detect Team Tracker entities: {str(e)}"
        )
```

#### 2.2 Add Database Query Debugging
Add a diagnostic endpoint to check what platform values actually exist:
```python
@router.get("/debug/platforms")
async def debug_platform_values(
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """Debug endpoint to see what platform values exist for sensor entities."""
    from sqlalchemy import func
    
    # Get all unique platform values for sensor entities
    result = await session.execute(
        select(DeviceEntity.platform, func.count(DeviceEntity.entity_id))
        .where(DeviceEntity.domain == "sensor")
        .group_by(DeviceEntity.platform)
    )
    
    platforms = {row[0]: row[1] for row in result.all()}
    
    # Check for team tracker-like entities
    team_like = await session.execute(
        select(DeviceEntity)
        .where(
            or_(
                DeviceEntity.entity_id.like("%team%tracker%"),
                DeviceEntity.platform.ilike("%team%tracker%")
            )
        )
    )
    
    return {
        "sensor_platforms": platforms,
        "team_tracker_like_entities": [
            {
                "entity_id": e.entity_id,
                "platform": e.platform,
                "name": e.name
            }
            for e in team_like.scalars().all()
        ]
    }
```

### Phase 3: Frontend Improvements

#### 3.1 Enhanced Error Messages
**File:** `services/ai-automation-ui/src/components/TeamTrackerSettings.tsx`

**Changes:**
```typescript
const detectMutation = useMutation({
  mutationFn: detectTeams,
  onSuccess: (data) => {
    queryClient.invalidateQueries({ queryKey: ['teamTrackerStatus'] });
    queryClient.invalidateQueries({ queryKey: ['teamTrackerTeams'] });
    const count = data.detected_count || 0;
    if (count > 0) {
      toast.success(`✅ Detected ${count} Team Tracker entities!`);
    } else {
      toast.warning('⚠️ No Team Tracker entities found. Make sure Team Tracker is installed in Home Assistant.');
    }
  },
  onError: (error: Error) => {
    const errorMessage = error instanceof Error 
      ? error.message 
      : 'Failed to detect Team Tracker entities';
    console.error('Team Tracker detection error:', error);
    toast.error(`❌ ${errorMessage}`);
  },
});
```

#### 3.2 Add Loading States
Show loading indicator during detection:
```typescript
{detectMutation.isPending && (
  <div className="text-sm text-gray-500">
    Scanning for Team Tracker entities...
  </div>
)}
```

### Phase 4: Testing & Validation

#### 4.1 Test Cases
1. **No Team Tracker Installed:**
   - Should return 0 detected entities
   - Should show "Not Installed" status
   - Should not throw error

2. **Team Tracker Installed:**
   - Should detect entities with various platform values
   - Should create team entries in database
   - Should update integration status

3. **Error Scenarios:**
   - Database connection errors
   - Invalid platform values
   - Missing entity data

#### 4.2 Manual Testing Steps
1. Check actual platform values in database:
   ```sql
   SELECT DISTINCT platform FROM device_entities WHERE domain = 'sensor';
   SELECT entity_id, platform, name FROM device_entities WHERE entity_id LIKE '%team%tracker%';
   ```

2. Test detection endpoint:
   ```bash
   curl -X POST http://localhost:8028/api/team-tracker/detect \
     -H "Authorization: Bearer $API_KEY"
   ```

3. Test debug endpoint:
   ```bash
   curl http://localhost:8028/api/team-tracker/debug/platforms \
     -H "Authorization: Bearer $API_KEY"
   ```

## Implementation Order

1. ✅ **Phase 1.1**: Enhanced detection logic with multiple strategies
2. ✅ **Phase 1.2**: Add debug logging
3. ✅ **Phase 2.1**: Add error handling to detect endpoint
4. ✅ **Phase 2.2**: Add debug endpoint for platform values
5. ✅ **Phase 3.1**: Improve frontend error messages
6. ✅ **Phase 3.2**: Add loading states
7. ✅ **Phase 4**: Testing and validation

## Success Criteria

- [ ] Detection works with various platform value formats
- [ ] Error messages provide actionable information
- [ ] No 500 errors on detection endpoint
- [ ] Debug endpoint helps identify platform value issues
- [ ] Frontend shows clear status and error messages
- [ ] Team Tracker entities are successfully detected and stored

## Notes

- The actual platform value used by Home Assistant Team Tracker integration may vary
- Need to verify actual database values before finalizing platform matching logic
- Consider adding a configuration option for custom platform values if needed

