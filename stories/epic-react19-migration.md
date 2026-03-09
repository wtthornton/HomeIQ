# Epic 39: React 19 Migration

**Priority:** P2 Medium
**Estimated Duration:** 2-3 weeks
**Status:** Open
**Created:** 2026-03-09
**Source:** Sprint 4 gap (Vite 7 + Tailwind 4 done, React stayed at 18)

## Overview

Migrate all three frontend applications from React 18 to React 19. This completes the frontend framework upgrade initiative started in Sprint 4 (Epic 5) which upgraded Vite and Tailwind but deferred React due to breaking changes in the concurrent rendering model.

## Background

React 19 introduces significant changes:
- **React Compiler** (formerly React Forget) — automatic memoization, removing need for manual `useMemo`/`useCallback`
- **Actions** — native form handling with `useActionState` and `useFormStatus`
- **`use()` hook** — read promises and context in render
- **`ref` as prop** — no more `forwardRef` wrapper
- **Document metadata** — native `<title>`, `<meta>`, `<link>` support in components
- **Breaking:** `defaultProps` on function components removed, `propTypes` runtime checking removed

## Current State

| App | Location | React Version | Router | State | Build |
|-----|----------|---------------|--------|-------|-------|
| AI Automation UI | `domains/frontends/ai-automation-ui/` | 18.x | react-router-dom 6 | React Query + Context | Vite 7 |
| Health Dashboard | `domains/frontends/health-dashboard/` | 18.x | react-router-dom 6 | React Query + Context | Vite 7 |
| Observability Dashboard | `domains/frontends/observability-dashboard/` | 18.x | Streamlit | N/A | Streamlit |

**Note:** Observability Dashboard is Streamlit (Python), not React — excluded from this epic.

## Stories

### Story 39.1: Dependency Audit & Compatibility Check
**Priority:** P0 (Prerequisite)
**Estimate:** 1 day

Audit all React dependencies for React 19 compatibility before upgrading.

**Acceptance Criteria:**
- [ ] Run `npm outdated` on both React apps
- [ ] Check react-router-dom 6 compatibility with React 19
- [ ] Check @tanstack/react-query compatibility with React 19
- [ ] Check recharts, react-force-graph, lucide-react compatibility
- [ ] Document any packages needing version bumps or replacements
- [ ] Resolve 6 known npm vulnerabilities (from react-force-graph)
- [ ] Create compatibility matrix in this story

### Story 39.2: AI Automation UI — React 19 Upgrade
**Priority:** P1 High
**Estimate:** 3 days

Upgrade ai-automation-ui to React 19 with all breaking change fixes.

**Acceptance Criteria:**
- [ ] Upgrade react, react-dom to ^19.0.0
- [ ] Upgrade @types/react, @types/react-dom
- [ ] Replace `ReactDOM.createRoot` pattern if changed
- [ ] Remove `forwardRef` wrappers — use `ref` as prop
- [ ] Remove any `defaultProps` on function components
- [ ] Fix any `useEffect` strictness changes
- [ ] Verify all 6 sidebar pages render correctly
- [ ] Verify cross-app switcher works
- [ ] Build passes with zero errors
- [ ] No console warnings related to React 19 deprecations

### Story 39.3: Health Dashboard — React 19 Upgrade
**Priority:** P1 High
**Estimate:** 3 days

Upgrade health-dashboard to React 19 with all breaking change fixes.

**Acceptance Criteria:**
- [ ] Upgrade react, react-dom to ^19.0.0
- [ ] Upgrade @types/react, @types/react-dom
- [ ] Remove `forwardRef` wrappers — use `ref` as prop
- [ ] Remove any `defaultProps` on function components
- [ ] Verify all 5 sidebar sections render correctly
- [ ] Verify MemoryTab, TrustScoreWidget, mobile drawer
- [ ] Build passes with zero errors
- [ ] No console warnings related to React 19 deprecations

### Story 39.4: React Compiler Integration
**Priority:** P2 Medium
**Estimate:** 2 days

Enable the React Compiler (babel plugin) for automatic memoization.

**Acceptance Criteria:**
- [ ] Install `babel-plugin-react-compiler` or `react-compiler-runtime`
- [ ] Configure Vite plugin for React Compiler
- [ ] Remove manual `useMemo` / `useCallback` calls that the compiler handles
- [ ] Verify no performance regressions (Lighthouse score ≥ baseline)
- [ ] Document any components that need `"use no memo"` directive

### Story 39.5: Adopt React 19 Patterns
**Priority:** P2 Medium
**Estimate:** 2 days

Refactor existing code to use React 19 idioms where beneficial.

**Acceptance Criteria:**
- [ ] Convert form handlers to use `useActionState` where applicable
- [ ] Replace `useContext` with `use(Context)` in simple cases
- [ ] Use native `<title>` / `<meta>` instead of react-helmet if present
- [ ] Verify all Playwright E2E tests still pass (160/167 baseline)

### Story 39.6: E2E Validation & Regression Testing
**Priority:** P1 High
**Estimate:** 1 day

Full E2E validation after React 19 migration.

**Acceptance Criteria:**
- [ ] All 3 Playwright E2E spec files pass
- [ ] No visual regressions in critical pages
- [ ] Cross-app navigation works between all 3 apps
- [ ] Mobile responsive layouts verified
- [ ] Performance: no Lighthouse regression > 5 points
- [ ] Bundle size delta documented

## Dependencies

- Vite 7 already configured (Sprint 4)
- Tailwind 4 already configured (Sprint 4)
- react-router-dom must be compatible version
- @tanstack/react-query must be compatible version

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| react-force-graph incompatible | Medium | Medium | Replace or fork if needed |
| React Compiler breaks custom hooks | Low | Medium | Use `"use no memo"` directive |
| E2E tests break from DOM changes | Medium | Low | Update selectors as needed |

## Rollback

Revert package.json and lock files to pre-upgrade state. No backend changes involved.
