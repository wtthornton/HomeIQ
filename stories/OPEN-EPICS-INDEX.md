# HomeIQ — Open Epics & Stories Index

**Created:** 2026-02-27 | **Updated:** 2026-03-06 (Sprint 8 planning: Pattern Detection + ML Upgrades)
**Total:** 39 Epics, 258 Stories, ~700+ files addressed

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
└── Result: 52/53 healthy (ai-core-service needs AI_CORE_API_KEY env var)

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

Sprint 8 (PLANNED — Mar 2026) — Pattern Detection + ML Upgrades
├── Epic 37: Pattern Detection Expansion [P1]               ← OPEN (10 stories, 8 new detectors)
└── Epic 38: ML Dependencies Upgrade [P2]                   ← OPEN (8 stories, sentence-transformers 5.x + more)
```

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
| 37 | [Pattern Detection Expansion](epic-pattern-detection-expansion.md) | `epic-pattern-detection-expansion.md` | P1 High | 10 | 2-3 weeks | **Open** (8 new detectors from stale branch) |
| 38 | [ML Dependencies Upgrade](epic-ml-dependencies-upgrade.md) | `epic-ml-dependencies-upgrade.md` | P2 Medium | 8 | 1-2 weeks | **Open** (sentence-transformers 5.x) |

## Story Count by Priority

| Priority | Count | Description |
|----------|-------|-------------|
| P0 Critical | 28 | DB migration (10) + Security (6) + Tier 1 hardening (4) + Memory Foundation (6) + Embed Testing (2) ✅ |
| P1 High | 132 | Quality, testing, deployment, browser review, TAPPS, Docker, Memory (18), Pattern Detection (10) |
| P2 Medium | 41 | Framework upgrades, feature integrations, Trust model (7), ML Upgrades (8) |
| P3 Low | 7 | ML model training, placeholder implementations, Seasonal/Frequency detectors (3) |
| **Total** | **258** | 240 complete (37 epics) + 18 open (2 epics) |

## Sprint 2 Results (COMPLETE — Mar 4, Agent Teams)

**Executed via 2-wave agent teams in a single session:**

```
Wave 1 (parallel, ~10 min):
├── lint-datetime:  Stories 16.1 + 16.4 — 215 files, UP017/UP041/DTZ003
├── lint-imports:   Stories 16.2 + 16.5 + 16.6 — 653 files, I001/F401/ARG
├── lint-security:  Story 16.3 — 6 files, S104 suppression
└── lib-hardener:   Stories 20.1-20.5 — lint fixes alone pushed all libs to 81.6+

Wave 2 (parallel, ~30 min):
├── tier1-admin:    Story 17.1 — admin-api 67.2 → 80.34 (decomposed to 7 modules)
├── tier1-ws-data:  Stories 17.2+17.3 — ws 70.9→84.94, data-api 72.1→84.9+
├── collector-fixer: Stories 18.1-18.6 — all 8 data collectors pass 70+
├── lowscore-fixer-1: Stories 19.1-19.3 — activity-writer 51.9→81.9, ha-setup 54.4→77.0, ml-service 57.1→74.9
└── lowscore-fixer-2: Stories 19.4-19.7 — ai-core 71.7, openvino 71.4, ha-ai-agent 73.4, auto-linter 75.7, auto-trace 74.5

Actual Outcome:
  Pass rate: 45% → ~90%+ (24/53 → 48+/53)
  Tier 1: 0/3 strict pass → 3/3 (admin 80.3, ws 84.9, data-api 84.9)
  Libs: 0/5 strict pass → 5/5 (all 81.6+)
  Data collectors: 0/8 → 8/8
  Low-score services: 0/8 → 8/8 (activity-writer biggest jump: +30 points)
```

## Sprint 3 Results (COMPLETE — Mar 4, Agent Teams)

**Executed via 2-wave agent teams in a single session:**

```
Wave 1 (parallel):
├── docker-isolation:     Epic 21 (Stories 21.1-21.5) — 9 compose name directives, 2 prefix fixes, ensure-network scripts, 2 build context alignments
└── dockerfile-hardener:  Epic 23 (Stories 23.1-23.8) — 2 root-user fixes, 4 healthchecks, 3 UID fixes, 3 multi-stage conversions, 3 install order fixes, 2 httpx→urllib, 1 EXPOSE, CRLF + .gitattributes

Wave 2 (parallel, after Wave 1):
├── volume-decoupler:     Epic 22 (Stories 22.1-22.3) — homeiq_logs + ai_automation_data + ai_automation_models decoupled, docs written
└── deployment-tooling:   Epic 24 (Stories 24.1-24.5) — deploy.sh archived, domain.sh + start-stack.sh created, deploy-phase-5 updated

Actual Outcome:
  Files changed: 29 modified + 9 new = 38 total
  Insertions: 195, Deletions: 557
  Security: 2 root-user Dockerfiles fixed, 4 missing healthchecks added
  Consistency: 3 UIDs standardized, 3 single-stage→multi-stage, 2 CRLF fixed
  Infrastructure: 9 compose files isolated, 3 shared volumes decoupled
  Tooling: domain.sh, start-stack.sh, ensure-network.sh (+ PowerShell equivalents)
```

## Sprint 4 Results (COMPLETE — Mar 4, Agent Teams)

**Executed via 4-wave agent teams in a single session:**

```
Wave 1 (parallel, 7 agents):
├── lib-builder:     InfluxDBManager in homeiq-data (Story 13.1)
├── frontend-1:      ai-automation-ui Vite 7 + Tailwind 4 (build passes)
├── frontend-2:      health-dashboard Vite 7 + Tailwind 4 (build passes)
├── migrate-1a:      automation-linter, yaml-validation, automation-trace
├── migrate-1b:      ai-code-executor, ha-setup, device-setup-assistant
├── migrate-1c:      activity-recognition, activity-writer, api-automation-edge
└── migrate-1d:      blueprint-suggestion, rule-recommendation-ml, ai-pattern-service

Wave 2 (parallel, 4 agents):
├── migrate-2a:      ai-core-service, openvino-service, ml-service
├── migrate-2b:      rag-service, ai-training-service, device-intelligence-service
├── migrate-2c:      ha-ai-agent-service, ai-automation-service-new, ai-query-service
└── migrate-2d:      proactive-agent, energy-forecasting, energy-correlator, sports-api, weather-api

Wave 3 (parallel, 3 agents):
├── migrate-3a:      smart-meter, air-quality, carbon-intensity, electricity-pricing (aiohttp→FastAPI)
├── migrate-3b:      calendar-service, log-aggregator, data-retention
└── migrate-3c:      admin-api, data-api, websocket-ingestion (Tier 1 critical)

Wave 4 (1 agent):
└── migrate-4a:      ha-simulator, observability-dashboard

Actual Outcome:
  Files changed: 115 (7810 insertions, 8467 deletions = -657 net lines)
  Services migrated: 38/38 to shared library pattern (create_app + ServiceLifespan + BaseServiceSettings)
  aiohttp→FastAPI: 7 services converted (smart-meter, air-quality, carbon-intensity, electricity-pricing, calendar, log-aggregator, energy-correlator)
  Frontend: 2 apps upgraded (Vite 7.3.1 + Tailwind 4 CSS-native @theme)
  New lib: InfluxDBManager in homeiq-data (consolidates 3 patterns)
  4 commits on master: 9403372f, 14755a55, c06cd2fb, ca40d3ca
```

## Sprint 5 Results (COMPLETE — Mar 4, Agent Teams)

**Sapphire-inspired HA integration — parallel agent execution:**

```
Sprint 5 (parallel, 2 agents):
├── device-control:    Epic 25 (Stories 25.1-25.7) — new ha-device-control service (port 8040)
│   ├── 20 new files: scaffold, entity resolver, controllers, routers, Dockerfile
│   └── 4 modified files: tool_schemas.py, tool_service.py, main.py, config.py (agent wiring)
└── event-bus:         Epic 28 (Stories 28.1-28.4) — house status aggregation + push
    ├── 10 new files: aggregator, WS publisher, status router, event bus client, HouseStatusCard
    └── 4 modified files: ws-ingestion main/_startup/_event_handlers, context_builder

Actual Outcome:
  New service: ha-device-control (8 tool functions, entity resolution, blacklist, circuit breaker)
  Agent wiring: 8 device control tools registered in ha-ai-agent-service (tool schemas + proxy handler)
  House status: real-time aggregation from websocket-ingestion events, WS push to frontends
  Context: agent reads house status from aggregator instead of polling HA REST
  Files: 24 new + 8 modified = 32 total
```

## Sprint 6 Results (COMPLETE — Mar 4, Agent Teams)

**Voice gateway + scheduled tasks — parallel agent execution:**

```
Sprint 6 (parallel, 2 agents):
├── voice-gateway:     Epic 26 (Stories 26.1-26.6) — new voice-gateway service (port 8041)
│   ├── 16 new files: STT (Faster Whisper), TTS (Kokoro), wake word (OpenWakeWord)
│   │   pipeline orchestrator, hot-swap admin, voice WebSocket, VoiceControls.tsx
│   └── 1 modified file: frontends/compose.yml
└── scheduled-tasks:   Epic 27 (Stories 27.1-27.5) — cron scheduler in proactive-agent
    ├── 10 new files: SQLAlchemy models, APScheduler, executor, templates, router
    │   ScheduledTasks.tsx, taskApi.ts, scheduledTask.ts
    └── 5 modified files: config.py, main.py, Sidebar.tsx, App.tsx, api.ts

Actual Outcome:
  New service: voice-gateway (STT/TTS/wake word with null-object fallback, GPU/CPU cascade)
  Voice pipeline: wake → record → STT → agent API → TTS → play (with processing lock)
  Hot-swap: runtime enable/disable of STT/TTS/wake word without restart
  Scheduler: APScheduler with cron, cooldown, jitter, 4 built-in templates
  Task executor: isolated LLM conversations via agent API, notification integration
  Frontend: VoiceControls.tsx + ScheduledTasks.tsx + sidebar nav + routing
  Files: 26 new + 6 modified = 32 total
  Quality: all Python files pass quality gate (70+), security clean
```

## Sprint 7 Results (COMPLETE — Mar 6, Agent Teams)

**Memory Brain implementation — 4-wave agent execution:**

```
Wave 1 (Epic 29 Foundation):
├── lib-foundation:    homeiq-memory shared library (14 Python files)
│   ├── models.py — SQLAlchemy models (Memory, MemoryArchive, enums)
│   ├── client.py — MemoryClient CRUD operations
│   ├── search.py — Hybrid search (FTS + pgvector, RRF fusion)
│   ├── embeddings.py — Sentence-transformers embedding generator
│   ├── decay.py — Confidence decay engine (90/180/120-day half-lives)
│   ├── consolidator.py — Mem0-style extract-consolidate-retrieve
│   ├── injector.py — LLM prompt context injection
│   └── health.py — Self-healing and health checks

Wave 2 (Epics 30+31+35.1-3, parallel):
├── ha-ai-agent:       Chat memory extraction (LLM-based fact extraction)
├── ai-automation:     Approval/rejection → outcome/boundary memories
├── rule-rec-ml:       Rating feedback → outcome memories
├── admin-api:         Memory CRUD endpoints (/api/v1/memories)
├── data-api:          Consolidation job (APScheduler, 6-hour cycle)
└── proactive-agent:   Suggestion engagement tracking

Wave 3 (Epics 32+33, parallel):
├── consolidation:     Metrics tracking, routine synthesis (weekly)
├── ha-ai-agent:       Memory injection into LLM prompts
├── suggestion-svc:    Boundary filtering, preference boosting
└── proactive-agent:   Memory-aware suggestion timing

Wave 4 (Epics 34+35.4):
├── trust-api:         GET /api/v1/memories/trust (Bayesian scoring)
├── dashboard:         TrustScoreWidget + MemoryTab components
└── self-healing:      FTS index repair, embedding backfill, graceful fallback

Actual Outcome:
  New shared library: homeiq-memory (14 files, 55+ tests)
  Services integrated: ha-ai-agent, ai-automation-service-new, rule-recommendation-ml,
                       admin-api, data-api, proactive-agent, health-dashboard
  New API endpoints: 8 memory management + 2 trust score + 3 job control
  Frontend: MemoryTab, TrustScoreWidget, useTrustScore hook
  Quality: All core files pass quality gate (70+), 0 security issues
```

## Key Dates

| Date | Milestone |
|------|-----------|
| Feb 27 | Sprint 0 complete — SQLite fully removed, PostgreSQL is sole database |
| Mar 3 | Sprint 1.5 complete — 15 epics done, TAPPS baseline captured |
| Mar 4 | Sprint 2 complete — 5 epics (16-20) done via 2-wave agent teams, pass rate 45%→90%+ |
| Mar 4 | Sprint 3 complete — 4 epics (21-24) done via 2-wave agent teams, Docker breakout complete |
| Mar 4 | Sprint 4 complete — Epic 5 + Epics 12-14 via 4-wave agent teams, 38 services + 2 frontends |
| Mar 4 | Sprint 5 complete — Epics 25+28 (device control + event bus), 32 files, 2 new services |
| Mar 4 | Sprint 6 complete — Epics 26+27 (voice gateway + scheduled tasks), 32 files |
| Mar 6 | Sprint 7 complete — Epics 29-35 (Memory Brain), homeiq-memory lib + 8 service integrations |
| Mar 6 | Sprint 8 planned — Epics 37-38 (Pattern Detection + ML Upgrades) from stale branch review |
| Mar 6 | Production redeployed — 51/51 containers healthy (voice-gateway + health check fixes) |
| ~Mar 17 | Production deployment eligible (DB migration done, security hardened, quality gated) |

## Coverage of All Known Open Items

| Open Item (from review) | Addressed In |
|---|---|
| **SQLite removal (356 files)** | **Epic 0, Stories 1-10** |
| SQLite in compose files (11 files) | Epic 0, Story 1 |
| SQLite fallback in database init (12 files) | Epic 0, Story 2 |
| SQLite in config files (11 files) | Epic 0, Story 3 |
| aiosqlite in requirements (19 files) | Epic 0, Story 4 |
| SQLite in Alembic configs (26 files) | Epic 0, Story 5 |
| SQLite test fixtures (12 files) | Epic 0, Story 6 |
| SQLite-specific scripts (14+ files) | Epic 0, Story 7 |
| SQLite in CI workflows | Epic 0, Story 8 |
| SQLite in Python source (misc) | Epic 0, Story 9 |
| SQLite in documentation (103 .md files) | Epic 0, Story 10 |
| Hardcoded API keys (3 apps) | Epic 1, Story 1 |
| CORS wildcard + credentials | Epic 1, Story 2 |
| Missing CSP headers | Epic 1, Story 3 |
| ReDoS, path traversal, XSS | Epic 1, Story 4 |
| CSRF Math.random, auth inconsistency | Epic 1, Story 5 |
| Docker security (root, health check) | Epic 1, Story 6 |
| Story 32.1 refactoring (stalled) | Epic 2, Story 1 |
| Lazy loading / bundle size | Epic 2, Story 2 |
| Polling / data fetching chaos | Epic 2, Story 3 |
| Type conflicts / any types | Epic 2, Story 4 |
| darkMode prop drilling | Epic 2, Story 5 |
| Stale data / reactive bugs | Epic 2, Story 6 |
| Console logs, dead code | Epic 2, Story 7 |
| Health dashboard test coverage (3/10) | Epic 2, Story 8 |
| API layer duplication (10 modules) | Epic 3, Story 1 |
| Monolithic components (1427 lines) | Epic 3, Story 2 |
| 3 competing state patterns | Epic 3, Story 3 |
| Dead code / stub functions | Epic 3, Story 4 |
| Accessibility gaps | Epic 3, Story 5 |
| Console logging / dependencies | Epic 3, Story 6 |
| nginx rate limiting | Epic 3, Story 7 |
| AI UI test coverage (7/60 files) | Epic 3, Story 8 |
| time.sleep() blocking Streamlit | Epic 4, Story 1 |
| Automation debugging page broken | Epic 4, Story 2 |
| Anomaly detection duplicates | Epic 4, Story 3 |
| httpx connection leak | Epic 4, Story 4 |
| Dead code / unused deps | Epic 4, Story 5 |
| Port configuration conflict | Epic 4, Story 6 |
| Zero test coverage (observability) | Epic 4, Story 7 |
| Container resource limits | Epic 4, Story 8 |
| React 18 → 19 | Epic 5, Stories 1-2 |
| Vite 6 → 7 | Epic 5, Story 3 |
| Tailwind 3 → 4 | Epic 5, Story 4 |
| Node.js / tooling | Epic 5, Story 5 |
| Phase 3 prerequisites | Epic 6, Story 1 |
| numpy/scipy upgrades | Epic 6, Story 2 |
| pandas 3.0 upgrade | Epic 6, Story 3 |
| scikit-learn + model regen | Epic 6, Story 4 |
| 6 skipped test suites | Epic 6, Story 5 |
| 42 test stubs (automation-core) | Epic 6, Story 6 |
| 13 test stubs (pattern-analysis) | Epic 6, Story 7 |
| Story 39.13 pattern integration | Epic 7, Story 1 |
| Entity extractor gap | Epic 7, Story 2 |
| Sequence transformer training | Epic 7, Story 3 |
| Transformer prediction | Epic 7, Story 4 |
| api-automation-edge placeholders | Epic 7, Story 5 |
| CI/CD step 3.7 contradiction | Epic 7, Story 6 |
| Phase 5 staged deployment | Epic 8, Stories 1-6 |
| Phase 6 post-deployment validation | Epic 8, Stories 7-8 |
| 6 npm vulnerabilities (react-force-graph) | Epic 5, Story 2 (reassessed during React 19) |
| automation-linter future roadmap | Out of scope (product roadmap, not engineering debt) |
| **TAPPS quality tracking by service (50 services + 5 libs)** | **Epic 15, Stories 0-11** |
| **Shared library standardization (~7,400 dup lines)** | **Epics 12-14** |
| Health check boilerplate (38 services, 8+ status variants) | Epic 12, Story 1 |
| FastAPI app factory duplication (34 services) | Epic 12, Story 2 |
| Settings class boilerplate (16+ services) | Epic 12, Story 3 |
| Lifespan handler duplication (29 services) | Epic 12, Story 4 |
| InfluxDB client duplication (3 implementations) | Epic 13, Story 1 |
| DataAPIClient duplication (7 implementations) | Epic 13, Story 2 |
| HTTP session lifecycle (7+ services) | Epic 13, Story 3 |
| OpenAI client duplication (3 implementations) | Epic 13, Story 4 |
| Background task management (10 services) | Epic 14, Story 1 |
| APScheduler boilerplate (11 services) | Epic 14, Story 2 |
| **Project-wide lint: UP017, I001, B104, UP041, F401** | **Epic 16, Stories 1-7** |
| **Tier 1 quality: admin-api, data-api, websocket-ingestion** | **Epic 17, Stories 1-4** |
| **Data collectors 0/8 pass rate** | **Epic 18, Stories 1-7** |
| **7 services scoring <67** | **Epic 19, Stories 1-7** |
| **5 libs failing strict (80+) gate** | **Epic 20, Stories 1-6** |
| **Per-domain Docker Desktop isolation (9 compose files)** | **Epic 21, Stories 1-5** |
| **Cross-domain volume conflicts (3 volumes, 6 compose files)** | **Epic 22, Stories 1-3** |
| **Dockerfile security: root user, missing healthcheck, UID** | **Epic 23, Stories 1-8** |
| **Deployment tooling gaps (no per-domain scripts)** | **Epic 24, Stories 1-5** |
| **36 failing Playwright E2E tests (AI Automation UI)** | **Epic 36, Stories 1-10** |
| **Memory Brain — institutional memory layer** | **Epics 29-35** |
| homeiq-memory shared library (14 files) | Epic 29, Stories 1-6 |
| Chat memory extraction (LLM-based) | Epic 30, Story 1 |
| Approval/rejection memories | Epic 30, Story 2 |
| Rating feedback memories | Epic 30, Story 3 |
| Override detection consolidation | Epic 31, Story 1 |
| Usage pattern consolidation | Epic 31, Story 3 |
| Suggestion engagement tracking | Epic 31, Story 4 |
| Consolidation job infrastructure | Epic 32, Story 1 |
| Routine synthesis | Epic 32, Story 2 |
| Memory injection in ha-ai-agent | Epic 33, Story 2 |
| Memory injection in suggestion service | Epic 33, Story 3 |
| Trust score API | Epic 34, Story 1 |
| Trust dashboard widget | Epic 34, Stories 2-3 |
| Memory admin API | Epic 35, Story 1 |
| Memory dashboard page | Epic 35, Story 2 |
| Self-healing and graceful degradation | Epic 35, Story 4 |
| **Pattern Detection Expansion (8 detectors from stale branch)** | **Epic 37, Stories 1-10** |
| Sequence Detector (A → B → C patterns) | Epic 37, Story 1 |
| Duration Detector (consistent state durations) | Epic 37, Story 2 |
| Day Type Detector (weekday vs weekend) | Epic 37, Story 3 |
| Room-Based Detector (multi-device room patterns) | Epic 37, Story 4 |
| Seasonal Detector (monthly/quarterly changes) | Epic 37, Story 5 |
| Anomaly Detector (unusual pattern deviations) | Epic 37, Story 6 |
| Frequency Detector (consistent activation counts) | Epic 37, Story 7 |
| Contextual Detector (sun/weather/occupancy) | Epic 37, Story 8 |
| Pattern Service Integration | Epic 37, Story 9 |
| Dashboard Integration | Epic 37, Story 10 |
| **ML Dependencies Upgrade (from stale branch)** | **Epic 38, Stories 1-8** |
| Embedding Compatibility Test Infrastructure | Epic 38, Story 1 |
| sentence-transformers 5.x Assessment | Epic 38, Story 2 |
| sentence-transformers Upgrade (conditional) | Epic 38, Story 3 |
| Embedding Re-indexing (conditional) | Epic 38, Story 4 |
| transformers Upgrade | Epic 38, Story 5 |
| OpenVINO + Optimum-Intel Upgrade | Epic 38, Story 6 |
| Model Regeneration (if required) | Epic 38, Story 7 |
| Documentation and Rollback Plan | Epic 38, Story 8 |
