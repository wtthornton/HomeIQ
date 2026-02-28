---
epic: docker-modernization
priority: high
status: complete
estimated_duration: 5-7 days
risk_level: medium
source: Domain Architecture Restructuring Initiative (Epic 3 of 3)
---

# Epic: Docker Compose Modernization & Parallel Builds

**Status:** Complete
**Priority:** High
**Duration:** 5-7 days
**Risk Level:** Medium
**PRD Reference:** `docs/planning/service-decomposition-plan.md`
**Initiative:** Domain Architecture Restructuring (Epic 3 of 3)

## Overview

Rewrite all Docker Compose files to match the new 9-domain folder structure introduced by Epic 1 (Folder Restructuring) and add `docker-bake.hcl` for parallel builds. The current `compose/` directory has 6 group files (core.yml, collectors.yml, ml.yml, automation.yml, devices.yml, frontends.yml) plus per-group `.env.example` files. This epic co-locates compose files within each domain directory, splits the automation-intelligence group into 4 domain-specific compose files (automation-core, blueprints, energy-analytics, pattern-analysis), and introduces Docker Buildx Bake for parallel image builds.

**Current structure (6 groups):**
```
compose/
  core.yml, collectors.yml, ml.yml, automation.yml, devices.yml, frontends.yml
  core.env.example, collectors.env.example, ml.env.example, ...
docker-compose.yml  (root, uses include: directive)
```

**Target structure (9 domains):**
```
domains/
  core-platform/compose.yml       + compose.env.example   (6 services)
  data-collectors/compose.yml     + compose.env.example   (8 services)
  ml-engine/compose.yml           + compose.env.example   (10 services)
  automation-core/compose.yml     + compose.env.example   (7 services)
  blueprints/compose.yml          + compose.env.example   (4 services)
  energy-analytics/compose.yml    + compose.env.example   (3 services)
  device-management/compose.yml   + compose.env.example   (8 services)
  pattern-analysis/compose.yml    + compose.env.example   (2 services)
  frontends/compose.yml           + compose.env.example   (4 services, incl Jaeger)
docker-compose.yml   (root, include: all 9)
docker-bake.hcl      (parallel builds)
```

## Objectives

1. Co-locate compose files with their domain services under `domains/{group}/compose.yml`
2. Enable parallel Docker builds via `docker-bake.hcl` (one target per service, one group per domain)
3. Split automation-intelligence into 4 domain-specific compose files (automation-core, blueprints, energy-analytics, pattern-analysis)
4. Maintain zero-diff service definitions (same ports, volumes, networks, environment variables)

## Success Criteria

- [ ] `docker compose config` output matches original service definitions (zero-diff on ports, volumes, networks)
- [ ] `docker buildx bake {group}` builds all services in a given domain in parallel
- [ ] Each domain can start independently with `docker compose -f domains/{group}/compose.yml up`
- [ ] All services reachable on their expected ports after full stack startup
- [ ] Root `docker-compose.yml` with `include:` directive merges all 9 domain files correctly
- [ ] Old `compose/` directory removed with no dangling references

## Key Docker Patterns

All compose files must include:
- **Health checks** for every service (HTTP endpoint, TCP socket, or command)
- **Resource limits** (`mem_limit`, `cpus`) appropriate to the service tier
- **Restart policies** (`restart: unless-stopped` for production services)
- **Build context** set to repo root with `dockerfile:` pointing to `domains/{group}/{service}/Dockerfile`
- **Per-group `.env` file** references via `env_file:`
- **Network:** `homeiq-network` (core-platform defines it; all others use `external: true`)

---

## User Stories

### Story 1: Create `docker-bake.hcl` for Parallel Builds

**As a** DevOps engineer
**I want** a `docker-bake.hcl` file at the repo root with a target per service and a group per domain
**So that** I can build all images in a domain in parallel with `docker buildx bake {group}` and the full stack with `docker buildx bake full`

**Acceptance Criteria:**
- [ ] `docker-bake.hcl` created at repo root
- [ ] One `target` block per service, referencing `domains/{group}/{service}/Dockerfile` with repo root as context
- [ ] 9 `group` blocks, one per domain (core-platform, data-collectors, ml-engine, automation-core, blueprints, energy-analytics, device-management, pattern-analysis, frontends)
- [ ] 1 `full` group that includes all 9 domain groups
- [ ] Each target includes appropriate labels (`org.opencontainers.image.*`)
- [ ] `docker buildx bake core-platform` builds all 6 core services in parallel
- [ ] `docker buildx bake full` builds all services across all domains
- [ ] Variable blocks for common build args (e.g., `PYTHON_VERSION`, `NODE_VERSION`)

**Story Points:** 5
**Dependencies:** Epic 1 Story 1 (folder restructuring complete)
**Affected Services:** All services (build configuration only)

---

### Story 2: Rewrite core-platform compose.yml

**As a** platform operator
**I want** `domains/core-platform/compose.yml` to define all 6 core services with the `homeiq-network` network
**So that** the core platform can start independently and other domains can attach to its network

**Acceptance Criteria:**
- [ ] `domains/core-platform/compose.yml` defines 6 services: influxdb, data-api, websocket-ingestion, admin-api, health-dashboard, data-retention
- [ ] Defines `homeiq-network` as a bridge network (other domains reference it as `external: true`)
- [ ] Defines shared volumes (e.g., influxdb-data, postgres-data)
- [ ] All 6 services have health checks (HTTP `/health` or TCP socket)
- [ ] Resource limits set for each service (influxdb gets higher memory allocation)
- [ ] Build contexts reference `domains/core-platform/{service}/Dockerfile`
- [ ] Port mappings match existing: influxdb (8086), data-api (8006), websocket-ingestion (8001), admin-api (8003), health-dashboard (3000), data-retention (8007)
- [ ] `env_file: compose.env.example` references co-located environment file
- [ ] `docker compose -f domains/core-platform/compose.yml config` produces valid output

**Story Points:** 5
**Dependencies:** Epic 1 Story 2 (core-platform services moved to domain folder)
**Affected Services:** influxdb, data-api (8006), websocket-ingestion (8001), admin-api (8003), health-dashboard (3000), data-retention (8007)

---

### Story 3: Rewrite data-collectors compose.yml

**As a** platform operator
**I want** `domains/data-collectors/compose.yml` to define all 8 stateless collector services
**So that** data collectors can be scaled and restarted independently of other domains

**Acceptance Criteria:**
- [ ] `domains/data-collectors/compose.yml` defines 8 collector services
- [ ] Uses `homeiq-network` as `external: true`
- [ ] All services are stateless (no persistent volumes)
- [ ] Health checks for all 8 services
- [ ] Resource limits appropriate for lightweight collector processes
- [ ] Restart policy: `unless-stopped`
- [ ] Port mappings match existing compose/collectors.yml
- [ ] `docker compose -f domains/data-collectors/compose.yml config` produces valid output

**Story Points:** 3
**Dependencies:** Epic 1 Story 3 (data-collectors services moved to domain folder)
**Affected Services:** 8 data collector services

---

### Story 4: Rewrite ml-engine compose.yml

**As a** ML engineer
**I want** `domains/ml-engine/compose.yml` to define all 10 ML services with proper dependency chains and resource profiles
**So that** ML services start in the correct order and have sufficient memory/CPU for model inference

**Acceptance Criteria:**
- [ ] `domains/ml-engine/compose.yml` defines 10 ML services
- [ ] Internal `depends_on` chain: openvino -> ml-service -> ner-service -> ai-core-service (with `condition: service_healthy`)
- [ ] GPU/high-memory resource profiles: `mem_limit` of 2G+ for model-serving services
- [ ] Uses `homeiq-network` as `external: true`
- [ ] Health checks for all 10 services (model readiness endpoints where applicable)
- [ ] Build contexts reference `domains/ml-engine/{service}/Dockerfile`
- [ ] Port mappings match existing compose/ml.yml
- [ ] OpenVINO service has appropriate device mappings if GPU is available
- [ ] `docker compose -f domains/ml-engine/compose.yml config` produces valid output

**Story Points:** 5
**Dependencies:** Epic 1 Story 4 (ml-engine services moved to domain folder)
**Affected Services:** 10 ML services (openvino-service, ml-service, ner-service, ai-core-service, and 6 others)

---

### Story 5: Create automation-core compose.yml (NEW)

**As a** automation developer
**I want** `domains/automation-core/compose.yml` to define the 7 core automation services split from the old automation.yml
**So that** automation services are isolated from blueprints, energy, and pattern services

**Acceptance Criteria:**
- [ ] `domains/automation-core/compose.yml` defines 7 automation services
- [ ] Services migrated from the relevant portion of `compose/automation.yml`
- [ ] Uses `homeiq-network` as `external: true`
- [ ] Health checks for all 7 services
- [ ] Resource limits appropriate for automation workloads
- [ ] Port mappings preserved from original automation.yml for migrated services
- [ ] `depends_on` relationships maintained where services have inter-dependencies
- [ ] `docker compose -f domains/automation-core/compose.yml config` produces valid output

**Story Points:** 3
**Dependencies:** Epic 1 Story 5 (automation-core services moved to domain folder)
**Affected Services:** 7 automation-core services

---

### Story 6: Create blueprints compose.yml (NEW)

**As a** automation developer
**I want** `domains/blueprints/compose.yml` to define the 4 blueprint-related services
**So that** blueprint generation and management services can be deployed and scaled independently

**Acceptance Criteria:**
- [ ] `domains/blueprints/compose.yml` defines 4 blueprint services
- [ ] Services extracted from the relevant portion of `compose/automation.yml`
- [ ] Uses `homeiq-network` as `external: true`
- [ ] Health checks for all 4 services
- [ ] Resource limits appropriate for blueprint workloads
- [ ] Port mappings preserved from original definitions
- [ ] `docker compose -f domains/blueprints/compose.yml config` produces valid output

**Story Points:** 2
**Dependencies:** Epic 1 Story 6 (blueprints services moved to domain folder)
**Affected Services:** 4 blueprint services

---

### Story 7: Create energy-analytics compose.yml (NEW)

**As a** energy analyst
**I want** `domains/energy-analytics/compose.yml` to define the 3 energy analytics services
**So that** energy monitoring and forecasting services can be deployed independently

**Acceptance Criteria:**
- [ ] `domains/energy-analytics/compose.yml` defines 3 energy services
- [ ] Services extracted from the relevant portion of `compose/automation.yml`
- [ ] Uses `homeiq-network` as `external: true`
- [ ] Health checks for all 3 services
- [ ] Resource limits appropriate for analytics workloads (forecasting may need more memory)
- [ ] Port mappings preserved from original definitions
- [ ] `docker compose -f domains/energy-analytics/compose.yml config` produces valid output

**Story Points:** 2
**Dependencies:** Epic 1 Story 7 (energy-analytics services moved to domain folder)
**Affected Services:** 3 energy analytics services

---

### Story 8: Create device-management compose.yml

**As a** device integrator
**I want** `domains/device-management/compose.yml` to define all 8 device management services
**So that** device discovery, intelligence, and management services are grouped and deployable together

**Acceptance Criteria:**
- [ ] `domains/device-management/compose.yml` defines 8 device services
- [ ] Services migrated from `compose/devices.yml`
- [ ] Uses `homeiq-network` as `external: true`
- [ ] Health checks for all 8 services
- [ ] Resource limits appropriate for device management workloads
- [ ] Port mappings match existing compose/devices.yml
- [ ] `docker compose -f domains/device-management/compose.yml config` produces valid output

**Story Points:** 3
**Dependencies:** Epic 1 Story 8 (device-management services moved to domain folder)
**Affected Services:** 8 device management services

---

### Story 9: Create pattern-analysis compose.yml (NEW)

**As a** pattern analyst
**I want** `domains/pattern-analysis/compose.yml` to define the 2 pattern analysis services
**So that** pattern detection and analysis services can be deployed independently

**Acceptance Criteria:**
- [ ] `domains/pattern-analysis/compose.yml` defines 2 pattern services
- [ ] Services extracted from the relevant portion of `compose/automation.yml`
- [ ] Uses `homeiq-network` as `external: true`
- [ ] Health checks for both services
- [ ] Resource limits appropriate for pattern analysis workloads
- [ ] Port mappings preserved from original definitions
- [ ] `docker compose -f domains/pattern-analysis/compose.yml config` produces valid output

**Story Points:** 1
**Dependencies:** Epic 1 Story 9 (pattern-analysis services moved to domain folder)
**Affected Services:** 2 pattern analysis services

---

### Story 10: Create frontends compose.yml

**As a** frontend developer
**I want** `domains/frontends/compose.yml` to define all 4 frontend services including Jaeger
**So that** UI services and observability tooling are grouped and deployable together

**Acceptance Criteria:**
- [ ] `domains/frontends/compose.yml` defines 4 services (including Jaeger for tracing)
- [ ] Services migrated from `compose/frontends.yml`
- [ ] Uses `homeiq-network` as `external: true`
- [ ] Health checks for all 4 services
- [ ] Jaeger service has appropriate port mappings (16686 UI, 6831 UDP, 14268 HTTP)
- [ ] Resource limits appropriate for frontend and tracing workloads
- [ ] Port mappings match existing compose/frontends.yml
- [ ] `docker compose -f domains/frontends/compose.yml config` produces valid output

**Story Points:** 2
**Dependencies:** Epic 1 Story 10 (frontends services moved to domain folder)
**Affected Services:** 4 frontend services (including Jaeger)

---

### Story 11: Rewrite Root `docker-compose.yml` with `include:` Directive

**As a** platform operator
**I want** the root `docker-compose.yml` to use the `include:` directive referencing all 9 domain compose files
**So that** `docker compose up` from the repo root starts the entire stack, and `docker compose up {service}` targets individual services

**Acceptance Criteria:**
- [ ] Root `docker-compose.yml` uses `include:` (Docker Compose v2.20+ feature) to reference all 9 domain files
- [ ] Include order: core-platform first (defines network), then remaining 8 domains
- [ ] `docker compose config` from repo root outputs valid merged configuration
- [ ] `docker compose up` starts all services across all domains
- [ ] `docker compose up data-api` targets a specific service within the merged config
- [ ] `docker compose ps` shows services from all domains
- [ ] No duplicate network or volume definitions in merged output
- [ ] Comment header documenting the include order and why core-platform is first

**Story Points:** 3
**Dependencies:** Stories 2-10 (all domain compose files exist)
**Affected Services:** All services (orchestration configuration)

---

### Story 12: Create Per-Domain `.env.example` Files

**As a** developer setting up the project
**I want** each domain to have a `compose.env.example` file with group-specific environment variables
**So that** I can configure each domain independently and understand what variables each group requires

**Acceptance Criteria:**
- [ ] 9 `compose.env.example` files created, one per domain directory
- [ ] Variables migrated from existing `compose/*.env.example` files to corresponding domain files
- [ ] Variables split from old `automation.env.example` into 4 domain-specific files (automation-core, blueprints, energy-analytics, pattern-analysis)
- [ ] Each file includes comments documenting variable purpose, default values, and whether required or optional
- [ ] Shared variables (e.g., `INFLUXDB_URL`, `DATA_API_URL`) are duplicated across domains that need them (not referenced cross-domain)
- [ ] Sensitive variables use placeholder values (e.g., `API_KEY=changeme`)
- [ ] No secrets or real credentials in `.env.example` files

**Story Points:** 3
**Dependencies:** Stories 2-10 (compose files define which variables are needed)
**Affected Services:** All services (environment configuration)

---

### Story 13: Delete Old `compose/` Directory

**As a** developer
**I want** the old `compose/` directory removed after migration is verified
**So that** there is a single source of truth for compose configuration (the domain directories)

**Acceptance Criteria:**
- [ ] All service definitions from `compose/*.yml` accounted for in `domains/*/compose.yml`
- [ ] All environment variables from `compose/*.env.example` accounted for in `domains/*/compose.env.example`
- [ ] `compose/` directory deleted (core.yml, collectors.yml, ml.yml, automation.yml, devices.yml, frontends.yml, test.yml, all .env.example files, README.md)
- [ ] No references to `compose/` directory remain in documentation or scripts
- [ ] `compose/test.yml` contents migrated or documented as replaced by new test strategy
- [ ] Git history preserves the old files (standard git rm)

**Story Points:** 1
**Dependencies:** Story 11 (root docker-compose.yml rewritten and validated)
**Affected Services:** None (cleanup only)

---

### Story 14: Validate Full Stack with `docker compose config`

**As a** platform operator
**I want** to validate that the merged Docker Compose configuration matches the original service definitions
**So that** the migration is confirmed as zero-diff and no services were lost or misconfigured

**Acceptance Criteria:**
- [ ] Run `docker compose config` on the new root `docker-compose.yml` and capture output
- [ ] Compare service count: verify all 52 services (6+8+10+7+4+3+8+2+4) are present
- [ ] Compare port mappings: every service has identical host:container port bindings as before
- [ ] Compare network configuration: all services on `homeiq-network`
- [ ] Compare volume mounts: persistent volumes match original definitions
- [ ] Compare environment variables: no variables lost or renamed
- [ ] `docker buildx bake full --print` outputs valid build configuration for all targets
- [ ] Validation script or checklist documented for CI integration

**Story Points:** 3
**Dependencies:** Story 11 (root docker-compose.yml with include directive)
**Affected Services:** All services (validation only)

---

## Dependencies

```
Epic 1 (Folder Restructuring)
    │
    ▼
Story 1 (docker-bake.hcl) ─────────────────────────────────────────┐
    │                                                               │
    │   Stories 2-10 (domain compose files) ← PARALLELIZABLE        │
    │   ┌────────────────────────────────────────────────────────┐   │
    │   │  Story 2  (core-platform)     ← defines network       │   │
    │   │  Story 3  (data-collectors)                            │   │
    │   │  Story 4  (ml-engine)                                  │   │
    │   │  Story 5  (automation-core)    ← NEW split             │   │
    │   │  Story 6  (blueprints)         ← NEW split             │   │
    │   │  Story 7  (energy-analytics)   ← NEW split             │   │
    │   │  Story 8  (device-management)                          │   │
    │   │  Story 9  (pattern-analysis)   ← NEW split             │   │
    │   │  Story 10 (frontends)                                  │   │
    │   └────────────────────────────────────────────────────────┘   │
    │       │                                                       │
    │       ▼                                                       │
    │   Story 11 (root docker-compose.yml) ← depends on 2-10       │
    │       │                                                       │
    │       ├── Story 12 (per-domain .env.example) ← depends on 2-10│
    │       │                                                       │
    │       ▼                                                       │
    │   Story 13 (delete compose/) ← depends on 11                  │
    │       │                                                       │
    │       ▼                                                       │
    └──▶ Story 14 (validation) ← depends on 11, 1                  │
                                                                    │
```

## Suggested Execution Order

| Phase | Stories | Parallelizable | Rationale |
|-------|---------|----------------|-----------|
| **Phase 1** | Story 1 | Yes (independent) | docker-bake.hcl can be written as soon as Epic 1 folder structure is known |
| **Phase 2** | Stories 2-10 | Yes (all 9 in parallel) | Each compose file is independent; Story 2 should be done first or concurrently since it defines the network |
| **Phase 3** | Stories 11, 12 | Yes (parallel with each other) | Root compose and env files depend on Phase 2 but are independent of each other |
| **Phase 4** | Story 13 | No | Cleanup; must wait for Phase 3 validation |
| **Phase 5** | Story 14 | No | Final validation gate; must be last |

**Critical path:** Epic 1 -> Story 2 (core-platform) -> Story 11 (root compose) -> Story 14 (validation)

## Agent Team Strategy

**Recommended team size:** 3-4 agents

| Agent | Role | Assigned Stories | Notes |
|-------|------|-----------------|-------|
| **Agent A** (Lead) | Core infrastructure | Stories 1, 2, 11, 14 | Handles bake file, core-platform (defines network), root compose, and final validation |
| **Agent B** | Domain compose (batch 1) | Stories 3, 4, 5, 8 | Larger compose files: data-collectors (8), ml-engine (10), automation-core (7), device-management (8) |
| **Agent C** | Domain compose (batch 2) | Stories 6, 7, 9, 10 | Smaller compose files: blueprints (4), energy-analytics (3), pattern-analysis (2), frontends (4) |
| **Agent D** | Environment & cleanup | Stories 12, 13 | Per-domain env files and old directory cleanup |

**Coordination rules:**
- Agent A creates Story 2 (core-platform) first so the `homeiq-network` definition exists for reference
- Agents B and C must read the EXISTING compose files (`compose/*.yml`) and adapt paths/service definitions
- Agent D waits for Agents B and C to finish before creating env files
- Agent A runs Story 14 (validation) only after all other stories are complete
- All agents verify their compose files with `docker compose -f domains/{group}/compose.yml config`

## Implementation Artifacts

| Artifact | Path | Story |
|----------|------|-------|
| **Docker Bake File** | `docker-bake.hcl` | 1 |
| **Core Platform Compose** | `domains/core-platform/compose.yml` | 2 |
| **Data Collectors Compose** | `domains/data-collectors/compose.yml` | 3 |
| **ML Engine Compose** | `domains/ml-engine/compose.yml` | 4 |
| **Automation Core Compose** | `domains/automation-core/compose.yml` | 5 |
| **Blueprints Compose** | `domains/blueprints/compose.yml` | 6 |
| **Energy Analytics Compose** | `domains/energy-analytics/compose.yml` | 7 |
| **Device Management Compose** | `domains/device-management/compose.yml` | 8 |
| **Pattern Analysis Compose** | `domains/pattern-analysis/compose.yml` | 9 |
| **Frontends Compose** | `domains/frontends/compose.yml` | 10 |
| **Root Compose (rewritten)** | `docker-compose.yml` | 11 |
| **Core Platform Env** | `domains/core-platform/compose.env.example` | 12 |
| **Data Collectors Env** | `domains/data-collectors/compose.env.example` | 12 |
| **ML Engine Env** | `domains/ml-engine/compose.env.example` | 12 |
| **Automation Core Env** | `domains/automation-core/compose.env.example` | 12 |
| **Blueprints Env** | `domains/blueprints/compose.env.example` | 12 |
| **Energy Analytics Env** | `domains/energy-analytics/compose.env.example` | 12 |
| **Device Management Env** | `domains/device-management/compose.env.example` | 12 |
| **Pattern Analysis Env** | `domains/pattern-analysis/compose.env.example` | 12 |
| **Frontends Env** | `domains/frontends/compose.env.example` | 12 |
| **Old Compose Dir (deleted)** | `compose/` (removed) | 13 |

**Total Story Points:** 41

## References

- [PRD: Service Decomposition Plan](../docs/planning/service-decomposition-plan.md)
- Epic 1: Folder Restructuring (prerequisite)
- Epic 2: Shared Library Extraction (parallel)
- [Docker Compose `include:` specification](https://docs.docker.com/compose/how-tos/multiple-compose-files/include/)
- [Docker Buildx Bake reference](https://docs.docker.com/build/bake/reference/)
- ~~[Existing compose files](../compose/)~~ (deleted — now in `domains/*/compose.yml`)

---

## Execution Notes

**Completed:** 2026-02-23

### Key Decisions During Execution

1. **Test services (home-assistant-test, websocket-ingestion-test)** — Moved to `core-platform/compose.yml` with `test` profile, since they test core-platform services. The old `compose/test.yml` is fully migrated.

2. **ha-simulator** — Moved to `core-platform/compose.yml` with `development` profile, logging label updated from `group=test` to `group=core-platform`.

3. **proactive-agent-service depends_on** — Originally depended on `ha-ai-agent-service` which is now in a different domain (automation-core). Converted to cross-domain comment since Docker Compose `include:` merges services at the root level and cross-domain depends_on can't be expressed in individual domain compose files. The root compose.yml handles this via the include order.

4. **automation-linter shared volume** — Updated from `../shared/ha_automation_lint` to `../../libs/homeiq-ha/src/homeiq_ha/ha_automation_lint` to reflect Epic 2's library extraction.

5. **ner-service and openai-service** — These build from `domains/archive/2025-q4/ai-automation-service/docker/`. Kept in ml-engine compose.yml with updated paths.

6. **Logging labels** — All services previously in `automation-intelligence` group updated to their new domain group names (automation-core, blueprints, energy-analytics, pattern-analysis).

### Validation Results

- `docker compose config --quiet` — **PASS** (zero errors)
- Default services: 45
- With all profiles (production + development + test): **53 services**
- `docker buildx bake -f docker-bake.hcl --print full` — **PASS** (49 build targets, 10 groups)
- No duplicate port bindings
- All 14 files from `compose/` directory git rm'd
