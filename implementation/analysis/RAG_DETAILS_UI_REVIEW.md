# RAG Details UI Review and Recommendations

**Date:** January 15, 2026  
**Status:** Review Complete  
**Goal:** Filter RAG Details UI to show only RAG (Retrieval-Augmented Generation) metrics

## Executive Summary

The RAG Details Modal currently displays a mix of RAG-specific metrics and general data ingestion metrics. This review identifies which sections should be retained (RAG-only) and which should be removed (non-RAG metrics).

## Current RAG Details UI Structure

### ✅ RAG-Specific Metrics (KEEP)

**RAG Operations Section** (Lines 314-428 in `RAGDetailsModal.tsx`)
- **Total RAG Calls** - Total RAG operations
- **Store Operations** - Knowledge stored via RAG
- **Retrieve Operations** - Knowledge retrieved via RAG
- **Search Operations** - Semantic searches performed
- **Cache Hit Rate** - RAG cache performance (hits/misses)
- **Avg Latency** - Average RAG operation latency (min-max range)
- **Error Rate** - RAG operation error percentage
- **Avg Success Score** - RAG operation quality metric

**Source:** `RAGServiceMetrics` interface (from `/rag-service/api/v1/metrics` endpoint)

### ❌ Non-RAG Metrics (REMOVE)

#### 1. Data Metrics Section (Lines 430-529)
**Status:** REMOVE - These are websocket-ingestion metrics, not RAG metrics

**Metrics to Remove:**
- **Total Events** - From `websocket-ingestion` service (general event count)
- **Throughput** - Events per minute from ingestion pipeline
- **Connection Attempts** - WebSocket connection attempts
- **Error Rate** - General ingestion error rate (not RAG-specific)
- **Response Time** - General ingestion response time
- **Last Data Refresh** - Data refresh timestamp
- **Data Source** - Source identifier (e.g., "services-fallback")

**Source:** `Statistics` prop (from `/api/v1/statistics` endpoint)

#### 2. Data Breakdown Section (Lines 532-641)
**Status:** REMOVE - These are event statistics, not RAG metrics

**Metrics to Remove:**
- **Events Processed** - Total events processed (not RAG operations)
- **Unique Entities** - Distinct entities in events (not RAG-specific)
- **Events per Entity** - Average events per entity
- **Events/Minute** - Event processing rate
- **Event Types Breakdown** - Breakdown of event types (state_changed, etc.)

**Source:** `eventsStats` prop (from `/api/v1/events/stats` endpoint)

#### 3. Component Details Section (Lines 643-747)
**Status:** REMOVE or MODIFY - These are ingestion pipeline components, not RAG components

**Components to Remove:**
- **WebSocket Connection** - WebSocket connection health (not RAG-specific)
- **Event Processing** - Event processing pipeline health (not RAG-specific)
- **Data Storage** - Data storage health (general, not RAG-specific)

**Note:** These components track:
- Latency (WebSocket/Storage latency)
- Error Rate (general error rate)
- Throughput (events per minute)
- Queue Size (processing queue)
- Availability (component availability)
- Response Time (component response time)

**Source:** `RAGStatus.components` (Red/Amber/Green status for ingestion pipeline)

**Important:** The `RAGStatus` type is actually for the **ingestion pipeline** (Red/Amber/Green status system), not for RAG (Retrieval-Augmented Generation). This is a naming confusion.

### ⚠️ Overall Status Section (Lines 262-278)
**Status:** REVIEW - Currently based on ingestion pipeline RAGStatus

**Current Implementation:**
- Shows overall status (GREEN/AMBER/RED) from `ragStatus.overall`
- Based on ingestion pipeline components (websocket, processing, storage)
- Not derived from RAG metrics

**Recommendation Options:**

**Option A: Remove Overall Status**
- Remove entirely if it's not RAG-specific
- Simplest approach

**Option B: Replace with RAG-Specific Overall Status**
- Derive overall status from RAG metrics:
  - GREEN: Error rate < 1%, latency < 100ms, success score > 0.8
  - AMBER: Error rate 1-5%, latency 100-500ms, success score 0.6-0.8
  - RED: Error rate > 5%, latency > 500ms, success score < 0.6
- More complex but provides RAG-specific health indicator

**Option C: Keep as-is (if user wants high-level system health)**
- Keep if user wants to see overall system health alongside RAG metrics
- Add clarification that it's system health, not RAG health

## Available RAG Metrics (Complete List)

Based on `RAGServiceMetrics` interface and `/rag-service/api/v1/metrics` endpoint:

### Operation Counts
1. `total_calls` - Total RAG operations
2. `store_calls` - Store operations (knowledge stored)
3. `retrieve_calls` - Retrieve operations (knowledge retrieved)
4. `search_calls` - Search operations (semantic searches)

### Cache Metrics
5. `cache_hits` - Cache hits
6. `cache_misses` - Cache misses
7. `cache_hit_rate` - Cache hit rate (calculated: hits / (hits + misses))

### Performance Metrics
8. `avg_latency_ms` - Average latency in milliseconds
9. `min_latency_ms` - Minimum latency
10. `max_latency_ms` - Maximum latency
11. `total_latency_ms` - Total latency (sum of all operations)

### Error Metrics
12. `errors` - Total errors
13. `embedding_errors` - Embedding-specific errors
14. `storage_errors` - Storage-specific errors
15. `error_rate` - Error rate (calculated: errors / total_calls)

### Quality Metrics
16. `avg_success_score` - Average success score (0.0-1.0)
17. `total_success_scores` - Number of success scores recorded

## Recommendations Summary

### ✅ KEEP (RAG-Specific)

1. **RAG Operations Section** (Lines 314-428)
   - All 8 metrics are RAG-specific
   - Source: `ragMetrics` from `/rag-service/api/v1/metrics`
   - Status: ✅ Keep as-is

2. **Header** (Lines 223-258)
   - Title: "RAG Status Details"
   - Subtitle: "Component Health Breakdown" (consider renaming to "RAG Metrics")
   - Status: ✅ Keep (consider subtitle update)

3. **Footer** (Lines 750-767)
   - Close button
   - Status: ✅ Keep

### ❌ REMOVE (Non-RAG Metrics)

1. **Data Metrics Section** (Lines 430-529)
   - **Action:** Remove entire section
   - **Reason:** Websocket-ingestion metrics, not RAG metrics
   - **Impact:** Removes 6 metrics (Total Events, Throughput, Connection Attempts, Error Rate, Response Time, Last Data Refresh)

2. **Data Breakdown Section** (Lines 532-641)
   - **Action:** Remove entire section
   - **Reason:** Event statistics, not RAG metrics
   - **Impact:** Removes 4 metrics (Events Processed, Unique Entities, Events per Entity, Events/Minute) and Event Types Breakdown

3. **Component Details Section** (Lines 643-747)
   - **Action:** Remove entire section
   - **Reason:** Ingestion pipeline components (websocket, processing, storage), not RAG components
   - **Impact:** Removes 3 component cards with their metrics

### ⚠️ REVIEW (Overall Status)

**Current:** Shows overall status from ingestion pipeline RAGStatus

**Recommendations:**
- **Option A (Recommended):** Remove Overall Status section
  - Simplest approach
  - RAG Operations section provides all necessary metrics
  - Avoids confusion with ingestion pipeline status

- **Option B:** Replace with RAG-specific overall status
  - Derive from RAG metrics (error rate, latency, success score)
  - Provides RAG health indicator
  - Requires implementation of RAG health calculation logic

- **Option C:** Keep with clarification
  - Add label: "System Health" (not "RAG Health")
  - Keep if user wants system context alongside RAG metrics

## Implementation Plan

### Phase 1: Remove Non-RAG Sections (Simple)
1. Remove Data Metrics Section (Lines 430-529)
2. Remove Data Breakdown Section (Lines 532-641)
3. Remove Component Details Section (Lines 643-747)
4. Remove `statistics` and `eventsStats` props if no longer needed

### Phase 2: Review Overall Status (Decision Required)
1. Decide on Option A, B, or C for Overall Status
2. If Option A: Remove Overall Status section (Lines 262-278)
3. If Option B: Implement RAG-specific health calculation
4. If Option C: Add clarification label

### Phase 3: Optional Enhancements
1. Consider adding more RAG metrics if available:
   - Embedding errors breakdown
   - Storage errors breakdown
   - Success score distribution
   - Time-based metrics (calls per hour, etc.)
2. Update subtitle from "Component Health Breakdown" to "RAG Metrics" or "RAG Operations Metrics"
3. Add refresh button for manual metrics refresh
4. Add time range selector (1h, 6h, 24h) if time-based metrics are added

## Code Changes Required

### File: `services/health-dashboard/src/components/RAGDetailsModal.tsx`

**Remove:**
- Lines 430-529: Data Metrics Section
- Lines 532-641: Data Breakdown Section
- Lines 643-747: Component Details Section
- Lines 262-278: Overall Status Section (if Option A chosen)

**Update Props (if removing sections):**
```typescript
export interface RAGDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  ragStatus: RAGStatus | null; // May not be needed if Overall Status removed
  // statistics?: Statistics | null; // REMOVE - no longer needed
  // eventsStats?: any | null; // REMOVE - no longer needed
  darkMode: boolean;
}
```

**Update Component Usage:**
- Remove `statistics` prop from `RAGDetailsModal` usage in `OverviewTab.tsx`
- Remove `eventsStats` prop from `RAGDetailsModal` usage
- Remove `ragStatus` prop if Overall Status is removed (but keep for now if Option C chosen)

## Expected Result

After implementation, the RAG Details Modal will show:

1. **Header** - "RAG Status Details" with close button
2. **Overall Status** (if kept) - System health indicator (with clarification if Option C)
3. **RAG Operations** - 8 RAG-specific metrics:
   - Total RAG Calls
   - Store Operations
   - Retrieve Operations
   - Search Operations
   - Cache Hit Rate
   - Avg Latency
   - Error Rate
   - Avg Success Score
4. **Footer** - Close button

**Total Metrics Displayed:** 8 RAG-specific metrics (down from ~20+ mixed metrics)

## Benefits

1. **Clarity** - UI focuses exclusively on RAG metrics
2. **Relevance** - No confusion with ingestion pipeline metrics
3. **Simplicity** - Cleaner, more focused interface
4. **Accuracy** - Metrics match the "RAG Status Details" title
5. **Maintainability** - Fewer dependencies (no statistics/eventsStats props)

## Questions for Stakeholder

1. **Overall Status:** Should we remove it (Option A), replace with RAG-specific status (Option B), or keep with clarification (Option C)?

2. **Additional RAG Metrics:** Are there other RAG metrics we should display that aren't currently shown?

3. **Time-based Metrics:** Should we add time-based metrics (calls per hour, latency trends, etc.)?

4. **Component Health:** If we remove Component Details, should we add RAG-specific component health (e.g., Embedding Service, Storage Service, Cache Service)?

## Related Files

- `services/health-dashboard/src/components/RAGDetailsModal.tsx` - Main component
- `services/health-dashboard/src/components/OverviewTab.tsx` - Component usage
- `services/health-dashboard/src/services/api.ts` - RAG API client
- `services/rag-service/src/utils/metrics.py` - RAG metrics implementation
- `services/rag-service/src/api/metrics_router.py` - RAG metrics API endpoint
