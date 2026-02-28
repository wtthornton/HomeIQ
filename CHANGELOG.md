# Changelog

## [Unreleased] - 2026-02-27

### Major

- **feat: complete SQLite removal — PostgreSQL is sole database (Epic 0)** (81a233dc) — 311 files changed across all 10 stories: removed SQLite from 11 compose files, 12 database init files, 11 config files, 19 requirements files, 13 Alembic configs, 12 test fixtures, CI workflows, 100+ docs; deleted 24 SQLite-specific scripts; archived migration tools

### Security

- **fix: resolve 5 blocking security/quality findings** (b7d0c198) — SQL injection prevention in `database_pool.py`, timing-safe auth token comparison, CORS credentials bypass guard in admin-api, race condition lock on shared engine creation, timezone-aware datetimes in data-api and admin-api

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
