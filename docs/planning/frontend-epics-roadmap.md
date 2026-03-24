# Frontend Technology Stack Improvement Epics

**Created:** 2026-02-27
**Based on research:** `docs/research/2026-frontend-tech-stack-research.md`
**Status:** Ready for epic creation in project management system

---

## Summary Table

| Epic | Priority | Effort | Impact | Start | Dependencies |
|------|----------|--------|--------|-------|--------------|
| Frontend Security Hardening | P1 | 2-4 hrs | Critical | Sprint 2 | None |
| Streamlit Performance | P1 | 1 week | High | Sprint 2 | Streamlit 1.37+ |
| Bundle Optimization | P1 | 2-3 weeks | Medium | Sprint 2 | vite-plugin-visualizer |
| React 19 & Vite 7 Upgrade | P2 | 3-4 weeks | Medium | Sprint 3 | None (after P1 complete) |
| Frontend Testing Framework | P2 | 3 weeks | High | Sprint 3 | React 19 + Vite 7 done |
| Tailwind CSS 4 Migration | P3 | 1-2 weeks | Low | Backlog | None |

---

## Epic 1: Frontend Security Hardening

**Priority:** P1 (Critical)
**Effort:** 2-4 hours
**Impact:** Critical (prevent API key leaks, XSS attacks)
**Timeline:** Sprint 2 (1 week)

### Objective
Audit frontend apps for exposed credentials, implement secure API communication patterns, and prevent future key leaks via CI/CD checks.

### Stories

**Story 1.1: Audit API Key Usage**
- Grep for `VITE_.*KEY` in both ai-automation-ui and health-dashboard
- Audit .env and .env.local files
- Check for secrets in source code (git history if needed)
- Document findings in security audit report
- Effort: 1 hour
- Acceptance: Audit report with all findings documented

**Story 1.2: Implement Secure API Communication Pattern**
- Review current API client implementations
- Ensure credentials are passed via HttpOnly cookies, not env vars
- If direct API key needed, implement backend gateway pattern
- Document authentication flow for team
- Update API client examples in docs
- Effort: 1-2 hours
- Acceptance: API communication passes security review

**Story 1.3: Add Pre-commit Security Checks**
- Add git hook to grep for exposed `VITE_.*KEY` patterns
- Fail commit if secrets detected
- Document in CONTRIBUTING.md
- Verify .gitignore includes .env.local
- Effort: 1 hour
- Acceptance: Pre-commit hook prevents future commits with exposed keys

**Story 1.4: Document Security Guidelines**
- Add security section to frontend README
- Document API authentication patterns
- Add OWASP top 10 checklist for frontends
- Link to security best practices
- Effort: 1 hour
- Acceptance: Documentation published and reviewed

### Definition of Done
- Security audit complete with zero exposed secrets
- API communication pattern implemented (gateway or secure cookie)
- Pre-commit hooks active
- Documentation published
- Team trained on new pattern

---

## Epic 2: Streamlit Performance Optimization

**Priority:** P1 (High)
**Effort:** 1 week
**Impact:** High (removes blocking UI, improves responsiveness)
**Timeline:** Sprint 2 (1-2 weeks)
**Dependencies:** Streamlit 1.37+ (upgrade required)

### Objective
Replace `time.sleep()` blocking calls with Streamlit 1.37's `@st.fragment` decorator to enable partial page reruns and responsive real-time dashboards.

### Current Problem
- observability-dashboard likely uses `time.sleep()` in polling loops
- Full-page reruns block UI during sleep periods
- Users experience frozen dashboard

### Stories

**Story 2.1: Audit Streamlit for `time.sleep()` Usage**
- Grep for `time.sleep()` in observability-dashboard `src/dashboard_pages/*.py`
- Identify blocking calls and their purpose (refresh interval? data polling?)
- Document each usage with context and required refresh rate
- Effort: 1 hour
- Acceptance: Audit report with all blocking calls documented

**Story 2.2: Upgrade Streamlit to 1.37+**
- Update `observability-dashboard/requirements.txt`: streamlit>=1.37.0
- Test startup: `streamlit run src/main.py`
- Verify all pages load without errors
- Effort: 2 hours (including testing)
- Acceptance: Streamlit runs without compatibility issues

**Story 2.3: Refactor Real-Time Monitoring Page**
- Wrap live metric updates in `@st.fragment(run_every=5)` or `run_every=10`
- Remove `time.sleep()` from refresh loop
- Test dashboard responsiveness
- Verify metrics update smoothly
- Effort: 2 hours
- Acceptance: Metrics update without blocking, demo shows smooth UX

**Story 2.4: Refactor Service Performance Page**
- Wrap metric panels in `@st.fragment(run_every=10)` for Jaeger/InfluxDB data
- Remove blocking calls
- Test performance metric updates
- Effort: 2 hours
- Acceptance: Performance data updates smoothly, no UI freezing

**Story 2.5: Add Caching for Expensive Queries**
- Add `@st.cache_data(ttl=60)` to expensive Jaeger/InfluxDB queries
- Reduce refresh rate if queries are costly (e.g., run_every=15 instead of 5)
- Measure InfluxDB query latency
- Effort: 2 hours
- Acceptance: Dashboard remains responsive even with high query cost

**Story 2.6: Performance Testing & Documentation**
- Load test dashboard with rapid interactions
- Measure response time vs. baseline
- Document `@st.fragment` pattern for future pages
- Update developer guide on best practices
- Effort: 2 hours
- Acceptance: Performance test passes, documentation complete

### Definition of Done
- All `time.sleep()` calls removed from observability-dashboard
- `@st.fragment` implemented in all real-time pages
- Dashboard responsive (no more frozen UI)
- Caching implemented for expensive operations
- Documentation updated

---

## Epic 3: Bundle Optimization & Analysis

**Priority:** P1 (Medium)
**Effort:** 2-3 weeks
**Impact:** Medium (faster initial load, better Lighthouse scores)
**Timeline:** Sprint 2-3
**Dependencies:** None (measurement-first approach)

### Objective
Establish bundle size baseline, implement advanced code splitting and lazy loading, and optimize dependencies to reduce initial load time and improve Lighthouse Performance score.

### Current State
- ai-automation-ui: ~150-180 KB gzipped (estimated)
- health-dashboard: ~120-150 KB gzipped (estimated)
- Build time: ~2-3 minutes
- No formal metrics tracked

### Stories

**Story 3.1: Establish Bundle Size Baseline**
- Install vite-plugin-visualizer in both apps
- Generate bundle reports: `npm run build && open dist/stats.html`
- Document baseline metrics:
  - Total bundle size (gzipped + uncompressed)
  - Vendor bundle size
  - Build time
  - Lighthouse Performance score
- Create dashboard to track over time (spreadsheet or script)
- Effort: 2 hours
- Acceptance: Baseline metrics documented with evidence (screenshots)

**Story 3.2: Implement Advanced Code Splitting**
- Review vite.config.ts rollupOptions
- Define manual chunks: `vendor`, `ui-lib`, `pages`
- Separate react + react-dom into vendor chunk
- Lazy-load page components with React.lazy() + Suspense
- Test route navigation to verify chunks load on demand
- Effort: 3 hours
- Acceptance: Chunks visible in stats.html, route nav loads chunks dynamically

**Story 3.3: Dependency Audit & Consolidation**
- Run `npm ls --depth=0` in both apps
- Identify duplicate/similar libraries (e.g., multiple charting libs)
- Evaluate consolidation opportunities
- Check for unused dependencies
- Document findings with recommendations
- Effort: 3 hours
- Acceptance: Audit report with consolidation recommendations

**Story 3.4: Implement Suspense Boundaries**
- Add `<Suspense>` boundaries around lazy components
- Create shared loading UI component
- Test fallback UI appears during chunk load
- Effort: 2 hours
- Acceptance: Loading state visible while chunks load

**Story 3.5: Measure & Compare Metrics**
- Run npm run build and collect new metrics
- Compare to baseline: bundle size, build time, LCP
- Generate before/after report
- Update Lighthouse score (target: 85+)
- Effort: 2 hours
- Acceptance: Metrics comparison complete, improvements documented

**Story 3.6: Document & Maintain**
- Add bundle metrics to README (link to stats.html)
- Create CI check to alert on bundle size growth (warn >10%, fail >20%)
- Document code splitting strategy for future developers
- Effort: 2 hours
- Acceptance: Documentation complete, CI check in place

### Definition of Done
- Bundle baseline established and documented
- Advanced code splitting implemented
- Dependency audit complete with recommendations
- Suspense boundaries added for good UX
- Metrics improved or documented (not regressed)
- CI/CD updated to monitor bundle size

---

## Epic 4: React 19 & Vite 7 Upgrade

**Priority:** P2 (Medium)
**Effort:** 3-4 weeks
**Impact:** Medium (tech debt reduction, preparation for future features)
**Timeline:** Sprint 3-4
**Dependencies:** Epic 3 (bundle optimization baseline)

### Objective
Upgrade React from 18 to 19 and Vite from 6 to 7 in both frontend applications, addressing breaking changes and validating compatibility across all components and tests.

### Scope
- **ai-automation-ui** (port 3001)
- **health-dashboard** (port 3000)

### Stories

**Story 4.1: React 19 Migration - ai-automation-ui**
- Update package.json: react ^18.3.1 → ^19.0.0, @types/react ^18.3.27 → ^19.0.0
- Run npm install and type-check: `tsc --noEmit`
- Fix any type errors (React.FC deprecated, form hooks changes)
- Audit form components (IdeaCard, etc.) for useFormStatus changes
- Run unit tests: `npm run test:run`
- Run E2E smoke tests: `npm run test:e2e:smoke`
- Manual testing of critical user flows (create suggestion, manage ideas)
- Effort: 1 week
- Acceptance: All tests pass, no console errors, manual flows work

**Story 4.2: React 19 Migration - health-dashboard**
- Update package.json: react ^18.3.1 → ^19.0.0, @types/react ^18.3.5 → ^19.0.0
- Run npm install and type-check
- Fix type errors and form hooks
- Audit context usage (GroupsTab, Dashboard)
- Run unit tests and E2E smoke tests
- Manual testing of dashboard flows
- Effort: 1 week
- Acceptance: All tests pass, no errors, dashboard responsive

**Story 4.3: Vite 7 Migration - Environment Variables & Config**
- Audit .env files in both apps for all VITE_* variables
- Ensure all variables are declared (not dynamically added)
- Update vite.config.ts in both apps: vite ^6.4.1 → ^7.0.0
- Verify postcss.config.js has autoprefixer plugin
- Test dev server: `npm run dev` in both apps
- Effort: 1 week
- Acceptance: Dev server runs without errors, all env vars defined

**Story 4.4: Vite 7 Build & Test**
- Run npm run build in both apps
- Verify no build errors or warnings
- Compare bundle sizes to baseline (Epic 3)
- Run unit tests and E2E smoke tests in both apps
- Document any bundle size changes
- Effort: 3 days
- Acceptance: Builds succeed, no regressions in tests or bundle size

**Story 4.5: Modernize React Usage (Optional Enhancement)**
- Replace old React.FC patterns with modern function components
- Adopt new use() hook for promise unwrapping where applicable
- Remove unnecessary useCallback/useMemo where use() simplifies logic
- Update ESLint rules (disable React.FC rules)
- Effort: 2 days
- Acceptance: Codebase uses modern React 19 patterns, ESLint clean

### Definition of Done
- React 19 running in both apps
- Vite 7 running in both apps
- All tests passing (unit + E2E)
- No console errors
- Bundle size not regressed
- Documentation updated with new versions

---

## Epic 5: Frontend Testing Framework

**Priority:** P2 (High)
**Effort:** 3 weeks
**Impact:** High (quality assurance, regression prevention, developer confidence)
**Timeline:** Sprint 4-5 (after React 19 + Vite 7)
**Dependencies:** React 19 & Vite 7 migration complete

### Objective
Implement a comprehensive 3-tier testing pyramid (unit, integration, E2E) with 75% coverage target, enabling confident refactoring and rapid regression detection.

### Current State
- Unit tests: Vitest partially in place, coverage unknown
- Integration tests: Missing
- E2E tests: Playwright in place, smoke tests limited
- Target coverage: 75% overall

### Stories

**Story 5.1: Set Up Coverage Reporting**
- Configure Vitest coverage in both apps: `vitest --coverage`
- Generate baseline coverage reports
- Document coverage goals per file type (utilities 85%, components 70%, critical 90%)
- Add coverage to CI/CD pipeline (warn if <75%, fail if <60%)
- Effort: 2 hours
- Acceptance: Coverage reports generated, baseline documented

**Story 5.2: Unit Tests - ai-automation-ui Critical Paths**
- Target 70% coverage of critical path components
- Focus on: IdeaCard, IdeaList, Sidebar, Ideas page
- Write tests for user interactions (click, type, submit)
- Use screen.getByRole(), not implementation details
- Effort: 1 week
- Acceptance: 70% coverage in critical path, tests follow RTL best practices

**Story 5.3: Unit Tests - health-dashboard Critical Paths**
- Target 70% coverage of critical path components
- Focus on: Dashboard, GroupsTab, ServiceTab, metric updates
- Test data flow and state changes
- Effort: 1 week
- Acceptance: 70% coverage, all tests passing

**Story 5.4: Integration Tests - API Flows**
- Set up MSW (Mock Service Worker) for API mocking
- Write 5-10 integration tests per app
- Test component + API interaction (create suggestion, fetch metrics)
- Test error scenarios (400, 500, timeout)
- Effort: 1 week
- Acceptance: Integration tests pass, MSW working for all API calls

**Story 5.5: E2E Test Expansion - Smoke Tests**
- Expand smoke test suite (currently ~3 tests per app)
- Add @smoke tags to critical user journeys
- Test navigation, main interactions, error handling
- Target: 10-15 smoke tests per app
- Effort: 3 days
- Acceptance: Smoke tests pass on every PR

**Story 5.6: E2E Test Expansion - Full Tests**
- Add @full tags for comprehensive end-to-end workflows
- Test complete user journeys: create → configure → deploy
- Test cross-browser (Chromium, Firefox)
- Test mobile viewports
- Effort: 1 week
- Acceptance: Full test suite passes nightly, cross-browser working

**Story 5.7: CI/CD Integration**
- Update CI/CD to run `npm run test:run` (unit + integration)
- Run `npm run test:e2e:smoke` before merge
- Schedule nightly `npm run test:e2e` (full)
- Add coverage reports to PR comments
- Effort: 1 day
- Acceptance: CI/CD running tests automatically, reports visible

**Story 5.8: Testing Documentation & Standards**
- Create testing guidelines in CONTRIBUTING.md
- Document RTL best practices and patterns
- Add test templates for common component types
- Document coverage targets and reporting
- Effort: 1 day
- Acceptance: Documentation published, team trained

### Definition of Done
- 75% overall coverage across both apps (unit + integration)
- All critical paths tested
- MSW set up for API mocking
- E2E smoke tests pass on every PR
- E2E full tests pass nightly
- Coverage monitoring in CI/CD
- Documentation complete

---

## Epic 6: Tailwind CSS 4 Migration

**Priority:** P3 (Low)
**Effort:** 1-2 weeks
**Impact:** Low (mostly configuration, no functional changes)
**Timeline:** Backlog (after P1-P2 complete)
**Dependencies:** None (independent migration)

### Objective
Upgrade Tailwind CSS from 3 to 4, migrating from JavaScript config to CSS-based `@theme` directive, and updating design system variables.

### Current State
- Tailwind CSS 3.4.18 in both apps
- tailwind.config.ts files with theme extensions
- design-system.css with custom CSS variables

### Stories

**Story 6.1: Audit Tailwind 3 Usage**
- Review both tailwind.config.ts files
- Search for deprecated color names (warm-gray, cool-gray, etc.)
- Document custom theme extensions (colors, spacing, typography)
- Check for any Tailwind plugins used
- Effort: 1 day
- Acceptance: Audit report with findings, no blockers identified

**Story 6.2: Create CSS-Based Config - ai-automation-ui**
- Create `src/input.css` with `@import "tailwindcss"`
- Add `@theme { --color-teal: #14b8a6; ... }` for custom colors
- Add `@source "../src/**/*.{ts,tsx}"`
- Delete old tailwind.config.ts
- Update vite.config.ts if needed
- Test build and dev server
- Effort: 2 hours
- Acceptance: Tailwind works with new CSS config, no errors

**Story 6.3: Create CSS-Based Config - health-dashboard**
- Same as 6.2 but for health-dashboard
- Include all Radix UI colors and design tokens
- Effort: 2 hours
- Acceptance: Build succeeds, styles applied correctly

**Story 6.4: Refactor design-system.css**
- Extract theme variables to CSS @theme directives
- Update any deprecated color names
- Consolidate light-mode variables (currently only dark mode defined)
- Test light mode color contrast
- Effort: 1 day
- Acceptance: design-system.css uses new @theme syntax, light mode defined

**Story 6.5: Test & Verify**
- Visual regression testing (spot-check UI across pages)
- npm run test:run (unit tests)
- npm run test:e2e:smoke (E2E smoke tests)
- Compare bundle sizes to React 19 + Vite 7 baseline
- Effort: 1 day
- Acceptance: All tests pass, no visual regressions, bundle size stable

**Story 6.6: Update Documentation**
- Document Tailwind CSS 4 usage in README
- Update design system documentation
- Note @theme pattern for future contributors
- Effort: 2 hours
- Acceptance: Documentation published

### Definition of Done
- Tailwind CSS 4 running in both apps
- CSS-based config in place (no more tailwind.config.ts)
- All tests passing
- No visual regressions
- Documentation updated

---

## Implementation Order

```
Sprint 2:
  ├─ Epic 1: Frontend Security (2-4 hrs)
  ├─ Epic 2: Streamlit Performance (1 week)
  └─ Epic 3: Bundle Optimization (2-3 weeks, parallel)

Sprint 3-4:
  ├─ Epic 4: React 19 + Vite 7 (3-4 weeks)
  └─ Epic 3: Complete (if not done)

Sprint 5-6:
  ├─ Epic 5: Frontend Testing (3 weeks)
  └─ (Other stories in parallel)

Backlog:
  └─ Epic 6: Tailwind CSS 4 (1-2 weeks, after P1-P2)
```

---

## Risk Mitigation

| Epic | Risk | Mitigation |
|------|------|-----------|
| Security | Key leaks in production | Pre-commit hooks, automated audit in CI |
| Streamlit | Regression in dashboard UX | Comprehensive testing, load test before deploy |
| Bundle | Size regression | CI check to alert on size growth |
| React 19 + Vite 7 | Breaking changes | Comprehensive test suite, feature branch, rollback plan |
| Testing | Test flakiness | MSW mocking, stable timeouts, retry logic |
| Tailwind 4 | Style regressions | Visual regression testing, careful migration |

---

## Resource Allocation

**Recommended team allocation:**
- 1 frontend engineer full-time on these epics
- Code review from tech lead (3-5 hrs/week)
- QA testing (2 hrs/week for E2E tests)

**Estimated timeline:**
- 12-16 weeks total (Sprints 2-6)
- Parallelizable work can reduce to 10 weeks

---

## Success Metrics

| Epic | Metric | Target |
|------|--------|--------|
| Security | Exposed secrets found | 0 |
| Streamlit | Dashboard responsiveness | <100ms update latency |
| Bundle | LH Performance score | 85+ |
| React 19 | Test pass rate | 100% |
| Testing | Coverage | 75% overall |
| Tailwind 4 | Visual regressions | 0 |

---

**Next steps:**
1. Create epics in project management system
2. Assign resources to Sprint 2 stories
3. Review research document for detailed implementation guidance
4. Schedule kickoff meeting with team
