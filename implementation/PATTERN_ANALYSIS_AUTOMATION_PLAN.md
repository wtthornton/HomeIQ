# Pattern Analysis Re-run Automation Plan

**Date:** January 16, 2026  
**Status:** 🚀 **READY TO EXECUTE**

---

## Executive Summary

Automated script to re-run pattern analysis and validate synergy detection fix using hybrid API + Playwright approach.

---

## Approach: Hybrid API + Playwright

### Strategy

1. **API for Execution** (Reliable)
   - Trigger analysis via API endpoint
   - Poll status via API endpoint
   - Get results via API endpoint

2. **Playwright for UI Validation** (User Experience)
   - Navigate to UI
   - Verify results displayed correctly
   - Test user experience end-to-end

---

## Execution Steps

### Phase 1: Trigger Analysis (API)

1. **Check Service Health**
   - Verify ai-pattern-service is running
   - Check health endpoint: `GET http://localhost:8034/health`

2. **Trigger Analysis**
   - Call: `POST http://localhost:8034/api/analysis/trigger`
   - Verify response: `{"success": true, "status": "running"}`

3. **Wait for Completion** (API Polling)
   - Poll: `GET http://localhost:8034/api/analysis/status`
   - Check status: `"ready"` or `"error"`
   - Timeout: 15 minutes (60 attempts × 15 seconds)
   - Expected duration: 5-15 minutes

### Phase 2: Validate Results (API)

4. **Get Synergy Stats**
   - Call: `GET http://localhost:8034/api/v1/synergies/stats`
   - Verify multiple synergy types exist:
     - `device_pair` count > 0 ✅
     - `device_chain` count > 0 ✅
     - `event_context` count ≥ 0 ✅

5. **Check Pattern Count**
   - Verify pattern count maintained or increased
   - No significant decrease

### Phase 3: UI Validation (Playwright)

6. **Navigate to UI**
   - Open: `http://localhost:3001/patterns`
   - Wait for page load

7. **Verify UI State**
   - Check analysis status shows "ready" or "complete"
   - Verify no error messages displayed
   - Check patterns are displayed

8. **Verify Synergy Types in UI**
   - Check synergy type filter/counts in UI
   - Verify multiple types visible (not just event_context)
   - Take screenshot for documentation

---

## Success Criteria

### ✅ Fix Verification Successful If:

1. **Analysis Completed**
   - Status: `"ready"` (not `"error"`)
   - No exceptions in service logs

2. **Multiple Synergy Types Detected**
   - `device_pair` count > 0
   - `device_chain` count > 0
   - Total synergies increased or maintained

3. **UI Displays Results**
   - Patterns page loads correctly
   - Synergy types visible in UI
   - No errors displayed

4. **No Regressions**
   - Pattern count maintained
   - No service errors
   - External data filtering still working (0 external patterns)

---

## Script Implementation

### File: `scripts/automate_pattern_analysis_rerun.py`

**Dependencies:**
- `playwright` (for UI automation)
- `httpx` or `requests` (for API calls)
- Standard library: `time`, `json`, `sys`

**Structure:**
1. API client functions
2. Playwright UI validation functions
3. Main execution flow
4. Error handling and reporting

---

## Expected Timeline

- **Analysis Duration:** 5-15 minutes
- **API Validation:** 1-2 minutes
- **UI Validation:** 30 seconds
- **Total Time:** 15-30 minutes

---

## Rollback Plan

If automation fails:
1. Check service logs: `docker logs ai-pattern-service --tail 100`
2. Verify service health: `curl http://localhost:8034/health`
3. Check database directly if needed
4. Manual verification using guide: `PATTERN_ANALYSIS_RERUN_GUIDE.md`

---

## Next Steps

1. ✅ Create automation script
2. ✅ Execute automation
3. ✅ Document results
4. ✅ Update status in comprehensive summary

---

**Status:** 🚀 **READY TO EXECUTE**  
**Last Updated:** January 16, 2026
