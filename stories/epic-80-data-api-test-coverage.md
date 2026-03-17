# Epic 80: Data-API Test Coverage & Security Hardening

**Priority:** P1 — Critical (8.8% coverage on Tier 1 service)
**Effort:** 5-7 days (45-60 hours)
**Dependencies:** None (all infrastructure in place)
**Service:** `domains/core-platform/data-api/` (Port 8006)

## Motivation

The data-api is the central REST gateway for the entire HomeIQ platform — health-dashboard,
admin-api, and all frontend UIs depend on it. At 8.8% test coverage (5/57 source files),
it is the single largest quality risk in the stack. Security-sensitive modules (auth, database)
have zero test coverage.

## Stories

### Phase 1: Security & Auth (Day 1)

| Story | Description | Effort |
|-------|-------------|--------|
| 80.1 | **auth.py test suite** — Bearer token validation, missing/invalid/expired tokens, header parsing, auth bypass attempts. Target: 10+ tests | 3h |
| 80.2 | **database.py test suite** — Connection pool lifecycle, query execution, transaction handling, error recovery, auth credential management. Target: 12+ tests | 4h |
| 80.3 | **api_key_service.py test suite** — Key generation, validation, rotation, revocation, rate limiting. Target: 8+ tests | 3h |

### Phase 2: Core Endpoints (Days 2-3)

| Story | Description | Effort |
|-------|-------------|--------|
| 80.4 | **devices_endpoints.py test suite** — CRUD operations, area queries, filtering, pagination, device relationships. 38+ routes, target: 25+ tests | 8h |
| 80.5 | **events_endpoints.py test suite** — Event queries, category filtering, stats aggregation, search, SSE streaming. Target: 15+ tests | 5h |
| 80.6 | **health_endpoints.py test suite** — Health check, service status, dependency checks, degraded state handling. Target: 10+ tests | 3h |
| 80.7 | **alert_endpoints.py test suite** — Alert CRUD, active alerts, summary, acknowledgement, silencing. Target: 10+ tests | 3h |

### Phase 3: Business Logic Services (Days 4-5)

| Story | Description | Effort |
|-------|-------------|--------|
| 80.8 | **entity_registry.py + entity_enrichment.py tests** — Entity relationships, capability enrichment, registry sync. Target: 12+ tests | 4h |
| 80.9 | **device_classifier.py + device_health.py tests** — Classification rules, health scoring, state transitions. Target: 10+ tests | 3h |
| 80.10 | **Remaining endpoint modules** — docker, automation_analytics, jobs, energy, sports, config, evaluation, ha_automation endpoints. Target: 20+ tests across 8 modules | 8h |

### Phase 4: Infrastructure & Integration (Days 6-7)

| Story | Description | Effort |
|-------|-------------|--------|
| 80.11 | **cache.py + config.py tests** — Cache hit/miss/eviction, config loading, env var parsing. Target: 8+ tests | 3h |
| 80.12 | **Integration tests** — Cross-endpoint flows (auth → device query → event lookup), error propagation, rate limiting under load. Target: 8+ tests | 4h |

## Acceptance Criteria

- data-api test coverage reaches **45%+** (from 8.8%)
- All security modules (auth, database, api_key_service) have dedicated test suites
- Zero security-sensitive code paths without assertion coverage
- All tests pass in CI (`pytest tests/` green)

## Target Test Count

- **Phase 1:** 30+ tests (security foundation)
- **Phase 2:** 60+ tests (endpoint coverage)
- **Phase 3:** 42+ tests (business logic)
- **Phase 4:** 16+ tests (infrastructure + integration)
- **Total:** 148+ new tests
