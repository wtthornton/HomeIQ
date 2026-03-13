# HomeIQ — Open Epics & Stories Index

**Created:** 2026-02-27 | **Updated:** 2026-03-13 (Epic 57 complete, Phase 5 plan refreshed)
**Total:** 58 Completed Epics, 364 Stories complete | 5 Planned Epics (open)

> **IMPORTANT FOR AGENTS:** This is the **single source of truth** for all epic tracking.
> Before creating new epics, check this index for duplicates or superseded work.
> After completing any epic/story, update this file immediately.
> Open/planned work is in the **Open Work** section below the execution history.
> Sprint results archive: [SPRINT-HISTORY.md](SPRINT-HISTORY.md)

## Execution Order & Dependencies

```
Sprint 0 (COMPLETE)
└── Epic 0: SQLite Removal [P0, 3-5 days]                  ← COMPLETE (356 files cleaned)

Sprint 1.5 (Mar 2 — Agent Team Blitz) ← ALL COMPLETE
├── Epic 1: Frontend Security Hardening [P0]                ← COMPLETE (6 stories, 14 files)
├── Epic 4: Observability Dashboard Fixes [P1]              ← COMPLETE (8 stories, 35 tests)
├── Epic 9.3: TAPPS CI Integration [P1]                     ← COMPLETE (quality-gate.yml)
├── Epic 10: Browser Review AI UI [P1]                      ← COMPLETE (4/4 stories)
├── Epic 11: Browser Review Health Dashboard [P1]           ← COMPLETE (5/5 stories)
├── Epic 2: Health Dashboard Quality [P1]                   ← COMPLETE (8 stories)
├── Epic 3: AI Automation UI Quality [P1]                   ← COMPLETE (8 stories)
├── Epic 6: Backend Completion (ML + Tests) [P1]            ← COMPLETE (7 stories)
├── Epic 7: Feature Gaps [P2]                               ← COMPLETE (6 stories)
├── Epic 8: Production Deployment Scripts [P1]              ← COMPLETE (8 stories)
├── Epics 12-14: Shared Library Standardization [P1-P2]     ← COMPLETE (10 stories)
├── Epic 15: TAPPS Tracking by Service [P1]                 ← COMPLETE (53 services scored)
└── Epic 5: Frontend Framework Upgrades [P2]                ← PARTIAL (package.json not updated)

Sprint 2 — Quality Baseline Remediation ← ALL COMPLETE (Agent Teams, Mar 4)
├── Epic 16: Project-Wide Lint Cleanup [P1]                 ← COMPLETE (1571 violations fixed, 870+ files)
├── Epic 17: Tier 1 Quality Hardening [P0]                  ← COMPLETE (3/3 strict 80+: admin 80.3, ws 84.9, data 84.9)
├── Epic 18: Data Collectors Remediation [P1]               ← COMPLETE (8/8 pass 70+, was 0/8)
├── Epic 19: Low-Score Service Remediation [P1]             ← COMPLETE (8/8 pass 70+, activity-writer 51.9→81.9)
└── Epic 20: Shared Library Strict Compliance [P1]          ← COMPLETE (5/5 pass strict 80+, via lint fixes)

Sprint 3 — Docker Breakout ← ALL COMPLETE (Agent Teams, Mar 4)
├── Epic 21: Per-Domain Docker Isolation [P1]               ← COMPLETE (9 compose files + 2 scripts + 2 build contexts)
├── Epic 23: Dockerfile Hardening [P1]                      ← COMPLETE (13 Dockerfiles: root-user, healthcheck, UID, multi-stage)
├── Epic 22: Volume Decoupling [P1]                         ← COMPLETE (3 volumes decoupled, external refs + docs)
└── Epic 24: Deployment Tooling [P1]                        ← COMPLETE (domain.sh, start-stack.sh, deploy.sh archived)

Sprint 4 — Frontend Upgrades + Service Migration ← ALL COMPLETE (Agent Teams, Mar 4)
├── Epic 5: Vite 7 + Tailwind 4 Migration [P2]              ← COMPLETE (2 apps, builds pass)
└── Epics 12-14: Full Service Migration [P1]                 ← COMPLETE (38/38 services + InfluxDBManager)

Epic 8: Phase 5 Production Deployment ← COMPLETE (Mar 4)
├── Pre-deployment: 9/9 checks passed (42/42 health endpoints, PG 8/8 schemas, InfluxDB OK)
├── Docker fixes: .dockerignore **/node_modules, Dockerfile COPY reorder, psutil dep, uvicorn deps
├── Compose fixes: network external:true, blueprint health checks curl→python
├── Code fixes: ws-ingestion InvalidStateTransition re-export, asynccontextmanager, ha-ai-agent openai_api_key
└── Result: 52/53 healthy (ai-core-service resolved — AI_CORE_API_KEY now in .env)

Sprint 5 (COMPLETE — Mar 4, Agent Teams) — Sapphire-Inspired HA Enhancements
├── Epic 25: Direct Device Control Service [P1]             ← COMPLETE (7 stories, 24 files, new service port 8040)
└── Epic 28: Enhanced Event Bus + Real-Time Status [P2]     ← COMPLETE (4 stories, 14 files, aggregation + push)

Sprint 6 (COMPLETE — Mar 4, Agent Teams) — Voice + Scheduled Tasks
├── Epic 26: Voice Gateway Service [P1]                     ← COMPLETE (6 stories, 17 files, new service port 8041)
└── Epic 27: Scheduled AI Tasks (Continuity) [P2]           ← COMPLETE (5 stories, 15 files, enhances proactive-agent)

Sprint 7 (COMPLETE — Mar 6, Agent Teams) — Memory Brain (Institutional Memory)
├── Epic 29: Memory Store Foundation [P0]                   ← COMPLETE (6 stories, homeiq-memory lib + pgvector)
├── Epic 30: Explicit Memory Capture [P1]                   ← COMPLETE (4 stories, chat + feedback → memory)
├── Epic 31: Implicit Memory Capture [P1]                   ← COMPLETE (4 stories, overrides + behavior → memory)
├── Epic 32: Synthesized Memory [P1]                        ← COMPLETE (5 stories, consolidation job)
├── Epic 33: Memory Injection [P1]                          ← COMPLETE (5 stories, all AI services query memory)
├── Epic 34: Trust Model & Adaptive UX [P2]                 ← COMPLETE (3 stories, per-domain trust)
└── Epic 35: Memory Lifecycle & Observability [P2]          ← COMPLETE (4 stories, admin, dashboard, GC)

Sprint 8 (COMPLETE — Mar 7, 2026) — Pattern Detection + ML Upgrades
├── Epic 37: Pattern Detection Expansion [P1]               ← COMPLETE (10/10: 8 detectors + scheduler + dashboard)
└── Epic 38: ML Dependencies Upgrade [P2]                   ← COMPLETE (7/8: transformers, openvino, optimum-intel; 38.4 skipped)

Sprint 9 (Mar 2026) — React 19 + ML Patterns + Memory Tuning
├── Epic 39: React 19 Migration [P2]                        ← COMPLETE (6 stories, both apps already React 19.2.4 + Compiler)
├── Epic 40: Pattern Detection ML Upgrade [P2]              ← COMPLETE (8 stories, LSTM + Isolation Forest + FP-Growth)
└── Epic 41: Memory Brain Quality Tuning [P2]               ← COMPLETE (7 stories, trust scores + search + metrics)

Sprint 10 (COMPLETE — Mar 10, 2026) — Frontend Testing & Coverage
├── Epic 42: Frontend Test Infrastructure [P0]               ← COMPLETE (5 stories, 25 failures fixed, coverage config added)
├── Epic 43: Health Dashboard Testing [P0]                   ← COMPLETE (8 stories, 268 tests / 30 files, 16% file coverage)
├── Epic 44: AI Automation UI Testing [P0]                   ← COMPLETE (8 stories, 285 tests / 22 files, 19% file coverage)
└── Epic 45: Observability Dashboard Testing [P1]            ← COMPLETE (4 stories, 109 tests / 8 files, 57% file coverage)

Sprint 11 (COMPLETE — Mar 10, 2026) — Auto-Bugfix Pipeline
└── Epic 46: Auto-Bugfix Scan Robustness & Tests [P1]        ← COMPLETE (5 stories: scan format doc, retry/fallback, 3 test suites)

Sprint 12 (COMPLETE — Mar 12, 2026) — Auto-Bugfix Dashboard
└── Epic 47: Auto-Bugfix Dashboard Real-Time Updates [P1]   ← COMPLETE (7/7 stories: live usage from stream, atomic state writes, XHR polling 800ms, file:// fallback)

Sprint 13 (COMPLETE — Mar 10, 2026) — Auto-Bugfix Subagents
└── Epic 48: Auto-Bugfix Subagents Integration [P1]         ← COMPLETE (5 stories: bug-scanner subagent, -UseSubagents, docs)

Sprint 14 (COMPLETE — Mar 12, 2026) — E2E Playwright Coverage Expansion
└── Epic 49: E2E Playwright Coverage Expansion [P1]         ← COMPLETE (13/13: visual regression aligned, mocked Ask AI, empty/error/loading tests, route-spec matrix, /scheduled spec)

Sprint 15 (COMPLETE) — Auto-Fix Isolated Project (Epic 0)
└── Epic 50: Auto-Fix Isolated Project — Structure Setup [P1]  ← COMPLETE / EXECUTED (7 stories; structure in place; ready for Epic 1)

Sprint 16 (Complete) — E2E Skipped Tests
└── Epic 51: E2E Skipped Tests — Fix or Delete [P1]         ← COMPLETE (12 stories; 0 skipped). Follow-up: health 223 pass/2 fixme (RAG); AI UI 3 fail = enhancement-button.

Sprint 17 (COMPLETE — Mar 11, 2026) — Ask AI Integration Validation
└── Epic 53: Ask AI Integration Validation [P1]             ← COMPLETE (4 stories: schema doc, HA helper, full-flow test, CI decision=local/on-demand)

Sprint 18 (COMPLETE — Mar 12, 2026) — Auto-Bugfix Cleanup
└── Epic 52: Auto-Bugfix Cleanup — Delete Legacy [P1]       ← COMPLETE (6 stories: config verified, scripts assessed, docs updated, no deletions needed — all already config-driven)

Sprint 19 (COMPLETE — Mar 12, 2026) — Consolidation + Production Hardening + Observability
├── Epic 54: Consolidation Sprint [P1]                        ← COMPLETE (6/6 stories, commit 64f5f85c)
├── Epic 55: Production Hardening [P1]                        ← COMPLETE (6/6 stories, commit 0df0ae6e)
│   └── Rate limits, pool tuning, health hardening, security headers
└── Epic 56: Observability & Monitoring Hardening [P1]        ← COMPLETE (6/6 stories, commit cd0ffc32)
    └── Structured logging, Prometheus metrics, tracing, alerts, ops scripts, E2E smoke test

Sprint 20 (COMPLETE — Mar 13, 2026) — Cleanup & Gaps + Phase 5 Refresh
├── Epic 57: Cleanup & Gaps [P1]                              ← COMPLETE (4/4 stories)
│   └── tool_calls persistence, RAG data-testid, entity_extractor verified, secret scanning hook
└── Phase 5 Plan Refresh                                      ← COMPLETE (44+ health endpoints, 1366+ tests, 51+ services)

Sprint 21 (COMPLETE — Mar 13, 2026) — Chat Endpoint Complexity Refactor
└── Epic 60: Chat Endpoint Complexity Refactor [P1]           ← COMPLETE (3/3 stories)
    └── tool_execution.py extracted, _run_openai_loop() helper, lint fixes (721→481+254 lines)
```

---

## Open Work — Planned Epics (Not Yet Started)

> These epics are defined in planning docs but have **no commits yet**.
> They are listed in recommended execution order.
> Next available epic number: **61** (Epics 57-60 complete).

### P0 — Execute Now

| # | Epic | Source Doc | Stories | Effort | Notes |
|---|------|-----------|---------|--------|-------|
| — | **Phase 5: Production Deployment** | [phase-5-deployment-plan.md](../docs/planning/phase-5-deployment-plan.md) | 9-tier rollout | 5 days | **REFRESHED Mar 13** — plan updated to 56 epics / 51+ services / 44+ health endpoints / 1366+ tests. Incorporates Epics 54-56 hardening. Ready for scheduling. |

### P1 — Start After Phase 5

| # | Epic | Source Doc | Stories | Effort | Notes |
|---|------|-----------|---------|--------|-------|
| 58 | **Frontend Test Quality** | [frontend-testing-epics.md](../docs/planning/frontend-testing-epics.md) Epic 54→58 | 6 | 1 week | A11y sweep, dark mode sweep, error boundaries, testing standards |
| 59 | **Frontend Integration & E2E** | [frontend-testing-epics.md](../docs/planning/frontend-testing-epics.md) Epic 55→59 | 6 | 2 weeks | Cross-component flows, E2E smoke, performance baselines, visual regression |
| — | **Bundle Optimization** | [frontend-epics-roadmap.md](../docs/planning/frontend-epics-roadmap.md) Epic 3 | 6 | 2-3 weeks | Code splitting, lazy loading, bundle size monitoring |

### P2 — Deferred / After Stability Window

| # | Epic | Source Doc | Stories | Effort | Notes |
|---|------|-----------|---------|--------|-------|
| — | **Phase 3: ML/AI Library Upgrades** | [phase-3-plan-ml-ai-upgrades.md](../docs/planning/phase-3-plan-ml-ai-upgrades.md) | ~20 | 3-4 weeks | HIGH RISK: NumPy 2.x, Pandas 3.0. Wait 3 weeks post-Phase 5. Epic 38 already handled transformers/openvino/sentence-transformers. |

### P3 — Backlog

| # | Epic | Source Doc | Stories | Effort | Notes |
|---|------|-----------|---------|--------|-------|
| — | **Auto-Bugfix Bash Parity** | [auto-bugfix-streaming-dashboard-prd.md](../docs/planning/auto-bugfix-streaming-dashboard-prd.md) Epic 4 | 3 | 1 week | Bash stream parser for Linux/macOS |
| — | **Auto-Bugfix Test/Reliability** | [auto-bugfix-streaming-dashboard-prd.md](../docs/planning/auto-bugfix-streaming-dashboard-prd.md) Epic 5 | 3 | 1 week | Dry-run mode, error resilience, stream recording |

### Epic 57: Cleanup & Gaps — COMPLETE (Mar 13)

**Priority:** P1 | **Effort:** 1-2 days | **Dependencies:** None | **Status:** COMPLETE (4/4)

| Story | Description | Status |
|-------|-------------|--------|
| 57.1 | Fix 3 enhancement-button E2E failures | **DONE** — tool_calls JSON column + ORM + persistence + API response + frontend mapping (7 files) |
| 57.2 | Fix 2 RAG fixme tests in health-dashboard | **DONE** — data-testid="rag-status-card" + data-rag-state added to loading/unavailable paths |
| 57.3 | ~~Wire `entity_extractor` in ai-query-service~~ | **ALREADY DONE** — EntityExtractor() at query_router.py:54. No code change needed. |
| 57.4 | Add pre-commit secret scanning hook | **DONE** — `no-secrets` hook in .pre-commit-config.yaml + scripts/check-secrets.py (5 patterns) |

### Epic 60: Chat Endpoint Complexity Refactor — COMPLETE (Mar 13)

**Priority:** P1 | **Effort:** 1 session | **Dependencies:** None | **Status:** COMPLETE (3/3)

| Story | Description | Status |
|-------|-------------|--------|
| 60.1 | **Extract tool execution into helper module** — `safe_parse_tool_arguments`, `process_tool_result`, `execute_tool_calls` moved to `tool_execution.py` (254 lines) | **DONE** |
| 60.2 | **Extract OpenAI loop into helper** — `_run_openai_loop()` returns `LoopResult` dataclass. `chat()` is now: setup → loop → build response (721→481 lines) | **DONE** |
| 60.3 | **Fix remaining lint issues** — f-string logging → `%s` format, `# noqa: B008` for FastAPI Depends, long lines fixed | **DONE** |

### Archived (Verified Complete / Resolved)

These items were previously listed as open but are now confirmed done:

| Item | Resolution |
|------|-----------|
| ~~Tailwind CSS 4 Migration~~ | Already done in Sprint 4 — `tailwindcss ^4.0.0` + `@theme` in CSS |
| ~~Streamlit Performance (time.sleep)~~ | Already fixed — `st.fragment` with `run_every` in `real_time_monitoring.py` |
| ~~Frontend Security Hardening (roadmap Epic 1)~~ | Largely covered by completed Epic 1 (6 stories). Only gap = pre-commit hook (→ Story 57.4) |
| ~~Frontend Test Infra (old "Epic 50")~~ | Delivered by Epic 42 — coverage config, pytest for obs-dashboard, 25 failures fixed |
| ~~HD Critical Path Testing (old "Epic 51")~~ | Delivered by Epic 43 — 268 tests, 30 files |
| ~~AI UI Critical Path Testing (old "Epic 52")~~ | Delivered by Epic 44 — 285 tests, 22 files |
| ~~Obs Dashboard Full Suite (old "Epic 53")~~ | Delivered by Epic 45 — 109 tests, 8 files, 57% coverage (exceeds 70% target for pure logic) |
| ~~AI_CORE_API_KEY missing~~ | Set in `.env` — resolved |
| ~~Frontend Epics Roadmap Epic 5 (Testing)~~ | Superseded by frontend-testing-epics.md, itself now largely delivered by Epics 42-45 |

---

## Epic Summary

| # | Epic | File | Priority | Stories | Duration | Status |
|---|------|------|----------|---------|----------|--------|
| 0 | [SQLite Removal](epic-sqlite-removal.md) | `epic-sqlite-removal.md` | **P0 Critical** | 10 | 3-5 days | **Complete** |
| 1 | [Frontend Security Hardening](epic-frontend-security-hardening.md) | `epic-frontend-security-hardening.md` | **P0 Critical** | 6 | 3-5 days | **Complete** |
| 2 | [Health Dashboard Quality](epic-health-dashboard-quality.md) | `epic-health-dashboard-quality.md` | P1 High | 8 | 2-3 weeks | **Complete** |
| 3 | [AI Automation UI Quality](epic-ai-automation-ui-quality.md) | `epic-ai-automation-ui-quality.md` | P1 High | 8 | 2-3 weeks | **Complete** |
| 4 | [Observability Dashboard Fixes](epic-observability-dashboard-fixes.md) | `epic-observability-dashboard-fixes.md` | P1 High | 8 | 1-2 weeks | **Complete** |
| 5 | [Frontend Framework Upgrades](epic-frontend-framework-upgrades.md) | `epic-frontend-framework-upgrades.md` | P2 Medium | 5 | 3-4 weeks | **Complete** (Vite 7 + Tailwind 4, builds pass) |
| 6 | [Backend Completion](epic-backend-completion.md) | `epic-backend-completion.md` | P1 High | 7 | 2-3 weeks | **Complete** |
| 7 | [Feature Gaps](epic-feature-gaps.md) | `epic-feature-gaps.md` | P2 Medium | 6 | 4-6 weeks | **Complete** |
| 8 | [Production Deployment](epic-production-deployment.md) | `epic-production-deployment.md` | P1 High | 8 | 2 weeks | **Complete** (scripts ready) |
| 9 | [TAPPS Quality Gate Compliance](epic-tapps-quality-gate-compliance.md) | `epic-tapps-quality-gate-compliance.md` | P1 High | 3 | 1 week | **Complete** |
| 10 | [Browser Review – AI Automation UI](epic-browser-review-ai-automation-ui.md) | `epic-browser-review-ai-automation-ui.md` | P1 High | 4 | 2-3 weeks | **Complete** |
| 11 | [Browser Review – Health Dashboard](epic-browser-review-health-dashboard.md) | `epic-browser-review-health-dashboard.md` | P1 High | 5 | 2-3 weeks | **Complete** |
| 12 | [Core Service Bootstrap Standardization](epic-core-service-bootstrap-standardization.md) | `epic-core-service-bootstrap-standardization.md` | P1 High | 4 | 3-4 weeks | **Complete** (5 POC services migrated) |
| 13 | [External Service Connector Standardization](epic-external-service-connector-standardization.md) | `epic-external-service-connector-standardization.md` | P1 High | 4 | 2-3 weeks | **Complete** (libs created + tested) |
| 14 | [Background Processing Standardization](epic-background-processing-standardization.md) | `epic-background-processing-standardization.md` | P2 Medium | 2 | 1-2 weeks | **Complete** (libs created + tested) |
| 15 | [TAPPS Tracking by Service](epic-tapps-tracking-by-service.md) | `epic-tapps-tracking-by-service.md` | P1 High | 12 | 3-4 weeks | **Complete** (53 scored, 45% pass) |
| 16 | [Project-Wide Lint Cleanup](epic-project-wide-lint-cleanup.md) | `epic-project-wide-lint-cleanup.md` | P1 High | 7 | 1-2 weeks | **Complete** (1571 violations, 870+ files) |
| 17 | [Tier 1 Quality Hardening](epic-tier1-quality-hardening.md) | `epic-tier1-quality-hardening.md` | **P0 Critical** | 4 | 2-3 weeks | **Complete** (3/3 strict 80+) |
| 18 | [Data Collectors Remediation](epic-data-collectors-remediation.md) | `epic-data-collectors-remediation.md` | P1 High | 7 | 2-3 weeks | **Complete** (8/8 pass 70+) |
| 19 | [Low-Score Service Remediation](epic-low-score-remediation.md) | `epic-low-score-remediation.md` | P1 High | 7 | 2-3 weeks | **Complete** (8/8 pass 70+) |
| 20 | [Shared Library Strict Compliance](epic-shared-library-strict-compliance.md) | `epic-shared-library-strict-compliance.md` | P1 High | 6 | 1-2 weeks | **Complete** (5/5 strict 80+) |
| 21 | [Per-Domain Docker Desktop Isolation](epic-per-domain-docker-isolation.md) | `epic-per-domain-docker-isolation.md` | P1 High | 5 | 1 week | **Complete** |
| 22 | [Cross-Domain Shared Resource Decoupling](epic-cross-domain-volume-decoupling.md) | `epic-cross-domain-volume-decoupling.md` | P1 High | 3 | 1 week | **Complete** |
| 23 | [Dockerfile Security & Consistency Hardening](epic-dockerfile-hardening.md) | `epic-dockerfile-hardening.md` | P1 High | 8 | 1 week | **Complete** |
| 24 | [Domain Deployment Tooling](epic-domain-deployment-tooling.md) | `epic-domain-deployment-tooling.md` | P1 High | 5 | 1 week | **Complete** |
| 25 | [Direct Device Control](epic-sapphire-ha-integration.md) | `epic-sapphire-ha-integration.md` | P1 High | 7 | 2 weeks | **Complete** |
| 26 | [Voice Gateway Service](epic-sapphire-ha-integration.md) | `epic-sapphire-ha-integration.md` | P1 High | 6 | 2-3 weeks | **Complete** |
| 27 | [Scheduled AI Tasks](epic-sapphire-ha-integration.md) | `epic-sapphire-ha-integration.md` | P2 Medium | 5 | 1-2 weeks | **Complete** |
| 28 | [Enhanced Event Bus](epic-sapphire-ha-integration.md) | `epic-sapphire-ha-integration.md` | P2 Medium | 4 | 1 week | **Complete** |
| 29 | [Memory Store Foundation](epic-memory-brain.md) | `epic-memory-brain.md` | **P0 Critical** | 6 | 2 weeks | **Complete** (homeiq-memory lib, 14 files) |
| 30 | [Explicit Memory Capture](epic-memory-brain.md) | `epic-memory-brain.md` | P1 High | 4 | 1-2 weeks | **Complete** (chat + approval extraction) |
| 31 | [Implicit Memory Capture](epic-memory-brain.md) | `epic-memory-brain.md` | P1 High | 4 | 1-2 weeks | **Complete** (override + engagement tracking) |
| 32 | [Synthesized Memory](epic-memory-brain.md) | `epic-memory-brain.md` | P1 High | 5 | 1-2 weeks | **Complete** (consolidation job + routines) |
| 33 | [Memory Injection](epic-memory-brain.md) | `epic-memory-brain.md` | P1 High | 5 | 1-2 weeks | **Complete** (4 AI services integrated) |
| 34 | [Trust Model & Adaptive UX](epic-memory-brain.md) | `epic-memory-brain.md` | P2 Medium | 3 | 1 week | **Complete** (API + dashboard widget) |
| 35 | [Memory Lifecycle & Observability](epic-memory-brain.md) | `epic-memory-brain.md` | P2 Medium | 4 | 1 week | **Complete** (admin API, dashboard, self-heal) |
| 36 | [E2E Playwright Test Remediation](epic-e2e-playwright-test-remediation.md) | `epic-e2e-playwright-test-remediation.md` | P1 High | 10 | 1 day | **Complete** (36→0 failures, 160/167 pass) |
| 37 | [Pattern Detection Expansion](epic-pattern-detection-expansion.md) | `epic-pattern-detection-expansion.md` | P1 High | 10 | 2-3 weeks | **Complete** (10/10: 8 detectors + integration) |
| 38 | [ML Dependencies Upgrade](epic-ml-dependencies-upgrade.md) | `epic-ml-dependencies-upgrade.md` | P2 Medium | 8 | 1-2 weeks | **Complete** (7/8, 1 skipped) |
| 39 | [React 19 Migration](epic-react19-migration.md) | `epic-react19-migration.md` | P2 Medium | 6 | 2-3 weeks | **Complete** |
| 40 | [Pattern Detection ML Upgrade](epic-pattern-detection-ml-upgrade.md) | `epic-pattern-detection-ml-upgrade.md` | P2 Medium | 8 | 3-4 weeks | **Complete** |
| 41 | [Memory Brain Quality Tuning](epic-memory-brain-tuning.md) | `epic-memory-brain-tuning.md` | P2 Medium | 7 | 2 weeks | **Complete** |
| 42 | [Frontend Test Infrastructure](epic-frontend-test-infrastructure.md) | `epic-frontend-test-infrastructure.md` | **P0 Critical** | 5 | 1 week | **Complete** (25 failures fixed, coverage config) |
| 43 | [Health Dashboard Testing](epic-health-dashboard-testing.md) | `epic-health-dashboard-testing.md` | **P0 Critical** | 8 | 2 weeks | **Complete** (268 tests, 30 files) |
| 44 | [AI Automation UI Testing](epic-ai-automation-ui-testing.md) | `epic-ai-automation-ui-testing.md` | **P0 Critical** | 8 | 2 weeks | **Complete** (285 tests, 22 files) |
| 45 | [Observability Dashboard Testing](epic-observability-dashboard-testing.md) | `epic-observability-dashboard-testing.md` | P1 High | 4 | 1 week | **Complete** (109 tests, 8 files) |
| 46 | [Auto-Bugfix Scan Robustness & Tests](epic-auto-bugfix-robustness-and-tests.md) | `epic-auto-bugfix-robustness-and-tests.md` | P1 High | 5 | 1-2 weeks | **Complete** |
| 47 | [Auto-Bugfix Dashboard Real-Time Updates](../docs/planning/auto-bugfix-dashboard-realtime-epic.md) | `docs/planning/auto-bugfix-dashboard-realtime-epic.md` | P1 High | 7 | 1-2 weeks | **Complete** (7/7: live usage, atomic writes, 800ms polling, file:// fallback) |
| 48 | [Auto-Bugfix Subagents Integration](epic-auto-bugfix-subagents-integration.md) | `epic-auto-bugfix-subagents-integration.md` | P1 High | 5 | 1-2 weeks | **Complete** |
| 49 | [E2E Playwright Coverage Expansion](epic-e2e-playwright-coverage-expansion.md) | `epic-e2e-playwright-coverage-expansion.md` | P1 High | 13 | 2-3 weeks | **Complete** (13/13: aligned, mocked, tested, matrix) |
| 50 | [Auto-Fix Isolated Project — Structure Setup](epic-50-auto-fix-isolated-project-structure.md) | `epic-50-auto-fix-isolated-project-structure.md` | P1 High | 7 | 1 day | **Complete** |
| 51 | [E2E Skipped Tests — Fix or Delete](epic-51-e2e-skipped-tests.md) | `epic-51-e2e-skipped-tests.md` | P1 High | 12 | 1–2 weeks | **Complete** (0 skipped). Follow-up → Epic 57. |
| 52 | [Auto-Bugfix Cleanup — Delete Legacy, Keep Config-Driven](epic-auto-bugfix-cleanup-legacy.md) | `epic-auto-bugfix-cleanup-legacy.md` | P1 High | 6 | 2-3 days | **Complete** (config verified, scripts assessed, docs updated) |
| 53 | [Ask AI Integration Validation](epic-53-ask-ai-integration-validation.md) | `epic-53-ask-ai-integration-validation.md` | P1 High | 4 | 1-2 weeks | **Complete** (schema doc, HA helper, full-flow test, CI=local) |
| 54 | Consolidation Sprint | N/A | P1 High | 6 | 1 day | **Complete** (commit 64f5f85c) |
| 55 | Production Hardening | N/A | P1 High | 6 | 1 day | **Complete** (commit 0df0ae6e) |
| 56 | Observability & Monitoring Hardening | N/A | P1 High | 6 | 1 day | **Complete** (commit cd0ffc32) |
| 57 | Cleanup & Gaps | *(this file)* | P1 High | 4 | 1-2 days | **Complete** (4/4: tool_calls persistence, RAG card data-testid, entity_extractor verified, secret scanning hook) |
| 60 | Chat Endpoint Complexity Refactor | *(this file)* | P1 High | 3 | 1 session | **Complete** (3/3: tool_execution.py extracted, _run_openai_loop helper, lint fixes) |

## Story Count by Priority

| Priority | Count | Description |
|----------|-------|-------------|
| P0 Critical | 49 | DB migration (10) + Security (6) + Tier 1 hardening (4) + Memory Foundation (6) + Embed Testing (2) + Frontend Test Infra (5) + HD Testing (8) + AI UI Testing (8) |
| P1 High | 142 | Quality, testing, deployment, browser review, TAPPS, Docker, Memory (18), Pattern Detection (10), React 19 (3), ML Feedback (1), Memory Metrics (2), Obs Dashboard Testing (4) |
| P2 Medium | 53 | Framework upgrades, feature integrations, Trust model (7), ML Upgrades (8), React Compiler (2), ML Models (5), Memory Tuning (4) |
| P3 Low | 10 | ML model training, placeholder implementations, Seasonal/Frequency detectors (3), Prophet (1), Pattern Fusion (1), Memory Dashboard (1) |
| **Total** | **364** | 364 complete (58 epics). See **Open Work** section for planned epics. |

## Key Dates

| Date | Milestone |
|------|-----------|
| Feb 27 | Sprint 0 complete — SQLite fully removed, PostgreSQL is sole database |
| Mar 3 | Sprint 1.5 complete — 15 epics done, TAPPS baseline captured |
| Mar 4 | Sprints 2-6 complete — 19 epics via agent teams (quality, Docker, services, voice, device control) |
| Mar 6 | Sprint 7 complete — Epics 29-35 (Memory Brain), homeiq-memory lib + 8 service integrations |
| Mar 7 | Sprint 8 complete — Epic 37 (10/10) + Epic 38 (7/8), pattern detection + ML deps |
| Mar 6 | Production redeployed — 51/51 containers healthy |
| Mar 10 | Sprint 10 complete — Epics 42-45 (Frontend Testing), 662 tests, 60 test files |
| Mar 12 | Sprint 19 complete — Epics 54-56 (Consolidation + Production Hardening + Observability) |
| Mar 13 | Epic 57 complete (4/4: tool_calls, RAG testid, entity_extractor, secret scanning). Phase 5 plan refreshed (44+ health endpoints, 1366+ tests). Epic 60 complete (chat_endpoints refactor: 721→481+254 lines). |

> **Detailed sprint results:** [SPRINT-HISTORY.md](SPRINT-HISTORY.md)

## Superseded Epics

> **Epics 56 and 57** from `docs/planning/epic-56-57-pattern-detectors-ml-upgrade.md` are **SUPERSEDED**.
> Epic 56 (Advanced Pattern Detection Framework) was fully delivered by Epic 37 (Sprint 8, Mar 7, 2026).
> Epic 57 (ML Stack Modernization) was mostly delivered by Epic 38 (Sprint 8, Mar 7, 2026).
> The remaining gap (Story 57.6: ML Dependency Alignment Audit) is addressed by Epic 54, Story 54.4.
>
> **Frontend Testing Epics "50-55"** from `frontend-testing-epics.md` are **SUPERSEDED / RENUMBERED**:
> - Old "Epic 50" (Test Infra) → delivered by Epic 42
> - Old "Epic 51" (HD Testing) → delivered by Epic 43
> - Old "Epic 52" (AI UI Testing) → delivered by Epic 44
> - Old "Epic 53" (Obs Dashboard) → delivered by Epic 45
> - Old "Epic 54" (Test Quality) → renumbered to **Epic 58**
> - Old "Epic 55" (Integration & E2E) → renumbered to **Epic 59**
