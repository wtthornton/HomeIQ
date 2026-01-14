# Team Tracker Platform Sync Notes

**Date**: January 16, 2026  
**Status**: Working (with limitation)  
**Issue**: Platform field sync limitation in HTTP discovery

## Current Status

### ✅ Platform Field IS Synced
- **Location**: `services/data-api/src/devices_endpoints.py:1339`
- **Code**: `platform=entity_data.get('platform', 'unknown')`
- **Result**: Platform field is stored in DeviceEntity table

### ⚠️ Platform Value Limitation

**Issue**: HTTP-based discovery uses domain instead of integration platform

**Location**: `services/websocket-ingestion/src/discovery_service.py:235`

```python
"platform": domain,  # Use domain as platform identifier
```

**Impact**:
- Team Tracker entities show `platform="sensor"` instead of `platform="teamtracker"`
- Detection still works via entity_id matching (fallback)
- WebSocket discovery method would provide correct platform from registry

### ✅ Detection Still Works

**Why**: Detection uses dual matching strategy:

1. **Primary**: Platform matching (line 185-188)
   - Checks for platform variations: "teamtracker", "team_tracker", etc.
   - Currently fails because platform="sensor"

2. **Fallback**: Entity ID matching (line 196-201)
   - Checks entity_id patterns: "team_tracker", "teamtracker", etc.
   - This works correctly: `sensor.dal_team_tracker`, `sensor.vgk_team_tracker`

**Evidence**: Diagnostic script shows 2 entities detected correctly via entity_id matching

## Recommended Fix (Future Enhancement)

**Option 1**: Use WebSocket discovery for platform value
- WebSocket entity registry (`config/entity_registry/list`) returns correct platform
- Current code already has WebSocket fallback method

**Option 2**: Enhance HTTP discovery to fetch entity registry
- Use `/api/config/entity_registry/list` endpoint (if available)
- Map platform from registry data

**Option 3**: Accept current behavior
- Detection works via entity_id fallback
- Platform value limitation is non-critical
- No user-facing impact

## Current Behavior

- ✅ Entities are synced to database
- ✅ Platform field is stored
- ⚠️ Platform value is domain (sensor) not integration (teamtracker)
- ✅ Detection works via entity_id matching
- ✅ Team Tracker integration status shows correctly
- ✅ Teams are detected and stored

## Conclusion

Platform sync is **working correctly** for Team Tracker detection, despite the platform value limitation. The entity_id fallback strategy ensures detection works regardless of platform value. This is a non-critical enhancement opportunity, not a blocking issue.
