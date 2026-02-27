# Implementation Plan: Service Decomposition (Option C — Criticality + Domain Hybrid)

**Document Type:** Implementation Plan
**Status:** Complete (All 5 Epics done; extended to 9 domains; CI/CD Phase 3 6/7 complete, step 3.7 remaining; Phase 4 Resilience 7/7 complete)
**Created:** February 2026
**Epic Reference:** Domain Architecture Restructuring (see `stories/epic-domain-architecture-restructuring.md`)
**Approach:** Option C — Criticality + Domain Hybrid (extended from 6 groups to 9 domains)

> **Note (2026-02-23):** The original 6-group plan was implemented and then extended to 9 domains by splitting `automation-intelligence` (16 services) into 4 sub-domains: automation-core (7), blueprints (4), energy-analytics (3), pattern-analysis (2). Epics 1-4 are complete. See `stories/epic-domain-architecture-restructuring.md` for current status.
**Reviewed Against:** Docker Compose v2.20+ best practices, GitHub Actions monorepo patterns, Python packaging standards, microservices resilience patterns
**Verified Environment:** Docker Desktop v4.61.0, Docker Engine v29.2.1, Docker Compose v5.0.2, WSL 2 backend (Windows 11 Pro)

---

## Executive Summary

HomeIQ currently runs 52 microservices in a single monorepo with a single `docker-compose.yml`. This plan decomposes them into **6 independently deployable groups** based on deployment criticality and domain boundaries. The goal is to enable independent scaling, faster CI/CD, clearer ownership, and blast-radius isolation — without breaking the existing architecture.

### Why Option C

| Criteria | Score | Rationale |
|----------|-------|-----------|
| Failure isolation | High | core-platform survives if ML or automation groups crash |
| Scaling profile match | High | GPU-heavy ML vs stateless collectors vs HA-critical core |
| Deploy cadence alignment | High | Core deploys rarely; frontends and ML deploy frequently |
| Group balance | Good | No group exceeds 16 services (vs 33 in data-flow option) |
| Dependency direction | Clean | Acyclic — all groups depend downward toward core-platform |

---

## Completion Summary

> **Added 2026-02-24 (Story 7, Epic 5):** This section documents final outcomes after Epics 1-4 were completed.

### Migration Outcome

The original plan defined **6 groups**. During implementation, the `automation-intelligence` group (16 services) proved too large for a single ownership boundary. It was split into **4 sub-domains**, bringing the total to **9 domains**:

| Original Group | Final Domain(s) | Service Count |
|----------------|-----------------|---------------|
| core-platform | core-platform | 6 (+ha-simulator) |
| data-collectors | data-collectors | 8 |
| ml-engine | ml-engine | 10 |
| automation-intelligence (16) | automation-core | 7 |
| | blueprints | 4 |
| | energy-analytics | 3 |
| | pattern-analysis | 2 |
| device-management | device-management | 8 |
| frontends | frontends | 4 (+jaeger) |

### Epic Links

All implementation work is tracked across 5 epics:

| Epic | File | Status |
|------|------|--------|
| Epic 1: Domain Folder Restructuring | `stories/epic-domain-folder-restructuring.md` | Complete (Feb 2026) |
| Epic 2: Shared Library Decomposition | `stories/epic-shared-library-decomposition.md` | Complete (Feb 2026) |
| Epic 3: Docker Modernization | `stories/epic-docker-modernization.md` | Complete (Feb 2026) |
| Epic 4: Reference Updates | `stories/epic-reference-updates.md` | Complete (Feb 2026) |
| Epic 5: Validation and Cleanup | `stories/epic-validation-and-cleanup.md` | Complete (Feb 2026) |

### Completion Timeline

- **Epics 1-5:** Completed February 2026 (all 12 Epic 5 stories done — 47/49 services healthy, 704 tests passing, 70 Python files validated)
- **Phase 3 CI/CD:** 6/7 steps complete (steps 3.1-3.6 implemented, step 3.5 done 2026-02-27). Remaining: step 3.7 (deprecate monolithic `test.yml`)
- **Phase 4 Resilience:** 7/7 steps complete (4.1-4.4 done Feb 2026, 4.5-4.7 done 2026-02-27)

---

## The 6 Groups

### Group 1: `core-platform` (6 services)

**Purpose:** The data backbone. If this is down, everything is down. Deployed rarely, tested heavily, always-on HA.

| Service | Port | Role |
|---------|------|------|
| influxdb | 8086 | Time-series database — all sensor/event data |
| data-api | 8006 | Central query hub — every service reads through this |
| websocket-ingestion | 8001 | Primary HA event capture → InfluxDB writer |
| admin-api | 8004 | System control plane, health checks, config |
| health-dashboard | 3000 | Primary user UI (React/Vite) |
| data-retention | 8080 | Data lifecycle — cleanup, compression, rotation |

**Depends on:** Nothing (root of dependency tree)
**Depended on by:** All other groups
**Compose file:** `domains/core-platform/compose.yml`
**Deploy cadence:** Low — changes require staging + canary
**Resource profile:** High availability, persistent volumes, health-checked

**Existing reference:** `docker-compose.minimal.yml` already contains influxdb + data-api — extend this.

---

### Group 2: `data-collectors` (8 services)

**Purpose:** Stateless data fetchers. Each service polls an external API on a schedule and writes to InfluxDB. Independently restartable, no cross-dependencies.

| Service | Port | External Source |
|---------|------|-----------------|
| weather-api | 8009 | OpenWeatherMap |
| smart-meter-service | 8014 | Home Assistant power entities |
| sports-api | 8005 | ESPN / HA Team Tracker |
| air-quality-service | 8012 | OpenWeatherMap AQI |
| carbon-intensity-service | 8010 | WattTime |
| electricity-pricing-service | 8011 | Energy pricing provider |
| calendar-service | 8013 | HA calendar entities |
| log-aggregator | 8015 | Docker socket / service logs |

**Depends on:** Group 1 (influxdb write, data-api metadata)
**Depended on by:** Groups 3, 4 (indirect — via InfluxDB data)
**Compose file:** `domains/data-collectors/compose.yml`
**Deploy cadence:** Medium — per-API contract change
**Resource profile:** Lightweight, stateless, low memory (128-256MB each)

**Key characteristic:** Every service follows the same pattern:
```
Scheduled fetch → transform → InfluxDB write
```
All are independently deployable and restartable with zero impact on other collectors.

---

### Group 3: `ml-engine` (10 services)

**Purpose:** All ML model inference, embedding generation, and training. Heaviest compute requirements (GPU/high memory). Changes driven by model updates, not feature work.

| Service | Port | Role |
|---------|------|------|
| ai-core-service | 8018 | ML orchestrator — routes to inference backends |
| openvino-service | 8026 | Transformer embeddings, semantic search, reranking |
| ml-service | 8025 | Classical ML — clustering, anomaly detection |
| ner-service | (internal 8031) | BERT-based Named Entity Recognition |
| openai-service | 8020 | OpenAI API client wrapper (GPT-5.2-codex) |
| rag-service | 8027 | Retrieval-Augmented Generation + vector search |
| ai-training-service | 8033 | Soft prompt training, model fine-tuning |
| device-intelligence-service | 8028 | 6,000+ device capability mapping (ML models) |
| model-prep | (one-shot) | HuggingFace model download/cache |
| nlp-fine-tuning | (one-shot) | NLP model fine-tuning pipeline |

**Depends on:** Group 1 (data-api for entity/device metadata)
**Depended on by:** Group 4 (automation calls ML for inference), Group 5 (device classification)
**Compose file:** `domains/ml-engine/compose.yml`
**Deploy cadence:** Frequent — model updates, library upgrades
**Resource profile:** GPU-capable, high memory (512MB-1.5GB per service), CPU-intensive

**Internal dependency chain:**
```
openvino-service (embeddings)
        ↓
ml-service (classical ML)
        ↓
ner-service (NER)           → ai-core-service (orchestrator)
        ↓
openai-service (LLM)
```
ai-core-service depends on openvino, ml-service, ner-service, and openai-service. These should always deploy together.

---

### Group 4: `automation-intelligence` (16 services)

**Purpose:** Everything related to automation generation, suggestion, validation, and deployment. The feature-richest group — most active development happens here.

| Service | Port | Role |
|---------|------|------|
| ha-ai-agent-service | 8030 | HA AI agent — context building, entity resolution, GUI automation path |
| ai-automation-service-new | 8036 | Core automation engine — NL → YAML (CLI path) |
| ai-query-service | 8035 | Natural language query interface |
| ai-pattern-service | 8034 | Pattern detection, synergy analysis |
| ai-code-executor | (internal) | Safe code execution sandbox |
| automation-miner | 8029 | Community automation crawler (Discourse/GitHub) |
| automation-linter | 8016 | YAML validation and linting |
| yaml-validation-service | 8037 | Unified schema/entity/service validation |
| blueprint-index | 8038 | Blueprint metadata indexing and search |
| blueprint-suggestion-service | 8039 | Automation suggestions based on user devices |
| rule-recommendation-ml | 8040 | ML-powered automation recommendations |
| api-automation-edge | 8041 | Edge computing for API-driven automations |
| proactive-agent-service | 8031 | Proactive recommendations and suggestions |
| energy-correlator | 8017 | Device-power causality analysis |
| energy-forecasting | 8042 | 7-day energy consumption predictions |
| automation-trace-service | 8044 | HA automation trace + logbook ingestion |

**Depends on:** Group 1 (data-api), Group 3 (ML inference via ai-core-service)
**Depended on by:** Group 6 (frontends display automation results)
**Compose file:** `domains/automation-core/compose.yml`
**Deploy cadence:** High — most active feature development
**Resource profile:** Medium, CPU-bound (256MB-512MB each)

**Internal dependency chain:**
```
ha-ai-agent-service
    ├→ ai-automation-service-new → yaml-validation-service
    ├→ ai-query-service
    ├→ ai-pattern-service
    └→ proactive-agent-service

blueprint-suggestion-service → blueprint-index
                             → ai-pattern-service
```

---

### Group 5: `device-management` (8 services)

**Purpose:** Device lifecycle — health monitoring, onboarding, classification, activity recognition. Medium churn, independent of automation features.

| Service | Port | Role |
|---------|------|------|
| device-health-monitor | 8019 | Device health tracking, battery monitoring |
| device-context-classifier | 8032 | Room/location inference |
| device-setup-assistant | 8021 | Guided device onboarding |
| device-database-client | 8022 | Device data access layer + caching |
| device-recommender | 8023 | Device upgrade suggestions |
| activity-recognition | 8043 | LSTM/ONNX user activity detection |
| activity-writer | 8045 | Periodic activity prediction pipeline |
| ha-setup-service | 8024 | HA health checks, integration monitoring |

**Depends on:** Group 1 (data-api), Group 3 (device-intelligence-service for classification)
**Depended on by:** Group 4 (automation uses device context)
**Compose file:** `domains/device-management/compose.yml`
**Deploy cadence:** Medium
**Resource profile:** Low-medium (128-512MB each)

---

### Group 6: `frontends` (3 services + infra)

**Purpose:** User-facing UIs and observability tooling. Fast iteration, independent build pipelines (Node/React vs Python).

| Service | Port | Role |
|---------|------|------|
| health-dashboard | 3000 | Primary user UI (React/Vite/TypeScript) |
| ai-automation-ui | 3001 | AI automation web UI (React) |
| observability-dashboard | 8501 | Monitoring dashboard (Streamlit) |
| jaeger | 16686 | Distributed tracing UI |

**Depends on:** Group 1 (admin-api, data-api), Group 4 (automation endpoints)
**Compose file:** `domains/frontends/compose.yml`
**Deploy cadence:** High — UI iteration is fast
**Resource profile:** Lightweight, CDN-friendly static assets

**Note:** `health-dashboard` appears in both Group 1 and Group 6. It is **developed** with frontends but **deployed** with core-platform for availability. The core compose includes it; the frontend compose includes only ai-automation-ui and observability-dashboard as overrides.

---

## Dependency Graph (Groups)

```
                    ┌──────────────────────────┐
                    │   Group 1: core-platform  │
                    │ (InfluxDB, data-api,      │
                    │  websocket, admin, dash,  │
                    │  data-retention)           │
                    └────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
  ┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐
  │ Group 2:      │   │ Group 3:         │   │ Group 5:         │
  │ data-         │   │ ml-engine        │   │ device-          │
  │ collectors    │   │ (ai-core,        │   │ management       │
  │ (weather,     │   │  openvino, ML,   │   │ (health, setup,  │
  │  smart-meter, │   │  NER, OpenAI,    │   │  classifier,     │
  │  sports, etc) │   │  RAG, training)  │   │  activity)       │
  └───────────────┘   └────────┬─────────┘   └──────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Group 4: automation- │
                    │ intelligence         │
                    │ (ha-ai-agent,        │
                    │  ai-automation,      │
                    │  patterns, blueprints│
                    │  energy, traces)     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Group 6: frontends   │
                    │ (ai-automation-ui,   │
                    │  observability,      │
                    │  jaeger)             │
                    └──────────────────────┘
```

**Key property:** No circular dependencies. Every arrow points downward from core-platform. Groups 2, 3, and 5 are siblings (no inter-dependency). Group 4 depends on Group 3 for ML. Group 6 depends on Groups 1 and 4.

---

## Implementation Phases

### Phase 0: Preparation (Low Risk) -- COMPLETE

**Goal:** Validate the grouping without changing any runtime behavior.

| Step | Task | Files Affected | Risk |
|------|------|----------------|------|
| 0.1 | Create `docker/` directory for group compose files | New directory | None |
| 0.2 | Extract shared network, volume, and env definitions into `docker-compose.base.yml` | New file | None |
| 0.3 | Create service inventory spreadsheet mapping each service → group | Documentation only | None |
| 0.4 | Audit `libs/homeiq-patterns/` imports — which groups use which shared modules | Documentation only | None |
| 0.5 | Audit environment variables — identify cross-group env vars vs group-local | Documentation only | None |

**Deliverable:** Verified service-to-group mapping with no ambiguity.

---

### Phase 1: Compose File Split (Low-Medium Risk) -- COMPLETE

**Goal:** Split the monolithic `docker-compose.yml` into 6 group-specific compose files using the Docker Compose `include` directive (v2.20+).

> **Completion Note (Feb 2026):** Implemented with **9 domain compose files** (not 6) under `domains/{group}/compose.yml`. The root `docker-compose.yml` includes all 9 via the `include` directive. No separate `compose/` directory was created; compose files live directly inside each domain folder.

> **Best Practice Note:** The `include` directive is preferred over the `-f` flag approach. Each included file is parsed as its own Compose application model with its own project directory for relative path resolution. This avoids the long `-f` chains and makes per-group `.env` files possible. See [Docker Compose Include Docs](https://docs.docker.com/compose/how-tos/multiple-compose-files/include/).

| Step | Task | Details |
|------|------|---------|
| 1.1 | Create `domains/` directory structure | Houses all group compose files and per-group `.env` files |
| 1.2 | Create `domains/core-platform/compose.yml` + `.env` | influxdb, data-api, websocket-ingestion, admin-api, health-dashboard, data-retention. Defines `homeiq-network` and shared volumes. |
| 1.3 | Create `domains/data-collectors/compose.yml` + `.env` | 8 data collector services. Each uses `external: true` for `homeiq-network`. |
| 1.4 | Create `domains/ml-engine/compose.yml` + `.env` | 10 ML services with internal dependency chain |
| 1.5 | Create `domains/automation-core/compose.yml` + `.env` | 16 automation services |
| 1.6 | Create `domains/device-management/compose.yml` + `.env` | 8 device management services |
| 1.7 | Create `domains/frontends/compose.yml` + `.env` | 3 frontend + Jaeger services |
| 1.8 | Create root `docker-compose.yml` using `include` | Replaces monolithic file — includes all 6 group files |
| 1.9 | Verify: `docker compose config` matches original | Zero-diff validation |
| 1.10 | Archive original as `docker-compose.yml.bak` | Rollback safety net |

**Root `docker-compose.yml` after split (using `include` directive):**
```yaml
# docker-compose.yml — includes all groups
include:
  - path: domains/core-platform/compose.yml
    env_file: domains/core-platform/.env
  - path: domains/data-collectors/compose.yml
    env_file: domains/data-collectors/.env
  - path: domains/ml-engine/compose.yml
    env_file: domains/ml-engine/.env
  - path: domains/automation-core/compose.yml
    env_file: domains/automation-core/.env
  - path: domains/device-management/compose.yml
    env_file: domains/device-management/.env
  - path: domains/frontends/compose.yml
    env_file: domains/frontends/.env
```

**Per-group standalone usage (the key benefit):**
```bash
# Full stack (just use root compose — same as before)
docker compose up -d

# Core only (minimal)
docker compose -f domains/core-platform/compose.yml up -d

# Core + collectors only (data pipeline without AI)
docker compose -f domains/core-platform/compose.yml -f domains/data-collectors/compose.yml up -d

# Development: full stack + dev tools
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**Per-group `.env` files (best practice):**
Each group gets its own `.env` file for environment isolation:
- `domains/core-platform/.env` — INFLUXDB_TOKEN, DATABASE_URL, API_KEY
- `domains/data-collectors/.env` — OPENWEATHERMAP_KEY, WATTTIME_USERNAME, etc.
- `domains/ml-engine/.env` — OPENAI_API_KEY, MODEL_CACHE_DIR, GPU_DEVICE
- `domains/automation-core/.env` — HA_URL, HA_TOKEN
- `domains/device-management/.env` — HA_URL, HA_TOKEN
- `domains/frontends/.env` — API_BASE_URL, VITE_* vars

**Network strategy:**
- `domains/core-platform/compose.yml` defines `homeiq-network` as a named network
- All other group files reference it as `external: true`
- This allows groups to communicate when co-deployed but doesn't crash when deployed alone

```yaml
# In domains/core-platform/compose.yml
networks:
  homeiq-network:
    name: homeiq-network

# In domains/data-collectors/compose.yml (and all other groups)
networks:
  homeiq-network:
    external: true
```

**Cross-group `depends_on` handling:**
- **Remove all cross-group `depends_on`** from the compose files. Cross-group dependencies should be handled at the application level, not the orchestrator level.
- **Reason:** `depends_on` only works when services are in the same compose project. With `include`, they are separate projects. Instead, services must use application-level health checks and retry logic (see Phase 4).
- **Intra-group `depends_on`** are kept (e.g., `ai-core-service` → `openvino-service` within ml.yml).

**Conflict prevention:**
- The `include` directive reports errors if any service name conflicts across included files
- Ensure no service appears in more than one group file
- `health-dashboard` lives **only** in `domains/core-platform/compose.yml` (not duplicated in frontends)

**Deliverable:** 6 group compose files + root include file. `docker compose config` output matches original service definitions. No runtime changes.

---

### Phase 2: Shared Library Packaging (Medium Risk) -- COMPLETE

**Goal:** Extract `libs/homeiq-patterns/` (formerly `shared/patterns/`) into an installable Python package so groups don't need the full monorepo to build.

> **Completion Note (Feb 2026):** Implemented with **5 installable packages** under `libs/`: homeiq-patterns, homeiq-resilience, homeiq-observability, homeiq-data, homeiq-ha. All use `pyproject.toml` with src-layout and are installed in Dockerfiles via `COPY libs/ /tmp/libs/ && pip install /tmp/libs/homeiq-*/`.

> **Best Practice Note:** Use `pyproject.toml` with setuptools (simplest) or hatch (modern). For a monorepo, editable installs (`pip install -e`) during development and published packages for Docker builds is the recommended dual-mode approach. See [Python Packaging Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) and [Python Monorepo with UV](https://tomasrepcik.dev/blog/2025/2025-10-26-python-workspaces/).

| Step | Task | Details |
|------|------|---------|
| 2.1 | Add `pyproject.toml` to `libs/homeiq-patterns/` | Package name: `homeiq-patterns`, version managed via git tags |
| 2.2 | Define package structure | `src/homeiq_patterns/` layout with `__init__.py` re-exporting `RAGContextService`, `UnifiedValidationRouter`, `PostActionVerifier` |
| 2.3 | Pin shared dependencies | All third-party deps used by patterns go in `pyproject.toml [project.dependencies]` with version ranges |
| 2.4 | Add development install support | `pip install -e libs/homeiq-patterns/` for local development (editable mode) |
| 2.5 | Update all service `requirements.txt` | Replace `sys.path` hacks with `homeiq-patterns>=1.0.0` |
| 2.6 | Update all service Dockerfiles | Replace shared lib COPY with `pip install homeiq-patterns` |
| 2.7 | Choose distribution method (see decision matrix below) | Recommended: `pip install git+https://` for simplicity |
| 2.8 | Update CI to build + publish on `libs/homeiq-patterns/**` change | Trigger downstream group rebuilds via `workflow_dispatch` |
| 2.9 | Run full test suite (152 pattern tests + per-service tests) | Verify no regressions |

**`pyproject.toml` for libs/homeiq-patterns/:**
```toml
[build-system]
requires = ["setuptools>=68.0", "setuptools-scm>=8.0"]
build-backend = "setuptools.build_meta"

[project]
name = "homeiq-patterns"
dynamic = ["version"]
requires-python = ">=3.11"
dependencies = []  # Add shared deps here

[tool.setuptools-scm]
root = "../.."  # Git root relative to this file

[tool.setuptools.packages.find]
where = ["src"]
```

**Distribution method decision matrix:**

| Method | Setup Effort | Build Speed | Version Pinning | Recommended For |
|--------|-------------|-------------|-----------------|-----------------|
| `pip install git+https://github.com/org/repo#subdirectory=libs/homeiq-patterns` | Low | Medium | Git tags/SHAs | Small teams, monorepo stays |
| GitHub Packages (PyPI) | Medium | Fast (cached) | Semver | Larger teams, frequent publishes |
| Local path in Docker (`COPY + pip install -e .`) | None | Fast | Always latest | Interim migration step |

**Recommended approach:** Start with **local path** (step 2.4) for the initial migration to validate imports work, then move to **git+https** for Docker builds. Upgrade to GitHub Packages only if publish frequency justifies it.

**`sys.path` hack removal:**
Currently services use this pattern:
```python
try:
    _project_root = str(Path(__file__).resolve().parents[N])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass  # Docker: PYTHONPATH already includes /app
```
This gets replaced with:
```python
from homeiq_patterns import RAGContextService, UnifiedValidationRouter, PostActionVerifier
```

**Migration safety:** Do the replacement service-by-service, not all at once. Each service gets a PR that:
1. Adds `homeiq-patterns` to its `requirements.txt`
2. Removes `sys.path` manipulation
3. Updates imports
4. Runs that service's tests

**Deliverable:** `libs/homeiq-patterns/` is a pip-installable package. No service needs the full repo to build.

---

### Phase 3: CI/CD Pipeline Split (Medium Risk) -- 6/7 COMPLETE

**Goal:** Each group gets its own CI pipeline. Changes to Group 2 don't trigger Group 3 builds. Shared library changes cascade to all dependent groups.

> **Status Note (Feb 2026):** Steps 3.1-3.6 are implemented. 9 domain CI workflows + reusable template + shared lib cascade + cross-group integration tests all exist in `.github/workflows/`. Remaining: step 3.7 (deprecate monolithic `test.yml`).

> **Best Practice Note:** Use reusable workflows to avoid duplication, concurrency groups to cancel superseded runs, and `workflow_dispatch` for cascade rebuilds. See [GitHub Actions Monorepo Guide](https://oneuptime.com/blog/post/2026-02-02-github-actions-monorepos/view) and [Monorepo Path Filters](https://oneuptime.com/blog/post/2025-12-20-monorepo-path-filters-github-actions/view).

| Step | Task | Details | Status |
|------|------|---------|--------|
| 3.1 | Create reusable workflow template | `.github/workflows/reusable-group-ci.yml` — lint, test, Docker build for any service list | Done |
| 3.2 | Create path-scoped workflows per group | 9 workflow files (expanded from 6) that call the reusable template | Done |
| 3.3 | Add concurrency groups per workflow | `concurrency: { group: ci-$GROUP-${{ github.ref }}, cancel-in-progress: true }` | Done |
| 3.4 | Add shared library publish + cascade workflow | Triggers on `libs/**`, publishes package, dispatches all 9 group CIs | Done |
| 3.5 | Add cross-group integration test workflow | `.github/workflows/integration-tests.yml` — 5 jobs: core-connectivity, cross-domain-api, health-aggregation, shared-lib-compat, integration-summary. Fixtures at `tests/integration/cross_group/` | Done (2026-02-27) |
| 3.6 | Add path trigger for compose file changes | Each `ci-*.yml` includes `domains/{group}/compose.yml` in paths | Done |
| 3.7 | Deprecate monolithic workflow | `test.yml` refactored: python-tests matrix removed, E2E + integration jobs retained | Done (2026-02-25) |

**Reusable workflow pattern:**
```yaml
# .github/workflows/reusable-group-ci.yml
name: Group CI (Reusable)
on:
  workflow_call:
    inputs:
      group_name:
        required: true
        type: string
      services:
        required: true
        type: string  # JSON array of service directory names

permissions:
  contents: read

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    concurrency:
      group: ci-${{ inputs.group_name }}-${{ github.ref }}
      cancel-in-progress: true
    strategy:
      matrix:
        service: ${{ fromJson(inputs.services) }}
      fail-fast: false  # Don't hide failures on other services
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with: { python-version: "3.12" }
      - run: pip install ruff
      - run: ruff check domains/*/${{ matrix.service }}/
      - run: |
          cd domains/*/${{ matrix.service }}
          pip install -r requirements.txt 2>/dev/null || true
          pytest tests/ -v 2>/dev/null || echo "No tests found"
```

**Path trigger example (collectors):**
```yaml
# .github/workflows/ci-collectors.yml
name: CI — data-collectors
on:
  push:
    paths:
      - 'domains/data-collectors/weather-api/**'
      - 'domains/data-collectors/smart-meter-service/**'
      - 'domains/data-collectors/sports-api/**'
      - 'domains/data-collectors/air-quality-service/**'
      - 'domains/data-collectors/carbon-intensity-service/**'
      - 'domains/data-collectors/electricity-pricing-service/**'
      - 'domains/data-collectors/calendar-service/**'
      - 'domains/data-collectors/log-aggregator/**'
      - 'domains/data-collectors/compose.yml'
      - 'domains/data-collectors/.env'
  pull_request:
    paths: [same as above]

concurrency:
  group: ci-collectors-${{ github.ref }}
  cancel-in-progress: true

jobs:
  ci:
    uses: ./.github/workflows/reusable-group-ci.yml
    with:
      group_name: collectors
      services: '["weather-api","smart-meter-service","sports-api","air-quality-service","carbon-intensity-service","electricity-pricing-service","calendar-service","log-aggregator"]'
```

**Shared library cascade rebuild:**
```yaml
# .github/workflows/publish-shared-patterns.yml
name: Publish homeiq-patterns
on:
  push:
    paths: ['libs/homeiq-patterns/**']
    branches: [main]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - run: pip install build && python -m build libs/homeiq-patterns/
      # Publish step here (GitHub Packages or git tag)

  cascade:
    needs: publish
    strategy:
      matrix:
        workflow: [ci-core, ci-collectors, ci-ml, ci-automation, ci-devices, ci-frontends]
    steps:
      - uses: benc-uk/workflow-dispatch@v1
        with:
          workflow: ${{ matrix.workflow }}.yml
          ref: main
```

**Anti-patterns to avoid (from GitHub Actions best practices):**
- Do NOT use `fail-fast: true` in test matrices — it hides failures on other services
- Do NOT use overly permissive `GITHUB_TOKEN` — set `permissions: contents: read` at workflow level
- Do NOT skip concurrency groups — wastes runner minutes on superseded commits
- Always include `libs/homeiq-patterns/**` in path triggers for groups that use the shared library

**Deliverable:** 6 independent CI pipelines + 1 reusable template + 1 integration pipeline + 1 cascade workflow. Build times drop proportionally to group isolation.

---

### Phase 4: Inter-Group Resilience (Medium Risk) -- COMPLETE (7/7)

**Goal:** Services gracefully handle missing groups. If ml-engine is down, automation-intelligence degrades instead of crashing.

**Status:** All 7 steps complete (4.1-4.4 February 2026, 4.5-4.7 done 2026-02-27).

> **Best Practice Note:** For Docker Compose deployments (not Kubernetes), use application-level resilience — not a service mesh. Circuit breakers, exponential backoff retries, and structured health checks are the standard. See [Microservices Patterns](https://microservices.io/patterns/).

| Step | Task | Details | Status |
|------|------|---------|--------|
| 4.1 | Create `libs/homeiq-resilience/` utility module | CircuitBreaker, CrossGroupClient, GroupHealthCheck, wait_for_dependency | **Done** |
| 4.2 | Add circuit breakers at every cross-group boundary | Rolled out to ha-ai-agent, blueprint-suggestion, ai-pattern, ai-automation, proactive-agent, device-health-monitor | **Done** |
| 4.3 | Implement structured health check responses | `/health` returns group-aware status with dependency health via GroupHealthCheck | **Done** |
| 4.4 | Add startup retry loops | `wait_for_dependency()` non-fatal probes in all cross-group callers | **Done** |
| 4.5 | Add fallback behavior for AI services | CircuitBreaker wrappers in device_suggestion_service, capability_analyzer, ai_prompt_generation_service, device_validation_service; cache-first fallbacks; new breakers.py for proactive-agent | Done (2026-02-27) |
| 4.6 | Update health-dashboard to show group-level status | GET /health/groups endpoint with per-group aggregation; GroupsTab redesign with color-coded badges, expandable service lists, progress bars; 15 new service definitions in ServicesTab | Done (2026-02-27) |
| 4.7 | Add service-to-service authentication at group boundaries | ServiceAuthValidator + require_service_auth FastAPI dependency in homeiq-resilience auth.py; ha_agent_client and device_intelligence_client migrated to CrossGroupClient with auth | Done (2026-02-27) |

**Circuit breaker pattern (using `tenacity`):**
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

class CrossGroupClient:
    """Base client for cross-group HTTP calls with circuit breaker."""

    def __init__(self, base_url: str, group_name: str):
        self.base_url = base_url
        self.group_name = group_name
        self._circuit_open = False
        self._failure_count = 0
        self._failure_threshold = 5
        self._recovery_timeout = 60  # seconds

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
    )
    async def call(self, method: str, path: str, **kwargs):
        if self._circuit_open:
            raise CircuitOpenError(f"Circuit open for group {self.group_name}")
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
                response = await client.request(method, path, **kwargs)
                self._failure_count = 0
                return response
        except Exception:
            self._failure_count += 1
            if self._failure_count >= self._failure_threshold:
                self._circuit_open = True
            raise
```

**Structured health check response:**
```json
{
  "status": "degraded",
  "group": "automation-intelligence",
  "version": "1.2.3",
  "uptime_seconds": 3600,
  "dependencies": {
    "data-api": { "status": "healthy", "latency_ms": 12 },
    "ai-core-service": { "status": "unreachable", "last_seen": "2026-02-22T10:00:00Z" }
  },
  "degraded_features": ["ml-powered suggestions (using rule-based fallback)"]
}
```

**Fallback strategy per group boundary:**

| Caller Group | Upstream Group | Fallback When Upstream Down |
|-------------|----------------|----------------------------|
| automation-intelligence | ml-engine | Rule-based recommendations, cached embeddings |
| automation-intelligence | core-platform | **Fatal** — no fallback, service cannot function |
| device-management | ml-engine | Skip ML classification, return raw device data |
| frontends | automation-intelligence | Show "AI features temporarily unavailable" banner |
| data-collectors | core-platform | **Fatal** — buffer to disk, retry when InfluxDB returns |

**Startup resilience pattern:**
```python
async def wait_for_dependency(url: str, name: str, max_retries: int = 30):
    """Wait for upstream dependency with exponential backoff."""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{url}/health", timeout=5.0)
                if resp.status_code == 200:
                    logger.info(f"Dependency {name} is healthy")
                    return
        except Exception:
            pass
        wait = min(2 ** attempt, 30)
        logger.warning(f"Waiting for {name} (attempt {attempt+1}/{max_retries}, next in {wait}s)")
        await asyncio.sleep(wait)
    logger.error(f"Dependency {name} not available after {max_retries} attempts — starting in degraded mode")
```

**Deliverable:** Any group can start independently. Missing upstream groups cause graceful degradation, not crashes. Health endpoints report dependency status.

---

### Phase 5: Documentation & Runbook Updates (Low Risk) -- COMPLETE

**Goal:** All documentation reflects the new group structure.

| Step | Task | Files |
|------|------|-------|
| 5.1 | Update `docs/architecture/SERVICES_RANKED_BY_IMPORTANCE.md` | Add group assignments |
| 5.2 | Update `docs/architecture/README_ARCHITECTURE_QUICK_REF.md` | Add group architecture diagram |
| 5.3 | Update `docs/deployment/DEPLOYMENT_RUNBOOK.md` | Per-group deploy procedures |
| 5.4 | Update `docs/architecture/event-flow-architecture.md` | Add group boundaries to flow diagrams |
| 5.5 | Create `docs/architecture/service-groups.md` | Canonical reference for group definitions |
| 5.6 | Update `README.md` | Reference new group structure |
| 5.7 | Create per-group `README.md` in compose directory | Quick-start guide per group |

---

### Phase 6 (Future): Repository Split (High Risk — Optional)

**Goal:** Move each group into its own Git repository for full isolation.

This phase is **not recommended now**. The compose file split (Phase 1) provides 80% of the benefit at 20% of the cost. Repository splitting introduces:
- Cross-repo dependency management complexity
- Shared library versioning overhead
- Integration testing challenges
- Developer workflow disruption

**Trigger for Phase 6:** When the team grows beyond ~8 developers and group-level CI pipelines are consistently independent for 3+ months.

---

## Risk Assessment

| Phase | Risk | Likelihood | Impact | Mitigation |
|-------|------|-----------|--------|------------|
| Phase 1 | Compose syntax errors | Low | Low | `docker compose config` validation before merge; zero-diff check against original |
| Phase 1 | Missing service in split | Low | High | Automated count assertion: `sum(group services) == 52`; CI script to verify |
| Phase 1 | Cross-group `depends_on` breaks | Medium | Medium | Remove all cross-group `depends_on` upfront; replace with app-level retries |
| Phase 1 | Network isolation breaks service discovery | Medium | High | All groups share `homeiq-network` (external); test inter-group HTTP calls |
| Phase 2 | Import breakage from `sys.path` removal | Medium | High | Migrate one service at a time; run per-service tests after each migration |
| Phase 2 | Docker build failures from shared lib path changes | Medium | Medium | Build every Dockerfile in CI before merge; keep `COPY` fallback during transition |
| Phase 2 | Version pinning conflicts | Low | Medium | Use compatible version ranges (`>=1.0,<2.0`); single source of truth for shared deps |
| Phase 3 | Missed path trigger (silent build skip) | Medium | Medium | Integration test on `main` catches regressions; weekly full-rebuild cron job |
| Phase 3 | Cascade rebuild storm from shared lib change | Low | Low | Rate-limit `workflow_dispatch` calls; use concurrency groups to deduplicate |
| Phase 4 | Circuit breaker misconfiguration (too aggressive) | Medium | Medium | Start with conservative thresholds (5 failures / 60s recovery); tune with metrics |
| Phase 4 | Fallback behavior diverges from real behavior | Low | Medium | Integration tests that verify fallback paths; health-dashboard shows degradation mode |

---

## Cross-Cutting Concerns

### Security at Group Boundaries

Per microservices best practices, group boundaries are trust boundaries:

- **Service-to-service auth:** All cross-group HTTP calls use Bearer token authentication via `CrossGroupClient(auth_token=...)`. Token sourced from `DATA_API_API_KEY` / `API_KEY` environment variables. **Implemented** for all 6 cross-group callers.
- **Network policy:** While all groups share `homeiq-network` for simplicity, consider per-group networks in Phase 6 for defense-in-depth
- **Secrets management:** Per-group `.env` files must NOT be committed to Git. Add `domains/*/.env` to `.gitignore`. Use Docker secrets or a `.env.example` pattern.
- **API versioning:** Cross-group APIs should be versioned (`/api/v1/`) so groups can evolve independently without breaking consumers

### Observability Across Groups

- **Distributed tracing:** `CrossGroupClient` automatically injects `traceparent`/`tracestate` headers when OpenTelemetry is installed (optional import, no hard dependency). Each cross-group call sets span attribute `homeiq.target_group` for group-level trace filtering. **Implemented** in `libs/homeiq-resilience/cross_group_client.py`.
- **Structured logging:** `setup_logging(service_name, group_name="...")` embeds the group name in every JSON log line. **Implemented** in `libs/homeiq-resilience/logging_config.py` and all 6 cross-group callers.
- **Group-level metrics:** health-dashboard should aggregate health by group, not just by individual service. `/health` endpoints now return structured `GroupHealthCheck` responses with `group`, `dependencies`, `status`, and `uptime_seconds` fields.
- **Alerting:** Group-level alerting rules documented in `libs/homeiq-resilience/README.md`. Severity matrix: core-platform (P1/page), ml-engine/automation-intelligence (P2/alert), data-collectors/device-management/frontends (P3/notify).

---

## Success Criteria

- [ ] 6 group compose files created, validated, documented
- [ ] `docker compose -f ... config` output matches original `docker-compose.yml` (zero-diff)
- [ ] Each group can start independently with `docker compose -f base -f group up`
- [ ] `libs/homeiq-patterns/` is a pip-installable package
- [ ] 6 CI pipelines with correct path triggers
- [ ] All 152 pattern tests pass after shared lib packaging
- [ ] Health dashboard shows group-level status
- [ ] Deployment runbook updated for per-group operations
- [ ] No service has a hard crash when an upstream group is missing

---

## Recommended Execution Order

```
Phase 0  ──────►  Phase 1  ──────►  Phase 5
(1-2 days)       (3-5 days)        (1-2 days)
   Prep            Compose split     Docs
                       │
                       ▼
                  Phase 2  ──────►  Phase 3
                 (5-7 days)        (3-5 days)
                  Shared lib        CI split
                       │
                       ▼
                  Phase 4
                 (5-7 days)
                  Resilience
```

**Quick win:** Phases 0 + 1 + 5 can be completed first as a standalone milestone, delivering immediate value (selective group deployment) without touching any Python code.

**Total estimated scope:** Phases 0-5 represent ~20-30 days of engineering effort across the full rollout.

---

## Deviations from Original Plan

> **Added 2026-02-24 (Story 7, Epic 5):** Documents where the implementation diverged from this plan.

| # | Deviation | Explanation |
|---|-----------|-------------|
| 1 | **9 domains instead of 6 groups** | `automation-intelligence` (16 services) was split into automation-core (7), blueprints (4), energy-analytics (3), pattern-analysis (2) for better ownership boundaries. |
| 2 | **`ha-simulator` added to core-platform** | Not in the original plan. Added during restructuring as a development/testing tool that belongs with core infrastructure. |
| 3 | **`automation-trace-service` added to automation-core** | New service (port 8044) created during the Deploy Pipeline Root Cause Fixes epic for HA automation trace + logbook ingestion. |
| 4 | **`activity-writer` and `activity-recognition` added to device-management** | New services from the Activity Recognition Integration epic (ports 8045 and 8043 respectively). |
| 5 | **No `compose/` directory** | The plan originally implied a `docker/` directory (Phase 0, Step 0.1). Compose files instead live directly at `domains/{group}/compose.yml`. |
| 6 | **`frontends` group has 4 services, not 3** | Jaeger (port 16686) was included in the frontends domain. The original plan listed 3 services + infra but the actual compose includes Jaeger as a full service. |
| 7 | **5 shared libraries instead of 1** | Phase 2 planned packaging `homeiq-patterns` only. The implementation created 5 packages: homeiq-patterns, homeiq-resilience, homeiq-observability, homeiq-data, homeiq-ha. |

---

## Lessons Learned

> **Added 2026-02-24 (Story 7, Epic 5):** Post-implementation retrospective.

### What Worked Well

1. **Direct migration without symlinks.** For a pre-production project with no live traffic, moving files directly (rather than using symlinks or gradual redirects) was the fastest path. Symlinks would have added complexity with Docker build contexts for no benefit.

2. **9 domains provided better ownership boundaries than 6.** The original `automation-intelligence` group with 16 services was too broad. Splitting it into 4 sub-domains (automation-core, blueprints, energy-analytics, pattern-analysis) made each domain's purpose immediately clear and reduced the blast radius of changes.

3. **Shared library packaging as pip packages.** Installing `libs/homeiq-*` as proper pip packages (with `pyproject.toml` and src-layout) eliminated `sys.path` manipulation across 50+ services. The import pattern `from homeiq_patterns import X` is clean and works identically in development (`pip install -e`) and Docker builds.

### What Caused Problems

4. **`sys.path` hacks in tests were the biggest source of post-migration regressions.** Many test files had their own `sys.path.insert()` calls pointing to old paths. These broke silently (tests passed locally due to editable installs but failed in Docker). Every test file needed auditing.

5. **Missing `from pathlib import Path` imports were hidden by runtime import chains.** Some modules relied on `Path` being imported transitively through other modules' `sys.path` setup code. When that setup code was removed, `NameError: name 'Path' is not defined` errors appeared in modules that never explicitly imported it. This was only caught during testing.

6. **Docker build context assumptions.** Several Dockerfiles assumed they were built from the service directory. The migration to `docker-bake.hcl` with `context = "."` (project root) required updating all `COPY` paths. Services with relative `COPY ../../../shared/` paths were the most fragile.

### Recommendations for Similar Migrations

7. **Run the full test suite after every service migration, not just at the end.** Batch migration (moving all services, then testing) made it harder to isolate which move broke which test.

8. **Install shared libraries as pip packages (`pip install -e libs/X`) before removing any `sys.path` hacks.** This ensures the new import paths are available before the old ones are removed, allowing incremental migration.

---

## References

- [Docker Compose Include Directive](https://docs.docker.com/compose/how-tos/multiple-compose-files/include/) — official docs for the `include` approach used in Phase 1
- [Docker Compose Multiple Files](https://docs.docker.com/compose/how-tos/multiple-compose-files/) — merge vs include comparison
- [Docker Compose Best Practices 2026](https://hackmamba.io/engineering/best-practices-when-using-docker-compose/) — per-group `.env`, health checks, network isolation
- [Python Packaging Guide — pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — shared library packaging (Phase 2)
- [Python Monorepo with UV Workspaces](https://tomasrepcik.dev/blog/2025/2025-10-26-python-workspaces/) — workspace configuration for monorepos
- [GitHub Actions for Monorepos](https://oneuptime.com/blog/post/2026-02-02-github-actions-monorepos/view) — path-scoped workflows, cascade rebuilds
- [Monorepo Path Filters in GitHub Actions](https://oneuptime.com/blog/post/2025-12-20-monorepo-path-filters-github-actions/view) — path trigger patterns
- [Cross-Repository Workflows](https://oneuptime.com/blog/post/2025-12-20-cross-repository-workflows-github-actions/view) — `workflow_dispatch` cascade pattern
- [Microservices Patterns](https://microservices.io/patterns/) — circuit breaker, graceful degradation, service boundaries
- [Creating Separate Monorepo CI/CD Pipelines](https://blog.logrocket.com/creating-separate-monorepo-ci-cd-pipelines-github-actions/) — reusable workflows approach
