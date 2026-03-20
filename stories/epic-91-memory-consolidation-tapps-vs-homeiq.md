# Epic 91: Memory Consolidation Research — TappsMCP vs homeiq-memory

**Priority:** P3 — Backlog | **Effort:** 1-2 weeks | **Sprint:** TBD (Research, deferred: both systems work in their respective scopes)
**Dependencies:** Epics 29-35 (Memory Brain — all complete)

## Goal

Research whether to consolidate HomeIQ's memory system onto TappsMCP's `tapps_memory` (23-action cross-session knowledge store) instead of maintaining the custom `homeiq-memory` library, and determine what TappsMCP enhancements would be needed to support HomeIQ's domain-specific requirements.

## Motivation

HomeIQ currently maintains two independent memory systems:

1. **homeiq-memory** (`libs/homeiq-memory/`) — A full semantic memory library built in Sprint 7 (Epics 29-35) with hybrid search (FTS + pgvector), confidence decay, Mem0-style consolidation, HA entity domain classification, embedding generation, and LLM prompt injection. Backed by PostgreSQL `memory` schema with 4 Alembic migrations.

2. **TappsMCP `tapps_memory`** — A cross-session knowledge persistence tool with 23 actions (save, search, consolidate, federation, etc.), tiered TTLs (architectural 180d, pattern 60d, procedural 30d, context 14d), project/branch/session/shared scopes, and up to 1500 entries. Designed for developer tooling memory, isolated per project.

The overlap is significant: both handle save/search/consolidate/decay. However, TappsMCP is project-isolated (developer tooling scope), while homeiq-memory is runtime-scoped (end-user HA preferences and behaviors). This research epic determines whether TappsMCP can be extended to serve both purposes, or whether the two systems should remain separate with clear boundaries.

## Key Questions to Answer

1. **Scope alignment**: Can TappsMCP's project-isolated model extend to runtime service memory (user preferences, behavioral patterns, HA entity context)?
2. **Feature gap analysis**: What homeiq-memory capabilities are missing from TappsMCP? (pgvector hybrid search, HA domain taxonomy, confidence model, embedding generation, health checks, metrics)
3. **Enhancement feasibility**: What TappsMCP enhancements would be required? Are they reasonable contributions or would they distort TappsMCP's purpose?
4. **Performance**: Can TappsMCP handle the query volume of 53 services injecting memory context into LLM prompts at runtime?
5. **Data model**: TappsMCP uses tiered TTLs vs homeiq-memory's per-type half-life decay with confidence scoring — can these be reconciled?
6. **Operational**: Would coupling runtime memory to a dev-tooling MCP server create availability/deployment concerns?

## Stories

| # | Story | Status |
|-------|-------------|--------|
| 91.1 | **Feature matrix: homeiq-memory vs tapps_memory** — Document every capability of both systems side-by-side. Include: storage model, search (FTS, vector, hybrid), consolidation logic, decay/TTL model, entity classification, embedding support, health checks, metrics, API surface. Deliverable: comparison table in `docs/research/`. | TODO |
| 91.2 | **TappsMCP architecture deep-dive** — Research TappsMCP's internal architecture, extension points, and plugin model. Determine if it supports custom memory types, custom decay functions, external embedding providers, and domain-specific classifiers. Document findings. | TODO |
| 91.3 | **Gap analysis & enhancement proposal** — Based on 91.1-91.2, identify the specific enhancements TappsMCP would need. Categorize as: (a) reasonable upstream contributions, (b) HomeIQ-specific forks/plugins, (c) infeasible/out-of-scope. | TODO |
| 91.4 | **Runtime vs dev-time architecture assessment** — Evaluate whether TappsMCP can serve as a runtime dependency for 53 production containers. Consider: availability requirements, query latency, connection pooling, deployment topology, failure modes. | TODO |
| 91.5 | **Proof of concept: TappsMCP memory bridge** — If 91.3 shows a viable path, build a thin adapter that maps homeiq-memory's API (save/search/consolidate/inject) to TappsMCP's `tapps_memory` actions. Validate with 3 representative services: ha-ai-agent-service, device-intelligence-service, proactive-agent-service. | TODO |
| 91.6 | **Decision document & recommendation** — Write ADR (Architecture Decision Record) with one of three outcomes: (A) migrate fully to TappsMCP with enhancements, (B) use TappsMCP for dev-time + homeiq-memory for runtime (clear boundaries), (C) keep homeiq-memory, deprecate overlap. Include migration plan if A. | TODO |

## Acceptance Criteria

1. Feature comparison matrix complete with no gaps in analysis
2. TappsMCP enhancement requirements documented with feasibility assessment
3. Runtime architecture risks evaluated with concrete latency/availability data
4. ADR published with clear recommendation and rationale
5. If migration path chosen: POC validates >=3 services work through TappsMCP adapter
6. Stakeholder sign-off on chosen direction before any migration work begins

## Files Affected

- `docs/research/memory-tapps-vs-homeiq-comparison.md` — new feature matrix (91.1)
- `docs/research/tapps-memory-architecture.md` — new architecture analysis (91.2)
- `docs/research/tapps-enhancement-proposal.md` — new gap analysis (91.3)
- `docs/research/tapps-runtime-assessment.md` — new runtime evaluation (91.4)
- `libs/homeiq-memory/src/homeiq_memory/tapps_bridge.py` — new POC adapter (91.5)
- `docs/adr/adr-091-memory-consolidation.md` — new ADR (91.6)

## Risks

- **Scope creep**: Research epics can expand indefinitely. Time-box each story to 2 days max.
- **Upstream dependency**: If TappsMCP needs enhancements, timeline depends on maintainer responsiveness.
- **False economy**: Consolidating may reduce code but increase coupling to an external tool for critical runtime functionality.

## Out of Scope

- Actual migration of services (separate epic if decision is A)
- TappsMCP upstream contributions (separate epic)
- Changes to existing homeiq-memory library during research phase
