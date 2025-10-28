# Historical Totals Bug Investigation

**Date:** January 27, 2025  
**Issue:** Total Events on dashboard only shows session count, not database total

## Problem Identified

User correctly noticed that "Total Events" on the dashboard should include:
- **Historical events** in the InfluxDB database (all time)
- **Current session events** since service restart

Currently, it only shows session events (~145), not the full database total.

## Root Cause

The `HistoricalEventCounter` service is failing to parse InfluxDB query results with error:
```
Error parsing count result: '_field'
Error parsing grouped count result: '_field'
```

This causes historical totals to default to 0, so the dashboard only displays current session events.

## Fix Attempts Made

### Attempt 1: Fix event_type parsing
- **File:** `services/websocket-ingestion/src/historical_event_counter.py`
- **Change:** Fixed event_type extraction in grouped queries
- **Result:** ❌ Same error persisted

### Attempt 2: Improve error handling
- **File:** `services/websocket-ingestion/src/historical_event_counter.py`
- **Changes:** 
  - Simplified `get_value()` calls
  - Added try-catch around individual record parsing
  - Changed to debug level logging for errors
- **Result:** ❌ Still seeing '_field' error

### Attempt 3: Add detailed debugging
- **File:** `services/websocket-ingestion/src/historical_event_counter.py`
- **Changes:**
  - Added logging for table/record counts
  - Added exception chaining (`exc_info=True`)
- **Result:** 🔄 In progress

## Current State

- **Code updated:** Yes (multiple attempts)
- **Service rebuilt:** Yes
- **Service restarted:** Yes
- **Historical totals loading:** ❌ Still failing (returning 0)
- **Dashboard showing:** Only session events

## Investigation Needed

The error `'_field'` is unusual - it suggests:
1. Exception is being raised with just the string `'_field'`
2. OR there's a mismatch in how InfluxDB records are accessed
3. OR the query result structure is different than expected

## Next Steps

1. **Enable DEBUG logging** and restart to see full stack trace
2. **Test InfluxDB query directly** to verify result structure
3. **Check InfluxDB client version** compatibility
4. **Consider alternative approach**:
   - Use simpler count query
   - Query for last event timestamp instead
   - Calculate total differently

## Alternative Solution

If fixing the parser proves too complex, consider:
1. **Show separate metrics**: 
   - "Events Today" (session + some historical)
   - "All Time Total" (from different calculation)
2. **Use InfluxDB monitoring** to get total event count from database stats
3. **Periodic total update**: Store running total separately, update every hour

## Files Modified

- `services/websocket-ingestion/src/historical_event_counter.py` (lines 114-172)

## Status

**Current:** Investigation in progress  
**Priority:** Medium (dashboard still functions, just shows incomplete data)  
**Impact:** User confusion about actual total events in system

