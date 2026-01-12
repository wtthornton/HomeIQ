# Pattern Analysis Re-run Guide

**Date:** January 16, 2026  
**Status:** ⚠️ **URGENT - CRITICAL ACTION REQUIRED**  
**Purpose:** Guide for re-running pattern analysis to verify synergy detection fixes

---

## Executive Summary

Pattern analysis needs to be re-run to verify that the synergy detection bug fix is working correctly. Currently, only 1 synergy type (`event_context`) is detected, but after the fix, we should see multiple types (`device_pair`, `device_chain`).

---

## Current Status

### Problem

- **Only 1 synergy type detected:** All 48 synergies are `event_context` type
- **Missing synergy types:** Zero `device_pair` or `device_chain` synergies
- **Pattern-synergy alignment:** 84% mismatch (775 patterns don't align with synergies)

### Root Cause (FIXED)

- `DeviceSynergyDetector` was instantiated without required `data_api_client` parameter
- Detector couldn't fetch devices/entities, causing detection to fail silently
- Only `event_context` synergies (from archived code) were in database

### Fix Applied

- ✅ Fixed `pattern_analysis.py` to pass `data_api_client` parameter
- ✅ Detector can now fetch devices and entities correctly
- ✅ Code changes committed

**Status:** ✅ Fixed, ⚠️ **NEEDS VERIFICATION VIA RE-RUN**

---

## How to Re-run Pattern Analysis

### Option 1: Via UI (Recommended)

1. **Navigate to Pattern Service UI**
   - Open browser to: `http://localhost:3001/patterns` (or your UI URL)
   - Or navigate to the Patterns/Synergies dashboard

2. **Trigger Analysis**
   - Look for "Run Analysis" or "Generate Patterns" button
   - Click the button to trigger pattern analysis
   - Wait for analysis to complete (may take several minutes)

3. **Verify Results**
   - Check synergy types in dashboard
   - Should see multiple types: `device_pair`, `device_chain`, `event_context`
   - Check pattern-synergy alignment (should improve from 84% mismatch)

---

### Option 2: Via API Endpoint

1. **Find Analysis Endpoint**
   - Check `services/ai-pattern-service/src/api/` for analysis endpoints
   - Common endpoint: `POST /api/patterns/analyze` or `/api/synergies/analyze`

2. **Trigger Analysis**
   ```bash
   # Example (adjust URL and endpoint as needed)
   curl -X POST http://localhost:8003/api/patterns/analyze
   ```

3. **Verify Results**
   - Check database or dashboard for new synergies
   - Verify synergy types are diverse (not just `event_context`)

---

### Option 3: Via Script

1. **Find Analysis Script**
   - Check `scripts/` directory for pattern analysis scripts
   - Common script: `scripts/run_pattern_analysis.py` or similar

2. **Run Script**
   ```bash
   python scripts/run_pattern_analysis.py
   # Or with Docker database:
   python scripts/run_pattern_analysis.py --use-docker-db
   ```

3. **Verify Results**
   - Script should output synergy detection results
   - Check for multiple synergy types in output

---

## Verification Steps

After re-running pattern analysis, verify the fixes are working:

### 1. Check Synergy Types

**Command:**
```bash
python scripts/diagnose_synergy_types.py --use-docker-db
```

**Expected Results:**
- Multiple synergy types: `device_pair`, `device_chain`, `event_context`
- Device pairs detected for compatible devices
- Device chains detected for sequential device interactions

**Current (Before Re-run):**
- Only 1 type: `event_context` (48 synergies)

**Expected (After Re-run):**
- Multiple types: `device_pair`, `device_chain`, `event_context`
- Total synergies: 48+ (should increase with device pairs/chains)

---

### 2. Check Pattern-Synergy Alignment

**Command:**
```bash
python scripts/validate_patterns_comprehensive.py --use-docker-db --time-window 7
```

**Expected Results:**
- Pattern-synergy alignment improved (currently 84% mismatch)
- More patterns should align with synergies
- Device pair patterns should align with device_pair synergies

**Current (Before Re-run):**
- 775 patterns (84%) don't align with synergies
- Only event_context synergies exist

**Expected (After Re-run):**
- Alignment improved (target: <50% mismatch)
- Device pair patterns align with device_pair synergies

---

### 3. Check External Data Filtering

**Command:**
```bash
python scripts/validate_patterns_comprehensive.py --use-docker-db --time-window 7
```

**Expected Results:**
- 0 external data patterns (sports, weather, calendar)
- 0 invalid patterns
- 0 stale patterns

**Current (After Fix):**
- ✅ 0 external data patterns (verified)
- ✅ 0 invalid patterns (verified)
- ✅ 0 stale patterns (verified)

---

### 4. Check Pattern Support Scores

**Command:**
```bash
# Check synergy pattern support scores
python scripts/validate_synergy_patterns.py --use-docker-db
```

**Expected Results:**
- All synergies have `pattern_support_score > 0.0`
- `validated_by_patterns = True` for synergies with pattern support

**Current (After Fix):**
- ✅ All 48 synergies have calculated scores (avg: 0.203, max: 0.287)
- ✅ Pattern support scores working

---

## Success Criteria

### ✅ Fix Verification Successful If:

1. **Multiple Synergy Types Detected**
   - At least 2 synergy types present (device_pair, device_chain, or event_context)
   - Not just `event_context` type

2. **Device Pairs Detected**
   - At least some `device_pair` synergies exist
   - Device pairs are for compatible devices (e.g., lights + switches)

3. **Pattern-Synergy Alignment Improved**
   - Mismatch reduced from 84% to <70% (target: <50%)
   - Device pair patterns align with device_pair synergies

4. **No Regressions**
   - External data filtering still working (0 external patterns)
   - Pattern support scores still working
   - No new invalid patterns created

---

## Troubleshooting

### Issue: Still Only event_context Synergies

**Possible Causes:**
1. Analysis didn't complete successfully
2. Fix not deployed (code changes not in running service)
3. Data API not accessible (device/entity data not available)

**Solutions:**
1. Check analysis logs for errors
2. Verify code changes are deployed (check `pattern_analysis.py` has `data_api_client` parameter)
3. Verify data-api service is running and accessible
4. Check database for new synergies (may need to query directly)

---

### Issue: Analysis Fails

**Possible Causes:**
1. Database connection issues
2. Data API connection issues
3. Service not running

**Solutions:**
1. Check service logs: `docker logs ai-pattern-service --tail 100`
2. Verify database is accessible
3. Verify data-api service is running: `curl http://localhost:8006/health`
4. Check environment variables are set correctly

---

### Issue: No Device Pairs Detected

**Possible Causes:**
1. No compatible device pairs in Home Assistant data
2. Filters too restrictive (`same_area_required`, `min_confidence`)
3. Device pair detection logic needs adjustment

**Solutions:**
1. Check Home Assistant has compatible device pairs
2. Review device pair detection filters in code
3. Adjust filters if needed (same_area_required, min_confidence)
4. Check device data in database

---

## Expected Timeline

- **Analysis Duration:** 5-15 minutes (depends on data volume)
- **Verification:** 10-15 minutes (running verification scripts)
- **Total Time:** 15-30 minutes

---

## Related Documentation

- `implementation/FINAL_RECOMMENDATIONS_PATTERN_SYNERGY_VALIDATION.md` - Comprehensive recommendations
- `implementation/EXECUTIVE_SUMMARY_VALIDATION.md` - Validation summary
- `services/ai-pattern-service/src/scheduler/pattern_analysis.py` - Analysis code (fixed)

---

## Next Steps After Re-run

1. **If Successful:**
   - Document results
   - Update status in comprehensive summary
   - Monitor pattern-synergy alignment over time

2. **If Issues Found:**
   - Document issues
   - Investigate root causes
   - Create follow-up fixes
   - Re-run analysis after fixes

---

**Status:** ⚠️ **URGENT - REQUIRES MANUAL ACTION**  
**Last Updated:** January 16, 2026  
**Next Review:** After re-run completion
