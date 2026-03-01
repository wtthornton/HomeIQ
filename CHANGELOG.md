# Changelog

## [Unreleased] - 2026-03-01

### Added

- **standardize PostgreSQL initialization with DatabaseManager across all 13 services** (d93bcac) - Bill Thornton
- **TAPPS quality gate fixes + browser review critical stories (6 stories, 52 files)** (c224571) - Bill Thornton
- **complete SQLite removal — PostgreSQL is sole database (Epic 0)** (6c5480b) - Bill Thornton
- **Phase 4.7 — cross-group service-to-service Bearer token auth** (b99aef7) - Bill Thornton
- **Phase 4.6 — group-level health dashboard with color-coded aggregation** (2af65d4) - Bill Thornton
- **Phase 4.5 — AI fallback with CircuitBreaker for ml-engine degradation** (d885f05) - Bill Thornton
- **Phase 4b frontend redesign — teal palette, sidebar nav, app consolidation** (9c170ff) - Bill Thornton
- **infra fixes, library bumps, and proactive-agent RAG integration** (74ee779) - Bill Thornton
- **implement 5 service stubs across 4 domains** (c0c7919) - Bill Thornton
- **implement 6 stub services and wire persistent eval sinks** (88a4a31) - Bill Thornton
- **operational readiness - Alembic, monitoring, CI, backups, E2E, runbooks** (41c61dd) - Bill Thornton
- **SQLite to PostgreSQL migration + library version standardization** (8508f97) - Bill Thornton
- **Phase 1 dependency updates, Dockerfile modernization, and documentation refresh** (7066ce7) - Bill Thornton

### Fixed

- **update E2E test to accept degraded status from api-automation-edge** (a525412) - Bill Thornton
- **508-compliant status indicators + resolve 12 false health statuses** (3b40295) - Bill Thornton
- **eliminate false-positive health status for data sources** (e5d3cb6) - Bill Thornton
- **resolve 119 E2E test failures after frontend sidebar redesign** (c27e453) - Bill Thornton
- **resolve 5 blocking security/quality findings + add deployment planning docs** (9d570d2) - Bill Thornton
- **wire HealthEndpointManager into simple_main.py for /health/groups** (6991a46) - Bill Thornton
- **add missing logging_config module to homeiq-data package** (e26008a) - Bill Thornton
- **switch Claude Code hooks from .sh to .ps1 for Windows compatibility** (06dfa52) - Bill Thornton
- **remove 20 files committed with literal ${workspaceFolder} path prefix** (850d47a) - Bill Thornton
- **update pytest-asyncio config for explicit loop scope across all services** (141da0d) - Bill Thornton


### Added

- **DatabaseManager standardization across all 13 PostgreSQL services** — new `DatabaseManager` class in homeiq-data shared library replaces 4 different database initialization patterns with a single, standardized approach. `initialize()` never raises, enabling graceful degradation. Added `validate_database_url()` to prevent empty-string URLs from reaching SQLAlchemy. 14 database modules + 12 lifespan handlers updated. Fixes proactive-agent-service crash when `POSTGRES_URL` is unset.
- **508 accessibility compliance for health dashboard status indicators** — replaced color-only dots with distinct SVG icon shapes (CheckCircle, AlertTriangle, Octagon/stop-sign, CircleMinus), added ARIA roles/labels, replaced emoji indicators in ConnectionStatusIndicator with Lucide icons
- **TAPPS quality gate fixes + browser review critical stories (6 stories, 52 files)** (c224571) - Bill Thornton
- **complete SQLite removal — PostgreSQL is sole database (Epic 0)** (6c5480b) - Bill Thornton
- **Phase 4.7 — cross-group service-to-service Bearer token auth** (b99aef7) - Bill Thornton
- **Phase 4.6 — group-level health dashboard with color-coded aggregation** (2af65d4) - Bill Thornton
- **Phase 4.5 — AI fallback with CircuitBreaker for ml-engine degradation** (d885f05) - Bill Thornton
- **Phase 4b frontend redesign — teal palette, sidebar nav, app consolidation** (9c170ff) - Bill Thornton
- **infra fixes, library bumps, and proactive-agent RAG integration** (74ee779) - Bill Thornton
- **implement 5 service stubs across 4 domains** (c0c7919) - Bill Thornton
- **implement 6 stub services and wire persistent eval sinks** (88a4a31) - Bill Thornton
- **operational readiness - Alembic, monitoring, CI, backups, E2E, runbooks** (41c61dd) - Bill Thornton
- **SQLite to PostgreSQL migration + library version standardization** (8508f97) - Bill Thornton
- **Phase 1 dependency updates, Dockerfile modernization, and documentation refresh** (7066ce7) - Bill Thornton
- **complete domain architecture restructuring (Epics 1-4)** (d47f7c0) - Bill Thornton

### Fixed

- **proactive-agent-service crash when POSTGRES_URL is unset** — empty string passed to SQLAlchemy caused service to never start. Now handled by DatabaseManager graceful degradation.
- **eliminate false-positive health status for data sources** (e5d3cb6) - Bill Thornton
- **health dashboard: 10 services showing false-positive RED** — changed health endpoints to return HTTP 200 with `"status": "degraded"` instead of HTTP 503 for expected conditions (missing HA config, unavailable DB, downstream services down). Affected: energy-correlator, energy-forecasting, proactive-agent-service, ai-pattern-service, api-automation-edge, ai-core-service, device-intelligence-service, device-context-classifier, device-setup-assistant
- **health dashboard: 2 services showing false-positive GREEN** — air-quality-service now reports "degraded" when 0% fetch success rate; calendar-service no longer returns 503 for "no_calendars_found"
- **health dashboard: weather-api and carbon-intensity-service incorrectly shown as stopped** — removed hardcoded STOPPED status in admin-api mock container data; added Compose label fallback for service name matching
- **resolve 119 E2E test failures after frontend sidebar redesign** (c27e453) - Bill Thornton
- **resolve 5 blocking security/quality findings + add deployment planning docs** (9d570d2) - Bill Thornton
- **wire HealthEndpointManager into simple_main.py for /health/groups** (6991a46) - Bill Thornton
- **add missing logging_config module to homeiq-data package** (e26008a) - Bill Thornton
- **switch Claude Code hooks from .sh to .ps1 for Windows compatibility** (06dfa52) - Bill Thornton
- **remove 20 files committed with literal ${workspaceFolder} path prefix** (850d47a) - Bill Thornton
- **update pytest-asyncio config for explicit loop scope across all services** (141da0d) - Bill Thornton
- **resolve data-api startup and legacy shared.* imports (Phase 1 complete)** (296ce95) - Bill Thornton
- **resolve pre-existing e2e test failures** (d1d0921) - Bill Thornton
- **OTel mock fallbacks, blueprint-suggestion Docker context, resilience E2E tests** (7d6c3e9) - Bill Thornton


### Added

- **complete SQLite removal — PostgreSQL is sole database (Epic 0)** (6c5480b) - Bill Thornton
- **Phase 4.7 — cross-group service-to-service Bearer token auth** (b99aef7) - Bill Thornton
- **Phase 4.6 — group-level health dashboard with color-coded aggregation** (2af65d4) - Bill Thornton
- **Phase 4.5 — AI fallback with CircuitBreaker for ml-engine degradation** (d885f05) - Bill Thornton
- **Phase 4b frontend redesign — teal palette, sidebar nav, app consolidation** (9c170ff) - Bill Thornton
- **infra fixes, library bumps, and proactive-agent RAG integration** (74ee779) - Bill Thornton
- **implement 5 service stubs across 4 domains** (c0c7919) - Bill Thornton
- **implement 6 stub services and wire persistent eval sinks** (88a4a31) - Bill Thornton
- **operational readiness - Alembic, monitoring, CI, backups, E2E, runbooks** (41c61dd) - Bill Thornton
- **SQLite to PostgreSQL migration + library version standardization** (8508f97) - Bill Thornton
- **Phase 1 dependency updates, Dockerfile modernization, and documentation refresh** (7066ce7) - Bill Thornton
- **complete domain architecture restructuring (Epics 1-4)** (d47f7c0) - Bill Thornton
- **service groups decomposition + cross-group resilience rollout** (6e9cf95) - Bill Thornton

### Fixed

- **resolve 5 blocking security/quality findings + add deployment planning docs** (9d570d2) - Bill Thornton
- **wire HealthEndpointManager into simple_main.py for /health/groups** (6991a46) - Bill Thornton
- **add missing logging_config module to homeiq-data package** (e26008a) - Bill Thornton
- **switch Claude Code hooks from .sh to .ps1 for Windows compatibility** (06dfa52) - Bill Thornton
- **remove 20 files committed with literal ${workspaceFolder} path prefix** (850d47a) - Bill Thornton
- **update pytest-asyncio config for explicit loop scope across all services** (141da0d) - Bill Thornton
- **resolve data-api startup and legacy shared.* imports (Phase 1 complete)** (296ce95) - Bill Thornton
- **resolve pre-existing e2e test failures** (d1d0921) - Bill Thornton
- **OTel mock fallbacks, blueprint-suggestion Docker context, resilience E2E tests** (7d6c3e9) - Bill Thornton
- **resolve 3 deployment bugs in resilience startup and health probes** (e206790) - Bill Thornton

### Major

- **feat: complete SQLite removal — PostgreSQL is sole database (Epic 0)** (81a233dc) — 311 files changed across all 10 stories: removed SQLite from 11 compose files, 12 database init files, 11 config files, 19 requirements files, 13 Alembic configs, 12 test fixtures, CI workflows, 100+ docs; deleted 24 SQLite-specific scripts; archived migration tools

### Testing

- **fix: resolve 119 E2E test failures after frontend sidebar redesign** (c27e453b) — Updated all Playwright E2E tests for Phase 4b sidebar navigation: page objects, route mappings (/ha-agent→/chat, /deployed→/automations, etc.), removed aria-selected assertions, deleted obsolete setup/synergies test files, added API timeout handling; 234 passed, 0 failed
- **fix: eliminate false-positive health status for data sources** (833be425) — Admin-api now overrides "healthy" when credentials are missing or all fetches failed; calendar-service tracks discovered vs configured calendars; dashboard labels insert spaces in camelCase keys

### Security

- **fix: Logs tab secret sanitization (browser-review Story 2)** — Added `sanitizeLogMessage()` with 7 regex patterns to redact Bearer tokens, API keys, passwords, connection strings, and secrets in LogTailViewer (fetchLogs, searchLogs, copyLog); 11 new tests
- **fix: resolve Bandit security findings (TAPPS Story 2)** — B104 nosec for Docker bind-all in blueprint-suggestion-service and energy-correlator; B112 narrowed bare except to specific types in correlator.py
- **fix: resolve 5 blocking security/quality findings** (b7d0c198) — SQL injection prevention in `database_pool.py`, timing-safe auth token comparison, CORS credentials bypass guard in admin-api, race condition lock on shared engine creation, timezone-aware datetimes in data-api and admin-api

### Fixed

- **fix: Ideas page suggestions API failure (browser-review Story 1)** — 10s fetch timeout via AbortController in api.ts, auth error classification (401/403), exponential backoff retries, error/empty state UI in ConversationalDashboard, ProactiveSuggestions, and BlueprintSuggestions
- **fix: Overview KPI perpetual loading (browser-review Story 1)** — `fetchWithTimeout(10s)` in useHealth/useStatistics hooks, `KPIValue` component with 3 states (loading/unavailable/stale), stale data preserved with "Xm ago" indicator, Retry button in SystemStatusHero
- **fix: Explore page devices API and mobile nav (browser-review Story 2)** — Demo mode banner with retry in Discovery.tsx, loading skeleton, dropdown disabled with spinner in DeviceExplorer, Explore added to MOBILE_TABS replacing Settings in Sidebar.tsx

### Improved

- **refactor: raise converter.py and yaml_transformer.py quality scores (TAPPS Story 1)** — converter.py MI 64→71 (CC 14→7 via data-driven field mapping), yaml_transformer.py MI 68→70 (CC 10→6 via strategy dispatch dict)

### Added

- **Phase 3 readiness report, Story 6.5 cutover plan, Phase 5 deployment plan, quality audit** (b7d0c198)
- **Phase 4.7 — cross-group service-to-service Bearer token auth** (b99aef75)
- **Phase 4.6 — group-level health dashboard with color-coded aggregation** (2af65d40)
- **Phase 4.5 — AI fallback with CircuitBreaker for ml-engine degradation** (d885f058)
- **Phase 4b frontend redesign — teal palette, sidebar nav, app consolidation** (9c170ff2)
- **infra fixes, library bumps, and proactive-agent RAG integration** (74ee7798)
- **implement 5 service stubs across 4 domains** (c0c7919b)
- **implement 6 stub services and wire persistent eval sinks** (88a4a319)
- **operational readiness — Alembic, monitoring, CI, backups, E2E, runbooks** (41c61dd1)
- **SQLite to PostgreSQL migration + library version standardization** (8508f973)
- **Phase 1 dependency updates, Dockerfile modernization, and documentation refresh** (7066ce7d)
- **complete domain architecture restructuring (Epics 1-4)** (d47f7c08)
- **service groups decomposition + cross-group resilience rollout** (6e9cf956)
- **upgrade LLM/ML model stack — OpenAI SDK 2.x, gpt-5.2-codex, library alignment** (b62f1a62)
- **feat(activity-recognition): Phase 1+2 integration and quality improvements** (78f19c48)
- **feat(ai-automation-service-new): separate plan (gpt-4o-mini) and YAML (Codex) models** (1bb834b1)
- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (35dccf6)
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (a30197f)
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (b929ef5)

### Fixed

- **wire HealthEndpointManager into simple_main.py for /health/groups** (6991a465)
- **add missing logging_config module to homeiq-data package** (e26008a1)
- **switch Claude Code hooks from .sh to .ps1 for Windows compatibility** (06dfa526)
- **remove 20 files committed with literal ${workspaceFolder} path prefix** (850d47ab)
- **update pytest-asyncio config for explicit loop scope across all services** (141da0d6)
- **resolve data-api startup and legacy shared.* imports (Phase 1 complete)** (296ce95c)
- **resolve pre-existing e2e test failures** (d1d0921a)
- **OTel mock fallbacks, blueprint-suggestion Docker context, resilience E2E tests** (7d6c3e98)
- **resolve 3 deployment bugs in resilience startup and health probes** (e2067902)
- **fix(ha-ai-agent): inject entity inventory, fix device-intel auth, switch to gpt-4.1** (9d9c397e)
- **resolve 5 deployment bugs across data-api, ha-ai-agent, ai-pattern, smart-meter** (e4e2c8ec)
- **platform-wide code quality review — 6,500+ lint fixes across 46 services** (9aae7e56)
- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (4f92f92f)
- **YAML tests, deployment router, entity extraction, and validator** (34f6f50)
- **Fix activity-recognition bugs; ai-automation-service updates** (a8bbcf9)
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (be3f154)
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (7e4a019)
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (624419d)
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (998501c)
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (e0099bb)
- **resolve 10 bugs via TappsMCP and misc updates** (93ab49f)
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (b6aeb25)
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (3cb5415)

### Chores

- **miscellaneous fixes — compose configs, lint cleanup, CI updates** (4a27d78e)
- **Phase 3 ML prerequisites, rollback script, and planning updates** (06c028c0)
- **cross-group integration test workflow (Step 3.5)** (98e6609e)
- **align ML library version pins and fix import ordering** (247d12ff)
- **untrack runtime files and update .gitignore** (cf20454e)
