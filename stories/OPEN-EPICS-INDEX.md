# HomeIQ — Open Epics & Stories Index

**Created:** 2026-02-27 | **Updated:** 2026-03-19 (Epic 97 complete, Epics 93+94+97 committed)
**Total:** 93 Completed Epics, 609 Stories complete | 3 Closed/Archived | 4 Planned (1 P1, 1 P2, 2 P3)

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

Sprint 22 (COMPLETE — Mar 13, 2026) — Frontend Test Quality
└── Epic 58: Frontend Test Quality [P1]                       ← COMPLETE (6/6 stories)
    └── TESTING_STANDARDS.md, error boundary tests (4), skeleton tests (2), a11y sweep (8 files), dark mode sweep, MSW expansion

Sprint 23 (COMPLETE — Mar 13, 2026) — Phase 5 Deployment + Frontend E2E
├── Epic 61: Phase 5 Production Deployment Execution [P0]     ← COMPLETE (6/6 stories)
│   └── Script updates, pre-deployment validation, 9-tier staged rollout, post-deployment validation (852 tests passing)
└── Epic 59: Frontend Integration & E2E [P1]                  ← COMPLETE (6/6 stories)
    └── 27 integration tests (HD + AI UI), E2E smoke, cross-app nav, perf baselines, visual regression

Sprint 24 (COMPLETE — Mar 14, 2026) — HA Setup Wizard UI
└── Epic 63: HA Setup Wizard & Entity Management UI [P1]      ← COMPLETE (7/7 stories)
    └── HASetupTab (lazy-loaded), EntityAuditView with scoring, LabelEditor, AliasEditor, NameEditor, ExclusionManager, BulkActionsBar + QuickActions

Sprint 25 (COMPLETE — Mar 16, 2026) — Bundle Optimization
└── Epic 65: Bundle Optimization [P1]                          ← COMPLETE (6/6 stories)
    └── AI UI: index 966→218 KB (-77%), 8 lazy routes, force-graph deferred. HD: visualizer added. CI bundle check script.

Sprint 26 (COMPLETE — Mar 16, 2026) — AI Classification + Validation Loop
├── Epic 66: AI/Agent Service Classification [P1]              ← COMPLETE (5/5 stories)
│   └── 4-tier classification (T1-T4) of all 51 services, ADR single-agent, Mermaid decision tree, cross-refs, HD badges
└── Epic 67: AI Automation Validation Loop [P1]                ← COMPLETE (6/6 stories)
    └── LinterClient + ValidationRetryLoop (max 3 attempts), error-feedback prompt, CircuitBreaker, metrics, 10 tests

Sprint 27 (COMPLETE — Mar 16, 2026) — Autonomous Agent + Self-Improving Agent
├── Epic 68: Proactive Agent — Autonomous Upgrade [P1]         ← COMPLETE (8/8 stories)
│   └── Observe-reason-act loop, Memory Brain preference recall, confidence/risk scoring, autonomous execution via ha-device-control, feedback loop, safety guardrails, audit trail + undo, 20 tests
└── Epic 70: Self-Improving Agent (Hermes) [P1]                ← COMPLETE (8/8 stories)
    └── Smart model routing (gpt-4.1-mini/gpt-5.2-codex), skill learning + skills guard (100+ threat patterns), context compression, subagent delegation (max 3 parallel), session search, user modeling, prompt caching, 30+ tests

Sprint 28 (COMPLETE — Mar 16, 2026) — Convention Compliance + Eval Feedback Loop
├── Epic 64: Convention Compliance & Auto-Enhancement [P2]     ← COMPLETE (6/6 stories)
│   └── Score engine (100-point scale, 6 rules), auto-alias generator (5 strategies), compliance dashboard widget, name suggestions, discovery sync (aliases+labels flow-through), chat naming hints
└── Epic 69: Agent Eval Feedback Loop [P2]                     ← COMPLETE (7/7 stories)
    └── Complexity classifier (5-factor), adaptive model router (eval-score auto-upgrade), eval-routing correlation, degradation alerting (>10% drop / floor breach), regression investigator, cost tracker + savings, admin config + model lock

Sprint 29 (COMPLETE — Mar 16, 2026) — 2026 Release: ML/AI Library Upgrades
└── Epic 71: ML/AI Library Upgrades (Phase 3) [P2]             ← COMPLETE (8/8 stories)
    └── NumPy 2.4.3, Pandas 3.0.1, scikit-learn 1.8.0, SciPy 1.17.1, OpenAI 2.28.0, joblib 1.5.3. 8 services updated, 27 files audited, zero deprecated APIs, PyArrow added for Pandas 3.0

Sprint 34 (COMPLETE — Mar 16, 2026) — P1 Blockers + Integration Tests + Production Alerting
├── Blocker Fixes [P1]                                          ← COMPLETE
│   ├── Playwright dual-version conflict — aligned root + tests/e2e to @playwright/test@1.58.2
│   └── tests/shared/ import paths — fixed 10 files, conftest.py → libs/*/src, bare imports → package-qualified
├── Epic 78: Cross-Service Integration Tests [P1]               ← COMPLETE (6/6 stories, 24 new tests)
│   ├── 78.1 Tier 1 data flow chain (InfluxDB write/query, DataAPIClient, bearer auth, retry, roundtrip)
│   ├── 78.2 Zeek pipeline (conn.log, dns.log parsers, fingerprint PG schema, anomaly lifecycle, health)
│   ├── 78.3 Agent chains (CrossGroupClient retry, CircuitBreaker, confidence scoring, auth propagation, safety guardrails)
│   ├── 78.4 Memory Brain (save/search, semantic relevance, decay tiers, consolidation, domain scoping)
│   ├── 78.5 Cross-group auth (invalid token rejection, valid token acceptance, header injection)
│   └── 78.6 CI updates (4 new GitHub Actions jobs, workflow_dispatch)
└── Epic 79: Production Alerting & SLA Monitoring [P1]          ← COMPLETE (6/6 stories)
    ├── 79.1 SLA recording rules (availability, latency p95/p99, error rate, error budget per tier)
    ├── 79.2 SLA alert rules (8 rules: tier breaches, latency, error budget burn rate)
    ├── 79.3 AlertManager (v0.28.1 container, 3 receivers, inhibition rules, Prometheus integration)
    ├── 79.4 Grafana SLA dashboard (availability gauges, error budget, latency heatmap, active alerts)
    ├── 79.5 Zeek security alerts (8 rules: new device, beaconing, DGA, weak TLS, expired cert, rogue MQTT)
    └── 79.6 Admin API webhook (AlertStore with 15-min TTL, /api/alerts/webhook + /active + /active/count)
```

Sprint 35 (COMPLETE — Mar 16, 2026) — Security Hardening + Test Coverage
├── aiohttp CVE remediation [P0]                                  ← COMPLETE (40 files: >=3.9.0 → >=3.13.3, fixes 8 CVEs)
├── npm CVE fix [P0]                                              ← COMPLETE (basic-ftp path traversal GHSA-5rq4-664w-9x2c)
└── Epic 80: Data-API Test Coverage & Security Hardening [P1]     ← COMPLETE (12/12 stories, 345 new tests)
    ├── Phase 1: 80.1 auth.py (55), 80.2 database.py (27), 80.3 api_key_service.py (60) — 158 tests
    ├── Phase 2-4: 80.4 devices (29), 80.5 events (16), 80.6 health (16), 80.7 alerts (19) — 80 tests
    │   80.8 entity_registry (13), 80.9 device_classifier (14), 80.11 cache/config (12), 80.12 integration (10) — 49 tests
    └── Phase 5: 80.10 remaining endpoints: automation, jobs, config, eval, metrics, energy, sports, activity, analytics (53) — 53 tests
    + websocket-ingestion _startup.py (16 tests: 3 startup phases, graceful failure)
    + conftest.py fixes (admin-api, websocket-ingestion, data-api path_setup loader)

Sprint 36 (COMPLETE — Mar 16, 2026) — Docker Rebuild & Zeek Hardening
├── Epic 81: Docker Rebuild & Deploy — aiohttp CVE [P0]              ← COMPLETE (5/5 stories)
│   └── 58/58 containers healthy, aiohttp 3.13.3 verified across all images, postgres-exporter PG17 fix, Zeek 8.1.1 compat
└── Epic 82: Zeek Container Docker Healthcheck [P1]                  ← COMPLETE (5/5 stories)
    └── healthcheck.sh (process+log freshness check), regression tested, 58/58 containers healthy

Sprint 37 (COMPLETE — Mar 17, 2026) — Data-API Route Coverage Expansion
└── Epic 83: Data-API HTTP Route Coverage Expansion [P1]             ← COMPLETE (11/11 stories)
    └── 186 tests (167 pass, 19 need PG), 5 pre-existing bugs documented, route shadowing discovered

Sprint 38 (COMPLETE — Mar 18, 2026) — Data-API Unit Coverage + E2E Selector Remediation
├── Epic 85: Data-API Unit & Line Coverage Expansion [P1]              ← COMPLETE (10/10 stories)
│   └── 443 new unit tests across 20 test files, line coverage 8.8% → 40%+
└── Epic 84: E2E Stale Selector Remediation [P2]                       ← COMPLETE (11/11 stories)
    └── 169+ stale selectors remediated across 15 E2E files

Sprint 39 (COMPLETE — Mar 18, 2026) — Zeek Native Telemetry & Capture Health
└── Epic 86: Zeek 8.x Native Telemetry & Capture Health Dashboard [P2] ← COMPLETE (7/7 stories)
    └── Zeek telemetry on :9911, Prometheus scrape, 6 recording rules, 4 alert rules, Grafana dashboard

Sprint 40 (COMPLETE — Mar 18, 2026) — E2E Stability, CVE Hardening, Data-API Coverage
├── Epic 87: Data-API Coverage Expansion Phase 2 [P2]                     ← COMPLETE (6/6 stories)
├── Epic 88: Dependency CVE Sweep & Hardening [P2]                        ← COMPLETE (4/4 stories)
└── Epic 89: E2E Test Stability & Green CI [P2]                           ← COMPLETE (5/5 stories)

Sprint 41 (COMPLETE — Mar 18, 2026) — Ask AI → HA YAML E2E Pipeline
└── Epic 90: Ask AI → HA YAML E2E Pipeline [P1]                          ← COMPLETE (10/10 stories)
    └── 7 backend integration tests + 14 YAML-asserted E2E tests + 107 blueprint service tests + CI workflow + cleanup harness + docs
```

---

## Open Work — Planned Epics (Not Yet Started)

> These epics are defined in planning docs but have **no commits yet**.
> They are listed in recommended execution order.
> Next available epic number: **99** (92 epics complete, 76-77 closed won't-do, 91-92/95-98 planned).
> **Priority review:** 2026-03-19 — restacked based on safety impact, cost ROI, dependencies.

### P0 — Complete

| # | Epic | Stories | Effort | Sprint | Notes |
|---|------|---------|--------|--------|-------|
| 93 | **Entity Safety Blacklisting** | 5 | 2 days | 43 | ✅ **COMPLETE** — Defence-in-depth: `entity_blacklist.yaml` config + `EntityBlacklist` class, context filtering in `enhanced_context_builder.py`, validation rejection in `yaml-validation-service` Stage 5 (errors not warnings), system prompt updated (blocked not warned), admin override via env var + `X-Safety-Override` header, docs + 44 tests. |

### P1 — Planned

| # | Epic | Stories | Effort | Sprint | Notes |
|---|------|---------|--------|--------|-------|
| 94 | **Prompt Sections to Config Files** | 5 | 3-4 days | 43 | ✅ **COMPLETE** — 13 section files extracted from 1033-line SYSTEM_PROMPT, YAML config with ordering/enable/disable, PromptLoader class with variable substitution ({ha_version} etc.), env var overrides (PROMPT_VAR_*), graceful fallback to constant, 21 tests (byte-identical regression, ordering, disabled sections, variables, token budget), PROMPT_ASSEMBLY.md docs. |
| 97 | **Prompt Caching & Claude Provider** | 6 | 1-2 weeks | 44 | ✅ **COMPLETE** — AnthropicLLMClient with cache_control breakpoints (2 cache BPs: system prompt + entity context), LLMRouter with CircuitBreaker fallback, bidirectional tool schema translator (OpenAI↔Anthropic), extended thinking for complex automations, LLMResponse dataclass, provider selection wired into chat handler (LLM_PROVIDER=anthropic activates), benchmark script, 54 tests. |
| 95 | **Consume HA MCP Servers** | 7 | 1-2 weeks | 45 | Replace custom HomeAssistantClient with MCP protocol. MCPClient infra, HA MCP server evaluation, adapter, shadow mode, switchover, Docker deploy, data-collector audit. Demoted from P0: current client works, MCP is modernization not a fix. |

### P2 — Planned

| # | Epic | Stories | Effort | Sprint | Notes |
|---|------|---------|--------|--------|-------|
| 96 | **Proactive Predictive Automation** | 8 | 2-3 weeks | 46+ | Wire existing services (proactive-agent, energy-forecasting, activity-recognition) for pattern detection, energy optimization, anomaly alerts. 2026 differentiator. Demoted from P1: high value but largest effort, no dependencies blocked. |
| ~~98~~ | ~~Local LLM Fallback via Ollama~~ | — | — | — | **Archived 2026-03-19.** See Closed — Won't Do. |

### P3 — Backlog

| # | Epic | Stories | Effort | Notes |
|---|------|---------|--------|-------|
| 92 | **Live AI E2E Tests — 0% to 100% Pass Rate** | 10 | 1-2 weeks | Local-only E2E already passing (19/19, commit a6bbce96). Live CI tests are nice-to-have. Root causes documented. Defer until after feature epics. |
| 91 | **Memory Consolidation Research — TappsMCP vs homeiq-memory** | 6 | 1-2 weeks | Pure research — homeiq-memory works fine at runtime, TappsMCP serves dev-time scope. No user-facing impact. Defer. |

### In Progress

> No epics currently in progress.

### P1 — All Complete

> Epics 85-86 completed Mar 18. Epic 89 (E2E Stability) completed Mar 18. Epic 90 (Ask AI YAML E2E Pipeline) completed Mar 18.

### P2 — All Complete

> Epic 84 (E2E Stale Selector Remediation) completed Mar 18. All P2 complete through Epic 89.

### Closed — Won't Do

| # | Epic | Decision | Date | Rationale |
|---|------|----------|------|-----------|
| 76 | **Auto-Bugfix Bash Parity** | **Closed — Won't Do** | 2026-03-18 | `auto-bugfix.sh` is a thin wrapper that delegates to PowerShell; `pwsh` is available on Linux/macOS. Native bash JSON stream parsing (jq/python3) would double maintenance burden for near-zero audience. If Linux-native is ever needed, a Python CLI wrapper is the better path. |
| 77 | **Auto-Bugfix Test/Reliability** | **Closed — Won't Do** | 2026-03-18 | Dry-run mode has limited ROI (pipeline already supports `--bugs 1`). Error resilience only matters if Epic 76 ships. Stream recording (Story 5.3) was the only high-value item — extracted into Epic 87 Story 87.3. |
| 98 | **Local LLM Fallback via Ollama** | **Archived** | 2026-03-19 | Epic 97 delivered Claude as a second provider with circuit-breaker fallback — two cloud providers cover resilience needs. Local Ollama adds operational complexity (7B model quality, GPU requirements, prompt simplification) for marginal outage coverage. Revisit only if dual-cloud proves insufficient. |

### P2 — Next Up (Higher-Value Alternatives)

> Freed ~2 weeks of effort from Epics 76-77 redirected to production risk reduction.

| # | Epic | Stories | Effort | Notes |
|---|------|---------|--------|-------|
| 87 | **Data-API Coverage Expansion Phase 2** | 6 | 1-2 weeks | Push data-api from 40% → 60%+ line coverage. Focus: untested route handlers, error paths, edge cases. Includes stream recording extraction (Story 87.3 from Epic 77). |
| 88 | **Dependency CVE Sweep & Hardening** | 4 | 3-5 days | Full dependency scan across 75 requirements files. Pin vulnerable transitive deps. Audit dev-tool CVEs (black, pip, wheel). |
| 89 | **E2E Test Stability & Green CI** | 5 | 1 week | Post-Epic 84 follow-up. Fix 4 AI UI failures + flaky tests, increase Ask AI timeouts, establish green-CI baseline across 93 specs. |

### Epic 87: Data-API Coverage Expansion Phase 2 — COMPLETE (Mar 18)

**Priority:** P2 | **Effort:** 1 session | **Dependencies:** Epics 80/83/85 (complete) | **Status:** COMPLETE (6/6)
**Affects:** `domains/core-platform/data-api/` (tests/ and src/), `scripts/auto-bugfix-stream.ps1`
**Goal:** Push data-api line coverage from 40% → 60%+. Added 312 new unit tests covering 4 zero-coverage modules + memory consolidation + automation analytics.

| Story | Description | Status |
|-------|-------------|--------|
| 87.1 | **Docker service & endpoint tests** — Created `test_docker_service_unit.py` (69 tests) and `test_docker_endpoints_unit.py` (31 tests). 98% coverage of `docker_service.py`, 93% of `docker_endpoints.py`. | COMPLETE |
| 87.2 | **Metrics & hygiene endpoint tests** — Created `test_metrics_endpoints_unit.py` (21 tests) and `test_hygiene_endpoints_unit.py` (31 tests). Full coverage of both modules. | COMPLETE |
| 87.3 | **Auto-bugfix stream recording** — Added 7-day auto-cleanup to `auto-bugfix-stream.ps1`. Stream logging and .gitignore already existed. | COMPLETE |
| 87.4 | **Memory consolidation deep coverage** — Created `test_memory_consolidation_unit.py` (117 tests). 82% coverage of `jobs/memory_consolidation.py` (1,366 lines). Covers override detection, pattern detection, drift, routine synthesis, metrics history. | COMPLETE |
| 87.5 | **Automation analytics expansion** — Created `test_automation_analytics_unit.py` (43 tests). 100% coverage of `automation_analytics_endpoints.py`. All sort/filter/pagination paths tested. | COMPLETE |
| 87.6 | **Coverage gate & CI integration** — Added `--cov-fail-under=60` to pytest.ini addopts. Coverage gate enforced on every test run. | COMPLETE |

### Epic 88: Dependency CVE Sweep & Hardening — COMPLETE (Mar 18)

**Priority:** P2 | **Effort:** 1 session | **Dependencies:** Epic 81 (aiohttp CVE, complete) | **Status:** COMPLETE (4/4)
**Affects:** 81 requirements files across all 9 domains + 6 shared libs, `.pre-commit-config.yaml`
**Goal:** Full dependency audit, consolidate version pins, add pre-commit pip-audit hook, document unavoidable CVEs.

| Story | Description | Status |
|-------|-------------|--------|
| 88.1 | **Full dependency audit** — Audited all 81 requirements files and 6 pyproject.toml files. Found: 1 unbounded pydantic, 4 unbounded FastAPI, 7 overly-broad pydantic-settings, FastAPI/Pydantic version spreads. aiohttp already fixed (Epic 81). | COMPLETE |
| 88.2 | **Pin & upgrade vulnerable dependencies** — Fixed 12 files: 4 FastAPI unbounded → `<1.0.0`, 1 pydantic unbounded → `>=2.9.0,<3.0.0`, 7 pydantic-settings `>=2.0.0` → `>=2.6.0,<3.0.0`. | COMPLETE |
| 88.3 | **Add pip-audit pre-commit hook** — Added local `pip-audit-base` hook to `.pre-commit-config.yaml` that audits `requirements-base.txt` on changes. | COMPLETE |
| 88.4 | **Create KNOWN-VULNERABILITIES.md** — Created `docs/KNOWN-VULNERABILITIES.md` with: fixed CVEs (8 aiohttp + 12 pin fixes), dev-only CVEs (no fix, risk accepted), accepted version spreads, audit instructions, history. | COMPLETE |

### Epic 89: E2E Test Stability & Green CI — COMPLETE (Mar 18)

**Priority:** P2 | **Effort:** 1 session | **Dependencies:** Epic 84 (selector remediation, complete) | **Status:** COMPLETE (5/5)
**Affects:** `tests/e2e/` (93 spec files, 356+ tests), `.github/workflows/test.yml`, Playwright configs
**Goal:** All 93 E2E specs green in CI. Fix 4 known AI UI failures, resolve Ask AI timeouts, add flaky test quarantine, establish green baseline.

| Story | Description | Status |
|-------|-------------|--------|
| 89.1 | **Fix 4 AI UI test failures** — Fixed: ask-ai-mocked (replaced `.catch(() => {})` with `.or()` assertions), automation-creation (step 5 loose assertion replaced with proper `.or()` chain), enhancement-button (added mocked CI tests + increased live AI timeouts to 60s), blueprint-suggestions (replaced `expect(typeof x).toBe('boolean')` with real assertions). | COMPLETE |
| 89.2 | **Fix Ask AI timeout failures** — Increased AI Automation UI Playwright config timeout from 30s → 60s. Live AI tests (ask-ai-complete, ask-ai-to-ha-automation) already had 90-120s. Enhancement-button live tests bumped to 60s. | COMPLETE |
| 89.3 | **Add flaky test quarantine** — Created `FLAKY_TESTS.md` registry. Excluded `ask-ai-complete`, `ask-ai-to-ha-automation`, `ask-ai-debug` from main CI gate via `--ignore-pattern`. Live AI tests gated behind `AI_SERVICES_AVAILABLE=1`. | COMPLETE |
| 89.4 | **Visual regression stability** — Added `document.fonts.ready` wait to prevent woff2 flakiness. Pinned `maxDiffPixelRatio: 0.02` (2%) across all 27 screenshot assertions via `SNAPSHOT_OPTS` constant. | COMPLETE |
| 89.5 | **Green CI baseline & metrics** — Added pass-rate check step to CI (warns if < 95%). Added JSON reporter. Updated `tests/e2e/README.md` with test matrix table (93 specs, ~356 tests). | COMPLETE |

### Epic 90: Ask AI → HA YAML E2E Pipeline — COMPLETE (Mar 18)

**Priority:** P1 | **Effort:** 1 session | **Dependencies:** Epics 53, 84, 89 (all complete) | **Status:** COMPLETE (10/10)
**Affects:** `tests/e2e/`, `tests/integration/`, `domains/blueprints/`, `.github/workflows/`
**Goal:** End-to-end testing from Ask AI prompt → YAML generation → validation → HA deployment → YAML retrieval & structural verification. Un-quarantined live AI tests with reliability patterns. Added YAML content verification layer.

| Story | Description | Status |
|-------|-------------|--------|
| 90.1 | **Backend integration test: chat → YAML round-trip** — `tests/integration/test_ask_ai_yaml_pipeline.py` (7 tests). HTTP POST to `/api/v1/chat`, asserts `preview_automation_from_prompt` tool_call, parses YAML, validates trigger/action structure. 5 prompt categories: presence, time, device-state, multi-domain, scene. + 2 API contract tests. | COMPLETE |
| 90.2 | **YAML retrieval & structural validation helper** — `tests/e2e/helpers/yaml-validator.ts`. Exports: `fetchAndValidateAutomationYAML`, `assertTriggerPlatform`, `assertActionService`, `assertEntityIds`, `assertAutomationEnabled` + TypeScript interfaces for HA automation config. | COMPLETE |
| 90.3 | **Add YAML content assertions to E2E** — All 14 tests in `ask-ai-to-ha-automation.spec.ts` now call `fetchAndValidateAutomationYAML` after automation creation. Prompt-specific assertions: presence→state trigger, time→time trigger, scene→scene.turn_on, multi-domain→multiple action services. | COMPLETE |
| 90.4 | **Fix ask-ai-complete reliability** — Split 26 tests into Fast (4 UI-only, 30s) and Slow (22 OpenAI, 120s) groups. All `waitForToast` → 45-60s. `expect.poll()` for async state. `test.slow()` + retries=2 for OpenAI tests. | COMPLETE |
| 90.5 | **Test isolation & cleanup harness** — `tests/e2e/helpers/test-cleanup.ts`. `AutomationTracker` class with `track(id)` + `cleanup(request)` via HA API DELETE. `healthGate(request)` for beforeAll skip-if-down. `snapshotAutomationIds` + `verifyNoLeakedAutomations`. | COMPLETE |
| 90.6 | **Un-quarantine live AI tests for CI** — `.github/workflows/test-live-ai.yml`. Manual + nightly (3:00 UTC). Docker stack startup, retries=2, workers=1, timeout=180s. Pass-rate JSON artifact + GitHub job summary. `FLAKY_TESTS.md` updated. | COMPLETE |
| 90.7 | **YAML validation service integration tests** — `tests/integration/test_yaml_validation_service.py` (15 tests). All 6 stages: syntax error, schema (missing trigger/action), normalization (triggers→trigger, initial_state), safety (lock/alarm warnings), style (Jinja2), edge cases (empty, non-dict). | COMPLETE |
| 90.8 | **Predictive suggestion service tests** — 4 files, 107 tests. Blueprint suggestion: 35 scorer tests (weights, complexity, fallback) + 15 API tests. Rule recommendation: 30 model tests (collaborative, device-based, popular, cold-start, save/load, pickle security) + 27 API tests. | COMPLETE |
| 90.9 | **Hybrid Flow integration test** — `tests/integration/test_hybrid_flow_pipeline.py` (7 tests). Plan → Validate → Compile pipeline. Determinism proof: 3 identical compile calls → identical YAML. Cross-service validation: compiled YAML → yaml-validation-service. | COMPLETE |
| 90.10 | **E2E regression suite & documentation** — Created `ASK_AI_YAML_VERIFICATION.md` (test matrix: 5 categories × 3 levels). Updated `ASK_AI_TEST_STATUS.md` (archived Oct 2025 data). Updated `README.md` test matrix (500+ tests). Updated `FLAKY_TESTS.md` with CI job reference. | COMPLETE |

**Key deliverables:** Backend integration tests (HTTP-level, no UI), YAML content validator helper, structural assertions on every created automation, test cleanup harness, un-quarantined live AI CI job, predictive suggestion test coverage, hybrid flow determinism verification.

**Architecture notes:**
- Two automation paths exist: **GUI** (ha-ai-agent-service:8030 → GPT picks entities/YAML) and **CLI** (ai-automation-service-new:8036 → deterministic template compilation). Both must be tested.
- Validation chain has 3 strategies (YAML service → AI automation service → basic fallback). Tests must verify all 3.
- `yaml-validation-service` does 6-stage validation: syntax → schema → referential integrity → service schema → safety → maintainability.
- The `preview_automation_from_prompt` tool stores pending previews in conversation state — the approval flow requires multi-turn conversation testing.
- Blueprint suggestion scoring weights sum to 0.80, not 1.0 — Story 90.8 should fix this.
- Rule-recommendation-ml uses insecure pickle deserialization and loses feedback on restart — Story 90.8 should document/flag these.

---

### Epic 84: E2E Stale Selector Remediation — COMPLETE (Mar 18)

**Priority:** P2 | **Effort:** 1 session | **Dependencies:** None | **Status:** COMPLETE (11/11)
**Affects:** `tests/e2e/` (12+ Playwright spec files, 3 doc/script files)

| Story | Description | Status |
|-------|-------------|--------|
| 84.1 | **Remove deprecated enrichment-pipeline references** — Removed port 8002 health checks from `integration-performance-enhanced.spec.ts`, `performance.spec.ts`, `integration.spec.ts`, README, shell scripts | COMPLETE |
| 84.2 | **Remove deprecated SQLite/migration tests** — Replaced SQLite backend refs with PostgreSQL-only in `database-health.spec.ts`, `database-migration.spec.ts` | COMPLETE |
| 84.3 | **Fix navigation pattern — sidebar to tabs** — Replaced all `nav-monitoring/settings/dashboard` with `tab-services/configuration/overview` across 7 files | COMPLETE |
| 84.4 | **Fix deprecated screen selectors** — Replaced `monitoring-screen`, `settings-screen` with `dashboard-content` + tab assertions across 6 files | COMPLETE |
| 84.5 | **Fix settings selectors** — Rewrote `settings-screen.spec.ts` to use `dashboard-content` and valid Configuration tab selectors | COMPLETE |
| 84.6 | **Fix health card internal selectors** — Replaced `health-card-title/status/value` with `health-card` parent + text/attribute queries | COMPLETE |
| 84.7 | **Fix event and statistics selectors** — Replaced `events-feed/list/section`, `statistics-*` with `event-stream` and API-level assertions | COMPLETE |
| 84.8 | **Fix service-card selectors** — Verified `service-card` testid exists, updated `service-list` container usage | COMPLETE |
| 84.9 | **Full rewrite of user-journey-complete.spec.ts** — Complete rewrite using tab-based navigation, valid health-card queries, event-stream | COMPLETE |
| 84.10 | **Add missing data-testid attributes** — Audit confirmed 35+ production testids already cover all E2E needs | COMPLETE |
| 84.11 | **Full E2E regression verification** — 137 tests across 11 files parse successfully, zero stale selectors remain | COMPLETE |

### Epic 86: Zeek 8.x Native Telemetry & Capture Health Dashboard — COMPLETE (Mar 18)

**Priority:** P2 | **Effort:** 1 session | **Dependencies:** Epics 72, 79, 82 (all complete) | **Status:** COMPLETE (7/7)
**Affects:** `domains/data-collectors/zeek-network-service/`, `infrastructure/prometheus/`, `infrastructure/grafana/`, `domains/core-platform/compose.yml`

| Story | Description | Status |
|-------|-------------|--------|
| 86.1 | **Enable Zeek telemetry framework** — Added `@load frameworks/telemetry` + `Telemetry::metrics_port = 9911` to local.zeek | COMPLETE |
| 86.2 | **Docker networking** — Added `extra_hosts: host.docker.internal:host-gateway` to Prometheus, `EXPOSE 9911` to Dockerfile.zeek, `ZEEK_TELEMETRY_PORT` env var | COMPLETE |
| 86.3 | **Prometheus scrape config** — New `zeek-telemetry` job targeting `host.docker.internal:9911`, 30s interval, labels: service=zeek, metrics_source=native-telemetry | COMPLETE |
| 86.4 | **Recording rules** — 6 rules in `zeek_capture_health` group: packets received/dropped rate, drop ratio (clamped), memory, event queue depth avg, active connections | COMPLETE |
| 86.5 | **Alert rules** — 4 alerts in `zeek_capture_alerts` group: ZeekPacketDropHigh (>0.1%, critical), ZeekMemoryPressure (>3.2GB, warning), ZeekEventQueueSaturated (>10k, warning), ZeekCaptureStalled (0 pps, critical) | COMPLETE |
| 86.6 | **Grafana dashboard** — `zeek-capture-health.json` with 9 panels: packets time series, drop ratio gauge, memory gauge, event queue with threshold line, active connections, capture health status stat | COMPLETE |
| 86.7 | **Verification & docs** — Updated TECH_STACK.md (port 9911), healthcheck.sh (optional telemetry check), OPEN-EPICS-INDEX.md | COMPLETE |

**Key deliverables:** 1 new Grafana dashboard, 6 recording rules, 4 alert rules, 1 Prometheus scrape job, port 9911 reserved

---

### Epic 72: Zeek Core Network Ingestion (MVP) — COMPLETE (Mar 16)

**Priority:** P1 | **Effort:** 1-2 weeks | **Dependencies:** None (greenfield) | **Status:** COMPLETE (7/7)
**New service:** `domains/data-collectors/zeek-network-service/` (port 8048)

| Story | Description | Status |
|-------|-------------|--------|
| 72.1 | **Zeek Docker image & config files** — `Dockerfile.zeek` (FROM `zeek/zeek:8.1.1`), `local.zeek` + `homeiq.zeek`, entrypoint script for env var expansion | COMPLETE |
| 72.2 | **Compose integration & shared volume** — `zeek` + `zeek-network-service` in compose.yml, `--net=host`, BPF filter, `zeek-logs` + `zeek-state` volumes | COMPLETE |
| 72.3 | **Python service scaffold** — FastAPI + BaseServiceSettings + 6 homeiq libs, Alembic init, multi-stage Alpine Dockerfile | COMPLETE |
| 72.4 | **conn.log parser + InfluxDB writer** — 30s polling, seek offset persistence, log rotation handling, 5-min in-memory buffer on InfluxDB outage | COMPLETE |
| 72.5 | **dns.log parser + InfluxDB writer** — dns.log → `network_dns` measurement, reuses log_tracker | COMPLETE |
| 72.6 | **Per-device metric aggregation** — 60s window → `network_device_metrics`, double-buffer pattern | COMPLETE |
| 72.7 | **REST API + integration tests** — 6 endpoints, 25 tests passing, IP validation, safe int/float for Zeek `-` values | COMPLETE |

**Key deliverables:** 22 new files, 2 Docker containers (zeek + zeek-network-service), 3 InfluxDB measurements, 25 unit tests

---

### Epic 73: Zeek Device Fingerprinting (Phase 2) — COMPLETE (Mar 16)

**Priority:** P1 | **Effort:** 2-3 weeks | **Dependencies:** Epic 72 (complete) | **Status:** COMPLETE (6/6)
**Extends:** `domains/data-collectors/zeek-network-service/`

| Story | Description | Status |
|-------|-------------|--------|
| 73.1 | **Custom Zeek image with fingerprinting packages** — ja3, ja4, hassh, KYD already in `Dockerfile.zeek` | COMPLETE |
| 73.2 | **DHCP parsing + PostgreSQL fingerprints** — `dhcp_parser.py`, `fingerprint_service.py`, Alembic 001 migration, MAC-keyed upsert | COMPLETE |
| 73.3 | **TLS fingerprinting** — `tls_parser.py` parsing ja3.log, ja4.log, ssl.log → JA3/JA4 hashes | COMPLETE |
| 73.4 | **SSH + software fingerprinting** — `ssh_parser.py` parsing hassh.log + software.log → HASSH hashes, user-agent, OS guess | COMPLETE |
| 73.5 | **MAC OUI vendor lookup** — `oui_lookup.py` with ~200 curated IoT/networking vendor OUI prefixes | COMPLETE |
| 73.6 | **Fingerprint REST API + tests** — 3 new endpoints, 32 new tests (57 total) | COMPLETE |

**Key deliverables:** 9 new files, 1 PostgreSQL table (devices.network_device_fingerprints), 3 new REST endpoints, 32 new tests

---

### Epic 64: Convention Compliance & Auto-Enhancement — COMPLETE (Mar 16)

**Priority:** P2 | **Effort:** 1-2 weeks | **Dependencies:** Epics 62-63 (complete) | **Status:** COMPLETE (6/6)
**Enhances:** `ml-engine/device-intelligence-service`, `core-platform/health-dashboard`, `automation-core/ha-ai-agent-service`

| Story | Description | Status |
|-------|-------------|--------|
| 64.1 | **Naming Convention Score Engine** — `GET /api/naming/audit` + `GET /api/naming/score/{entity_id}` in device-intelligence-service. 100-point scale: area_id (+20), AI intent label (+20), aliases (+20), friendly name convention (+20), device_class (+10), sensor role label (+10). Returns per-entity scores, issues, suggestions + aggregate summary. | COMPLETE |
| 64.2 | **Auto-Alias Generation** — `POST /api/naming/suggest-aliases` in device-intelligence-service. Pattern-based (no AI): singular/plural, area-less, abbreviations (TV/AC), type shorthand, casual variants. Conflict detection prevents duplicate aliases across entities. 3-5 suggestions per entity. | COMPLETE |
| 64.3 | **Compliance Dashboard Widget** — `ConventionComplianceCard.tsx` on Overview tab. Shows aggregate compliance %, top 3 issues with counts, "Fix →" links to HA Setup tab with filters. Auto-refreshes every 5 minutes. Calls `GET /api/naming/audit`. | COMPLETE |
| 64.4 | **Name Suggestion Integration** — `GET /api/naming/suggest-name/{entity_id}` in device-intelligence. Wraps existing `DeviceNameGenerator` with convention-aware suggestions (area prefix, Title Case, no brand). Wire into NameEditor (Story 63.5) for one-click "Use suggestion". | COMPLETE |
| 64.5 | **Entity Discovery Sync Enhancement** — Already implemented: websocket-ingestion passes aliases + labels from HA Entity Registry API through to data-api bulk_upsert JSONB columns. Pipeline verified working. | COMPLETE |
| 64.6 | **Convention Enforcement in Chat** — In ha-ai-agent-service naming_hints.py, surface naming hints when matched entities have low convention scores. "I couldn't find that entity" → suggest HA Setup. `ai:critical` label → confirmation step. Max 1 hint per turn. | COMPLETE |

**Dependency Graph:**
```
64.1 score engine ← Epic 62.2 (label query)
64.2 auto-aliases ← Epic 62.3 (alias search)
64.3 compliance card ← 64.1
64.4 name suggestions ← Epic 62.4 (entity CRUD)
64.5 discovery sync ← Epic 62.4
64.6 chat hints ← Epic 62.6 (label filtering) + 64.1
```

**Recommended execution order:** 64.1 → 64.2 → 64.3 (depends on 64.1) → 64.4 → 64.5 → 64.6 (depends on 64.1)
Stories 64.1 + 64.2 can run in parallel. Stories 64.4 + 64.5 can run in parallel.

**New Files:**
- `domains/ml-engine/device-intelligence-service/src/services/naming_convention/score_engine.py`
- `domains/ml-engine/device-intelligence-service/src/services/naming_convention/convention_rules.py`
- `domains/ml-engine/device-intelligence-service/src/services/naming_convention/alias_generator.py`
- `domains/ml-engine/device-intelligence-service/src/naming_endpoints.py`
- `domains/core-platform/health-dashboard/src/components/overview/ConventionComplianceCard.tsx`

---

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

### Epic 58: Frontend Test Quality — COMPLETE (Mar 13)

**Priority:** P1 | **Effort:** 1 session | **Dependencies:** Epics 42-45 | **Status:** COMPLETE (6/6)

| Story | Description | Status |
|-------|-------------|--------|
| 58.1 | **A11y test sweep** — Added `getByRole`, heading-level, button-element assertions to 8 test files across HD + AI UI | **DONE** |
| 58.2 | **Dark mode test sweep** — Added dark mode rendering test to ConversationSidebar (AI UI already had coverage in MessageContent, AutomationPreview) | **DONE** |
| 58.3 | **Error boundary tests** — 4 new test files: HD ErrorBoundary (12 tests), AI UI MarkdownErrorBoundary (8), ProposalErrorBoundary (8), PageErrorBoundary (11) | **DONE** |
| 58.4 | **Skeleton component tests** — 2 new test files: HD Skeletons (23 tests for Card/Graph/List/Table), AI UI Skeletons (25 tests for Card/Grid/Filter/Stats) | **DONE** |
| 58.5 | **Testing standards doc** — Created `docs/TESTING_STANDARDS.md` with conventions, required categories, a11y patterns, coverage targets, templates | **DONE** |
| 58.6 | **MSW handler expansion** — Added 6 new success handlers (energy, events, integrations, RAG, memory, config) + 6 error handlers (500, 401, 404, 503, network error) | **DONE** |

### Epic 59: Frontend Integration & E2E — COMPLETE (Mar 13)

**Priority:** P1 | **Effort:** 1 session | **Dependencies:** Epics 42-45, 58 | **Status:** COMPLETE (6/6)

| Story | Description | Status |
|-------|-------------|--------|
| 59.1 | **Health Dashboard integration tests** — 14 tests: cross-tab nav, URL hash sync, group expand/collapse, auto-refresh, time range persistence, custom events, keyboard nav, degraded status resilience | **DONE** |
| 59.2 | **AI Automation UI integration tests** — 13 tests: conversation lifecycle, optimistic updates, multi-turn flows, sidebar loading, error handling, input sanitization, performance tracking | **DONE** |
| 59.3 | **Health Dashboard E2E smoke tests** — 11 Playwright tests: dashboard loads, overview metrics, services health, devices list, sidebar navigation, dark mode persistence, time range, auto-refresh, deep linking, API error handling | **DONE** |
| 59.4 | **Cross-app navigation E2E** — 6 tests: app switcher links, HD↔AI UI navigation, HD↔Observability, footer links, URL safety validation | **DONE** |
| 59.5 | **Performance baseline tests** — 7 tests: overview <5s, services <3s, 1000 devices render, 10k events, AI UI <3s, tab switch <1.5s, CLS <0.25 | **DONE** |
| 59.6 | **Visual regression setup** — 12 Playwright screenshot tests: overview, services, config, navigation, health cards, dark mode, mobile, tablet, loading, error, modal, chart states | **DONE** |

### Epic 61: Phase 5 Production Deployment Execution — COMPLETE (Mar 13)

**Priority:** P0 | **Effort:** 5 days | **Dependencies:** Epics 54-58, 60 | **Status:** COMPLETE (6/6)

| Story | Description | Status |
|-------|-------------|--------|
| 61.1 | **Update deployment scripts** — Add 6 missing services to pre-deployment-check.sh, fix tiers 4-9 port list in deploy-phase-5.sh, correct plan ports (ha-device-control 8046, voice-gateway 8047) | **DONE** |
| 61.2 | **Pre-deployment validation (Day 1)** — 48/48 health endpoints, Docker config validates, PostgreSQL 8/8 schemas, InfluxDB healthy, 231GB disk, Prometheus+Grafana healthy. **Decision: GO** | **DONE** |
| 61.3 | **Create deployment backups** — PostgreSQL dump (6.2MB), backup manifest created | **DONE** |
| 61.4 | **Tier 1-3 deployment (Day 2)** — All 21 services verified healthy (48/48 endpoints 200 OK), PostgreSQL 10 schemas, InfluxDB v2.8.0 ready | **DONE** |
| 61.5 | **Tiers 4-9 deployment (Day 2)** — All 22 remaining services verified healthy, 43/43 version check script passing, monitoring (Prometheus+Grafana) confirmed | **DONE** |
| 61.6 | **Post-deployment validation (Day 3-5)** — 852 tests passing (319 HD + 366 AI UI + 109 obs + 58 Python), validation report generated, post-deployment-validate.sh created | **DONE** |

### Epic 63: HA Setup Wizard & Entity Management UI — COMPLETE (Mar 14)

**Priority:** P1 | **Effort:** 1 session | **Dependencies:** Epic 62 | **Status:** COMPLETE (7/7)

| Story | Description | Status |
|-------|-------------|--------|
| 63.1 | **HA Setup tab & navigation** — HASetupTab.tsx lazy-loaded, added to NAV_GROUPS under "Devices & Data" after Devices, URL hash `#ha-setup`, sub-nav: Audit/Labels/Aliases/Exclusions | **DONE** |
| 63.2 | **Entity Audit View** — EntityAuditView.tsx with AuditSummaryCards (compliance %, missing area/labels/aliases counts), entity scoring (100-pt scale), sortable/filterable table, click-to-expand | **DONE** |
| 63.3 | **Label Editor Panel** — LabelEditor.tsx with taxonomy dropdown, custom label input (prefix:name validation), smart suggestions per domain/device_class, removable badges, optimistic saves | **DONE** |
| 63.4 | **Alias Editor Panel** — AliasEditor.tsx with free-text input, auto-suggestions (singular/plural, without area, abbreviations), removable tags, saves via admin-api | **DONE** |
| 63.5 | **Friendly Name Editor** — NameEditor.tsx with live convention check (area prefix, Title Case, no brand/model), AI-suggested name, saves name_by_user via admin-api | **DONE** |
| 63.6 | **Exclusion Manager** — ExclusionManager.tsx with glob pattern management, ai:ignore entity listing, suggested exclusion patterns, match count preview, total impact summary | **DONE** |
| 63.7 | **Bulk Operations & Quick Actions** — BulkActionsBar.tsx (multi-select + bulk add/remove labels, quick Mark Automatable/Ignore), QuickActions.tsx (6 domain-wide one-click actions) | **DONE** |

### Epic 66: AI/Agent Service Classification — COMPLETE (Mar 16)

**Priority:** P1 | **Effort:** 1 session | **Dependencies:** None | **Status:** COMPLETE (5/5)

| Story | Description | Status |
|-------|-------------|--------|
| 66.1 | **Service Classification Audit & Tier Document** — `docs/architecture/ai-agent-classification.md` with 4-tier classification (T1-T4) for all 51 services, evidence table, summary stats | **DONE** |
| 66.2 | **ADR — Single Agent Architecture** — `docs/architecture/adr-single-agent-architecture.md` documenting why only ha-ai-agent-service is T1 (cost, latency, testability, security, debuggability) | **DONE** |
| 66.3 | **Decision Tree** — Mermaid flowchart in classification doc: LLM? → Iterates? → Tool use? → Tier assignment | **DONE** |
| 66.4 | **Cross-Reference Integration** — AI Tier column in TECH_STACK.md service table, links in service-groups.md | **DONE** |
| 66.5 | **Health Dashboard AI Tier Badges** — Static manifest `ai-tier-manifest.json`, `useAiTierManifest` hook, Badge in ServiceCard (T1-T3 only, T4 hidden) | **DONE** |

### Epic 67: AI Automation Validation Loop — COMPLETE (Mar 16)

**Priority:** P1 | **Effort:** 1 session | **Dependencies:** Epic 66 | **Status:** COMPLETE (6/6)

| Story | Description | Status |
|-------|-------------|--------|
| 67.1 | **Validation Client Integration** — `LinterClient` for POST /lint with CircuitBreaker, `LintResult` dataclass, 2s timeout | **DONE** |
| 67.2 | **Retry Loop** — `ValidationRetryLoop.generate_and_validate()` with configurable max retries (default 3), best-attempt tracking | **DONE** |
| 67.3 | **Error Context Prompt** — `ERROR_FEEDBACK_PROMPT` template with original request + failed YAML + structured error list for LLM correction | **DONE** |
| 67.4 | **Graceful Degradation** — CircuitBreaker + try/except for both linter and validator; `AI FALLBACK:` logging; pass-through when services are down | **DONE** |
| 67.5 | **Metrics & Observability** — `first_pass_rate`, `average_retries`, `total_generations` tracked on ValidationRetryLoop; `/health/validation-metrics` endpoint | **DONE** |
| 67.6 | **Integration Tests** — 10 tests: pass-first-try, pass-second-try, all-exhausted, linter-down, validator-down, both-down, no-clients, metrics, error-format, LinterClient unit tests | **DONE** |

### Epic 68: Proactive Agent — Autonomous Upgrade — COMPLETE (Mar 16)

**Priority:** P1 | **Effort:** 2-3 weeks | **Dependencies:** Epic 66, Memory Brain | **Status:** COMPLETE (8/8)
**Enhances:** `energy-analytics/proactive-agent-service`, `automation-core/ha-device-control`

| Story | Description | Status |
|-------|-------------|--------|
| 68.1 | **Observe-Reason-Act Agent Loop** — `ProactiveAgentLoop` with observe (house status + weather + time), reason (LLM structured output), act (route to auto-execute/suggest/suppress) on configurable interval (default 15m) | **DONE** |
| 68.2 | **Memory Brain Integration — Preference Recall** — `PreferenceService` queries behavioral/boundary memories + `action_preference_history` table for acceptance rates. Injects preference context into LLM reasoning prompt | **DONE** |
| 68.3 | **Confidence & Risk Scoring Engine** — `ConfidenceScorer` with 5-factor scoring (LLM confidence 30%, acceptance rate 30%, context match 20%, preference 10%, reversibility 10%). Risk classification by entity domain. Safety-critical domains hardcoded as frozenset | **DONE** |
| 68.4 | **Autonomous Execution Path** — `AutonomousExecutor` calls ha-device-control directly (lights, switches, climate, scenes). Pre/post state snapshots, `DeviceControlClient` with CrossGroupClient + circuit breaker, user notification after execution | **DONE** |
| 68.5 | **Feedback Loop — Outcome Recording** — `FeedbackRecorder` updates `action_preference_history` table on every outcome (accepted/rejected/auto-executed/undone). Records to Memory Brain for broader preference learning | **DONE** |
| 68.6 | **User Configuration & Safety Guardrails** — `UserPreference` model, REST endpoints (GET/PUT /api/proactive/preferences), configurable thresholds/quiet hours/excluded categories. Lock/alarm/camera always blocked (hardcoded frozenset) | **DONE** |
| 68.7 | **Audit Trail & Reversibility** — `AutonomousActionAudit` model with pre/post state snapshots, confidence/risk scores, undo capability within configurable window (default 15m). GET /api/proactive/audit + POST /api/proactive/undo/{id} | **DONE** |
| 68.8 | **Integration Tests & Safety Validation** — 20 tests: confidence scoring (high/low/medium), risk classification, safety blocked domains, quiet hours suppression, autonomous disabled, preference learning, undo rate calculation, time slot mapping | **DONE** |

---

### Epic 70: Self-Improving Agent (Hermes) — COMPLETE (Mar 16)

**Priority:** P1 | **Effort:** 3-4 weeks | **Dependencies:** Epic 60 (complete), Memory Brain | **Status:** COMPLETE (8/8)
**Enhances:** `automation-core/ha-ai-agent-service`

| Story | Description | Status |
|-------|-------------|--------|
| 70.1 | **Procedural Skill Learning** — `SkillStore` (CRUD + text search), `SkillExtractor` (trigger heuristics: 5+ iterations, save keywords), `SkillRecall` (category + area + text search, 500-token budget), `Skill` SQLAlchemy model in agent.skills table | **DONE** |
| 70.2 | **Skills Guard (Security Scanner)** — `SkillsGuard.scan()` with 85+ threat patterns across 6 categories (prompt injection, HA dangerous services, exfiltration, destructive, structural, unicode abuse). Blocks critical/high, warns medium/low. filter_safe_skills for recall | **DONE** |
| 70.3 | **Smart Model Routing** — `choose_model_route()` routes simple queries (<160 chars, <28 words, no automation keywords) to gpt-4.1-mini, complex to gpt-5.2-codex. Fallback to primary on any error. Cost factor tracking | **DONE** |
| 70.4 | **Context Compression** — `ContextCompressor` preserves first 3 + last 4 turns, LLM-summarizes middle. Orphaned tool_call/tool_result pair sanitization. Graceful fallback to drop-without-summary on summarization failure | **DONE** |
| 70.5 | **Subagent Delegation** — `DelegateService` + `SubagentRunner`: up to 3 parallel child loops with area-scoped context, restricted toolsets, per-subagent token budget (8K default). asyncio.gather() with result synthesis | **DONE** |
| 70.6 | **Session Search** — `SessionSearch.search()` via PostgreSQL text matching on messages table. Groups by conversation_id, deduplicates, top 3 sessions. Optional summarization via cheap model. format_for_context() for prompt injection | **DONE** |
| 70.7 | **User Modeling** — `UserProfile` model (5 dimensions: confirmation, trigger, risk, communication, naming). `PreferenceExtractor` (background LLM analysis), `ProfileInjector` (200-token budget system prompt section). Configurable TTL (default 90d) | **DONE** |
| 70.8 | **Prompt Caching** — `apply_cache_control()` for Anthropic (explicit cache_control markers) and OpenAI (message restructuring for automatic caching). system_and_3 strategy. `estimate_cache_savings()` for cost tracking | **DONE** |

---

### Epic 71: ML/AI Library Upgrades (Phase 3) — COMPLETE (Mar 16)

**Priority:** P2 | **Effort:** 1 session | **Dependencies:** Phase 5 stable 3+ weeks | **Status:** COMPLETE (8/8)
**Affects:** device-intelligence-service, ml-service, ai-pattern-service, ha-ai-agent-service, ai-automation-service-new, ai-query-service, proactive-agent-service, nlp-fine-tuning

| Story | Description | Status |
|-------|-------------|--------|
| 71.1 | **NumPy 2.4.3 upgrade** — Updated numpy pin from `>=1.26.0,<3.0.0` to `>=2.4.3,<3.0.0` in device-intelligence-service, ml-service, ai-pattern-service. Code audit: 27 files, zero deprecated NumPy 1.x APIs (no np.bool/int/float/object/NZERO usage). NEP 50 dtype promotion compatible. | **DONE** |
| 71.2 | **Pandas 3.0.1 upgrade** — Updated pandas pin from `>=2.2.0,<3.1.0` to `>=3.0.1,<3.1.0` in device-intelligence-service, ai-pattern-service. Added `pyarrow>=18.0.0` dependency (required for Pandas 3.0 default string dtype). Code audit: no `df.append()`, no `dtype=='object'` checks, no deprecated APIs. | **DONE** |
| 71.3 | **scikit-learn 1.8.0 upgrade** — Updated scikit-learn pin from `>=1.5.0,<2.0.0` to `>=1.8.0,<2.0.0` in device-intelligence-service, ml-service, ai-pattern-service. All import paths current (sklearn.ensemble, .preprocessing, .metrics, .model_selection, .cluster). Added model regeneration documentation. | **DONE** |
| 71.4 | **SciPy 1.17.1 upgrade** — Updated scipy pin from `>=1.13.0,<2.0.0` to `>=1.17.1,<2.0.0` in ml-service, ai-pattern-service. No direct scipy imports in source (transitive dependency via sklearn). | **DONE** |
| 71.5 | **OpenAI SDK 2.28.0 upgrade** — Updated openai pin from `>=2.21.0,<3.0.0` to `>=2.28.0,<3.0.0` across 5 services: ha-ai-agent-service, ai-automation-service-new, ai-query-service, proactive-agent-service, nlp-fine-tuning. Already on v2 API — no code changes needed. | **DONE** |
| 71.6 | **joblib 1.5.3 upgrade** — Updated joblib pin from `>=1.3.0,<2.0.0` to `>=1.5.3,<2.0.0` in device-intelligence-service. Added model regeneration guidance to predictive_analytics.py docstring and error handler (13 joblib.load/dump call sites). | **DONE** |
| 71.7 | **Model regeneration safety** — Enhanced error message in `initialize_models()` (predictive_analytics.py) to guide operators when sklearn-incompatible .pkl files are detected. Existing try/except gracefully degrades; nightly APScheduler retraining auto-regenerates. | **DONE** |
| 71.8 | **Phase 3 plan finalization** — Updated `docs/planning/phase-3-plan-ml-ai-upgrades.md` with verified 2026 version numbers (web-verified from PyPI), marked all prerequisites DONE, updated version table for all 8 services, documented verification sources. | **DONE** |

**Code Audit Summary:**
- 27 Python files audited across 4 services + homeiq-memory lib
- **Zero deprecated APIs found** — codebase fully compatible with all target versions
- **No code changes required** for NumPy 2.x, Pandas 3.0, or sklearn 1.8.0
- **Critical note**: 36 .pkl model files must be regenerated after first deployment (automatic via nightly training)

---

### Epic 65: Bundle Optimization — COMPLETE (Mar 16)

**Priority:** P1 | **Effort:** 1 session | **Dependencies:** None | **Status:** COMPLETE (6/6)

| Story | Description | Status |
|-------|-------------|--------|
| 65.1 | **Establish bundle size baseline** — Installed `rollup-plugin-visualizer` in both apps, captured baseline metrics (AI UI: 966 KB main, HD: 264 KB main), `dist/stats.html` treemap reports | **DONE** |
| 65.2 | **Implement advanced code splitting** — AI UI: `manualChunks` config (vendor, query, force-graph, charts, markdown, animation), 8 page routes converted to `React.lazy()` dynamic imports | **DONE** |
| 65.3 | **Dependency audit & consolidation** — Identified `react-force-graph`+`three` (1.9 MB) only used in Synergies graph view; lazy-loaded `NetworkGraphView`, `Patterns`, `Synergies` sub-pages inside Insights | **DONE** |
| 65.4 | **Implement Suspense boundaries** — `PageLoadingSkeleton` at route level, skeleton fallback on Insights sub-tabs, "Loading graph..." on NetworkGraphView | **DONE** |
| 65.5 | **Measure & compare metrics** — Main bundle 966→218 KB (-77%), initial gzip 269→69 KB (-74%), 10 lazy route chunks, force-graph deferred from /insights to graph-view-only | **DONE** |
| 65.6 | **Document & CI bundle check** — `.github/scripts/check-bundle-size.sh` (warn >10%, fail >20%), updated FRONTEND_IMPLEMENTATION_PATTERNS.md, epic index | **DONE** |

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
| 58 | Frontend Test Quality | *(this file)* | P1 High | 6 | 1 session | **Complete** (6/6: TESTING_STANDARDS.md, error boundary tests, skeleton tests, a11y sweep, dark mode, MSW expansion) |
| 59 | Frontend Integration & E2E | *(this file)* | P1 High | 6 | 1 session | **Complete** (6/6: 27 integration tests, E2E smoke, cross-app nav, perf baselines, visual regression) |
| 60 | Chat Endpoint Complexity Refactor | *(this file)* | P1 High | 3 | 1 session | **Complete** (3/3: tool_execution.py extracted, _run_openai_loop helper, lint fixes) |
| 61 | Phase 5 Production Deployment | *(this file)* | **P0 Critical** | 6 | 5 days | **Complete** (6/6: script updates, pre/post-deployment validation, 9-tier rollout, 852 tests) |
| 62 | Entity Convention API Foundation | *(this file)* | P1 High | 8 | 1-2 weeks | **Complete** (8/8: areas, labels, aliases, CRUD, dynamic areas, filtering, alias tiers, scoring) |
| 63 | HA Setup Wizard & Entity Management UI | *(this file)* | P1 High | 7 | 1 session | **Complete** (7/7: HASetupTab, EntityAuditView, LabelEditor, AliasEditor, NameEditor, ExclusionManager, BulkActionsBar) |
| 65 | Bundle Optimization | *(this file)* | P1 High | 6 | 1 session | **Complete** (6/6: AI UI main 966→218 KB, 8 lazy routes, force-graph deferred, visualizer, CI check) |
| 66 | AI/Agent Service Classification | [epic-66-ai-agent-classification.md](epic-66-ai-agent-classification.md) | P1 High | 5 | 1 session | **Complete** (5/5: classification doc, ADR, decision tree, cross-refs, HD badges) |
| 67 | AI Automation Validation Loop | [epic-67-automation-validation-loop.md](epic-67-automation-validation-loop.md) | P1 High | 6 | 1 session | **Complete** (6/6: LinterClient, retry loop, error prompt, circuit breaker, metrics, tests) |
| 68 | Proactive Agent Upgrade | [epic-68-proactive-agent-upgrade.md](epic-68-proactive-agent-upgrade.md) | P1 High | 8 | 2-3 weeks | **Complete** (8/8: observe-reason-act loop, confidence/risk scoring, autonomous execution, safety guardrails, audit + undo, 20 tests) |
| 69 | Agent Eval Feedback Loop | [epic-69-agent-eval-feedback-loop.md](epic-69-agent-eval-feedback-loop.md) | P2 Medium | 7 | 2 weeks | **Complete** (7/7: complexity classifier, adaptive routing, eval alerting, regression investigation, cost tracking, admin config) |
| 70 | Self-Improving Agent (Hermes-Inspired) | [epic-70-hermes-self-improving-agent.md](epic-70-hermes-self-improving-agent.md) | P1 High | 8 | 3-4 weeks | **Complete** (8/8: smart routing, skill learning + guard, context compression, subagent delegation, session search, user modeling, prompt caching, 30+ tests) |
| 71 | ML/AI Library Upgrades (Phase 3) | [phase-3-plan-ml-ai-upgrades.md](../docs/planning/phase-3-plan-ml-ai-upgrades.md) | P2 Medium | 8 | 1 session | **Complete** (8/8: NumPy 2.4.3, Pandas 3.0.1, sklearn 1.8.0, SciPy 1.17.1, OpenAI 2.28.0, joblib 1.5.3, 8 services, PyArrow added) |
| 78 | Cross-Service Integration Tests | [epic-78-cross-service-integration-tests.md](epic-78-cross-service-integration-tests.md) | P1 High | 6 | 1 session | **Complete** (6/6: Tier 1 data flow, Zeek pipeline, agent chains, Memory Brain, cross-group auth, CI — 24 new tests, 39 total) |
| 79 | Production Alerting & SLA Monitoring | [epic-79-production-alerting-sla.md](epic-79-production-alerting-sla.md) | P1 High | 6 | 1 session | **Complete** (6/6: SLA rules, SLA alerts, AlertManager v0.28.1, Grafana dashboard, Zeek alerts, admin webhook) |
| 80 | Data-API Test Coverage & Security Hardening | [epic-80-data-api-test-coverage.md](epic-80-data-api-test-coverage.md) | P1 High | 12 | 5-7 days | **Complete** (12/12: 345 tests — auth, database, endpoints, security) |
| 81 | Docker Rebuild & Deploy — aiohttp CVE | [epic-81-docker-rebuild-aiohttp-cve.md](epic-81-docker-rebuild-aiohttp-cve.md) | P1 High | 5 | 1 session | **Complete** (5/5: 58/58 containers healthy, aiohttp 3.13.3 verified, postgres-exporter PG17, Zeek 8.1.1 compat) |
| 82 | Zeek Container Docker Healthcheck | [epic-82-zeek-docker-healthcheck.md](epic-82-zeek-docker-healthcheck.md) | P1 High | 5 | 1 session | **Complete** (5/5: process + log-freshness healthcheck for homeiq-zeek) |
| 83 | Data-API HTTP Route Coverage Expansion | [epic-83-data-api-route-coverage.md](epic-83-data-api-route-coverage.md) | P1 High | 11 | 3-5 sessions | **Complete** (11/11: 193 tests — HTTP route coverage, dead code discovery, bug documentation) |
| 85 | Data-API Unit & Line Coverage Expansion | [epic-85-data-api-line-coverage.md](epic-85-data-api-line-coverage.md) | P1 High | 10 | 1 session | **Complete** (10/10: 443 new unit tests across 20 test files — entity enrichment, device classification, flux utils security, metrics buffer, sports writer, service lifecycle, config management, background jobs, endpoint models. Line coverage 8.8% → 40%+) |
| 86 | Zeek 8.x Native Telemetry & Capture Health Dashboard | [epic-86-zeek-telemetry-capture-health.md](epic-86-zeek-telemetry-capture-health.md) | P2 Medium | 7 | 1 session | **Complete** (7/7: Zeek telemetry :9911, Prometheus scrape, 6 recording rules, 4 capture alerts, Grafana dashboard, port 9911 in TECH_STACK) |
| 87 | Data-API Coverage Expansion Phase 2 | *(this file)* | P2 Medium | 6 | 1-2 weeks | **Planned** — 40% → 60%+ line coverage, 4 zero-coverage modules + memory consolidation deep paths |
| 88 | Dependency CVE Sweep & Hardening | *(this file)* | P2 Medium | 4 | 3-5 days | **Planned** — Full audit of 75 requirements files, pip-audit hook, KNOWN-VULNERABILITIES.md |
| 89 | E2E Test Stability & Green CI | *(this file)* | P2 Medium | 5 | 1 week | **Planned** — Fix 4 AI UI failures, Ask AI timeouts, flaky quarantine, green baseline across 93 specs |
| 90 | Ask AI → HA YAML E2E Pipeline | [epic-90-ask-ai-yaml-e2e.md](epic-90-ask-ai-yaml-e2e.md) | P1 High | 10 | 2-3 weeks | **Complete** (10/10: 7 backend integration tests, 14 YAML-asserted E2E tests, 107 blueprint service tests, reliability fixes, CI workflow, cleanup harness, docs) |

## Story Count by Priority

| Priority | Count | Description |
|----------|-------|-------------|
| P0 Critical | 49 | DB migration (10) + Security (6) + Tier 1 hardening (4) + Memory Foundation (6) + Embed Testing (2) + Frontend Test Infra (5) + HD Testing (8) + AI UI Testing (8) |
| P1 High | 209 | Quality, testing, deployment, browser review, TAPPS, Docker, Memory (18), Pattern Detection (10), React 19 (3), ML Feedback (1), Memory Metrics (2), Obs Dashboard Testing (4), Proactive Agent (8), Self-Improving Agent (8), Integration Tests (6), Alerting/SLA (6), Data-API Test Coverage (12), aiohttp CVE Deploy (5), Data-API Unit Coverage (10) |
| P2 Medium | 101 | Framework upgrades, feature integrations, Trust model (7), ML Upgrades (8), React Compiler (2), ML Models (5), Memory Tuning (4), Convention Compliance (6), Agent Eval (7), ML/AI Library Upgrades (8), MQTT/Protocol Intelligence (5), Zeek Telemetry (7), Data-API Coverage Ph2 (6), CVE Sweep (4), E2E Stability (5) |
| P3 Low | 12 | ML model training, placeholder implementations, Seasonal/Frequency detectors (3), Prophet (1), Pattern Fusion (1), Memory Dashboard (1) |
| **Total** | **608** | 593 complete + 15 planned stories (90 epics complete, 2 closed won't-do). |

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
| Mar 13 | Epic 57 complete (4/4: tool_calls, RAG testid, entity_extractor, secret scanning). Phase 5 plan refreshed (44+ health endpoints, 1366+ tests). Epic 60 complete (chat_endpoints refactor: 721→481+254 lines). Epic 58 complete (6/6: test quality). **Epic 61 complete (6/6: Phase 5 deployment — 852 tests passing, all 43 services verified, post-deployment validation report).** |
| Mar 14 | Sprint 24 complete — Epic 63 (7/7: HA Setup Wizard & Entity Management UI) |
| Mar 16 | Sprint 25 complete — Epic 65 (6/6: Bundle Optimization — AI UI main bundle 966→218 KB, -77%) |
| Mar 16 | Sprint 26 complete — Epic 66 (5/5: AI Service Classification — 4-tier taxonomy, ADR, HD badges) + Epic 67 (6/6: Validation Loop — retry + circuit breaker + 10 tests) |
| Mar 16 | Sprint 27 complete — Epic 68 (8/8: Proactive Agent autonomous upgrade — observe-reason-act, confidence scoring, safety guardrails, audit+undo) + Epic 70 (8/8: Self-Improving Agent — smart routing, skill learning, context compression, delegation, session search, user modeling, prompt caching) |
| Mar 16 | Sprint 28 complete — Epic 64 (6/6: Convention Compliance — score engine, alias generator, dashboard widget, name suggestions, chat hints) + Epic 69 (7/7: Agent Eval Feedback Loop — complexity classifier, adaptive routing, alerting, regression investigation, cost tracking) |
| Mar 16 | Sprint 29 complete — Epic 71 (8/8: ML/AI Library Upgrades — NumPy 2.4.3, Pandas 3.0.1, scikit-learn 1.8.0, SciPy 1.17.1, OpenAI 2.28.0, joblib 1.5.3, 8 services updated) |
| Mar 16 | Sprint 30 complete — **Epic 72 (7/7: Zeek Core Network Ingestion)** — Greenfield zeek-network-service (:8048). 2 containers (zeek packet capture + Python sidecar), conn.log + dns.log parsing → 3 InfluxDB measurements, device aggregation with double-buffer, REST API (6 endpoints), 25 tests. Review fixes: batch writes, SecretStr, schema SQL injection guard, safe int/float, IPv6 support |
| Mar 16 | Sprint 31 complete — **Epic 73 (6/6: Zeek Device Fingerprinting)** — DHCP parsing + PostgreSQL fingerprints table, JA3/JA4 TLS fingerprinting, HASSH SSH fingerprinting, software.log parsing, MAC OUI vendor lookup (~200 vendors), fingerprint REST API (3 new endpoints), 32 new tests |
| Mar 16 | Sprint 32 complete — **Epic 74 (5/5: Zeek MQTT & Protocol Intelligence)** — MQTT parsing (connect/publish/subscribe → InfluxDB), TLS certificate tracking (x509+ssl → PostgreSQL), DNS behavior profiles (6 categories, 7-day rolling counts), protocol intelligence REST API (5 new endpoints), security alerts (rogue MQTT clients, expired certs, weak TLS), 2 Alembic migrations, 39 new tests |
| Mar 16 | Sprint 34 complete — **P1 Blockers** (Playwright 1.58.2 alignment, tests/shared import paths: 10 files fixed) + **Epic 78 (6/6: Cross-Service Integration Tests)** — 24 new tests (39 total): Tier 1 data flow, Zeek pipeline, agent chains, Memory Brain, cross-group auth, 4 new CI jobs + **Epic 79 (6/6: Production Alerting & SLA Monitoring)** — SLA recording rules (3 tiers), 8 SLA alerts, AlertManager v0.28.1 container, Grafana SLA dashboard, 8 Zeek security alerts, admin-api webhook (AlertStore with TTL) |
| Mar 16 | Sprint 35 complete — **aiohttp CVE fix** (8 CVEs, 40 files pinned >=3.13.3) + **npm CVE fix** (basic-ftp CVSS 9.1) + **Epic 80 Phase 1** (158 new security tests: auth, database, api_key_service, _startup) + conftest.py fixes across 3 Tier 1 services |
| Mar 17 | Sprint 37 — **Epic 81 (5/5: Docker Deployment & CVE Verification)** — 58/58 containers healthy. Fixes: homeiq-observability aiohttp dep, postgres-exporter v0.17.0 (PG17), Zeek 8.1.1 compat (Dockerfile, packages, configs, CRLF). All 44 Python containers verified on aiohttp 3.13.3 |
| Mar 18 | Sprint 38 — **Epic 85 (10/10: Data-API Unit & Line Coverage Expansion)** — 443 new unit tests across 20 test files. Line coverage 8.8% → 40%+. Covers: entity enrichment, device classification, flux utils (security-critical), metrics buffer, sports writer, service lifecycle, config management, background jobs, endpoint models, auth, cache |
| Mar 18 | Sprint 39 — **Epic 86 (7/7: Zeek Native Telemetry & Capture Health Dashboard)** — Zeek 8.x telemetry on :9911, Prometheus `zeek-telemetry` scrape job, 6 recording rules (packet rates, drop ratio, memory, event queue, connections), 4 alert rules (PacketDropHigh, MemoryPressure, EventQueueSaturated, CaptureStalled), Grafana dashboard (9 panels), healthcheck.sh telemetry check |
| Mar 18 | Sprint 41 — **Epic 90 (10/10: Ask AI → HA YAML E2E Pipeline)** — 7 backend integration tests (chat→YAML, validation service, hybrid flow), 14 YAML-asserted E2E tests, 107 blueprint service tests (suggestion scorer + rule-recommendation-ml), ask-ai-complete reliability fix (fast/slow split, resilient waits), test cleanup harness, `test-live-ai.yml` CI workflow, YAML verification matrix docs. Total new tests: ~160 |

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
