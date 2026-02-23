---
epic: reference-updates
initiative: domain-architecture-restructuring
initiative_epic: 4
priority: high
status: complete
estimated_duration: 7-10 days
risk_level: medium-high
source: docs/planning/service-decomposition-plan.md
---

# Epic: Reference Updates (Domain Architecture Restructuring — Epic 4)

**Status:** Complete
**Priority:** High
**Duration:** 7--10 days (completed in 1 session)
**Risk Level:** Medium--High
**PRD Reference:** `docs/planning/service-decomposition-plan.md`
**Initiative:** Domain Architecture Restructuring (Epic 4 of 4)
**Prerequisites:** Epic 1 (Folder Moves), Epic 2 (Shared Library Decomposition), Epic 3 (Compose File Restructuring)

## Overview

After Epics 1--3 restructure the physical layout of the monorepo, this epic performs the BULK of the mechanical work: updating every reference across the codebase that still points at the old paths. This covers Dockerfiles, Python imports, CI/CD workflows, documentation, and project configuration files.

**Scope of change:**
- **After Epic 1:** Services moved from `services/{name}/` to `domains/{group}/{name}/`
- **After Epic 2:** Shared modules moved from `shared/` to `libs/{package}/src/{package_name}/`
- **After Epic 3:** Compose files moved from `compose/` to `domains/{group}/compose.yml`

**Scale:** 50+ Dockerfiles, 30+ Python services with `sys.path` hacks, 6+ CI workflows, 40+ documentation files.

## Objectives

1. Zero broken imports after folder restructure
2. Zero broken Dockerfile builds
3. All CI pipelines trigger correctly on code changes
4. All documentation paths are accurate

## Success Criteria

- [ ] All Dockerfiles build successfully (`docker compose build` exits 0 for every group)
- [ ] All Python imports resolve (no `ModuleNotFoundError` at startup)
- [ ] All CI workflows trigger on correct paths (verified via dry-run or test push)
- [ ] All documentation paths are valid (no broken relative links)
- [ ] No remaining references to old `services/` or `shared/` paths (verified via grep)

---

## User Stories

### Story 1: Update Dockerfiles -- core-platform Group (5 Dockerfiles)

**As a** DevOps engineer
**I want** all core-platform Dockerfiles updated with correct paths and package installs
**So that** `docker compose build` succeeds for the core-platform group after folder restructuring

**Acceptance Criteria:**
- [ ] `COPY services/{name}/ /app/` changed to `COPY domains/core-platform/{name}/ /app/` (or build-context-relative equivalent)
- [ ] `COPY shared/ /app/shared/` replaced with `COPY libs/homeiq-patterns/ /tmp/libs/homeiq-patterns/` + `COPY libs/homeiq-data/ /tmp/libs/homeiq-data/` + `RUN pip install /tmp/libs/homeiq-patterns/ /tmp/libs/homeiq-data/`
- [ ] All 5 Dockerfiles build successfully in isolation
- [ ] Services start and pass health checks

**Files to modify:**
- `domains/core-platform/data-api/Dockerfile`
- `domains/core-platform/websocket-ingestion/Dockerfile`
- `domains/core-platform/admin-api/Dockerfile`
- `domains/core-platform/data-retention/Dockerfile`
- `domains/core-platform/health-dashboard/Dockerfile`

**Story Points:** 5
**Dependencies:** Epic 1 Story 2 (core-platform folder move), Epic 2 (all stories -- shared library packaging)
**Affected Services:** data-api (8006), websocket-ingestion (8001), admin-api (8004), data-retention (8080), health-dashboard (3000)

---

### Story 2: Update Dockerfiles -- data-collectors Group (8 Dockerfiles)

**As a** DevOps engineer
**I want** all data-collectors Dockerfiles updated with correct paths and package installs
**So that** `docker compose build` succeeds for the data-collectors group after folder restructuring

**Acceptance Criteria:**
- [ ] `COPY services/{name}/ /app/` changed to `COPY domains/data-collectors/{name}/ /app/`
- [ ] `COPY shared/ /app/shared/` replaced with `pip install` of relevant homeiq-* libs
- [ ] All 8 Dockerfiles build successfully in isolation
- [ ] Services start and pass health checks

**Files to modify:**
- `domains/data-collectors/weather-api/Dockerfile`
- `domains/data-collectors/smart-meter-service/Dockerfile`
- `domains/data-collectors/sports-api/Dockerfile`
- `domains/data-collectors/air-quality-service/Dockerfile`
- `domains/data-collectors/carbon-intensity-service/Dockerfile`
- `domains/data-collectors/electricity-pricing-service/Dockerfile`
- `domains/data-collectors/calendar-service/Dockerfile`
- `domains/data-collectors/log-aggregator/Dockerfile`

**Story Points:** 5
**Dependencies:** Epic 1 Story 3 (data-collectors folder move), Epic 2 (all stories)
**Affected Services:** weather-api (8009), smart-meter-service (8014), sports-api (8005), air-quality-service (8012), carbon-intensity-service (8010), electricity-pricing-service (8011), calendar-service (8013), log-aggregator (8015)

---

### Story 3: Update Dockerfiles -- ml-engine Group (10 Dockerfiles)

**As a** DevOps engineer
**I want** all ml-engine Dockerfiles updated with correct paths and package installs
**So that** `docker compose build` succeeds for the ml-engine group after folder restructuring

**Acceptance Criteria:**
- [ ] `COPY services/{name}/ /app/` changed to `COPY domains/ml-engine/{name}/ /app/`
- [ ] `COPY shared/ /app/shared/` replaced with `pip install` of relevant homeiq-* libs
- [ ] All 10 Dockerfiles build successfully in isolation
- [ ] Services start and pass health checks
- [ ] GPU-dependent services (openvino-service) verified with runtime flags

**Files to modify:**
- `domains/ml-engine/ai-core-service/Dockerfile`
- `domains/ml-engine/openvino-service/Dockerfile`
- `domains/ml-engine/ml-service/Dockerfile`
- `domains/ml-engine/ner-service/Dockerfile`
- `domains/ml-engine/openai-service/Dockerfile`
- `domains/ml-engine/rag-service/Dockerfile`
- `domains/ml-engine/ai-training-service/Dockerfile`
- `domains/ml-engine/device-intelligence-service/Dockerfile`
- `domains/ml-engine/model-prep/Dockerfile`
- `domains/ml-engine/nlp-fine-tuning/Dockerfile`

**Story Points:** 5
**Dependencies:** Epic 1 Story 4 (ml-engine folder move), Epic 2 (all stories)
**Affected Services:** ai-core-service (8018), openvino-service (8026), ml-service (8025), ner-service, openai-service (8020), rag-service (8027), ai-training-service (8033), device-intelligence-service (8028), model-prep, nlp-fine-tuning

---

### Story 4: Update Dockerfiles -- automation-core Group (7 Dockerfiles)

**As a** DevOps engineer
**I want** all automation-core Dockerfiles updated with correct paths and package installs
**So that** `docker compose build` succeeds for the automation-core group after folder restructuring

**Acceptance Criteria:**
- [ ] `COPY services/{name}/ /app/` changed to `COPY domains/automation-core/{name}/ /app/`
- [ ] `COPY shared/ /app/shared/` replaced with `pip install` of relevant homeiq-* libs
- [ ] All 7 Dockerfiles build successfully in isolation
- [ ] Services start and pass health checks

**Files to modify:**
- `domains/automation-core/ha-ai-agent-service/Dockerfile`
- `domains/automation-core/ai-automation-service-new/Dockerfile`
- `domains/automation-core/ai-query-service/Dockerfile`
- `domains/automation-core/ai-pattern-service/Dockerfile`
- `domains/automation-core/proactive-agent-service/Dockerfile`
- `domains/automation-core/automation-linter/Dockerfile`
- `domains/automation-core/yaml-validation-service/Dockerfile`

**Story Points:** 5
**Dependencies:** Epic 1 Story 5 (automation-core folder move), Epic 2 (all stories)
**Affected Services:** ha-ai-agent-service (8030), ai-automation-service-new (8036), ai-query-service (8035), ai-pattern-service (8034), proactive-agent-service (8031), automation-linter (8016), yaml-validation-service (8037)

---

### Story 5: Update Dockerfiles -- blueprints Group (4 Dockerfiles)

**As a** DevOps engineer
**I want** all blueprints Dockerfiles updated with correct paths and package installs
**So that** `docker compose build` succeeds for the blueprints group after folder restructuring

**Acceptance Criteria:**
- [ ] `COPY services/{name}/ /app/` changed to `COPY domains/blueprints/{name}/ /app/`
- [ ] `COPY shared/ /app/shared/` replaced with `pip install` of relevant homeiq-* libs
- [ ] All 4 Dockerfiles build successfully in isolation
- [ ] Services start and pass health checks

**Files to modify:**
- `domains/blueprints/blueprint-index/Dockerfile`
- `domains/blueprints/blueprint-suggestion-service/Dockerfile`
- `domains/blueprints/automation-miner/Dockerfile`
- `domains/blueprints/rule-recommendation-ml/Dockerfile`

**Story Points:** 3
**Dependencies:** Epic 1 Story 6 (blueprints folder move), Epic 2 (all stories)
**Affected Services:** blueprint-index (8038), blueprint-suggestion-service (8039), automation-miner (8029), rule-recommendation-ml (8040)

---

### Story 6: Update Dockerfiles -- energy-analytics Group (3 Dockerfiles)

**As a** DevOps engineer
**I want** all energy-analytics Dockerfiles updated with correct paths and package installs
**So that** `docker compose build` succeeds for the energy-analytics group after folder restructuring

**Acceptance Criteria:**
- [ ] `COPY services/{name}/ /app/` changed to `COPY domains/energy-analytics/{name}/ /app/`
- [ ] `COPY shared/ /app/shared/` replaced with `pip install` of relevant homeiq-* libs
- [ ] All 3 Dockerfiles build successfully in isolation
- [ ] Services start and pass health checks

**Files to modify:**
- `domains/energy-analytics/energy-correlator/Dockerfile`
- `domains/energy-analytics/energy-forecasting/Dockerfile`
- `domains/energy-analytics/api-automation-edge/Dockerfile`

**Story Points:** 2
**Dependencies:** Epic 1 Story 7 (energy-analytics folder move), Epic 2 (all stories)
**Affected Services:** energy-correlator (8017), energy-forecasting (8042), api-automation-edge (8041)

---

### Story 7: Update Dockerfiles -- device-management Group (8 Dockerfiles)

**As a** DevOps engineer
**I want** all device-management Dockerfiles updated with correct paths and package installs
**So that** `docker compose build` succeeds for the device-management group after folder restructuring

**Acceptance Criteria:**
- [ ] `COPY services/{name}/ /app/` changed to `COPY domains/device-management/{name}/ /app/`
- [ ] `COPY shared/ /app/shared/` replaced with `pip install` of relevant homeiq-* libs
- [ ] All 8 Dockerfiles build successfully in isolation
- [ ] Services start and pass health checks

**Files to modify:**
- `domains/device-management/device-health-monitor/Dockerfile`
- `domains/device-management/device-context-classifier/Dockerfile`
- `domains/device-management/device-setup-assistant/Dockerfile`
- `domains/device-management/device-database-client/Dockerfile`
- `domains/device-management/device-recommender/Dockerfile`
- `domains/device-management/activity-recognition/Dockerfile`
- `domains/device-management/activity-writer/Dockerfile`
- `domains/device-management/ha-setup-service/Dockerfile`

**Story Points:** 5
**Dependencies:** Epic 1 Story 8 (device-management folder move), Epic 2 (all stories)
**Affected Services:** device-health-monitor (8019), device-context-classifier (8032), device-setup-assistant (8021), device-database-client (8022), device-recommender (8023), activity-recognition (8043), activity-writer (8045), ha-setup-service (8024)

---

### Story 8: Update Dockerfiles -- pattern-analysis Group (2 Dockerfiles)

**As a** DevOps engineer
**I want** all pattern-analysis Dockerfiles updated with correct paths and package installs
**So that** `docker compose build` succeeds for the pattern-analysis group after folder restructuring

**Acceptance Criteria:**
- [ ] `COPY services/{name}/ /app/` changed to `COPY domains/pattern-analysis/{name}/ /app/`
- [ ] `COPY shared/ /app/shared/` replaced with `pip install` of relevant homeiq-* libs
- [ ] Both Dockerfiles build successfully in isolation
- [ ] Services start and pass health checks

**Files to modify:**
- `domains/pattern-analysis/automation-trace-service/Dockerfile`
- `domains/pattern-analysis/ai-code-executor/Dockerfile`

**Story Points:** 2
**Dependencies:** Epic 1 Story 9 (pattern-analysis folder move), Epic 2 (all stories)
**Affected Services:** automation-trace-service (8044), ai-code-executor

---

### Story 9: Update Dockerfiles -- frontends Group (3 Dockerfiles)

**As a** DevOps engineer
**I want** all frontends Dockerfiles updated with correct paths and package installs
**So that** `docker compose build` succeeds for the frontends group after folder restructuring

**Acceptance Criteria:**
- [ ] `COPY services/{name}/ /app/` changed to `COPY domains/frontends/{name}/ /app/`
- [ ] Frontend build contexts updated (Node/React services may have different COPY patterns)
- [ ] All 3 Dockerfiles build successfully in isolation
- [ ] Services start and respond on expected ports

**Files to modify:**
- `domains/frontends/ai-automation-ui/Dockerfile`
- `domains/frontends/observability-dashboard/Dockerfile`
- `domains/frontends/jaeger/Dockerfile` (if custom)

**Story Points:** 3
**Dependencies:** Epic 1 Story 10 (frontends folder move), Epic 2 (all stories)
**Affected Services:** ai-automation-ui (3001), observability-dashboard (8501), jaeger (16686)

---

### Story 10: Replace All sys.path Hacks with Package Imports

**As a** Python developer
**I want** every `sys.path.insert` hack that references `shared/` or the project root replaced with clean package imports
**So that** services use proper Python packaging and no longer depend on filesystem layout for imports

**Acceptance Criteria:**
- [ ] Every instance of `sys.path.insert(0, ...)` referencing shared/ or project root is removed
- [ ] Every instance of `Path(__file__).resolve().parents[N]` used for sys.path manipulation is removed
- [ ] `from shared.patterns.rag_context_service import RAGContextService` replaced with `from homeiq_patterns import RAGContextService`
- [ ] `from shared.patterns.unified_validation_router import ...` replaced with `from homeiq_patterns import ...`
- [ ] `from shared.patterns.post_action_verifier import ...` replaced with `from homeiq_patterns import ...`
- [ ] All resilience imports replaced with `from homeiq_resilience import ...`
- [ ] All data utility imports replaced with `from homeiq_data import ...`
- [ ] All HA client imports replaced with `from homeiq_ha import ...`
- [ ] All observability imports replaced with `from homeiq_observability import ...`
- [ ] All services start without `ModuleNotFoundError`
- [ ] Existing test suites pass (152 shared pattern tests + per-service tests)

**Current pattern (to find and replace):**
```python
try:
    _project_root = str(Path(__file__).resolve().parents[N])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass  # Docker: PYTHONPATH already includes /app
from shared.patterns.rag_context_service import RAGContextService
```

**Target pattern:**
```python
from homeiq_patterns import RAGContextService
```

**Story Points:** 8
**Dependencies:** Epic 2 (all stories -- shared library packaging complete with all homeiq-* packages published)
**Affected Services:** All Python services (~30 services across all domain groups)

---

### Story 11: Update All Service requirements.txt Files

**As a** Python developer
**I want** every service's `requirements.txt` updated with homeiq-* package dependencies
**So that** services declare their shared library dependencies explicitly and builds work in both local dev and Docker

**Acceptance Criteria:**
- [ ] Every service that imports from `homeiq_patterns` has `homeiq-patterns>=1.0.0` in `requirements.txt`
- [ ] Every service that imports from `homeiq_resilience` has `homeiq-resilience>=1.0.0` in `requirements.txt`
- [ ] Every service that imports from `homeiq_data` has `homeiq-data>=1.0.0` in `requirements.txt`
- [ ] Every service that imports from `homeiq_ha` has `homeiq-ha>=1.0.0` in `requirements.txt`
- [ ] Every service that imports from `homeiq_observability` has `homeiq-observability>=1.0.0` in `requirements.txt`
- [ ] Local dev: `-e ../../libs/homeiq-patterns` works via editable install
- [ ] Docker: `COPY libs/ /tmp/libs/ && pip install /tmp/libs/homeiq-patterns` works in Dockerfiles
- [ ] `pip install -r requirements.txt` succeeds for every service

**Story Points:** 5
**Dependencies:** Epic 2 (all stories -- homeiq-* packages defined with pyproject.toml)
**Affected Services:** All Python services (~30 services)

---

### Story 12: Rewrite CI/CD Workflows

**As a** DevOps engineer
**I want** all CI/CD workflow path triggers updated from `services/{name}/**` to `domains/{group}/{name}/**`
**So that** code changes trigger the correct group's build pipeline and shared library changes cascade to all dependents

**Acceptance Criteria:**
- [ ] All path triggers updated from `services/{name}/**` to `domains/{group}/{name}/**`
- [ ] 9 group-level workflows created (one per domain group), replacing existing per-service or monolithic workflows
- [ ] `libs/**` added to path triggers for groups that import homeiq-* packages
- [ ] `domains/{group}/compose.yml` changes trigger the relevant group's CI
- [ ] Shared library changes (`libs/homeiq-patterns/**`) cascade to all dependent group workflows via `workflow_dispatch`
- [ ] Concurrency groups configured to cancel superseded runs: `concurrency: { group: ci-$GROUP-${{ github.ref }}, cancel-in-progress: true }`
- [ ] Reusable workflow template `.github/workflows/reusable-group-ci.yml` handles lint, test, Docker build
- [ ] Dry-run validation: workflows trigger on test push to feature branch

**Files to modify:**
- `.github/workflows/*.yml` (all existing workflow files)
- New: `.github/workflows/ci-core-platform.yml`
- New: `.github/workflows/ci-data-collectors.yml`
- New: `.github/workflows/ci-ml-engine.yml`
- New: `.github/workflows/ci-automation-core.yml`
- New: `.github/workflows/ci-blueprints.yml`
- New: `.github/workflows/ci-energy-analytics.yml`
- New: `.github/workflows/ci-device-management.yml`
- New: `.github/workflows/ci-pattern-analysis.yml`
- New: `.github/workflows/ci-frontends.yml`
- New: `.github/workflows/reusable-group-ci.yml`

**Story Points:** 8
**Dependencies:** Epic 1 (all stories -- folder structure finalized), Epic 2 (all stories -- shared lib paths finalized)
**Affected Services:** All services (CI pipeline coverage)

---

### Story 13: Update All Documentation

**As a** developer reading project documentation
**I want** every reference to `services/`, `shared/`, and `compose/` updated to the new paths
**So that** documentation accurately reflects the repository structure and I can navigate the codebase without confusion

**Acceptance Criteria:**
- [ ] Every `.md` file referencing `services/{name}` updated to `domains/{group}/{name}`
- [ ] Every `.md` file referencing `shared/patterns/` updated to `libs/homeiq-patterns/`
- [ ] Every `.md` file referencing `compose/{name}.yml` updated to `domains/{group}/compose.yml`
- [ ] Architecture diagrams updated with new paths
- [ ] Service inventory tables updated with new locations
- [ ] All relative links verified (no broken `../` references)
- [ ] Grep for `services/` in `*.md` returns zero hits (excluding historical changelog entries)

**Key files to update:**
- `README.md`
- `TECH_STACK.md`
- `AGENTS.md`
- `docs/architecture/*.md`
- `docs/deployment/*.md`
- `docs/planning/*.md`
- `docs/architecture/SERVICES_RANKED_BY_IMPORTANCE.md` (moved from `services/`)
- `docs/architecture/README_ARCHITECTURE_QUICK_REF.md` (moved from `services/`)
- `libs/homeiq-patterns/README.md` (moved from `shared/patterns/`)
- All epic files in `stories/`

**Story Points:** 5
**Dependencies:** Epic 1 (all stories), Epic 2 (all stories), Epic 3 (all stories)
**Affected Services:** None (documentation only)

---

### Story 14: Update CLAUDE.md and Memory Files

**As a** developer using AI-assisted tooling
**I want** all path references in CLAUDE.md and project memory files updated to the new structure
**So that** AI assistants have accurate context about the repository layout and provide correct path suggestions

**Acceptance Criteria:**
- [ ] `CLAUDE.md` updated: all `services/` references changed to `domains/{group}/`
- [ ] `CLAUDE.md` updated: all `shared/` references changed to `libs/{package}/`
- [ ] `CLAUDE.md` updated: `sys.path` hack documentation replaced with package import pattern
- [ ] Memory files (`.claude/` project instructions) updated with new paths
- [ ] Pattern references updated (e.g., `shared/patterns/rag_context_service.py` becomes `libs/homeiq-patterns/src/homeiq_patterns/rag_context_service.py`)
- [ ] Service location references updated (e.g., `services/ha-ai-agent-service/` becomes `domains/automation-core/ha-ai-agent-service/`)

**Files to modify:**
- `CLAUDE.md`
- `.claude/` project instruction files
- Memory files referenced by AI tooling

**Story Points:** 2
**Dependencies:** Epic 1 (all stories), Epic 2 (all stories), Epic 3 (all stories)
**Affected Services:** None (AI tooling configuration only)

---

## Dependencies

```
Epic 1 (Folder Moves)
  ├─ Story 2 ──> Story 1  (core-platform Dockerfiles)
  ├─ Story 3 ──> Story 2  (data-collectors Dockerfiles)
  ├─ Story 4 ──> Story 3  (ml-engine Dockerfiles)
  ├─ Story 5 ──> Story 4  (automation-core Dockerfiles)
  ├─ Story 6 ──> Story 5  (blueprints Dockerfiles)
  ├─ Story 7 ──> Story 6  (energy-analytics Dockerfiles)
  ├─ Story 8 ──> Story 7  (device-management Dockerfiles)
  ├─ Story 9 ──> Story 8  (pattern-analysis Dockerfiles)
  └─ Story 10 ─> Story 9  (frontends Dockerfiles)

Epic 2 (Shared Library Decomposition)
  └─ All stories ──> Story 1-9  (Dockerfiles need lib COPY + pip install)
  └─ All stories ──> Story 10  (import replacement needs packages)
  └─ All stories ──> Story 11  (requirements.txt needs package names)

Epic 1 + Epic 2
  └─ All stories ──> Story 12  (CI paths depend on final folder + lib layout)

Epic 1 + Epic 2 + Epic 3
  └─ All stories ──> Story 13  (docs reference all three path sets)
  └─ All stories ──> Story 14  (CLAUDE.md references all paths)
```

**Simplified dependency graph:**

```
Epic 1 (folders) + Epic 2 (libs)
         │
         ├──────────────────────────────────┐
         │                                  │
         ▼                                  ▼
  Stories 1-9 (Dockerfiles)          Story 10 (sys.path)
  [parallelizable by group]          Story 11 (requirements.txt)
         │                                  │
         └──────────┬───────────────────────┘
                    │
                    ▼
             Story 12 (CI/CD)
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
    + Epic 3    Story 13    Story 14
   (compose)    (docs)     (CLAUDE.md)
```

---

## Suggested Execution Order

| Phase | Stories | Parallelizable | Rationale |
|-------|---------|----------------|-----------|
| **Phase A** | Stories 1--9 (Dockerfiles) | Yes -- 9 agents, one per group | Highest volume, mechanical, independently testable per group |
| **Phase B** | Stories 10--11 (imports + requirements) | Partially -- Story 10 can split by group | Must complete after Epic 2; Story 11 depends on Story 10 choices |
| **Phase C** | Story 12 (CI/CD) | No | Requires final folder + lib layout from Phases A--B |
| **Phase D** | Stories 13--14 (docs + CLAUDE.md) | Yes -- 2 agents | Independent of each other; requires Epics 1--3 complete |

**Critical path:** Epic 1 + Epic 2 --> Stories 1--9 (parallel) --> Story 12 --> Story 13

---

## Agent Team Strategy

### Recommended Team Composition

| Agent | Role | Stories | Estimated Duration |
|-------|------|---------|-------------------|
| **dockerfile-core** | Dockerfile updater | Story 1 | 0.5 days |
| **dockerfile-collectors** | Dockerfile updater | Story 2 | 0.5 days |
| **dockerfile-ml** | Dockerfile updater | Story 3 | 0.5 days |
| **dockerfile-automation** | Dockerfile updater | Story 4 | 0.5 days |
| **dockerfile-blueprints** | Dockerfile updater | Story 5 | 0.5 days |
| **dockerfile-energy** | Dockerfile updater | Story 6 | 0.5 days |
| **dockerfile-devices** | Dockerfile updater | Story 7 | 0.5 days |
| **dockerfile-patterns** | Dockerfile updater | Story 8 | 0.5 days |
| **dockerfile-frontends** | Dockerfile updater | Story 9 | 0.5 days |
| **import-replacer** | Python import migration | Stories 10--11 | 2--3 days |
| **ci-updater** | CI/CD workflow rewrite | Story 12 | 2 days |
| **docs-updater** | Documentation paths | Stories 13--14 | 1--2 days |
| **quality-watchdog** | Validates builds/tests | Cross-cutting | Continuous |

### Parallelization Notes

- **Stories 1--9:** Fully parallelizable. Each agent works on one domain group's Dockerfiles. No cross-group conflicts. Assign one agent per group for maximum throughput.
- **Story 10:** Can be split by domain group for parallel agents (each agent handles imports for services in one group), but requires coordination to avoid merge conflicts in shared test files.
- **Story 12 and Story 13:** Independent of each other and parallelizable after Phase A--B complete.
- **Quality watchdog:** Runs `docker compose build` per group after each Dockerfile story completes. Runs `python -c "import homeiq_patterns"` per service after Story 10.

### Dockerfile Update Pattern (for all agents)

**Current pattern:**
```dockerfile
COPY services/data-api/ /app/
COPY shared/ /app/shared/
```

**Target pattern:**
```dockerfile
COPY domains/core-platform/data-api/ /app/
COPY libs/homeiq-patterns/ /tmp/libs/homeiq-patterns/
COPY libs/homeiq-data/ /tmp/libs/homeiq-data/
RUN pip install /tmp/libs/homeiq-patterns/ /tmp/libs/homeiq-data/
```

### Import Replacement Pattern (for Story 10 agent)

**Current pattern:**
```python
try:
    _project_root = str(Path(__file__).resolve().parents[N])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass  # Docker: PYTHONPATH already includes /app
from shared.patterns.rag_context_service import RAGContextService
```

**Target pattern:**
```python
from homeiq_patterns import RAGContextService
```

---

## Implementation Artifacts

| Artifact | Current Path | New Path |
|----------|-------------|----------|
| **Dockerfiles (50+)** | `services/{name}/Dockerfile` | `domains/{group}/{name}/Dockerfile` |
| **Compose files** | `compose/{group}.yml` | `domains/{group}/compose.yml` |
| **Shared patterns** | `shared/patterns/` | `libs/homeiq-patterns/src/homeiq_patterns/` |
| **Shared resilience** | `shared/resilience/` | `libs/homeiq-resilience/src/homeiq_resilience/` |
| **Shared data** | `shared/data/` | `libs/homeiq-data/src/homeiq_data/` |
| **Shared HA** | `shared/ha/` | `libs/homeiq-ha/src/homeiq_ha/` |
| **Shared observability** | `shared/observability/` | `libs/homeiq-observability/src/homeiq_observability/` |
| **CI workflows** | `.github/workflows/*.yml` | `.github/workflows/ci-{group}.yml` + `reusable-group-ci.yml` |
| **Service requirements** | `services/{name}/requirements.txt` | `domains/{group}/{name}/requirements.txt` |
| **Project docs** | `README.md`, `TECH_STACK.md`, `AGENTS.md` | Same files, updated paths |
| **AI config** | `CLAUDE.md` | Same file, updated paths |
| **Architecture docs** | `docs/architecture/*.md` | Same files, updated paths |
| **Deployment docs** | `docs/deployment/*.md` | Same files, updated paths |
| **Epic files** | `stories/epic-*.md` | Same files, updated paths |
| **Service inventory** | `services/SERVICES_RANKED_BY_IMPORTANCE.md` | `docs/architecture/SERVICES_RANKED_BY_IMPORTANCE.md` |
| **Architecture quick ref** | `services/README_ARCHITECTURE_QUICK_REF.md` | `docs/architecture/README_ARCHITECTURE_QUICK_REF.md` |

---

## Story Point Summary

| Story | Description | Points |
|-------|-------------|--------|
| Story 1 | Dockerfiles -- core-platform (5) | 5 |
| Story 2 | Dockerfiles -- data-collectors (8) | 5 |
| Story 3 | Dockerfiles -- ml-engine (10) | 5 |
| Story 4 | Dockerfiles -- automation-core (7) | 5 |
| Story 5 | Dockerfiles -- blueprints (4) | 3 |
| Story 6 | Dockerfiles -- energy-analytics (3) | 2 |
| Story 7 | Dockerfiles -- device-management (8) | 5 |
| Story 8 | Dockerfiles -- pattern-analysis (2) | 2 |
| Story 9 | Dockerfiles -- frontends (3) | 3 |
| Story 10 | Replace sys.path hacks | 8 |
| Story 11 | Update requirements.txt files | 5 |
| Story 12 | Rewrite CI/CD workflows | 8 |
| Story 13 | Update documentation | 5 |
| Story 14 | Update CLAUDE.md + memory | 2 |
| **Total** | | **63** |

---

## Verification Checklist

After all stories are complete, run the following verification sweep:

```bash
# 1. Verify no remaining old-path references
grep -r "services/" --include="*.py" --include="*.yml" --include="*.yaml" \
  --include="Dockerfile" --include="*.md" . | grep -v "node_modules" | grep -v ".git"

grep -r "shared/" --include="*.py" --include="*.yml" --include="*.yaml" \
  --include="Dockerfile" . | grep -v "node_modules" | grep -v ".git"

grep -r "compose/" --include="*.yml" --include="*.yaml" --include="*.md" \
  . | grep -v "node_modules" | grep -v ".git"

# 2. Verify all Dockerfiles build
for group in core-platform data-collectors ml-engine automation-core \
  blueprints energy-analytics device-management pattern-analysis frontends; do
  docker compose -f domains/$group/compose.yml build
done

# 3. Verify all Python imports resolve
for group in domains/*/; do
  for service in $group*/; do
    if [ -f "$service/src/main.py" ]; then
      python -c "import importlib; importlib.import_module('$(basename $service).src.main')" 2>&1
    fi
  done
done

# 4. Verify sys.path hacks are gone
grep -rn "sys.path.insert" --include="*.py" . | grep -v "node_modules" | grep -v ".git" | grep -v "test"
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Merge conflicts from parallel Dockerfile edits | Low | Low | Each agent works in a separate domain directory -- no overlap |
| Missed `sys.path` hack in obscure service | Medium | Medium | Comprehensive grep + runtime import verification |
| CI workflow path triggers miss edge cases | Medium | High | Dry-run workflow validation on feature branch before merge |
| Documentation update misses a file | Medium | Low | Automated grep verification in checklist |
| Docker build context size increases from lib COPY | Low | Medium | Use `.dockerignore` to exclude tests/docs from lib copies |
| Circular import introduced during migration | Low | High | Run `homeiq_dependency_graph` after Story 10 |

---

## References

- [PRD: Service Decomposition Plan](../docs/planning/service-decomposition-plan.md)
- [Epic: Reusable Pattern Framework](epic-reusable-pattern-framework.md) (defines shared patterns being repackaged)
- [Epic: Platform-Wide Pattern Rollout](epic-platform-wide-pattern-rollout.md) (defines services using shared patterns)
- [Service Inventory](../docs/architecture/SERVICES_RANKED_BY_IMPORTANCE.md)
- [Architecture Quick Reference](../docs/architecture/README_ARCHITECTURE_QUICK_REF.md)
