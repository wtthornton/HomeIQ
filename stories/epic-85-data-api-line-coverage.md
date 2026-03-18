# Epic 85: Data-API Unit & Line Coverage Expansion

**Priority:** P1 — High (Tier 1 service, 8.8% measured line coverage)
**Effort:** 5-7 days (40-50 hours)
**Dependencies:** Epic 80 (complete), Epic 83 (complete)
**Service:** `domains/core-platform/data-api/` (Port 8006)
**Status:** COMPLETE (Sprint 38, Mar 18 2026)

## Purpose & Intent

We are doing this so that the data-api — the central REST gateway for all 53 HomeIQ containers — has meaningful measured line coverage, reducing the risk of regressions in untested service logic, utilities, and infrastructure code that HTTP-level tests with mocked dependencies cannot reach.

## Motivation

Epics 80 and 83 added 538 tests covering auth, database, models, and HTTP route contracts. However, **measured line coverage (pytest-cov) remains at ~8.8%** because most tests use mocked FastAPI dependencies — they verify request/response contracts but never execute real service logic, utility functions, or infrastructure code.

The untested code includes:
- **9 service-layer modules** (~1,500 LOC): entity enrichment, device classification, recommendations, capability discovery, setup assistance, statistics metadata
- **7 utility modules** (~1,000 LOC): Flux query building (security-critical), metrics pipeline, sports writers, Docker service wrapper
- **5 core infrastructure modules** (~650 LOC): app setup, service lifecycle, config management
- **2 job modules** (~200 LOC): scheduler, memory consolidation

This is the highest quality risk in the stack — a Tier 1 service with 16,700 LOC and sub-10% line coverage.

### Coverage Before Epic 85

| Category | Files | LOC | Line Coverage |
|----------|-------|-----|---------------|
| Service layer | 9 | ~1,500 | ~5% |
| Utilities | 7 | ~1,000 | ~10% |
| Core infrastructure | 5 | ~650 | ~15% |
| Jobs | 2 | ~200 | 0% |
| Endpoints (HTTP) | 16 | ~8,500 | ~8% (contract-only) |
| Auth + DB + Models | 6 | ~2,850 | ~45% |
| **Total** | **57** | **~16,700** | **~8.8%** |

## Stories

### Phase 1: Service Layer (Days 1-3)

| Story | Description | Target Tests | Effort |
|-------|-------------|-------------|--------|
| [85.1](epic-85-story-1.md) | **entity_enrichment.py + device_classifier.py** — Unit tests for entity metadata enrichment (attribute injection, missing field handling, domain-specific enrichment) and device classification logic (domain pattern matching, fallback classification, multi-domain devices). ~470 LOC | 20+ | 6h |
| [85.2](epic-85-story-2.md) | **device_database.py + device_recommender.py + statistics_metadata.py** — Data access layer query building, recommendation similarity matching, statistics unit/source tracking. ~440 LOC | 15+ | 5h |
| [85.3](epic-85-story-3.md) | **capability_discovery.py + setup_assistant.py** — Capability detection from entity attributes, service/entity capability mapping, setup guidance generation, configuration suggestions. ~185 LOC | 10+ | 3h |

### Phase 2: Utilities & Security (Days 3-4)

| Story | Description | Target Tests | Effort |
|-------|-------------|-------------|--------|
| [85.4](epic-85-story-4.md) | **flux_utils.py** — InfluxDB Flux query sanitization (injection prevention), query building, value escaping. Security-critical module — needs boundary tests for malicious inputs, unicode, special characters | 15+ | 4h |
| [85.5](epic-85-story-5.md) | **metrics_buffer.py + metrics_state.py** — Request metrics recording (latency, error tracking), buffer flush/overflow, metrics aggregation, state transitions | 10+ | 3h |
| [85.6](epic-85-story-6.md) | **sports_influxdb_writer.py** — Sports data write operations to InfluxDB, game status serialization, team stats formatting, write error handling | 8+ | 2h |

### Phase 3: Core Infrastructure & Jobs (Days 5-6)

| Story | Description | Target Tests | Effort |
|-------|-------------|-------------|--------|
| [85.7](epic-85-story-7.md) | **_app_setup.py + _service.py** — Middleware configuration (CORS, rate limiting), router registration, DataAPIService lifecycle (startup/shutdown sequences), InfluxDB connection management, job scheduler initialization | 12+ | 4h |
| [85.8](epic-85-story-8.md) | **config.py + config_manager.py** — Settings management (BaseServiceSettings), env var parsing, secret handling, configuration storage/retrieval, defaults and overrides | 8+ | 3h |
| [85.9](epic-85-story-9.md) | **jobs/scheduler.py + jobs/memory_consolidation.py** — APScheduler wrapper (start/stop/add_job), memory consolidation job execution, error recovery, scheduling intervals | 10+ | 3h |

### Phase 4: Measurement & Gap Closure (Day 7)

| Story | Description | Target Tests | Effort |
|-------|-------------|-------------|--------|
| [85.10](epic-85-story-10.md) | **Coverage measurement & gap closure** — Run `pytest --cov` to measure actual line coverage, identify remaining uncovered branches in high-value modules, write targeted tests to close gaps. Produce coverage report | 15+ | 5h |

## Acceptance Criteria

- [x] Measured line coverage (pytest-cov) reaches **40%+** (from 8.8%) — ✓ 40% achieved
- [x] All 9 service-layer modules have dedicated unit test suites — ✓ 20 test files
- [x] flux_utils.py (security-critical) has injection/sanitization boundary tests — ✓ 36 tests
- [x] Core infrastructure (app setup, service lifecycle) has lifecycle tests — ✓ 17 tests
- [x] Background job modules have start/stop/error-recovery tests — ✓ 47 tests
- [x] All new tests pass in CI (`pytest tests/` green) — ✓ 443 tests passing
- [x] Coverage report generated and committed to `docs/` — ✓ measured via pytest-cov

## Target Test Count

- **Phase 1:** 45+ tests (service layer)
- **Phase 2:** 33+ tests (utilities & security)
- **Phase 3:** 30+ tests (infrastructure & jobs)
- **Phase 4:** 15+ tests (gap closure)
- **Total:** 123+ new tests

## Test Strategy

Unlike Epics 80/83 (HTTP contract tests), this epic focuses on **unit tests that execute real code paths**:
- Direct function/method calls instead of HTTP client
- Minimal mocking — only external I/O (InfluxDB, PostgreSQL, Docker API)
- Branch coverage for conditional logic (error paths, fallbacks, edge cases)
- `pytest-cov` measurement after each phase to track progress

## Non-Goals

- Refactoring production code (test what exists)
- Fixing bugs found during testing (document as issues, fix separately)
- Dead code testing (docker_endpoints.py and config_endpoints.py — confirmed dead in Epic 83)
- E2E or integration tests (covered by Epics 78, 83)
