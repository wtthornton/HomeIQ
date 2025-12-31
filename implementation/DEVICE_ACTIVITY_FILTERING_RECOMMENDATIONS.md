# Device Activity Filtering Recommendations

**Date:** 2025-12-31  
**Status:** Research Complete, Recommendations Ready

## Executive Summary

Based on research of Home Assistant best practices and 2025 smart home industry standards, this document provides recommendations for filtering inactive devices from pattern and synergy displays while preserving historical data.

**Key Finding:** Devices that were active when patterns were created may now be inactive (turned off, removed, or seasonal). We should filter display by device activity while preserving patterns for historical reference.

---

## Research Findings

### Home Assistant Best Practices (Context7)

1. **Device State Tracking:**
   - Home Assistant tracks `last_changed` and `last_seen` timestamps
   - Devices can be marked as `disabled_by` or `entry_type`
   - State triggers can detect inactivity (e.g., "not changed for 30 minutes")

2. **Device Lifecycle:**
   - Devices may be temporarily offline
   - Devices may be removed from system
   - Devices may be seasonal (irrigation, fans, holiday lights)

3. **Filtering Recommendations:**
   - Filter disabled devices from automations
   - Check `last_changed` for device activity
   - Consider device type when determining inactivity

### Industry Standards (2025 Research)

1. **Smart Home Device Activity:**
   - Average U.S. household: 21 connected devices
   - 45% of U.S. internet households own smart devices
   - Devices may be inactive due to:
     - Seasonal usage (irrigation, fans, holiday lights)
     - Maintenance or repairs
     - User preferences (turned off)
     - Technical issues (offline)

2. **Activity Time Windows:**
   - **Daily/Weekly Devices:** 7 days (lights, switches, locks, media players)
   - **Monthly Devices:** 30 days (climate, covers, some sensors)
   - **Seasonal Devices:** 90 days (irrigation, fans, outdoor devices)
   - **Historical Reference:** 365 days (archived patterns)

---

## Recommended Activity Time Windows

### Standard Windows (2025 Best Practices)

| Window | Days | Use Case | Examples |
|--------|------|----------|----------|
| **Recent** | 7 | Daily/weekly devices | Lights, switches, locks, media players, motion sensors |
| **Active** | 30 | Monthly devices | Climate, covers, fans, most sensors |
| **Seasonal** | 90 | Seasonal devices | Irrigation, outdoor devices, holiday lights |
| **Historical** | 365 | Archive reference | All devices (for historical analysis) |

### Domain-Specific Windows

Based on device usage patterns:

| Domain | Window | Rationale |
|--------|--------|-----------|
| `light` | 7 days | Used daily/weekly |
| `switch` | 7 days | Used daily/weekly |
| `lock` | 7 days | Used daily |
| `media_player` | 7 days | Used daily/weekly |
| `binary_sensor` | 7 days | Motion sensors used daily |
| `climate` | 30 days | Thermostats used monthly |
| `cover` | 30 days | Blinds adjusted monthly |
| `fan` | 30 days | Seasonal usage |
| `vacuum` | 7 days | Weekly cleaning |
| `irrigation` | 90 days | Seasonal (spring/summer) |
| `sensor` | 30 days | Many are passive, some active |

---

## Implementation Recommendations

### 1. Filter Patterns by Device Activity ✅ RECOMMENDED

**Approach:** Filter patterns for display based on device activity, but preserve all patterns in database.

**Implementation:**
```python
# In pattern_router.py or UI
active_devices = await get_active_devices(window_days=30)
patterns = await get_all_patterns()
filtered_patterns = [p for p in patterns if is_device_active(p.device_id, active_devices)]
```

**Benefits:**
- Users only see relevant patterns
- Historical patterns preserved for analysis
- Reduces confusion from inactive devices

**Time Window:** 30 days (default), configurable per domain

---

### 2. Filter Synergies by Device Activity ✅ RECOMMENDED

**Approach:** Filter synergies to only show those involving active devices.

**Implementation:**
```python
# In synergy_router.py or UI
active_devices = await get_active_devices(window_days=30)
synergies = await get_all_synergies()
filtered_synergies = [
    s for s in synergies 
    if any(d in active_devices for d in s.device_ids)
]
```

**Benefits:**
- Only actionable synergies shown
- Reduces clutter from inactive devices
- Better user experience

**Time Window:** 30 days (default), configurable

---

### 3. Add Activity Status to Patterns/Synergies ✅ RECOMMENDED

**Approach:** Add `is_active` flag to pattern/synergy responses.

**Implementation:**
```python
# Add to pattern/synergy response
{
    "id": "...",
    "device_id": "light.kitchen",
    "is_active": True,  # Device active in last 30 days
    "last_activity": "2025-12-28T10:30:00Z",
    ...
}
```

**Benefits:**
- UI can show/hide inactive items
- Users can toggle "Show inactive"
- Clear indication of device status

---

### 4. Domain-Specific Activity Windows ✅ RECOMMENDED

**Approach:** Use different time windows based on device domain.

**Implementation:**
```python
def get_activity_window(domain: str) -> int:
    """Get activity window for domain."""
    return DOMAIN_ACTIVITY_WINDOWS.get(domain, 30)  # Default: 30 days
```

**Benefits:**
- More accurate filtering
- Accounts for seasonal devices
- Better user experience

---

### 5. Archive vs. Hide Strategy ✅ RECOMMENDED

**Approach:** Don't delete inactive patterns, but archive/hide them.

**Implementation:**
- Add `is_active` flag to patterns table
- Update flag during analysis
- UI filters by `is_active=True` by default
- Allow users to "Show archived" if needed

**Benefits:**
- Preserves historical data
- Allows reactivation if device comes back
- Better data integrity

---

## Code Changes Required

### 1. Add Activity Filtering to Pattern API

**File:** `services/ai-pattern-service/src/api/pattern_router.py`

**Changes:**
```python
@router.get("/list")
async def list_patterns(
    include_inactive: bool = Query(default=False),
    activity_window_days: int = Query(default=30, ge=1, le=365),
    ...
):
    """List patterns, optionally filtering by device activity."""
    patterns = await get_all_patterns(...)
    
    if not include_inactive:
        active_devices = await get_active_devices(activity_window_days)
        patterns = filter_patterns_by_activity(patterns, active_devices)
    
    return patterns
```

---

### 2. Add Activity Filtering to Synergy API

**File:** `services/ai-pattern-service/src/api/synergy_router.py`

**Changes:**
```python
@router.get("/list")
async def list_synergies(
    include_inactive: bool = Query(default=False),
    activity_window_days: int = Query(default=30, ge=1, le=365),
    ...
):
    """List synergies, optionally filtering by device activity."""
    synergies = await get_synergy_opportunities(...)
    
    if not include_inactive:
        active_devices = await get_active_devices(activity_window_days)
        synergies = filter_synergies_by_activity(synergies, active_devices)
    
    return synergies
```

---

### 3. Add Activity Tracking to Pattern Analysis

**File:** `services/ai-pattern-service/src/scheduler/pattern_analysis.py`

**Changes:**
```python
async def _store_results(...):
    # After storing patterns, mark activity status
    active_devices = await self._get_active_devices(window_days=30)
    await self._update_pattern_activity_status(db, all_patterns, active_devices)
```

---

### 4. Create Activity Service

**File:** `services/ai-pattern-service/src/services/device_activity.py` (new)

**Purpose:** Centralized device activity tracking and filtering

**Functions:**
- `get_active_devices(window_days: int) -> Set[str]`
- `is_device_active(device_id: str, window_days: int) -> bool`
- `get_domain_activity_window(domain: str) -> int`
- `filter_patterns_by_activity(patterns, active_devices) -> List[Dict]`
- `filter_synergies_by_activity(synergies, active_devices) -> List[Dict]`

---

## UI/UX Recommendations

### 1. Default View: Active Devices Only

**Recommendation:** Show only active devices by default

**Rationale:**
- Users want to see actionable patterns/synergies
- Reduces clutter
- Better user experience

---

### 2. Toggle for Inactive Devices

**Recommendation:** Add "Show Inactive" toggle

**Implementation:**
```tsx
<Checkbox
  label="Show inactive devices"
  checked={showInactive}
  onChange={setShowInactive}
/>
```

**Benefits:**
- Users can view historical patterns if needed
- Flexibility for power users
- Clear indication of what's shown

---

### 3. Visual Indicators

**Recommendation:** Show activity status visually

**Implementation:**
- Green dot: Active (last 7 days)
- Yellow dot: Recently active (7-30 days)
- Gray dot: Inactive (>30 days)
- Tooltip: "Last active: 15 days ago"

---

### 4. Activity Filter Options

**Recommendation:** Allow users to select activity window

**Options:**
- "Last 7 days" (Recent)
- "Last 30 days" (Active) - Default
- "Last 90 days" (Seasonal)
- "All time" (Historical)

---

## Database Schema Changes

### Option 1: Add Activity Flags (Recommended)

**Add to `patterns` table:**
```sql
ALTER TABLE patterns ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE patterns ADD COLUMN last_activity_check DATETIME;
```

**Add to `synergy_opportunities` table:**
```sql
ALTER TABLE synergy_opportunities ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE synergy_opportunities ADD COLUMN last_activity_check DATETIME;
```

**Benefits:**
- Fast filtering (indexed boolean)
- Can update during analysis
- No need to query events every time

---

### Option 2: Query Events On-Demand (Simpler)

**Approach:** Query events when needed, don't store flags

**Benefits:**
- No schema changes
- Always up-to-date
- Simpler implementation

**Drawbacks:**
- Slower (queries events each time)
- More API calls

**Recommendation:** Use Option 1 for performance, Option 2 for simplicity

---

## Implementation Priority

### Phase 1: Quick Win (1-2 days)

1. ✅ Create `scripts/filter_inactive_devices.py` (done)
2. Add `include_inactive` parameter to API endpoints
3. Filter in API layer (query events on-demand)
4. Add UI toggle for "Show inactive"

**Impact:** Immediate improvement in user experience

---

### Phase 2: Performance Optimization (1 week)

1. Add `is_active` flags to database
2. Update flags during pattern analysis
3. Use flags for fast filtering
4. Add domain-specific windows

**Impact:** Better performance, more accurate filtering

---

### Phase 3: Advanced Features (2-3 weeks)

1. Activity status indicators in UI
2. Activity window selector
3. Activity analytics dashboard
4. Automatic pattern archiving

**Impact:** Enhanced user experience, better insights

---

## Best Practices Summary

### ✅ DO

1. **Filter by Activity:** Show only active devices by default
2. **Preserve History:** Don't delete inactive patterns
3. **Domain-Specific Windows:** Use appropriate windows per domain
4. **User Control:** Allow users to show inactive if needed
5. **Visual Indicators:** Show activity status clearly

### ❌ DON'T

1. **Delete Inactive Patterns:** Preserve for historical analysis
2. **One-Size-Fits-All:** Use same window for all domains
3. **Hard-Code Windows:** Make configurable
4. **Ignore Seasonal Devices:** Use longer windows for seasonal
5. **Forget User Control:** Always allow viewing inactive

---

## Time Window Recommendations

### Default: 30 Days

**Rationale:**
- Balances recent activity with seasonal devices
- Industry standard for "active" devices
- Catches monthly usage patterns

### Per-Domain Windows

**Daily/Weekly (7 days):**
- `light`, `switch`, `lock`, `media_player`, `binary_sensor`, `vacuum`

**Monthly (30 days):**
- `climate`, `cover`, `fan`, `sensor` (most)

**Seasonal (90 days):**
- `irrigation`, outdoor devices, holiday lights

**Historical (365 days):**
- Archive/reference only
- Not for active filtering

---

## Example Implementation

### API Endpoint Enhancement

```python
@router.get("/patterns/list")
async def list_patterns(
    include_inactive: bool = Query(default=False, description="Include inactive device patterns"),
    activity_window: int = Query(default=30, ge=1, le=365, description="Activity window in days"),
    db: AsyncSession = Depends(get_db)
):
    """List patterns, optionally filtered by device activity."""
    patterns = await get_all_patterns(db)
    
    if not include_inactive:
        # Get active devices from events
        active_devices = await get_active_devices_from_events(activity_window)
        
        # Filter patterns
        patterns = [
            p for p in patterns
            if is_pattern_device_active(p, active_devices)
        ]
    
    return {"patterns": patterns, "count": len(patterns)}
```

---

## Testing Recommendations

### Test Scenarios

1. **Active Device Patterns:**
   - Device active in last 7 days → Should show
   - Device active in last 30 days → Should show (default)
   - Device active 31 days ago → Should hide (default)

2. **Seasonal Devices:**
   - Irrigation active 60 days ago → Should show (90-day window)
   - Fan active 100 days ago → Should hide (30-day window)

3. **Co-Occurrence Patterns:**
   - Both devices active → Should show
   - One device active → Should show (partial match)
   - Neither active → Should hide

4. **UI Toggle:**
   - `include_inactive=False` → Only active
   - `include_inactive=True` → All patterns

---

## Success Metrics

### Immediate (After Phase 1)

- ✅ Users see only active device patterns
- ✅ Inactive patterns hidden by default
- ✅ Toggle works for showing inactive

### Short-Term (After Phase 2)

- ✅ Fast filtering (using database flags)
- ✅ Domain-specific windows working
- ✅ Activity status visible in UI

### Long-Term (After Phase 3)

- ✅ Activity analytics available
- ✅ Automatic archiving working
- ✅ User satisfaction improved

---

## Conclusion

**Recommendation:** Implement device activity filtering with:

1. **Default:** 30-day activity window
2. **Domain-Specific:** Per-domain windows (7/30/90 days)
3. **Preserve History:** Don't delete, just filter display
4. **User Control:** Toggle for inactive devices
5. **Visual Indicators:** Show activity status

**Implementation:** Start with Phase 1 (API filtering), then Phase 2 (database flags), then Phase 3 (advanced features).

**Expected Impact:**
- Better user experience (only relevant patterns shown)
- Reduced confusion (no inactive device patterns)
- Preserved history (all patterns kept for analysis)
- Improved accuracy (domain-specific windows)

---

## Files Created

1. **`scripts/filter_inactive_devices.py`** - Device activity filtering tool
2. **`implementation/DEVICE_ACTIVITY_FILTERING_RECOMMENDATIONS.md`** - This document

## Next Steps

1. Review recommendations
2. Implement Phase 1 (API filtering)
3. Test with real data
4. Gather user feedback
5. Iterate based on feedback
