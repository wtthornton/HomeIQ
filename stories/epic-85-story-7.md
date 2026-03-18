# Story 85.7 -- App Setup & Service Lifecycle Unit Tests

<!-- docsmcp:start:user-story -->

> **As a** platform engineer, **I want** unit tests covering app setup and service lifecycle, **so that** middleware configuration, router registration, and startup/shutdown sequences are validated

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that _app_setup.py (~139 LOC) and _service.py (~115 LOC) have unit tests verifying that middleware is configured correctly, all routers are registered, and the DataAPIService startup/shutdown lifecycle executes in the correct order — infrastructure code that affects every request.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

**_app_setup.py** — Configures FastAPI middleware (CORS, rate limiting, metrics collection), registers all API routers. Epic 83 discovered that docker_endpoints and config_endpoints are dead code (never registered here).

**_service.py** — DataAPIService class managing the full service lifecycle: auth initialization, InfluxDB connection, webhook detector startup, job scheduler initialization, and graceful shutdown.

These modules are the foundation of the entire service — bugs here affect all endpoints.

See [Epic 85](epic-85-data-api-line-coverage.md) for project context.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/core-platform/data-api/src/_app_setup.py`
- `domains/core-platform/data-api/src/_service.py`
- `domains/core-platform/data-api/tests/test_app_setup_unit.py` (new)
- `domains/core-platform/data-api/tests/test_service_lifecycle_unit.py` (new)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Read _app_setup.py and map middleware and router registration
- [ ] Write tests verifying CORS middleware is configured with expected origins
- [ ] Write tests verifying rate limiting middleware is attached
- [ ] Write tests verifying all active routers are registered (count and prefixes)
- [ ] Write tests verifying dead code routers (docker, config) are NOT registered
- [ ] Read _service.py and map startup/shutdown sequence
- [ ] Write tests for DataAPIService initialization — auth, rate limiter, InfluxDB client created
- [ ] Write tests for startup sequence — monitoring, InfluxDB, webhooks, scheduler started in order
- [ ] Write tests for shutdown sequence — connections closed, jobs stopped
- [ ] Write tests for startup failure handling — InfluxDB unavailable at boot
- [ ] Write tests for `_start_job_scheduler()` — scheduler configured correctly
- [ ] Write tests for partial startup failure — some components fail, others succeed
- [ ] Verify all tests pass: `pytest tests/test_app_setup_unit.py tests/test_service_lifecycle_unit.py -v`

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] _app_setup.py has 5+ tests verifying middleware and router registration
- [ ] _service.py has 7+ tests verifying lifecycle sequences
- [ ] Dead code routers confirmed absent from registration
- [ ] Startup failure handling verified (graceful degradation)
- [ ] External services (InfluxDB, PostgreSQL) mocked at connection level

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 85](epic-85-data-api-line-coverage.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_cors_middleware_configured` -- CORS middleware present with expected origins
2. `test_rate_limiting_middleware_configured` -- Rate limiter attached to app
3. `test_all_active_routers_registered` -- All active endpoint routers present
4. `test_dead_code_routers_absent` -- Docker and config routers NOT registered
5. `test_router_prefixes_correct` -- Each router has expected URL prefix
6. `test_service_init_creates_components` -- Init creates auth, rate limiter, InfluxDB client
7. `test_startup_sequence_order` -- Startup calls components in correct order
8. `test_shutdown_closes_connections` -- Shutdown closes InfluxDB and DB connections
9. `test_startup_influxdb_unavailable` -- InfluxDB failure doesn't crash startup
10. `test_start_job_scheduler` -- Scheduler started with expected jobs
11. `test_partial_startup_failure` -- Some components fail, service still starts degraded
12. `test_shutdown_idempotent` -- Multiple shutdown calls don't error

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- _app_setup.py router registration can be tested by inspecting `app.routes` after setup
- _service.py lifecycle requires mocking InfluxDB, PostgreSQL connections, and APScheduler
- Use `AsyncMock` for async startup/shutdown methods
- DataAPIService.startup() should never raise (pattern: returns bool) — verify this

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None (mocks all external dependencies)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- No dependency on other stories
- [x] **N**egotiable -- Lifecycle test depth adjustable
- [x] **V**aluable -- Foundation code affecting every request
- [x] **E**stimable -- Clear scope: 2 files, ~254 LOC
- [x] **S**mall -- 5 points, single session
- [x] **T**estable -- Lifecycle steps verifiable via mock call assertions

<!-- docsmcp:end:invest -->
