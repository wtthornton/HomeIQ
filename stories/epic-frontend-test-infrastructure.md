# Epic 42: Frontend Test Infrastructure & Coverage Baseline

**Sprint:** 10
**Priority:** P0 (Critical Foundation)
**Status:** Open
**Created:** 2026-03-09
**Effort:** 1 week
**Source:** `docs/planning/frontend-testing-epics.md` (Epic 50 mapping)

## Objective

Establish coverage reporting, fix broken/stub tests, and set up missing test infrastructure for all 3 frontend apps. This unblocks all subsequent frontend testing work.

## Stories

### Story 42.1: Coverage Reporting for React Apps
- Configure `vitest --coverage` with Istanbul provider in health-dashboard and ai-automation-ui
- Generate baseline coverage reports for both apps
- Add `npm run test:coverage` script
- Document baseline numbers
- **Effort:** 2 hours
- **Acceptance:** Coverage reports generated, baseline documented

### Story 42.2: Fix Stub Test Files (health-dashboard)
- Implement real tests in `ServiceMetrics.test.tsx` (currently 5 TODOs)
- Implement real tests in `serviceMetricsClient.test.ts` (currently 7 TODOs)
- Follow patterns from `SportsTab.test.tsx` and `LiveGameCard.test.tsx`
- **Effort:** 3 hours
- **Acceptance:** All TODO stubs replaced with passing tests

### Story 42.3: Fix Pre-existing Test Failure (api.test.ts)
- Fix `api.test.ts > fetches the services health endpoint directly` failure
- Root cause: MSW handler URL mismatch or auth issue
- **Effort:** 1 hour
- **Acceptance:** `npm run test:run` exits 0 with no failures

### Story 42.4: pytest Infrastructure for Observability Dashboard
- Add test dependencies: `pytest>=8.0`, `pytest-asyncio>=0.23`, `pytest-mock>=3.12`, `httpx[test]`
- Create `tests/` directory with `conftest.py`
- Create mock fixtures for JaegerClient, Streamlit session state
- **Effort:** 3 hours
- **Acceptance:** `pytest` runs successfully

### Story 42.5: CI Coverage Gating
- Update CI to run `npm run test:run` for both React apps
- Run `pytest` for observability-dashboard
- Add coverage thresholds: warn at <50%, fail at <30%
- **Effort:** 2 hours
- **Acceptance:** CI runs tests on PR, coverage report visible

## Acceptance Criteria
- [ ] Coverage baseline documented for all 3 apps
- [ ] 0 stub/TODO test files
- [ ] 0 pre-existing test failures
- [ ] pytest infrastructure ready for observability-dashboard
- [ ] CI runs all frontend tests
