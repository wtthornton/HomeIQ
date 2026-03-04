---
epic: low-score-remediation
priority: high
status: complete
estimated_duration: 2-3 weeks
risk_level: medium
source: reports/quality/TAPPS_BASELINE.md
type: quality
---

# Epic 19: Low-Score Service Remediation

**Status:** Complete (Mar 4, 2026 — Agent Teams Wave 2: 8/8 pass 70+)
**Priority:** High (P1)
**Duration:** 2-3 weeks
**Risk Level:** Medium (some services have high complexity)
**Source:** [TAPPS Quality Baseline](../reports/quality/TAPPS_BASELINE.md)
**Affects:** 7 services across 4 domains scoring below 67

## Context

Seven services score significantly below the standard (70) threshold, with the bottom two under 55. These represent the worst code quality in the project and need targeted remediation beyond the mechanical lint fixes in Epic 16.

| # | Service | Domain | Score | Gap | Key Issues |
|---|---------|--------|-------|-----|------------|
| 1 | activity-writer | device-management | 51.9 | 18.1 | CC~21, perf 5.5, sec 8 |
| 2 | ha-setup-service | device-management | 54.4 | 15.6 | 9 lint, no tests, large file |
| 3 | ml-service | ml-engine | 57.1 | 12.9 | CC~20, test_coverage 3 |
| 4 | ai-core-service | ml-engine | 58.4 | 11.6 | No tests, B104 |
| 5 | openvino-service | ml-engine | 59.4 | 10.6 | 3 UP041, B104 |
| 6 | ha-ai-agent-service | automation-core | 66.5 | 3.5 | CC~16, unused imports |
| 7 | automation-linter | automation-core | 64.6 | 5.4 | Structure 3/10 |

**Note:** data-collectors services (all <67) are handled in Epic 18 and excluded here.

---

## Stories

### Story 19.1: activity-writer — Major Refactoring (Score 51.9)

**Priority:** High | **Estimate:** 8h | **Risk:** Medium

**Current:** complexity=10, security=8, maintainability=6, test_coverage=5, performance=5.5, structure=10, devex=0

**Problem:** Worst score in the project. CC~21 means deeply nested logic. Performance score is low (5.5/10 — likely blocking I/O patterns). Security at 8 (below perfect 10).

**Acceptance Criteria:**
- [ ] Run `tapps_impact_analysis` before refactoring
- [ ] Split high-CC functions — extract InfluxDB write logic, event processing, retry logic into separate modules
- [ ] Fix performance issues (likely synchronous blocking in async code, or N+1 patterns)
- [ ] Add type annotations and 3-5 unit tests
- [ ] Fix lint issues (I001, UP041, UP017)
- [ ] Suppress B104 (Docker bind)
- [ ] Target score >= 70; achieve `tapps_quality_gate(preset="standard")` PASS

---

### Story 19.2: ha-setup-service — Lint Cleanup & Tests (Score 54.4)

**Priority:** High | **Estimate:** 6h | **Risk:** Low

**Current:** complexity=10, security=10, maintainability=6, test_coverage=0, performance=10, structure=10, devex=0

**Problem:** 9 lint issues (all UP017 datetime.UTC). Zero test coverage. Large main.py (936+ lines).

**Acceptance Criteria:**
- [ ] Fix all 9 UP017 occurrences (datetime.UTC)
- [ ] Suppress B104 (Docker bind)
- [ ] Add 5-8 tests covering health checks, setup endpoints, integration verification
- [ ] Add type annotations to route handlers
- [ ] Consider extracting sub-modules if main.py > 500 lines of logic
- [ ] Target score >= 70; achieve `tapps_quality_gate(preset="standard")` PASS

---

### Story 19.3: ml-service — Reduce CC~20 & Add Tests (Score 57.1)

**Priority:** High | **Estimate:** 6h | **Risk:** Medium

**Current:** complexity=10, security=10, maintainability=6, test_coverage=3, performance=8.5, structure=10, devex=0

**Problem:** CC~20 (high complexity). 655+ line main.py. Test coverage at 3/10.

**Acceptance Criteria:**
- [ ] Run `tapps_impact_analysis` before refactoring
- [ ] Split high-CC functions — extract algorithm routing, model loading, prediction logic
- [ ] Fix UP041 (`asyncio.TimeoutError` → `TimeoutError`)
- [ ] Suppress B104
- [ ] Add 5+ tests for ML prediction endpoints
- [ ] Target score >= 70; achieve `tapps_quality_gate(preset="standard")` PASS

---

### Story 19.4: ai-core-service — Add Tests & Fix B104 (Score 58.4)

**Priority:** Medium | **Estimate:** 4h | **Risk:** Low

**Current:** complexity=7.8, security=10, maintainability=6, test_coverage=0, performance=10, structure=10, devex=0

**Problem:** Zero test coverage is the primary gap. 521-line main.py with moderate complexity.

**Acceptance Criteria:**
- [ ] Add 5-8 tests for orchestrator endpoints, pattern analysis, health checks
- [ ] Add type annotations to route handlers
- [ ] Suppress B104
- [ ] Target score >= 70; achieve `tapps_quality_gate(preset="standard")` PASS

---

### Story 19.5: openvino-service — Fix UP041 & Add Tests (Score 59.4)

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

**Current:** complexity=7.2, security=10, maintainability=6, test_coverage=0, performance=10, structure=10, devex=0

**Problem:** 3 UP041 occurrences. Zero test coverage. B104.

**Acceptance Criteria:**
- [ ] Fix 3x `asyncio.TimeoutError` → `TimeoutError` (UP041)
- [ ] Suppress B104
- [ ] Add 3-5 tests for model inference endpoints
- [ ] Target score >= 70; achieve `tapps_quality_gate(preset="standard")` PASS

---

### Story 19.6: ha-ai-agent-service — Fix Imports & Reduce CC (Score 66.5)

**Priority:** Medium | **Estimate:** 4h | **Risk:** Medium

**Current:** complexity=8, security=10, maintainability=6, test_coverage=5, performance=10, structure=10, devex=4

**Problem:** CC~16 (high). Unused imports (F401: contextlib.suppress, pathlib.Path). Close to passing (3.5 gap).

**Acceptance Criteria:**
- [ ] Remove unused imports (F401)
- [ ] Split functions with CC > 10 — likely in chat/context building logic
- [ ] Suppress B104
- [ ] Add type annotations to 5+ key functions
- [ ] Target score >= 70; achieve `tapps_quality_gate(preset="standard")` PASS

---

### Story 19.7: automation-linter & automation-trace-service — Fix Structure

**Priority:** Low | **Estimate:** 4h | **Risk:** Low

**automation-linter:** Score 64.6 | structure=3/10, test_coverage=0
**automation-trace-service:** Score 65.9 | structure=3/10, test_coverage=0

**Problem:** Both have very low structure scores (3/10) indicating poor code organization. Both have zero test coverage.

**Acceptance Criteria:**
- [ ] Investigate why structure scores are 3/10 — likely missing `__init__.py`, poor module organization, or single-file architecture
- [ ] Add proper package structure if needed
- [ ] Fix `SIM105` in automation-trace-service (use `contextlib.suppress`)
- [ ] Fix I001 in automation-linter
- [ ] Add 2-3 tests per service
- [ ] Both achieve `tapps_quality_gate(preset="standard")` PASS

---

## Summary

| Story | Service(s) | Current | Target | Est. |
|-------|-----------|---------|--------|------|
| 19.1 | activity-writer | 51.9 | 70+ | 8h |
| 19.2 | ha-setup-service | 54.4 | 70+ | 6h |
| 19.3 | ml-service | 57.1 | 70+ | 6h |
| 19.4 | ai-core-service | 58.4 | 70+ | 4h |
| 19.5 | openvino-service | 59.4 | 70+ | 3h |
| 19.6 | ha-ai-agent-service | 66.5 | 70+ | 4h |
| 19.7 | automation-linter + trace | 64.6/65.9 | 70+ | 4h |
| **Total** | | | | **~35h** |

## Dependencies

- **Epic 16** (lint cleanup) should complete first — handles mechanical fixes
- **Epic 17** handles Tier 1 services separately — no overlap
- Stories 19.1-19.7 can be parallelized
- Use `tapps_impact_analysis()` before refactoring any service with consumers
