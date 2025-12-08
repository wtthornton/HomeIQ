# Event Context Synergy Fix

**Date:** December 2025  
**Issue:** All event-based synergies displayed "Sports/Calendar Event" instead of specific event types  
**Status:** ✅ Fixed

## Problem Summary

All synergies on the Synergies page were showing "Sports/Calendar Event" as the event type, regardless of whether they were actually Sports events, Calendar events, or Holiday events.

## Root Cause

The `store_synergy_opportunities` function in `services/ai-automation-service/src/database/crud.py` was creating a new `metadata` dictionary that only included standard fields (`trigger_entity`, `trigger_name`, `action_entity`, `action_name`, `relationship`, `rationale`), completely overwriting the original `opportunity_metadata` that contained event-specific fields:

- `event_context`: 'Sports events', 'Calendar events', or 'Holiday events'
- `event_type`: 'sports', 'calendar', or 'holiday'
- `suggested_action`: The suggested action text

This caused the UI to fall back to the default "Sports/Calendar Event" text when `event_context` was missing.

## Solution

Updated the metadata merging logic in `store_synergy_opportunities` to:

1. **Preserve existing `opportunity_metadata`**: Start with the original `opportunity_metadata` from the synergy data
2. **Merge standard fields**: Overlay standard fields (`trigger_entity`, `trigger_name`, etc.) to ensure they're set
3. **Preserve event-specific fields**: Event-specific fields like `event_context`, `event_type`, and `suggested_action` are now preserved

### Code Changes

**File:** `services/ai-automation-service/src/database/crud.py`  
**Lines:** 1953-1970

**Before:**
```python
# Create metadata dict from synergy data
metadata = {
    'trigger_entity': synergy_data.get('trigger_entity'),
    'trigger_name': synergy_data.get('trigger_name'),
    'action_entity': synergy_data.get('action_entity'),
    'action_name': synergy_data.get('action_name'),
    'relationship': synergy_data.get('relationship'),
    'rationale': synergy_data.get('rationale')
}
```

**After:**
```python
# Create metadata dict from synergy data
# 2025 Enhancement: Preserve existing opportunity_metadata (e.g., event_context, event_type, suggested_action)
# and merge with standard fields to avoid losing event-specific data
existing_metadata = synergy_data.get('opportunity_metadata', {})
if not isinstance(existing_metadata, dict):
    existing_metadata = {}

# Build base metadata with standard fields (only non-None values)
base_metadata = {}
for key in ['trigger_entity', 'trigger_name', 'action_entity', 'action_name', 'relationship', 'rationale']:
    value = synergy_data.get(key)
    if value is not None:
        base_metadata[key] = value

# Merge: Start with existing_metadata (preserves event_context, event_type, suggested_action, etc.)
# Then overlay base_metadata to ensure standard fields are set
# This preserves event-specific fields while filling in standard fields
metadata = {**existing_metadata, **base_metadata}
```

## Expected Behavior

After this fix:

1. **Sports events** will display: "Sports events" (from `event_context: 'Sports events'`)
2. **Calendar events** will display: "Calendar events" (from `event_context: 'Calendar events'`)
3. **Holiday events** will display: "Holiday events" (from `event_context: 'Holiday events'`)

## Testing

To verify the fix:

1. Run daily analysis to detect event opportunities
2. Check the Synergies page - each event-based synergy should show its specific event type
3. Verify that `opportunity_metadata.event_context` is preserved in the database

## Related Files

- `services/ai-automation-service/src/database/crud.py` - Fixed metadata merging
- `services/ai-automation-service/src/contextual_patterns/event_opportunities.py` - Creates event opportunities with proper metadata
- `services/ai-automation-ui/src/pages/Synergies.tsx` - Displays event context (already correct)

## 2025 Patterns Used

- ✅ Modern Python dict merging with `{**dict1, **dict2}` syntax
- ✅ Type safety checks (`isinstance` validation)
- ✅ Clear comments explaining the merge strategy
- ✅ Preserves backward compatibility (fallback still works if metadata is missing)

