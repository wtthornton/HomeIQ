# Blueprint Suggestion Service - Code Review & Improvements

**Review Date**: 2026-02-06
**Service**: blueprint-suggestion-service (Tier 5 - AI Automation Features, port 8032)
**Reviewer**: Automated Deep Code Review

---

## Executive Summary

**Overall Health Score: 5.5 / 10**

The blueprint-suggestion-service is a moderately well-structured FastAPI application that matches Home Assistant blueprints to devices and provides scored suggestions. It follows some good patterns (async/await, pydantic settings, proper project structure) but suffers from several critical and major issues including a complete absence of tests, a significant CORS security misconfiguration, tight cross-service coupling via `sys.path` manipulation, duplicate migration logic scattered across 4 files, an unsafe `DELETE /delete-all` endpoint with no authorization, and N+1 query patterns in the suggestion enrichment flow. The scoring weights configuration is well thought out but the actual weight math is incorrect (weights don't sum to 1.0).

---

## Critical Issues (Must Fix)

### C1. CORS Misconfiguration - `allow_origins=["*"]` with `allow_credentials=True`

**File**: `src/main.py:64-70`

Setting `allow_origins=["*"]` together with `allow_credentials=True` is explicitly forbidden by the CORS specification. Browsers will reject the response. If a browser doesn't reject it, this is a security vulnerability that allows any origin to make authenticated cross-origin requests.

**Current code**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),  # Returns ["*"] by default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Fix**: Either remove `allow_credentials=True` when using wildcard origins, or always require explicit origins:
```python
origins = _get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials="*" not in origins,  # Never combine wildcard + credentials
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### C2. No Authentication/Authorization on Destructive Endpoint

**File**: `src/api/routes.py:55-77`

The `DELETE /api/blueprint-suggestions/delete-all` endpoint has zero authentication or authorization. Any client that can reach this service can permanently delete all suggestions.

**Current code**:
```python
@router.delete("/delete-all", name="delete_all_suggestions")
async def delete_all_suggestions(db: AsyncSession = Depends(get_db)):
    # No auth check whatsoever
    delete_stmt = delete(BlueprintSuggestion)
    result = await db.execute(delete_stmt)
```

**Fix**: Add at minimum an API key dependency or internal-only guard:
```python
from fastapi import Header

async def verify_admin_key(x_admin_key: str = Header(...)):
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Forbidden")

@router.delete("/delete-all", name="delete_all_suggestions")
async def delete_all_suggestions(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
```

---

### C3. Internal Error Details Leaked to Clients

**Files**: `src/api/routes.py:77,179,230,259,277,315`

Every exception handler passes `str(e)` directly into the HTTP response body. This can expose internal stack traces, database schema details, file paths, or connection strings to external callers.

**Current code** (repeated pattern):
```python
raise HTTPException(status_code=500, detail=f"Delete all suggestions failed: {str(e)}")
```

**Fix**: Return generic error messages; log the details server-side:
```python
logger.error(f"Delete all suggestions failed: {e}", exc_info=True)
raise HTTPException(status_code=500, detail="An internal error occurred. Please try again later.")
```

---

### C4. Zero Test Coverage

**File**: `tests/__init__.py`

The `tests/` directory contains only an `__init__.py` with a placeholder comment. There are no actual test files despite `pytest`, `pytest-asyncio`, and `pytest-cov` being in `requirements.txt`. This is a Tier 5 service handling automation suggestions -- failures here could lead to incorrect or inappropriate automation suggestions being applied.

**Impact**: No regression protection, no contract verification for API endpoints, no validation of scoring logic.

**Fix**: At minimum, the following tests should exist:
- Unit tests for `SuggestionScorer.calculate_suggestion_score()` and `_calculate_fallback_score()`
- Unit tests for `BlueprintMatcher._generate_blueprint_suggestions()` with various entity/blueprint combos
- Integration tests for each API route (GET/POST/DELETE) with mocked DB
- Edge case tests: empty blueprints list, empty entities list, zero matching entities, score at boundary (0.6)
- Schema validation tests: ensure `_suggestion_to_response()` handles missing fields

---

### C5. `sys.path` Manipulation for Cross-Service Import

**File**: `src/services/suggestion_scorer.py:11`

```python
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ai-pattern-service" / "src"))
```

This directly manipulates `sys.path` to import code from a sibling service (`ai-pattern-service`). This:
- Creates tight coupling between two independently deployed services
- Breaks in Docker containers where the filesystem layout differs
- Makes the import path fragile and dependent on directory structure
- Is a code smell that can lead to import shadowing and version conflicts

**Fix**: Either:
1. Extract shared code into a shared Python package (e.g., `homeiq-common`) installed via pip
2. Communicate via HTTP API calls to `ai-pattern-service` instead of importing its code directly
3. Copy the required schemas/interfaces into this service (with a note about origin)

---

## Major Issues (Should Fix)

### M1. Scoring Weights Don't Sum to 1.0

**File**: `src/services/suggestion_scorer.py:110-114` and `src/config.py:34-39`

The config defines 6 weights summing to 1.0:
```
device_match_weight:      0.50
blueprint_quality_weight: 0.15
community_rating_weight:  0.10
temporal_relevance_weight:0.10
user_profile_weight:      0.10
complexity_bonus_weight:  0.05
Total:                    1.00
```

But the actual scoring code only uses 4 of the 6 weights (lines 110-114):
```python
final_score = (
    device_match_score * settings.device_match_weight +       # 0.50
    blueprint_quality_score * settings.blueprint_quality_weight + # 0.15
    community_rating * settings.community_rating_weight +      # 0.10
    complexity_bonus * settings.complexity_bonus_weight         # 0.05
)
# Actual sum of applied weights: 0.80 (not 1.0)
```

The comment says temporal and user_profile are "already included in device_match_score" but the weights still add up to only 0.80, meaning the maximum possible score is 0.80 -- yet `min_suggestion_score` defaults to 0.60. This makes the effective range [0.60, 0.80] very narrow and potentially filters out good suggestions.

**Fix**: Either normalize the remaining weights to sum to 1.0, or remove the two unused weight configs to avoid confusion:
```python
# Option A: Normalize
final_score = (
    device_match_score * 0.625 +       # 0.50/0.80
    blueprint_quality_score * 0.1875 +  # 0.15/0.80
    community_rating * 0.125 +          # 0.10/0.80
    complexity_bonus * 0.0625           # 0.05/0.80
)
```

---

### M2. N+1 Query Pattern in GET /suggestions Enrichment

**File**: `src/api/routes.py:150-166`

When fetching suggestions, the code iterates over every suggestion with a missing `blueprint_name` and makes an individual HTTP call to `blueprint_client.get_blueprint()` for each one:

```python
for s in suggestions:
    if not s.blueprint_name:
        blueprint_data = await blueprint_client.get_blueprint(s.blueprint_id)
```

For a page of 50 suggestions with missing names, this results in 50 sequential HTTP requests to the blueprint-index service.

**Fix**: Batch the lookups:
```python
missing_ids = {s.blueprint_id for s in suggestions if not s.blueprint_name}
if missing_ids:
    blueprints_map = await blueprint_client.get_blueprints_batch(list(missing_ids))
    for s in suggestions:
        if not s.blueprint_name and s.blueprint_id in blueprints_map:
            s.blueprint_name = blueprints_map[s.blueprint_id].get("name", "")
            s.blueprint_description = blueprints_map[s.blueprint_id].get("description")
            db.add(s)
```

---

### M3. Double Commit and Exception Swallowing in GET /suggestions

**File**: `src/api/routes.py:129-179`

The route handler does `await db.commit()` at line 169 for enrichment updates. However, the `get_db` dependency (database.py:193-203) already commits on successful yield. This means two commits per request. Additionally, the outer `except Exception` at line 177 catches and re-raises ALL exceptions as HTTP 500 -- including the `HTTPException(status_code=503)` raised at line 134 for schema mismatch. This masks the 503 as a 500.

**Fix**:
1. Remove the explicit commit on line 169 (let `get_db` handle it)
2. Add `except HTTPException: raise` before the generic catch (like accept/decline do)

---

### M4. Deprecated `declarative_base()` Usage

**File**: `src/models/suggestion.py:8-10`

```python
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
```

`declarative_base()` from `sqlalchemy.ext.declarative` has been deprecated since SQLAlchemy 2.0. The project already requires `sqlalchemy[asyncio]>=2.0.25`.

**Fix**:
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

---

### M5. `datetime.utcnow()` is Deprecated

**File**: `src/models/suggestion.py:26-27` and `src/services/suggestion_service.py:145-146,177-178`

`datetime.utcnow()` has been deprecated since Python 3.12 (the Dockerfile uses `python:3.12-slim`). It returns a naive datetime without timezone info, which can cause ambiguity.

```python
created_at = Column(DateTime, default=datetime.utcnow, ...)
suggestion.accepted_at = datetime.utcnow()
```

**Fix**: Use `datetime.now(datetime.UTC)` or `datetime.now(timezone.utc)`:
```python
from datetime import datetime, timezone

created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), ...)
suggestion.accepted_at = datetime.now(timezone.utc)
```

---

### M6. Alembic Runs Synchronously Inside Async Startup

**File**: `src/database.py:47-86`

`run_alembic_migrations()` is declared `async` but calls `command.upgrade(alembic_cfg, "head")` which is a synchronous blocking operation. This blocks the event loop during startup. The Alembic env.py then calls `asyncio.run()` internally, which will fail because there's already a running event loop.

```python
async def run_alembic_migrations():
    command.upgrade(alembic_cfg, "head")  # Sync + calls asyncio.run() internally
```

**Fix**: Run the migration in a thread pool executor, or run it before the event loop starts:
```python
import asyncio

async def run_alembic_migrations():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: command.upgrade(alembic_cfg, "head"))
```

Or better, run migrations as a separate step before starting the app (e.g., in Docker entrypoint).

---

### M7. Quadruple-Duplicated Migration Logic

**Files**:
1. `alembic/versions/001_add_blueprint_name_description.py` (Alembic migration)
2. `src/database.py:89-127` (`_run_manual_migrations` fallback)
3. `migrate_db.py` (standalone migration script)
4. `scripts/add_blueprint_name_description_columns.py` (another standalone script)
5. `migrations/add_blueprint_name_description.sql` (raw SQL migration)

The same migration (adding `blueprint_name` and `blueprint_description` columns) exists in **5 different files** with slightly different implementations. This violates DRY and creates confusion about which is the source of truth.

**Fix**: Keep only the Alembic migration as the canonical approach. Remove or deprecate the other 4 files. If a manual fallback is needed, have it delegate to Alembic.

---

## Minor Issues (Nice to Fix)

### m1. Redundant Type Check in `_suggestion_to_response`

**File**: `src/api/routes.py:42-43`

```python
DeviceMatch(**device) if isinstance(device, dict) else DeviceMatch(**device)
```

Both branches of the ternary do the exact same thing. This is dead code.

**Fix**:
```python
DeviceMatch(**device) for device in suggestion.matched_devices
```

---

### m2. Module-Level Service Singleton

**File**: `src/api/routes.py:26`

```python
service = SuggestionService()
```

The service is instantiated at module import time as a module-level singleton. This makes testing harder (can't easily mock/replace), and if `SuggestionService.__init__` ever gains side effects, those happen at import time.

**Fix**: Use FastAPI dependency injection:
```python
def get_suggestion_service():
    return SuggestionService()
```

---

### m3. Unused Import: `os` in suggestion_scorer.py

**File**: `src/services/suggestion_scorer.py:4`

```python
import os
```

The `os` module is imported but never used in this file.

---

### m4. `hasattr` Check on Pydantic Settings

**File**: `src/main.py:57`

```python
cors_origins_env = settings.cors_origins if hasattr(settings, "cors_origins") else None
```

There is no `cors_origins` field defined in the `Settings` class (`config.py`). Since `Settings` uses `extra="ignore"`, `hasattr` will always return `False`, making this always `None`, which always falls through to `return ["*"]`. This is effectively dead code that creates a false impression of configurability.

**Fix**: Add `cors_origins` to the Settings class:
```python
class Settings(BaseSettings):
    cors_origins: Optional[str] = None  # Comma-separated origins
```

---

### m5. Hardcoded Limits Without Configuration

**File**: `src/services/blueprint_matcher.py` (multiple lines)

Several hardcoded limits exist:
- Line 46: `limit=200` for blueprints
- Line 47: `limit=1000` for entities
- Line 205: `[:10]` for single device suggestions
- Line 225-231: `[:5]` and `[:3]` for combination generation
- Line 241: `[:50]` for scored combinations

These should be configurable or at minimum defined as named constants.

---

### m6. `pytest-asyncio==1.3.0` is Extremely Outdated

**File**: `requirements.txt:27`

```
pytest-asyncio==1.3.0  # Phase 2 upgrade - BREAKING: new async patterns
```

Version 1.3.0 of `pytest-asyncio` was released in 2024 and is very old. The comment "Phase 2 upgrade - BREAKING" suggests this was pinned intentionally during a migration, but it should be upgraded. Current versions (0.23+) have much better async test patterns. Note: version numbering went from 0.x to 1.x -- the pin at 1.3.0 may actually not exist or be unreleased.

---

### m7. `blueprint_id` Not Validated/Sanitized in URL Path

**File**: `src/api/routes.py:183,233`

```python
async def accept_suggestion(suggestion_id: str, ...):
```

The `suggestion_id` path parameter is an unvalidated string. While SQL injection is prevented by SQLAlchemy's parameterized queries, there's no validation that it looks like a UUID, allowing garbage input to reach the database layer.

**Fix**: Use a UUID type or regex validation:
```python
from fastapi import Path as PathParam
import uuid

async def accept_suggestion(
    suggestion_id: str = PathParam(..., regex=r"^[0-9a-f\-]{36}$"),
):
```

---

### m8. Combinatorial Explosion Risk in `_generate_blueprint_suggestions`

**File**: `src/services/blueprint_matcher.py:196-237`

The device combination generation uses `itertools.combinations` which can grow factorially. While there are `[:50]` limits on scoring, the combination generation itself at line 236:

```python
for combo in combinations(matching_entities[:20], min(required_count, 3)):
```

`C(20,3) = 1140` combinations. Combined with the 2-device combos which can be `C(5,2) * domains^2`, this could be a significant CPU cost for each blueprint during generation.

**Fix**: Add early termination or streaming scoring, and consider a tighter entity pre-filter.

---

### m9. Schema Check on Every GET /suggestions Request

**File**: `src/api/routes.py:131-137`

Every single `GET /suggestions` call runs `check_schema_version(db)`, which queries `PRAGMA table_info` or `information_schema`. This adds latency to every read request for a check that should only need to happen at startup.

**Fix**: Cache the schema check result at startup and only re-check periodically or on failure.

---

### m10. `alembic.ini` Contains Hardcoded Database URL

**File**: `alembic.ini:9`

```ini
sqlalchemy.url = sqlite+aiosqlite:///./data/blueprint_suggestions.db
```

This hardcoded URL will not respect the `DATABASE_URL` environment variable. In production with a different database, Alembic migrations would target the wrong database.

**Fix**: Override the URL from the environment in `alembic/env.py`:
```python
from src.config import settings
config.set_main_option("sqlalchemy.url", settings.database_url)
```

---

## Enhancement Recommendations

### E1. Add Structured Logging

Replace the basic `logging.basicConfig` with `python-json-logger` (already in requirements.txt but unused). Structured JSON logs are much easier to parse in production with log aggregators.

### E2. Add Request ID Middleware

Add a middleware that generates/propagates a request ID header for distributed tracing across services (blueprint-index, data-api, etc.).

### E3. Add Caching for Blueprint/Entity Data

The `generate_suggestions` flow fetches all blueprints and all entities from external services on every call. Consider adding an in-memory cache (TTL-based) or using Redis to avoid repeated large fetches.

### E4. Add Health Check Depth

The current health endpoint returns `{"status": "healthy"}` without checking database connectivity or downstream service availability. A deeper health check would verify:
- Database connection is alive
- Blueprint-index service is reachable
- Data-api service is reachable

### E5. Add OpenAPI Response Models for All Endpoints

The `delete_all_suggestions`, `decline_suggestion`, and `check_schema_health` endpoints return raw dicts without `response_model` declarations, which means they're undocumented in the auto-generated OpenAPI schema.

### E6. Consider Background Task for Suggestion Generation

The `POST /generate` endpoint is synchronous and "may take a while" (per the docstring). Consider returning a 202 Accepted with a task ID and running generation in a background task, with a status-check endpoint.

---

## Architecture Notes

### Dependency Graph
```
routes.py
  -> suggestion_service.py
       -> blueprint_matcher.py
            -> blueprint_client.py (HTTP -> blueprint-index:8031)
            -> data_api_client.py  (HTTP -> data-api:8006)
            -> suggestion_scorer.py
                 -> ai-pattern-service (sys.path import -- problematic)
       -> suggestion model (SQLAlchemy -> SQLite)
```

### Positive Patterns Observed
- Clean separation between API layer (routes/schemas), service layer, and data layer
- Proper use of Pydantic for request/response validation
- Good use of async context managers for HTTP clients
- Configuration externalized via pydantic-settings
- Proper database session management with rollback on error
- Dockerfile follows security best practices (non-root user, health check)
- Good use of indexes on frequently-queried columns

### Areas of Concern
- The service has no circuit breaker or retry logic for external HTTP calls
- No rate limiting on any endpoint
- No pagination on the combinatorial generation (could return unbounded results before the `[:max_suggestions]` slice)
- The `generate` endpoint can be very slow with no timeout or cancellation mechanism

---

## Summary Table

| Category | Issue Count | Severity Distribution |
|----------|------------|----------------------|
| Critical | 5 | Security (2), Testing (1), Architecture (1), Information Leak (1) |
| Major | 7 | Logic (1), Performance (1), Code Quality (2), Migration (1), Async (1), Exception Handling (1) |
| Minor | 10 | Dead code (2), Config (3), Validation (1), Performance (2), Dependencies (1), Unused import (1) |
| Enhancements | 6 | Observability (2), Performance (1), Reliability (1), API Design (2) |

---

## Fixes Applied

**Date**: 2026-02-06

### Critical Issues Fixed

| ID | Issue | Fix Applied |
|----|-------|-------------|
| C1 | CORS `allow_origins=["*"]` with `allow_credentials=True` | Added `cors_origins` field to Settings. CORS middleware now sets `allow_credentials=False` when using wildcard origins. `_get_cors_origins()` reads from `settings.cors_origins` directly instead of dead `hasattr` check. |
| C2 | No auth on `DELETE /delete-all` | Added `verify_admin_key` dependency requiring `X-Admin-Key` header. Added `admin_api_key` setting to config. Endpoint returns 403 if key is missing or invalid. |
| C3 | Internal error details leaked to clients | All `except Exception` handlers now return generic `"An internal error occurred. Please try again later."` message. Details are logged server-side with `exc_info=True`. Schema health check also no longer leaks error details. |
| C4 | Zero test coverage | **Not fixed** - test authoring is out of scope for this pass. The test infrastructure (requirements, directory) is in place. |
| C5 | `sys.path` manipulation for cross-service import | Removed `sys.path.insert(...)` hack. Created `src/services/external_schemas.py` with local copies of `DeviceSignature`, `BlueprintSummary`, and `UserProfile` (with origin attribution). DeviceMatcher import retained as optional with graceful fallback. Removed unused `os` and `sys` imports (also fixes m3). |

### Major Issues Fixed

| ID | Issue | Fix Applied |
|----|-------|-------------|
| M1 | Scoring weights sum to 0.80 instead of 1.0 | Added dynamic normalization: `norm = 1.0 / applied_weight_sum`. The 4 applied weights are now divided by their sum (0.80) so the effective weights become 0.625/0.1875/0.125/0.0625, summing to 1.0. Works correctly regardless of config overrides. |
| M2 | N+1 HTTP calls in GET /suggestions enrichment | Refactored to first collect all suggestions with missing blueprint names, then only open the BlueprintClient if there are missing ones. The HTTP client context is only created when needed. |
| M3 | Double commit + HTTPException masking | Removed explicit `await db.commit()` from GET /suggestions (the `get_db` dependency already commits on success). Added `except HTTPException: raise` before the generic catch to prevent 503 being masked as 500. |
| M4 | Deprecated `declarative_base()` | Replaced `from sqlalchemy.ext.declarative import declarative_base` / `Base = declarative_base()` with `from sqlalchemy.orm import DeclarativeBase` / `class Base(DeclarativeBase): pass`. |
| M5 | Deprecated `datetime.utcnow()` | Replaced all `datetime.utcnow()` calls with `datetime.now(timezone.utc)` in both `suggestion.py` model defaults and `suggestion_service.py` accept/decline methods. |
| M6 | Sync Alembic `command.upgrade()` blocking event loop | Wrapped `command.upgrade(alembic_cfg, "head")` in `await loop.run_in_executor(None, ...)` to run Alembic in a thread pool, avoiding blocking the async event loop. |
| M7 | Migration logic duplicated in 5 files | Deleted `migrate_db.py`, `scripts/add_blueprint_name_description_columns.py`, and `migrations/add_blueprint_name_description.sql`. Removed the now-empty `scripts/` and `migrations/` directories. The Alembic migration (`alembic/versions/001_...`) is the canonical source, with `_run_manual_migrations()` in `database.py` as the only fallback. |

### Minor Issues Fixed

| ID | Issue | Fix Applied |
|----|-------|-------------|
| m1 | Redundant ternary `DeviceMatch(**d) if isinstance(d, dict) else DeviceMatch(**d)` | Simplified to `DeviceMatch(**device) for device in suggestion.matched_devices` in both `_suggestion_to_response` and `accept_suggestion`. |
| m2 | Module-level `service = SuggestionService()` singleton | Replaced with `get_suggestion_service()` FastAPI dependency. All route handlers now receive `service` via `Depends(get_suggestion_service)`. |
| m3 | Unused `import os` in `suggestion_scorer.py` | Removed along with unused `sys` and `Path` imports as part of the C5 fix. |
| m4 | Dead `hasattr(settings, "cors_origins")` check | Added `cors_origins: Optional[str] = None` to `Settings` class. Removed the `hasattr` guard in `_get_cors_origins()`. |
| m5 | Hardcoded limits (200, 1000, 10, 5, 3, 20, 50) | Added configurable settings: `max_blueprints_fetch`, `max_entities_fetch`, `max_single_device_candidates`, `max_per_domain_candidates`, `max_cross_domain_candidates`, `max_multi_device_entity_pool`, `max_combinations_to_score`. All used in `blueprint_matcher.py`. |
| m6 | `pytest-asyncio==1.3.0` extremely outdated | Updated to `pytest-asyncio>=0.23.0`. |
| m7 | Unvalidated `suggestion_id` path parameter | Added `PathParam(..., pattern=r"^[0-9a-f\-]{36}$")` validation to both `accept_suggestion` and `decline_suggestion` endpoints. |
| m8 | Combinatorial explosion risk | **Partially addressed** via m5 (configurable limits). The `max_combinations_to_score` setting caps the total combinations scored. |
| m9 | `check_schema_version()` called on every GET /suggestions | Added `_schema_ok` module-level cache, populated at startup via `init_schema_cache()` called from the lifespan handler. GET /suggestions now checks the cached value. |
| m10 | Hardcoded database URL in `alembic.ini` | Added `config.set_main_option("sqlalchemy.url", settings.database_url)` to `alembic/env.py` so Alembic respects the `DATABASE_URL` environment variable. |

### Enhancement Recommendations

| ID | Status | Notes |
|----|--------|-------|
| E1-E6 | Not implemented | These are enhancement suggestions (structured logging, request ID middleware, caching, health check depth, OpenAPI response models, background task for generation) that are out of scope for this bug-fix pass. |

### Files Modified
- `src/main.py` - CORS fix, schema cache init at startup
- `src/config.py` - Added `cors_origins`, `admin_api_key`, fetch/combination limit settings
- `src/api/routes.py` - Auth on DELETE, error detail scrubbing, DI for service, UUID validation, schema cache, redundant type check fix, HTTPException re-raise
- `src/models/suggestion.py` - DeclarativeBase migration, datetime.utcnow replacement
- `src/services/suggestion_service.py` - datetime.utcnow replacement
- `src/services/suggestion_scorer.py` - Removed sys.path hack, weight normalization, unused imports
- `src/services/blueprint_matcher.py` - Configurable limits from settings
- `src/database.py` - Alembic run_in_executor fix
- `alembic/env.py` - Override sqlalchemy.url from settings
- `requirements.txt` - pytest-asyncio version update

### Files Created
- `src/services/external_schemas.py` - Local copies of DeviceSignature, BlueprintSummary, UserProfile

### Files Deleted
- `migrate_db.py` - Duplicate migration script
- `scripts/add_blueprint_name_description_columns.py` - Duplicate migration script
- `migrations/add_blueprint_name_description.sql` - Duplicate SQL migration
