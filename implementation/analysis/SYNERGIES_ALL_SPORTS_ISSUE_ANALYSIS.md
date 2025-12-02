# Synergies All Sports-Related Issue - Root Cause Analysis

**Date:** December 2, 2025  
**Status:** Issue Identified - Root Cause Found

---

## Executive Summary

**Problem**: All 40 synergies displayed on the synergies page are `event_context` type with sports/calendar event context, all related to media players/TVs.

**Root Cause**: Only the `EventOpportunityDetector` is successfully creating synergies. The `DeviceSynergyDetector` (which should create `device_pair` synergies) and other contextual detectors are either not running, failing silently, or not finding opportunities.

---

## Current Database State

**Query Results:**
```
synergy_type: event_context
Count: 40 (100%)
```

**Sample Synergy Metadata:**
- Type: `event_context`
- Relationship: `gametime_scene`
- Event Context: `Sports schedule available`
- Action Entity: Various media players (family_room_tv, samsung_7_series_65, sony_xr_77a80j, etc.)
- Impact Score: 0.65 (65%)
- Confidence: 0.70 (70%)

---

## Root Cause Analysis

### 1. EventOpportunityDetector is Working

**Location**: `services/ai-automation-service/src/contextual_patterns/event_opportunities.py`

**Behavior**:
- Finds entertainment devices (TVs, media players) via `_get_entertainment_devices()`
- Creates one `event_context` synergy per entertainment device
- Hardcoded values:
  - `synergy_type: 'event_context'`
  - `relationship: 'gametime_scene'`
  - `event_context: 'Sports schedule available'`
  - `impact_score: 0.65`
  - `confidence: 0.70`

**Code Evidence** (lines 54-71):
```python
for device in entertainment_devices:
    opportunities.append({
        'synergy_id': str(uuid.uuid4()),
        'synergy_type': 'event_context',
        'devices': [device['entity_id']],
        'action_entity': device['entity_id'],
        'area': device.get('area_id', 'unknown'),
        'relationship': 'gametime_scene',
        'impact_score': 0.65,  # Medium - convenience
        'complexity': 'medium',
        'confidence': 0.70,
        'opportunity_metadata': {
            'action_name': device.get('friendly_name', device['entity_id']),
            'event_context': 'Sports schedule available',
            'suggested_action': 'Activate game-time scene when team plays',
            'rationale': f"Automate {device.get('friendly_name', device['entity_id'])} for game-time entertainment"
        }
    })
```

### 2. DeviceSynergyDetector is NOT Creating Synergies

**Location**: `services/ai-automation-service/src/synergy_detection/synergy_detector.py`

**Expected Behavior**:
- Should create `device_pair` synergies based on 16 predefined relationship patterns:
  - motion_to_light
  - door_to_light
  - door_to_lock
  - temp_to_climate
  - occupancy_to_light
  - motion_to_climate
  - etc.

**Why It's Not Working**:
1. May not be running during daily analysis
2. May be failing silently
3. May not find compatible device pairs (filtering too strict)
4. May be filtered out by confidence threshold (default 0.7)

**Called In Daily Analysis** (Part A):
```python
synergy_detector = DeviceSynergyDetector(...)
synergies = await synergy_detector.detect_synergies()
```

### 3. WeatherOpportunityDetector is NOT Creating Synergies

**Location**: Should be in contextual patterns

**Expected Behavior**:
- Should create `weather_context` synergies based on weather conditions
- Should integrate with weather data

**Why It's Not Working**:
- May not be implemented
- May be failing silently
- May not have weather data available

### 4. EnergyOpportunityDetector is NOT Creating Synergies

**Location**: Should be in contextual patterns

**Expected Behavior**:
- Should create `energy_context` synergies based on energy pricing/usage
- Should optimize for peak pricing

**Why It's Not Working**:
- May not be implemented
- May be failing silently
- May not have energy data available

---

## Expected Synergy Types

Based on the code and type definitions, the system should support:

1. **`device_pair`** - Device-to-device synergies (motion→light, door→lock, etc.)
2. **`weather_context`** - Weather-aware automations
3. **`energy_context`** - Energy optimization opportunities
4. **`event_context`** - Event-based automations (currently the only one working)

---

## Next Steps

### Immediate Actions (Priority 1)

1. **Check Daily Analysis Logs**
   - Verify if DeviceSynergyDetector is running
   - Check for errors or warnings
   - Verify if it's finding device pairs

2. **Check DeviceSynergyDetector Execution**
   - Add more logging to understand why no device_pair synergies are created
   - Verify device pair detection is working
   - Check if compatible relationships are being found
   - Verify if existing automation filtering is too aggressive

3. **Check Confidence Threshold**
   - Default is 0.7 - may be filtering out valid synergies
   - Consider lowering temporarily to see what's being filtered

4. **Verify Weather/Energy Detectors**
   - Check if they're implemented
   - Check if they're running during daily analysis
   - Check for errors/warnings

### Short-Term Fixes (Priority 2)

1. **Fix EventOpportunityDetector Diversity**
   - Currently only creates sports/calendar events
   - Should support multiple event types (calendar events, sports, holidays, etc.)
   - Should not hardcode "Sports schedule available"

2. **Improve DeviceSynergyDetector**
   - Debug why no device_pair synergies are created
   - Fix any bugs preventing detection
   - Adjust filters/thresholds if needed

3. **Enable Weather/Energy Detection**
   - Implement missing detectors if needed
   - Fix any errors preventing execution
   - Ensure they integrate with daily analysis

### Long-Term Improvements (Priority 3)

1. **Add Logging/Monitoring**
   - Track which detectors are running
   - Track success/failure rates
   - Track synergy creation counts per type

2. **Improve Error Handling**
   - Better error messages when detectors fail
   - Don't fail silently
   - Surface warnings to UI

3. **Add Configuration**
   - Make confidence thresholds configurable
   - Allow enabling/disabling detector types
   - Allow filtering by synergy type in UI

---

## Investigation Commands

### Check Database State
```bash
# Count by type
docker exec ai-automation-service python -c "import sqlite3; conn = sqlite3.connect('/app/data/ai_automation.db'); cursor = conn.cursor(); cursor.execute('SELECT synergy_type, COUNT(*) FROM synergy_opportunities GROUP BY synergy_type'); print(cursor.fetchall())"

# Check recent synergies
docker exec ai-automation-service python -c "import sqlite3; import json; conn = sqlite3.connect('/app/data/ai_automation.db'); cursor = conn.cursor(); cursor.execute('SELECT synergy_type, created_at, opportunity_metadata FROM synergy_opportunities ORDER BY created_at DESC LIMIT 10'); [print(f\"{r[0]} | {r[1]} | {json.loads(r[2]) if r[2] else '{}'}\") for r in cursor.fetchall()]"
```

### Check Docker Logs
```powershell
# Check for synergy detection logs
docker logs ai-automation-service --tail 500 | Select-String -Pattern "synergy|DeviceSynergy|EventOpportunity|WeatherOpportunity|EnergyOpportunity" -CaseSensitive:$false

# Check daily analysis logs
docker logs ai-automation-service --tail 1000 | Select-String -Pattern "daily.*analysis|Part A|Part B|Part C|Part D" -CaseSensitive:$false
```

### Test API Endpoint
```powershell
# Get synergies
Invoke-WebRequest -Uri "http://localhost:8000/api/synergies" | Select-Object -ExpandProperty Content | ConvertFrom-Json | Select-Object -ExpandProperty data | Select-Object -ExpandProperty synergies | Group-Object synergy_type | Select-Object Name, Count
```

---

## Summary

**Current State:**
- ✅ EventOpportunityDetector working (creates event_context synergies)
- ❌ DeviceSynergyDetector not creating device_pair synergies
- ❌ WeatherOpportunityDetector not creating weather_context synergies
- ❌ EnergyOpportunityDetector not creating energy_context synergies

**Main Issue:**
The EventOpportunityDetector is hardcoded to only create sports-related event synergies for entertainment devices. Other detector types are either not running or not creating synergies.

**Next Action:**
1. Investigate why DeviceSynergyDetector isn't creating synergies
2. Check daily analysis logs for errors
3. Fix or enable missing detector types
4. Improve EventOpportunityDetector to support more event types beyond sports

