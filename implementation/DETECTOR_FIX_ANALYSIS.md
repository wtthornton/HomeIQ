# Detector Fix Analysis

## Issues Found

### 1. **Sequence Detector**
- **Problem**: Filters for state changes (on/off transitions) but many actionable devices may not have clear state changes
- **Issue**: `_filter_state_changes` may return empty if events don't have state column or states aren't binary
- **Fix**: Make state filtering more flexible, handle non-binary states

### 2. **Contextual Detector**
- **Problem**: Creates dummy weather/presence data but patterns may not meet thresholds
- **Issue**: Works with dummy data but may not produce meaningful patterns
- **Fix**: Make it work better with time-only context, reduce reliance on weather/presence

### 3. **Room-Based Detector**
- **Problem**: Requires 'area' column, defaults to 'unknown' if missing
- **Issue**: If all areas are 'unknown', no patterns will be detected
- **Fix**: Extract area from device_id if available, or use device grouping

### 4. **Duration Detector**
- **Problem**: Requires state changes (on/off) to calculate duration
- **Issue**: May not work with devices that don't have clear on/off states
- **Fix**: Make duration calculation more flexible

### 5. **Session/Day-Type/Seasonal/Anomaly**
- **Problem**: May be too strict or require specific data not available
- **Fix**: Make them more resilient, add better logging

## Root Cause

The main issue is that our new **pattern validation** filters out patterns AFTER detection, but the detectors are trying to detect patterns on ALL devices (including sensors). The detectors should:

1. Work on actionable devices only (or handle gracefully)
2. Be more resilient to missing optional data
3. Have better logging to understand why they return empty

## Fix Strategy

1. **Make detectors work with actionable devices** - Filter events before detection
2. **Add better error handling** - Don't fail silently
3. **Improve logging** - Log why patterns aren't found
4. **Make detectors more resilient** - Handle missing optional data gracefully
5. **Ensure patterns meet validation** - Check patterns before returning

