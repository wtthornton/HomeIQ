---
epic: health-dashboard-quality
priority: high
status: open
estimated_duration: 2-3 weeks
risk_level: medium
source: REVIEW_AND_FIXES.md (2026-02-06), REFACTORING_PLAN_32.1, TAPPS expert consultation
---

# Epic: Health Dashboard Quality & Performance

**Status:** Open
**Priority:** High (P1)
**Duration:** 2-3 weeks
**Risk Level:** Medium
**Predecessor:** Epic frontend-security-hardening (Stories 1, 4)
**Affects:** domains/core-platform/health-dashboard

## Context

The health dashboard code review (Feb 6, 2026) scored the app 6/10 overall with
test coverage at 3/10, performance at 5/10, and multiple architectural issues.
Story 32.1 refactoring (AnalyticsPanel/AlertsPanel) stalled at Phase 1 since Oct 2025.
The frontend redesign (Phase 4b) addressed navigation and design but not these
underlying quality issues.

## Stories

### Story 1: Complete Story 32.1 Refactoring (AlertsPanel)

**Priority:** High | **Estimate:** 4h | **Risk:** Low (Phase 1 already done)

**Problem:** AnalyticsPanel refactored (complexity 54→<10) but AlertsPanel (complexity 44)
still monolithic. Refactored files sitting as `.REFACTORED.tsx` not activated.

**Tasks:**
- Phase 2: Activate refactored AnalyticsPanel (rename `.REFACTORED.tsx` → main, archive `.OLD.tsx`)
- Phase 3: Refactor AlertsPanel — extract `alertHelpers.ts`, create `AlertCard`, `AlertFilters`, `AlertStats`, `AlertEmptyState` sub-components
- Phase 4: Run Vitest + Playwright E2E
- Phase 5: Remove all `.OLD.` and `.REFACTORED.` dead files (MED-01: 5 dead files)

**Acceptance Criteria:**
- [ ] AlertsPanel complexity < 15 (from 44)
- [ ] Zero `.OLD.` or `.REFACTORED.` files remain
- [ ] All existing tests pass

---

### Story 2: Implement Lazy Loading & Code Splitting

**Priority:** High | **Estimate:** 6h | **Risk:** Medium

**Problem:** All 16 tabs imported eagerly. Recharts (~400KB), chart.js (~200KB),
lucide-react (~100KB) bundled upfront. Initial load unnecessarily large.

**Files:** `src/components/Dashboard.tsx:1-26`, `vite.config.ts:103-104`

**Acceptance Criteria:**
- [ ] All tab components loaded via `React.lazy()` with `<Suspense>` fallback
- [ ] `manualChunks` in vite.config splits: recharts, chart.js, lucide-react, radix-ui
- [ ] Initial bundle < 300KB gzipped (measure with `npx vite-bundle-visualizer`)
- [ ] Loading skeleton shown during chunk download

---

### Story 3: Fix Polling & Data Fetching Architecture

**Priority:** High | **Estimate:** 8h | **Risk:** Medium

**Problem:** 10+ independent polling intervals (3s–120s), no `visibilitychange` pause,
OverviewTab starts 6-7 simultaneous intervals. Overlapping data fetched by multiple hooks.

**Files:** `EventStreamViewer.tsx`, `ServiceControl.tsx`, `useStatistics.ts`,
`useEnvironmentHealth.ts`, `useHealth.ts`, `useDataSources.ts`

**Acceptance Criteria:**
- [ ] All polling hooks pause when tab is not visible (`document.hidden`)
- [ ] `AbortController` signals passed to all `fetch()` calls and used on unmount
- [ ] `mounted` guard pattern consistent across all hooks
- [ ] Polling intervals configurable and documented
- [ ] OverviewTab shares data via React Context instead of duplicate fetches

---

### Story 4: Consolidate Type Definitions

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

**Problem:** Two conflicting `HealthStatus` definitions (interface vs enum),
two conflicting `Alert` types. 64 instances of `: any` across 27 files.

**Files:** `src/types.ts`, `src/types/health.ts`, `src/types/index.ts`,
`src/constants/alerts.ts`, `src/components/AlertCenter.tsx`

**Acceptance Criteria:**
- [ ] Single canonical `HealthStatus` and `Alert` type definition
- [ ] `: any` reduced by 50%+ (target: < 30 instances)
- [ ] `catch (err: any)` replaced with `catch (err: unknown)` throughout
- [ ] ESLint `@typescript-eslint/no-explicit-any` set to `error`

---

### Story 5: Replace darkMode Prop Drilling with Context

**Priority:** Medium | **Estimate:** 4h | **Risk:** Medium

**Problem:** `darkMode` prop drilled from Dashboard through every tab and sub-component.

**Acceptance Criteria:**
- [ ] `ThemeContext` provider wraps the app
- [ ] `useTheme()` hook replaces prop drilling in all components
- [ ] Zero `darkMode` prop declarations remaining
- [ ] Theme toggle still functional

---

### Story 6: Fix Stale Data & Reactive Bugs

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

**Problem:**
- `useDataFreshness.ts:106-110` — `isStale` uses `Date.now()` inside `useMemo` (not reactive)
- `useHealth.ts` — `AbortController` created but never passed to `fetch()`
- `useStatistics.ts` — `refresh()` defined outside `useEffect` without `mounted` guard

**Acceptance Criteria:**
- [ ] `isStale` recalculated via `useEffect` with interval timer
- [ ] All `AbortController` signals connected to their `fetch()` calls
- [ ] All hooks use consistent `mounted` guard pattern

---

### Story 7: Clean Up Production Code

**Priority:** Low | **Estimate:** 3h | **Risk:** Low

**Problem:**
- 130 `console.log/warn/error` calls across 54 files
- `ChartTest.tsx` debug component in production tree
- `window.confirm()` / `window.alert()` in 22 places
- `<meta robots="index, follow">` on internal dashboard
- `react-use-websocket` installed but unused

**Acceptance Criteria:**
- [ ] Production console statements removed or replaced with structured logger
- [ ] `ChartTest.tsx` removed
- [ ] `window.confirm` replaced with themed dialog component (at least for destructive actions)
- [ ] Meta robots set to `noindex, nofollow`
- [ ] Unused dependencies removed from `package.json`
- [ ] DOM anti-pattern in OverviewTab replaced with `navigateToTab` event

---

### Story 8: Establish Test Coverage Foundation

**Priority:** High | **Estimate:** 2-3 days | **Risk:** Low

**Problem:** 14 test files for 100+ source files. Zero tests for tabs, 17% for hooks,
~6% for components. `Dashboard.test.tsx` references stale text "HA Ingestor Dashboard".

**Acceptance Criteria:**
- [ ] Test setup has global mocks: `fetch`, `localStorage`, `IntersectionObserver`, `matchMedia`
- [ ] Vitest config with coverage thresholds (target: 40% line coverage as baseline)
- [ ] Tests for all 12 custom hooks (unit tests with MSW or manual mocks)
- [ ] Tests for 5 highest-complexity components
- [ ] Stale `Dashboard.test.tsx` assertions updated
- [ ] CI runs `vitest --coverage` and fails below threshold
