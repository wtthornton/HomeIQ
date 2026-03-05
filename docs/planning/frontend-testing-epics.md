# Frontend Testing Epics & Stories

**Created:** 2026-03-02
**Based on:** Automated agent review of all 3 frontend apps
**Status:** In Progress — Epic 37 (E2E intent-based rewrite) complete
**Supersedes:** Frontend Epics Roadmap Epic 5 (generic testing framework) — this plan is detailed and actionable

> **Epic 37 (Complete — 2026-03-05):** All 55 Playwright E2E test files rewritten with
> intent-based methodology across Health Dashboard (30 files) and AI Automation UI (21 files).
> 157/189 tests passing (83%), 20 skipped. Commit `b8fe047`.

---

## Executive Summary

A 3-agent parallel review audited every test file, component, hook, service, and utility across all three frontend apps. The findings reveal significant gaps:

| App | Test Files | Source Files | File Coverage | Test Cases | Infrastructure |
|-----|-----------|-------------|---------------|------------|----------------|
| **health-dashboard** | 15 | 169 | 14% | ~142 | Vitest + RTL + MSW |
| **ai-automation-ui** | 7 | 105 | 7% | ~100 | Vitest + RTL + Playwright (22 E2E) |
| **observability-dashboard** | 0 | 12 | 0% | 0 | None (Streamlit/Python) |
| **TOTAL** | 22 | 286 | 8% | ~242 | Mixed |

### Key Findings
- **2 stub test files** with TODO placeholders (ServiceMetrics, serviceMetricsClient)
- **0 tests** for observability-dashboard (Streamlit app — needs pytest setup)
- **Major tabs untested**: OverviewTab (47KB), ConfigurationTab, HygieneTab, ValidationTab, EnergyTab
- **No API client tests** for core chat/conversation services (ai-automation-ui)
- **No hook tests** for 14/16 hooks in health-dashboard
- **Strong patterns exist**: SportsTab.test.tsx, inputSanitizer.test.ts, store.test.ts are excellent references

---

## Epic Numbering

Project epics 1-49 are allocated. Frontend testing starts at **Epic 50**.

---

## Epic 50: Frontend Test Infrastructure & Coverage Baseline

**Priority:** P0 (Critical Foundation)
**Effort:** 1 week
**Impact:** Enables all subsequent testing work
**Dependencies:** None

### Objective
Establish coverage reporting, fix broken/stub tests, and set up missing test infrastructure for the observability-dashboard.

### Stories

**Story 50.1: Set Up Coverage Reporting for React Apps**
- Configure `vitest --coverage` with Istanbul provider in health-dashboard and ai-automation-ui
- Generate baseline coverage reports for both apps
- Add `npm run test:coverage` script if missing
- Document baseline numbers in this file
- Effort: 2 hours
- Acceptance: Coverage reports generated, baseline documented

**Story 50.2: Fix Stub Test Files (health-dashboard)**
- Implement real tests in `ServiceMetrics.test.tsx` (currently 5 TODOs)
- Implement real tests in `serviceMetricsClient.test.ts` (currently 7 TODOs)
- Follow existing patterns from `LiveGameCard.test.tsx` and `SportsTab.test.tsx`
- Effort: 3 hours
- Acceptance: All TODO stubs replaced with passing tests, 0 stub files remain

**Story 50.3: Fix Pre-existing Test Failure (api.test.ts)**
- Fix `api.test.ts > fetches the services health endpoint directly` failure
- Root cause: MSW handler URL mismatch or auth issue
- Ensure all health-dashboard tests pass green
- Effort: 1 hour
- Acceptance: `npm run test:run` exits 0 with no failures

**Story 50.4: Set Up pytest Infrastructure for Observability Dashboard**
- Add test dependencies to requirements.txt: `pytest>=8.0`, `pytest-asyncio>=0.23`, `pytest-mock>=3.12`, `httpx[test]`
- Create `tests/` directory with `conftest.py`
- Create mock fixtures for JaegerClient, Streamlit session state
- Add `pytest.ini` or pyproject.toml config
- Effort: 3 hours
- Acceptance: `pytest` runs successfully (even with 0 tests initially)

**Story 50.5: Add CI Coverage Gating**
- Update CI to run `npm run test:run` for both React apps
- Run `pytest` for observability-dashboard
- Add coverage thresholds: warn at <50%, fail at <30% (initial low bar)
- Effort: 2 hours
- Acceptance: CI runs tests on PR, coverage report visible

### Definition of Done
- Coverage baseline documented for all 3 apps
- 0 stub/TODO test files
- 0 pre-existing test failures
- pytest infrastructure ready for observability-dashboard
- CI runs all frontend tests

---

## Epic 51: Health Dashboard — Critical Path Testing

**Priority:** P0 (Critical)
**Effort:** 2 weeks
**Impact:** High — covers the largest app with most users
**Dependencies:** Epic 50 complete

### Objective
Achieve 50%+ file coverage for health-dashboard by testing all critical tabs, core hooks, and the API layer.

### Stories

**Story 51.1: OverviewTab Tests (P0)**
- Create `src/components/tabs/__tests__/OverviewTab.test.tsx`
- Test: rendering, metric cards, chart display, loading/error states, dark mode
- This is the 47KB main entry point — the most critical untested component
- Mock: useHealth, useStatistics, useServiceMetrics hooks
- Target: 15-20 tests
- Effort: 4 hours
- Acceptance: All states covered, 0 failures

**Story 51.2: Core Hooks Test Suite (P0)**
- Create tests for these 6 critical hooks:
  - `useDevices.ts` — device fetching, error handling, refresh
  - `useAlerts.ts` — alert data, filtering
  - `useDataSources.ts` — data source status
  - `useEnvironmentHealth.ts` — environment metrics
  - `useServiceMetrics.ts` — service metric fetching
  - `useRealtimeMetrics.ts` — real-time data stream
- Follow pattern from `useHealth.test.ts` and `useStatistics.test.ts`
- Target: 8-12 tests per hook (50-70 total)
- Effort: 6 hours
- Acceptance: All hooks tested with success, error, and loading paths

**Story 51.3: API Client Expansion (P0)**
- Expand `api.test.ts` from 2 tests to comprehensive coverage
- Test all dataApi methods: getDevices, getEntities, getIntegrations, getServices, getHealth
- Test all adminApi methods: getStatistics, getConfiguration
- Test error handling: 400, 401, 404, 500, network timeout
- Test auth header inclusion
- Target: 25-30 tests
- Effort: 4 hours
- Acceptance: All API methods tested, all error codes handled

**Story 51.4: Configuration & Settings Tabs (P1)**
- Create tests for:
  - `ConfigurationTab.tsx` (6.7KB) — form handling, config display
  - `SetupTab.tsx` (2.4KB) — initial setup flow
- Target: 10-15 tests per tab
- Effort: 3 hours
- Acceptance: Form interactions, validation, save/cancel tested

**Story 51.5: Data & Analytics Tabs (P1)**
- Create tests for:
  - `EnergyTab.tsx` (12KB) — energy metrics, charts
  - `EventsTab.tsx` (7.2KB) — event stream, filtering
  - `DataSourcesTab.tsx` — data source status display
  - `DependenciesTab.tsx` (2.6KB) — dependency graph
- Target: 8-12 tests per tab
- Effort: 5 hours
- Acceptance: Data loading, filtering, error states covered

**Story 51.6: Quality & Monitoring Tabs (P1)**
- Create tests for:
  - `HygieneTab.tsx` (13KB) — device health checks
  - `ValidationTab.tsx` (18KB) — automation validation
  - `ServicesTab.tsx` — service status display
  - `GroupsTab.tsx` — group health display
- Target: 10-15 tests per tab
- Effort: 5 hours
- Acceptance: Status indicators, health checks, grouping logic tested

**Story 51.7: Alert System Tests (P1)**
- Create tests for:
  - `AlertsPanel.tsx` — alert list, filtering, dismiss
  - `AlertCard.tsx` — individual alert rendering
  - `AlertFilters.tsx` — filter controls
  - `AlertStats.tsx` — alert statistics
  - `useAlerts.ts` hook (if not covered in 51.2)
- Target: 20-25 tests
- Effort: 4 hours
- Acceptance: Alert lifecycle (create, display, filter, dismiss) fully tested

**Story 51.8: Modal Dialog Tests (P2)**
- Create tests for:
  - `ServiceDetailsModal.tsx`
  - `RAGDetailsModal.tsx`
  - `IntegrationDetailsModal.tsx`
  - `DataSourceConfigModal.tsx`
- Test: open/close, data display, interactions, keyboard escape
- Target: 6-8 tests per modal
- Effort: 4 hours
- Acceptance: All modals tested for rendering, interactions, accessibility

### Definition of Done
- 50%+ file coverage for health-dashboard
- All P0 components/hooks/services tested
- All tab components have at least basic rendering + loading + error tests
- CI green

---

## Epic 52: AI Automation UI — Critical Path Testing

**Priority:** P0 (Critical)
**Effort:** 2 weeks
**Impact:** High — core AI chat interface and automation management
**Dependencies:** Epic 50 complete

### Objective
Achieve 40%+ file coverage for ai-automation-ui by testing the chat system, API clients, and core page components.

### Stories

**Story 52.1: API Client Unit Tests (P0)**
- Create `src/services/__tests__/api-v2.test.ts`
  - Test: conversation CRUD, message sending, error handling, auth
  - Target: 15-20 tests
- Create `src/services/__tests__/haAiAgentApi.test.ts`
  - Test: chat API calls, tool execution, response parsing
  - Target: 15-20 tests
- Effort: 4 hours
- Acceptance: All API methods tested with success + error paths

**Story 52.2: HAAgentChat Page Tests (P0)**
- Create `src/pages/__tests__/HAAgentChat.test.tsx`
- Test: conversation loading, message rendering, input handling, send flow
- Test: error states (API failure, network timeout)
- Test: conversation switching, new conversation
- Mock: haAiAgentApi, api-v2, useConversationV2
- Target: 20-30 tests
- Effort: 4 hours
- Acceptance: All major user flows tested

**Story 52.3: Chat Component Tests (P0)**
- Create tests for:
  - `MessageContent.tsx` — markdown rendering, tool call display, code blocks
  - `ConversationSidebar.tsx` — conversation list, selection, deletion
  - `AutomationProposal.tsx` — YAML display, approve/reject actions
  - `MarkdownErrorBoundary.tsx` — error fallback rendering
- Target: 15-20 tests per component
- Effort: 6 hours
- Acceptance: All content types rendered correctly, interactions work

**Story 52.4: Device Picker & Suggestions Tests (P0)**
- Create tests for:
  - `DevicePicker.tsx` — device list loading, filtering, multi-select, API calls
  - `DeviceSuggestions.tsx` — suggestion display, selection
- Mock: deviceApi service
- Target: 15-20 tests
- Effort: 3 hours
- Acceptance: Filter combinations, selection state, error handling tested

**Story 52.5: useConversationV2 Hook Tests (P1)**
- Create `src/hooks/__tests__/useConversationV2.test.ts`
- Test: conversation lifecycle (create, load, send message, receive response)
- Test: async operations, loading states, error handling
- Test: conversation history management
- Target: 15-20 tests
- Effort: 3 hours
- Acceptance: All hook states and transitions tested

**Story 52.6: Page Component Tests (P1)**
- Create tests for:
  - `Suggestions.tsx` — suggestion list, filtering, status management
  - `Deployed.tsx` — deployed automation display, status badges
  - `Patterns.tsx` — pattern display and filtering
  - `Synergies.tsx` — synergy detection display
- Target: 10-12 tests per page
- Effort: 5 hours
- Acceptance: Data loading, filtering, user interactions tested

**Story 52.7: Modal & Action Tests (P1)**
- Create tests for:
  - `BatchActionModal.tsx` — bulk approve/reject/deploy
  - `DeviceMappingModal.tsx` — device mapping UI
  - `SuggestionCard.tsx` — individual suggestion actions
  - `ConversationalSuggestionCard.tsx` — conversational variant
- Target: 8-10 tests per component
- Effort: 4 hours
- Acceptance: All modals open/close, actions dispatch correctly

**Story 52.8: Service Layer Tests (P2)**
- Create tests for:
  - `deviceApi.ts` — device CRUD operations
  - `proactiveApi.ts` — proactive suggestion API
  - `blueprintSuggestionsApi.ts` — blueprint API
- Target: 8-10 tests per service
- Effort: 3 hours
- Acceptance: All endpoints tested with mocked HTTP responses

### Definition of Done
- 40%+ file coverage for ai-automation-ui
- Chat system fully tested (API, page, components, hook)
- All page components have at least basic tests
- CI green

---

## Epic 53: Observability Dashboard — Full Test Suite

**Priority:** P1 (High)
**Effort:** 1 week
**Impact:** Medium — smaller app but 0% coverage is a risk
**Dependencies:** Epic 50 Story 50.4 (pytest setup)

### Objective
Achieve 70%+ coverage for the observability-dashboard by testing the Jaeger client, data processing functions, and async helpers.

### Stories

**Story 53.1: JaegerClient Unit Tests (P0)**
- Create `tests/test_jaeger_client.py`
- Test with mocked httpx:
  - `get_traces()` — success, filters, timestamp conversion (microseconds), error handling
  - `get_services()` — success, caching (5-min TTL), force_refresh
  - `get_trace()` — single trace retrieval, 404 handling
  - `get_dependencies()` — dependency graph parsing
  - `search_traces()` — search with parameters
  - `close()` — client cleanup
- Test Pydantic model validation: TraceSpan, Trace, Service, Dependency
- Test malformed JSON graceful fallback
- Target: 25-30 tests
- Effort: 4 hours
- Acceptance: All methods tested, cache behavior validated, error paths covered

**Story 53.2: Async Helpers Tests (P0)**
- Create `tests/test_async_helpers.py`
- Test `run_async_safe()`:
  - Normal path (no existing event loop)
  - Streamlit path (event loop already running → ThreadPoolExecutor fallback)
  - Timeout handling (default 30s)
  - Exception propagation
- Target: 8-10 tests
- Effort: 2 hours
- Acceptance: Both event loop paths tested, timeout verified

**Story 53.3: Service Performance Page Logic Tests (P1)**
- Create `tests/test_service_performance.py`
- Extract and test pure functions:
  - `_calculate_service_metrics()` — percentile calculations (p50, p95, p99)
  - Health status determination (error rate thresholds: 5% warning, 10% critical)
  - Latency penalty calculation (>1000ms)
  - DataFrame creation and formatting
- Test edge cases: empty traces, single span, high error rates, zero division
- Target: 15-20 tests
- Effort: 3 hours
- Acceptance: All calculation logic tested with boundary conditions

**Story 53.4: Real-Time Monitoring Logic Tests (P1)**
- Create `tests/test_real_time_monitoring.py`
- Test:
  - `_detect_anomalies()` — 1000ms latency threshold, error detection
  - `_calculate_service_health()` — formula: `100 - (error_rate * 2) - latency_penalty`
  - `_has_errors()` — error tag detection with truthy value
  - DataFrame creation with status emoji mapping
- Edge cases: no traces, all errors, health score floor at 0
- Target: 12-15 tests
- Effort: 3 hours
- Acceptance: Anomaly detection and health scoring fully validated

**Story 53.5: Trace Visualization Logic Tests (P1)**
- Create `tests/test_trace_visualization.py`
- Test:
  - `_has_errors()` — error tag detection
  - `_create_trace_dataframe()` — unique service extraction, duration aggregation
  - Duration conversion (microseconds to milliseconds)
  - CHILD_OF reference parsing for dependency graph
- Target: 10-12 tests
- Effort: 2 hours
- Acceptance: Data transformation logic validated

**Story 53.6: Automation Debugging Logic Tests (P2)**
- Create `tests/test_automation_debugging.py`
- Test:
  - `_query_automation_traces()` — filter by automation_id, home_id, correlation_id (OR logic)
  - `_is_automation_success()` — error tag detection, success tag fallback
  - Performance DataFrame creation with status field
  - Step sorting by startTime
- Target: 10-12 tests
- Effort: 2 hours
- Acceptance: Filter logic and status determination tested

### Definition of Done
- 70%+ coverage for observability-dashboard
- JaegerClient fully tested with mocked HTTP
- All calculation/transformation logic tested
- pytest runs clean in CI

---

## Epic 54: Test Quality & Cleanup

**Priority:** P2 (Important)
**Effort:** 1 week
**Impact:** Medium — improves reliability of existing tests
**Dependencies:** Epics 51-52 in progress or complete

### Objective
Improve quality of existing and newly created tests. Add missing accessibility, dark mode, and error boundary coverage. Establish testing standards.

### Stories

**Story 54.1: Accessibility Test Sweep**
- Audit all test files for accessibility assertions
- Add ARIA label checks, keyboard navigation, screen reader text to:
  - All tab components (heading roles, landmark regions)
  - All modal components (focus trap, escape key, aria-modal)
  - All form components (label associations, error announcements)
- Follow pattern from `LiveGameCard.test.tsx` (ARIA labels) and `Navigation.test.tsx` (aria-current, focus styles)
- Effort: 4 hours
- Acceptance: Every interactive component has at least 1 accessibility assertion

**Story 54.2: Dark Mode Test Sweep**
- Add dark mode rendering test to every component test file
- Pattern: render with `darkMode={true}`, assert class names include dark variant
- Follow pattern from `SportsTab.test.tsx` (`bg-gray-900` check)
- Effort: 3 hours
- Acceptance: Every component test has a dark mode test case

**Story 54.3: Error Boundary Tests**
- Create tests for:
  - health-dashboard: `ErrorBoundary.tsx`, `PageErrorBoundary.tsx`
  - ai-automation-ui: `MarkdownErrorBoundary.tsx`
- Test: error thrown by child → fallback rendered, error info displayed
- Test: recovery (re-render after error cleared)
- Effort: 2 hours
- Acceptance: Error boundaries tested with thrown errors and recovery

**Story 54.4: Loading Skeleton Tests**
- Create tests for health-dashboard skeleton components:
  - `SkeletonCard.tsx`, `SkeletonGraph.tsx`, `SkeletonList.tsx`, `SkeletonTable.tsx`
- Test: renders correctly, has proper ARIA attributes (`aria-busy`, `role="status"`)
- Test: correct number of placeholder elements
- Effort: 2 hours
- Acceptance: All skeletons render and are accessible

**Story 54.5: Testing Standards Documentation**
- Create `docs/TESTING_STANDARDS.md` covering:
  - Test file naming and location conventions
  - Required test categories per component type (rendering, interactions, states, a11y, dark mode)
  - Mock setup/teardown patterns
  - When to use unit vs integration vs E2E
  - Coverage targets by file type (utilities 85%, components 60%, hooks 70%, pages 50%)
- Add test templates for: component, hook, service, utility
- Effort: 3 hours
- Acceptance: Standards doc published, templates available

**Story 54.6: MSW Handler Expansion (health-dashboard)**
- Expand `src/tests/mocks/handlers.ts` to cover all API endpoints
- Add handlers for: devices, entities, integrations, alerts, energy, events
- Add error response handlers (500, 401, timeout)
- Effort: 2 hours
- Acceptance: All data-api and admin-api endpoints have MSW handlers

### Definition of Done
- Every component test file includes accessibility and dark mode tests
- Error boundaries and skeletons tested
- Testing standards document published
- MSW handlers comprehensive

---

## Epic 55: Integration & E2E Test Expansion

**Priority:** P2 (Important)
**Effort:** 2 weeks
**Impact:** High — catches cross-component and real-world bugs
**Dependencies:** Epics 51-53 substantially complete

### Objective
Add integration tests for cross-component flows and expand E2E coverage for critical user journeys.

### Stories

**Story 55.1: Health Dashboard Integration Tests**
- Test cross-tab navigation flows (tab switching preserves state)
- Test data refresh propagation (refresh in one tab updates shared state)
- Test sidebar navigation with URL routing
- Use MSW for realistic API responses
- Target: 10-15 integration tests
- Effort: 4 hours
- Acceptance: Navigation and data flow across tabs verified

**Story 55.2: AI Automation UI Integration Tests**
- Test complete conversation flow: open chat → send message → receive response → view proposal → approve
- Test suggestion lifecycle: view → select → review → deploy
- Test device picker → suggestion integration
- Use MSW for realistic API responses
- Target: 10-15 integration tests
- Effort: 5 hours
- Acceptance: End-to-end user flows verified at component level

**Story 55.3: Health Dashboard E2E Smoke Tests (Playwright)**
- Create/expand Playwright specs for health-dashboard:
  - Overview page loads with metrics
  - Device page loads and filters work
  - Service page shows health status
  - Navigation between all sidebar items
  - Dark mode toggle persists
- Target: 10-12 smoke tests
- Effort: 4 hours
- Acceptance: Smoke tests pass on every PR

**Story 55.4: Cross-App Navigation E2E**
- Test app switcher navigation between:
  - health-dashboard ↔ ai-automation-ui
  - health-dashboard ↔ observability-dashboard
- Test shared footer links
- Target: 5-8 tests
- Effort: 3 hours
- Acceptance: Cross-app navigation verified

**Story 55.5: Performance Baseline Tests**
- Add performance assertions for large datasets:
  - health-dashboard: 1000+ devices render within 2s
  - ai-automation-ui: 100+ suggestions render within 1s
  - health-dashboard: 10,000+ events don't freeze UI
- Use Playwright `page.evaluate()` for timing measurements
- Effort: 3 hours
- Acceptance: Performance thresholds documented and enforced

**Story 55.6: Visual Regression Setup**
- Set up Playwright visual comparison for stable UI components
- Create baseline screenshots for: Overview, Devices, Services pages
- Configure tolerance thresholds (5% pixel difference)
- Effort: 3 hours
- Acceptance: Visual regression catches CSS breakage

### Definition of Done
- Integration tests cover cross-component data flows
- E2E smoke tests run on every PR
- Performance baselines established
- Visual regression active for key pages

---

## Execution Timeline

```
Week 1:  Epic 50 (Infrastructure & Baseline)
         ├── 50.1 Coverage reporting
         ├── 50.2 Fix stub tests
         ├── 50.3 Fix pre-existing failures
         ├── 50.4 pytest for observability-dashboard
         └── 50.5 CI gating

Week 2-3: Epic 51 (Health Dashboard) + Epic 53 (Observability)
         ├── 51.1 OverviewTab (P0)        53.1 JaegerClient (P0)
         ├── 51.2 Core Hooks (P0)         53.2 Async Helpers (P0)
         ├── 51.3 API Client (P0)         53.3 Service Performance (P1)
         ├── 51.4 Config/Setup Tabs       53.4 Real-Time Monitoring (P1)
         ├── 51.5 Data/Analytics Tabs     53.5 Trace Visualization (P1)
         ├── 51.6 Quality/Monitor Tabs    53.6 Automation Debugging (P2)
         ├── 51.7 Alert System
         └── 51.8 Modals

Week 3-4: Epic 52 (AI Automation UI)
         ├── 52.1 API Clients (P0)
         ├── 52.2 HAAgentChat Page (P0)
         ├── 52.3 Chat Components (P0)
         ├── 52.4 Device Picker (P0)
         ├── 52.5 useConversationV2 (P1)
         ├── 52.6 Page Components (P1)
         ├── 52.7 Modals & Actions (P1)
         └── 52.8 Service Layer (P2)

Week 5:  Epic 54 (Quality & Cleanup)
         ├── 54.1 Accessibility sweep
         ├── 54.2 Dark mode sweep
         ├── 54.3 Error boundaries
         ├── 54.4 Loading skeletons
         ├── 54.5 Testing standards doc
         └── 54.6 MSW handler expansion

Week 6-7: Epic 55 (Integration & E2E)
         ├── 55.1 HD integration tests
         ├── 55.2 AI-UI integration tests
         ├── 55.3 HD E2E smoke tests
         ├── 55.4 Cross-app E2E
         ├── 55.5 Performance baselines
         └── 55.6 Visual regression
```

---

## Coverage Targets

| Milestone | health-dashboard | ai-automation-ui | observability-dashboard |
|-----------|-----------------|-----------------|------------------------|
| **Current** | 14% files | 7% files | 0% files |
| **After Epic 50** | 16% (stubs fixed) | 7% | 0% (infra ready) |
| **After Epic 51** | 50%+ | 7% | 0% |
| **After Epic 52** | 50%+ | 40%+ | 0% |
| **After Epic 53** | 50%+ | 40%+ | 70%+ |
| **After Epic 54** | 55%+ | 45%+ | 70%+ |
| **After Epic 55** | 60%+ | 50%+ | 70%+ |

---

## Story Count Summary

| Epic | Stories | Est. Tests | Effort |
|------|---------|-----------|--------|
| **50** Infrastructure & Baseline | 5 | ~30 | 1 week |
| **51** Health Dashboard Critical | 8 | ~180 | 2 weeks |
| **52** AI Automation UI Critical | 8 | ~170 | 2 weeks |
| **53** Observability Dashboard | 6 | ~85 | 1 week |
| **54** Quality & Cleanup | 6 | ~50 | 1 week |
| **55** Integration & E2E | 6 | ~55 | 2 weeks |
| **TOTAL** | **39 stories** | **~570 tests** | **~9 weeks** |

---

## Appendix A: Existing Test Quality Ratings

### health-dashboard (15 test files)

| Test File | Tests | Quality | Notes |
|-----------|-------|---------|-------|
| inputSanitizer.test.ts | 87 | 5/5 | Comprehensive security testing |
| useTeamPreferences.test.ts | 14 | 5/5 | localStorage integration solid |
| SportsTab.test.tsx | 16 | 5/5 | All states, accessibility, dark mode |
| LiveGameCard.test.tsx | 8 | 5/5 | Accessibility + dark mode |
| DevicesTab.test.tsx | 15 | 4/5 | Good coverage, new addition |
| Dashboard.interactions.test.tsx | 5 | 4/5 | Good interaction tests |
| EnvironmentHealthCard.test.tsx | 5 | 4/5 | Loading, error, health states |
| useHealth.test.ts | 4 | 4/5 | MSW mocking solid |
| useStatistics.test.ts | 3 | 4/5 | Period parameter tested |
| UpcomingGameCard.test.tsx | 6 | 4/5 | Good accessibility |
| apiUsageCalculator.test.ts | 9 | 4/5 | Color/threshold logic |
| Dashboard.test.tsx | 3 | 3/5 | Too minimal |
| api.test.ts | 2 | 3/5 | Needs expansion + has failure |
| ServiceMetrics.test.tsx | 5 | 1/5 | STUB — all TODO |
| serviceMetricsClient.test.ts | 7 | 1/5 | STUB — all TODO |

### ai-automation-ui (7 test files)

| Test File | Tests | Quality | Notes |
|-----------|-------|---------|-------|
| inputSanitizer.test.ts | 48 | 5/5 | XSS prevention comprehensive |
| store.test.ts | 40+ | 5/5 | Zustand state mgmt thorough |
| AutomationPreview.test.tsx | 30+ | 5/5 | Best component test example |
| HAAgentChat.originalPrompt.test.tsx | 18 | 5/5 | State + persistence thorough |
| proposalParser.test.ts | 18 | 4/5 | Good utility coverage |
| Navigation.test.tsx | 14 | 5/5 | Accessibility-first |
| LoadingSpinner.test.tsx | 11 | 5/5 | All variants + accessibility |

### observability-dashboard (0 test files)
No tests exist.

---

## Appendix B: Reference Test Patterns

When creating new tests, use these as templates:

- **Tab Component**: `health-dashboard/src/components/tabs/__tests__/DevicesTab.test.tsx`
- **Hook**: `health-dashboard/src/hooks/__tests__/useHealth.test.ts`
- **Sports Component**: `health-dashboard/src/components/sports/__tests__/SportsTab.test.tsx`
- **Store**: `ai-automation-ui/src/store/__tests__/store.test.ts`
- **Complex Component**: `ai-automation-ui/src/components/ha-agent/__tests__/AutomationPreview.test.tsx`
- **Security Utility**: `health-dashboard/src/utils/__tests__/inputSanitizer.test.ts`
