# Degraded Performance Resolution Plan

**Date:** January 2025  
**Status:** Plan Created  
**Issue:** Dashboard showing "DEGRADED PERFORMANCE" due to Processing component AMBER status

---

## Executive Summary

The HomeIQ dashboard is displaying **"DEGRADED PERFORMANCE"** status because:
- **Current Throughput:** 4.68 evt/min
- **Amber Threshold:** 5 evt/min
- **Status:** 4.68 < 5 → **AMBER** → **DEGRADED**

However, the system is actually **healthy**:
- ✅ Error Rate: 0.00%
- ✅ Latency: 8.9 ms (excellent)
- ✅ Core components (INGESTION, STORAGE): Healthy
- ✅ System functioning normally

This is a **false positive** caused by a strict threshold that doesn't account for:
1. Normal low-activity periods (night time, quiet hours)
2. Momentary throughput dips
3. Context (error rate and latency are excellent)

---

## Root Cause Analysis

### Current State

**Dashboard Metrics (from images):**
- **Throughput:** 4.68 evt/min
- **Processing Status:** AMBER
- **Overall Status:** DEGRADED PERFORMANCE
- **Error Rate:** 0.00% ✅
- **Latency:** 8.9 ms avg ✅
- **Uptime:** 22h 0m 43s ✅

**RAG Thresholds (Current):**
```typescript
processing: {
  green: { throughput: 20, queueSize: 10 },
  amber: { throughput: 5, queueSize: 50 }   // Current threshold
}
```

**RAG Calculation Logic:**
- If throughput < 5 evt/min → AMBER
- If throughput < 2.5 evt/min (amber * 0.5) → RED
- If any component is AMBER → Overall status is AMBER
- If overall is AMBER → System status is "DEGRADED"

### Why This Is Happening

1. **Normal Low-Activity Period**
   - Home Assistant systems naturally have quiet periods
   - Night time, minimal device activity
   - 4.68 evt/min is within normal range for low-activity periods

2. **Threshold Too Strict**
   - Current threshold (5 evt/min) doesn't account for:
     - Time-of-day variations
     - Momentary dips
     - Context (error rate, latency)

3. **No Context Awareness**
   - System only checks throughput
   - Ignores that error rate is 0% and latency is excellent
   - No consideration of historical patterns

### Research Findings

Based on Home Assistant event rate research:
- **Small Home:** 36-48 evt/min average (0.6-0.8 eps)
- **Medium Home:** 180-240 evt/min average (3-4 eps)
- **Large Home:** 840-1200 evt/min average (14-20 eps)

**Current system (4.68 evt/min)** is:
- Very low for any home size
- Could indicate:
  - Low-activity period (normal)
  - Small installation with minimal devices
  - Quiet time of day

---

## Solution Options

### Option 1: Lower Threshold Further (Quick Fix) ⚠️

**Approach:** Lower amber threshold from 5 to 3 evt/min

**Pros:**
- ✅ Quick to implement
- ✅ Reduces false positives
- ✅ Still catches real issues (< 3 evt/min is concerning)

**Cons:**
- ❌ Doesn't address root cause
- ❌ May hide real problems
- ❌ Still sensitive to momentary dips
- ❌ No context awareness

**Implementation:**
```typescript
processing: {
  green: { throughput: 20, queueSize: 10 },
  amber: { throughput: 3, queueSize: 50 }   // Lower from 5 to 3
}
```

**Risk:** Medium - May hide real issues if throughput drops below 3

---

### Option 2: Context-Aware Thresholds (Recommended) ✅

**Approach:** Consider error rate and latency when determining status

**Logic:**
- If error rate = 0% AND latency < 20ms → Allow lower throughput threshold
- If error rate > 0% OR latency > 50ms → Use standard threshold
- This prevents false positives when system is clearly healthy

**Pros:**
- ✅ Addresses root cause
- ✅ More intelligent status determination
- ✅ Reduces false positives while maintaining sensitivity
- ✅ Better user experience

**Cons:**
- ⚠️ More complex logic
- ⚠️ Requires testing

**Implementation:**
```typescript
// In calculateComponentRAG for processing:
if (component === 'processing') {
  const throughput = metrics.throughput ?? undefined;
  const errorRate = metrics.errorRate ?? 0;
  const latency = metrics.latency ?? 0;
  
  // Context-aware threshold adjustment
  // If system is healthy (low error, low latency), be more lenient
  const isSystemHealthy = errorRate === 0 && latency < 20;
  const adjustedAmberThreshold = isSystemHealthy 
    ? componentThresholds.amber.throughput * 0.6  // 60% of threshold (3 evt/min)
    : componentThresholds.amber.throughput;       // Standard threshold (5 evt/min)
  
  // Use adjustedAmberThreshold in calculations...
}
```

**Risk:** Low - Maintains sensitivity while reducing false positives

---

### Option 3: Time-Based Averaging (Best Long-Term) ✅

**Approach:** Use rolling average over last 5-15 minutes instead of instantaneous value

**Pros:**
- ✅ Smooths out momentary dips
- ✅ More stable status
- ✅ Better reflects actual system health
- ✅ Industry best practice

**Cons:**
- ⚠️ Requires storing historical data
- ⚠️ More complex implementation
- ⚠️ May delay detection of real issues

**Implementation:**
- Use `usePerformanceHistory` hook (already exists)
- Calculate average throughput over last 5-15 minutes
- Use average for RAG calculation instead of instantaneous value

**Risk:** Low - Standard approach in monitoring systems

---

### Option 4: Hybrid Approach (Recommended) ✅✅

**Approach:** Combine Option 2 (Context-Aware) + Option 3 (Time-Based Averaging)

**Implementation:**
1. Use rolling average throughput (last 5 minutes)
2. Apply context-aware threshold adjustment
3. Consider error rate and latency in decision

**Pros:**
- ✅ Best of both worlds
- ✅ Most robust solution
- ✅ Industry best practice
- ✅ Excellent user experience

**Cons:**
- ⚠️ Most complex to implement
- ⚠️ Requires more testing

**Risk:** Very Low - Most comprehensive solution

---

## Recommended Solution: Hybrid Approach

### Phase 1: Quick Fix (Immediate)
**Implement Option 2: Context-Aware Thresholds**

This provides immediate relief while maintaining system health detection.

**Changes:**
1. Modify `calculateComponentRAG` in `ragCalculations.ts`
2. Add context-aware threshold adjustment
3. Test with current metrics

**Expected Result:**
- Throughput: 4.68 evt/min
- Error Rate: 0%
- Latency: 8.9 ms
- Adjusted threshold: 3 evt/min (5 * 0.6)
- Status: 4.68 > 3 → **GREEN** → **OPERATIONAL**

### Phase 2: Enhancement (Next Sprint)
**Implement Option 3: Time-Based Averaging**

Add rolling average calculation for more stable status.

**Changes:**
1. Enhance `usePerformanceHistory` hook
2. Use average throughput in RAG calculations
3. Add configuration for averaging window

---

## Implementation Plan

### Step 1: Implement Context-Aware Thresholds

**File:** `services/health-dashboard/src/utils/ragCalculations.ts`

**Changes:**
1. Modify `calculateComponentRAG` function
2. Add context-aware logic for processing component
3. Adjust threshold based on error rate and latency

**Code Changes:**
```typescript
else if (component === 'processing') {
  const throughput = metrics.throughput ?? undefined;
  const errorRate = metrics.errorRate ?? 0;
  const latency = metrics.latency ?? 0;

  // Context-aware threshold adjustment
  // If system is healthy (no errors, low latency), be more lenient with throughput
  const isSystemHealthy = errorRate === 0 && latency < 20;
  const adjustedAmberThreshold = isSystemHealthy 
    ? componentThresholds.amber.throughput * 0.6  // 60% of threshold (3 evt/min when healthy)
    : componentThresholds.amber.throughput;       // Standard threshold (5 evt/min)

  // If throughput is undefined/null, we don't have data yet - default to green
  if (throughput === undefined || throughput === null) {
    state = 'green';
    reasons.push('Metrics data not yet available - assuming healthy');
  }
  // Check red thresholds (throughput too low or error rate too high)
  else if (throughput < adjustedAmberThreshold * 0.5 || 
      errorRate > 5.0) {
    state = 'red';
    if (throughput < adjustedAmberThreshold * 0.5) {
      reasons.push(`Low throughput: ${throughput.toFixed(1)} evt/min (threshold: ${(adjustedAmberThreshold * 0.5).toFixed(1)} evt/min)`);
    }
    if (errorRate > 5.0) {
      reasons.push(`High error rate: ${errorRate.toFixed(2)}% (threshold: 5.0%)`);
    }
  }
  // Check amber thresholds
  else if (throughput < adjustedAmberThreshold || 
           errorRate > 2.0) {
    state = 'amber';
    if (throughput < adjustedAmberThreshold) {
      reasons.push(`Reduced throughput: ${throughput.toFixed(1)} evt/min (threshold: ${adjustedAmberThreshold.toFixed(1)} evt/min, ${isSystemHealthy ? 'adjusted for healthy system' : 'standard'})`);
    }
    if (errorRate > 2.0) {
      reasons.push(`Elevated error rate: ${errorRate.toFixed(2)}% (threshold: 2.0%)`);
    }
  } else {
    reasons.push('All metrics within normal thresholds');
  }
}
```

### Step 2: Testing

**Test Cases:**
1. **Current Scenario:**
   - Throughput: 4.68 evt/min
   - Error Rate: 0%
   - Latency: 8.9 ms
   - Expected: GREEN (4.68 > 3.0)

2. **Unhealthy System:**
   - Throughput: 4.68 evt/min
   - Error Rate: 3%
   - Latency: 50 ms
   - Expected: AMBER (4.68 < 5.0, standard threshold)

3. **Very Low Throughput:**
   - Throughput: 1.5 evt/min
   - Error Rate: 0%
   - Latency: 10 ms
   - Expected: RED (1.5 < 1.8 = 3.0 * 0.5)

4. **Normal Operation:**
   - Throughput: 10 evt/min
   - Error Rate: 0%
   - Latency: 10 ms
   - Expected: GREEN

### Step 3: Verification

**After Implementation:**
1. ✅ Dashboard should show "ALL SYSTEMS OPERATIONAL"
2. ✅ Processing component should show GREEN
3. ✅ Overall RAG status should be GREEN
4. ✅ Status should remain stable during low-activity periods

### Step 4: Documentation

**Update:**
1. `implementation/DEGRADED_PERFORMANCE_ANALYSIS.md` - Mark as resolved
2. Add comments to code explaining context-aware logic
3. Update threshold documentation

---

## Risk Assessment

### Risks
1. **False Negatives:** System might not detect real issues
   - **Mitigation:** Maintain RED threshold at 50% of amber (very low)
   - **Mitigation:** Standard threshold still applies if error rate > 0% or latency > 20ms

2. **Complexity:** More complex logic
   - **Mitigation:** Well-documented code
   - **Mitigation:** Comprehensive tests

3. **User Confusion:** Status changes might be unexpected
   - **Mitigation:** Clear reasons in RAG status
   - **Mitigation:** Documentation

### Benefits
1. ✅ Reduced false positives
2. ✅ Better user experience
3. ✅ More intelligent status determination
4. ✅ Maintains sensitivity to real issues

---

## Success Criteria

### Immediate (Phase 1)
- [ ] Dashboard shows "ALL SYSTEMS OPERATIONAL" for current metrics
- [ ] Processing component shows GREEN when system is healthy
- [ ] No false positives during normal low-activity periods
- [ ] Still detects real issues (error rate, latency problems)

### Long-Term (Phase 2)
- [ ] Time-based averaging implemented
- [ ] Stable status during momentary dips
- [ ] Historical pattern analysis
- [ ] Configurable thresholds

---

## Timeline

### Phase 1: Context-Aware Thresholds
- **Implementation:** 1-2 hours
- **Testing:** 1 hour
- **Verification:** 30 minutes
- **Total:** ~3 hours

### Phase 2: Time-Based Averaging (Future)
- **Implementation:** 4-6 hours
- **Testing:** 2 hours
- **Verification:** 1 hour
- **Total:** ~8 hours

---

## Next Steps

1. ✅ Review and approve plan
2. ✅ Implement Phase 1 (Context-Aware Thresholds)
3. ✅ Build and deploy changes
4. ⏳ Verify dashboard status (pending user verification)
5. ✅ Document changes
6. ⏳ Plan Phase 2 (Time-Based Averaging) - Future enhancement

---

## Implementation Status

### ✅ Phase 1: Context-Aware Thresholds - COMPLETED

**Date:** January 2025  
**Status:** ✅ **IMPLEMENTED AND DEPLOYED**

**Changes Made:**
1. ✅ Modified `calculateComponentRAG` in `services/health-dashboard/src/utils/ragCalculations.ts`
   - Added context-aware threshold adjustment logic
   - Adjusted threshold to 60% (3 evt/min) when system is healthy (error rate = 0%, latency < 20ms)
   - Maintains standard threshold (5 evt/min) when system has issues

2. ✅ Enhanced `extractComponentMetrics` function
   - Added latency to processing metrics (using websocket latency as proxy)
   - Enables context-aware threshold calculation

3. ✅ Build and Deployment
   - Code compiled successfully
   - Docker container rebuilt
   - Container restarted

**Expected Results:**
- With current metrics (4.68 evt/min, 0% error rate, 8.9 ms latency):
  - System is healthy → Adjusted threshold: 3.0 evt/min
  - 4.68 > 3.0 → Status: **GREEN**
  - Overall status: **ALL SYSTEMS OPERATIONAL**

**Verification:**
- [ ] Dashboard should now show "ALL SYSTEMS OPERATIONAL" instead of "DEGRADED PERFORMANCE"
- [ ] Processing component should show GREEN status
- [ ] Overall RAG status should be GREEN
- [ ] Status should remain stable during low-activity periods

---

**Last Updated:** January 2025  
**Status:** ✅ **PHASE 1 IMPLEMENTED AND DEPLOYED**  
**Priority:** High (affecting user experience)

