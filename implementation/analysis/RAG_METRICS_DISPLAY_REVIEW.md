# RAG Metrics Display Review

**Date:** January 16, 2026  
**Status:** Review Complete - Issues Found  
**Goal:** Review and fix display of RAG (Retrieval-Augmented Generation) metrics vs data ingestion metrics

## Executive Summary

**CRITICAL ISSUE FOUND:** The "RAG Status Monitor" is displaying **data ingestion metrics** (websocket-ingestion statistics) instead of **RAG metrics** (Retrieval-Augmented Generation operations). RAG metrics are being fetched but never displayed.

## Current State Analysis

### What's Being Displayed (WRONG)

The "RAG Status Monitor" currently shows:

#### In RAGStatusCard (Card View):
1. **"Data Metrics" Section** (Lines 209-268 in `RAGStatusCard.tsx`):
   - Total Events (from `statistics.metrics?.['websocket-ingestion']?.total_events_received`)
   - Throughput (events/min from websocket-ingestion)
   - Connections (connection attempts from websocket-ingestion)
   - Last Refresh (statistics timestamp)

**These are data ingestion metrics, NOT RAG metrics.**

#### In RAGDetailsModal (Modal View):
1. **"Data Metrics" Section** (Lines 277-376 in `RAGDetailsModal.tsx`):
   - Total Events (websocket-ingestion)
   - Throughput (websocket-ingestion)
   - Connection Attempts (websocket-ingestion)
   - Error Rate (websocket-ingestion)
   - Response Time (websocket-ingestion)
   - Last Data Refresh

2. **"Data Breakdown" Section** (Lines 379-487):
   - Events Processed
   - Unique Entities
   - Events per Entity
   - Event Types Breakdown

**All of these are data ingestion metrics, NOT RAG metrics.**

### What Should Be Displayed (CORRECT)

#### RAG Metrics (Available but NOT Displayed):

The `rag-service` has a metrics endpoint (`GET /api/v1/metrics`) that provides:

```typescript
{
  total_calls: number;           // Total RAG operations
  store_calls: number;           // Knowledge storage operations
  retrieve_calls: number;        // Knowledge retrieval operations
  search_calls: number;          // Semantic search operations
  cache_hits: number;            // Embedding cache hits
  cache_misses: number;          // Embedding cache misses
  cache_hit_rate: number;        // Cache hit percentage
  avg_latency_ms: number;        // Average RAG operation latency
  min_latency_ms: number;        // Minimum latency
  max_latency_ms: number;        // Maximum latency
  errors: number;                // Total errors
  embedding_errors: number;      // Embedding generation errors
  storage_errors: number;        // Storage errors
  error_rate: number;            // Error rate percentage
  avg_success_score: number;     // Average success score
}
```

### Code Analysis

#### Issue 1: RAG Metrics Fetched But Not Displayed

**File:** `services/health-dashboard/src/components/RAGDetailsModal.tsx`

**Lines 136-154:** RAG metrics ARE being fetched:
```typescript
useEffect(() => {
  const fetchRAGMetrics = async () => {
    if (!isOpen) return;
    
    try {
      setRagMetricsLoading(true);
      const metrics = await ragApi.getMetrics();  // ✅ Fetched
      setRagMetrics(metrics);                     // ✅ Stored in state
    } catch (error) {
      console.error('Failed to fetch RAG service metrics:', error);
      // ❌ Silent failure - no error displayed to user
    } finally {
      setRagMetricsLoading(false);
    }
  };

  fetchRAGMetrics();
}, [isOpen]);
```

**BUT:** The `ragMetrics` state is never used to render UI! There's no section displaying RAG metrics in the modal.

#### Issue 2: Data Ingestion Metrics Displayed Instead

**File:** `services/health-dashboard/src/components/RAGDetailsModal.tsx`

**Lines 277-376:** "Data Metrics" section displays websocket-ingestion statistics:
```typescript
{statistics && (
  <div>
    <h3>Data Metrics</h3>
    {/* Shows websocket-ingestion statistics */}
    {formatNumber(statistics.metrics?.['websocket-ingestion']?.total_events_received)}
    {statistics.metrics?.['websocket-ingestion']?.events_per_minute}
    {/* etc. */}
  </div>
)}
```

**This section should either:**
1. Be removed from RAG Status Monitor, OR
2. Be renamed to "Data Ingestion Metrics" and displayed separately from RAG metrics

#### Issue 3: RAGStatusCard Shows Wrong Metrics

**File:** `services/health-dashboard/src/components/RAGStatusCard.tsx`

**Lines 209-268:** "Data Metrics" section shows websocket-ingestion statistics:
```typescript
{statistics && (
  <div className="mt-4 pt-4 border-t">
    <h4>Data Metrics</h4>
    {/* Shows websocket-ingestion statistics */}
    {formatNumber(statistics.metrics?.['websocket-ingestion']?.total_events_received)}
    {/* etc. */}
  </div>
)}
```

**Same issue as Issue 2.**

## Root Cause

1. **Misunderstanding of "RAG" terminology:**
   - "RAG Status Monitor" was implemented as "Red/Amber/Green" status monitor (system health)
   - But users expect "RAG" to mean "Retrieval-Augmented Generation" metrics
   - The implementation shows system health metrics (data ingestion) instead of RAG operation metrics

2. **Incomplete implementation:**
   - RAG metrics are fetched but never displayed
   - Data ingestion metrics were already available and displayed instead

3. **Missing UI sections:**
   - No "RAG Operations" section in RAGDetailsModal
   - No RAG metrics display in RAGStatusCard

## Recommendations

### Priority 1: Display Real RAG Metrics

#### 1.1 Add RAG Metrics Section to RAGDetailsModal

**File:** `services/health-dashboard/src/components/RAGDetailsModal.tsx`

**Add after line 275 (after Overall Status, before Data Metrics):**

```typescript
{/* RAG Operations Metrics Section */}
{ragMetrics && (
  <div className={`
    rounded-lg p-4 border-2
    ${darkMode ? 'bg-blue-900/30 border-blue-600' : 'bg-blue-50 border-blue-200'}
  `}>
    <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
      RAG Operations
    </h3>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {/* Total RAG Calls */}
      <div>
        <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Total RAG Calls
        </div>
        <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          {formatNumber(ragMetrics.total_calls)}
        </div>
      </div>

      {/* Store Calls */}
      <div>
        <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Store Operations
        </div>
        <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          {formatNumber(ragMetrics.store_calls)}
        </div>
      </div>

      {/* Retrieve Calls */}
      <div>
        <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Retrieve Operations
        </div>
        <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          {formatNumber(ragMetrics.retrieve_calls)}
        </div>
      </div>

      {/* Search Calls */}
      <div>
        <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Search Operations
        </div>
        <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          {formatNumber(ragMetrics.search_calls)}
        </div>
      </div>

      {/* Cache Hit Rate */}
      <div>
        <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Cache Hit Rate
        </div>
        <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          {(ragMetrics.cache_hit_rate * 100).toFixed(1)}%
        </div>
      </div>

      {/* Avg Latency */}
      <div>
        <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Avg Latency
        </div>
        <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          {ragMetrics.avg_latency_ms.toFixed(1)}ms
        </div>
      </div>

      {/* Error Rate */}
      <div>
        <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Error Rate
        </div>
        <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          {(ragMetrics.error_rate * 100).toFixed(2)}%
        </div>
      </div>

      {/* Success Score */}
      <div>
        <div className={`text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Avg Success Score
        </div>
        <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          {ragMetrics.avg_success_score.toFixed(2)}
        </div>
      </div>
    </div>
  </div>
)}

{ragMetricsLoading && (
  <div className="text-center py-4">
    <LoadingSpinner variant="dots" size="sm" color="default" />
    <span className={`ml-2 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
      Loading RAG metrics...
    </span>
  </div>
)}
```

#### 1.2 Update RAGStatusCard to Show RAG Metrics Summary

**File:** `services/health-dashboard/src/components/RAGStatusCard.tsx`

**Add RAG metrics fetch and display:**

1. Add state for RAG metrics (similar to RAGDetailsModal)
2. Fetch RAG metrics on mount
3. Replace or supplement "Data Metrics" section with RAG metrics summary

**Option A:** Replace "Data Metrics" with "RAG Metrics" (if RAG is active)
**Option B:** Show both (RAG Metrics when available, Data Metrics as fallback)

### Priority 2: Handle RAG Service Unavailability

#### 2.1 Show RAG Metrics Only When RAG Service is Active

**Check if RAG service is available:**
- If RAG service is unavailable (error fetching metrics), show a message: "RAG service not available" or "RAG metrics unavailable"
- Don't show data ingestion metrics as a fallback in RAG Status Monitor

#### 2.2 Improve Error Handling

**File:** `services/health-dashboard/src/components/RAGDetailsModal.tsx`

**Current (Line 146-147):**
```typescript
} catch (error) {
  console.error('Failed to fetch RAG service metrics:', error);
  // Don't set error state - just don't show the metrics
}
```

**Should be:**
```typescript
} catch (error) {
  console.error('Failed to fetch RAG service metrics:', error);
  // Set error state to show user-friendly message
  setRagMetricsError(true);
}
```

**Then display:**
```typescript
{ragMetricsError && (
  <div className={`p-4 rounded-lg ${darkMode ? 'bg-yellow-900/30 border-yellow-600' : 'bg-yellow-50 border-yellow-200'} border-2`}>
    <p className={`text-sm ${darkMode ? 'text-yellow-200' : 'text-yellow-800'}`}>
      ⚠️ RAG service metrics unavailable. The RAG service may not be running or configured.
    </p>
  </div>
)}
```

### Priority 3: Clarify Terminology

#### 3.1 Rename "Data Metrics" Section

**Option A:** Remove "Data Metrics" from RAG Status Monitor entirely  
**Option B:** Rename to "Data Ingestion Metrics" and display separately

#### 3.2 Update Documentation

- Clarify that "RAG Status Monitor" shows Red/Amber/Green system health indicators
- Add separate section for "RAG Operations Metrics" when RAG service is active
- Update README to explain the distinction

### Priority 4: Conditional Display Logic

#### 4.1 Only Show RAG Metrics When RAG is Active

**Implementation:**
```typescript
// Check if RAG service is available
const ragServiceAvailable = ragMetrics !== null && !ragMetricsError;

// Only show RAG metrics section if service is available
{ragServiceAvailable && (
  <RAGMetricsSection metrics={ragMetrics} />
)}

// Only show data ingestion metrics if RAG is not available
{!ragServiceAvailable && (
  <DataIngestionMetricsSection statistics={statistics} />
)}
```

#### 4.2 Update RAGStatusCard Logic

**Show RAG metrics summary when available:**
- If RAG metrics available: Show "RAG Operations" summary
- If RAG metrics unavailable: Show "System Status" (Red/Amber/Green) only

## Implementation Plan

### Phase 1: Add RAG Metrics Display (High Priority)

1. **Update RAGDetailsModal:**
   - Add RAG metrics display section
   - Improve error handling
   - Test with RAG service running/stopped

2. **Update RAGStatusCard:**
   - Add RAG metrics fetch
   - Display RAG metrics summary
   - Fallback to system status if RAG unavailable

**Estimated Time:** 2-3 hours

### Phase 2: Handle Edge Cases (Medium Priority)

1. **Error States:**
   - RAG service unavailable
   - Network errors
   - Invalid response format

2. **Loading States:**
   - Show loading spinner while fetching
   - Don't flash wrong data

**Estimated Time:** 1-2 hours

### Phase 3: Clean Up Terminology (Low Priority)

1. **Rename Sections:**
   - "Data Metrics" → "Data Ingestion Metrics" (or remove)
   - Add "RAG Operations Metrics" section

2. **Update Documentation:**
   - README updates
   - Component documentation

**Estimated Time:** 1 hour

## Testing Plan

### Test Cases

1. **RAG Service Available:**
   - ✅ RAG metrics displayed
   - ✅ Data ingestion metrics not shown (or shown separately)

2. **RAG Service Unavailable:**
   - ✅ Error message shown
   - ✅ No RAG metrics section displayed
   - ✅ System status (Red/Amber/Green) still works

3. **RAG Service Returns Zero Metrics:**
   - ✅ Shows "0" values correctly
   - ✅ No errors or crashes

4. **Network Error:**
   - ✅ Error message displayed
   - ✅ UI doesn't break

5. **Loading States:**
   - ✅ Loading spinner shown while fetching
   - ✅ Smooth transition when data arrives

## Files to Modify

1. **`services/health-dashboard/src/components/RAGDetailsModal.tsx`**
   - Add RAG metrics display section
   - Improve error handling

2. **`services/health-dashboard/src/components/RAGStatusCard.tsx`**
   - Add RAG metrics fetch
   - Update display logic

3. **`services/health-dashboard/src/types/rag.ts`** (if needed)
   - Add RAGServiceMetrics type if not already defined

## Questions to Resolve

1. **Should we remove "Data Metrics" section entirely from RAG Status Monitor?**
   - Option A: Remove entirely (RAG Status Monitor = RAG metrics only)
   - Option B: Keep but rename to "Data Ingestion Metrics" and show separately

2. **Should RAG Status Monitor show system health (Red/Amber/Green) AND RAG metrics?**
   - Current: Shows system health indicators
   - Proposed: Show both system health and RAG metrics

3. **What should happen when RAG service is unavailable?**
   - Option A: Show error message
   - Option B: Hide RAG Status Monitor entirely
   - Option C: Show system health only

## Playwright Validation Results

**Date:** January 16, 2026  
**Validation Method:** Browser inspection via Playwright  
**URL:** http://localhost:3000

### RAGStatusCard (Card View) - VERIFIED

**What's Displayed:**
- ✅ Overall Status: GREEN
- ✅ Component Breakdown: WebSocket (GREEN), Processing (GREEN), Storage (GREEN)
- ❌ **"Data Metrics" Section** shows:
  - Total Events: 2.71M
  - Throughput: 9.0 evt/min
  - Connections: 1
  - Last Refresh: -1s ago

**Issues Confirmed:**
- ❌ No RAG metrics displayed
- ❌ Shows data ingestion metrics (websocket-ingestion statistics) instead

### RAGDetailsModal (Modal View) - VERIFIED

**What's Displayed:**
- ✅ Overall Status: GREEN
- ✅ Component Details: WebSocket Connection, Event Processing, Data Storage (all GREEN)
- ❌ **"Data Metrics" Section** shows:
  - Total Events: 2.71M (Period: 1h)
  - Throughput: 9.0 evt/min
  - Connection Attempts: 1
  - Error Rate: 0.00%
  - Response Time: 0.0ms
  - Last Data Refresh: 7s ago
  - Data Source: services-fallback
- ❌ **"Data Breakdown" Section** shows:
  - Events Processed: 2.71M
  - Unique Entities: 0
  - Events per Entity: N/A
  - Events/Minute: 0.0

**Missing:**
- ❌ **NO "RAG Operations" section**
- ❌ **NO RAG metrics displayed** (total_calls, store_calls, retrieve_calls, search_calls, cache_hit_rate, etc.)

**Code Verification:**
- ✅ RAG metrics ARE being fetched (lines 136-154 in RAGDetailsModal.tsx)
- ✅ `ragMetrics` state is set when fetch succeeds
- ❌ `ragMetrics` state is NEVER used to render UI
- ❌ No UI section exists to display RAG metrics

### Console Errors

**Error Found:**
```
[ERROR] Connecting to 'http://localhost:8027/api/v1/metrics' violates the following Content Security...
[ERROR] Fetch API cannot load http://localhost:8027/api/v1/metrics. Refused to connect because it vi...
```

**Root Cause:**
- Browser is trying to access RAG service directly at `http://localhost:8027/api/v1/metrics`
- Should use nginx proxy at `/rag-service/api/v1/metrics` instead
- This may indicate RAG service is not accessible or CORS/CSP configuration issue

**Note:** The fetch failure is silent - no error is shown to the user in the UI.

### Screenshot Evidence

Screenshot saved: `rag-status-modal-current-state.png`
- Shows modal displaying only "Data Metrics" and "Data Breakdown" sections
- No "RAG Operations" or "RAG Metrics" section visible
- Confirms findings from code review

## Conclusion

**VALIDATED:** The current implementation displays data ingestion metrics (websocket-ingestion statistics) instead of RAG metrics (Retrieval-Augmented Generation operations). RAG metrics are being fetched but never displayed.

**Playwright Inspection Confirmed:**
1. ✅ RAGStatusCard shows "Data Metrics" with websocket-ingestion statistics (WRONG)
2. ✅ RAGDetailsModal shows "Data Metrics" and "Data Breakdown" sections (WRONG)
3. ✅ RAGDetailsModal has NO "RAG Operations" section (MISSING)
4. ✅ RAG metrics fetch may be failing silently (CORS/CSP error in console)

**Immediate Action Required:**
1. Add RAG metrics display section to RAGDetailsModal
2. Update RAGStatusCard to show RAG metrics summary
3. Improve error handling for RAG service unavailability
4. Fix CORS/CSP configuration or use correct proxy path for RAG metrics endpoint

**Long-term Considerations:**
1. Clarify terminology (RAG = Retrieval-Augmented Generation vs Red/Amber/Green)
2. Decide whether to show both system health and RAG metrics
3. Update documentation to explain the distinction
