# Ask AI Test Endpoint 404 Investigation

**Date:** December 2024  
**Status:** ✅ RESOLVED - Issue was incorrect port number  
**Test:** `tests/integration/test_ask_ai_specific_ids.py`

---

## Problem Summary

The test was getting a 404 Not Found error when calling the API endpoint with specific query and suggestion IDs that were known to exist in the database.

---

## Root Cause Analysis

### Issue #1: Wrong Port Number (PRIMARY ISSUE)

**Problem:** Test was calling `http://localhost:8018` but Docker maps the service to port **8024** externally.

**Evidence:**
- `docker-compose.yml` line 885: `ports: - "8024:8018"`
- Service listens on 8018 internally, but external access is on 8024

**Fix:** Updated test to use port 8024:
```python
BASE_URL = "http://localhost:8024/api/v1/ask-ai"
```

### Issue #2: Incorrect Assertion Logic

**Problem:** Test assertion was checking for `valid` field, but successful responses have `executed` instead.

**Actual Response Structure:**
```json
{
  "suggestion_id": "ask-ai-a2ee3f3c",
  "query_id": "query-5849c3e4",
  "executed": true,
  "automation_id": "automation.office_party_lights",
  "automation_yaml": "...",
  "deleted": true,
  "message": "✅ Test completed successfully...",
  "quality_report": {...}
}
```

**Fix:** Updated assertion to check for `executed` or `automation_id` instead of `valid`.

---

## Test Results After Fix

✅ **API Endpoint:** Working correctly  
✅ **Query Found:** `query-5849c3e4` exists in database  
✅ **Suggestion Found:** `ask-ai-a2ee3f3c` exists in query's suggestions  
✅ **Test Execution:** Automation created and executed successfully  
✅ **Response:** 200 OK with full execution details

---

## Key Findings

1. **Database Access:** Query and suggestion IDs were correctly found in SQLite database at `/app/data/ai_automation.db`

2. **API Functionality:** The test endpoint works as expected:
   - Fetches query from database ✓
   - Finds suggestion in query's suggestions array ✓
   - Generates YAML ✓
   - Creates automation in Home Assistant ✓
   - Executes automation ✓
   - Deletes automation after test ✓

3. **Response Format:** Successful responses include:
   - `executed: true` (not `valid`)
   - `automation_id`
   - `automation_yaml`
   - `quality_report` with detailed checks
   - `deleted: true` (automation cleaned up)

---

## Lessons Learned

1. **Always check Docker port mappings** - Services may be exposed on different ports externally
2. **Verify response schema** - Don't assume field names without checking actual API responses
3. **Test with actual data** - The IDs from the GUI test were correct and worked once the port was fixed

---

## Test Status

**Before Fix:**
- Port 8018 → 404 Not Found
- Assertion checking wrong fields

**After Fix:**
- Port 8024 → 200 OK ✅
- Correct assertion logic ✅
- Test passes successfully ✅

