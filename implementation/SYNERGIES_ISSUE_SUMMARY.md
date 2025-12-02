# Synergies All Sports-Related Issue - Summary & Next Steps

**Date:** December 2, 2025  
**Issue:** All synergies displayed are sports-related event_context type

---

## Problem Identified

**Current State:**
- All 40 synergies in database are `event_context` type
- All related to sports/calendar events
- All targeting media players/TVs
- No `device_pair`, `weather_context`, or `energy_context` synergies

**Root Cause:**
The `EventOpportunityDetector` is the only detector successfully creating synergies. It's hardcoded to create sports-related synergies for entertainment devices. Other detectors (`DeviceSynergyDetector`, `WeatherOpportunityDetector`, `EnergyOpportunityDetector`) are either not running or not creating synergies.

---

## Why All Synergies Are Sports-Related

1. **EventOpportunityDetector** (working):
   - Finds entertainment devices (TVs, media players)
   - Creates one synergy per device
   - Hardcoded: `event_context: 'Sports schedule available'`
   - Hardcoded: `relationship: 'gametime_scene'`

2. **DeviceSynergyDetector** (not working):
   - Should create `device_pair` synergies (motion→light, door→lock, etc.)
   - Either not running or not finding compatible pairs

3. **WeatherOpportunityDetector** (not working):
   - Should create `weather_context` synergies
   - Not creating any synergies

4. **EnergyOpportunityDetector** (not working):
   - Should create `energy_context` synergies
   - Not creating any synergies

---

## Next Steps

### Step 1: Investigate DeviceSynergyDetector (HIGH PRIORITY)

**Why**: This should be creating the majority of synergies (device pairs)

**Actions**:
1. Check daily analysis logs for errors
   ```powershell
   docker logs ai-automation-service --tail 1000 | Select-String -Pattern "DeviceSynergy|Part A" -CaseSensitive:$false
   ```

2. Check if device pairs are being found but filtered out
   - Review confidence threshold (default 0.7 may be too high)
   - Check if existing automation filter is too aggressive
   - Verify device pair detection logic

3. Run manual detection test:
   ```python
   # Test DeviceSynergyDetector directly
   from services.ai_automation_service.src.synergy_detection.synergy_detector import DeviceSynergyDetector
   detector = DeviceSynergyDetector(...)
   synergies = await detector.detect_synergies()
   ```

**Expected Outcome**: Should find many device_pair synergies based on 16 relationship patterns

### Step 2: Fix EventOpportunityDetector Diversity (MEDIUM PRIORITY)

**Why**: Even if working, it's too narrow (only sports events)

**Actions**:
1. Support multiple event types:
   - Calendar events (meetings, appointments)
   - Holidays
   - Sports events (current)
   - Custom events

2. Remove hardcoded "Sports schedule available" message

3. Query actual sports data service if available

**File**: `services/ai-automation-service/src/contextual_patterns/event_opportunities.py`

### Step 3: Enable Weather/Energy Detectors (MEDIUM PRIORITY)

**Why**: Should provide contextual opportunities beyond devices

**Actions**:
1. Check if `WeatherOpportunityDetector` exists and is implemented
2. Check if `EnergyOpportunityDetector` exists and is implemented
3. Verify they're being called in daily analysis
4. Fix any errors preventing execution

**Location**: Should be in `services/ai-automation-service/src/contextual_patterns/`

### Step 4: Add Better Logging/Monitoring (LOW PRIORITY)

**Why**: Need visibility into what's happening

**Actions**:
1. Add logging for each detector type
2. Track success/failure rates
3. Track synergy counts per type
4. Add monitoring/metrics

---

## Quick Investigation Commands

### Check Database
```bash
# Count by type
docker exec ai-automation-service python -c "import sqlite3; conn = sqlite3.connect('/app/data/ai_automation.db'); cursor = conn.cursor(); cursor.execute('SELECT synergy_type, COUNT(*) FROM synergy_opportunities GROUP BY synergy_type'); print(cursor.fetchall())"
```

### Check Logs
```powershell
# Recent synergy detection logs
docker logs ai-automation-service --tail 500 | Select-String -Pattern "synergy|opportunity" -CaseSensitive:$false

# Daily analysis logs
docker logs ai-automation-service --tail 1000 | Select-String -Pattern "daily.*analysis" -CaseSensitive:$false
```

### Check API
```powershell
# Get synergy statistics
Invoke-WebRequest -Uri "http://localhost:8000/api/synergies/stats" | Select-Object -ExpandProperty Content
```

---

## Expected Outcome After Fixes

**Should See:**
- `device_pair`: Many synergies (motion→light, door→lock, etc.)
- `weather_context`: Some synergies (if weather data available)
- `energy_context`: Some synergies (if energy data available)
- `event_context`: Few synergies (sports, calendar events)

**Not Just:**
- Only `event_context` synergies
- Only sports-related
- Only media players

---

## Files to Review

1. `services/ai-automation-service/src/synergy_detection/synergy_detector.py` - DeviceSynergyDetector
2. `services/ai-automation-service/src/contextual_patterns/event_opportunities.py` - EventOpportunityDetector
3. `services/ai-automation-service/src/scheduler/daily_analysis.py` - Daily analysis orchestration
4. `services/ai-automation-service/src/contextual_patterns/` - Weather/Energy detectors (check if exist)

---

## Detailed Analysis

See: `implementation/analysis/SYNERGIES_ALL_SPORTS_ISSUE_ANALYSIS.md`

