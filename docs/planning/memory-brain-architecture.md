# HomeIQ Memory Brain — Vision & Architecture

**Status:** Implemented
**Created:** 2026-03-04
**Implemented:** 2026-03-06
**Inspired by:** [Sapphire](https://github.com/ddxfish/sapphire.git) memory system, [Mem0](https://mem0.ai/research) consolidation architecture, 2026 AI agent memory best practices

## Problem Statement

HomeIQ has ~58 production-profile containers (62 Compose definitions) generating rich intelligence — pattern detection (21 synergy detectors), energy correlations, activity recognition, device health scoring, blueprint matching, and proactive suggestions. Each subsystem produces insights that are **consumed once and forgotten**.

**The core gap:** HomeIQ has a nervous system without a brain.

| What exists | What's missing |
|-------------|----------------|
| InfluxDB captures every sensor event | No distillation of what events *mean* over time |
| Pattern service detects co-occurrence | Patterns don't remember being rejected or outgrown |
| Synergy detection finds device relationships | No memory of which synergies users actually deployed |
| Energy correlator measures power deltas | No longitudinal learning ("space heater always gets overridden") |
| Activity recognition labels current state | No routine memory ("weekday vs weekend schedules") |
| User approves/rejects automations | Feedback doesn't propagate back to future suggestions |
| Users manually override automations | Overrides aren't recognized as implicit feedback |

**Every manual override is feedback. Every ignored suggestion is feedback. Every automation that runs for months is feedback. Right now, that feedback evaporates.**

## What Memory Is (and Is Not)

### Memory IS
- **Distilled insights** from raw data — not another event log
- **Searchable context** injected into AI prompts before generating output
- **Consolidated facts** that cross a stability threshold (not single events)
- **Living knowledge** with confidence decay and contradiction detection

### Memory IS NOT
- A replacement for InfluxDB time-series storage
- Real-time event processing (one light switch flip is not a memory)
- Unbounded accumulation (memories decay, get garbage-collected)
- A single monolithic store (different memory types serve different purposes)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        MEMORY BRAIN                             │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  EXPLICIT     │  │  IMPLICIT     │  │  SYNTHESIZED          │  │
│  │  (user-driven)│  │  (behavior)   │  │  (system-derived)     │  │
│  │              │  │              │  │                      │  │
│  │ Chat context │  │ Overrides    │  │ Pattern consolidation│  │
│  │ Approvals    │  │ Usage drift  │  │ Correlation insights │  │
│  │ Rejections   │  │ Abandonment  │  │ Routine detection    │  │
│  │ Stated prefs │  │ Engagement   │  │ Seasonal shifts      │  │
│  │ Feedback     │  │ Manual actions│ │ Trust scores         │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│         └─────────────────┼──────────────────────┘              │
│                           ▼                                     │
│              ┌─────────────────────────┐                       │
│              │   PostgreSQL + pgvector  │                       │
│              │   ─────────────────────  │                       │
│              │   memories table         │                       │
│              │   + FTS index            │                       │
│              │   + HNSW vector index    │                       │
│              │   + confidence/decay     │                       │
│              └────────────┬────────────┘                        │
│                           │                                     │
│              ┌────────────▼────────────┐                       │
│              │   HYBRID SEARCH (RRF)   │                       │
│              │   FTS → Vector → LIKE   │                       │
│              │   Reciprocal Rank Fusion │                       │
│              └────────────┬────────────┘                        │
│                           │                                     │
│              ┌────────────▼────────────┐                       │
│              │   MEMORY API            │                       │
│              │   (homeiq-memory lib)   │                       │
│              │   save / search / decay │                       │
│              └─────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
         ┌──────────┐ ┌──────────┐ ┌──────────┐
         │ Pattern  │ │ Proactive│ │ Ask AI   │
         │ Service  │ │ Agent    │ │ (ha-ai-  │
         │          │ │          │ │  agent)  │
         │ Queries  │ │ Queries  │ │ Queries  │
         │ memory   │ │ memory   │ │ memory   │
         │ before   │ │ before   │ │ before   │
         │ detecting│ │ suggesting│ │ responding│
         └──────────┘ └──────────┘ └──────────┘
              ... and every other AI service
```

## Memory Taxonomy

Five memory types, each serving a distinct purpose:

### 1. Behavioral Memory (`behavioral`)
**Source:** Implicit — device usage patterns, manual actions
**Consolidation:** After 10+ occurrences over 2+ weeks
**Decay:** 90-day half-life if pattern stops recurring
**Example:** "User turns on office lights at 8:45 AM on weekdays"

### 2. Preference Memory (`preference`)
**Source:** Explicit (chat) + Implicit (overrides, modifications)
**Consolidation:** Immediately from chat; after 3+ overrides from behavior
**Decay:** 180-day half-life (preferences change slowly)
**Example:** "User prefers 72F in evening, overrides 68F automation target consistently"

### 3. Boundary Memory (`boundary`)
**Source:** Explicit rejections, stated constraints
**Consolidation:** Immediately on rejection; reinforced by repeated rejection
**Decay:** Never auto-decays (boundaries are explicit user choices)
**Example:** "User does not want automations controlling garage door or locks"

### 4. Outcome Memory (`outcome`)
**Source:** PostActionVerifier results, automation run history
**Consolidation:** After automation runs 7+ days with/without issues
**Decay:** 120-day half-life
**Example:** "Sunset lighting automation deployed 2025-12-15, zero overrides in 3 months"

### 5. Routine Memory (`routine`)
**Source:** Synthesized from activity recognition + device patterns
**Consolidation:** Weekly consolidation job compares current vs. stored routines
**Decay:** Replaced (not decayed) when routine shifts detected
**Example:** "Weekday: wake 6:30, leave 7:45, return 5:30, sleep 10:30"

## Three Input Channels

### Channel 1: Explicit (User-Driven)
- Chat messages expressing preferences: "I don't like bright lights in the evening"
- Approval/rejection of suggestions with reasons
- Ratings and feedback on automations
- Direct statements: "Remember that I work from home on Fridays"

**Capture point:** `ha-ai-agent-service` conversation handler
**Mechanism:** LLM extracts memory-worthy facts from conversation (Mem0-style extraction)

### Channel 2: Implicit (Behavioral)
- Manual overrides within N minutes of an automation running
- Automation disablement/abandonment (enabled but user manually contradicts)
- Device usage patterns that diverge from automations
- Suggestion engagement: viewed vs. ignored vs. acted upon

**Capture point:** `websocket-ingestion` state events + `data-api` automation tracking
**Mechanism:** Consolidation job compares automation intent vs. actual device state

### Channel 3: Synthesized (System-Derived)
- Pattern service consolidates stable patterns into memories
- Energy correlator distills longitudinal efficiency insights
- Activity recognition consolidates routine baselines
- Trust scores computed from approval/rejection/override ratios

**Capture point:** Periodic consolidation job (every 6 hours)
**Mechanism:** Queries InfluxDB for recent patterns, compares against existing memories, applies Mem0-style consolidation (merge/update/skip/delete)

## Storage Design

### PostgreSQL Schema (in `memory` schema)

```sql
CREATE TABLE memory.memories (
    id              BIGSERIAL PRIMARY KEY,
    content         TEXT NOT NULL,           -- max 1024 chars
    memory_type     VARCHAR(20) NOT NULL,    -- behavioral/preference/boundary/outcome/routine
    confidence      FLOAT NOT NULL DEFAULT 0.5,
    source_channel  VARCHAR(20) NOT NULL,    -- explicit/implicit/synthesized
    source_service  VARCHAR(50),             -- which service created it
    entity_ids      TEXT[],                  -- related HA entity IDs
    area_ids        TEXT[],                  -- related HA areas
    domain          VARCHAR(30),             -- semantic domain (lighting, climate, security, etc.)
    tags            TEXT[],                  -- free-form tags for filtering
    embedding       vector(384),             -- pgvector embedding (384 for default all-MiniLM-L6-v2)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed   TIMESTAMPTZ,             -- for decay calculation
    access_count    INTEGER DEFAULT 0,       -- retrieval frequency
    superseded_by   BIGINT REFERENCES memory.memories(id),
    metadata        JSONB                    -- flexible extra data
);

-- Full-text search index
CREATE INDEX idx_memories_fts ON memory.memories
    USING gin(to_tsvector('english', content));

-- Vector similarity index (HNSW for fast ANN)
CREATE INDEX idx_memories_embedding ON memory.memories
    USING hnsw (embedding vector_cosine_ops);

-- Type + confidence for filtered queries
CREATE INDEX idx_memories_type_conf ON memory.memories (memory_type, confidence DESC);

-- Entity lookup
CREATE INDEX idx_memories_entities ON memory.memories USING gin(entity_ids);

-- Domain classification
CREATE INDEX idx_memories_domain ON memory.memories (domain);
```

### Hybrid Search (Reciprocal Rank Fusion)

Following [ParadeDB's RRF pattern](https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual) and Sapphire's 4-stage cascading search:

```sql
-- Stage 1: FTS match (keyword precision)
WITH fts AS (
    SELECT id, ROW_NUMBER() OVER (
        ORDER BY ts_rank(to_tsvector('english', content), plainto_tsquery($1)) DESC
    ) AS r
    FROM memory.memories
    WHERE to_tsvector('english', content) @@ plainto_tsquery($1)
      AND confidence > 0.3
    LIMIT 20
),
-- Stage 2: Vector similarity (semantic meaning)
semantic AS (
    SELECT id, ROW_NUMBER() OVER (
        ORDER BY embedding <=> $2  -- query embedding
    ) AS r
    FROM memory.memories
    WHERE confidence > 0.3
    LIMIT 20
),
-- Stage 3: RRF fusion
rrf AS (
    SELECT id, 0.6 / (60 + r) AS s FROM fts       -- 60% weight to keywords
    UNION ALL
    SELECT id, 0.4 / (60 + r) AS s FROM semantic   -- 40% weight to semantics
)
SELECT m.id, m.content, m.memory_type, m.confidence, m.entity_ids,
       m.area_ids, m.tags, m.created_at, SUM(rrf.s) AS relevance_score
FROM rrf JOIN memory.memories m USING (id)
GROUP BY m.id, m.content, m.memory_type, m.confidence, m.entity_ids,
         m.area_ids, m.tags, m.created_at
ORDER BY relevance_score DESC
LIMIT 10;
```

## Confidence & Decay Model

Inspired by [Mem0's consolidation architecture](https://mem0.ai/research) and adapted for IoT behavioral data:

### Confidence Sources
- **Initial:** 0.5 (new memory)
- **Reinforced:** +0.1 per confirming observation (cap at 0.95)
- **Accessed:** +0.02 per retrieval (memory was useful enough to surface)
- **Contradicted:** Set to 0.1, link `superseded_by` to new memory

### Decay Function
```python
def effective_confidence(memory) -> float:
    """Exponential decay based on memory type half-life."""
    half_lives = {
        "behavioral": 90,   # days
        "preference": 180,
        "boundary": None,   # never decays
        "outcome": 120,
        "routine": None,    # replaced, not decayed
    }
    half_life = half_lives[memory.memory_type]
    if half_life is None:
        return memory.confidence

    days_since_update = (now() - memory.updated_at).days
    decay = 0.5 ** (days_since_update / half_life)
    return memory.confidence * decay
```

### Garbage Collection
- Weekly job: archive memories where `effective_confidence < 0.15`
- Archived memories move to `memory.memories_archive` (queryable but excluded from search)
- Contradiction detection: compare active memories for logical conflicts

## Consolidation Process

Following [Mem0's extract-consolidate-retrieve pattern](https://arxiv.org/pdf/2504.19413):

### 1. Extract
New candidate memories arrive from the three input channels. Each candidate includes:
- Raw content text
- Source channel and service
- Related entity/area IDs
- Initial confidence

### 2. Consolidate
For each candidate, retrieve top-5 semantically similar existing memories:

| Scenario | Action |
|----------|--------|
| No similar memories exist | **Insert** as new memory |
| Similar memory with same meaning | **Reinforce** — bump confidence, update timestamp |
| Similar memory with updated info | **Update** — merge content, keep higher confidence |
| Contradicts existing memory | **Supersede** — mark old as superseded, insert new |
| Duplicate of recent memory | **Skip** — no action needed |

### 3. Retrieve
Every AI service queries memory before generating output:
- `ha-ai-agent-service`: "What do I know about this user's preferences for [topic]?"
- `proactive-agent-service`: "What outcomes have similar suggestions had?"
- `pattern-service`: "Has this pattern been rejected before?"
- `suggestion-service`: "What boundaries exist for these entity types?"
- `blueprint-suggestion-service`: "What automation style does this user prefer?"

## Integration Contract

Every AI-facing service MUST query the memory API before generating suggestions, responses, or recommendations. The memory context is injected as a structured block in the LLM prompt:

```
[Memory Context]
- User prefers 72F evening temperature (preference, confidence: 0.85)
- Motion-based bathroom lights rejected — cats trigger sensors (boundary, confidence: 0.95)
- Weekday routine: wake 6:30, leave 7:45, return 5:30 (routine, confidence: 0.80)
- Sunset lighting automation: running 3 months, zero overrides (outcome, confidence: 0.90)
- User engages with energy suggestions but ignores climate ones (behavioral, confidence: 0.70)
```

## Shared Library: `homeiq-memory`

Shared library under `libs/homeiq-memory/` (v1.0.0) providing:
- `MemoryClient` — async client for CRUD + search operations (with fallback methods)
- `MemoryConsolidator` — Mem0-style extract/consolidate/supersede logic with contradiction detection
- `MemorySearch` — hybrid RRF search (FTS 60% + pgvector 40%) with graceful degradation
- `EmbeddingGenerator` — async sentence-transformer encoding (all-MiniLM-L6-v2 384-dim or nomic-embed-text-v1.5 768-dim)
- `MemoryInjector` — formats memories for LLM prompt injection with token budgeting
- `MemoryHealthCheck` — health monitoring with auto-repair (FTS reindex, orphaned chain fix)
- Confidence decay functions: `effective_confidence`, `reinforce`, `contradict`, `should_archive`
- Domain taxonomy: auto-classifies HA entity prefixes to semantic domains
- Callback-based metrics interface for InfluxDB/Prometheus integration

See [libs/homeiq-memory/README.md](../../libs/homeiq-memory/README.md) for full API reference and usage examples.

All services install `homeiq-memory` the same way as existing shared libs:
```dockerfile
COPY libs/ /tmp/libs/
RUN pip install /tmp/libs/homeiq-memory/
```

## Key Design Decisions

### Why PostgreSQL + pgvector (not separate vector DB)
HomeIQ already uses PostgreSQL 17 for all metadata. Adding pgvector keeps the operational footprint small — no new infrastructure. For HomeIQ's scale (thousands to low millions of memories), pgvector with HNSW indexing provides sub-50ms search latency.

Reference: [pgvector hybrid search best practices](https://jkatz05.com/post/postgres/hybrid-search-postgres-pgvector/)

### Why Not Sapphire's SQLite Approach
Sapphire uses per-concern SQLite databases. HomeIQ already standardized on PostgreSQL with `DatabaseManager`. SQLite would be a regression and break the `homeiq-data` library contract.

### Why 1024-char Limit (Not Sapphire's 512)
HomeIQ memories need to reference entity IDs, area names, and automation context. 512 chars is too restrictive. 1024 provides enough room without encouraging verbose memories.

### Why Consolidation Thresholds
A single light switch flip is noise. A pattern needs 10+ occurrences over 2+ weeks to become a behavioral memory. This prevents memory bloat and ensures only stable patterns are retained. Thresholds are configurable per memory type.

### Why Boundary Memories Never Decay
When a user explicitly says "never automate my garage door," that's a hard constraint. Auto-decaying it would violate user trust. Boundaries can only be removed by explicit user action.

## References

- [Mem0: Production-Ready AI Agents with Scalable Long-Term Memory](https://mem0.ai/research) — 26% accuracy uplift via extract-consolidate-retrieve
- [Mem0 vs Zep vs Claude-Mem: Best AI Agent Memory 2026](https://serenitiesai.com/articles/ai-agent-memory-why-2026-is-the-year-of-persistent-context) — layered memory architecture comparison
- [Hybrid Search in PostgreSQL: The Missing Manual (ParadeDB)](https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual) — RRF implementation patterns
- [pgvector Hybrid Search (Jonathan Katz)](https://jkatz05.com/post/postgres/hybrid-search-postgres-pgvector/) — HNSW indexing best practices
- [AI Agent Architecture 2026 (Redis)](https://redis.io/blog/ai-agent-architecture/) — working/episodic/semantic memory layers
- [Sapphire](https://github.com/ddxfish/sapphire.git) — 5-layer personal memory with FTS5 + ONNX embeddings + 4-stage cascading search
- [Building Smarter AI Agents: Long-Term Memory (AWS)](https://aws.amazon.com/blogs/machine-learning/building-smarter-ai-agents-agentcore-long-term-memory-deep-dive/) — enterprise memory patterns
