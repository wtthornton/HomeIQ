# Pattern Detection Analysis and Recommendations

**Date:** October 2025  
**Status:** Analysis Complete - Awaiting Approval  
**Issue:** Too many patterns (1222), many low-quality, not useful for automation

## Executive Summary

The pattern detection system is generating **1,222 patterns** but only **2 pattern types** are being stored despite 10 detectors running. Many patterns are low-quality (5-9 occurrences) and target sensors that update constantly (battery levels, trackers), creating noise rather than actionable automation opportunities.

## Current State Analysis

### Pattern Statistics (from UI)
- **Total Patterns:** 1,222
- **Unique Devices:** 1,222 (suspiciously identical - suggests 1 pattern per device)
- **Pattern Types:** 2 (time_of_day, co_occurrence)
- **Average Confidence:** 99%
- **Last Analysis:** Never (suggests data may be stale)

### Pattern Types Detected (from UI)
1. **time_of_day** - Most common, showing patterns like:
   - `sensor.tapps_iphone_16_battery_level` (7 occurrences)
   - `sensor.roborock_status` (5 occurrences)
   - `sensor.dal_team_tracker` (multiple co-occurrence patterns)
   - `event.backup_automatic_backup` (9 occurrences)

2. **co_occurrence** - Examples:
   - `sensor.dal_team_tracker+sensor.slzb_06p7_coordinator_zigbee_chip_temp` (405 occurrences)
   - `sensor.dal_team_tracker+sensor.vgk_team_tracker` (1171 occurrences)

### Detectors Configured (from daily_analysis.py)
1. ✅ `TimeOfDayPatternDetector` - min_occurrences=5, min_confidence=0.7
2. ✅ `CoOccurrencePatternDetector` - min_support=5, min_confidence=0.7
3. ✅ `SequenceDetector` - min_sequence_occurrences=3, min_confidence=0.7
4. ✅ `ContextualDetector` - min_confidence=0.7
5. ✅ `RoomBasedDetector` - min_room_occurrences=5, min_confidence=0.7
6. ✅ `SessionDetector` - min_session_occurrences=3, min_confidence=0.7
7. ✅ `DurationDetector` - min_occurrences=3, min_confidence=0.7
8. ✅ `DayTypeDetector` - min_day_type_occurrences=5, min_confidence=0.7
9. ✅ `SeasonalDetector` - min_seasonal_occurrences=10, min_confidence=0.7
10. ✅ `AnomalyDetector` - min_anomaly_occurrences=3, min_confidence=0.7

**Problem:** All 10 detectors run, but only 2 pattern types appear in database. This suggests:
- 8 detectors aren't finding patterns (or failing silently)
- Patterns are being filtered out somewhere
- Patterns aren't being stored correctly

## Issues Identified

### 1. **Low-Quality Patterns**
- Patterns with only 5-9 occurrences are being stored
- Sensors that update constantly (battery, trackers) create noise
- Patterns with 100% confidence but low occurrence counts suggest confidence calculation issues

### 2. **Noise from System Sensors**
Examples of problematic patterns:
- Battery level sensors (`sensor.tapps_iphone_16_battery_level`)
- System status sensors (`sensor.roborock_status`)
- Tracker sensors that update frequently (`sensor.dal_team_tracker`)
- System events (`event.backup_automatic_backup`)

These are not useful for automation because:
- They update automatically (battery levels)
- They're system events, not user actions
- They don't represent actionable behaviors

### 3. **Missing Pattern Types**
Only 2 of 10 detector types are producing results:
- ✅ `time_of_day` - Working
- ✅ `co_occurrence` - Working
- ❌ `sequence` - Not found
- ❌ `contextual` - Not found
- ❌ `room_based` - Not found
- ❌ `session` - Not found
- ❌ `duration` - Not found
- ❌ `day_type` - Not found
- ❌ `seasonal` - Not found
- ❌ `anomaly` - Not found

### 4. **Suspicious Statistics**
- Total patterns = Unique devices (1222 = 1222) suggests one pattern per device
- This is unusual - typically devices would have multiple patterns or multiple devices would share patterns

### 5. **Confidence Calculation Issues**
- Patterns with 5-9 occurrences showing 100% confidence
- Confidence should be based on consistency, not just meeting minimum threshold
- Example: A pattern with 5 occurrences shouldn't have 100% confidence

## Root Causes

### 1. **Insufficient Filtering**
- No filtering by entity domain/type (sensors vs lights vs switches)
- No exclusion list for system sensors
- No minimum occurrence threshold validation beyond detector settings

### 2. **Confidence Calculation**
- Confidence appears to be binary (pass/fail) rather than calculated
- Low occurrence patterns shouldn't have high confidence
- Need confidence based on:
  - Occurrence count (more = higher)
  - Consistency (variance in timing)
  - Statistical significance

### 3. **Missing Pattern Validation**
- Patterns stored without utility validation
- No check if pattern is actionable/useful
- No filtering by device type relevance

### 4. **Detector Failures**
- 8 detectors not producing results (may be failing silently)
- Need to check logs for errors
- May need to adjust thresholds or fix detector logic

## Recommendations

### Phase 1: Immediate Fixes (High Priority)

#### 1.1 Add Entity Domain Filtering
**Action:** Filter out patterns from non-actionable entities

```python
# Exclude these domains/prefixes:
EXCLUDED_DOMAINS = [
    'sensor',  # Most sensors don't represent user actions
    'event',   # System events
    'image',   # Camera images
    'counter', # Counters
    'input_number', # Configuration
]

# Keep these domains:
ACTIONABLE_DOMAINS = [
    'light',
    'switch',
    'cover',
    'climate',
    'fan',
    'lock',
    'scene',
    'automation',
    'script',
    'media_player',
]

# Exclude specific prefixes:
EXCLUDED_PREFIXES = [
    'sensor.home_assistant_',  # System sensors
    'sensor.slzb_',            # Zigbee coordinator
    'sensor.*_battery_level',  # Battery sensors
    'sensor.*_battery_state',  # Battery state
    'sensor.*_status',         # Status sensors
    'sensor.*_tracker',        # Tracker sensors
    'sensor.*_distance',       # Distance sensors
    'sensor.*_steps',          # Fitness sensors
]
```

#### 1.2 Increase Minimum Occurrences
**Action:** Raise minimum occurrence thresholds

```python
# Current (too low):
min_occurrences = 5  # For time_of_day
min_support = 5      # For co_occurrence

# Recommended (more meaningful):
min_occurrences = 10  # For time_of_day (at least 10 occurrences in 30 days)
min_support = 10      # For co_occurrence (at least 10 co-occurrences)
min_sequence_occurrences = 5  # For sequences (5 complete sequences)
```

#### 1.3 Fix Confidence Calculation
**Action:** Calculate confidence based on actual metrics

```python
def calculate_confidence(occurrences, total_events, variance, min_occurrences):
    """
    Calculate confidence based on:
    - Occurrence count (more is better)
    - Consistency (lower variance is better)
    - Statistical significance
    """
    # Base confidence from occurrence ratio
    occurrence_ratio = occurrences / max(total_events, min_occurrences * 10)
    
    # Variance penalty (lower variance = higher confidence)
    variance_penalty = min(variance / 100, 1.0)  # Normalize variance
    
    # Minimum threshold boost
    if occurrences >= min_occurrences * 2:
        threshold_boost = 0.1
    else:
        threshold_boost = 0.0
    
    confidence = min(0.95, occurrence_ratio * (1 - variance_penalty) + threshold_boost)
    
    return max(0.5, confidence)  # Minimum 50% confidence
```

#### 1.4 Add Pattern Utility Scoring
**Action:** Score patterns by automation potential

```python
def calculate_utility_score(pattern):
    """
    Score pattern by how useful it is for automation:
    - Device type relevance
    - Action clarity
    - Automation potential
    - User impact
    """
    score = 0.0
    
    # Device type score
    device_type = pattern.get('device_id', '').split('.')[0]
    if device_type in ACTIONABLE_DOMAINS:
        score += 0.4
    elif device_type == 'sensor':
        score += 0.1  # Low score for sensors
    
    # Occurrence count score
    occurrences = pattern.get('occurrences', 0)
    if occurrences >= 20:
        score += 0.3
    elif occurrences >= 10:
        score += 0.2
    else:
        score += 0.1
    
    # Pattern type score
    pattern_type = pattern.get('pattern_type', '')
    if pattern_type in ['time_of_day', 'sequence', 'co_occurrence']:
        score += 0.3  # High utility types
    
    return min(1.0, score)
```

### Phase 2: Pattern Type Optimization (Medium Priority)

#### 2.1 Disable Low-Value Detectors
**Recommendation:** Disable detectors that aren't producing useful results

```python
# Keep these (high value):
ENABLED_DETECTORS = [
    'time_of_day',      # ✅ Core pattern type
    'co_occurrence',    # ✅ Core pattern type
    'sequence',         # ✅ Useful for automation
    'room_based',       # ✅ Useful for automation
]

# Disable these (low value or not working):
DISABLED_DETECTORS = [
    'contextual',       # ❌ Requires weather data (may not be available)
    'session',          # ❌ Not producing results
    'duration',         # ❌ Not producing results
    'day_type',         # ❌ Not producing results
    'seasonal',         # ❌ Requires long-term data
    'anomaly',          # ❌ Not producing results
]
```

#### 2.2 Fix Detector Issues
**Action:** Investigate why 8 detectors aren't producing results

- Check logs for errors
- Verify detector thresholds aren't too strict
- Test each detector individually
- Fix any bugs in detector logic

### Phase 3: Pattern Cleanup (Medium Priority)

#### 3.1 Clean Existing Database
**Action:** Remove low-quality patterns from database

```sql
-- Remove patterns from excluded domains
DELETE FROM patterns 
WHERE device_id LIKE 'sensor.%' 
   OR device_id LIKE 'event.%'
   OR device_id LIKE 'image.%'
   OR device_id LIKE '%_battery_level'
   OR device_id LIKE '%_battery_state'
   OR device_id LIKE '%_status'
   OR device_id LIKE '%_tracker';

-- Remove patterns with low occurrences
DELETE FROM patterns 
WHERE occurrences < 10;

-- Remove patterns with low utility
DELETE FROM patterns 
WHERE confidence < 0.75 
   OR occurrences < 10;
```

#### 3.2 Add Pattern Validation
**Action:** Validate patterns before storing

```python
def validate_pattern(pattern):
    """Validate pattern before storing"""
    
    # Check domain
    device_id = pattern.get('device_id', '')
    domain = device_id.split('.')[0] if '.' in device_id else ''
    
    if domain in EXCLUDED_DOMAINS:
        return False
    
    # Check prefix exclusions
    for prefix in EXCLUDED_PREFIXES:
        if device_id.startswith(prefix):
            return False
    
    # Check minimum occurrences
    if pattern.get('occurrences', 0) < 10:
        return False
    
    # Check confidence
    if pattern.get('confidence', 0) < 0.7:
        return False
    
    # Check utility score
    utility = calculate_utility_score(pattern)
    if utility < 0.5:
        return False
    
    return True
```

### Phase 4: Enhanced Filtering (Low Priority)

#### 4.1 Add User-Configurable Filters
**Action:** Allow users to configure pattern filters in UI

- Exclude specific devices
- Exclude specific domains
- Adjust minimum occurrence thresholds
- Adjust confidence thresholds

#### 4.2 Add Pattern Quality Indicators
**Action:** Show pattern quality in UI

- Occurrence count
- Confidence score
- Utility score
- Last seen date
- Trend (increasing/decreasing)

## Implementation Plan

### Step 1: Quick Wins (1-2 hours)
1. ✅ Add entity domain filtering to pattern storage
2. ✅ Increase minimum occurrence thresholds
3. ✅ Add exclusion list for system sensors
4. ✅ Fix confidence calculation

### Step 2: Database Cleanup (30 minutes)
1. ✅ Run SQL cleanup script
2. ✅ Verify pattern count reduction
3. ✅ Test UI with cleaned data

### Step 3: Detector Investigation (2-4 hours)
1. ✅ Check logs for detector errors
2. ✅ Test each detector individually
3. ✅ Fix detector issues or disable non-working detectors
4. ✅ Verify pattern types are being stored

### Step 4: Validation & Testing (1-2 hours)
1. ✅ Add pattern validation before storage
2. ✅ Test with sample data
3. ✅ Verify quality improvements
4. ✅ Update UI to show quality indicators

## Expected Results

### Before Fixes
- Total Patterns: 1,222
- Pattern Types: 2
- Quality: Low (many noise patterns)
- Useful Patterns: ~10-20%

### After Fixes
- Total Patterns: ~50-100 (high quality)
- Pattern Types: 4-6 (time_of_day, co_occurrence, sequence, room_based)
- Quality: High (actionable patterns only)
- Useful Patterns: ~80-90%

## Approval Required

**Please approve the following:**

1. ✅ **Entity Domain Filtering** - Filter out sensors, events, and other non-actionable entities
2. ✅ **Increased Minimum Occurrences** - Raise from 5 to 10 for most detectors
3. ✅ **Pattern Validation** - Add validation before storing patterns
4. ✅ **Database Cleanup** - Remove existing low-quality patterns
5. ✅ **Detector Investigation** - Fix or disable non-working detectors
6. ✅ **Confidence Calculation Fix** - Calculate confidence based on actual metrics

**Questions for Review:**
- Which pattern types are most valuable for your use case?
- Should we disable any detectors permanently?
- What minimum occurrence threshold makes sense (10, 15, 20)?
- Are there specific device types you want to exclude?

---

**Next Steps:** Awaiting approval to proceed with Phase 1 fixes.

