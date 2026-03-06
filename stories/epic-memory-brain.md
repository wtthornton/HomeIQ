# Epic: Memory Brain — Institutional Memory for HomeIQ

**Status:** Complete
**Created:** 2026-03-04
**Completed:** 2026-03-06
**Architecture:** [docs/planning/memory-brain-architecture.md](../docs/planning/memory-brain-architecture.md)
**Integration Map:** [docs/planning/memory-integration-map.md](../docs/planning/memory-integration-map.md)

---

## Epic Overview

Add a semantic memory consolidation layer ("Memory Brain") that captures, distills, and serves institutional knowledge across all HomeIQ AI services. The system learns from explicit user feedback, implicit behavioral signals (overrides, usage patterns, abandonment), and synthesized insights (pattern consolidation, routine detection).

**Key outcome:** Every AI service queries memory before generating output, making suggestions, responses, and recommendations informed by the full history of what worked, what failed, and what the user actually wants.

---

## Epic 1 (Index #29): Memory Store Foundation

**Goal:** Build the `homeiq-memory` shared library and PostgreSQL schema.

### Story 1.1: Database Schema & Migrations
- Enable `pgvector` extension in PostgreSQL (`CREATE EXTENSION IF NOT EXISTS vector`)
- Create `memory` schema in PostgreSQL
- `memories` table with: content, memory_type, confidence, source_channel, source_service, entity_ids, area_ids, tags, embedding (vector), timestamps, access_count, superseded_by, metadata
- `memories_archive` table (same schema, for decayed memories)
- FTS index on content (`to_tsvector`)
- HNSW vector index via pgvector
- Composite indexes on (memory_type, confidence), GIN on entity_ids
- Alembic migration using existing `homeiq-data` patterns

### Story 1.2: MemoryClient — Core CRUD
- `save(content, memory_type, source_channel, entity_ids?, area_ids?, tags?, metadata?)` — insert with embedding generation
- `get(memory_id)` — retrieve by ID
- `update(memory_id, content?, confidence?, metadata?)` — update with re-embedding if content changed
- `delete(memory_id)` — soft-delete (move to archive)
- `supersede(old_id, new_memory)` — mark old as superseded, insert new
- Async SQLAlchemy, follows `homeiq-data` DatabaseManager patterns

### Story 1.3: Hybrid Search (RRF)
- `search(query, memory_types?, entity_ids?, limit=10)` — returns ranked memories
- FTS stage: `plainto_tsquery` on content
- Vector stage: embedding similarity via pgvector `<=>` operator
- Reciprocal Rank Fusion: configurable weights (default 60/40 keyword/semantic)
- Minimum confidence threshold filter (default 0.3)
- Results include `relevance_score` from RRF

### Story 1.4: Embedding Generation
- Lightweight embedding model (all-MiniLM-L6-v2, 384-dim, or nomic-embed-text-v1.5, 768-dim — benchmark both)
- Async generation with batch support
- Lazy loading (model loads on first use)
- Configurable model path for air-gapped environments

### Story 1.5: Confidence & Decay Engine
- `reinforce(memory_id)` — bump confidence +0.1 (cap 0.95)
- `record_access(memory_id)` — bump access_count, update last_accessed
- `effective_confidence(memory)` — exponential decay based on memory_type half-life
- Half-lives: behavioral=90d, preference=180d, boundary=never, outcome=120d, routine=replaced
- Unit tests for decay calculations

### Story 1.6: Package & Install
- `libs/homeiq-memory/` package structure (pyproject.toml, src/, tests/)
- Dependencies: sqlalchemy, asyncpg, pgvector, sentence-transformers (or onnxruntime)
- Docker install pattern: `pip install /tmp/libs/homeiq-memory/`
- 80%+ test coverage on core CRUD and search

---

## Epic 2 (Index #30): Explicit Memory Capture (User-Driven)

**Goal:** Capture memories from user conversations and explicit feedback.

### Story 2.1: Chat Memory Extraction
- In `ha-ai-agent-service`, after each user message, run LLM extraction: "What facts worth remembering are in this message?"
- LLM returns structured output: `{content, memory_type, entity_ids?}`
- Apply Mem0-style consolidation before saving (check for duplicates/updates)
- Configurable: enable/disable extraction per chat session
- Integration point: `conversation_service.py`

### Story 2.2: Approval/Rejection Memory
- In `ai-automation-service-new`, when user approves/rejects a suggestion:
  - Approved: save outcome memory with automation details
  - Rejected: save boundary or preference memory with rejection reason
  - Modified: save preference memory capturing the modification
- Wire to existing `user_feedback` field in Suggestion model
- Integration point: `suggestion_service.py`

### Story 2.3: Rating & Feedback Memory
- When user rates an automation (existing rating service in pattern-service):
  - Low rating (1-2): save outcome memory "automation X underperformed"
  - High rating (4-5): save outcome memory "automation X well-received"
  - Extract reason from comment field if present
- Wire to existing `recommendation_feedback` table
- Integration point: `feedback_store.py` in rule-recommendation-ml

### Story 2.4: User Preference Settings Memory
- When user changes preferences via `preference_router.py`:
  - Save preference memory: "user changed creativity_level from balanced to conservative"
  - Track preference evolution over time
- Integration point: `preference_router.py`

---

## Epic 3 (Index #31): Implicit Memory Capture (Behavioral)

**Goal:** Detect user intent from device behavior — overrides, usage patterns, abandonment.

### Story 3.1: Override Detection
- Consolidation job queries InfluxDB for pattern: manual state change within 15 min of automation-triggered change for same entity
- If 3+ overrides for same entity in 7 days: save behavioral memory
- Include entity_id, automation context, and override direction
- Example: "User overrides thermostat from 68→72F within 10 min of automation, 5 times this week"

### Story 3.2: Automation Abandonment Detection
- Consolidation job queries automation deployment history:
  - Automation deployed but disabled within 14 days → outcome memory "automation abandoned"
  - Automation deployed but manually contradicted daily → behavioral memory
- Compare automation target state vs. actual device state from InfluxDB

### Story 3.3: Usage Pattern Consolidation
- Consolidation job queries InfluxDB for stable device usage patterns:
  - Same device, same action, similar time, 10+ occurrences over 2+ weeks
  - Save as behavioral memory with confidence based on consistency
- Exclude patterns that already have matching memories (dedup)
- Detect pattern drift: if existing behavioral memory no longer matches data, update it

### Story 3.4: Suggestion Engagement Tracking
- Track when proactive suggestions are: delivered, viewed, acted upon, ignored
- After 5+ ignored suggestions of same category: save behavioral memory "user ignores [category] suggestions"
- After 3+ acted-upon suggestions of same type: save preference memory "user engages with [type]"
- Integration point: `suggestion_storage_service.py` in proactive-agent

---

## Epic 4 (Index #32): Synthesized Memory (System-Derived)

**Goal:** Periodic consolidation job that distills raw data into high-level memories.

### Story 4.1: Consolidation Job Infrastructure
- Scheduled task (every 6 hours) — implement as APScheduler job in data-api or standalone lightweight service
- Queries InfluxDB, PostgreSQL automation tables, and existing memory store
- Applies Mem0-style consolidation: for each candidate, retrieve top-5 similar memories → insert/reinforce/update/supersede/skip
- Logging and metrics: memories created, reinforced, superseded, archived per run

### Story 4.2: Routine Synthesis
- Weekly job aggregates activity-recognition labels from InfluxDB
- Build weekday vs. weekend routine profiles (wake, leave, return, sleep times)
- Compare to existing routine memories — update if shifted, reinforce if stable
- Integration: reads from InfluxDB activity data, writes routine memories

### Story 4.3: Energy Insight Synthesis
- Consolidation job queries `event_energy_correlation` measurement from InfluxDB
- Identify stable energy patterns: "device X consistently uses Y watts"
- Identify seasonal patterns by comparing current month to historical data
- Write outcome memories for confirmed energy savings from deployed automations

### Story 4.4: Trust Score Computation
- Compute per-domain trust scores from approval/rejection/override ratios:
  - `trust = approvals / (approvals + rejections + overrides)` with Bayesian smoothing
- Store as synthesized preference memories: "lighting trust: 0.85, climate trust: 0.45, lock trust: 0.0"
- Update weekly
- Used by suggestion services to adjust confirmation UX

### Story 4.5: Garbage Collection & Contradiction Detection
- Archive memories where `effective_confidence < 0.15`
- Detect contradictions: two active memories about same entity with conflicting content
- Flag contradictions for consolidation (keep higher confidence, supersede lower)
- Log metrics: memories archived, contradictions resolved

---

## Epic 5 (Index #33): Memory Injection (AI Service Integration)

**Goal:** Every AI service queries memory before generating output.

### Story 5.1: MemoryInjector — Prompt Context Builder
- `MemoryInjector.get_context(query, memory_types?, entity_ids?, limit=10)` → formatted text block
- Output format: `[Memory Context]\n- {content} ({type}, confidence: {score})\n...`
- Sorted by relevance_score from hybrid search
- Token budget awareness: truncate if context exceeds configurable token limit (default 2000 tokens)

### Story 5.2: ha-ai-agent-service Integration
- Before every LLM call in `context_builder.py`:
  - `MemoryInjector.get_context(query=user_message)`
  - Inject as system message or user context block
- Memories inform the AI's responses naturally: "Based on your preference for warm evenings..."

### Story 5.3: Suggestion Service Integration
- `suggestion_service.py` in ai-automation-service-new:
  - Query boundary memories → exclude matching suggestions before generation
  - Query preference memories → boost matching suggestions in ranking
  - Query outcome memories → factor past success/failure into confidence_score
- `synergy_quality_scorer.py` in ai-pattern-service:
  - Add memory-based quality factor (weight: 15%)

### Story 5.4: Proactive Agent Integration
- `proactive-agent-service` before generating suggestions:
  - Query behavioral memories for engagement patterns
  - Query routine memories for optimal suggestion timing
  - Query boundary memories to filter domains
  - Include memory context in RAG prompt alongside existing corpus

### Story 5.5: Blueprint Scoring Integration
- `suggestion_scorer.py` in blueprint-suggestion-service:
  - Add memory-based scoring factor (weight: 15%)
  - Query outcome memories for same blueprint type
  - Query preference memories for complexity/style preferences

---

## Epic 6 (Index #34): Trust Model & Adaptive UX

**Goal:** Build per-domain trust scores that influence the automation approval experience.

### Story 6.1: Trust Score API
- Endpoint: `GET /api/v1/memory/trust?domain=light`
- Returns trust score (0.0-1.0) with breakdown: approvals, rejections, overrides, total
- Per-domain (light, climate, lock, cover, fan, switch, etc.)
- Computed from memory store (approval/rejection outcome memories + override behavioral memories)

### Story 6.2: Adaptive Confirmation UX
- High trust (>0.8): streamlined one-click approval, minimal explanation
- Medium trust (0.4-0.8): standard approval flow with explanation
- Low trust (<0.4): extra confirmation step, detailed explanation, "are you sure?" prompt
- Zero trust (0.0): require explicit opt-in before even showing suggestions for this domain

### Story 6.3: Trust Dashboard Widget
- Health dashboard widget showing trust scores per domain
- Trend visualization (trust growing or declining over time)
- Quick action: "reset trust for domain X" (clears relevant memories)

---

## Epic 7 (Index #35): Memory Lifecycle & Observability

**Goal:** Ensure memory system is maintainable, observable, and self-healing.

### Story 7.1: Memory Admin API
- CRUD endpoints for memory management (admin-api):
  - `GET /api/v1/memories` — list with filters (type, confidence, entity, search)
  - `GET /api/v1/memories/{id}` — detail view
  - `DELETE /api/v1/memories/{id}` — manual removal
  - `POST /api/v1/memories/{id}/reinforce` — manual confidence boost
- Pagination, sorting, filtering

### Story 7.2: Memory Dashboard Page
- New page in health-dashboard showing:
  - Memory count by type and confidence distribution
  - Recent memories (last 24h)
  - Consolidation job status and metrics
  - Decay visualization (memories approaching archive threshold)
  - Contradiction alerts

### Story 7.3: Metrics & Alerting
- Prometheus metrics: `homeiq_memory_total`, `homeiq_memory_searches`, `homeiq_memory_consolidation_duration`
- Grafana dashboard panel
- Alerts: consolidation job failure, memory count growing unbounded, excessive contradictions

### Story 7.4: Self-Healing
- Database integrity checks on service startup (PostgreSQL is robust but verify pgvector index health)
- Embedding backfill: detect memories with NULL embeddings, generate in batch
- FTS index rebuild if search returns unexpected results
- Graceful degradation: if memory store unreachable, AI services proceed without memory context (log warning, don't fail)

---

## Dependency Graph

```
Epic 1 (Foundation)
  ├── Epic 2 (Explicit Capture) ──────────────┐
  ├── Epic 3 (Implicit Capture) ──────────────┤
  ├── Epic 4 (Synthesized Memory) ────────────┤
  │                                            ▼
  └── Epic 5 (Memory Injection) ←── requires memories to exist
         │
         ├── Epic 6 (Trust Model) ←── requires injection + outcome memories
         └── Epic 7 (Lifecycle) ←── can start in parallel with Epic 5
```

**Recommended execution order:**
1. Epic 1 (Foundation) — must be first
2. Epic 2 + Epic 7.1-7.3 in parallel — explicit capture + admin tooling
3. Epic 3 + Epic 4 in parallel — implicit + synthesized capture
4. Epic 5 — injection (needs memories to exist from Epics 2-4)
5. Epic 6 — trust model (needs injection working)

---

## Success Metrics

| Metric | Baseline (today) | Target |
|--------|-------------------|--------|
| Suggestion acceptance rate | Unknown (not tracked) | +20% improvement after 30 days |
| Repeated rejections of same pattern | Frequent (no memory) | Near zero |
| Override rate on deployed automations | Unknown | -30% (automations better match preferences) |
| Proactive suggestion engagement | Unknown | +25% (better timing + relevance) |
| Time to useful suggestion for new user | Cold start | Warm start after 1 week of memory building |

---

## Technical References

- [Mem0 Architecture Paper](https://arxiv.org/pdf/2504.19413) — extract-consolidate-retrieve pattern
- [Mem0 vs Zep vs Claude-Mem 2026](https://serenitiesai.com/articles/ai-agent-memory-why-2026-is-the-year-of-persistent-context) — memory lifecycle management
- [ParadeDB Hybrid Search](https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual) — RRF implementation in PostgreSQL
- [pgvector Best Practices](https://jkatz05.com/post/postgres/hybrid-search-postgres-pgvector/) — HNSW indexing, hybrid search
- [Sapphire](https://github.com/ddxfish/sapphire.git) — personal AI memory with 4-stage cascading search (inspiration for search strategy)
- [AI Agent Architecture 2026 (Redis)](https://redis.io/blog/ai-agent-architecture/) — working/episodic/semantic memory layers
- [AWS AgentCore Long-Term Memory](https://aws.amazon.com/blogs/machine-learning/building-smarter-ai-agents-agentcore-long-term-memory-deep-dive/) — enterprise memory patterns
