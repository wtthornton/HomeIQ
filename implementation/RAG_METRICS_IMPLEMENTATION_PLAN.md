# RAG Metrics Implementation Plan

**Date:** January 12, 2026  
**Status:** Planning  
**Goal:** Track and display RAG (Retrieval-Augmented Generation) metrics in the RAG Status Monitor

## Current Situation

### What We Have Now
- **RAG Status Monitor** displays database/ingestion metrics (events, throughput, connections)
- These are NOT RAG (Retrieval-Augmented Generation) metrics
- RAG system exists in archived services (2025-q4/ai-automation-service)
- OpenVINO service is active and provides embeddings/reranking that RAG uses
- **NO metrics endpoint exists** for RAG calls/queries

### What User Wants
- Track **RAG (Retrieval-Augmented Generation) calls/queries**
- Display RAG metrics in the "RAG Status Monitor"
- Metrics should show:
  - How many times RAG was called
  - RAG query counts
  - Embedding generation counts
  - Retrieval counts
  - Similarity search counts

## RAG System Architecture

### Components
1. **RAGClient** (archived: `services/archive/2025-q4/ai-automation-service/src/services/rag/client.py`)
   - Uses OpenVINO service for embeddings
   - Stores/retrieves semantic knowledge
   - Methods: `store()`, `retrieve()`, `retrieve_hybrid()`, `_get_embedding()`

2. **OpenVINO Service** (active: `services/openvino-service`)
   - Provides embeddings via `/embeddings` endpoint
   - Provides reranking via `/rerank` endpoint
   - Currently has NO metrics endpoint

3. **Usage Points**
   - Clarification detection (archived services)
   - Query similarity search
   - Knowledge base retrieval

## Metrics to Track

### Primary Metrics
1. **RAG Calls/Queries**
   - Total RAG retrieval calls
   - RAG store calls
   - Calls per time period (1h, 6h, 24h)

2. **Embedding Operations**
   - Total embeddings generated
   - Embedding cache hits/misses
   - Embedding generation time (avg)

3. **Retrieval Operations**
   - Total retrieval queries
   - Hybrid retrieval queries (dense + sparse)
   - Average similarity scores
   - Top-K results returned

4. **Knowledge Base Stats**
   - Total knowledge entries stored
   - Knowledge types breakdown
   - Storage/retrieval ratio

### Secondary Metrics (OpenVINO Service)
1. **Embedding Endpoint Calls**
   - `/embeddings` request count
   - Average processing time
   - Error rate

2. **Reranking Endpoint Calls**
   - `/rerank` request count
   - Average processing time
   - Error rate

## Implementation Options

### Option 1: Track OpenVINO Service Calls (Proxy Metrics)
**Pros:**
- OpenVINO service is active
- Can add metrics middleware/logging easily
- Provides visibility into RAG usage (embeddings/reranking)

**Cons:**
- Not all OpenVINO calls are RAG-related
- Doesn't track RAGClient.store() calls
- Doesn't track retrieval queries

**Implementation:**
1. Add metrics tracking to OpenVINO service
2. Create `/metrics` or `/stats` endpoint
3. Track: embedding calls, rerank calls, processing times
4. Update UI to fetch from OpenVINO service

### Option 2: Create RAG Metrics Service (If RAG is Active)
**Pros:**
- Accurate RAG-specific metrics
- Tracks all RAG operations (store, retrieve, hybrid)
- Can track knowledge base stats

**Cons:**
- RAG is in archived services (not actively used?)
- Requires migrating RAG to active services
- More complex implementation

**Implementation:**
1. Add metrics tracking to RAGClient
2. Store metrics in database or memory
3. Create metrics endpoint (new service or add to existing)
4. Update UI to fetch RAG metrics

### Option 3: Hybrid Approach (Recommended)
**Pros:**
- Track OpenVINO calls as immediate solution
- Plan for RAG metrics when RAG is active
- Provides visibility now, extensible later

**Cons:**
- Not 100% accurate for RAG-only metrics
- Requires two metrics sources

**Implementation:**
1. **Phase 1:** Add OpenVINO metrics endpoint
   - Track embedding/rerank calls
   - Display in RAG Status Monitor as "RAG Operations (via OpenVINO)"
   
2. **Phase 2:** Add RAG metrics when RAG is active
   - Track RAGClient operations
   - Display combined metrics

## Recommended Implementation (Option 3 - Phase 1)

### Step 1: Add Metrics to OpenVINO Service
**File:** `services/openvino-service/src/main.py`

Add:
- Request counter for `/embeddings`
- Request counter for `/rerank`
- Processing time tracking
- Error tracking
- Metrics endpoint: `GET /metrics` or `GET /stats`

### Step 2: Update Health Dashboard API Client
**File:** `services/health-dashboard/src/services/api.ts`

Add:
- `getOpenVINOMetrics()` method
- Fetch from `http://openvino-service:8019/metrics`

### Step 3: Update RAG Status Monitor UI
**Files:**
- `services/health-dashboard/src/components/RAGStatusCard.tsx`
- `services/health-dashboard/src/components/RAGDetailsModal.tsx`
- `services/health-dashboard/src/components/tabs/OverviewTab.tsx`

Changes:
- Fetch OpenVINO metrics instead of database stats
- Display RAG metrics (embedding calls, rerank calls, processing times)
- Rename "Data Metrics" to "RAG Metrics" or "RAG Operations"

### Step 4: Update Types
**File:** `services/health-dashboard/src/types/rag.ts` (or create new types file)

Add:
- `RAGMetrics` interface
- `OpenVINOMetrics` interface

## Metrics Display Format

### RAG Status Card (Summary)
- **Total RAG Calls:** 1,234 (1h)
- **Embeddings Generated:** 567
- **Rerank Operations:** 89
- **Avg Processing Time:** 45ms

### RAG Details Modal (Detailed)
- **RAG Operations**
  - Total Calls: 1,234
  - Period: 1h
  - Last Refresh: 2s ago
  
- **Embedding Operations**
  - Total: 567
  - Avg Time: 42ms
  - Cache Hit Rate: 75%
  
- **Reranking Operations**
  - Total: 89
  - Avg Time: 120ms
  - Avg Candidates: 10
  
- **Error Rate**
  - Embeddings: 0.5%
  - Reranking: 1.2%

## Next Steps

1. **Confirm RAG Usage:** Is RAG currently active or only in archived services?
2. **Choose Implementation Option:** Option 3 (Hybrid) recommended
3. **Implement OpenVINO Metrics:** Add metrics tracking and endpoint
4. **Update UI:** Fetch and display RAG metrics
5. **Test:** Verify metrics are accurate and displayed correctly

## Questions to Resolve

1. Is RAG (Retrieval-Augmented Generation) currently active in production?
2. Should we track OpenVINO calls as RAG metrics (proxy) or wait for RAG metrics?
3. What time period should metrics cover? (1h, 6h, 24h)
4. Should we rename "RAG Status Monitor" to avoid confusion with Red/Amber/Green?
