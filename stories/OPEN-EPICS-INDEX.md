# HomeIQ — Open Epics & Stories Index

**Created:** 2026-02-27 | **Updated:** 2026-03-01
**Total:** 15 Epics, 82 Stories, ~395+ files addressed

## Execution Order & Dependencies

```
Sprint 0 (COMPLETE)
└── Epic 0: SQLite Removal [P0, 3-5 days]                  ← COMPLETE (356 files cleaned)

Sprint 1 (Week of Mar 3)
├── Epic 1: Frontend Security Hardening [P0, 3-5 days]     ← parallel with Sprint 0
├── Epic 4: Observability Dashboard Fixes [P1, 1-2 weeks]  ← can parallel
└── Epic 6 Story 1: Phase 3 Prerequisites [P1, 4h]

Sprint 2 (Mar 10-21)
├── Epic 2: Health Dashboard Quality [P1, 2-3 weeks]
├── Epic 3: AI Automation UI Quality [P1, 2-3 weeks]
└── Epic 6 Stories 5-7: Test Stub Cleanup [P2, 4 days]

Sprint 3 (Mar 17-28) — overlaps Sprint 2
├── Epic 6 Stories 2-4: ML Library Upgrades [P1, 8 days]
└── Epic 8: Production Deployment [P1, 2 weeks]            ← after security hardening

Sprint 4 (Apr — future)
├── Epic 5: Frontend Framework Upgrades [P2, 3-4 weeks]
└── Epic 7: Feature Gaps [P2-P3, 4-6 weeks]

Sprint 5 (Apr-May — Shared Library Standardization)
├── Epic 12: Core Service Bootstrap [P1, 3-4 weeks]  ← HealthCheck, AppFactory, Settings, Lifespan
├── Epic 13: External Connectors [P1, 2-3 weeks]     ← InfluxDB, DataAPI, HTTP, OpenAI
└── Epic 14: Background Processing [P2, 1-2 weeks]   ← TaskManager, Scheduler
```

## Epic Summary

| # | Epic | File | Priority | Stories | Duration | Status |
|---|------|------|----------|---------|----------|--------|
| 0 | [SQLite Removal](epic-sqlite-removal.md) | `epic-sqlite-removal.md` | **P0 Critical** | 10 | 3-5 days | **Complete** |
| 1 | [Frontend Security Hardening](epic-frontend-security-hardening.md) | `epic-frontend-security-hardening.md` | **P0 Critical** | 6 | 3-5 days | Open |
| 2 | [Health Dashboard Quality](epic-health-dashboard-quality.md) | `epic-health-dashboard-quality.md` | P1 High | 8 | 2-3 weeks | Open |
| 3 | [AI Automation UI Quality](epic-ai-automation-ui-quality.md) | `epic-ai-automation-ui-quality.md` | P1 High | 8 | 2-3 weeks | Open |
| 4 | [Observability Dashboard Fixes](epic-observability-dashboard-fixes.md) | `epic-observability-dashboard-fixes.md` | P1 High | 8 | 1-2 weeks | Open |
| 5 | [Frontend Framework Upgrades](epic-frontend-framework-upgrades.md) | `epic-frontend-framework-upgrades.md` | P2 Medium | 5 | 3-4 weeks | Open |
| 6 | [Backend Completion](epic-backend-completion.md) | `epic-backend-completion.md` | P1 High | 7 | 2-3 weeks | Open |
| 7 | [Feature Gaps](epic-feature-gaps.md) | `epic-feature-gaps.md` | P2 Medium | 6 | 4-6 weeks | Open |
| 8 | [Production Deployment](epic-production-deployment.md) | `epic-production-deployment.md` | P1 High | 8 | 2 weeks | Open |
| 9 | [TAPPS Quality Gate Compliance](epic-tapps-quality-gate-compliance.md) | `epic-tapps-quality-gate-compliance.md` | P1 High | 3 | 1 week | **In Progress** (2/3) |
| 10 | [Browser Review – AI Automation UI](epic-browser-review-ai-automation-ui.md) | `epic-browser-review-ai-automation-ui.md` | P1 High | 4 | 2-3 weeks | **In Progress** (2/4) |
| 11 | [Browser Review – Health Dashboard](epic-browser-review-health-dashboard.md) | `epic-browser-review-health-dashboard.md` | P1 High | 5 | 2-3 weeks | **In Progress** (2/5) |
| 12 | [Core Service Bootstrap Standardization](epic-core-service-bootstrap-standardization.md) | `epic-core-service-bootstrap-standardization.md` | P1 High | 4 | 3-4 weeks | Open |
| 13 | [External Service Connector Standardization](epic-external-service-connector-standardization.md) | `epic-external-service-connector-standardization.md` | P1 High | 4 | 2-3 weeks | Open |
| 14 | [Background Processing Standardization](epic-background-processing-standardization.md) | `epic-background-processing-standardization.md` | P2 Medium | 2 | 1-2 weeks | Open |

## Story Count by Priority

| Priority | Count | Description |
|----------|-------|-------------|
| P0 Critical | 16 | DB migration (10, complete) + Security hardening (6) |
| P1 High | 40 | Quality, performance, testing, deployment, browser review |
| P1 High | 8 | Shared library standardization (Epics 12-13) |
| P2 Medium | 13 | Framework upgrades, feature integrations, background processing (Epic 14) |
| P3 Low | 4 | ML model training, placeholder implementations |
| P1 High (complete) | 6 | Browser review (4) + TAPPS (2) done in Sprint 1.5 |
| **Total** | **82** | |

## Key Dates

| Date | Milestone |
|------|-----------|
| Feb 27 | Sprint 0 complete — SQLite fully removed, PostgreSQL is sole database |
| Mar 3 | Sprint 1 starts — security hardening + observability fixes |
| ~Mar 17 | Production deployment eligible (DB migration done, security next) |
| Apr | Frontend framework upgrades + feature gap work begins |

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
