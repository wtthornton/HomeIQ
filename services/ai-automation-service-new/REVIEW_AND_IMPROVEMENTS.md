# AI Automation Service - Code Review & Improvements

**Service**: `ai-automation-service-new` (Port 8025, Tier 5)
**Reviewer**: Claude Opus 4.6 (automated deep code review)
**Date**: 2026-02-06
**Scope**: Full codebase review - `src/`, `tests/`, config files, Dockerfile, migrations

---

## Executive Summary

**Overall Health Score: 6.5 / 10**

The ai-automation-service-new is a substantial, well-structured FastAPI service implementing automation suggestion generation, YAML compilation, and Home Assistant deployment. The architecture shows good separation of concerns with proper dependency injection, async patterns, and a well-designed hybrid flow (Intent -> Plan -> Validate -> Compile -> Deploy). However, the codebase has several critical security issues, significant resource management problems, moderate code quality concerns, and test coverage gaps that should be addressed before production deployment.

**Strengths**:
- Clean dependency injection using FastAPI's `Depends` with `Annotated` types
- Good async/await patterns throughout
- Well-designed hybrid flow architecture (template-based compilation)
- Proper retry logic with tenacity on external API calls
- Reasonable database schema with migration support
- Non-root Docker user with multi-stage build

**Key Concerns**:
- Critical authentication bypass vulnerability
- HTTP clients leaked on every request (no connection pooling reuse)
- Proxy routers duplicate code extensively (DRY violation)
- Stale/inaccurate router tests that may pass but don't test actual behavior
- Error messages leak internal details to API consumers
- Missing input validation on several endpoints
- `get_usage_stats` loads ALL suggestions into memory

---

## Critical Issues (Must Fix)

### C1. Authentication Bypass via `X-Internal-Service` Header

**File**: `src/api/middlewares.py:149`
**Severity**: CRITICAL
**Type**: Security

The `AuthenticationMiddleware._is_internal_request()` method trusts a plain HTTP header `X-Internal-Service: true` to bypass authentication entirely. Any external client can add this header to skip all auth checks.

```python
# CURRENT (VULNERABLE) - line 149
if request.headers.get("X-Internal-Service") == "true":
    return True
```

**Impact**: Complete authentication bypass. Any unauthenticated user can access all protected endpoints by adding a single header.

**Recommendation**: Remove the header-based bypass entirely. Internal service-to-service auth should rely solely on network-level controls (IP ranges) or use a shared secret/mTLS. If the header must be kept, it should require a cryptographic signature or shared secret that cannot be forged by external clients.

---

### C2. No API Key Validation - Keys Accepted Without Verification

**File**: `src/api/middlewares.py:178-198`
**Severity**: CRITICAL
**Type**: Security

The `AuthenticationMiddleware` accepts ANY non-empty string as a valid API key. There is no validation against stored keys, no lookup, no hash comparison - any string works.

```python
# CURRENT (VULNERABLE) - lines 186-198
if not api_key:
    return JSONResponse(status_code=401, ...)

# api_key is NEVER validated - any non-empty string passes
request.state.api_key = api_key
request.state.authenticated = True
```

**Impact**: Authentication is effectively non-existent for external requests. Anyone who provides any Bearer token or X-HomeIQ-API-Key header gains full access.

**Recommendation**: Implement actual API key validation against a store (database, environment variable set, or external auth service). At minimum, validate against a configured secret.

---

### C3. Error Messages Leak Internal Details

**File**: `src/api/error_handlers.py:49`, `src/api/deployment_router.py:269`
**Severity**: HIGH
**Type**: Security (Information Disclosure)

The `handle_route_errors` decorator passes `str(e)` directly as the HTTP response detail. Internal exception messages (database errors, file paths, stack traces) are returned to API consumers.

```python
# error_handlers.py:49
raise HTTPException(
    status_code=default_status_code,
    detail=str(e)  # Leaks internal error details
)

# deployment_router.py:269
raise HTTPException(status_code=500, detail=f"Failed to deploy automation: {str(e)}")
```

**Impact**: Internal implementation details, database schema information, file paths, and service URLs can be exposed to attackers.

**Recommendation**: Log the full error internally, but return a generic error message to the client. Use error codes for client-side handling.

---

### C4. HTTP Clients Created Per-Request, Never Closed

**File**: `src/api/dependencies.py:69-95`
**Severity**: HIGH
**Type**: Resource Leak / Performance

Every dependency injection call creates a new `DataAPIClient`, `OpenAIClient`, `HomeAssistantClient`, and `YAMLValidationClient` instance. Each creates a new `httpx.AsyncClient` with connection pooling. These clients are never closed, leaking connections.

```python
# dependencies.py:69-71 - New client on every request
def get_data_api_client() -> DataAPIClient:
    return DataAPIClient(base_url=settings.data_api_url)  # New httpx.AsyncClient created

# Similarly for get_ha_client(), get_openai_client(), get_yaml_validation_client()
```

**Impact**: Connection pool exhaustion under load. Each request creates 2-4 HTTP clients with 10 max connections each. Under moderate load (100 req/s), thousands of orphaned connections accumulate.

**Recommendation**: Use application-scoped singletons for HTTP clients, created during lifespan startup and closed during shutdown. Store them on `app.state` and inject via dependency.

---

### C5. `get_usage_stats` Loads All Suggestions Into Memory

**File**: `src/services/suggestion_service.py:312-314`
**Severity**: HIGH
**Type**: Performance / Memory

The `get_usage_stats()` method loads ALL suggestions into memory to count them by status, instead of using SQL aggregation.

```python
# CURRENT - loads entire table
query = select(Suggestion)
result = await self.db.execute(query)
all_suggestions = result.scalars().all()  # ALL rows loaded

stats = {"total": len(all_suggestions), ...}
for suggestion in all_suggestions:
    status = suggestion.status or "unknown"
    stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
```

**Impact**: With thousands of suggestions, this causes high memory usage and slow response times. O(N) memory and time complexity for a simple COUNT query.

**Recommendation**: Use SQL GROUP BY:
```python
from sqlalchemy import func
query = select(Suggestion.status, func.count()).group_by(Suggestion.status)
result = await self.db.execute(query)
stats["by_status"] = {status: count for status, count in result.all()}
```

---

### C6. Query Suggestions Loads All Records Into Memory

**File**: `src/api/suggestion_router.py:379-406`
**Severity**: HIGH
**Type**: Performance / Memory

The `query_suggestions` endpoint loads ALL suggestions with JSON into memory, then filters and paginates in Python.

```python
# Lines 380-382 - loads ALL suggestions
stmt = select(Suggestion).where(Suggestion.automation_json.isnot(None))
result = await db.execute(stmt)
suggestions = result.scalars().all()  # ALL rows

# Then filters in Python
automations = [s.automation_json for s in suggestions if s.automation_json]
matching_automations = query_svc.query(automations, filters)

# Then paginates in Python
paginated = matching_automations[offset:offset + limit]
```

**Impact**: O(N) memory usage with full table scans. With large datasets, this will cause OOM errors and extreme latency.

**Recommendation**: Push filtering to SQL where possible (JSON field queries in SQLite). For complex JSON queries, consider adding indexed materialized columns for frequently queried fields.

---

## Major Issues (Should Fix)

### M1. Proxy Router Code Duplication (3x identical proxy functions)

**Files**: `src/api/pattern_router.py`, `src/api/synergy_router.py`, `src/api/analysis_router.py`
**Type**: DRY Violation

Three proxy routers each implement nearly identical `_proxy_to_pattern_service()` functions with slight variations. The synergy_router has improved error handling that the other two lack.

**Recommendation**: Extract a shared `ProxyClient` class or utility function that all three routers use.

---

### M2. Double Entity Context Fetch in YAML Generation

**File**: `src/services/yaml_generation_service.py:313-344`
**Type**: Performance

In `_generate_yaml_from_homeiq_json`, entity context is fetched twice: once at line 338 (stored in local variable but never used for prompt building), and again inside `generate_homeiq_json()` at line 196.

```python
# Line 338 - fetched but only used elsewhere
entity_context = await self._fetch_entity_context()  # Fetch #1

# Line 341-344 - generate_homeiq_json() fetches entity_context AGAIN at line 196
automation_json = await self.generate_homeiq_json(
    suggestion=suggestion,
    homeiq_context=homeiq_context
)
# Inside generate_homeiq_json, line 196:
# entity_context = await self._fetch_entity_context()  # Fetch #2
```

**Impact**: Two redundant HTTP calls to Data API per YAML generation, doubling latency.

**Recommendation**: Fetch entity context once and pass it through, or cache it with a short TTL.

---

### M3. `defaultdict(lambda)` for Rate Limiting is Not Thread-Safe

**File**: `src/api/middlewares.py:31-37`
**Type**: Concurrency Bug

The rate limit buckets use `defaultdict(lambda: {...})` which creates new entries on access. Under concurrent async access, the token bucket read-modify-write at lines 82-87 has a race condition.

```python
# Lines 82-87 - non-atomic read-modify-write
elapsed = current_time - bucket["last_refill"]
tokens_to_add = elapsed * bucket["refill_rate"]
bucket["tokens"] = min(bucket["capacity"], bucket["tokens"] + tokens_to_add)
bucket["last_refill"] = current_time
```

**Impact**: Under high concurrency, tokens can be double-counted or consumed incorrectly. In practice, this is moderate risk since Python's GIL provides some protection for single-process deployment.

**Recommendation**: Use `asyncio.Lock` per bucket, or switch to Redis-based rate limiting for production.

---

### M4. Deprecated `declarative_base()` Usage

**File**: `src/database/models.py:12`
**Type**: Code Quality / Deprecation

Uses the legacy `declarative_base()` import path which is deprecated in SQLAlchemy 2.x.

```python
from sqlalchemy.ext.declarative import declarative_base  # Deprecated
Base = declarative_base()
```

**Recommendation**: Use the modern pattern:
```python
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase):
    pass
```

---

### M5. `datetime.utcnow()` Used Instead of `datetime.now(timezone.utc)`

**File**: `src/services/automation_combiner.py:131`
**Type**: Code Quality / Deprecation

`datetime.utcnow()` is deprecated in Python 3.12+ and returns a naive datetime.

```python
created_at=datetime.utcnow(),  # Deprecated, returns naive datetime
```

**Recommendation**: Use `datetime.now(timezone.utc)` consistently (already used elsewhere in the codebase).

---

### M6. VersioningService References Non-Existent `ha_client.set_state()` Method

**File**: `src/services/versioning_service.py:246-249`
**Type**: Bug

The `restore_state()` method calls `self.ha_client.set_state()`, but `HomeAssistantClient` has no `set_state()` method.

```python
await self.ha_client.set_state(  # Method doesn't exist on HomeAssistantClient
    entity_id=entity_id,
    state=state,
    attributes=attributes
)
```

Similarly, `_create_snapshot()` calls `self.ha_client.get_state()` which also doesn't exist.

**Impact**: `restore_state()` and `_create_snapshot()` will always raise `AttributeError` at runtime.

---

### M7. Template Library Recreated Per-Request in Compile/Validate Routers

**Files**: `src/api/automation_compile_router.py:46-51`, `src/api/automation_validate_router.py:42-47`
**Type**: Performance

Unlike the plan router which caches the template library as a module-level global, the compile and validate routers create a new `TemplateLibrary` instance on every request, re-reading and parsing all template JSON files from disk each time.

```python
# automation_compile_router.py:46-51 - no caching
def get_template_library() -> TemplateLibrary:
    from pathlib import Path
    current_file = Path(__file__)
    templates_dir = current_file.parent.parent / "templates" / "templates"
    return TemplateLibrary(templates_dir=templates_dir)  # Disk I/O every request
```

**Recommendation**: Use the same global caching pattern as `automation_plan_router.py`.

---

### M8. Alembic `run_migrations()` Uses Sync `command.upgrade` in Async Context

**File**: `src/database/__init__.py:88-113`
**Type**: Bug / Architecture

The `run_migrations()` function is declared `async` but calls `command.upgrade(alembic_cfg, "head")` which is a synchronous blocking call. This will block the event loop during startup.

**Impact**: Service startup blocks the event loop while migrations run. For simple migrations this is brief, but for complex migrations it could cause timeouts.

**Recommendation**: Run migrations in a thread executor, or run them as a separate pre-startup step.

---

### M9. `get_db()` Auto-Commits on Success

**File**: `src/database/__init__.py:77-85`
**Type**: Architecture

The `get_db()` dependency automatically commits the session after the request handler returns. This means read-only endpoints also perform unnecessary commit operations.

```python
async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()  # Always commits, even on reads
        except Exception:
            await session.rollback()
            raise
```

**Impact**: Unnecessary database overhead on read-only endpoints. Also, if a handler raises an HTTPException (which is caught by FastAPI, not by this try/except), the commit still happens.

**Recommendation**: Don't auto-commit in the dependency. Let service methods manage their own transactions explicitly.

---

### M10. Preference Router Stub Ignores Updates

**File**: `src/api/preference_router.py:75-102`
**Type**: Misleading API

The `PUT /api/v1/preferences` endpoint accepts update requests but silently ignores them, always returning defaults. The API returns 200 OK, misleading clients into thinking the update was persisted.

**Impact**: Users believe their preference changes are saved when they are not.

**Recommendation**: Either implement storage or return 501 Not Implemented.

---

## Minor Issues (Nice to Fix)

### m1. Unused Imports

- `src/api/pattern_router.py:4`: `Any` imported but only used in type hint that could be removed
- `src/api/pattern_router.py:11`: `get_authenticated_user` imported but never used
- `src/api/synergy_router.py:4`: `Any` imported but unused
- `src/api/synergy_router.py:11`: `get_authenticated_user` imported but never used
- `src/api/analysis_router.py:4`: `Any` imported but unused
- `src/api/analysis_router.py:11`: `get_authenticated_user` imported but never used
- `src/api/deployment_router.py:15`: `Depends` imported but `handle_route_errors` decorator is used instead
- `src/api/health_router.py:63`: `Response` imported inside function body (should be at top)
- `src/api/middlewares.py:12`: `Annotated` imported but never used
- `src/api/middlewares.py:15`: `HTTPBearer`, `HTTPAuthorizationCredentials` imported but never used

### m2. Emoji in Log Messages

**Files**: Multiple (`main.py`, `middlewares.py`, `database/__init__.py`, etc.)
**Type**: Code Quality

Log messages contain emoji characters which can cause issues with log aggregation systems, grep, and terminals that don't support Unicode.

### m3. `sys.path` Manipulation

**Files**: `src/main.py:37`, `src/clients/openai_client.py:29-51`
**Type**: Code Quality

Multiple `sys.path.insert()` calls to find shared modules. The OpenAI client has particularly complex path resolution logic with 4 candidate paths. This is fragile and should be handled by proper package installation or `PYTHONPATH` configuration.

### m4. `scheduler_time` Parsing Has No Validation

**File**: `src/main.py:114-116`
**Type**: Error Handling

The scheduler time parsing assumes "HH:MM" format but doesn't validate. Invalid values like "abc" or "25:99" will cause unhandled exceptions.

```python
schedule_time = settings.scheduler_time.split(":")
hour = int(schedule_time[0])     # No validation
minute = int(schedule_time[1])   # No validation
```

### m5. `coverage.json` and `htmlcov/` Committed to Repository

**Type**: Repository Hygiene

Coverage artifacts (`coverage.json`, `htmlcov/`) should be in `.gitignore`, not tracked in the repository.

### m6. `.ruff_cache` Directories in Source Tree

Multiple `.ruff_cache` directories exist inside `src/api/`, `src/services/`, `src/clients/`, etc. These should be gitignored.

### m7. `tests/tests/` Nested Test Directory

**File**: `tests/tests/test_test_suggestion_router.py`

There's a nested `tests/tests/` directory which suggests accidental duplication.

### m8. Config Model Uses `class Config` Instead of `model_config`

**File**: `src/api/preference_router.py:29,43`

Pydantic v2 prefers `model_config` over inner `class Config`. The preference router models use the deprecated pattern while `src/config.py` correctly uses `model_config = ConfigDict(...)`.

### m9. `aiohttp` in Requirements but Never Used

**File**: `requirements.txt:18`

`aiohttp>=3.13.2,<4.0.0` is listed as a dependency but the codebase exclusively uses `httpx` for HTTP client operations. This adds unnecessary container size.

---

## Enhancement Recommendations

### E1. Add Request/Response Logging Middleware

Currently there's no structured request/response logging. Add middleware that logs:
- Request method, path, duration
- Response status code
- Correlation ID (already partially supported via observability)

### E2. Add Circuit Breaker for External Service Calls

The Data API, OpenAI, and HA clients use retry logic but no circuit breaker. When a downstream service is completely down, retries compound the problem. Consider using `tenacity` with a circuit breaker pattern or the `pybreaker` library.

### E3. Add OpenAPI Response Models to All Endpoints

Many endpoints return `dict[str, Any]` without response models. Adding Pydantic response models would improve API documentation and enable client code generation.

### E4. Add Database Connection Health to Rate Limit / Background Tasks

The background rate limit cleanup task runs silently. If it fails, there's no visibility. Add health metrics for background tasks.

### E5. Implement Proper Cost Tracking in OpenAI Client

The `total_cost_usd` field in `OpenAIClient` is always 0.0. If cost tracking is desired, implement actual cost calculation based on model and token count.

### E6. Add Pagination to `list_deployed_automations`

`DeploymentService.list_deployed_automations()` calls `ha_client.list_automations()` which fetches ALL states from HA and filters. This should support pagination.

### E7. Consider Moving to Mapped Column Syntax for SQLAlchemy 2.x

The database models use the legacy `Column()` syntax. Modern SQLAlchemy 2.x supports `Mapped[type]` annotations which provide better type checking.

---

## Architecture Improvement Suggestions

### A1. Introduce a Shared Service Registry / Client Pool

Create a `ServiceRegistry` class managed by the FastAPI lifespan that holds singleton instances of all HTTP clients. This solves C4 (resource leaks) and ensures clean shutdown.

```
Lifespan startup:
  -> Create DataAPIClient singleton
  -> Create OpenAIClient singleton
  -> Create HAClient singleton
  -> Store on app.state

Dependency injection:
  -> Read from app.state (no new instances)

Lifespan shutdown:
  -> Close all clients
```

### A2. Extract Shared Proxy Logic

The pattern/synergy/analysis proxy routers should share a common `ServiceProxy` class that handles:
- Header forwarding
- Error handling (use synergy_router's improved version as the base)
- Timeout configuration
- Retry logic

### A3. Separate Read and Write Database Dependencies

Instead of a single `get_db()` that auto-commits, provide:
- `get_db_read()`: Read-only session (no commit)
- `get_db_write()`: Write session (commits on success)

This makes transaction boundaries explicit and avoids unnecessary commits.

### A4. Add Idempotency Keys for Deployment Operations

Deployment operations (`deploy_suggestion`, `deploy_compiled_automation`) should support idempotency keys to prevent duplicate deployments from network retries.

---

## Test Coverage Analysis

### Current Test Files (28 files):
- `test_main.py` - App initialization tests
- `test_suggestion_router.py` - Suggestion endpoint tests
- `test_deployment_router.py` - Deployment endpoint tests
- `test_health_router.py` - Health check tests
- `test_safety_validation.py` - Safety validation unit tests
- `test_data_api_client.py` - Data API client tests
- `test_llm_integration.py` - LLM integration tests
- `test_yaml_validation.py` - YAML validation tests
- `test_services_integration.py` - Service integration tests
- `test_performance.py` - Performance tests
- `test_json_*` (5 files) - JSON workflow tests
- `test_version_aware_renderer.py` - Version-aware rendering tests
- `test_database_init.py` - Database initialization tests
- `test_ha_2026_1_trigger_types.py` - HA trigger type tests
- `tests/services/` (2 files) - YAML generation service tests
- `tests/clients/` (1 file) - OpenAI client tests
- `tests/e2e/` (3 files) - End-to-end tests
- `tests/integration/` (1 file) - Integration tests

### Coverage Gaps:

1. **No tests for proxy routers** (`pattern_router`, `synergy_router`, `analysis_router`)
2. **No tests for preference router**
3. **No tests for `automation_plan_router`**, `automation_validate_router`, `automation_compile_router`, `automation_lifecycle_router`
4. **No tests for `intent_planner.py`** service
5. **No tests for `template_validator.py`** service
6. **No tests for `yaml_compiler.py`** service
7. **No tests for `versioning_service.py`** (including the broken `set_state`/`get_state` calls)
8. **No tests for `automation_combiner.py`** service
9. **No tests for `json_query_service.py`** service
10. **No tests for `ha_version_service.py`** service
11. **Router tests appear stale** - `test_suggestion_router.py` expects response keys like `"status": "foundation_ready"` and `"stats"` which don't match the actual router implementation
12. **`test_deployment_router.py` appears stale** - expects different response structures than what the actual routers return
13. **No tests for rate limiting behavior** (429 responses, token refill)
14. **No tests for authentication middleware** bypass scenarios

### Test Quality Issues:

- **Stale test expectations**: `test_suggestion_router.py:19-24` expects `{"status": "foundation_ready"}` but the actual `/generate` endpoint returns `{"success": True, "suggestions": [...], "count": N}`. Tests may have been written against earlier stub implementations.
- **Missing mock for `conftest.py:167`**: The `mock_ha_client` fixture in conftest.py doesn't override the actual service dependencies, so router tests may be hitting the real (or error) code paths.
- **No negative test cases** for input validation (e.g., `limit=-1`, `offset=-1`, malformed JSON payloads)

---

## Dependency Review

### `requirements.txt` Issues:

| Package | Issue |
|---------|-------|
| `aiohttp>=3.13.2` | Not used anywhere in codebase - remove |
| `apscheduler>=3.10.4,<3.11.0` | v3.x is maintenance-only; v4.0 is the actively developed version |
| `opentelemetry-instrumentation-requests` | Service uses `httpx`, not `requests` - should use `opentelemetry-instrumentation-httpx` |
| `python-dotenv` | May be unnecessary since `pydantic-settings` handles `.env` files natively |

---

## Dockerfile Review

**Score: 8/10** - Generally well-done multi-stage build.

**Positives**:
- Multi-stage build reduces final image size
- Non-root user (`appuser`)
- Health check configured
- Build cache for pip

**Issues**:
1. **No `.dockerignore`** found - may be copying unnecessary files (`.git`, `__pycache__`, `htmlcov`, `.ruff_cache`)
2. **`pip install --upgrade pip==25.2`** pins pip to a specific version that may not exist yet or could become outdated
3. **`--no-cache-dir` with `--mount=type=cache`** is contradictory - the cache mount provides caching, `--no-cache-dir` disables pip's internal cache
4. **Missing `alembic/` directory** in COPY - migrations won't be available in container
5. **No signal handling** - `CMD` should use `exec` form (which it does, good) but no SIGTERM handling mention

---

## Summary of Priority Actions

| Priority | ID | Issue | Effort |
|----------|----|-------|--------|
| P0 | C1 | Auth bypass via X-Internal-Service header | Small |
| P0 | C2 | No API key validation | Medium |
| P1 | C4 | HTTP clients leaked per-request | Medium |
| P1 | C3 | Error messages leak internal details | Small |
| P1 | C5 | get_usage_stats loads all rows | Small |
| P1 | C6 | query_suggestions loads all rows | Medium |
| P2 | M1 | Proxy router code duplication | Medium |
| P2 | M2 | Double entity context fetch | Small |
| P2 | M6 | VersioningService calls non-existent methods | Small |
| P2 | M7 | Template library recreated per-request | Small |
| P2 | M8 | Sync Alembic in async context | Small |
| P2 | M9 | get_db auto-commits on reads | Medium |
| P3 | M4 | Deprecated declarative_base() | Small |
| P3 | M5 | Deprecated datetime.utcnow() | Trivial |
| P3 | m9 | Unused aiohttp dependency | Trivial |

---

## Fixes Applied

**Date**: 2026-02-06
**Applied by**: Claude Opus 4.6 (automated fix pass)

### Critical Issues Fixed

| ID | Fix Summary | Files Modified |
|----|-------------|----------------|
| C1 | Removed `X-Internal-Service` header bypass entirely. Internal requests now rely solely on IP-based network checks (Docker/private networks). | `src/api/middlewares.py` |
| C2 | Added API key validation against a configurable `api_keys` set in settings. When `API_KEYS` env var is set, only those keys are accepted. Empty set allows any key (dev mode). | `src/api/middlewares.py`, `src/config.py` |
| C3 | Replaced `str(e)` in all HTTP error responses with generic messages ("Check server logs for details"). Full errors still logged server-side. Fixed in: `error_handlers.py`, `deployment_router.py`, `suggestion_router.py`, `automation_compile_router.py`, `automation_validate_router.py`, `health_router.py`. | 6 files |
| C4 | HTTP clients are now application-scoped singletons. Added `init_clients()` and `close_clients()` in `dependencies.py`, called from lifespan startup/shutdown in `main.py`. Fallback to per-request creation for tests. | `src/api/dependencies.py`, `src/main.py` |
| C5 | `get_usage_stats()` now uses `SELECT status, COUNT(*) GROUP BY status` instead of loading all rows into memory. | `src/services/suggestion_service.py` |
| C6 | `query_suggestions` now adds ordering and early-exit for empty results. Full SQL-level JSON filtering not feasible in SQLite, but improved with count check and ordering. | `src/api/suggestion_router.py` |

### Major Issues Fixed

| ID | Fix Summary | Files Modified |
|----|-------------|----------------|
| M1 | Extracted shared `proxy_to_service()` function into `src/api/proxy_utils.py`. All three proxy routers (pattern, synergy, analysis) now use this shared utility with the best error handling from synergy_router. | `src/api/proxy_utils.py` (new), `src/api/pattern_router.py`, `src/api/synergy_router.py`, `src/api/analysis_router.py` |
| M2 | Removed duplicate `_fetch_entity_context()` call in `_generate_yaml_from_homeiq_json()`. Entity context is now fetched only once inside `generate_homeiq_json()`. | `src/services/yaml_generation_service.py` |
| M3 | Added `asyncio.Lock` per rate-limit bucket for thread-safe token bucket operations. Replaced `defaultdict` with explicit bucket creation. | `src/api/middlewares.py` |
| M4 | Replaced deprecated `from sqlalchemy.ext.declarative import declarative_base` with modern `from sqlalchemy.orm import DeclarativeBase` class pattern. | `src/database/models.py` |
| M5 | Replaced `datetime.utcnow()` with `datetime.now(timezone.utc)` in `automation_combiner.py`. | `src/services/automation_combiner.py` |
| M6 | Added `get_state()` and `set_state()` methods to `HomeAssistantClient` using the HA `/api/states/<entity_id>` endpoint. `VersioningService.restore_state()` and `_create_snapshot()` will now work at runtime. | `src/clients/ha_client.py` |
| M7 | Added module-level `_template_library` singleton caching to compile and validate routers, matching the pattern used in `automation_plan_router.py`. | `src/api/automation_compile_router.py`, `src/api/automation_validate_router.py` |
| M8 | `run_migrations()` now runs the synchronous `alembic.command.upgrade()` in a thread executor via `asyncio.get_running_loop().run_in_executor()` to avoid blocking the event loop. | `src/database/__init__.py` |
| M9 | Removed auto-commit from `get_db()` dependency. Service methods now manage their own transactions explicitly. Session still auto-rolls back on exception. | `src/database/__init__.py` |
| M10 | `PUT /api/v1/preferences` now returns `501 Not Implemented` instead of silently accepting and ignoring updates. | `src/api/preference_router.py` |

### Minor Issues Fixed

| ID | Fix Summary | Files Modified |
|----|-------------|----------------|
| m1 | Removed unused imports: `Annotated`, `HTTPBearer`, `HTTPAuthorizationCredentials`, `OrderedDict` from middlewares. Removed `Any`, `get_authenticated_user`, `httpx`, `Depends` unused imports from proxy routers (rewritten). | `src/api/middlewares.py`, proxy routers |
| m4 | Added validation for `scheduler_time` parsing: checks format, validates hour (0-23) and minute (0-59) ranges. | `src/main.py` |
| m5/m6 | Created `.gitignore` for service with entries for `coverage.json`, `htmlcov/`, `.ruff_cache/`. | `.gitignore` (new) |
| m8 | Replaced deprecated Pydantic `class Config` with `model_config` dict in preference router models. | `src/api/preference_router.py` |
| m9 | Removed unused `aiohttp>=3.13.2,<4.0.0` dependency from `requirements.txt`. | `requirements.txt` |

### Enhancement Recommendations Addressed

- **E1 (partial)**: Request timing and performance metrics already tracked by `RateLimitMiddleware` via `X-Response-Time` header and `_performance_metrics` dict.
- **A1**: Implemented via C4 fix - singleton client registry with lifespan management.
- **A2**: Implemented via M1 fix - shared `proxy_to_service()` utility.
- **A3 (partial)**: Implemented via M9 fix - removed auto-commit, services manage own transactions.

### Not Fixed (by design)

| ID | Reason |
|----|--------|
| m2 | Emoji in log messages: Left as-is since they are used consistently throughout the codebase and removing them is cosmetic. |
| m3 | `sys.path` manipulation: Requires broader packaging changes beyond this service. |
| m5 (files) | Existing committed `coverage.json`/`htmlcov` files not removed - `.gitignore` added to prevent future commits. |
| m7 | Nested `tests/tests/` directory: Not modified to avoid breaking test discovery configurations. |
| E2-E6 | Enhancement recommendations deferred - require architectural decisions beyond a fix pass. |
