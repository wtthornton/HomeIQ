---
epic: data-collectors-remediation
priority: high
status: complete
estimated_duration: 2-3 weeks
risk_level: low
source: reports/quality/TAPPS_BASELINE.md
type: quality
---

# Epic 18: Data Collectors Domain Remediation

**Status:** Complete (Mar 4, 2026 — Agent Teams Wave 2: 8/8 pass 70+)
**Priority:** High (P1)
**Duration:** 2-3 weeks
**Risk Level:** Low (stateless services, isolated changes)
**Source:** [TAPPS Quality Baseline](../reports/quality/TAPPS_BASELINE.md)
**Affects:** data-collectors (8 services)

## Context

The data-collectors domain has a **0% quality gate pass rate** — all 8 services fail the standard (70) threshold. This is the worst-performing domain in the project.

| Service | Score | Gap to 70 | Key Issues |
|---------|-------|-----------|------------|
| air-quality-service | 57.3 | 12.7 | 8 lint, CC~11, no tests |
| smart-meter-service | 60.9 | 9.1 | 9 lint (UP017), B104, no tests |
| weather-api | 60.5 | 9.5 | 6 lint (UP017), B104, CC~12 |
| sports-api | 60.5 | 9.5 | B311+B104, CC~15 |
| carbon-intensity-service | 60.5 | 9.5 | B104, CC~11 |
| electricity-pricing-service | 63.8 | 6.2 | 5 lint (UP017), B104, no tests |
| log-aggregator | 63.8 | 6.2 | 7 lint, no tests |
| calendar-service | 67.3 | 2.7 | 6 lint (UP017), B104 |

**Common patterns across all 8:**
1. `datetime.utcnow()` → needs `datetime.now(UTC)` (UP017)
2. `host="0.0.0.0"` in uvicorn — needs B104 suppression
3. Zero or minimal test coverage
4. Moderate cyclomatic complexity (CC 11-15)

**Note:** Epic 16 (lint cleanup) will handle UP017, I001, B104 — this epic focuses on the remaining gaps (tests, complexity, structure).

---

## Stories

### Story 18.1: calendar-service — Close the 2.7-Point Gap

**Priority:** High | **Estimate:** 2h | **Risk:** Low

**Current:** 67.3 (gap: 2.7 to 70)

**Problem:** Nearest to passing. After Epic 16 lint fixes (UP017, B104), likely needs minimal additional work.

**Acceptance Criteria:**
- [ ] After Epic 16 lint fixes, re-score to confirm remaining gap
- [ ] Add type annotations to main route handlers
- [ ] Add 2-3 basic tests (health endpoint, event parsing)
- [ ] Achieve `tapps_quality_gate(preset="standard")` PASS

---

### Story 18.2: electricity-pricing-service — Improve Coverage

**Priority:** High | **Estimate:** 3h | **Risk:** Low

**Current:** 63.8 (gap: 6.2)

**Acceptance Criteria:**
- [ ] Add type annotations to public functions
- [ ] Add 3-5 tests for pricing data fetching and parsing
- [ ] Fix remaining lint issues after Epic 16
- [ ] Achieve `tapps_quality_gate(preset="standard")` PASS

---

### Story 18.3: log-aggregator — Add Tests & Fix Lint

**Priority:** High | **Estimate:** 3h | **Risk:** Low

**Current:** 63.8 (gap: 6.2)

**Acceptance Criteria:**
- [ ] Add 3-5 tests for log aggregation logic
- [ ] Fix `SIM105` — use `contextlib.suppress(asyncio.CancelledError)`
- [ ] Remove unused `request` args (ARG001) or prefix with `_`
- [ ] Achieve `tapps_quality_gate(preset="standard")` PASS

---

### Story 18.4: carbon-intensity-service & weather-api — Reduce Complexity

**Priority:** Medium | **Estimate:** 4h | **Risk:** Low

**Current:** Both at 60.5 (gap: 9.5)

**Problem:** CC~11-12 in main data-fetching functions. After lint fixes, complexity reduction and basic tests needed.

**Acceptance Criteria:**
- [ ] Split high-CC functions in both services (target CC < 10)
- [ ] Add 2-3 tests per service for API fetching and data transformation
- [ ] Add type annotations to public functions
- [ ] Both achieve `tapps_quality_gate(preset="standard")` PASS

---

### Story 18.5: smart-meter-service & air-quality-service — Foundation

**Priority:** Medium | **Estimate:** 5h | **Risk:** Low

**Current:** 60.9 and 57.3 (largest gaps)

**Problem:** Both have zero test coverage and moderate complexity. air-quality-service also uses deprecated `asyncio.TimeoutError`.

**Acceptance Criteria:**
- [ ] Add 3-5 tests per service
- [ ] Fix `asyncio.TimeoutError` → `TimeoutError` in air-quality-service (UP041)
- [ ] Add type annotations to key functions
- [ ] Reduce CC where possible (extract helper functions)
- [ ] Both achieve `tapps_quality_gate(preset="standard")` PASS

---

### Story 18.6: sports-api — Fix Security & Complexity

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

**Current:** 60.5 (gap: 9.5)

**Problem:** CC~15 (highest in domain). B311 (random module used for non-security purpose — needs suppression or replacement). B104.

**Acceptance Criteria:**
- [ ] Replace `random` usage with appropriate alternative, or suppress B311 with justification
- [ ] Split high-CC functions (target CC < 10)
- [ ] Add 2-3 tests for sports data fetching
- [ ] Achieve `tapps_quality_gate(preset="standard")` PASS

---

### Story 18.7: Domain Re-Score & Baseline Update

**Priority:** High | **Estimate:** 1h | **Risk:** Low

**Acceptance Criteria:**
- [ ] Run `tapps_quick_check` on all 8 data-collector services
- [ ] All 8 pass `tapps_quality_gate(preset="standard")`
- [ ] Update `reports/quality/TAPPS_BASELINE.md` with new scores
- [ ] data-collectors pass rate: 0/8 → 8/8

---

## Summary

| Story | Service(s) | Current | Target | Est. |
|-------|-----------|---------|--------|------|
| 18.1 | calendar-service | 67.3 | 70+ | 2h |
| 18.2 | electricity-pricing-service | 63.8 | 70+ | 3h |
| 18.3 | log-aggregator | 63.8 | 70+ | 3h |
| 18.4 | carbon-intensity, weather-api | 60.5 | 70+ | 4h |
| 18.5 | smart-meter, air-quality | 60.9/57.3 | 70+ | 5h |
| 18.6 | sports-api | 60.5 | 70+ | 3h |
| 18.7 | Re-score & baseline update | — | — | 1h |
| **Total** | | | | **~21h** |

## Dependencies

- **Epic 16** (lint cleanup) should complete first — it handles UP017, I001, B104 mechanically
- Stories 18.1-18.6 can be parallelized after Epic 16
- Story 18.7 must be last
