# Epic 84: E2E Test Stale Selector & Deprecated Reference Remediation

**Priority:** P2 High | **Effort:** 1 session | **Dependencies:** None | **Status:** COMPLETE (Mar 18)
**Affects:** `tests/e2e/` (40+ Playwright spec files)

## Background

After completing the health-dashboard redesign (tab-based navigation, new component structure)
and deprecating the enrichment-pipeline (Epic 31), approximately **130+ E2E test failures** remain
due to stale `data-testid` selectors, deprecated service references, and outdated navigation
patterns. These tests were written against an earlier version of the dashboard that used sidebar
navigation (`nav-monitoring`, `nav-settings`, `nav-dashboard`) and screen-based views
(`monitoring-screen`, `settings-screen`).

### Current Dashboard Architecture

The health-dashboard now uses a **tab-based navigation model**:
- Valid selectors: `dashboard-root`, `dashboard-header`, `dashboard-content`, `dashboard-title`
- Tab navigation: `tab-navigation`, `tab-overview`, `tab-services`, `tab-configuration`, `tab-events`, `tab-logs`
- Components: `service-list`, `health-card`, `event-stream`, `event-stream-viewer`
- Controls: `auto-refresh-toggle`, `theme-toggle`, `time-range-selector`
- Status: `error-state`, `error-message`, `websocket-status`, `rag-status-card`

### Categories of Stale References

| Category | Count | Impact |
|----------|-------|--------|
| Stale `data-testid` selectors | 169+ uses across 20+ files | Tests fail with element-not-found |
| Deprecated navigation (`nav-*`) | 35 uses across 4 files | Entire navigation model changed |
| Deprecated enrichment-pipeline (port 8002) | 6+ references in 2 files | Connection refused / timeout |
| Deprecated SQLite references | 3 files | Wrong database assumptions |
| Deprecated screen patterns (`*-screen`) | 18 uses across 7 files | Views no longer exist |
| Internal card field selectors | 9 uses across 3 files | Sub-component IDs not exposed |

### Remediation Strategy

- **Fix real code first**: If the dashboard is missing a `data-testid` that tests legitimately
  need, add it to the dashboard component source.
- **Fix tests second**: Update selectors to match current dashboard structure.
- **Delete deprecated tests**: Remove tests for services that no longer exist (enrichment-pipeline,
  SQLite migration).

## Stories

| Story | Description | Files | Stale Refs | Status |
|-------|-------------|-------|------------|--------|
| 84.1 | **Remove deprecated enrichment-pipeline references** — Delete port 8002 health checks, enrichment service expectations, and weather enrichment endpoint tests | `integration-performance-enhanced.spec.ts`, `performance.spec.ts` | 6+ | COMPLETE |
| 84.2 | **Remove deprecated SQLite/migration tests** — Delete or rewrite tests that assume SQLite backend, migration state, or sqlite3 dependency checks | `database-migration.spec.ts`, `database-health.spec.ts`, `cross-service-data-flow.spec.ts` | 3 files | COMPLETE |
| 84.3 | **Fix navigation pattern — sidebar to tabs** — Replace all `nav-monitoring`, `nav-settings`, `nav-dashboard` selectors with tab-based navigation (`tab-overview`, `tab-services`, `tab-configuration`, `tab-events`) | `dashboard-data-loading.spec.ts`, `performance.spec.ts`, `user-journey-complete.spec.ts`, `integration-performance-enhanced.spec.ts` | 35 | COMPLETE |
| 84.4 | **Fix deprecated screen selectors** — Replace `monitoring-screen` and `settings-screen` with tab navigation + tab content assertions | `monitoring-screen.spec.ts`, `dashboard-data-loading.spec.ts`, `performance.spec.ts`, `integration.spec.ts`, `user-journey-complete.spec.ts` | 18+ | COMPLETE |
| 84.5 | **Fix settings selectors** — Replace `settings-screen`, `settings-form`, `settings-modal` and related selectors with `tab-configuration` tab content queries | 14 files with `settings-*` selectors | 36 | COMPLETE |
| 84.6 | **Fix health card internal selectors** — Replace `health-card-status`, `health-card-title`, `health-card-value` with `health-card` parent + text/role queries | `dashboard-data-loading.spec.ts`, `integration-performance-enhanced.spec.ts`, `user-journey-complete.spec.ts` | 9 | COMPLETE |
| 84.7 | **Fix event and statistics selectors** — Replace `events-feed`, `events-section`, `events-list` with `event-stream`; replace `statistics-section`, `statistics-card`, `statistic-value` with Overview tab content | `dashboard-data-loading.spec.ts`, `integration.spec.ts`, `user-journey-complete.spec.ts` | 16 | COMPLETE |
| 84.8 | **Fix service-card selectors** — Verify if `service-card` is still exposed in `service-list` or update to use `service-list` child queries | `modals.spec.ts`, `filters.spec.ts`, `monitoring-screen.spec.ts`, `integration.spec.ts` | 10 | COMPLETE |
| 84.9 | **Fix user-journey-complete.spec.ts** — Full rewrite of the comprehensive user journey test to match current tab-based UI, auth model, and service topology | `user-journey-complete.spec.ts` | 53+ | COMPLETE |
| 84.10 | **Add missing data-testid attributes to dashboard** — Audit dashboard components for any testid gaps that tests legitimately need; add `data-testid` attributes to source components | `domains/core-platform/health-dashboard/src/` | — | COMPLETE |
| 84.11 | **Full E2E regression run** — Execute complete Playwright suite across chromium/firefox/webkit, verify 0 stale selector failures, document remaining auth-only or API-mismatch failures separately | All spec files | — | COMPLETE |

## Acceptance Criteria

- [x] Zero E2E test failures caused by stale `data-testid` selectors
- [x] No references to port 8002 (enrichment-pipeline) in any test file
- [x] No references to SQLite backend in any test file
- [x] All navigation tests use tab-based model (`tab-*` selectors)
- [x] Dashboard source has `data-testid` on all testable interactive elements
- [x] Full Playwright suite passes on chromium (firefox/webkit stretch goal)
