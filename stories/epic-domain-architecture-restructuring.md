---
epic: domain-architecture-restructuring
priority: high
status: complete
estimated_duration: 2-3 weeks
risk_level: medium
source: PRD – Service Decomposition Plan (Direct Path to Option A)
type: initiative
---

# Initiative: Domain Architecture Restructuring

**Status:** Complete (All 5 Epics Done)

**Final Results:**
- Epics 1-4: Structural migration complete (52 services → 9 domains, 5 shared libs)
- Epic 5: Validation complete — 47/49 services healthy, 704 tests pass, 70 Python files validated
- Docker: 28 Dockerfiles fixed (install ordering), 6 builds verified, full stack operational
- Bugs found and fixed: 9 missing `from pathlib import Path` imports, 80+ stale imports, 5 config paths
**Priority:** High
**Duration:** 2–3 weeks (pre-production fast track)
**Risk Level:** Medium
**PRD Reference:** `docs/planning/service-decomposition-plan.md`

## Overview

Restructure the HomeIQ monorepo from a flat `services/` directory with 52 services into a domain-aligned `domains/` directory with 9 groups, decompose the monolithic `shared/` directory into 5 installable Python packages under `libs/`, modernize Docker infrastructure with per-domain compose files and parallel builds via docker-bake, and update all references across the entire codebase.

This is the **direct path** — no symlinks, no Strangler Fig, no phased migration. The project is pre-production, so we move fast and fix forward.

### Why 9 Groups (not 6)

The original decomposition plan defined 6 groups. We extend to 9 by splitting `automation-intelligence` (16 services — too large for single-team ownership) into 4 sub-domains:

| Original Group | New Groups | Services |
|---|---|---|
| automation-intelligence (16) | **automation-core** | 7 |
| | **blueprints** | 4 |
| | **energy-analytics** | 3 |
| | **pattern-analysis** | 2 |

No other groups change. Result: no group exceeds 10 services.

## The 9 Domain Groups

| # | Domain | Services | Key Responsibilities |
|---|--------|----------|---------------------|
| 1 | **core-platform** | 6 | Data backbone — InfluxDB, data-api, websocket-ingestion, admin-api, health-dashboard, data-retention |
| 2 | **data-collectors** | 8 | Stateless external API fetchers — weather, sports, air quality, carbon, electricity, calendar, smart-meter, logs |
| 3 | **ml-engine** | 10 | ML inference, embeddings, training — ai-core, openvino, ml-service, NER, OpenAI, RAG, training, device-intelligence, model-prep, nlp-fine-tuning |
| 4 | **automation-core** | 7 | Core automation engine — ha-ai-agent, ai-automation-service-new, ai-query, automation-linter, yaml-validation, ai-code-executor, automation-trace |
| 5 | **blueprints** | 4 | Blueprint discovery and recommendations — blueprint-index, blueprint-suggestion, rule-recommendation-ml, automation-miner |
| 6 | **energy-analytics** | 3 | Energy intelligence — energy-correlator, energy-forecasting, proactive-agent-service |
| 7 | **device-management** | 8 | Device lifecycle — health monitor, classifier, setup assistant, database client, recommender, activity recognition/writer, ha-setup |
| 8 | **pattern-analysis** | 2 | Behavioral patterns — ai-pattern-service, api-automation-edge |
| 9 | **frontends** | 4 | User interfaces — ai-automation-ui, observability-dashboard, health-dashboard, jaeger |

**Total:** 52 services across 9 domains.

## Target Folder Structure

```
homeiq/
├── domains/
│   ├── core-platform/
│   │   ├── websocket-ingestion/
│   │   ├── data-api/
│   │   ├── admin-api/
│   │   ├── health-dashboard/
│   │   ├── data-retention/
│   │   ├── compose.yml
│   │   └── README.md
│   ├── data-collectors/
│   │   ├── weather-api/
│   │   ├── smart-meter-service/
│   │   ├── ... (8 services)
│   │   ├── compose.yml
│   │   └── README.md
│   ├── ml-engine/
│   │   ├── ai-core-service/
│   │   ├── ... (10 services)
│   │   ├── compose.yml
│   │   └── README.md
│   ├── automation-core/
│   │   ├── ha-ai-agent-service/
│   │   ├── ... (7 services)
│   │   ├── compose.yml
│   │   └── README.md
│   ├── blueprints/
│   │   ├── blueprint-index/
│   │   ├── ... (4 services)
│   │   ├── compose.yml
│   │   └── README.md
│   ├── energy-analytics/
│   │   ├── energy-correlator/
│   │   ├── energy-forecasting/
│   │   ├── proactive-agent-service/
│   │   ├── compose.yml
│   │   └── README.md
│   ├── device-management/
│   │   ├── device-health-monitor/
│   │   ├── ... (8 services)
│   │   ├── compose.yml
│   │   └── README.md
│   ├── pattern-analysis/
│   │   ├── ai-pattern-service/
│   │   ├── api-automation-edge/
│   │   ├── compose.yml
│   │   └── README.md
│   └── frontends/
│       ├── ai-automation-ui/
│       ├── observability-dashboard/
│       ├── health-dashboard/
│       ├── compose.yml
│       └── README.md
│
├── libs/
│   ├── homeiq-patterns/          # shared/patterns/ → installable package
│   │   ├── src/homeiq_patterns/
│   │   ├── tests/
│   │   └── pyproject.toml
│   ├── homeiq-resilience/        # shared/resilience/ → installable package
│   │   ├── src/homeiq_resilience/
│   │   └── pyproject.toml
│   ├── homeiq-data/              # influx client, db pool, cache, auth
│   │   ├── src/homeiq_data/
│   │   └── pyproject.toml
│   ├── homeiq-ha/                # HA connection, automation lint
│   │   ├── src/homeiq_ha/
│   │   └── pyproject.toml
│   └── homeiq-observability/     # metrics, logging, monitoring
│       ├── src/homeiq_observability/
│       └── pyproject.toml
│
├── docker-compose.yml            # Root include: all domain compose files
├── docker-bake.hcl               # Parallel build groups
├── pyproject.toml                # Root workspace config
└── ...
```

## Dependency Graph (Domains)

```
                         ┌──────────────────────┐
                         │  core-platform (6)    │
                         └──────────┬───────────┘
                                    │
         ┌──────────────┬───────────┼───────────┐
         │              │           │            │
         ▼              ▼           ▼            ▼
  data-collectors  ml-engine  device-mgmt  pattern-analysis
      (8)           (10)        (8)           (2)
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
   automation-  blueprints  energy-
     core (7)     (4)      analytics (3)
          │
          ▼
     frontends (4)
```

## Epic Breakdown

| # | Epic | Stories | Story Points | Duration | Dependencies |
|---|------|---------|-------------|----------|-------------|
| 1 | [Domain Folder Restructuring](epic-domain-folder-restructuring.md) | 12 | 27 | **Complete** | None |
| 2 | [Shared Library Decomposition](epic-shared-library-decomposition.md) | 9 | 25 | **Complete** | None (parallel with Epic 1) |
| 3 | [Docker Modernization](epic-docker-modernization.md) | 14 | 41 | **Complete** | Epic 1 |
| 4 | [Reference Updates](epic-reference-updates.md) | 14 | 63 | **Complete** | Epics 1, 2, 3 |
| 5 | [Validation and Cleanup](epic-validation-and-cleanup.md) | 12 | 41 | 3–5 days | Epics 1–4 |
| | **Totals** | **61 stories** | **197 points** | **2–3 weeks** | |

## Execution Plan

```
Week 1:
  Epic 1 (folder moves)  ────────────────────►
  Epic 2 (shared lib split) ─────────────────►  (parallel with Epic 1)

Week 2:
  Epic 3 (Docker modernization) ─────────────►  (after Epic 1)
  Epic 4 (reference updates) ────────────────────────────────►  (after Epics 1+2+3)

Week 3:
  Epic 4 (continued) ───────►
  Epic 5 (validation + cleanup) ─────────────►  (after Epic 4)
```

### Critical Path

```
Epic 1 Story 1 (create dirs) → Epic 1 Stories 2-10 (move services, parallel)
                                       │
                                       ▼
                              Epic 3 (Docker compose + bake)
                                       │
Epic 2 (shared lib split) ────────────►│
                                       ▼
                              Epic 4 (reference updates)
                                       │
                                       ▼
                              Epic 5 (validation + cleanup)
```

**Epics 1 and 2 are independent** — folder moves and shared lib packaging have no dependency on each other. Run them in parallel with separate agent teams.

## Agent Team Strategy

This initiative is designed for **Claude Agent Teams** with parallel execution:

### Recommended Team Structure

| Team | Agent Count | Epics | Role |
|------|-------------|-------|------|
| **Restructuring Team** | 10 agents | Epic 1 | 1 lead + 9 movers (one per domain group, parallel) |
| **Library Team** | 6 agents | Epic 2 | 1 lead + 5 packagers (one per lib, parallel) |
| **Docker Team** | 10 agents | Epic 3 | 1 lead + 9 compose writers (parallel) |
| **Reference Team** | 10 agents | Epic 4 | 1 lead + 9 per-domain updaters (parallel) |
| **Validation Team** | 4 agents | Epic 5 | Build lead, test lead, docs lead, quality watchdog |

### Parallelization Opportunities

1. **Within Epic 1:** Stories 2-10 (9 domain moves) run in parallel after Story 1
2. **Within Epic 2:** Stories 2-6 (5 package creations) run in parallel after Story 1
3. **Epic 1 and Epic 2:** Run entirely in parallel (no dependency between them)
4. **Within Epic 3:** Stories 2-10 (9 compose files) run in parallel
5. **Within Epic 4:** Stories 1-9 (Dockerfile updates per group) run in parallel
6. **Within Epic 5:** Stories 5-11 run in parallel after Stories 1-4 pass

### Quality Watchdog

One agent per team runs `tapps_quick_check()` on every modified Python file and `tapps_validate_config()` on every Docker/compose file. No story is marked complete until the quality gate passes.

## Success Criteria

- [ ] All 52 services located under `domains/` in 9 group directories
- [ ] All shared libraries installable as 5 pip packages under `libs/`
- [ ] `docker compose up -d` starts all services from new structure
- [ ] `docker buildx bake full` builds all images in parallel
- [ ] All 152+ tests pass
- [ ] All CI pipelines trigger on correct domain paths
- [ ] No remaining references to old `services/` or `shared/` paths
- [ ] Architecture documentation reflects 9-domain structure
- [ ] TAPPS quality gates pass on all modified files

## References

- [Service Decomposition Plan](../docs/planning/service-decomposition-plan.md) — original 6-group plan (Option C)
- [Service Groups Architecture](../docs/architecture/service-groups.md) — canonical group definitions
- [Services Ranked by Importance](../docs/architecture/SERVICES_RANKED_BY_IMPORTANCE.md) — tier classification
- [Architecture Quick Reference](../docs/architecture/README_ARCHITECTURE_QUICK_REF.md) — current structure reference
- [Shared Patterns README](../libs/homeiq-patterns/README.md) — reusable pattern framework
- [Shared Resilience README](../libs/homeiq-resilience/README.md) — cross-group resilience utilities
