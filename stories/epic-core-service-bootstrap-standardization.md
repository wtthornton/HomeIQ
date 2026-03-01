---
epic: core-service-bootstrap-standardization
priority: high
status: open
estimated_duration: 3-4 weeks
risk_level: medium
source: Architecture review of 50 microservices (2026-03-01)
---

# Epic 12: Core Service Bootstrap Standardization

**Status:** Open
**Priority:** High (P1)
**Duration:** 3-4 weeks
**Risk Level:** Medium
**Source:** Duplicated boilerplate analysis across 50 HomeIQ microservices
**Affects:** All services in `domains/`, shared libraries in `libs/`

## Context

Every HomeIQ microservice independently implements 4 tightly-coupled bootstrap patterns: health checks, app factory, settings, and lifespan management. This results in ~5,600 lines of duplicated boilerplate across 38 services with 8+ inconsistent status value variants, no shared health framework (only admin-api uses `homeiq_data.types.health`), and divergent middleware stacking. The `DatabaseManager` standardization (completed Mar 1) proved this extraction pattern works — the same approach applies to the remaining bootstrap stack.

## Stories

### Story 12.1: HealthCheckManager — Standardized Health Endpoints

**Priority:** High | **Estimate:** 2 days | **Risk:** Medium

**Problem:** 38 services implement `/health` endpoints independently with 8+ status value variants (`healthy`, `ok`, `pass`, `alive`, `live`, `critical`, `warning`, `starting`). Database `SELECT 1` probes are copy-pasted across 80+ files. Only admin-api uses the shared `homeiq_data.types.health` utilities. No consistent liveness vs. readiness separation.

**Files:**
- New: `libs/homeiq-resilience/src/homeiq_resilience/health_manager.py`
- Modify: `libs/homeiq-resilience/src/homeiq_resilience/__init__.py` (add export)
- Migrate: 38 health routers in `domains/*/*/src/api/health_router.py` and `domains/*/*/src/main.py`

**Key examples of current duplication:**
- `domains/automation-core/ai-automation-service-new/src/api/health_router.py` — database probe + GroupHealthCheck
- `domains/automation-core/ai-query-service/src/api/health_router.py` — simple database probe
- `domains/ml-engine/rag-service/src/api/health_router.py` — multi-check readiness (DB + downstream)
- `domains/core-platform/admin-api/src/health_endpoints.py` — full dependency checks (23+ services)

**Acceptance Criteria:**
- [ ] `HealthCheckManager` class in `homeiq-resilience` with pluggable component checks (database, InfluxDB, downstream services)
- [ ] Standardized response format: `{"status": "healthy|degraded|unhealthy|starting", "service": "...", "checks": {...}}`
- [ ] Liveness (`/health`) and readiness (`/health/ready`) endpoints generated from single config
- [ ] All health endpoints return HTTP 200 for healthy/degraded/starting (project convention)
- [ ] Database `SELECT 1` probe built in — no per-service implementation needed
- [ ] `GroupHealthCheck` integration automatic when `homeiq-resilience` is installed
- [ ] 38 services migrated with no health response regressions
- [ ] Unit tests for HealthCheckManager (healthy, degraded, unavailable component scenarios)

---

### Story 12.2: Service App Factory — Standardized FastAPI Creation

**Priority:** High | **Estimate:** 2 days | **Risk:** Medium

**Problem:** 34 services duplicate ~50 lines of FastAPI initialization: CORS middleware (with inconsistent security — some allow `*` with credentials), observability instrumentation (conditional import), error handler registration, request ID tracing, and router inclusion. Middleware stacking order varies across services, causing subtle behavior differences.

**Files:**
- New: `libs/homeiq-patterns/src/homeiq_patterns/app_factory.py`
- Modify: `libs/homeiq-patterns/src/homeiq_patterns/__init__.py` (add export)
- Migrate: 34 `main.py` files across `domains/*/*/src/`

**Key examples of current duplication:**
- `domains/core-platform/data-api/src/main.py` (lines 269-445) — CORS security check, auth deps, 10+ routers
- `domains/automation-core/ai-automation-service-new/src/main.py` (lines 341-401) — CORS, observability, auth+rate-limit middleware
- `domains/ml-engine/ai-core-service/src/main.py` (lines 200-237) — request ID middleware, size limit, OpenAPI tags
- `domains/blueprints/blueprint-index/src/main.py` (lines 48-76) — minimal CORS + router

**Acceptance Criteria:**
- [ ] `create_service_app()` factory function accepting: title, version, routers, middleware list, lifespan, CORS config
- [ ] CORS security enforced: `allow_credentials=False` when `*` in origins (no per-service check needed)
- [ ] Observability middleware auto-applied when `homeiq-observability` is importable
- [ ] Error handler registration automatic via `homeiq_patterns.register_error_handlers`
- [ ] Request ID / correlation ID middleware included by default
- [ ] 34 services migrated with identical HTTP behavior (middleware order preserved)
- [ ] Unit tests for factory output (middleware stack, CORS config, router registration)

---

### Story 12.3: BaseServiceSettings — Common Configuration Fields

**Priority:** High | **Estimate:** 1.5 days | **Risk:** Low

**Problem:** 16+ services define nearly identical `Settings(BaseSettings)` classes with 50-80 lines each, repeating: `service_name`, `service_port`, `log_level`, `database_url`, `postgres_url`, `database_schema`, `database_pool_size`, `database_max_overflow`, `data_api_url`, `openai_api_key`, `openai_model`, `openai_timeout`, `cors_origins`, `scheduler_enabled`, `scheduler_time`, `scheduler_timezone`. The `effective_database_url` property and `model_config = SettingsConfigDict(...)` are copy-pasted verbatim.

**Files:**
- New: `libs/homeiq-patterns/src/homeiq_patterns/base_settings.py`
- Modify: `libs/homeiq-patterns/src/homeiq_patterns/__init__.py` (add export)
- Migrate: 16+ `config.py` files across `domains/*/*/src/`

**Key examples of current duplication:**
- `domains/automation-core/ai-automation-service-new/src/config.py` — database, data-api, OpenAI, scheduler, CORS fields
- `domains/automation-core/ha-ai-agent-service/src/config.py` — database, data-api, OpenAI, HA, cache TTL fields
- `domains/energy-analytics/proactive-agent-service/src/config.py` — database, data-api, OpenAI, scheduler fields
- `domains/automation-core/ai-query-service/src/config.py` — database, data-api, OpenAI, query-specific fields
- `domains/device-management/ha-setup-service/src/config.py` — database, data-api, HA, CORS, health check fields

**Acceptance Criteria:**
- [ ] `BaseServiceSettings(BaseSettings)` class with common field groups: service identity, database, data-api, OpenAI, logging
- [ ] `effective_database_url` property built-in (resolves `POSTGRES_URL` > `DATABASE_URL` > default)
- [ ] `model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)` inherited
- [ ] Per-service settings classes inherit from `BaseServiceSettings` and add only service-specific fields
- [ ] Existing config.py files shrink from ~60 lines to ~15-20 lines (service-specific fields only)
- [ ] No behavior change for any service — all env vars still respected
- [ ] Unit tests for field resolution priority and property behavior

---

### Story 12.4: LifespanBuilder — Declarative Startup/Shutdown

**Priority:** High | **Estimate:** 2 days | **Risk:** Medium

**Problem:** 29 services implement a lifespan handler (`@asynccontextmanager async def lifespan`) with the same sequence: log startup, probe dependencies, init database, register health checks, setup observability, start background services, yield, stop services, close database. This 30-60 line pattern is copy-pasted with minor variations. Startup error handling is inconsistent — some services crash on DB failure, others degrade gracefully.

**Files:**
- New: `libs/homeiq-patterns/src/homeiq_patterns/lifespan_builder.py`
- Modify: `libs/homeiq-patterns/src/homeiq_patterns/__init__.py` (add export)
- Migrate: 29 `main.py` lifespan handlers across `domains/*/*/src/`

**Key examples of current duplication:**
- `domains/core-platform/data-api/src/main.py` (lines 237-266) — DB init, service startup/shutdown
- `domains/automation-core/ai-automation-service-new/src/main.py` (lines 256-338) — DB, dependency probing, observability, scheduler, rate limiting
- `domains/ml-engine/ai-core-service/src/main.py` (lines 156-198) — env validation, ServiceManager init/close
- `domains/energy-analytics/proactive-agent-service/src/main.py` (lines 86-132) — settings, dependencies, DB, scheduler
- `domains/blueprints/blueprint-index/src/main.py` (lines 29-46) — minimal DB init/close

**Acceptance Criteria:**
- [ ] `LifespanBuilder` class with declarative hooks: `on_startup(callback)`, `on_shutdown(callback)`, `with_database(db_manager)`, `with_dependencies([...])`, `with_scheduler(scheduler)`
- [ ] Standardized startup sequence: log deployment mode → probe dependencies → init database → register health → start services
- [ ] All database initialization uses graceful degradation (never raises — `DatabaseManager` pattern)
- [ ] Dependency probing via `wait_for_dependency()` is non-fatal by default
- [ ] Generates a FastAPI-compatible `@asynccontextmanager` lifespan from the builder
- [ ] 29 services migrated — lifespan handlers reduced from 30-60 lines to 5-10 lines
- [ ] Unit tests for startup sequence ordering, shutdown cleanup, and error isolation
