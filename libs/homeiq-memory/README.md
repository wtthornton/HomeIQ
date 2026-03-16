# homeiq-memory

Semantic memory store for HomeIQ. Captures user preferences, behaviors, and boundaries with hybrid search (FTS + pgvector), confidence decay, and LLM prompt injection.

**Version:** 1.0.0 | **Python:** >=3.11 | **Schema:** `memory`

## Quick Start

```python
from homeiq_memory import MemoryClient, MemorySearch, MemoryConsolidator, MemoryInjector

# 1. Initialize client
client = MemoryClient()  # reads MEMORY_DATABASE_URL or DATABASE_URL
await client.initialize()
await client.preload_embeddings()

# 2. Save a memory
from homeiq_memory import MemoryType, SourceChannel

memory = await client.save(
    content="User prefers 72F in the evening",
    memory_type=MemoryType.PREFERENCE,
    source_channel=SourceChannel.EXPLICIT,
    source_service="ha-ai-agent-service",
    entity_ids=["climate.living_room"],
)

# 3. Search memories (hybrid FTS + vector)
search = MemorySearch(
    session_factory=client._session_maker,
    embedding_generator=client.embedding_generator,
)
results = await search.search("temperature preferences", limit=10)

# 4. Inject into LLM prompt
injector = MemoryInjector(search, token_budget=2000)
context_block = await injector.get_context("evening temperature settings")
# Returns: "[Memory Context]\n- User prefers 72F in the evening (preference, confidence: 0.85)"

# 5. Consolidate (deduplicate, reinforce, supersede)
consolidator = MemoryConsolidator(client, search)
result = await consolidator.consolidate(
    content="User likes it warm at night",
    memory_type=MemoryType.PREFERENCE,
    source_channel=SourceChannel.IMPLICIT,
)
# result.action: INSERT | REINFORCE | UPDATE | SUPERSEDE | SKIP
```

## Installation

In your service's Dockerfile:

```dockerfile
COPY libs/ /tmp/libs/
RUN pip install /tmp/libs/homeiq-memory/

# With embedding support (adds sentence-transformers + torch):
RUN pip install "/tmp/libs/homeiq-memory/[embeddings]"
```

## Memory Types

| Type | Half-life | Decays? | Use case |
|------|-----------|---------|----------|
| `BEHAVIORAL` | 90 days | Yes | Observed patterns ("lights on at 6:30 AM weekdays") |
| `PREFERENCE` | 180 days | Yes | Stated or inferred likes ("prefers dim evening lights") |
| `BOUNDARY` | -- | Never | Hard constraints ("never automate garage door") |
| `OUTCOME` | 120 days | Yes | Automation results ("sunset lighting: zero overrides in 3 months") |
| `ROUTINE` | -- | Replaced | Schedules ("weekday: wake 6:30, leave 7:45, return 5:30") |

## Source Channels

| Channel | Meaning |
|---------|---------|
| `EXPLICIT` | User directly stated (chat, approval, rejection) |
| `IMPLICIT` | Inferred from behavior (overrides, usage patterns) |
| `SYNTHESIZED` | System-derived (pattern consolidation, routine detection) |

## Confidence Model

- **Initial:** 0.5 for new memories
- **Reinforced:** +0.1 per confirming observation (capped at 0.95)
- **Accessed:** +0.02 per retrieval
- **Contradicted:** Set to 0.1, old memory linked via `superseded_by`
- **Decay:** `effective = confidence * 0.5^(days / half_life)`
- **Garbage collection:** Archive when effective confidence < 0.15

```python
from homeiq_memory import effective_confidence, reinforce, should_archive

score = effective_confidence(memory)  # time-decayed confidence
reinforce(memory, amount=0.1)         # bump on confirmation
should_archive(memory)                # True if below threshold
```

## Hybrid Search (RRF)

Combines PostgreSQL full-text search with pgvector cosine similarity using Reciprocal Rank Fusion:

```
score = 0.6/(60 + fts_rank) + 0.4/(60 + vector_rank)
```

Additional boosts:
- **Recency:** +0.1 for memories < 30 days old
- **Confidence:** +0.05 for high-confidence memories
- **Fallback:** Degrades to FTS-only if vector search fails

```python
search = MemorySearch(
    session_factory=client._session_maker,
    embedding_generator=client.embedding_generator,
    fts_weight=0.6,    # default
    vector_weight=0.4,  # default
)
results = await search.search(
    query="temperature preferences",
    memory_types=[MemoryType.PREFERENCE, MemoryType.BOUNDARY],
    entity_ids=["climate.living_room"],
    min_confidence=0.3,
    limit=10,
)
```

## Consolidation (Mem0-style)

When a new memory candidate arrives, the consolidator compares it against existing memories:

| Similarity | Sentiment | Action |
|------------|-----------|--------|
| < 0.85 | -- | **INSERT** as new memory |
| >= 0.85 | Same meaning | **REINFORCE** (+0.1 confidence) |
| >= 0.85 | New details | **UPDATE** (merge content) |
| >= 0.85 | Contradicts | **SUPERSEDE** (replace old) |
| >= 0.95 | Same, < 24h | **SKIP** (duplicate) |

Contradiction detection uses regex-based negation/affirmative pattern matching.

```python
consolidator = MemoryConsolidator(client, search)

# Consolidate a new candidate
result = await consolidator.consolidate(
    content="User now prefers 74F in the evening",
    memory_type=MemoryType.PREFERENCE,
    source_channel=SourceChannel.EXPLICIT,
)
print(result.action)  # ConsolidationAction.SUPERSEDE

# Garbage collect stale memories
archived = await consolidator.run_garbage_collection(archive_threshold=0.15)

# Find contradictions
contradictions = await consolidator.detect_contradictions()
```

## Domain Classification

Automatically classifies memories by HA entity domain:

```python
from homeiq_memory import classify_domain, classify_domains

classify_domain(["light.kitchen", "light.bedroom"])  # "lighting"
classify_domains(["light.kitchen", "climate.bedroom"])  # ["climate", "lighting"]
```

Taxonomy: `light/switch` -> lighting, `climate/fan` -> climate, `lock/alarm_control_panel` -> security, `sensor` -> energy, `automation/script` -> automation, etc.

## Embedding Generation

Uses sentence-transformers for vector encoding:

```python
from homeiq_memory import EmbeddingGenerator

gen = EmbeddingGenerator()  # default: all-MiniLM-L6-v2 (384-dim)
# or: EmbeddingGenerator(model_name="nomic-ai/nomic-embed-text-v1.5")  # 768-dim

await gen.preload()  # background model loading
embedding = await gen.generate("user prefers warm evenings")
batch = await gen.generate_batch(["text1", "text2"])
```

## Health Checks

```python
from homeiq_memory import MemoryHealthCheck

health = MemoryHealthCheck(client)
status = await health.check_health(auto_repair=True)
# Checks: DB connectivity, pgvector extension, FTS index, embedding model, superseded chains
# Auto-repairs: FTS reindex, orphaned superseded_by cleanup

stats = await health.get_stats()
# {active: 1234, archived: 56, superseded: 78, missing_embedding: 0}

# Backfill missing embeddings
await health.backfill_embeddings(batch_size=50)
```

## LLM Prompt Injection

Format memories into token-budgeted context blocks:

```python
from homeiq_memory import MemoryInjector

injector = MemoryInjector(search, token_budget=2000)
context = await injector.get_context(
    query="evening lighting",
    entity_ids=["light.living_room"],
    exclude_types=[MemoryType.ROUTINE],
)
# "[Memory Context]\n- User prefers dim evening lights (preference, confidence: 0.85) [entities: light.living_room]"
```

## Metrics

Callback-based metrics for external backends (InfluxDB, Prometheus):

```python
from homeiq_memory import memory_metrics

# Register a sink
memory_metrics.register_callback(lambda metric, value, tags: send_to_influx(metric, value, tags))

# Emitted automatically:
# - memory_save_count, memory_delete_count
# - memory_consolidation_decisions (tags: action)
# - memory_embedding_latency_ms (histogram)
# - memory_search_latency_ms (histogram, tags: mode)
```

## Database Schema

Tables live in the `memory` PostgreSQL schema. Migrations managed via Alembic:

```
alembic/versions/
  001_create_memory_schema.py   -- memories + memory_archive tables, indexes
  002_fix_memory_type_enum.py   -- enum type fix
  003_add_domain_and_fix_fk.py  -- domain column + ON DELETE SET NULL for superseded_by
```

Run migrations:

```bash
cd libs/homeiq-memory
alembic upgrade head
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MEMORY_DATABASE_URL` | -- | Primary DB URL (takes precedence) |
| `DATABASE_URL` | `postgresql+asyncpg://homeiq:homeiq@localhost:5432/homeiq` | Fallback DB URL |

## Public API

All exports from `homeiq_memory`:

| Export | Module | Purpose |
|--------|--------|---------|
| `MemoryClient` | client | Async CRUD + search |
| `MemorySearch`, `MemorySearchResult` | search | Hybrid RRF search |
| `MemoryConsolidator`, `ConsolidationAction`, `ConsolidationResult` | consolidator | Mem0-style dedup |
| `MemoryInjector` | injector | LLM prompt formatting |
| `EmbeddingGenerator` | embeddings | Sentence-transformer encoding |
| `MemoryHealthCheck`, `HealthStatus` | health | Health + auto-repair |
| `Memory`, `MemoryArchive`, `MemoryType`, `SourceChannel`, `Base` | models | ORM models |
| `effective_confidence`, `reinforce`, `contradict`, `record_access`, `should_archive` | decay | Confidence functions |
| `HALF_LIVES`, `MAX_CONFIDENCE`, `ACCESS_CONFIDENCE_BUMP` | decay | Constants |
| `classify_domain`, `classify_domains`, `DOMAIN_TAXONOMY`, `VALID_DOMAINS` | domains | HA domain taxonomy |
| `memory_metrics` | metrics | Metrics interface |

## Related Docs

- [Architecture & Vision](../../docs/planning/memory-brain-architecture.md)
- [Integration Map](../../docs/planning/memory-integration-map.md)
