# AI Query Service - Code Review & Improvements

**Reviewer:** Claude Code (automated deep review)
**Date:** 2026-02-06
**Service:** ai-query-service (Tier 5 - AI Automation Features)
**Port:** 8018 (internal) / 8035 (external)

---

## Executive Summary

**Overall Health Score: 5/10**

The ai-query-service is a **foundation/scaffold** implementation extracted from ai-automation-service (Epic 39, Story 39.9). The service structure is well-organized and follows good architectural patterns, but the vast majority of business logic is unimplemented (stubbed with TODOs for Story 39.10). The code that does exist has several security, configuration, and testing issues that should be addressed before the full implementation is built on top of this foundation.

**Key Strengths:**
- Clean project structure with proper separation of concerns
- Good use of FastAPI, async patterns, and SQLAlchemy async sessions
- Multi-stage Docker build with non-root user
- Observability integration (OpenTelemetry) with graceful fallback
- Proper SQLite PRAGMA configuration for performance

**Key Weaknesses:**
- No authentication or rate limiting (explicitly TODO)
- Most endpoints return hardcoded placeholder responses
- Health endpoint does not actually check database connectivity
- Security gaps: user input logged unsanitized, error messages leak internal details
- Duplicate confidence calculation logic across classes
- Rollback shell scripts committed to repository
- Several heavy dependencies (pandas, numpy) imported but never used
- Tests lack coverage for error paths and security edge cases

---

## Critical Issues (Must Fix)

### C1. Health Endpoint Does Not Verify Database Connectivity

**File:** `src/api/health_router.py:20-31`

The `/health` endpoint always returns `"database": "unknown"` without actually checking the database. The Docker HEALTHCHECK uses this endpoint (`curl -f http://localhost:8018/health`), meaning the container will report healthy even when the database is completely down. Meanwhile, the `/ready` endpoint does check the DB but is not used by the Docker healthcheck.

**Impact:** False-positive health status in production. Orchestrators (Docker, Kubernetes) will route traffic to a service that cannot serve requests.

**Before:**
```python
@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "ai-query-service",
        "database": "unknown"
    }
```

**Recommendation:** Either make `/health` check the database (like `/ready` does), or change the Docker HEALTHCHECK to use `/ready`.

---

### C2. No Authentication or Rate Limiting

**File:** `src/main.py:177-186`

Both authentication and rate limiting are explicitly marked as TODO items. Without these, the service is vulnerable to:
- Unauthorized access to query endpoints
- Denial-of-service via query flooding
- Abuse of downstream OpenAI API credits

This is documented in the README as a known gap, but it is the single most critical blocker for production deployment.

**Recommendation:** Implement before any production or shared-environment deployment. The code references `ai-automation-service/src/api/middlewares.py` as a pattern to follow.

---

### C3. Readiness Check Leaks Internal Error Details

**File:** `src/api/health_router.py:54-61`

When the readiness check fails, the raw exception string is returned in the response body:

```python
except Exception as e:
    return {
        "status": "not_ready",
        "error": str(e)  # SECURITY: Leaks internal details
    }
```

**Impact:** Exposes internal database connection strings, file paths, and error details to callers. Also, the endpoint returns HTTP 200 even when the service is not ready, which will confuse health check probes.

**Recommendation:**
- Return HTTP 503 when not ready
- Do not include raw exception message in the response; log it server-side instead

---

### C4. User Query Logged Without Sanitization

**Files:**
- `src/api/query_router.py:58` - `logger.info(f"... Processing query: {request.query[:100]}...")`
- `src/services/query/processor.py:71` - `logger.info(f"... Processing query: {query[:100]}...")`

User-supplied natural language queries are logged directly. In a system that processes natural language, this creates risks:
- Log injection (newlines, control characters in query text)
- PII/sensitive data in logs (users may type passwords, addresses, etc.)
- ANSI escape sequence injection in terminal-viewed logs

**Recommendation:** Sanitize or redact user input before logging. At minimum, strip control characters. Consider logging only a hash or truncated sanitized version.

---

## Major Issues (Should Fix)

### M1. Duplicate Confidence Calculation Logic

**Files:**
- `src/services/query/processor.py:132-158` - `QueryProcessor._calculate_confidence()`
- `src/services/clarification/service.py:97-108` - `ClarificationService._calculate_base_confidence()`

These two methods contain nearly identical confidence calculation logic (both use the same formula: `0.5 + (entity_count * 0.08) + (quality_score * 0.15)`). This is a DRY violation that will lead to divergence as the code evolves.

**Recommendation:** Extract into a shared utility function, e.g., `src/services/confidence.py`.

---

### M2. Unused Heavy Dependencies: pandas, numpy

**File:** `requirements.txt:22-23`

```
pandas>=2.2.0,<3.0.0
numpy>=1.26.0,<1.27.0
```

Neither `pandas` nor `numpy` is imported or used anywhere in the service source code. These are large packages that:
- Add ~200MB+ to the Docker image
- Increase build time significantly
- Increase attack surface

**Recommendation:** Remove until actually needed. They can be added back when Story 39.10 implements features that require them.

---

### M3. SQLite Connection Pool Misconfiguration Risk

**File:** `src/database/__init__.py:18-29`

The code correctly uses `StaticPool` for SQLite, but the `Settings` class still exposes `database_pool_size` and `database_max_overflow` configuration (lines 13-14 in config.py) that are never used with SQLite. This is misleading documentation for operators.

Additionally, using `StaticPool` means a single connection is reused. Under concurrent async requests, this could cause `database is locked` errors if WAL mode isn't fully effective.

**Recommendation:** Document in the README that pool_size/max_overflow only apply to PostgreSQL. Consider using `NullPool` or a connection-per-request pattern for better concurrency handling.

---

### M4. Refine Endpoint Accepts Arbitrary Dict Without Validation

**File:** `src/api/query_router.py:97-115`

```python
async def refine_query(
    query_id: str,
    refinement: dict,  # No Pydantic model, no validation
    ...
```

The `/refine` endpoint accepts a raw `dict` body with no schema validation. This is inconsistent with the `/query` endpoint which properly uses a Pydantic model (`QueryRequest`). An attacker could send arbitrarily large or deeply nested JSON payloads.

**Recommendation:** Define a `RefineRequest` Pydantic model with validated fields (e.g., `feedback: str`, `selected_entities: list[str]`) matching the README documentation.

---

### M5. `get_db` Dependency Yields but Does Not Commit

**File:** `src/database/__init__.py:60-73`

```python
async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
```

The session is never committed. Any write operations (which Story 39.10 will add for query history storage) would silently lose data. The `async with` context manager already calls `close()`, making the explicit `close()` in the `finally` block redundant.

**Recommendation:** Add `await session.commit()` after successful request processing, or use an explicit commit pattern in the endpoint handlers. Remove the redundant `close()`.

---

### M6. Hardcoded `query_id` in Placeholder Response

**File:** `src/api/query_router.py:67-73`

```python
return QueryResponse(
    query_id="query-placeholder",  # Always the same ID
    ...
)
```

Every query returns the same `query_id`. If any downstream system or test relies on unique query IDs (which the `QueryProcessor` class does generate via UUID), this will cause data collisions.

**Recommendation:** Generate a unique ID even in the placeholder implementation:
```python
import uuid
query_id = f"query-{uuid.uuid4().hex[:8]}"
```

---

### M7. `sys.path.insert` Manipulation at Module Level

**File:** `src/main.py:36`

```python
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
```

This modifies the Python path at import time to find the `shared` package. This is fragile and can cause import order issues. The Dockerfile already sets `PYTHONPATH=/app:/app/src`, making this unnecessary in Docker. For local development, `pythonpath` is set in pytest.ini.

**Recommendation:** Remove the `sys.path.insert` and rely on `PYTHONPATH` environment variable consistently.

---

### M8. Rollback Scripts Committed to Repository

**Files:**
- `rollback_pytest_asyncio_20260205_141944.sh`
- `rollback_pytest_asyncio_20260205_143721.sh`

These are one-off migration rollback scripts with hardcoded Windows paths (`C:\cursor\HomeIQ\...`). They should not be in the repository as they are:
- Machine-specific (hardcoded paths)
- Temporary artifacts of a migration process
- Not cross-platform compatible (bash script with Windows paths)

**Recommendation:** Delete both files. Add `rollback_*.sh` to `.gitignore`.

---

## Minor Issues (Nice to Fix)

### m1. Emoji Characters in Log Messages

**Files:** Multiple (`main.py`, `query_router.py`, `processor.py`, `clarification/service.py`, `suggestion/generator.py`)

Examples: `"... Database initialized"`, `"... Processing query"`, `"... Failed to process query"`

While visually distinctive, emoji characters in log messages can cause issues with:
- Log aggregation tools that don't handle UTF-8 well
- Log parsing with regex patterns
- Terminal rendering in some environments

**Recommendation:** Use plain text prefixes like `[OK]`, `[ERROR]`, `[WARN]` instead of emoji, or make it configurable.

---

### m2. `QueryResponse` Uses `list[dict]` Instead of Typed Models

**File:** `src/api/query_router.py:37-43`

```python
class QueryResponse(BaseModel):
    suggestions: list[dict] = Field(default_factory=list)
    entities: list[dict] = Field(default_factory=list)
```

Using `list[dict]` loses type safety and prevents automatic OpenAPI schema generation for the response structure. When Story 39.10 is implemented, these should be proper Pydantic models.

**Recommendation:** Define `SuggestionResponse` and `EntityResponse` models with typed fields.

---

### m3. `conftest.py` `event_loop` Fixture Uses Deprecated Pattern

**File:** `tests/conftest.py:22-27`

```python
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

The `event_loop` fixture is deprecated in `pytest-asyncio >= 0.21`. With `asyncio_mode = auto` in pytest.ini, this fixture is unnecessary and may cause warnings or conflicts.

**Recommendation:** Remove the `event_loop` fixture entirely. Let pytest-asyncio manage the event loop.

---

### m4. `database/models.py` Contains Only TYPE_CHECKING Imports

**File:** `src/database/models.py`

This file contains only `TYPE_CHECKING` imports that reference `ai_automation_service.database.models` -- a package that is not available in this service's dependency tree. The imports will never actually resolve, making this file essentially dead code.

**Recommendation:** Either remove the file or add actual model definitions that the query service needs. When Story 39.10 is implemented, decide whether to share models via a common package or duplicate them.

---

### m5. Missing `__all__` Exports in Several `__init__.py` Files

**Files:**
- `src/__init__.py` - Empty
- `src/database/__init__.py` - Exports `get_db`, `init_db`, `engine` but no `__all__`
- `src/services/clarification/__init__.py` - Has `__all__`
- `src/services/suggestion/__init__.py` - Has `__all__`

Inconsistent export patterns across the codebase.

**Recommendation:** Add `__all__` to all `__init__.py` files for consistency.

---

### m6. `openai` Dependency Has No Upper Bound

**File:** `requirements.txt:19`

```
openai>=1.0.0
```

All other dependencies have upper bounds, but `openai` does not. Major version bumps in the OpenAI SDK have historically introduced breaking changes.

**Recommendation:** Pin to `openai>=1.0.0,<2.0.0` for safety.

---

### m7. `pytest` and `pytest-asyncio` in Main `requirements.txt`

**File:** `requirements.txt:37-38`

Test dependencies should be in a separate `requirements-dev.txt` or `requirements-test.txt` to keep the production image lean.

**Recommendation:** Create `requirements-dev.txt` for test/dev dependencies.

---

### m8. Port Mismatch in README vs `__main__` Block

**File:** `src/main.py:206-214`

```python
if __name__ == "__main__":
    uvicorn.run("main:app", ...)
```

The module string `"main:app"` won't work when running from the project root (it should be `"src.main:app"`). This is a minor issue since Docker uses the CMD directly, but it could confuse developers.

---

## Enhancement Recommendations

### E1. Add Request ID / Correlation ID to All Responses

The service integrates OpenTelemetry `CorrelationMiddleware`, but query responses don't include a `request_id` or `correlation_id` field. Adding this would significantly improve debugging.

**Recommendation:** Include `X-Request-ID` header in responses and add `request_id` to response bodies.

---

### E2. Implement Query Input Sanitization Layer

Before Story 39.10 adds OpenAI integration, implement a sanitization layer for natural language queries to prevent:
- Prompt injection attacks (e.g., "Ignore previous instructions and...")
- SQL injection via query text stored in the database
- XSS if query text is rendered in the UI

**Recommendation:** Create `src/services/sanitization.py` with:
- Control character stripping
- Maximum nesting depth for context dict
- Prompt injection detection patterns (blocklist approach)

---

### E3. Add Structured Logging with JSON Output

The service uses `logging.getLogger()` with string formatting. For production observability, structured JSON logging would enable better log aggregation and querying.

**Recommendation:** Use the `shared.logging_config.setup_logging` consistently (it may already produce structured output) and ensure all log calls use structured fields rather than f-string interpolation.

---

### E4. Implement Circuit Breaker for External Service Calls

When Story 39.10 adds calls to data-api, device-intelligence-service, Home Assistant, and OpenAI, implement circuit breakers to prevent cascade failures.

**Recommendation:** Use `aiohttp` session with retry/backoff or a library like `aiobreaker` for circuit breaker patterns.

---

### E5. Add OpenAPI Response Models for All Endpoints

**Files:** `src/api/query_router.py:76-94`, `src/api/query_router.py:97-115`

The `/suggestions` and `/refine` endpoints return raw `dict` without `response_model` declarations. This means FastAPI cannot generate accurate OpenAPI documentation.

**Recommendation:** Define Pydantic response models for all endpoints.

---

## Architecture Improvement Suggestions

### A1. Service Layer Should Not Depend on Database Session Directly

The `QueryProcessor`, `ClarificationService`, and `SuggestionGenerator` all accept `db: AsyncSession` as a parameter. This couples the service layer to SQLAlchemy implementation details.

**Recommendation:** Introduce a repository pattern where services depend on abstract repository interfaces rather than raw database sessions. This improves testability and allows swapping storage backends.

---

### A2. Consider Dependency Injection Container

Currently, `QueryProcessor` receives its dependencies via constructor arguments, but there's no wiring layer. When Story 39.10 adds the full implementation with multiple clients and services, manual wiring will become complex.

**Recommendation:** Consider using FastAPI's dependency injection system more extensively, or a lightweight DI container like `dependency-injector`.

---

### A3. Shared Database Access Is a Scaling Bottleneck

The service shares `ai_automation.db` (SQLite) with ai-automation-service. SQLite has fundamental limitations for concurrent write access across services:
- Single writer at a time (even with WAL mode)
- File-level locking
- No network access (both services must access the same filesystem)

**Recommendation:** For production scaling, migrate to PostgreSQL or separate the databases. The code already has a PostgreSQL path in `database/__init__.py` (lines 43-50), so this is partially prepared.

---

## Testing Analysis

### Coverage Summary (from coverage report)

| File | Statements | Missing | Coverage |
|------|-----------|---------|----------|
| `src/__init__.py` | 0 | 0 | 100% |
| `src/api/__init__.py` | 2 | 0 | 100% |
| `src/api/health_router.py` | 21 | 4 | ~81% |
| `src/api/query_router.py` | 29 | 6 | ~79% |
| `src/config.py` | 28 | 0 | 100% |
| `src/database/__init__.py` | 34 | 21 | ~38% |
| `src/database/models.py` | 1 | 1 | 0% |
| `src/main.py` | 74 | 13 | ~82% |
| `src/services/query/__init__.py` | 2 | 0 | 100% |
| `src/services/query/processor.py` | 64 | 13 | ~80% |

**Key gaps:**
- `database/__init__.py` at ~38% - the PostgreSQL path and `init_db` function are not tested
- `database/models.py` at 0% - dead code
- Clarification service and suggestion generator are not included in coverage (not imported by any tested code path)

### Missing Test Cases

1. **Query length validation** - No test for queries exceeding `max_query_length` (500 chars)
2. **Malformed JSON input** - No test for invalid request bodies
3. **Concurrent request handling** - Skipped, but important for the foundation
4. **Database connection failure during request** - Only tested at startup
5. **CORS header validation** - No test verifying CORS headers in responses
6. **Empty/whitespace-only query strings** - `process_query` handles this but the router does not
7. **Clarification service tests** - No test file for `ClarificationService`
8. **Suggestion generator tests** - No test file for `SuggestionGenerator`
9. **Error handler registration** - Tests only assert `app is not None`, not actual behavior

---

## Dockerfile Review

**File:** `Dockerfile`

**Good practices observed:**
- Multi-stage build (builder + runtime)
- Non-root user (`appuser:appgroup`)
- Explicit `HEALTHCHECK` directive
- `--no-install-recommends` for apt packages
- Cache mount for pip

**Issues:**

1. **Line 9:** `pip install --upgrade pip==25.2` pins to a specific pip version but uses `--upgrade` which is redundant with `==`. Minor.

2. **Lines 15-16:** `--mount=type=cache` and `--no-cache-dir` are contradictory. The cache mount caches the download cache, but `--no-cache-dir` tells pip not to use its cache. Remove `--no-cache-dir` to benefit from the cache mount.

3. **Line 4:** Uses `python:3.12-slim` but `requirements.txt` header says "Python 3.11+". Consistent, but should be documented.

4. **No `.env` file copied** - The `Settings` class reads from `.env` via pydantic-settings, but no `.env` file is included in the image. This is fine for production (env vars from orchestrator), but could confuse development.

---

## Dependencies Review

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| fastapi | 0.123.x | OK | Pinned to minor version |
| uvicorn | 0.32.x | OK | Pinned to minor version |
| pydantic | 2.9.x | OK | |
| pydantic-settings | 2.5.x | OK | |
| sqlalchemy | 2.0.x | OK | |
| aiosqlite | 0.20.x | OK | |
| aiohttp | 3.13.x | OK | Not used in current code |
| httpx | 0.28.x | OK | Used in tests |
| openai | >=1.0.0 | WARN | No upper bound |
| pandas | 2.2.x | REMOVE | Not used |
| numpy | 1.26.x | REMOVE | Not used |
| cachetools | >=5.3.0 | OK | Not yet used but planned for caching |
| OTel packages | Various | OK | For observability |
| pytest | >=7.4.0 | MOVE | Move to dev requirements |
| pytest-asyncio | >=0.21.0 | MOVE | Move to dev requirements |

---

## Summary of Recommendations by Priority

### Immediate (Before Story 39.10)
1. Fix `/health` endpoint to check database or switch Docker HEALTHCHECK to `/ready` (C1)
2. Fix readiness check to return 503 on failure and not leak error details (C3)
3. Remove unused `pandas`/`numpy` dependencies (M2)
4. Delete rollback scripts from repository (M8)
5. Add input validation model for `/refine` endpoint (M4)

### Before Production Deployment
6. Implement authentication middleware (C2)
7. Implement rate limiting (C2)
8. Add query input sanitization (E2, C4)
9. Fix `get_db` commit pattern (M5)
10. Pin `openai` upper bound (m6)

### During Story 39.10 Implementation
11. Extract shared confidence calculation (M1)
12. Define typed Pydantic response models (m2, E5)
13. Add missing test coverage for clarification and suggestion services
14. Implement circuit breakers for external calls (E4)
15. Remove `sys.path.insert` hack (M7)

### Long-term
16. Migrate from SQLite to PostgreSQL for multi-service scaling (A3)
17. Implement repository pattern (A1)
18. Add DI container (A2)
19. Separate test dependencies (m7)

---

*Review generated on 2026-02-06. Based on code at commit `e7f84387`.*

---

## Fixes Applied

The following issues from this review were resolved on 2026-02-06 (**8 files modified**):

1. **C1 - Health Endpoint Doesn't Check DB**: Rewrote `src/api/health_router.py` - health endpoint now checks database connectivity. Readiness endpoint returns 503 on failure with sanitized error messages (no internal details leaked).
2. **C4 - Unsanitized User Query Logging**: Fixed in `src/services/query/processor.py` and `src/api/query_router.py` - user queries are now sanitized before logging (replacing control characters, truncating to safe length).
3. **M1 - Duplicate Confidence Calculation**: Extracted shared `calculate_confidence()` into `src/services/query/processor.py`, removed duplicate logic from `src/services/clarification/service.py` which now imports the shared function.
4. **M2 - Unused pandas/numpy Dependencies**: Removed `pandas` and `numpy` from `requirements.txt` (~200MB+ Docker image savings).
5. **M4 - /refine Accepts Raw Dict**: Added Pydantic validation model for `/refine` endpoint input in `src/api/query_router.py`.
6. **M5 - get_db Never Commits**: Fixed `src/database/__init__.py` - session now properly commits on success before closing.
7. **M6 - Hardcoded query_id Placeholder**: Fixed in `src/services/query/processor.py` - now generates unique query IDs using UUID.
8. **M7 - sys.path.insert Hack**: Removed `sys.path.insert` manipulation from `src/main.py`.
9. **m - Suggestion Generator**: Added proper error handling in `src/services/suggestion/generator.py`.
