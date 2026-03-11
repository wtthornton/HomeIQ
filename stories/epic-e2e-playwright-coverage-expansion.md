# Epic 49: E2E Playwright Coverage Expansion

**Created:** 2026-03-11 | **Priority:** P1 | **Sprint:** 14 (Backlog)
**Status:** OPEN
**Scope:** Expand Playwright E2E coverage across four gap areas — Visual Regression, Ask AI/HA Agent, Error/Loading Depth, AI Automation UI Routes

## Objective

Address identified E2E test gaps so that critical user journeys, visual consistency, error/loading behavior, and all AI Automation UI routes are covered by automated tests. All stories in this epic are scoped to “hit priority” (deliver test or code changes that directly improve coverage in the target area).

## Gap Areas (Summary)

| Area | Current gap | Target |
|------|-------------|--------|
| **Visual regression** | Spec uses wrong/missing `data-testid`s and legacy routes; no baseline discipline | Align selectors with app; add/update baselines; optional CI gate |
| **Ask AI / HA Agent** | Full flow only in root specs; not in Docker CI; no mocked path for CI | Mocked Ask AI E2E in CI; optional full flow in extended run; doc ownership |
| **Error and loading depth** | Many tabs only assert “loads”; few test empty state + API failure + loading→loaded | Per-tab empty, failure, and loading tests for critical tabs |
| **AI Automation UI routes** | Route list in plan doesn’t match specs; Name Enhancement coverage unclear | Route–spec matrix; fill missing route coverage (e.g. name-enhancement) |

---

## 1. Visual Regression

### Story 49.1: Align visual regression selectors with health-dashboard [P1] — TEST FIX

**Problem:** `tests/e2e/visual-regression.spec.ts` uses `[data-testid="dashboard"]`, `health-cards`, `statistics-chart`, `events-feed` which do not exist in the app. App uses `dashboard-root`, `dashboard-header`, `dashboard-content`; no `health-cards` or `statistics-chart` or `events-feed`.

**Files:**
- `tests/e2e/visual-regression.spec.ts`

**AC:**
- [ ] Replace `[data-testid="dashboard"]` with `[data-testid="dashboard-root"]` (or equivalent) for wait and full-page screenshot.
- [ ] Replace `health-cards` with a selector that exists (e.g. `[data-testid="health-card"]` or section containing core system cards).
- [ ] Replace `statistics-chart` and `events-feed` with existing selectors or remove/skip those assertions until components expose testids.
- [ ] All visual regression tests that target health-dashboard run without selector timeouts; screenshots may still need baseline updates in a follow-up.

---

### Story 49.2: Align visual regression routes with tab-based health-dashboard [P1] — TEST FIX

**Problem:** Spec uses `/monitoring` and `/settings` as full-page routes; health-dashboard is tab-based with hash routing (e.g. `/#overview`, `/#configuration`).

**Files:**
- `tests/e2e/visual-regression.spec.ts`

**AC:**
- [ ] “Dashboard screen” test uses base URL and hash for overview (e.g. `/#overview` or `/#services`) where appropriate.
- [ ] “Monitoring screen” test either navigates to `/#services` and waits for services content or is skipped with a comment that monitoring is tab-based.
- [ ] “Settings screen” test either navigates to `/#configuration` and waits for configuration content or is skipped with a comment.
- [ ] No tests assume standalone `/monitoring` or `/settings` pages unless those routes exist in the app.

---

### Story 49.3: Add/update visual regression baselines and reduce flakiness [P2] — TEST FIX

**Problem:** Visual tests use `waitForTimeout(2000)` and may be flaky; baselines may be missing or outdated.

**Files:**
- `tests/e2e/visual-regression.spec.ts`
- Optional: `tests/e2e/visual-regression/` or baseline assets if stored in repo

**AC:**
- [ ] Replace fixed `waitForTimeout(2000)` with waiting for a stable element (e.g. `dashboard-content` visible and no loading spinner) before taking screenshots.
- [ ] Generate or update baseline screenshots for health-dashboard (overview, configuration, services) and document how to update baselines (e.g. `npx playwright test visual-regression --update-snapshots`).
- [ ] Optional: Add a short note in `tests/E2E_TESTING_GUIDE.md` or `tests/README.md` on when to re-run with `--update-snapshots`.

---

### Story 49.4: Optional visual regression CI gate [P2] — CONFIG

**Problem:** Visual regression is not enforced as a blocking CI gate; failures may be ignored.

**Files:**
- `.github/workflows/test.yml` (or equivalent)
- `tests/e2e/docker-deployment.config.ts` or `tests/playwright.config.ts`

**AC:**
- [ ] Document decision: either (a) add a dedicated (optional) job that runs visual regression and fails on diff, or (b) document that visual regression runs locally / on-demand only.
- [ ] If (a): add a job or config that runs `visual-regression.spec.ts` and fails the job on screenshot diff; document baseline update process in CI.
- [ ] If (b): add a line to `tests/README.md` or `tests/E2E_TESTING_GUIDE.md` stating visual regression is not part of default CI.

---

## 2. Ask AI / HA Agent

### Story 49.5: Add mocked Ask AI E2E path for CI [P1] — TEST ADD

**Problem:** Ask AI full flow (`ask-ai-complete.spec.ts`) depends on live OpenAI and is not in `docker-deployment.config.ts`; CI has no Ask AI coverage.

**Files:**
- `tests/e2e/ai-automation-ui/workflows/ask-ai-mocked.spec.ts` (new)
- `tests/e2e/utils/api-mocks.ts` or equivalent (extend if needed)
- `tests/e2e/docker-deployment.config.ts` (optional: include new spec in AI UI project)

**AC:**
- [ ] New spec file that exercises Ask AI page with mocked `/api/v1/ask-ai/*` (or equivalent) responses (e.g. static suggestion payload).
- [ ] Tests cover: page load, input visible, send button, “query submitted” flow that returns mocked suggestions (no real OpenAI call).
- [ ] Tests do not require OpenAI API key or HA; run in &lt; 30s.
- [ ] Spec is included in the AI Automation UI Playwright project so it runs in Docker E2E (or document that it runs in a separate “extended” job).

---

### Story 49.6: Document Ask AI and HA Agent E2E ownership and CI strategy [P1] — DOC

**Problem:** Full Ask AI and HA Agent E2E are outside default Docker run; no single place describes what runs where.

**Files:**
- `tests/E2E_TESTING_GUIDE.md` or `tests/README.md`
- Optional: `tests/e2e/ASK_AI_E2E_TESTS_README.md` (update if exists)

**AC:**
- [ ] Document that Ask AI has two test modes: (1) mocked E2E (CI, fast) and (2) full E2E with live OpenAI (local/optional, long timeout).
- [ ] List which specs run in Docker E2E vs “extended” or local-only (e.g. `ask-ai-complete.spec.ts`, `ask-ai-debug.spec.ts`).
- [ ] Add one sentence on HA Agent Chat E2E location (e.g. `tests/e2e/ai-automation-ui/pages/ha-agent-chat.spec.ts`) and whether it uses mocks or live backend.

---

### Story 49.7: Optional: Include full Ask AI spec in extended Docker E2E job [P2] — CONFIG

**Problem:** Full Ask AI flow is valuable but slow and environment-dependent.

**Files:**
- `tests/e2e/docker-deployment.config.ts` or a separate `tests/e2e/docker-deployment-extended.config.ts`
- `.github/workflows/` (optional: scheduled or manual job)

**AC:**
- [ ] Document decision: either add an “extended” config or job that includes `ask-ai-complete.spec.ts` (and optionally `ask-ai-debug.spec.ts`) with long timeout and required env (e.g. `OPENAI_API_KEY`), or explicitly state “full Ask AI E2E is local-only.”
- [ ] If extended job is added: config uses longer timeout (e.g. 90s per test) and documents env vars; CI job is optional/scheduled or manual so it doesn’t block main PRs.

---

## 3. Error and Loading Depth

### Story 49.8: Add empty-state tests for critical health-dashboard tabs [P1] — TEST ADD

**Problem:** Many tab specs only assert “tab loads and shows content”; empty state (no data) is not explicitly tested.

**Files:**
- `tests/e2e/health-dashboard/pages/tabs/overview.spec.ts`
- `tests/e2e/health-dashboard/pages/tabs/events.spec.ts`
- `tests/e2e/health-dashboard/pages/tabs/devices.spec.ts`
- Optionally: `services.spec.ts`, `alerts.spec.ts`, `data-sources.spec.ts`

**AC:**
- [ ] Overview: one test that, when relevant APIs return empty/minimal data (via route override or existing env), asserts the overview still renders without crash and shows a sensible empty or “no data” state (e.g. message or placeholder).
- [ ] Events: one test for empty event list (mocked or when no events) and assert no hard error.
- [ ] Devices: one test for empty device list and assert no hard error.
- [ ] Tests use route mocking where appropriate to force empty responses; avoid depending on production data.

---

### Story 49.9: Add API-failure tests for critical health-dashboard tabs [P1] — TEST ADD

**Problem:** Few tabs explicitly test behavior when their primary API returns 500 or network error.

**Files:**
- `tests/e2e/health-dashboard/pages/tabs/overview.spec.ts`
- `tests/e2e/health-dashboard/pages/tabs/events.spec.ts`
- `tests/e2e/health-dashboard/pages/tabs/devices.spec.ts`
- Optionally: `services.spec.ts`, `configuration.spec.ts`

**AC:**
- [ ] For each of overview, events, devices: one test that mocks the primary API to return 500 (or network error) and asserts the tab shows an error state or retry option (e.g. `[data-testid="error-state"]` or retry button) and does not leave the page broken or blank.
- [ ] Tests do not require real backend failure; use `page.route()` to force failure.

---

### Story 49.10: Add loading→loaded transition tests for critical tabs [P2] — TEST ADD

**Problem:** Loading spinners and transition to content are not consistently asserted.

**Files:**
- `tests/e2e/health-dashboard/pages/tabs/overview.spec.ts`
- `tests/e2e/health-dashboard/pages/tabs/services.spec.ts`
- `tests/e2e/health-dashboard/pages/tabs/devices.spec.ts`

**AC:**
- [ ] For at least two of the above tabs: one test that (optionally with a slow/mocked API) verifies a loading indicator appears (e.g. `[data-testid="loading-spinner"]` or skeleton) and then content or empty state appears after load.
- [ ] Tests are stable (use wait for element visibility, not fixed timeouts where possible).

---

### Story 49.11: Add error/loading depth for AI Automation UI critical pages [P2] — TEST ADD

**Problem:** AI Automation UI pages (dashboard, patterns, deployed, settings) may not have explicit empty-state or API-failure E2E tests.

**Files:**
- `tests/e2e/ai-automation-ui/pages/dashboard.spec.ts`
- `tests/e2e/ai-automation-ui/pages/patterns.spec.ts`
- `tests/e2e/ai-automation-ui/pages/deployed.spec.ts`
- `tests/e2e/ai-automation-ui/pages/settings.spec.ts`

**AC:**
- [ ] Dashboard: one test for empty suggestions (mocked empty response) and one for API error (e.g. 500) showing error/retry or graceful message.
- [ ] At least one of patterns / deployed / settings has an empty-state or error-state test (mocked).
- [ ] No new tests depend on live backend data for pass/fail.

---

## 4. AI Automation UI — Routes vs Tests

### Story 49.12: Create AI Automation UI route–spec matrix and fix gaps [P1] — DOC + TEST

**Problem:** Implementation plan lists routes (e.g. /ask-ai, /ha-agent, /name-enhancement) but it’s unclear which E2E spec covers which route; name-enhancement may be uncovered.

**Files:**
- `docs/planning/ai-automation-ui-routes-e2e-matrix.md` (new) or section in existing planning doc
- `tests/e2e/ai-automation-ui/pages/enhancement-button.spec.ts` or new `name-enhancement.spec.ts` if needed

**AC:**
- [ ] Document a route–spec matrix: route/path (e.g. `/`, `/patterns`, `/deployed`, `/ask-ai`, `/ha-agent`, `/settings`, `/discovery`, `/synergies`, `/proactive`, `/blueprint-suggestions`, `/admin`, `/name-enhancement`) and the corresponding E2E spec file(s).
- [ ] Identify any route with no E2E coverage; add at least one test (navigate to route, assert main content or title) for that route.
- [ ] If name-enhancement is a distinct route: add or extend a spec so the route is covered (e.g. enhancement-button or dedicated name-enhancement spec).

---

### Story 49.13: Align implementation plan and TEST_COVERAGE with actual tabs/routes [P2] — DOC

**Problem:** PLAYWRIGHT_FULL_UI_COVERAGE_IMPLEMENTATION_PLAN.md and TEST_COVERAGE.md reference “Setup” tab and “synergies” (health-dashboard); actual app has groups, evaluation, memory. AI UI route list may be outdated.

**Files:**
- `implementation/PLAYWRIGHT_FULL_UI_COVERAGE_IMPLEMENTATION_PLAN.md`
- `tests/TEST_COVERAGE.md`

**AC:**
- [ ] Health-dashboard: remove or correct “Setup” tab reference; add groups, evaluation, memory to tab list where applicable; fix “15/15” or “100%” claims to match actual tab count and coverage.
- [ ] AI Automation UI: update route/page table to match current routes and spec files (from Story 49.12).
- [ ] No false “100%” or “all routes covered” without a corresponding route–spec matrix or list.

---

## Priority Summary (All Hit)

| Story | Area | Priority | Type |
|-------|------|----------|------|
| 49.1 | Visual regression | P1 | TEST FIX |
| 49.2 | Visual regression | P1 | TEST FIX |
| 49.3 | Visual regression | P2 | TEST FIX |
| 49.4 | Visual regression | P2 | CONFIG |
| 49.5 | Ask AI / HA Agent | P1 | TEST ADD |
| 49.6 | Ask AI / HA Agent | P1 | DOC |
| 49.7 | Ask AI / HA Agent | P2 | CONFIG |
| 49.8 | Error/loading depth | P1 | TEST ADD |
| 49.9 | Error/loading depth | P1 | TEST ADD |
| 49.10 | Error/loading depth | P2 | TEST ADD |
| 49.11 | Error/loading depth | P2 | TEST ADD |
| 49.12 | AI UI routes | P1 | DOC + TEST |
| 49.13 | AI UI routes | P2 | DOC |

## Dependencies

- Existing Playwright setup and `docker-deployment.config.ts` (no new tools required).
- For Story 49.5: existing API mock patterns in `tests/e2e/utils/api-mocks.ts` or shared helpers.
- For Story 49.12: access to ai-automation-ui route list (e.g. router or app entry).

## Success Criteria (Epic)

- [ ] Visual regression spec runs against current health-dashboard without selector failures; routes and selectors documented or updated.
- [ ] Ask AI has a mocked E2E path runnable in CI; ownership and CI strategy documented.
- [ ] At least three critical health-dashboard tabs have explicit empty-state and API-failure tests; at least two have loading→loaded tests.
- [ ] AI Automation UI has a route–spec matrix; every listed route has at least one E2E test; implementation plan and TEST_COVERAGE are aligned with actual app.

## References

- Playwright test gaps analysis (source for this epic)
- `tests/E2E_TESTING_GUIDE.md`
- `tests/TEST_COVERAGE.md`
- `implementation/PLAYWRIGHT_FULL_UI_COVERAGE_IMPLEMENTATION_PLAN.md`
- `implementation/PLAYWRIGHT_E2E_ISSUES_LIST.md`
