# Synergy Type Analysis - Only event_context Found

## Problem Summary

The dashboard shows only **1 synergy type** (`event_context`), but the code should be detecting:
- `device_pair` (2-device synergies)
- `device_chain` (3+ device chains)
- `event_context` (sports/calendar/holiday scenes)

## Current State

**Database Analysis:**
- Total synergies: 48
- All synergies have `synergy_type: 'event_context'`
- All synergies have `synergy_depth: 2`
- Relationships: `sports_event_scene`, `calendar_event_scene`, `holiday_scene`
- **Zero** `device_pair` or `device_chain` synergies

**Sample Synergies:**
- All are single-device media players
- All triggered by events (sports, calendar, holidays)
- No device-to-device relationships

## Root Cause Analysis

### Issue 1: Method Signature Mismatch

In `pattern_analysis.py` line 301-305:
```python
synergy_detector = DeviceSynergyDetector()
synergies = await synergy_detector.detect_synergies(
    events_df=events_df,
    devices=devices,
    entities=entities
)
```

But `DeviceSynergyDetector.detect_synergies()` (line 439) has signature:
```python
async def detect_synergies(self) -> list[dict[str, Any]]:
```

**Problem:** The method doesn't accept `events_df`, `devices`, or `entities` parameters. It calls `_fetch_device_data()` internally, which may not be working correctly.

### Issue 2: event_context Synergies Source

The `event_context` synergies are being created from archived code (`event_opportunities.py`), but there's no current code path creating them. This suggests:
1. Old synergies are still in the database
2. A different service/endpoint is creating them
3. They're being created by a different code path

### Issue 3: Device Pair Detection Not Running

The `DeviceSynergyDetector` should:
1. Find compatible device pairs
2. Filter by existing automations
3. Rank and score synergies
4. Detect chains (3+ devices)

But none of these are producing results.

## Recommendations

### 1. Fix Method Signature

**File:** `services/ai-pattern-service/src/synergy_detection/synergy_detector.py`

**Change:** Update `detect_synergies()` to accept parameters:
```python
async def detect_synergies(
    self,
    events_df: pd.DataFrame | None = None,
    devices: list[dict] | None = None,
    entities: list[dict] | None = None
) -> list[dict[str, Any]]:
    """
    Detect all synergy opportunities.
    
    Args:
        events_df: Optional DataFrame with events (if None, will fetch)
        devices: Optional device list (if None, will fetch)
        entities: Optional entity list (if None, will fetch)
    
    Returns:
        List of synergy opportunity dictionaries
    """
    # Use provided data or fetch
    if devices is None or entities is None:
        devices, entities = await self._fetch_device_data()
    
    # ... rest of method
```

### 2. Verify Device Pair Detection Logic

**Check:**
- `_detect_compatible_pairs_pipeline()` is finding pairs
- `_filter_existing_automations()` isn't filtering everything
- `_rank_and_filter_synergies()` isn't too restrictive
- Confidence thresholds aren't too high

### 3. Add Logging

Add detailed logging to track:
- How many device pairs are found
- How many pass compatibility filters
- How many pass automation filters
- How many pass confidence thresholds
- Final counts by type

### 4. Test Detection Manually

Create a test script that:
1. Fetches devices and entities
2. Fetches recent events
3. Calls `detect_synergies()` directly
4. Reports what types are detected

### 5. Check for event_context Creation

Find where `event_context` synergies are being created:
- Search for `sports_event_scene`, `calendar_event_scene`, `holiday_scene`
- Check if a different service/endpoint creates them
- Verify if they should be disabled or if device pairs should be added

## Next Steps

1. **Fix method signature** - Make `detect_synergies()` accept parameters
2. **Add diagnostic logging** - Track detection pipeline stages
3. **Test detection** - Run detection manually and verify output
4. **Review filters** - Check if filters are too restrictive
5. **Re-run analysis** - After fixes, trigger "Run Analysis" and verify types

## Files to Review

- `services/ai-pattern-service/src/synergy_detection/synergy_detector.py` - Main detector
- `services/ai-pattern-service/src/scheduler/pattern_analysis.py` - Scheduler that calls detector
- `services/ai-pattern-service/src/crud/synergies.py` - Storage logic
- `scripts/diagnose_synergy_types.py` - Diagnostic script (created)

## Created Diagnostic Scripts

1. `scripts/diagnose_synergy_types.py` - Database analysis
2. `scripts/evaluate_synergy_detection.py` - Detection evaluation (import issues)
3. `scripts/diagnose_synergy_detection_issue.py` - API-based diagnosis
