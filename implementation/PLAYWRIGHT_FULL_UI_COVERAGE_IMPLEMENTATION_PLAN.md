# Playwright Full UI & API Coverage Implementation Plan

**Created:** February 7, 2026  
**Last Updated:** February 7, 2026 (Phases 5–6 complete)  
**Source:** tapps-agents planner  
**Goal:** Ensure ALL UI features, buttons, headers, APIs that the UIs use work via comprehensive Playwright E2E tests

---

## 1. Overview

### Objective
Create a comprehensive Playwright E2E test suite that delivers **full coverage** of HomeIQ frontends—every tab, button, header, form, API integration, and user interaction—to verify the UI and its backing APIs work correctly.

### Scope
- **health-dashboard** (Port 3000) – Primary system monitoring UI  
- **ai-automation-ui** (Port 3001) – AI automation, Ask AI, patterns, deployed automations

### Success Criteria
- Every tab renders and loads its data
- Every button/control performs its intended action
- Every API endpoint called by the UIs has at least one E2E test
- Headers, navigation, theme, refresh controls work as expected
- Error states and loading states are exercised

---

## 2. Frontend Inventory

### 2.1 Health Dashboard (Port 3000)

#### Tabs (16 total)
| Tab ID | Label | Primary APIs | Components |
|--------|-------|--------------|------------|
| overview | Overview | /api/health, /api/v1/health, /api/v1/stats, /api/v1/health/services, /api/v1/alerts/active, /api/v1/docker/containers, /api/v1/real-time-metrics | RAGStatusSection, CoreSystemCard, ConnectionStatusIndicator |
| setup | Setup & Health | /api/health, /api/v1/health | SetupWizard, EnvironmentHealth |
| services | Services | /api/v1/health/services | ServicesTab |
| dependencies | Dependencies | Integration health | DependenciesTab |
| devices | Devices | /api/devices, /api/entities | DevicesTab |
| events | Events | /api/v1/events, /api/v1/events/search, /api/v1/events/stats | EventsTab |
| logs | Logs | /api/v1/docker/containers/{id}/logs | LogsTab |
| sports | Sports | /api/v1/sports/games/live, /api/v1/sports/games/history, /api/v1/ha/game-context, /api/v1/ha/game-status | SportsTab |
| data-sources | Data Sources | /api/integrations | DataSourcesTab |
| energy | Energy | /api/v1/energy/statistics, /api/v1/energy/correlations, /api/v1/energy/current, /api/v1/energy/circuits, /api/v1/energy/top-consumers | EnergyTab |
| analytics | Analytics | Analytics data | AnalyticsTab |
| alerts | Alerts | /api/v1/alerts/active, /api/v1/alerts/{id}/acknowledge, /api/v1/alerts/{id}/resolve | AlertsTab |
| hygiene | Device Hygiene | /api/v1/hygiene/issues | HygieneTab |
| validation | HA Validation | HA validation APIs | ValidationTab |
| synergies | Synergies | AI pattern service | SynergiesTab |
| configuration | Configuration | /api/v1/docker/api-keys | ConfigurationTab |

#### Global Controls
| Control | data-testid | Action |
|---------|-------------|--------|
| Theme toggle | theme-toggle | Toggle light/dark mode |
| Auto-refresh toggle | auto-refresh-toggle | Enable/disable polling |
| Time range selector | time-range-selector | Change period (1h, 24h, 7d) |
| Tab navigation | tab-{id} | Switch tabs |
| Dashboard root | dashboard-root | Layout container |

#### API Endpoints Used (health-dashboard)
- `/api/health`, `/api/v1/health`, `/api/v1/health/services`
- `/api/v1/stats`, `/api/v1/stats?period=1h`
- `/api/v1/alerts/active`, `/api/v1/alerts/{id}/acknowledge`, `/api/v1/alerts/{id}/resolve`
- `/api/v1/docker/containers`, `/api/v1/docker/containers/{id}/start|stop|restart`
- `/api/v1/docker/containers/{id}/logs`, `/api/v1/docker/containers/{id}/stats`
- `/api/v1/docker/api-keys`, `/api/v1/docker/api-keys/{service}`, `/api/v1/docker/api-keys/{service}/test`
- `/api/v1/real-time-metrics`
- `/api/devices`, `/api/devices/{id}`
- `/api/entities`, `/api/entities/{id}`
- `/api/integrations`
- `/api/v1/events`, `/api/v1/events/{id}`, `/api/v1/events/search`, `/api/v1/events/stats`
- `/api/v1/energy/statistics`, `/api/v1/energy/correlations`, `/api/v1/energy/current`, `/api/v1/energy/circuits`, `/api/v1/energy/top-consumers`, `/api/v1/energy/device-impact/{id}`
- `/api/v1/hygiene/issues`, `/api/v1/hygiene/issues/{key}/status`, `/api/v1/hygiene/issues/{key}/actions/apply`
- `/api/v1/sports/games/live`, `/api/v1/sports/games/history`, `/api/v1/sports/games/timeline/{id}`
- `/api/v1/ha/game-context/{team}`, `/api/v1/ha/game-status/{team}`

### 2.2 AI Automation UI (Port 3001)

#### Pages
| Page | Route | Primary APIs | Components |
|------|-------|--------------|------------|
| Conversational Dashboard | / | AI automation, suggestions | SuggestionCard, FilterPills, BatchActions |
| Ask AI / HA Agent Chat | /ask-ai, /ha-agent | /api/v1/ask-ai/query, NL generate | SendButton, ConversationSidebar, DevicePicker, AutomationPreview |
| Deployed | /deployed | Deployed automations API | DeployedBadge, CTAActionButtons |
| Patterns | /patterns | Pattern API | PatternChart, PatternDetailsModal, SynergyChart |
| Settings | /settings | Settings API, API keys | PreferenceSettings, TeamTrackerSettings |
| Discovery | /discovery | Device intelligence | DeviceExplorer, SmartShopping |
| Synergies | /synergies | Synergy API | NetworkGraphView, RoomCard, RoomMapView |
| Proactive Suggestions | /proactive | Proactive API | ProactiveFilters, ProactiveStats, ProactiveSuggestionCard |
| Blueprint Suggestions | /blueprint-suggestions | Blueprint API | BlueprintSuggestions |
| Admin | /admin | Admin APIs | Admin page |
| Name Enhancement | /name-enhancement | Name enhancement API | NameEnhancementDashboard |

#### API Services Used (ai-automation-ui)
- AI Automation (8018): suggestions, NL generate, deploy
- Device Intelligence (8028): devices, team-tracker
- Admin (8004)
- Data (8006)
- HA AI Agent (8030)
- Blueprint Suggestions (8039)

#### Key UI Components to Test
- Navigation (all pages)
- DevicePicker, DeviceSuggestions
- SuggestionCard, ConversationalSuggestionCard
- Modals: BatchActionModal, ClearChatModal, DeleteConversationModal, DeviceMappingModal, PatternDetailsModal
- Chat interface: SendButton, ConversationSidebar, MessageContent
- Filters: FilterPills, ProactiveFilters, SearchBar
- Charts: PatternChart, SynergyChart, NetworkGraphView

---

## 3. Test Gap Analysis

### 3.1 Current Coverage (as of Feb 2026)
| Area | Existing Tests | Gaps |
|------|----------------|------|
| health-dashboard tabs | health-dashboard/pages/tabs/*.spec.ts (partial) | Many tabs untested; API mock setup required |
| health-dashboard components | health-dashboard/components/*.spec.ts | Forms, modals, charts need more coverage |
| health-dashboard APIs | api-endpoints.spec.ts | Direct API tests exist; UI→API flow under-tested |
| ai-automation-ui pages | ai-automation-ui/pages/*.spec.ts, ai-automation-*.spec.ts | Ask AI timing issues; Deployed, Patterns, Discovery need more tests |
| ai-automation-ui components | ai-automation-ui/components/*.spec.ts | DevicePicker, modals, chat flow need coverage |

### 3.2 Missing Test Categories
1. **Tab load + API integration** – Each tab loads and calls its APIs successfully  
2. **Button/control actions** – Theme toggle, refresh, time range, container start/stop  
3. **Form submissions** – Settings, API key updates, hygiene actions  
4. **Modal workflows** – Open, fill, submit, cancel  
5. **Error handling** – API errors, empty states, network failures  
6. **Accessibility** – Keyboard nav, ARIA, focus management  

---

## 4. User Stories & Prioritization

### Phase 1: Health Dashboard – Core UI (Complexity 2–3)
| ID | User Story | Complexity | Dependencies |
|----|------------|------------|--------------|
| P1.1 | As a user, I can load the health dashboard and see the header with theme toggle, auto-refresh, and time range selector | 1 | None |
| P1.2 | As a user, I can switch between all 16 tabs and each tab renders without crashing | 2 | P1.1 |
| P1.3 | As a user, the Overview tab loads and displays health cards, RAG status, and core system data | 3 | P1.2 |
| P1.4 | As a user, the theme toggle switches between light and dark mode and persists | 1 | P1.1 |
| P1.5 | As a user, the time range selector changes the data period (1h, 24h, 7d) | 2 | P1.1 |
| P1.6 | As a user, the auto-refresh toggle enables/disables data polling | 2 | P1.1 |

### Phase 2: Health Dashboard – API-Backed Tabs (Complexity 3–4)
| ID | User Story | Complexity | Dependencies |
|----|------------|------------|--------------|
| P2.1 | As a user, the Services tab loads and displays service health from /api/v1/health/services | 3 | P1.2 |
| P2.2 | As a user, the Devices tab loads and displays devices from /api/devices | 3 | P1.2 |
| P2.3 | As a user, the Events tab loads and displays events from /api/v1/events | 3 | P1.2 |
| P2.4 | As a user, the Alerts tab loads and displays alerts; I can acknowledge and resolve alerts | 4 | P1.2 |
| P2.5 | As a user, the Energy tab loads and displays energy statistics and correlations | 4 | P1.2 |
| P2.6 | As a user, the Hygiene tab loads and displays hygiene issues; I can update status/apply actions | 4 | P1.2 |
| P2.7 | As a user, the Configuration tab loads and I can view/update API keys | 4 | P1.2 |
| P2.8 | As a user, the Sports tab loads and displays live games and history | 4 | P1.2 |
| P2.9 | As a user, the Data Sources tab loads and displays integrations | 3 | P1.2 |
| P2.10 | As a user, the Logs tab loads container logs | 3 | P1.2 |
| P2.11 | As a user, the Analytics tab loads analytics data | 4 | P1.2 |
| P2.12 | As a user, the Validation tab loads HA validation results | 3 | P1.2 |
| P2.13 | As a user, the Synergies tab loads synergy data | 4 | P1.2 |
| P2.14 | As a user, the Dependencies tab loads dependency info | 3 | P1.2 |
| P2.15 | As a user, the Setup tab loads setup/health info | 3 | P1.2 |

### Phase 3: Health Dashboard – Docker & Advanced (Complexity 4)
| ID | User Story | Complexity | Dependencies |
|----|------------|------------|--------------|
| P3.1 | As a user, I can start/stop/restart containers from the Docker UI | 4 | P2.1 |
| P3.2 | As a user, I can view container logs and stats | 3 | P2.1 |
| P3.3 | As a user, API key test returns success/failure feedback | 3 | P2.7 |

### Phase 4: AI Automation UI – Core Pages (Complexity 3–4)
| ID | User Story | Complexity | Dependencies |
|----|------------|------------|--------------|
| P4.1 | As a user, I can navigate to all AI automation pages (Dashboard, Ask AI, Deployed, Patterns, Settings, Discovery, Synergies, Proactive, Blueprint, Admin) | 2 | None |
| P4.2 | As a user, the Dashboard page loads and displays suggestions (or empty state) | 4 | P4.1 |
| P4.3 | As a user, the Ask AI page loads; I can type a query and submit; suggestions appear (or mock) | 4 | P4.1 |
| P4.4 | As a user, the Deployed page loads and displays deployed automations | 3 | P4.1 |
| P4.5 | As a user, the Patterns page loads and displays pattern charts | 4 | P4.1 |
| P4.6 | As a user, the Settings page loads and I can view/update preferences | 3 | P4.1 |
| P4.7 | As a user, the Discovery page loads and displays device explorer | 4 | P4.1 |
| P4.8 | As a user, the Synergies page loads and displays synergy data | 4 | P4.1 |

### Phase 5: AI Automation UI – Components & Workflows (Complexity 4–5)
| ID | User Story | Complexity | Dependencies |
|----|------------|------------|--------------|
| P5.1 | As a user, I can filter suggestions by category/confidence | 3 | P4.2 |
| P5.2 | As a user, I can approve and deploy a suggestion | 5 | P4.2 |
| P5.3 | As a user, I can reject a suggestion with feedback | 4 | P4.2 |
| P5.4 | As a user, the DevicePicker opens and I can select devices | 4 | P4.3 |
| P5.5 | As a user, modals (ClearChat, DeleteConversation, BatchAction, DeviceMapping, PatternDetails) open and close correctly | 3 | P4.1 |
| P5.6 | As a user, the chat interface displays messages and loading states | 4 | P4.3 |
| P5.7 | As a user, the sidebar examples populate the query input when clicked | 2 | P4.3 |

### Phase 6: API Integration Tests (Complexity 3–4)
| ID | User Story | Complexity | Dependencies |
|----|------------|------------|--------------|
| P6.1 | Every health-dashboard API endpoint returns valid JSON when called (direct request test) | 3 | None |
| P6.2 | Every ai-automation-ui API endpoint returns valid JSON when called | 3 | None |
| P6.3 | UI→API flow: Dashboard tab X triggers call to API Y; response populates UI | 4 | P2.*, P4.* |

---

## 5. Implementation Phases

### Phase 1 (Week 1): Foundation
- Page Object Models for health-dashboard (DashboardPage, TabPage)
- Auth/mock setup for health-dashboard (api-helpers, auth-helpers)
- Tests: P1.1–P1.6

### Phase 2 (Week 2–3): Health Dashboard Tabs
- API mocks per tab (handlers for /api/v1/health, /api/devices, etc.)
- Tests: P2.1–P2.15

### Phase 3 (Week 3): Health Dashboard Advanced
- Docker container actions, logs, API key test
- Tests: P3.1–P3.3

### Phase 4 (Week 4): AI Automation UI Pages
- Page Object Models for ai-automation-ui
- Base URL/config for port 3001
- Tests: P4.1–P4.8

### Phase 5 (Week 5–6): AI Automation UI Workflows
- DevicePicker, modals, chat flow
- API mocks for AI automation (suggestions, deploy)
- Tests: P5.1–P5.7

### Phase 6 (Week 6): API Integration Matrix
- API endpoint inventory → test matrix
- Direct API tests for every endpoint
- UI→API flow assertions

---

## 6. Test Structure

```
tests/e2e/
├── health-dashboard/
│   ├── pages/
│   │   ├── dashboard.spec.ts
│   │   └── tabs/
│   │       ├── overview.spec.ts
│   │       ├── services.spec.ts
│   │       ├── devices.spec.ts
│   │       ├── events.spec.ts
│   │       ├── alerts.spec.ts
│   │       ├── energy.spec.ts
│   │       ├── hygiene.spec.ts
│   │       ├── configuration.spec.ts
│   │       ├── sports.spec.ts
│   │       ├── data-sources.spec.ts
│   │       ├── logs.spec.ts
│   │       ├── analytics.spec.ts
│   │       ├── validation.spec.ts
│   │       ├── synergies.spec.ts
│   │       ├── dependencies.spec.ts
│   │       └── setup.spec.ts
│   ├── components/
│   │   ├── theme-toggle.spec.ts
│   │   ├── refresh-controls.spec.ts
│   │   └── modals.spec.ts
│   └── fixtures/
│       └── api-mocks.ts (expand)
├── ai-automation-ui/
│   ├── pages/
│   │   ├── dashboard.spec.ts
│   │   ├── ask-ai.spec.ts
│   │   ├── deployed.spec.ts
│   │   ├── patterns.spec.ts
│   │   ├── settings.spec.ts
│   │   ├── discovery.spec.ts
│   │   └── synergies.spec.ts
│   ├── components/
│   │   ├── device-picker.spec.ts
│   │   ├── modals.spec.ts
│   │   └── workflows/
│       └── automation-creation.spec.ts
├── api-integration/
│   ├── health-dashboard-apis.spec.ts   # P6.1 Admin + Data API endpoints
│   ├── ai-automation-apis.spec.ts      # P6.2 AI automation services
│   └── ui-api-flow.spec.ts             # P6.3 UI→API flow verification
├── page-objects/
│   ├── HealthDashboardPage.ts
│   ├── AIDashboardPage.ts
│   └── ...
└── configs/
    ├── health-dashboard.config.ts  (baseURL 3000)
    └── ai-automation.config.ts     (baseURL 3001)
```

---

## 7. Configuration & Tooling

### Playwright Config
- **Multi-baseURL projects:** One project for health-dashboard (3000), one for ai-automation-ui (3001)
- **API mocking:** MSW or `page.route()` for deterministic tests
- **Timeouts:** 30s default; 60s for AI/async flows
- **Retries:** 1 local, 2 CI

### CI Integration
- Smoke suite (fast): system-health, minimal-dashboard
- Full suite: all tabs, all pages, API integration
- Run order: smoke → health-dashboard → ai-automation-ui → api-integration
- **api-integration project:** `tests/playwright.config.ts` includes `api-integration` project for `tests/e2e/api-integration/`

---

## 8. Dependencies

- Playwright 1.56+
- MSW (optional) for API mocking
- Docker Compose for backend services
- Admin API (8004), Data API (8006), AI Automation (8018) running for full tests

---

## 9. Acceptance Criteria

- [x] All 16 health-dashboard tabs have at least one test that loads the tab and verifies data/API call
- [x] All 10+ ai-automation-ui pages have at least one test that loads and verifies content
- [x] Theme toggle, refresh controls, time range selector tested
- [x] Every API endpoint in health-dashboard api.ts has at least one E2E or API test
- [x] Every API service in ai-automation-ui config has at least one test
- [x] Key modals and workflows (approve, deploy, reject) tested
- [ ] Test suite runs in CI with pass/fail gates

### Implementation Status (Feb 2026)

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 | Done | Page objects, auth (sessionStorage.api_key), P1.1-P1.6 |
| Phase 2 | Done | 16 tabs, services/configuration/logs with data-testid |
| Phase 3 | Done | P3.1-P3.3 (container actions, logs, API key test) |
| Phase 4 | Done | P4.1-P4.8, proactive + blueprint specs, navigation |
| Phase 5 | Done | P5.1-P5.7 filters, approve/deploy, reject, DevicePicker, modals, chat, sidebar |
| Phase 6 | Done | P6.1 health-dashboard + data-api endpoints, P6.2 ai-automation services, P6.3 UI→API flow |

---

## 10. References

- [Execution Status](PLAYWRIGHT_FULL_UI_COVERAGE_EXECUTION_STATUS.md) – Phase completion, run commands, files touched
- [E2E Issues List](PLAYWRIGHT_E2E_ISSUES_LIST.md) – Resolved issues, quality passes
- [API Reference](docs/api/API_REFERENCE.md)
- [Epic 31 Architecture](.cursor/rules/epic-31-architecture.mdc)
- [Existing E2E Tests](tests/e2e/README.md)
- [Services Ranked by Importance](services/SERVICES_RANKED_BY_IMPORTANCE.md)
