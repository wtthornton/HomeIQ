---
epic: shared-library-strict-compliance
priority: high
status: complete
estimated_duration: 1-2 weeks
risk_level: low
source: reports/quality/TAPPS_BASELINE.md
type: quality
---

# Epic 20: Shared Library Strict Gate Compliance

**Status:** Complete (Mar 4, 2026 — lint fixes pushed all libs to 81.6+)
**Priority:** High (P1)
**Duration:** 1-2 weeks
**Risk Level:** Low
**Source:** [TAPPS Quality Baseline](../reports/quality/TAPPS_BASELINE.md)
**Affects:** libs/ (5 shared packages used by all 50 services)

## Context

All 5 shared libraries fail the strict (80+) quality gate. They all score within a narrow band (76.3-76.8), just 3-4 points below the target. Since these libraries are imported by every service in the project, their quality bar should be the highest.

| Library | Score | Gap to 80 | Key Category Gaps |
|---------|-------|-----------|-------------------|
| homeiq-patterns | 76.5 | 3.5 | test_coverage=0, devex=0 |
| homeiq-resilience | 76.8 | 3.2 | test_coverage=0, devex=0 |
| homeiq-observability | 76.3 | 3.7 | test_coverage=0, devex=0, structure=9 |
| homeiq-data | 76.3 | 3.7 | test_coverage=0, devex=0, structure=9 |
| homeiq-ha | 76.3 | 3.7 | test_coverage=0, devex=0, structure=9 |

**Pattern:** All libs score 0 on `test_coverage` and `devex`. Adding tests and type annotations/docstrings to the `__init__.py` entry points will close the gap.

**Note:** homeiq-patterns already has 704+ tests in `libs/homeiq-patterns/tests/`. The issue is that TAPPS scores `__init__.py` entry points, not the full test suite. We may need to score additional source files to get a representative baseline.

---

## Stories

### Story 20.1: homeiq-resilience — Tests & Type Hints

**Priority:** High | **Estimate:** 4h | **Risk:** Low

**Scope:** `libs/homeiq-resilience/` — CircuitBreaker, CrossGroupClient, GroupHealthCheck, wait_for_dependency, app_factory, auth, health_check, http_client, lifespan, scheduler, startup

**Acceptance Criteria:**
- [ ] Add/verify tests for CircuitBreaker, CrossGroupClient, ServiceAuthValidator
- [ ] Add type annotations to all public exports in `__init__.py`
- [ ] Add module-level docstring to `__init__.py`
- [ ] Score the 3 most important source files (circuit_breaker.py, cross_group_client.py, auth.py)
- [ ] All scored files achieve `tapps_quality_gate(preset="strict")` PASS (>= 80)
- [ ] Update baseline

---

### Story 20.2: homeiq-data — Tests & Type Hints

**Priority:** High | **Estimate:** 4h | **Risk:** Low

**Scope:** `libs/homeiq-data/` — DatabaseManager, database_pool, InfluxDB client, caching, auth, base_settings, alembic_helpers, standard_data_api_client

**Acceptance Criteria:**
- [ ] Add/verify tests for DatabaseManager, database_pool, StandardDataAPIClient
- [ ] Add type annotations to all public exports
- [ ] Add module-level docstring to `__init__.py`
- [ ] Score key source files (database_manager.py, database_pool.py, standard_data_api_client.py)
- [ ] All scored files achieve `tapps_quality_gate(preset="strict")` PASS
- [ ] Update baseline

---

### Story 20.3: homeiq-patterns — Verify Existing Tests

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

**Scope:** `libs/homeiq-patterns/` — RAGContextService, UnifiedValidationRouter, PostActionVerifier

**Problem:** Already has 704+ tests, but `__init__.py` scores 0 on test_coverage. Need to verify tests exist and score representative source files.

**Acceptance Criteria:**
- [ ] Verify existing test suite covers RAGContextService, UnifiedValidationRouter, PostActionVerifier
- [ ] Add type annotations and docstring to `__init__.py` if missing
- [ ] Score 3 key source files (rag_context_service.py, unified_validation_router.py, post_action_verifier.py)
- [ ] All scored files achieve `tapps_quality_gate(preset="strict")` PASS
- [ ] Update baseline

---

### Story 20.4: homeiq-observability — Tests & Type Hints

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

**Scope:** `libs/homeiq-observability/` — logging_config, monitoring, metrics, tracing

**Acceptance Criteria:**
- [ ] Add tests for logging_config setup, metrics collection, tracing configuration
- [ ] Add type annotations to public exports
- [ ] Add module-level docstring
- [ ] Score key source files (logging_config.py, monitoring.py)
- [ ] All scored files achieve `tapps_quality_gate(preset="strict")` PASS
- [ ] Update baseline

---

### Story 20.5: homeiq-ha — Tests & Type Hints

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

**Scope:** `libs/homeiq-ha/` — HA connection manager, automation lint engine

**Acceptance Criteria:**
- [ ] Add/verify tests for HA connection manager and lint engine
- [ ] Add type annotations to public exports
- [ ] Add module-level docstring
- [ ] Score key source files
- [ ] All scored files achieve `tapps_quality_gate(preset="strict")` PASS
- [ ] Update baseline

---

### Story 20.6: Library Re-Score & Baseline Update

**Priority:** High | **Estimate:** 1h | **Risk:** Low

**Acceptance Criteria:**
- [ ] Run `tapps_quality_gate(preset="strict")` on all 5 library entry points
- [ ] All 5 achieve score >= 80
- [ ] Update `reports/quality/TAPPS_BASELINE.md` — libs pass rate: 0/5 → 5/5
- [ ] Update rollup summary

---

## Summary

| Story | Library | Current | Target | Est. |
|-------|---------|---------|--------|------|
| 20.1 | homeiq-resilience | 76.8 | 80+ | 4h |
| 20.2 | homeiq-data | 76.3 | 80+ | 4h |
| 20.3 | homeiq-patterns | 76.5 | 80+ | 2h |
| 20.4 | homeiq-observability | 76.3 | 80+ | 3h |
| 20.5 | homeiq-ha | 76.3 | 80+ | 3h |
| 20.6 | Re-score & baseline update | — | — | 1h |
| **Total** | | | | **~17h** |

## Dependencies

- **None** — this epic is independent
- Stories 20.1-20.5 can be parallelized
- Story 20.6 must be last
