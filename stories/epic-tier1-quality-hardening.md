---
epic: tier1-quality-hardening
priority: critical
status: complete
estimated_duration: 2-3 weeks
risk_level: medium
source: reports/quality/TAPPS_BASELINE.md
type: quality
---

# Epic 17: Tier 1 Critical Services — Quality Gate 80+

**Status:** Complete (Mar 4, 2026 — Agent Teams Wave 2: admin 80.3, ws 84.9, data-api 84.9)
**Priority:** P0 Critical
**Duration:** 2-3 weeks
**Risk Level:** Medium (refactoring production-critical code)
**Source:** [TAPPS Quality Baseline](../reports/quality/TAPPS_BASELINE.md)
**Affects:** core-platform (3 Tier 1 services)

## Context

Tier 1 services are the backbone of HomeIQ's event pipeline:
- **websocket-ingestion** (8001): All HA events flow through here
- **data-api** (8006): All query and metadata access
- **admin-api** (8004): System administration and configuration

All three **fail the strict (80+) quality gate**. admin-api (67.2) even fails the standard (70) gate.

| Service | Current Score | Target | Gap | Key Issues |
|---------|--------------|--------|-----|------------|
| admin-api | 67.2 | 80 | 12.8 | Complexity 5.6, test_coverage 5, devex 0 |
| websocket-ingestion | 70.9 | 80 | 9.1 | CC~14, maintainability 6, lint issues |
| data-api | 72.1 | 80 | 7.9 | Complexity 3.8, test_coverage 5, devex 0 |

**Scoring categories (max 10 each, weighted):**
- complexity, security, maintainability, test_coverage, performance, structure, devex

---

## Stories

### Story 17.1: admin-api — Refactor for Quality Gate

**Priority:** P0 | **Estimate:** 8h | **Risk:** Medium

**Current:** Score 67.2 | complexity=5.6, security=10, maintainability=6, test_coverage=5, performance=8, structure=10, devex=0

**Problem:** admin-api fails even the standard (70) gate. Key gaps are maintainability (6/7 needed for strict), test coverage, and devex (type hints, docstrings).

**Acceptance Criteria:**
- [ ] Reduce cyclomatic complexity in main.py — break up complex endpoint handlers
- [ ] Add type annotations to public functions and route handlers
- [ ] Add docstrings to FastAPI route handlers (these become OpenAPI descriptions)
- [ ] Add at least 3-5 unit tests for critical endpoints (health, config, docker)
- [ ] Fix any remaining lint issues (run `tapps_quick_check --fix`)
- [ ] Achieve `tapps_quality_gate(preset="strict")` PASS (score >= 80)

---

### Story 17.2: websocket-ingestion — Reduce Complexity & Fix Lint

**Priority:** P0 | **Estimate:** 8h | **Risk:** Medium

**Current:** Score 70.9 | complexity=6.8, security=10, maintainability=6, test_coverage=7, performance=9.5, structure=10, devex=4

**Problem:** CC~14 (moderate complexity) in event processing functions. Unused `logging` import. `datetime.utcnow()` usage. Missing type hints.

**Acceptance Criteria:**
- [ ] Split high-CC functions (target CC < 10 per function) — likely `process_event()` or `handle_message()`
- [ ] Remove unused `logging` import (F401)
- [ ] Fix `datetime.utcnow()` → `datetime.now(UTC)` (UP017)
- [ ] Fix import sorting (I001)
- [ ] Add type annotations to public functions
- [ ] Suppress B104 (intentional Docker bind)
- [ ] Achieve `tapps_quality_gate(preset="strict")` PASS (score >= 80)

---

### Story 17.3: data-api — Improve Coverage & DevEx

**Priority:** High | **Estimate:** 6h | **Risk:** Low

**Current:** Score 72.1 | complexity=3.8, security=10, maintainability=6, test_coverage=5, performance=10, structure=10, devex=0

**Problem:** Low test coverage (5/10) and zero devex score (no type hints, minimal docstrings). Complexity is already reasonable.

**Acceptance Criteria:**
- [ ] Add type annotations to all route handlers and service functions in main.py
- [ ] Add docstrings to FastAPI endpoints (auto-generate OpenAPI docs)
- [ ] Add 5-8 unit tests for critical query endpoints
- [ ] Raise maintainability from 6 to 7+ (may require extracting helper functions)
- [ ] Achieve `tapps_quality_gate(preset="strict")` PASS (score >= 80)

---

### Story 17.4: Integration Verification

**Priority:** High | **Estimate:** 3h | **Risk:** Low

**Problem:** After refactoring Tier 1 services, we must verify no regressions in the critical data flow: HA → websocket-ingestion → InfluxDB → data-api → health-dashboard.

**Acceptance Criteria:**
- [ ] Run `tapps_validate_changed()` on all modified files across the 3 services
- [ ] All 3 services pass `tapps_quality_gate(preset="strict")`
- [ ] Run `tapps_impact_analysis()` on any changed public APIs
- [ ] Update `reports/quality/TAPPS_BASELINE.md` with new Tier 1 scores
- [ ] Verify health endpoints still respond correctly
- [ ] Run existing test suites — no regressions

---

## Summary

| Story | Service | Current | Target | Est. |
|-------|---------|---------|--------|------|
| 17.1 | admin-api | 67.2 | 80+ | 8h |
| 17.2 | websocket-ingestion | 70.9 | 80+ | 8h |
| 17.3 | data-api | 72.1 | 80+ | 6h |
| 17.4 | Integration verification | — | — | 3h |
| **Total** | | | | **~25h** |

## Dependencies

- **Epic 16** (lint cleanup) should run first — it will boost scores by 2-5 points before this epic starts
- Stories 17.1-17.3 can be parallelized
- Story 17.4 depends on 17.1-17.3

## Risk Mitigation

- websocket-ingestion handles all HA events — refactoring must preserve event processing behavior
- data-api is the query backbone — any API signature changes break consumers
- Use `tapps_impact_analysis()` before changing any public interfaces
- All changes should be behind feature flags or backward-compatible
