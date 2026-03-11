# Epic 49: E2E Playwright Coverage Expansion — Execution Summary

**Completed:** 2026-03-11  
**Epic:** [stories/epic-e2e-playwright-coverage-expansion.md](../stories/epic-e2e-playwright-coverage-expansion.md)

## Summary

All 13 stories were addressed: visual regression fixes, Ask AI mocked CI path and docs, error/loading depth for health-dashboard and AI UI, and route–spec matrix with doc alignment.

## Delivered

### 1. Visual regression (49.1–49.4)

- **49.1–49.2:** `tests/e2e/visual-regression.spec.ts` — Replaced `[data-testid="dashboard"]` with `[data-testid="dashboard-root"]`; replaced `health-cards` / `statistics-chart` / `events-feed` with existing selectors or conditional screenshots; aligned routes to hash-based tabs (`/#overview`, `/#services`, `/#configuration`); removed reliance on `/monitoring` and `/settings`.
- **49.3:** Replaced fixed `waitForTimeout(2000)` with `waitForDashboardStable()` (wait for `dashboard-root` + `dashboard-content` + loading complete); added baseline-update note to `tests/E2E_TESTING_GUIDE.md`.
- **49.4:** Documented that visual regression is **not** part of default CI; run locally/on-demand. Updated `tests/README.md` and `tests/E2E_TESTING_GUIDE.md`.

### 2. Ask AI / HA Agent (49.5–49.6)

- **49.5:** Added `tests/e2e/ai-automation-ui/workflows/ask-ai-mocked.spec.ts` — Mocks `**/v1/ask-ai/query` and `**/v1/ask-ai/query/*/suggestions`; runs in Docker E2E without OpenAI or HA; &lt; 30s.
- **49.6:** Documented two modes in `tests/e2e/ASK_AI_E2E_TESTS_README.md` and `tests/E2E_TESTING_GUIDE.md`: (1) mocked E2E for CI, (2) full E2E local-only; HA Agent Chat spec location noted.

### 3. Error and loading depth (49.8–49.11)

- **49.8:** Empty-state tests: overview (empty health/stats), events (empty events list), devices (empty devices list) — all use `page.route()` to force empty responses; assert no crash and sensible empty/waiting state.
- **49.9:** API-failure tests: overview, events, devices — mock primary API to 500; assert error state or retry button visible.
- **49.10:** Loading→loaded: overview and services — delayed route then resolve; assert dashboard content visible.
- **49.11:** AI UI: dashboard empty + API 500 tests in `dashboard.spec.ts`; settings API 500 test in `settings.spec.ts`.

### 4. AI Automation UI routes (49.12–49.13)

- **49.12:** Created `docs/planning/ai-automation-ui-routes-e2e-matrix.md` (route → spec matrix). Added `tests/e2e/ai-automation-ui/pages/name-enhancement.spec.ts` for `/name-enhancement`.
- **49.13:** Updated `implementation/PLAYWRIGHT_FULL_UI_COVERAGE_IMPLEMENTATION_PLAN.md`: health-dashboard tabs 16→17, removed Setup, added groups, evaluation, memory; AI UI pages table aligned with route matrix. Updated `tests/TEST_COVERAGE.md`: 15/15→17 tabs, removed Setup, added Groups, Evaluation, Memory; AI UI section references route matrix.

## Optional (not implemented)

- **49.7:** Full Ask AI in extended Docker E2E job — documented as “full Ask AI E2E is local-only” (no extended job added).

## Files touched

- `tests/e2e/visual-regression.spec.ts` — rewritten (selectors, routes, waits, auth).
- `tests/e2e/ai-automation-ui/workflows/ask-ai-mocked.spec.ts` — new.
- `tests/e2e/ai-automation-ui/pages/name-enhancement.spec.ts` — new.
- `tests/e2e/ASK_AI_E2E_TESTS_README.md`, `tests/E2E_TESTING_GUIDE.md`, `tests/README.md` — docs.
- `tests/e2e/health-dashboard/pages/tabs/overview.spec.ts` — empty, API failure, loading tests.
- `tests/e2e/health-dashboard/pages/tabs/events.spec.ts` — empty, API failure tests.
- `tests/e2e/health-dashboard/pages/tabs/devices.spec.ts` — empty, API failure tests.
- `tests/e2e/health-dashboard/pages/tabs/services.spec.ts` — loading→loaded test.
- `tests/e2e/ai-automation-ui/pages/dashboard.spec.ts` — empty + error tests.
- `tests/e2e/ai-automation-ui/pages/settings.spec.ts` — error test.
- `docs/planning/ai-automation-ui-routes-e2e-matrix.md` — new.
- `implementation/PLAYWRIGHT_FULL_UI_COVERAGE_IMPLEMENTATION_PLAN.md`, `tests/TEST_COVERAGE.md` — alignment.

## How to run

- **Visual regression (local):**  
  `npx playwright test tests/e2e/visual-regression.spec.ts --config=tests/e2e/docker-deployment.config.ts`  
  Update baselines: `--update-snapshots`
- **Ask AI mocked (CI):**  
  Included in `docker-deployment.config.ts` via `**/ai-automation-ui/**/*.spec.ts` (runs with AI UI project).
- **Health-dashboard / AI UI specs:**  
  Use existing Docker E2E or app-specific Playwright configs as documented in `tests/README.md`.

## Success criteria (epic)

- [x] Visual regression spec runs against current health-dashboard without selector failures; routes and selectors documented or updated.
- [x] Ask AI has a mocked E2E path runnable in CI; ownership and CI strategy documented.
- [x] At least three critical health-dashboard tabs have explicit empty-state and API-failure tests; at least two have loading→loaded tests.
- [x] AI Automation UI has a route–spec matrix; every listed route has at least one E2E test; implementation plan and TEST_COVERAGE aligned with actual app.
