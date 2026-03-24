---
epic: project-wide-lint-cleanup
priority: high
status: complete
estimated_duration: 1-2 weeks
risk_level: low
source: reports/quality/TAPPS_BASELINE.md
type: quality
---

# Epic 16: Project-Wide Lint & Security Cleanup

**Status:** Complete (Mar 4, 2026 — Agent Teams Wave 1)
**Priority:** High (P1)
**Duration:** 1-2 weeks
**Risk Level:** Low
**Source:** [TAPPS Quality Baseline](../reports/quality/TAPPS_BASELINE.md)
**Affects:** All 9 domain groups (all Compose services — see docs/architecture/service-groups.md)

## Context

The TAPPS baseline (March 2026) revealed systemic lint and security issues across nearly every service. These are **mechanical fixes** with no behavioral changes — the highest-ROI path to raising project-wide scores from 69.4 mean toward 75+.

**Key issues (by frequency):**
- **UP017** (`datetime.UTC`): 30+ services use deprecated `datetime.utcnow()` — should use `datetime.now(UTC)`
- **I001** (import sorting): 20+ services have unsorted imports
- **B104** (bind `0.0.0.0`): 30+ services — expected for Docker containers, needs `# noqa: S104` suppression
- **UP041** (`TimeoutError`): 6+ services use deprecated `asyncio.TimeoutError`
- **F401** (unused imports): 5+ services
- **ARG001/ARG002** (unused args): 10+ services

**Impact:** Fixing these across all services will boost scores by 2-5 points each, potentially moving 10-15 services from FAIL to PASS.

---

## Stories

### Story 16.1: Fix UP017 — datetime.UTC Modernization

**Priority:** High | **Estimate:** 4h | **Risk:** Low

**Scope:** All Python files using `datetime.utcnow()` or `timezone.utc` instead of `datetime.UTC`.

**Problem:** Python 3.12+ deprecates `datetime.utcnow()`. Ruff UP017 flags every occurrence. The data-collectors domain (0/8 pass) has the highest density.

**Acceptance Criteria:**
- [ ] Replace `datetime.utcnow()` with `datetime.now(datetime.UTC)` across all services
- [ ] Replace `timezone.utc` with `datetime.UTC` where flagged
- [ ] Run `tapps_quick_check` on changed files — confirm lint count drops
- [ ] Verify no behavioral changes (UTC is UTC)

**Files (highest density):**
- `domains/data-collectors/` — all 8 services
- `domains/device-management/ha-setup-service/src/main.py` (9 occurrences)
- `domains/device-management/activity-writer/src/main.py`
- `domains/energy-analytics/energy-correlator/src/main.py`
- `domains/blueprints/automation-miner/src/cli.py`

---

### Story 16.2: Fix I001 — Import Sorting

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

**Scope:** All Python files with unsorted import blocks.

**Problem:** Ruff I001 flags unsorted imports. `ruff check --fix` can auto-fix these.

**Acceptance Criteria:**
- [ ] Run `ruff check --select I001 --fix` across all service `src/` directories
- [ ] Verify no functional changes (import ordering is cosmetic)
- [ ] Run `tapps_quick_check` on changed files

---

### Story 16.3: Suppress B104 — Docker Bind-All

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

**Scope:** All `uvicorn.run(host="0.0.0.0", ...)` calls.

**Problem:** Bandit B104 flags binding to all interfaces as a security risk. In Docker containers, this is intentional and expected. Suppression removes 30+ false-positive security findings.

**Acceptance Criteria:**
- [ ] Add `# noqa: S104` or `# nosec B104` to intentional `0.0.0.0` bind lines in all services
- [ ] Do NOT suppress any non-Docker bind-all (review each occurrence)
- [ ] Run `tapps_quick_check` — security issue count drops to 0 for suppressed files
- [ ] Document suppression pattern in `AGENTS.md` or `docs/TAPPS_TOOL_PRIORITY.md`

---

### Story 16.4: Fix UP041 — TimeoutError Alias

**Priority:** Low | **Estimate:** 1h | **Risk:** Low

**Scope:** Files using `asyncio.TimeoutError` instead of builtin `TimeoutError`.

**Problem:** Python 3.11+ makes `asyncio.TimeoutError` an alias for builtin `TimeoutError`. Ruff UP041 flags the unnecessary alias.

**Acceptance Criteria:**
- [ ] Replace `asyncio.TimeoutError` with `TimeoutError` in all flagged files
- [ ] Remove unused `asyncio` import if `TimeoutError` was the only usage
- [ ] Run `tapps_quick_check` on changed files

**Known files:**
- `domains/ml-engine/openvino-service/src/main.py` (3 occurrences)
- `domains/ml-engine/ml-service/src/main.py`
- `domains/data-collectors/air-quality-service/src/main.py` (2 occurrences)
- `domains/energy-analytics/energy-forecasting/src/main.py`
- `domains/device-management/activity-writer/src/main.py`

---

### Story 16.5: Fix F401 — Unused Imports

**Priority:** Medium | **Estimate:** 1h | **Risk:** Low

**Scope:** Files with unused imports flagged by ruff F401.

**Problem:** Unused imports bloat code and confuse dependency analysis.

**Acceptance Criteria:**
- [ ] Remove all unused imports flagged by ruff F401
- [ ] Verify no downstream breakage (some `__init__.py` re-exports are intentional)
- [ ] Run `tapps_quick_check` on changed files

**Known files:**
- `domains/core-platform/websocket-ingestion/src/main.py` — `logging` imported but unused
- `domains/automation-core/ha-ai-agent-service/src/main.py` — `contextlib.suppress`, `pathlib.Path`
- `domains/pattern-analysis/api-automation-edge/src/main.py` — `huey_config.huey`

---

### Story 16.6: Fix ARG001/ARG002 — Unused Function Arguments

**Priority:** Low | **Estimate:** 2h | **Risk:** Low

**Scope:** Files with unused function/method arguments.

**Problem:** Unused arguments indicate dead code or incomplete implementations. Some are legitimate (framework callbacks like `app` in lifespan handlers).

**Acceptance Criteria:**
- [ ] For framework-required args (e.g. `app` in FastAPI lifespan): prefix with `_` (e.g. `_app`)
- [ ] For genuinely unused args: remove if safe, or prefix with `_`
- [ ] Run `tapps_quick_check` on changed files

---

### Story 16.7: Re-score All Services and Update Baseline

**Priority:** High | **Estimate:** 2h | **Risk:** Low

**Scope:** Full project re-scan after Stories 16.1-16.6.

**Acceptance Criteria:**
- [ ] Run `tapps_quick_check` on all 53 Python service entry points
- [ ] Update `reports/quality/TAPPS_BASELINE.md` with new scores
- [ ] Update rollup summary with new pass/fail counts
- [ ] Document score delta (before/after) in baseline notes

---

## Summary

| Story | Scope | Est. | Ruff Rule |
|-------|-------|------|-----------|
| 16.1 | datetime.UTC modernization | 4h | UP017 |
| 16.2 | Import sorting | 2h | I001 |
| 16.3 | Docker bind-all suppression | 2h | B104/S104 |
| 16.4 | TimeoutError alias | 1h | UP041 |
| 16.5 | Unused imports | 1h | F401 |
| 16.6 | Unused arguments | 2h | ARG001/ARG002 |
| 16.7 | Re-score and update baseline | 2h | — |
| **Total** | | **~14h** | |

## Dependencies

- **None** — this epic is independent and can start immediately
- Stories 16.1-16.6 can be parallelized
- Story 16.7 must be last

## Impact Estimate

- Current pass rate: **24/53 (45%)**
- Expected pass rate after cleanup: **~35/53 (66%)**
- Current mean: **69.4** → Expected: **~73-75**
