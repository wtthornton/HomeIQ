# Epic 42: Frontend Test Infrastructure & Coverage Baseline

**Sprint:** 10
**Priority:** P0 (Critical Foundation)
**Status:** Complete
**Created:** 2026-03-09 | **Completed:** 2026-03-10
**Effort:** 1 week
**Source:** `docs/planning/frontend-testing-epics.md` (Epic 50 mapping)

## Objective

Fix all pre-existing test failures, implement stub tests, add missing coverage config, and unblock subsequent frontend testing work.

## Verified Baseline (2026-03-10)

| App | Test Files | Source Files | Tests | Passing | Failing |
|-----|-----------|-------------|-------|---------|---------|
| health-dashboard | 18 | 189 | 169 | 153 | **16 (6 files)** |
| ai-automation-ui | 12 | 116 | 175 | 166 | **9 (1 file)** |
| observability-dashboard | 3+conftest | 14 | 35 | **35** | 0 |

**Notes:**
- health-dashboard already has vitest coverage config (v8 provider, thresholds in vitest.config.ts, `test:coverage` script)
- observability-dashboard already has pytest.ini, conftest.py, and 35 passing tests — only needs pytest added to requirements.txt
- ai-automation-ui has vitest config in vite.config.ts but NO coverage config

## Stories

### Story 42.1: Coverage Config for ai-automation-ui
- Add `@vitest/coverage-v8` dev dependency
- Add coverage config to vite.config.ts (matching health-dashboard pattern)
- Add `test:coverage` script to package.json
- Add pytest to observability-dashboard requirements.txt
- **Effort:** 1 hour
- **Acceptance:** `npm run test:coverage` works in both React apps, `pytest` runnable from requirements

### Story 42.2: Fix Stub Test Files (health-dashboard)
- Implement real tests in `ServiceMetrics.test.tsx` (currently 5 TODOs)
- Implement real tests in `serviceMetricsClient.test.ts` (currently 7 TODOs)
- Follow patterns from `SportsTab.test.tsx` and `LiveGameCard.test.tsx`
- **Effort:** 3 hours
- **Acceptance:** All TODO stubs replaced with passing tests

### Story 42.3: Fix 16 Pre-existing Test Failures (health-dashboard)
- Fix 6 failing test files (16 tests total):
  - `Dashboard.interactions.test.tsx` (4 failures — dark mode toggle, auto-refresh, time range, tab navigation)
  - `api.test.ts` (1 failure — services health endpoint fetch)
  - `useHealth.test.ts` (4 failures — health status, 500 error, network fail, polling)
  - `useStatistics.test.ts` (3 failures — data display, error, period param)
  - `DevicesTab.test.tsx` (3 failures — heading, refresh button, refresh click)
  - `SportsTab.test.tsx` (1 failure — no games state)
- Root cause: likely MSW handler URL mismatches or happy-dom fetch issues
- **Effort:** 4 hours
- **Acceptance:** `npx vitest run` exits 0 with 0 failures

### Story 42.4: Fix 9 Pre-existing Test Failures (ai-automation-ui)
- Fix `AutomationPreview.test.tsx` (9 failures):
  - Initial Render (alias, description), DebugTab, Existing Functionality (validation feedback/errors, create button), Dark Mode, Edge Cases (missing conversationId), Entity Extraction
- Root cause: likely component API changes not reflected in tests
- **Effort:** 2 hours
- **Acceptance:** `npx vitest run` exits 0 with 0 failures

### Story 42.5: CI Coverage Gating
- Update CI to run `npm run test:run` for both React apps
- Run `pytest` for observability-dashboard
- Add coverage thresholds: warn at <50%, fail at <30%
- **Effort:** 2 hours
- **Acceptance:** CI runs tests on PR, coverage report visible

## Acceptance Criteria
- [ ] Coverage config working for all 3 apps
- [ ] 0 stub/TODO test files
- [ ] 0 pre-existing test failures (25 total: 16 HD + 9 AI UI)
- [ ] CI runs all frontend tests
