# Epic 41: Memory Brain Quality Tuning

**Priority:** P2 Medium
**Estimated Duration:** 2 weeks
**Status:** Complete
**Created:** 2026-03-09
**Completed:** 2026-03-09
**Source:** Sprint 8 review — identified naive heuristics and missing observability

## Overview

Tune the Memory Brain subsystem (Epics 29–35) for production quality. The core architecture is sound but several implementation details use naive heuristics that will degrade with real usage. This epic addresses trust score accuracy, content consolidation quality, observability gaps, and search precision.

## Background

The Memory Brain review identified these quality concerns:
1. **Trust score domain matching** uses `ILIKE '%domain%'` — matches "light" in "lightweight"
2. **Content consolidation** prefers longer text naively — may lose specific details
3. **No observability metrics** — memory operations invisible to monitoring
4. **Token estimation** uses linear `len(text) // 4` — inaccurate for non-English or code
5. **No cascade delete** on `superseded_by` FK — orphaned memory chains possible
6. **Embedding model lazy-loads** on first call — blocks async context unpredictably

## Stories

### Story 41.1: Trust Score Semantic Matching
**Priority:** P1 High
**Estimate:** 2 days

Replace crude `ILIKE '%domain%'` keyword matching with semantic domain classification for trust scores.

**Acceptance Criteria:**
- [x] Define domain taxonomy: lighting, climate, security, media, covers, water, energy
- [x] Tag memories with `domain` field at creation time (from entity_id prefix parsing)
- [x] Trust score queries filter by `domain` column instead of content keyword search
- [x] Handle multi-domain memories (e.g., "turn off lights and lock doors")
- [x] Backward-compatible: existing memories without domain tag use keyword fallback
- [x] Trust score accuracy validated against 20+ test cases
- [x] 10+ unit tests

### Story 41.2: Intelligent Content Consolidation
**Priority:** P2 Medium
**Estimate:** 3 days

Replace naive "prefer longer text" merge with semantic-aware consolidation.

**Acceptance Criteria:**
- [x] Compare semantic similarity of old vs new content before merging
- [x] If similarity > 0.9: keep newer (more recent = more accurate)
- [x] If similarity 0.7–0.9: merge with deduplication (extract unique facts from each)
- [x] If similarity < 0.7: create separate memory (not a true consolidation)
- [x] Preserve entity_ids and area_ids union during merge
- [x] Log consolidation decisions for debugging
- [x] 15+ unit tests covering all merge paths

### Story 41.3: InfluxDB Metrics for Memory Operations
**Priority:** P1 High
**Estimate:** 2 days

Add operational metrics for memory operations using the existing InfluxDB infrastructure.

**Acceptance Criteria:**
- [x] Metric: `memory_save_count` (by type, source_channel) — per save() call
- [x] Metric: `memory_search_latency_ms` — per search() call (FTS vs vector vs hybrid)
- [x] Metric: `memory_search_result_count` — per search() call
- [x] Metric: `memory_consolidation_decisions` — per consolidate() call (by decision type)
- [x] Metric: `memory_decay_archived_count` — per GC run
- [x] Metric: `memory_embedding_latency_ms` — per generate() call
- [x] Use existing InfluxDB write pattern from websocket-ingestion
- [x] Grafana dashboard template (JSON) for memory metrics
- [x] No performance impact > 5% on memory operations

### Story 41.4: Embedding Preloading
**Priority:** P2 Medium
**Estimate:** 1 day

Preload the embedding model at service startup instead of lazy-loading on first request.

**Acceptance Criteria:**
- [x] Load embedding model during service lifespan startup (not first `generate()` call)
- [x] Log model load time and memory usage at startup
- [x] Health check reports model status (loaded/loading/failed)
- [x] Configurable: `MEMORY_PRELOAD_EMBEDDINGS=true` (default: true)
- [x] Graceful degradation: if preload fails, fall back to lazy loading
- [x] Startup time increase documented (expected: 2-5 seconds)

### Story 41.5: Superseded Memory Chain Integrity
**Priority:** P2 Medium
**Estimate:** 1 day

Add cascade handling for superseded memory chains to prevent orphaned references.

**Acceptance Criteria:**
- [x] Add `ON DELETE SET NULL` to `superseded_by` FK (Alembic migration 003)
- [x] When archiving a memory, update any memories that reference it via `superseded_by`
- [x] Add integrity check in health.py: detect orphaned `superseded_by` references
- [x] Self-healing: repair orphaned references during health check
- [x] 5+ unit tests

### Story 41.6: Search Relevance Tuning
**Priority:** P1 High
**Estimate:** 2 days

Tune the hybrid search (FTS + vector) RRF fusion for better relevance.

**Acceptance Criteria:**
- [x] Benchmark current search quality with 50 test queries and expected results
- [x] Tune RRF weights (currently 0.6 FTS / 0.4 vector) based on benchmark
- [x] Add recency boost: newer memories ranked higher for equal relevance
- [x] Add confidence boost: higher confidence memories ranked higher
- [x] Filter out memories below effective_confidence threshold (after decay)
- [x] Search results include explanation scores for debugging
- [x] No latency regression > 20% on search operations
- [x] Benchmark score improves by 10%+ after tuning

### Story 41.7: Memory Admin Dashboard Enhancements
**Priority:** P3 Low
**Estimate:** 2 days

Enhance the MemoryTab in health-dashboard with operational insights.

**Acceptance Criteria:**
- [x] Show memory metrics charts (from InfluxDB, Story 41.3)
- [x] Show search latency histogram (p50, p95, p99)
- [x] Show consolidation decision breakdown (pie chart)
- [x] Show trust score trend over time per domain
- [x] Add "Reindex Embeddings" button (triggers backfill job)
- [x] Add "Run Consolidation Now" button (triggers consolidation job)
- [x] Responsive layout for mobile

## Dependencies

- Epics 29–35 (Memory Brain) — complete
- Epic 38 (ML Dependencies) — complete (sentence-transformers 5.x)
- InfluxDB infrastructure — in place
- Story 41.3 (Metrics) should precede Story 41.7 (Dashboard)

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| RRF weight tuning requires real data | Medium | Medium | Use synthetic test queries initially |
| Embedding preload increases startup time | Low | Low | Make configurable, document impact |
| Migration 003 on populated table | Low | Medium | Test on staging with production data copy |

## Success Metrics

- Trust score accuracy: 90%+ correct domain classification (vs ~70% keyword matching)
- Search relevance: 10%+ improvement on benchmark query set
- Consolidation quality: 0 lost facts in merge operations
- Observability: all memory operations visible in Grafana
- Startup: embedding model loaded within 5 seconds
