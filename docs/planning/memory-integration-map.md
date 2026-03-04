# HomeIQ Memory Brain — Integration Map

**Status:** Draft
**Created:** 2026-03-04
**Parent:** [memory-brain-architecture.md](memory-brain-architecture.md)

This document maps exactly what each subsystem **writes to** and **reads from** the memory brain. Developers reference this during implementation to understand their service's integration points.

---

## Shared Library

All services integrate via `libs/homeiq-memory/` which provides:
- `MemoryClient` — async CRUD + hybrid search
- `MemoryInjector` — formats top-N relevant memories for LLM prompt injection
- `MemoryConsolidator` — extract/merge/supersede logic (used by consolidation job)

Install pattern (same as existing libs):
```dockerfile
COPY libs/ /tmp/libs/
RUN pip install /tmp/libs/homeiq-memory/
```

---

## Integration Map by Subsystem

### 1. ha-ai-agent-service (Chat / Ask AI)
**Domain group:** `automation-core` | **Port:** 8030

| Direction | Memory Type | Trigger | Example |
|-----------|-------------|---------|---------|
| **WRITES** | `preference` | User states preference in chat | "I like it warm in the evening" → preference memory |
| **WRITES** | `boundary` | User states constraint in chat | "Don't automate the garage" → boundary memory |
| **WRITES** | `preference` | User modifies suggested automation params | Changed brightness 100→40% → "prefers dim evening lights" |
| **READS** | all types | Before every LLM response | Inject top-10 relevant memories as `[Memory Context]` block |

**Current feedback gap closed:** Chat context currently ephemeral — preferences stated in conversation are lost after session. Memory captures them permanently.

**Implementation notes:**
- Add LLM-based memory extraction after each user message (Mem0-style: ask LLM "what facts worth remembering are in this message?")
- `MemoryInjector.get_context(query=user_message, limit=10)` before building LLM prompt
- `conversation_service.py` is the integration point

---

### 2. ai-automation-service-new (Suggestions)
**Domain group:** `automation-core` | **Port:** 8036

| Direction | Memory Type | Trigger | Example |
|-----------|-------------|---------|---------|
| **WRITES** | `outcome` | Suggestion approved + deployed | "Sunset lighting deployed, user approved without changes" |
| **WRITES** | `outcome` | Suggestion rejected | "Motion→bathroom rejected: 'cats trigger it'" |
| **WRITES** | `preference` | User modifies suggestion before approving | "User always increases delay timers on motion automations" |
| **READS** | `boundary` | Before generating suggestions | Filter out suggestions that match boundary memories |
| **READS** | `preference` | Before ranking suggestions | Boost suggestions matching preference memories |
| **READS** | `outcome` | Before generating suggestions | "Similar automation failed/succeeded before" |

**Current feedback gap closed:** `user_feedback` field exists in Suggestion model but doesn't influence future generation. Memory makes past feedback queryable for future suggestions.

**Implementation notes:**
- `suggestion_service.py` — query boundaries before generation, query preferences for ranking
- `preference_router.py` — extend to write preference memories on user settings changes
- Wire `PostActionVerifier` outcomes → outcome memory writes

---

### 3. ai-pattern-service (Pattern Detection)
**Domain group:** `pattern-analysis` | **Port:** 8020

| Direction | Memory Type | Trigger | Example |
|-----------|-------------|---------|---------|
| **WRITES** | `behavioral` | Pattern stable (10+ occurrences, 2+ weeks) | "Kitchen lights on at 6:30 AM weekdays" |
| **WRITES** | `behavioral` | Pattern stopped recurring | "Kitchen morning pattern shifted to 7:00 AM" |
| **READS** | `boundary` | Before surfacing synergies to user | Skip synergies matching boundary memories |
| **READS** | `behavioral` | Before detecting new patterns | Don't re-detect patterns already consolidated into memory |
| **READS** | `outcome` | Before scoring synergy quality | Factor in whether similar synergies succeeded/failed |

**Current feedback gap closed:** Pattern confidence doesn't update from user feedback. Synergies get re-detected after rejection. Memory prevents both.

**Implementation notes:**
- Consolidation job (not real-time) queries `pattern_quality_scorer` results and writes stable patterns to memory
- `feedback_client.py` already caches synergy feedback — extend to also write boundary memories on rejection
- `synergy_quality_scorer.py` — add memory query as scoring factor

---

### 4. proactive-agent-service (Proactive Suggestions)
**Domain group:** `energy-analytics` | **Port:** 8031

| Direction | Memory Type | Trigger | Example |
|-----------|-------------|---------|---------|
| **WRITES** | `outcome` | Suggestion accepted/ignored | "Energy suggestion ignored 3 times this week" |
| **READS** | `preference` | Before generating suggestions | "User acts on lighting suggestions, ignores climate ones" |
| **READS** | `routine` | Before timing suggestions | "User engages most at 8 PM" |
| **READS** | `behavioral` | Before selecting suggestion category | Prioritize categories user has historically engaged with |
| **READS** | `boundary` | Before suggesting | Never suggest in boundary domains |

**Current feedback gap closed:** Proactive agent is stateless between cycles — doesn't know its own suggestion history or effectiveness. Memory gives it self-awareness.

**Implementation notes:**
- Track suggestion delivery + engagement (viewed? acted on? ignored?)
- `suggestion_storage_service.py` — extend with memory writes on engagement events
- RAG prompt generation should include memory context alongside existing RAG corpus

---

### 5. energy-correlator (Energy Analysis)
**Domain group:** `energy-analytics` | **Port:** 8017

| Direction | Memory Type | Trigger | Example |
|-----------|-------------|---------|---------|
| **WRITES** | `behavioral` | Stable energy pattern detected | "Space heater runs 3h daily in office, Oct-Mar" |
| **WRITES** | `outcome` | Energy savings realized | "LED switch saved 15W/activation, confirmed over 6 weeks" |
| **READS** | `behavioral` | Before correlating events | Baseline expectations for device power usage |

**Current feedback gap closed:** Energy correlations are written to InfluxDB as raw data but never distilled into reusable insights. Memory captures the meaning.

**Implementation notes:**
- Consolidation job queries InfluxDB `event_energy_correlation` measurement for stable patterns
- `energy_savings_calculator.py` results → outcome memories
- Seasonal detection: compare current patterns to memories from same period last year

---

### 6. activity-recognition (Activity Labels)
**Domain group:** `device-management` | **Port:** 8043 (internal 8036)

| Direction | Memory Type | Trigger | Example |
|-----------|-------------|---------|---------|
| **WRITES** | `routine` | Weekly consolidation of activity patterns | "Weekday: wake 6:30, leave 7:45, return 5:30, sleep 10:30" |
| **WRITES** | `routine` | Routine shift detected | "Routine changed: now waking at 7:00 (was 6:30)" |
| **READS** | `routine` | Before classifying anomalies | "User home at 2 PM Tuesday — deviation from routine" |

**Current feedback gap closed:** LSTM classifies in real-time but has no baseline memory. Can't distinguish "unusual" from "new normal."

**Implementation notes:**
- Consolidation job (weekly) aggregates activity labels from InfluxDB into routine memories
- Compare new week's pattern to stored routine memory — if significantly different, update memory
- Expose routine memories to proactive-agent for context-aware suggestions

---

### 7. blueprint-suggestion-service (Blueprint Matching)
**Domain group:** `blueprints` | **Port:** 8032

| Direction | Memory Type | Trigger | Example |
|-----------|-------------|---------|---------|
| **WRITES** | `outcome` | Blueprint deployed successfully | "Motion-light blueprint deployed in hallway, running 2 months" |
| **READS** | `preference` | Before scoring blueprints | "User prefers simple automations (low complexity)" |
| **READS** | `boundary` | Before matching | Exclude blueprints for boundary domains |
| **READS** | `outcome` | Before suggesting | "This blueprint type succeeded/failed before" |

**Current feedback gap closed:** `suggestion_scorer.py` has multi-factor scoring but no user history factor. Memory adds a "past success with similar blueprints" signal.

**Implementation notes:**
- Add memory-based scoring factor to `suggestion_scorer.py` (weight: 15%)
- Query outcome memories for same blueprint type or same entity domain

---

### 8. device-intelligence-service (Device Health & Recommendations)
**Domain group:** `ml-engine` | **Port:** 8019

| Direction | Memory Type | Trigger | Example |
|-----------|-------------|---------|---------|
| **WRITES** | `preference` | User customizes device naming | "User names devices by location (kitchen, office)" |
| **WRITES** | `behavioral` | Device usage pattern stable | "Office fan only used May-September" |
| **READS** | `preference` | Before generating recommendations | Tailor recommendations to user's technical level and preferences |

**Current feedback gap closed:** `preference_learner.py` learns naming patterns but doesn't share this knowledge with other services. Memory makes it cross-service.

---

### 9. websocket-ingestion (Event Stream)
**Domain group:** `core-platform` | **Port:** 8001

| Direction | Memory Type | Trigger | Example |
|-----------|-------------|---------|---------|
| **WRITES** | `behavioral` | Override detection (via consolidation job) | "User overrode thermostat within 10 min of automation 5 times this week" |

**Current feedback gap closed:** Raw events flow through but overrides (manual action contradicting recent automation) aren't detected as feedback.

**Implementation notes:**
- Consolidation job (not websocket-ingestion itself) queries InfluxDB for patterns where manual state change follows automation-triggered change within configurable window (default: 15 min)
- Writes override patterns as behavioral memories with entity_id and area_id tags

---

### 10. Consolidation Job (NEW — Periodic Background Service)

| Direction | Memory Type | Trigger | Example |
|-----------|-------------|---------|---------|
| **WRITES** | all types | Scheduled (every 6 hours) | Synthesizes memories from raw data |
| **READS** | all types | During consolidation | Checks existing memories before writing |

**Responsibilities:**
1. Query InfluxDB for stable behavioral patterns → write behavioral memories
2. Query automation run history for override patterns → write behavioral memories
3. Query activity recognition data for routine baselines → write/update routine memories
4. Query energy correlations for longitudinal insights → write outcome memories
5. Run Mem0-style consolidation: merge similar, supersede contradicted, reinforce confirmed
6. Run confidence decay calculation on all active memories
7. Archive memories below confidence threshold (0.15)
8. Detect contradictions between active memories

**Implementation:** New service or scheduled task within data-api (leverages existing DB access)

---

## Memory Flow Diagram

```
EXPLICIT INPUT                    IMPLICIT INPUT                 SYNTHESIZED INPUT
─────────────                    ──────────────                 ─────────────────
ha-ai-agent ──┐                  websocket-ingestion ──┐        consolidation-job ──┐
  (chat)      │                    (events)            │          (periodic)        │
              │                                        │                           │
ai-automation ┤  preference      override detection ───┤  behavioral              │
  (approve/   │  boundary                              │                           │
   reject)    │                  suggestion engagement ─┤  behavioral     pattern  ─┤
              │                    (view/ignore/act)    │                 synthesis │
              │                                        │                           │
              │                  automation abandon ────┤  behavioral     routine  ─┤
              │                    (disable/override)   │                 baseline  │
              │                                        │                           │
              ▼                                        ▼                           ▼
         ┌──────────────────────────────────────────────────────────────────────────┐
         │                     MEMORY STORE (PostgreSQL + pgvector)                 │
         │                                                                         │
         │   behavioral │ preference │ boundary │ outcome │ routine                │
         │                                                                         │
         │   Hybrid Search: FTS + Vector (RRF) │ Confidence Decay │ GC            │
         └──────────────────────────────┬──────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              ha-ai-agent        proactive-agent      suggestion-service
              (prompt inject)    (context query)      (filter + rank)
                    │                   │                   │
                    ▼                   ▼                   ▼
              pattern-service    blueprint-service    device-intelligence
              (skip rejected)    (score by history)   (cross-service prefs)
```

---

## What Changes Per Service (Developer Checklist)

| Service | Files to Modify | Effort |
|---------|----------------|--------|
| ha-ai-agent-service | `conversation_service.py`, `context_builder.py` | Medium — add extraction + injection |
| ai-automation-service-new | `suggestion_service.py`, `preference_router.py` | Medium — add memory queries to generation |
| ai-pattern-service | `synergy_quality_scorer.py`, `feedback_client.py` | Low — add memory as scoring factor |
| proactive-agent-service | `suggestion_storage_service.py`, prompt builder | Medium — track engagement, query before suggesting |
| energy-correlator | consolidation job only (no service changes) | Low — consolidation job queries InfluxDB |
| activity-recognition | consolidation job only (no service changes) | Low — consolidation job aggregates activities |
| blueprint-suggestion-service | `suggestion_scorer.py` | Low — add memory-based scoring factor |
| device-intelligence-service | `preference_learner.py` | Low — write to memory instead of local-only |
| websocket-ingestion | none (consolidation job handles override detection) | None |
| data-api | `evaluation_endpoints.py` (host consolidation job) | Medium — new scheduled task |
| **NEW: homeiq-memory lib** | new shared library | **High — core implementation** |
