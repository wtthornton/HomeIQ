# Epic 43: Health Dashboard — Critical Path Testing

**Sprint:** 10
**Priority:** P0 (Critical)
**Status:** Open
**Created:** 2026-03-09
**Effort:** 2 weeks
**Dependencies:** Epic 42 complete
**Source:** `docs/planning/frontend-testing-epics.md` (Epic 51 mapping)

## Objective

Achieve 50%+ file coverage for health-dashboard by testing all critical tabs, core hooks, and the API layer. Currently at 14% file coverage (15 test files / 169 source files).

## Stories

### Story 43.1: OverviewTab Tests (P0)
- Create `src/components/tabs/__tests__/OverviewTab.test.tsx`
- Test: rendering, metric cards, chart display, loading/error states, dark mode
- Mock: useHealth, useStatistics, useServiceMetrics hooks
- **Target:** 15-20 tests
- **Effort:** 4 hours
- **Acceptance:** All states covered, 0 failures

### Story 43.2: Core Hooks Test Suite (P0)
- Test 6 critical hooks: useDevices, useAlerts, useDataSources, useEnvironmentHealth, useServiceMetrics, useRealtimeMetrics
- Follow pattern from `useHealth.test.ts` and `useStatistics.test.ts`
- **Target:** 50-70 tests (8-12 per hook)
- **Effort:** 6 hours
- **Acceptance:** All hooks tested with success, error, and loading paths

### Story 43.3: API Client Expansion (P0)
- Expand `api.test.ts` from 2 tests to comprehensive coverage
- Test all dataApi methods: getDevices, getEntities, getIntegrations, getServices, getHealth
- Test all adminApi methods: getStatistics, getConfiguration
- Test error handling: 400, 401, 404, 500, network timeout
- **Target:** 25-30 tests
- **Effort:** 4 hours
- **Acceptance:** All API methods tested, all error codes handled

### Story 43.4: Configuration & Settings Tabs (P1)
- Test ConfigurationTab.tsx (6.7KB) and SetupTab.tsx (2.4KB)
- **Target:** 20-30 tests
- **Effort:** 3 hours

### Story 43.5: Data & Analytics Tabs (P1)
- Test EnergyTab, EventsTab, DataSourcesTab, DependenciesTab
- **Target:** 32-48 tests
- **Effort:** 5 hours

### Story 43.6: Quality & Monitoring Tabs (P1)
- Test HygieneTab (13KB), ValidationTab (18KB), ServicesTab, GroupsTab
- **Target:** 40-60 tests
- **Effort:** 5 hours

### Story 43.7: Alert System Tests (P1)
- Test AlertsPanel, AlertCard, AlertFilters, AlertStats
- **Target:** 20-25 tests
- **Effort:** 4 hours

### Story 43.8: Modal Dialog Tests (P2)
- Test ServiceDetailsModal, RAGDetailsModal, IntegrationDetailsModal, DataSourceConfigModal
- **Target:** 24-32 tests
- **Effort:** 4 hours

## Acceptance Criteria
- [ ] 50%+ file coverage for health-dashboard
- [ ] All P0 components/hooks/services tested
- [ ] All tab components have basic rendering + loading + error tests
- [ ] CI green
