---
epic: domain-folder-restructuring
priority: high
status: complete
estimated_duration: 3-5 days
risk_level: medium
source: docs/planning/service-decomposition-plan.md
initiative: Domain Architecture Restructuring (Epic 1 of N)
---

# Epic: Domain Folder Restructuring

**Status:** Complete
**Priority:** High
**Duration:** 3-5 days
**Risk Level:** Medium
**PRD Reference:** `docs/planning/service-decomposition-plan.md`
**Initiative:** Domain Architecture Restructuring -- Epic 1: Physical directory restructuring

## Overview

Move all 50+ services from the flat `services/` directory into a `domains/` directory with 9 domain group subdirectories. The existing service decomposition plan defines 6 logical groups; this epic extends to 9 groups by splitting the 16-service `automation-intelligence` group into 4 focused sub-domains: automation-core, blueprints, energy-analytics, and pattern-analysis.

This is a **pre-production** project. No backwards compatibility, symlinks, or migration shims are needed. The approach is straightforward: `git mv` each service into its domain directory and clean up.

**The 9 Domain Groups:**

| # | Domain | Service Count | Description |
|---|--------|---------------|-------------|
| 1 | `core-platform` | 5 (+ influxdb external) | Data backbone -- InfluxDB, data-api, websocket-ingestion, admin-api, health-dashboard, data-retention |
| 2 | `data-collectors` | 8 | Stateless external data fetchers |
| 3 | `ml-engine` | 10 | ML inference, embeddings, training |
| 4 | `automation-core` | 7 | Automation generation, validation, deployment |
| 5 | `blueprints` | 4 | Blueprint indexing, suggestions, recommendations |
| 6 | `energy-analytics` | 3 | Energy correlation, forecasting, proactive recommendations |
| 7 | `device-management` | 8 | Device lifecycle, health, onboarding, activity |
| 8 | `pattern-analysis` | 2 | Pattern detection, edge automation |
| 9 | `frontends` | 3 (+ jaeger external) | User-facing UIs and observability |

## Objectives

1. Mirror the logical service grouping in the physical filesystem
2. Enable domain-scoped CI path triggers (e.g., `domains/ml-engine/**`)
3. Reduce cognitive load -- developers navigate by domain, not alphabetical list of 50+ directories
4. Enable per-domain compose files co-located with their services

## Success Criteria

- [x] All 48 services accounted for across 9 domain directories (ner-service and openai-service do not exist in filesystem — removed from plan)
- [x] `git log --follow` works for all moved files (9,979 renames tracked)
- [ ] No broken Dockerfile COPY paths (fixed in Epic 4)
- [ ] No broken imports (fixed in Epic 4)
- [x] Empty `services/` directory removed
- [ ] Service decomposition plan updated to reflect 9-group structure

**Execution Notes:**
- `ner-service` and `openai-service` listed in original plan do NOT exist in the filesystem — ml-engine has 8 services, not 10
- `ha-simulator` added to core-platform (simulates HA websocket connection)
- `services/archive/` (untracked, deprecated Q4 2025 services) moved to `domains/archive/`
- `services/tests/` (shared test datasets) moved to `domains/tests/`
- 3 markdown files (`README_ARCHITECTURE_QUICK_REF.md`, `SERVICES_RANKED_BY_IMPORTANCE.md`, `TIER7_DEEP_REVIEW_SUMMARY.md`) moved to `docs/architecture/`

---

## User Stories

### Story 1: Create Domain Directory Structure

**As a** developer navigating the HomeIQ monorepo
**I want** a `domains/` directory with 9 group subdirectories, each containing a README
**So that** the filesystem reflects the logical domain architecture before services are moved

**Acceptance Criteria:**
- [ ] `domains/` directory created at project root
- [ ] 9 subdirectories created: `core-platform`, `data-collectors`, `ml-engine`, `automation-core`, `blueprints`, `energy-analytics`, `device-management`, `pattern-analysis`, `frontends`
- [ ] Each subdirectory contains a `README.md` describing the domain's purpose, services, and dependencies
- [ ] README files follow a consistent template: Purpose, Services (table), Depends On, Depended On By

**Story Points:** 2
**Dependencies:** None
**Affected Services:** None (directory creation only)
**Agent-Automatable:** Yes -- Claude sub-agent can create all directories and READMEs

---

### Story 2: Move core-platform Services

**As a** developer working on core infrastructure
**I want** the 5 core-platform services grouped under `domains/core-platform/`
**So that** I can find all data backbone services in one location

**Acceptance Criteria:**
- [ ] `services/websocket-ingestion` moved to `domains/core-platform/websocket-ingestion`
- [ ] `services/data-api` moved to `domains/core-platform/data-api`
- [ ] `services/admin-api` moved to `domains/core-platform/admin-api`
- [ ] `services/health-dashboard` moved to `domains/core-platform/health-dashboard`
- [ ] `services/data-retention` moved to `domains/core-platform/data-retention`
- [ ] influxdb is an external Docker image -- not moved, documented in README only
- [ ] All files preserved with `git mv` (no copy-delete)

**Exact commands:**
```bash
git mv services/websocket-ingestion domains/core-platform/websocket-ingestion
git mv services/data-api domains/core-platform/data-api
git mv services/admin-api domains/core-platform/admin-api
git mv services/health-dashboard domains/core-platform/health-dashboard
git mv services/data-retention domains/core-platform/data-retention
```

**Story Points:** 3
**Dependencies:** Story 1
**Affected Services:** websocket-ingestion (8001), data-api (8006), admin-api (8003/8004), health-dashboard (3000), data-retention (8080)

---

### Story 3: Move data-collectors Services

**As a** developer working on data ingestion
**I want** the 8 data collector services grouped under `domains/data-collectors/`
**So that** all external data fetchers are co-located by domain

**Acceptance Criteria:**
- [ ] `services/weather-api` moved to `domains/data-collectors/weather-api`
- [ ] `services/smart-meter-service` moved to `domains/data-collectors/smart-meter-service`
- [ ] `services/sports-api` moved to `domains/data-collectors/sports-api`
- [ ] `services/air-quality-service` moved to `domains/data-collectors/air-quality-service`
- [ ] `services/carbon-intensity-service` moved to `domains/data-collectors/carbon-intensity-service`
- [ ] `services/electricity-pricing-service` moved to `domains/data-collectors/electricity-pricing-service`
- [ ] `services/calendar-service` moved to `domains/data-collectors/calendar-service`
- [ ] `services/log-aggregator` moved to `domains/data-collectors/log-aggregator`
- [ ] All files preserved with `git mv` (no copy-delete)

**Exact commands:**
```bash
git mv services/weather-api domains/data-collectors/weather-api
git mv services/smart-meter-service domains/data-collectors/smart-meter-service
git mv services/sports-api domains/data-collectors/sports-api
git mv services/air-quality-service domains/data-collectors/air-quality-service
git mv services/carbon-intensity-service domains/data-collectors/carbon-intensity-service
git mv services/electricity-pricing-service domains/data-collectors/electricity-pricing-service
git mv services/calendar-service domains/data-collectors/calendar-service
git mv services/log-aggregator domains/data-collectors/log-aggregator
```

**Story Points:** 3
**Dependencies:** Story 1
**Affected Services:** weather-api (8009), smart-meter-service (8014), sports-api (8005), air-quality-service (8012), carbon-intensity-service (8010), electricity-pricing-service (8011), calendar-service (8013), log-aggregator (8015)

---

### Story 4: Move ml-engine Services

**As a** developer working on ML and AI inference
**I want** the 10 ML services grouped under `domains/ml-engine/`
**So that** all model inference, embedding, and training services are co-located

**Acceptance Criteria:**
- [ ] `services/ai-core-service` moved to `domains/ml-engine/ai-core-service`
- [ ] `services/openvino-service` moved to `domains/ml-engine/openvino-service`
- [ ] `services/ml-service` moved to `domains/ml-engine/ml-service`
- [ ] `services/ner-service` moved to `domains/ml-engine/ner-service`
- [ ] `services/openai-service` moved to `domains/ml-engine/openai-service`
- [ ] `services/rag-service` moved to `domains/ml-engine/rag-service`
- [ ] `services/ai-training-service` moved to `domains/ml-engine/ai-training-service`
- [ ] `services/device-intelligence-service` moved to `domains/ml-engine/device-intelligence-service`
- [ ] `services/model-prep` moved to `domains/ml-engine/model-prep`
- [ ] `services/nlp-fine-tuning` moved to `domains/ml-engine/nlp-fine-tuning`
- [ ] All files preserved with `git mv` (no copy-delete)

**Exact commands:**
```bash
git mv services/ai-core-service domains/ml-engine/ai-core-service
git mv services/openvino-service domains/ml-engine/openvino-service
git mv services/ml-service domains/ml-engine/ml-service
git mv services/ner-service domains/ml-engine/ner-service
git mv services/openai-service domains/ml-engine/openai-service
git mv services/rag-service domains/ml-engine/rag-service
git mv services/ai-training-service domains/ml-engine/ai-training-service
git mv services/device-intelligence-service domains/ml-engine/device-intelligence-service
git mv services/model-prep domains/ml-engine/model-prep
git mv services/nlp-fine-tuning domains/ml-engine/nlp-fine-tuning
```

**Story Points:** 3
**Dependencies:** Story 1
**Affected Services:** ai-core-service (8018), openvino-service (8026), ml-service (8025), ner-service (8031), openai-service (8020), rag-service (8027), ai-training-service (8033), device-intelligence-service (8028), model-prep (one-shot), nlp-fine-tuning (one-shot)

---

### Story 5: Move automation-core Services

**As a** developer working on automation generation and deployment
**I want** the 7 automation-core services grouped under `domains/automation-core/`
**So that** the NL-to-YAML pipeline, validation, and deployment services are co-located

**Acceptance Criteria:**
- [ ] `services/ha-ai-agent-service` moved to `domains/automation-core/ha-ai-agent-service`
- [ ] `services/ai-automation-service-new` moved to `domains/automation-core/ai-automation-service-new`
- [ ] `services/ai-query-service` moved to `domains/automation-core/ai-query-service`
- [ ] `services/automation-linter` moved to `domains/automation-core/automation-linter`
- [ ] `services/yaml-validation-service` moved to `domains/automation-core/yaml-validation-service`
- [ ] `services/ai-code-executor` moved to `domains/automation-core/ai-code-executor`
- [ ] `services/automation-trace-service` moved to `domains/automation-core/automation-trace-service`
- [ ] All files preserved with `git mv` (no copy-delete)

**Exact commands:**
```bash
git mv services/ha-ai-agent-service domains/automation-core/ha-ai-agent-service
git mv services/ai-automation-service-new domains/automation-core/ai-automation-service-new
git mv services/ai-query-service domains/automation-core/ai-query-service
git mv services/automation-linter domains/automation-core/automation-linter
git mv services/yaml-validation-service domains/automation-core/yaml-validation-service
git mv services/ai-code-executor domains/automation-core/ai-code-executor
git mv services/automation-trace-service domains/automation-core/automation-trace-service
```

**Story Points:** 3
**Dependencies:** Story 1
**Affected Services:** ha-ai-agent-service (8030), ai-automation-service-new (8036), ai-query-service (8035), automation-linter (8016), yaml-validation-service (8037), ai-code-executor (internal), automation-trace-service (8044)

---

### Story 6: Move blueprints Services

**As a** developer working on blueprint discovery and suggestions
**I want** the 4 blueprint services grouped under `domains/blueprints/`
**So that** all blueprint-related indexing, suggestion, and recommendation services are co-located

**Acceptance Criteria:**
- [ ] `services/blueprint-index` moved to `domains/blueprints/blueprint-index`
- [ ] `services/blueprint-suggestion-service` moved to `domains/blueprints/blueprint-suggestion-service`
- [ ] `services/rule-recommendation-ml` moved to `domains/blueprints/rule-recommendation-ml`
- [ ] `services/automation-miner` moved to `domains/blueprints/automation-miner`
- [ ] All files preserved with `git mv` (no copy-delete)

**Exact commands:**
```bash
git mv services/blueprint-index domains/blueprints/blueprint-index
git mv services/blueprint-suggestion-service domains/blueprints/blueprint-suggestion-service
git mv services/rule-recommendation-ml domains/blueprints/rule-recommendation-ml
git mv services/automation-miner domains/blueprints/automation-miner
```

**Story Points:** 2
**Dependencies:** Story 1
**Affected Services:** blueprint-index (8038), blueprint-suggestion-service (8039), rule-recommendation-ml (8040), automation-miner (8029)

---

### Story 7: Move energy-analytics Services

**As a** developer working on energy analysis and forecasting
**I want** the 3 energy services grouped under `domains/energy-analytics/`
**So that** energy correlation, forecasting, and proactive recommendation services are co-located

**Acceptance Criteria:**
- [ ] `services/energy-correlator` moved to `domains/energy-analytics/energy-correlator`
- [ ] `services/energy-forecasting` moved to `domains/energy-analytics/energy-forecasting`
- [ ] `services/proactive-agent-service` moved to `domains/energy-analytics/proactive-agent-service`
- [ ] All files preserved with `git mv` (no copy-delete)

**Exact commands:**
```bash
git mv services/energy-correlator domains/energy-analytics/energy-correlator
git mv services/energy-forecasting domains/energy-analytics/energy-forecasting
git mv services/proactive-agent-service domains/energy-analytics/proactive-agent-service
```

**Story Points:** 2
**Dependencies:** Story 1
**Affected Services:** energy-correlator (8017), energy-forecasting (8042), proactive-agent-service (8031)

---

### Story 8: Move device-management Services

**As a** developer working on device lifecycle and monitoring
**I want** the 8 device services grouped under `domains/device-management/`
**So that** all device health, onboarding, classification, and activity services are co-located

**Acceptance Criteria:**
- [ ] `services/device-health-monitor` moved to `domains/device-management/device-health-monitor`
- [ ] `services/device-context-classifier` moved to `domains/device-management/device-context-classifier`
- [ ] `services/device-setup-assistant` moved to `domains/device-management/device-setup-assistant`
- [ ] `services/device-database-client` moved to `domains/device-management/device-database-client`
- [ ] `services/device-recommender` moved to `domains/device-management/device-recommender`
- [ ] `services/activity-recognition` moved to `domains/device-management/activity-recognition`
- [ ] `services/activity-writer` moved to `domains/device-management/activity-writer`
- [ ] `services/ha-setup-service` moved to `domains/device-management/ha-setup-service`
- [ ] All files preserved with `git mv` (no copy-delete)

**Exact commands:**
```bash
git mv services/device-health-monitor domains/device-management/device-health-monitor
git mv services/device-context-classifier domains/device-management/device-context-classifier
git mv services/device-setup-assistant domains/device-management/device-setup-assistant
git mv services/device-database-client domains/device-management/device-database-client
git mv services/device-recommender domains/device-management/device-recommender
git mv services/activity-recognition domains/device-management/activity-recognition
git mv services/activity-writer domains/device-management/activity-writer
git mv services/ha-setup-service domains/device-management/ha-setup-service
```

**Story Points:** 3
**Dependencies:** Story 1
**Affected Services:** device-health-monitor (8019), device-context-classifier (8032), device-setup-assistant (8021), device-database-client (8022), device-recommender (8023), activity-recognition (8043), activity-writer (8045), ha-setup-service (8024)

---

### Story 9: Move pattern-analysis Services

**As a** developer working on pattern detection and edge automation
**I want** the 2 pattern services grouped under `domains/pattern-analysis/`
**So that** pattern detection and API automation edge services are co-located

**Acceptance Criteria:**
- [ ] `services/ai-pattern-service` moved to `domains/pattern-analysis/ai-pattern-service`
- [ ] `services/api-automation-edge` moved to `domains/pattern-analysis/api-automation-edge`
- [ ] All files preserved with `git mv` (no copy-delete)

**Exact commands:**
```bash
git mv services/ai-pattern-service domains/pattern-analysis/ai-pattern-service
git mv services/api-automation-edge domains/pattern-analysis/api-automation-edge
```

**Story Points:** 1
**Dependencies:** Story 1
**Affected Services:** ai-pattern-service (8034), api-automation-edge (8041)

---

### Story 10: Move frontends Services

**As a** developer working on user-facing UIs
**I want** the 3 frontend services grouped under `domains/frontends/`
**So that** all UI and observability dashboard services are co-located

**Acceptance Criteria:**
- [ ] `services/ai-automation-ui` moved to `domains/frontends/ai-automation-ui`
- [ ] `services/observability-dashboard` moved to `domains/frontends/observability-dashboard`
- [ ] `services/health-dashboard` is already moved in Story 2 (core-platform) -- documented in frontends README as "developed here, deployed with core"
- [ ] jaeger is an external Docker image -- not moved, documented in README only
- [ ] All files preserved with `git mv` (no copy-delete)

**Note:** `health-dashboard` lives under `domains/core-platform/` for deployment availability. The frontends README documents this cross-domain relationship.

**Exact commands:**
```bash
git mv services/ai-automation-ui domains/frontends/ai-automation-ui
git mv services/observability-dashboard domains/frontends/observability-dashboard
```

**Story Points:** 2
**Dependencies:** Story 1
**Affected Services:** ai-automation-ui (3001), observability-dashboard (8501)

---

### Story 11: Remove Empty services/ Directory and Update .gitignore

**As a** developer maintaining the repository
**I want** the empty `services/` directory removed and `.gitignore` updated
**So that** there is no ambiguity about where services live

**Acceptance Criteria:**
- [ ] `services/` directory is empty (all services moved in Stories 2-10)
- [ ] Any remaining non-service files in `services/` (READMEs, etc.) are relocated or removed
- [ ] `services/` directory deleted
- [ ] `.gitignore` updated: any `services/`-specific patterns changed to `domains/`
- [ ] Verify total service count: sum of all domain directories matches expected count (50 moved services)

**Story Points:** 1
**Dependencies:** Stories 2, 3, 4, 5, 6, 7, 8, 9, 10 (all move stories must complete first)
**Affected Services:** None

---

### Story 12: Update Service Decomposition Plan for 9-Group Structure

**As a** developer or architect referencing the service decomposition plan
**I want** `docs/planning/service-decomposition-plan.md` updated to reflect the 9-group structure
**So that** documentation matches the actual filesystem layout

**Acceptance Criteria:**
- [ ] Document updated from 6 groups to 9 groups
- [ ] `automation-intelligence` (16 services) split into: `automation-core` (7), `blueprints` (4), `energy-analytics` (3), `pattern-analysis` (2)
- [ ] Group dependency graph updated for the 9-group structure
- [ ] All service-to-group assignments verified against actual `domains/` contents
- [ ] All path references updated from `services/` to `domains/{group}/`
- [ ] CI path trigger examples updated for `domains/` paths

**Story Points:** 2
**Dependencies:** Story 1 (group definitions must be finalized)
**Affected Services:** None (documentation only)

---

## Dependencies

```
                        Story 1
                 (Create domains/ structure)
                          |
        +-----------------+------------------+
        |    |    |    |    |    |    |    |    |
        v    v    v    v    v    v    v    v    v
       S2   S3   S4   S5   S6   S7   S8   S9  S10    S12
      core coll  ml  auto blue ener dev  patt front  docs
        |    |    |    |    |    |    |    |    |
        +---------+----+----+----+----+----+---+
                          |
                        Story 11
                 (Remove services/, update .gitignore)
```

**Legend:**
- S2 = Story 2 (core-platform), S3 = Story 3 (data-collectors), S4 = Story 4 (ml-engine)
- S5 = Story 5 (automation-core), S6 = Story 6 (blueprints), S7 = Story 7 (energy-analytics)
- S8 = Story 8 (device-management), S9 = Story 9 (pattern-analysis), S10 = Story 10 (frontends)
- S12 = Story 12 (documentation update) -- can start as soon as Story 1 is complete

**Key constraint:** Stories 2-10 and 12 are independent of each other and can execute in parallel. Story 11 requires all of Stories 2-10 to complete first.

---

## Suggested Execution Order

| Phase | Stories | Parallelism | Rationale |
|-------|---------|-------------|-----------|
| **Phase A** | Story 1 | Sequential | Must complete first -- creates the target directory structure |
| **Phase B** | Stories 2-10, 12 | Fully parallel (up to 10 agents) | All moves are independent; no cross-story file conflicts |
| **Phase C** | Story 11 | Sequential | Cleanup -- only after all moves are verified |

**Optimal timeline with agent parallelism:**
- Phase A: ~15 minutes (directory + README creation)
- Phase B: ~30 minutes (all 10 stories executing simultaneously)
- Phase C: ~5 minutes (verification + cleanup)
- **Total: under 1 hour with full parallelism**

---

## Agent Team Strategy

Stories 2-10 are ideal for Claude Agent Teams parallelization. Each story moves a disjoint set of service directories with zero file overlap.

**Recommended team structure:**

| Agent Role | Assigned Stories | Rationale |
|------------|-----------------|-----------|
| **Team Lead** | Story 1, Story 11 | Creates structure, performs final cleanup and verification |
| **Agent A** | Story 2 (core-platform) | 5 git mv commands |
| **Agent B** | Story 3 (data-collectors) | 8 git mv commands |
| **Agent C** | Story 4 (ml-engine) | 10 git mv commands |
| **Agent D** | Story 5 (automation-core) | 7 git mv commands |
| **Agent E** | Story 6 (blueprints) | 4 git mv commands |
| **Agent F** | Story 7 (energy-analytics) | 3 git mv commands |
| **Agent G** | Story 8 (device-management) | 8 git mv commands |
| **Agent H** | Story 9 (pattern-analysis) | 2 git mv commands |
| **Agent I** | Story 10 (frontends) | 2 git mv commands |
| **Agent J** | Story 12 (documentation) | Updates decomposition plan |

**Execution flow:**
1. Team Lead executes Story 1 (create directory structure)
2. Team Lead broadcasts "Story 1 complete" to all agents
3. Agents A-J execute their stories in parallel
4. Each agent marks their story complete via TaskUpdate
5. Team Lead waits for all 10 stories to complete
6. Team Lead executes Story 11 (cleanup and verification)

**Conflict avoidance:** No two agents touch the same files. Each agent moves services from `services/X` to `domains/Y/X` where X is unique per agent. Git handles the moves atomically per agent.

**Verification step (Story 11):** The Team Lead should run:
```bash
# Verify all services moved
ls domains/core-platform/ | wc -l        # expect 5
ls domains/data-collectors/ | wc -l      # expect 8
ls domains/ml-engine/ | wc -l            # expect 10
ls domains/automation-core/ | wc -l      # expect 7
ls domains/blueprints/ | wc -l           # expect 4
ls domains/energy-analytics/ | wc -l     # expect 3
ls domains/device-management/ | wc -l    # expect 8
ls domains/pattern-analysis/ | wc -l     # expect 2
ls domains/frontends/ | wc -l            # expect 2 (+ README)

# Verify services/ is empty
ls services/  # should show only non-service files (READMEs, etc.)

# Verify git tracks the moves
git status --short | grep "^R" | wc -l   # should match total moved files
```

---

## Service Inventory

Complete mapping of services to domain groups for verification:

| # | Service | Current Path | Target Path | Domain |
|---|---------|-------------|-------------|--------|
| 1 | websocket-ingestion | `services/websocket-ingestion` | `domains/core-platform/websocket-ingestion` | core-platform |
| 2 | data-api | `services/data-api` | `domains/core-platform/data-api` | core-platform |
| 3 | admin-api | `services/admin-api` | `domains/core-platform/admin-api` | core-platform |
| 4 | health-dashboard | `services/health-dashboard` | `domains/core-platform/health-dashboard` | core-platform |
| 5 | data-retention | `services/data-retention` | `domains/core-platform/data-retention` | core-platform |
| 6 | weather-api | `services/weather-api` | `domains/data-collectors/weather-api` | data-collectors |
| 7 | smart-meter-service | `services/smart-meter-service` | `domains/data-collectors/smart-meter-service` | data-collectors |
| 8 | sports-api | `services/sports-api` | `domains/data-collectors/sports-api` | data-collectors |
| 9 | air-quality-service | `services/air-quality-service` | `domains/data-collectors/air-quality-service` | data-collectors |
| 10 | carbon-intensity-service | `services/carbon-intensity-service` | `domains/data-collectors/carbon-intensity-service` | data-collectors |
| 11 | electricity-pricing-service | `services/electricity-pricing-service` | `domains/data-collectors/electricity-pricing-service` | data-collectors |
| 12 | calendar-service | `services/calendar-service` | `domains/data-collectors/calendar-service` | data-collectors |
| 13 | log-aggregator | `services/log-aggregator` | `domains/data-collectors/log-aggregator` | data-collectors |
| 14 | ai-core-service | `services/ai-core-service` | `domains/ml-engine/ai-core-service` | ml-engine |
| 15 | openvino-service | `services/openvino-service` | `domains/ml-engine/openvino-service` | ml-engine |
| 16 | ml-service | `services/ml-service` | `domains/ml-engine/ml-service` | ml-engine |
| 17 | ner-service | `services/ner-service` | `domains/ml-engine/ner-service` | ml-engine |
| 18 | openai-service | `services/openai-service` | `domains/ml-engine/openai-service` | ml-engine |
| 19 | rag-service | `services/rag-service` | `domains/ml-engine/rag-service` | ml-engine |
| 20 | ai-training-service | `services/ai-training-service` | `domains/ml-engine/ai-training-service` | ml-engine |
| 21 | device-intelligence-service | `services/device-intelligence-service` | `domains/ml-engine/device-intelligence-service` | ml-engine |
| 22 | model-prep | `services/model-prep` | `domains/ml-engine/model-prep` | ml-engine |
| 23 | nlp-fine-tuning | `services/nlp-fine-tuning` | `domains/ml-engine/nlp-fine-tuning` | ml-engine |
| 24 | ha-ai-agent-service | `services/ha-ai-agent-service` | `domains/automation-core/ha-ai-agent-service` | automation-core |
| 25 | ai-automation-service-new | `services/ai-automation-service-new` | `domains/automation-core/ai-automation-service-new` | automation-core |
| 26 | ai-query-service | `services/ai-query-service` | `domains/automation-core/ai-query-service` | automation-core |
| 27 | automation-linter | `services/automation-linter` | `domains/automation-core/automation-linter` | automation-core |
| 28 | yaml-validation-service | `services/yaml-validation-service` | `domains/automation-core/yaml-validation-service` | automation-core |
| 29 | ai-code-executor | `services/ai-code-executor` | `domains/automation-core/ai-code-executor` | automation-core |
| 30 | automation-trace-service | `services/automation-trace-service` | `domains/automation-core/automation-trace-service` | automation-core |
| 31 | blueprint-index | `services/blueprint-index` | `domains/blueprints/blueprint-index` | blueprints |
| 32 | blueprint-suggestion-service | `services/blueprint-suggestion-service` | `domains/blueprints/blueprint-suggestion-service` | blueprints |
| 33 | rule-recommendation-ml | `services/rule-recommendation-ml` | `domains/blueprints/rule-recommendation-ml` | blueprints |
| 34 | automation-miner | `services/automation-miner` | `domains/blueprints/automation-miner` | blueprints |
| 35 | energy-correlator | `services/energy-correlator` | `domains/energy-analytics/energy-correlator` | energy-analytics |
| 36 | energy-forecasting | `services/energy-forecasting` | `domains/energy-analytics/energy-forecasting` | energy-analytics |
| 37 | proactive-agent-service | `services/proactive-agent-service` | `domains/energy-analytics/proactive-agent-service` | energy-analytics |
| 38 | device-health-monitor | `services/device-health-monitor` | `domains/device-management/device-health-monitor` | device-management |
| 39 | device-context-classifier | `services/device-context-classifier` | `domains/device-management/device-context-classifier` | device-management |
| 40 | device-setup-assistant | `services/device-setup-assistant` | `domains/device-management/device-setup-assistant` | device-management |
| 41 | device-database-client | `services/device-database-client` | `domains/device-management/device-database-client` | device-management |
| 42 | device-recommender | `services/device-recommender` | `domains/device-management/device-recommender` | device-management |
| 43 | activity-recognition | `services/activity-recognition` | `domains/device-management/activity-recognition` | device-management |
| 44 | activity-writer | `services/activity-writer` | `domains/device-management/activity-writer` | device-management |
| 45 | ha-setup-service | `services/ha-setup-service` | `domains/device-management/ha-setup-service` | device-management |
| 46 | ai-pattern-service | `services/ai-pattern-service` | `domains/pattern-analysis/ai-pattern-service` | pattern-analysis |
| 47 | api-automation-edge | `services/api-automation-edge` | `domains/pattern-analysis/api-automation-edge` | pattern-analysis |
| 48 | ai-automation-ui | `services/ai-automation-ui` | `domains/frontends/ai-automation-ui` | frontends |
| 49 | observability-dashboard | `services/observability-dashboard` | `domains/frontends/observability-dashboard` | frontends |
| 50 | influxdb | (external image) | N/A -- documented in core-platform README | core-platform |
| 51 | jaeger | (external image) | N/A -- documented in frontends README | frontends |
| 52 | health-dashboard | (see row 4) | Deployed with core-platform, documented in frontends README | core-platform |

**Total moved:** 49 service directories (50 services minus influxdb external, minus jaeger external, health-dashboard counted once)

---

## Story Points Summary

| Story | Points | Description |
|-------|--------|-------------|
| Story 1 | 2 | Create directory structure |
| Story 2 | 3 | Move core-platform (5 services) |
| Story 3 | 3 | Move data-collectors (8 services) |
| Story 4 | 3 | Move ml-engine (10 services) |
| Story 5 | 3 | Move automation-core (7 services) |
| Story 6 | 2 | Move blueprints (4 services) |
| Story 7 | 2 | Move energy-analytics (3 services) |
| Story 8 | 3 | Move device-management (8 services) |
| Story 9 | 1 | Move pattern-analysis (2 services) |
| Story 10 | 2 | Move frontends (2 services + docs) |
| Story 11 | 1 | Cleanup services/ directory |
| Story 12 | 2 | Update decomposition plan docs |
| **Total** | **27** | |

---

## References

- [Service Decomposition Plan (6-group)](../docs/planning/service-decomposition-plan.md) -- original 6-group Option C plan, extended to 9 groups by this epic
- [Services Ranked by Importance](../docs/architecture/SERVICES_RANKED_BY_IMPORTANCE.md) -- tier rankings for prioritization
- [Architecture Quick Reference](../docs/architecture/README_ARCHITECTURE_QUICK_REF.md) -- current flat service listing
