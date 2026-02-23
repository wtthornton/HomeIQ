---
epic: shared-library-decomposition
priority: high
status: complete
estimated_duration: 5-7 days
risk_level: medium
source: docs/planning/service-decomposition-plan.md (Phase 2)
initiative: Domain Architecture Restructuring (Epic 2 of N)
---

# Epic: Shared Library Decomposition

**Status:** Complete
**Priority:** High
**Duration:** 5-7 days
**Risk Level:** Medium
**PRD Reference:** `docs/planning/service-decomposition-plan.md` (Phase 2)
**Initiative:** Domain Architecture Restructuring (Epic 2)

## Overview

Split the monolithic `shared/` directory into 5 independently installable Python packages under a new `libs/` directory. Currently, all 46+ services import from `shared/` via `sys.path` hacks wrapped in `try/except IndexError` for Docker compatibility. This epic replaces that fragile mechanism with proper pip-installable packages, each with its own `pyproject.toml`, versioning, and test suite.

**Current state:** `shared/` contains patterns, resilience, data access, Home Assistant integration, observability, and miscellaneous utilities -- all tangled into a single directory with no dependency boundaries.

**Target state:** 5 focused packages in `libs/`, installable via `pip install -e libs/homeiq-<name>/`, with explicit dependency declarations per service.

### The 5 Packages

| Package | Source Directory/Files | Primary Consumers |
|---------|----------------------|-------------------|
| `homeiq-patterns` | `shared/patterns/` | ha-ai-agent-service, ai-automation-service-new |
| `homeiq-resilience` | `shared/resilience/` | All services (cross-group health, circuit breakers) |
| `homeiq-data` | `shared/influxdb_query_client.py`, `database_pool.py`, `cache.py`, `correlation_cache.py`, `service_client.py`, `auth.py`, `error_handler.py` | data-api, energy-*, weather-api |
| `homeiq-ha` | `shared/ha_connection_manager.py`, `shared/ha_automation_lint/` | ha-ai-agent-service, ai-automation-service-new |
| `homeiq-observability` | `shared/metrics_collector.py`, `logging_config.py`, `monitoring/`, `observability/`, `alert_manager.py` | All services |

## Objectives

1. Eliminate `sys.path` hacks across all services
2. Make shared libraries independently installable via `pip install -e`
3. Enable explicit dependency declarations per service (in each service's `pyproject.toml` or `requirements.txt`)
4. Enable independent versioning of shared libraries

## Success Criteria

- [ ] All 5 packages installable via `pip install -e libs/homeiq-patterns/` (and equivalents)
- [ ] All 152 pattern tests pass under the new package structure
- [ ] All resilience tests pass (test_circuit_breaker, test_health, test_traceparent)
- [ ] No remaining source files in `shared/` directory (directory deleted)
- [ ] Each package has a valid `pyproject.toml` with correct metadata and dependencies
- [ ] At least one service's imports updated as proof-of-concept (full migration is a follow-up epic)
- [ ] Root workspace configuration enables `pip install -e .` for all packages simultaneously

---

## User Stories

### Story 1: Create `libs/` Directory Structure with 5 Package Scaffolds

**As a** platform engineer
**I want** a standardized `libs/` directory with 5 package subdirectories, each containing `pyproject.toml`, `src/` layout, and `__init__.py`
**So that** each package follows Python packaging best practices and can be independently installed

**Acceptance Criteria:**
- [ ] `libs/` directory created at project root
- [ ] 5 subdirectories created: `homeiq-patterns/`, `homeiq-resilience/`, `homeiq-data/`, `homeiq-ha/`, `homeiq-observability/`
- [ ] Each subdirectory contains `src/<package_name>/` layout (e.g., `libs/homeiq-patterns/src/homeiq_patterns/`)
- [ ] Each `src/<package_name>/` contains an `__init__.py` with package version (`__version__ = "0.1.0"`)
- [ ] Each subdirectory contains a `pyproject.toml` using `setuptools` build backend with `[project]` metadata
- [ ] Each subdirectory contains a `tests/` directory with `__init__.py`
- [ ] Each `pyproject.toml` declares `python_requires >= "3.11"`

**Story Points:** 3
**Dependencies:** None
**Affected Services:** None (scaffold only)

**Files Created:**
```
libs/
  homeiq-patterns/
    pyproject.toml
    src/homeiq_patterns/__init__.py
    tests/__init__.py
  homeiq-resilience/
    pyproject.toml
    src/homeiq_resilience/__init__.py
    tests/__init__.py
  homeiq-data/
    pyproject.toml
    src/homeiq_data/__init__.py
    tests/__init__.py
  homeiq-ha/
    pyproject.toml
    src/homeiq_ha/__init__.py
    tests/__init__.py
  homeiq-observability/
    pyproject.toml
    src/homeiq_observability/__init__.py
    tests/__init__.py
```

---

### Story 2: Package homeiq-patterns

**As a** developer building RAG, validation, or verification features
**I want** `shared/patterns/` extracted into `libs/homeiq-patterns/` as a pip-installable package
**So that** I can declare `homeiq-patterns` as an explicit dependency and import via `from homeiq_patterns import RAGContextService`

**Acceptance Criteria:**
- [ ] All source files from `shared/patterns/` moved to `libs/homeiq-patterns/src/homeiq_patterns/`
- [ ] `evaluation/` subdirectory moved to `libs/homeiq-patterns/src/homeiq_patterns/evaluation/`
- [ ] All 152 tests moved from `shared/patterns/tests/` to `libs/homeiq-patterns/tests/`
- [ ] `pyproject.toml` declares dependencies: `pydantic`, `aiohttp` (and others from existing `shared/patterns/pyproject.toml`)
- [ ] `__init__.py` exports: `RAGContextService`, `RAGContextRegistry`, `UnifiedValidationRouter`, `PostActionVerifier`
- [ ] Package installable: `pip install -e libs/homeiq-patterns/` succeeds
- [ ] `import homeiq_patterns` works after installation
- [ ] Existing `shared/patterns/README.md` moved to `libs/homeiq-patterns/README.md`

**Story Points:** 5
**Dependencies:** Story 1
**Affected Services:** ha-ai-agent-service (8030), ai-automation-service-new (8024)

**Files Moved:**
| Source | Destination |
|--------|-------------|
| `shared/patterns/__init__.py` | `libs/homeiq-patterns/src/homeiq_patterns/__init__.py` |
| `shared/patterns/rag_context_service.py` | `libs/homeiq-patterns/src/homeiq_patterns/rag_context_service.py` |
| `shared/patterns/rag_context_registry.py` | `libs/homeiq-patterns/src/homeiq_patterns/rag_context_registry.py` |
| `shared/patterns/unified_validation_router.py` | `libs/homeiq-patterns/src/homeiq_patterns/unified_validation_router.py` |
| `shared/patterns/post_action_verifier.py` | `libs/homeiq-patterns/src/homeiq_patterns/post_action_verifier.py` |
| `shared/patterns/evaluation/` | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/` |
| `shared/patterns/tests/` | `libs/homeiq-patterns/tests/` |
| `shared/patterns/README.md` | `libs/homeiq-patterns/README.md` |

---

### Story 3: Package homeiq-resilience

**As a** developer building fault-tolerant services
**I want** `shared/resilience/` extracted into `libs/homeiq-resilience/` as a pip-installable package
**So that** I can declare `homeiq-resilience` as an explicit dependency and import circuit breakers, health checks, and startup utilities

**Acceptance Criteria:**
- [ ] All source files from `shared/resilience/` moved to `libs/homeiq-resilience/src/homeiq_resilience/`
- [ ] All tests moved from `shared/resilience/tests/` to `libs/homeiq-resilience/tests/`
- [ ] `pyproject.toml` declares dependencies: `aiohttp`, `tenacity` (inferred from circuit breaker and retry logic)
- [ ] `__init__.py` exports: `CrossGroupClient`, `CircuitBreaker`, `GroupHealthCheck`, `wait_for_dependency`
- [ ] Package installable: `pip install -e libs/homeiq-resilience/` succeeds
- [ ] Existing `shared/resilience/README.md` moved to `libs/homeiq-resilience/README.md`

**Story Points:** 3
**Dependencies:** Story 1
**Affected Services:** All services using cross-group resilience

**Files Moved:**
| Source | Destination |
|--------|-------------|
| `shared/resilience/__init__.py` | `libs/homeiq-resilience/src/homeiq_resilience/__init__.py` |
| `shared/resilience/circuit_breaker.py` | `libs/homeiq-resilience/src/homeiq_resilience/circuit_breaker.py` |
| `shared/resilience/cross_group_client.py` | `libs/homeiq-resilience/src/homeiq_resilience/cross_group_client.py` |
| `shared/resilience/health.py` | `libs/homeiq-resilience/src/homeiq_resilience/health.py` |
| `shared/resilience/startup.py` | `libs/homeiq-resilience/src/homeiq_resilience/startup.py` |
| `shared/resilience/tests/` | `libs/homeiq-resilience/tests/` |
| `shared/resilience/README.md` | `libs/homeiq-resilience/README.md` |

---

### Story 4: Package homeiq-data

**As a** developer building data-access layers
**I want** the data-access utilities (InfluxDB client, database pool, caching, service client, auth, error handling) extracted into `libs/homeiq-data/`
**So that** I can declare `homeiq-data` as an explicit dependency and import via `from homeiq_data import InfluxDBQueryClient`

**Acceptance Criteria:**
- [ ] `shared/influxdb_query_client.py` moved to `libs/homeiq-data/src/homeiq_data/influxdb_query_client.py`
- [ ] `shared/database_pool.py` moved to `libs/homeiq-data/src/homeiq_data/database_pool.py`
- [ ] `shared/cache.py` moved to `libs/homeiq-data/src/homeiq_data/cache.py`
- [ ] `shared/correlation_cache.py` moved to `libs/homeiq-data/src/homeiq_data/correlation_cache.py`
- [ ] `shared/service_client.py` moved to `libs/homeiq-data/src/homeiq_data/service_client.py`
- [ ] `shared/auth.py` moved to `libs/homeiq-data/src/homeiq_data/auth.py`
- [ ] `shared/error_handler.py` moved to `libs/homeiq-data/src/homeiq_data/error_handler.py`
- [ ] `pyproject.toml` declares dependencies: `influxdb-client`, `aiosqlite`, `aiohttp`, `pydantic`
- [ ] `__init__.py` exports key classes: `InfluxDBQueryClient`, `DatabasePool`, `Cache`, `ServiceClient`
- [ ] Package installable: `pip install -e libs/homeiq-data/` succeeds

**Story Points:** 3
**Dependencies:** Story 1
**Affected Services:** data-api (8006), energy-forecasting (8037), energy-correlator (8017), weather-api

**Files Moved:**
| Source | Destination |
|--------|-------------|
| `shared/influxdb_query_client.py` | `libs/homeiq-data/src/homeiq_data/influxdb_query_client.py` |
| `shared/database_pool.py` | `libs/homeiq-data/src/homeiq_data/database_pool.py` |
| `shared/cache.py` | `libs/homeiq-data/src/homeiq_data/cache.py` |
| `shared/correlation_cache.py` | `libs/homeiq-data/src/homeiq_data/correlation_cache.py` |
| `shared/service_client.py` | `libs/homeiq-data/src/homeiq_data/service_client.py` |
| `shared/auth.py` | `libs/homeiq-data/src/homeiq_data/auth.py` |
| `shared/error_handler.py` | `libs/homeiq-data/src/homeiq_data/error_handler.py` |

---

### Story 5: Package homeiq-ha

**As a** developer building Home Assistant integrations
**I want** the HA connection manager and automation lint engine extracted into `libs/homeiq-ha/`
**So that** I can declare `homeiq-ha` as an explicit dependency and import via `from homeiq_ha import HAConnectionManager`

**Acceptance Criteria:**
- [ ] `shared/ha_connection_manager.py` moved to `libs/homeiq-ha/src/homeiq_ha/ha_connection_manager.py`
- [ ] `shared/ha_automation_lint/` directory moved to `libs/homeiq-ha/src/homeiq_ha/ha_automation_lint/`
- [ ] `ha_automation_lint/` internal imports updated (e.g., `from homeiq_ha.ha_automation_lint.engine import ...`)
- [ ] `pyproject.toml` declares dependencies: `aiohttp`, `websockets`, `pyyaml`
- [ ] `__init__.py` exports: `HAConnectionManager`, `ha_automation_lint` (sub-package)
- [ ] Package installable: `pip install -e libs/homeiq-ha/` succeeds
- [ ] `ha_automation_lint` sub-package modules (engine, constants, models, fixers, parsers, renderers, rules) all importable

**Story Points:** 2
**Dependencies:** Story 1
**Affected Services:** ha-ai-agent-service (8030), ai-automation-service-new (8024)

**Files Moved:**
| Source | Destination |
|--------|-------------|
| `shared/ha_connection_manager.py` | `libs/homeiq-ha/src/homeiq_ha/ha_connection_manager.py` |
| `shared/ha_automation_lint/__init__.py` | `libs/homeiq-ha/src/homeiq_ha/ha_automation_lint/__init__.py` |
| `shared/ha_automation_lint/constants.py` | `libs/homeiq-ha/src/homeiq_ha/ha_automation_lint/constants.py` |
| `shared/ha_automation_lint/engine.py` | `libs/homeiq-ha/src/homeiq_ha/ha_automation_lint/engine.py` |
| `shared/ha_automation_lint/models.py` | `libs/homeiq-ha/src/homeiq_ha/ha_automation_lint/models.py` |
| `shared/ha_automation_lint/fixers/` | `libs/homeiq-ha/src/homeiq_ha/ha_automation_lint/fixers/` |
| `shared/ha_automation_lint/parsers/` | `libs/homeiq-ha/src/homeiq_ha/ha_automation_lint/parsers/` |
| `shared/ha_automation_lint/renderers/` | `libs/homeiq-ha/src/homeiq_ha/ha_automation_lint/renderers/` |
| `shared/ha_automation_lint/rules/` | `libs/homeiq-ha/src/homeiq_ha/ha_automation_lint/rules/` |

---

### Story 6: Package homeiq-observability

**As a** developer instrumenting services with metrics, logging, and monitoring
**I want** the observability stack extracted into `libs/homeiq-observability/`
**So that** I can declare `homeiq-observability` as an explicit dependency and import via `from homeiq_observability import MetricsCollector`

**Acceptance Criteria:**
- [ ] `shared/metrics_collector.py` moved to `libs/homeiq-observability/src/homeiq_observability/metrics_collector.py`
- [ ] `shared/logging_config.py` moved to `libs/homeiq-observability/src/homeiq_observability/logging_config.py`
- [ ] `shared/alert_manager.py` moved to `libs/homeiq-observability/src/homeiq_observability/alert_manager.py`
- [ ] `shared/monitoring/` directory moved to `libs/homeiq-observability/src/homeiq_observability/monitoring/`
- [ ] `shared/observability/` directory moved to `libs/homeiq-observability/src/homeiq_observability/observability/`
- [ ] `monitoring/` internal imports updated (alerting_service, logging_service, metrics_service, monitoring_endpoints, stats_endpoints)
- [ ] `observability/` internal imports updated (correlation, logging, tracing)
- [ ] `pyproject.toml` declares dependencies: `prometheus-client`, `opentelemetry-api`, `structlog`
- [ ] `__init__.py` exports: `MetricsCollector`, `configure_logging`, `AlertManager`
- [ ] Package installable: `pip install -e libs/homeiq-observability/` succeeds

**Story Points:** 3
**Dependencies:** Story 1
**Affected Services:** All services (every service uses logging and metrics)

**Files Moved:**
| Source | Destination |
|--------|-------------|
| `shared/metrics_collector.py` | `libs/homeiq-observability/src/homeiq_observability/metrics_collector.py` |
| `shared/logging_config.py` | `libs/homeiq-observability/src/homeiq_observability/logging_config.py` |
| `shared/alert_manager.py` | `libs/homeiq-observability/src/homeiq_observability/alert_manager.py` |
| `shared/monitoring/` | `libs/homeiq-observability/src/homeiq_observability/monitoring/` |
| `shared/observability/` | `libs/homeiq-observability/src/homeiq_observability/observability/` |

---

### Story 7: Create Root Workspace Configuration

**As a** developer working across multiple HomeIQ packages
**I want** a root `pyproject.toml` with workspace configuration (using uv workspaces or hatch)
**So that** I can install all 5 packages at once with `pip install -e .` or `uv sync`

**Acceptance Criteria:**
- [ ] Root `pyproject.toml` (or updated existing one) declares workspace members: `libs/homeiq-*`
- [ ] `uv sync` (or equivalent) installs all 5 packages in editable mode
- [ ] Cross-package dependencies declared (e.g., `homeiq-ha` depends on `homeiq-data` if needed)
- [ ] `[tool.uv.workspace]` or `[tool.hatch.envs]` section correctly configured
- [ ] Developer README section explains how to install all packages locally
- [ ] CI/Docker can install packages with `pip install -e libs/homeiq-patterns/ libs/homeiq-resilience/` etc.

**Story Points:** 2
**Dependencies:** Stories 2, 3, 4, 5, 6 (all packages must exist)
**Affected Services:** None (build infrastructure)

---

### Story 8: Validate All 152 Pattern Tests Pass with New Package Structure

**As a** quality engineer
**I want** all 152 existing pattern tests to pass after the package restructuring
**So that** I have confidence the move introduced no regressions

**Acceptance Criteria:**
- [ ] `pytest libs/homeiq-patterns/tests/ -v` runs all 152 tests
- [ ] All 152 tests pass (zero failures, zero errors)
- [ ] Test imports updated from `shared.patterns.*` to `homeiq_patterns.*`
- [ ] `conftest.py` (if any) updated for new package paths
- [ ] Resilience tests also pass: `pytest libs/homeiq-resilience/tests/ -v`
- [ ] No tests reference `shared/` directory in imports or fixtures

**Story Points:** 3
**Dependencies:** Story 2 (homeiq-patterns package)
**Affected Services:** None (test infrastructure)

---

### Story 9: Delete Old `shared/` Directory

**As a** platform engineer
**I want** the old `shared/` directory removed after all code has been migrated
**So that** no service accidentally imports from the deprecated location

**Acceptance Criteria:**
- [ ] All files previously in `shared/` have been moved to their respective `libs/` packages
- [ ] Remaining files in `shared/` not covered by Stories 2-6 are accounted for (see Remaining Files table below)
- [ ] `shared/` directory deleted from the repository
- [ ] `grep -r "from shared" services/` returns zero matches (or a tracked list for follow-up migration)
- [ ] `grep -r "sys.path.*shared" services/` returns zero matches (or a tracked list for follow-up migration)
- [ ] CI builds pass without `shared/` directory

**Story Points:** 1
**Dependencies:** Stories 2, 3, 4, 5, 6 (all packages moved), Story 8 (tests pass)
**Affected Services:** All services (import paths)

**Remaining `shared/` Files Not in Stories 2-6:**

These files must be assigned to a package or deprecated before deletion:

| File | Recommended Destination | Notes |
|------|------------------------|-------|
| `shared/correlation_middleware.py` | `libs/homeiq-observability/` | Request correlation middleware |
| `shared/deployment_validation.py` | `libs/homeiq-ha/` | Deployment validation logic |
| `shared/enhanced_ha_connection_manager.py` | `libs/homeiq-ha/` | Extended HA connection manager |
| `shared/exceptions.py` | `libs/homeiq-data/` | Common exception classes |
| `shared/log_validator.py` | `libs/homeiq-observability/` | Log format validation |
| `shared/metrics_api.py` | `libs/homeiq-observability/` | Metrics API endpoints |
| `shared/rate_limiter.py` | `libs/homeiq-data/` | Rate limiting utility |
| `shared/service_container.py` | `libs/homeiq-data/` | DI container |
| `shared/state_machine.py` | `libs/homeiq-data/` | State machine utility |
| `shared/system_metrics.py` | `libs/homeiq-observability/` | System metrics collection |
| `shared/endpoints/` | `libs/homeiq-observability/` | Shared endpoint utilities |
| `shared/homeiq_automation/` | `libs/homeiq-ha/` | Automation utilities |
| `shared/prompt_guidance/` | `libs/homeiq-patterns/` | Prompt guidance data |
| `shared/types/` | `libs/homeiq-data/` | Shared type definitions |
| `shared/yaml_validation_service/` | `libs/homeiq-ha/` | YAML validation service |

---

## Dependencies

```
Story 1 (Scaffold libs/)
    ├──> Story 2 (homeiq-patterns)  ──┐
    ├──> Story 3 (homeiq-resilience) ─┤
    ├──> Story 4 (homeiq-data)  ──────┤──> Story 7 (Workspace Config)
    ├──> Story 5 (homeiq-ha)  ────────┤        │
    └──> Story 6 (homeiq-observability)┘        │
              │                                 │
              ├── Story 2 ──> Story 8 (Validate Tests)
              │                    │
              └────────────────────┴──> Story 9 (Delete shared/)
```

## Suggested Execution Order

| Day | Stories | Rationale |
|-----|---------|-----------|
| **Day 1** | Story 1 | Scaffold must exist before any package work |
| **Day 1-3** | Stories 2, 3, 4, 5, 6 (parallel) | All 5 packages can be created simultaneously; Story 2 is highest effort (5 SP) |
| **Day 3-4** | Story 7 | Workspace config after all packages exist |
| **Day 4-5** | Story 8 | Test validation after packages are installable |
| **Day 5** | Story 9 | Cleanup only after all tests pass |

**Total Story Points:** 25

---

## Agent Team Strategy

Stories 2-6 are fully parallelizable after Story 1 completes. This is an ideal workload for Claude Agent Teams.

### Recommended Team Composition

| Agent | Role | Assigned Stories | Notes |
|-------|------|-----------------|-------|
| **team-lead** | Orchestrator | Story 1, Story 7, Story 9 | Creates scaffold, then coordinates; owns workspace config and final cleanup |
| **patterns-agent** | Package builder | Story 2, Story 8 | Highest risk agent -- 152 tests to migrate; should start first |
| **resilience-agent** | Package builder | Story 3 | Smallest package with clear boundaries |
| **data-agent** | Package builder | Story 4 | 7 individual files to consolidate |
| **ha-agent** | Package builder | Story 5 | HA connection manager + lint engine subdirectory |
| **observability-agent** | Package builder | Story 6 | 2 subdirectories (monitoring/, observability/) + 3 files |
| **quality-watchdog** | Validator | Story 8 (assist) | Runs `tapps_validate_changed` on all moved files; blocks Story 9 until all gates pass |

### Execution Flow

1. **team-lead** completes Story 1 and broadcasts "scaffold ready"
2. **patterns-agent**, **resilience-agent**, **data-agent**, **ha-agent**, **observability-agent** start in parallel
3. Each agent messages **team-lead** on completion
4. **team-lead** starts Story 7 once all 5 agents report done
5. **patterns-agent** runs Story 8 (test validation) in parallel with Story 7
6. **quality-watchdog** validates all changed files
7. **team-lead** executes Story 9 only after Stories 7 and 8 are complete

### Risk Mitigation

- **Story 2 is highest risk** due to 152 tests and the `evaluation/` subdirectory with its own complex module tree. Assign the most capable agent.
- **Internal imports within `ha_automation_lint/`** (fixers, parsers, renderers, rules) must be updated to use `homeiq_ha.ha_automation_lint.*` paths.
- **Cross-package dependencies** (e.g., if `homeiq-ha` imports from `homeiq-data`) must be declared in `pyproject.toml` -- agents should flag any discovered cross-dependencies.

---

## Implementation Artifacts

| Artifact | Path |
|----------|------|
| **Package: homeiq-patterns** | `libs/homeiq-patterns/` |
| Package config | `libs/homeiq-patterns/pyproject.toml` |
| Source code | `libs/homeiq-patterns/src/homeiq_patterns/` |
| Tests (152) | `libs/homeiq-patterns/tests/` |
| Evaluation framework | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/` |
| **Package: homeiq-resilience** | `libs/homeiq-resilience/` |
| Package config | `libs/homeiq-resilience/pyproject.toml` |
| Source code | `libs/homeiq-resilience/src/homeiq_resilience/` |
| Tests | `libs/homeiq-resilience/tests/` |
| **Package: homeiq-data** | `libs/homeiq-data/` |
| Package config | `libs/homeiq-data/pyproject.toml` |
| Source code | `libs/homeiq-data/src/homeiq_data/` |
| **Package: homeiq-ha** | `libs/homeiq-ha/` |
| Package config | `libs/homeiq-ha/pyproject.toml` |
| Source code | `libs/homeiq-ha/src/homeiq_ha/` |
| HA Automation Lint sub-package | `libs/homeiq-ha/src/homeiq_ha/ha_automation_lint/` |
| **Package: homeiq-observability** | `libs/homeiq-observability/` |
| Package config | `libs/homeiq-observability/pyproject.toml` |
| Source code | `libs/homeiq-observability/src/homeiq_observability/` |
| Monitoring sub-package | `libs/homeiq-observability/src/homeiq_observability/monitoring/` |
| Observability sub-package | `libs/homeiq-observability/src/homeiq_observability/observability/` |
| **Workspace Configuration** | `pyproject.toml` (root, updated) |
| **Deleted Directory** | `shared/` (removed in Story 9) |

## Import Migration Reference

After this epic, service imports change from:

```python
# BEFORE (sys.path hack)
try:
    _project_root = str(Path(__file__).resolve().parents[4])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass

from shared.patterns.rag_context_service import RAGContextService
from shared.resilience import CircuitBreaker
from shared.influxdb_query_client import InfluxDBQueryClient
from shared.logging_config import configure_logging
```

```python
# AFTER (pip-installed packages)
from homeiq_patterns import RAGContextService
from homeiq_resilience import CircuitBreaker
from homeiq_data import InfluxDBQueryClient
from homeiq_observability import configure_logging
```

> **Note:** Full service import migration across all 46+ services is tracked as a separate follow-up epic (Epic 3: Service Import Migration). This epic focuses solely on creating the packages and validating they work.

## References

- [Service Decomposition Plan (PRD)](../docs/planning/service-decomposition-plan.md)
- [Reusable Pattern Framework (predecessor)](epic-reusable-pattern-framework.md)
- [High-Value Domain Extensions](epic-high-value-domain-extensions.md)
- [Platform-Wide Pattern Rollout](epic-platform-wide-pattern-rollout.md)
- [Shared Patterns README](../libs/homeiq-patterns/README.md)
- [Shared Resilience README](../libs/homeiq-resilience/README.md)
