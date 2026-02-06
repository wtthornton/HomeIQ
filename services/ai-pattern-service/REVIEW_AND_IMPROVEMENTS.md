# AI Pattern Service - Comprehensive Code Review

**Reviewer:** Claude Opus 4.6 (Automated Deep Review)
**Date:** 2026-02-06
**Service:** ai-pattern-service (Tier 5 - AI Automation Features, Port 8020/8034)
**Codebase Size:** ~80 source files, ~30 test files, ~15,000 lines of code

---

## Executive Summary

**Overall Health Score: 5.5 / 10**

The ai-pattern-service is a feature-rich microservice with a well-defined domain (pattern detection, synergy analysis, blueprint opportunities). It demonstrates good architectural separation with distinct modules for API, CRUD, clients, scheduler, learning, and synergy detection. However, the codebase suffers from **significant code duplication**, **security vulnerabilities**, **dead code**, and **incomplete implementations** that reduce maintainability and reliability.

**Strengths:**
- Well-structured module separation (api/, clients/, crud/, learning/, synergy_detection/)
- Multi-stage Docker build with non-root user
- Graceful degradation for optional dependencies (GNN, Transformer, XAI)
- Comprehensive README with API documentation
- Good database integrity checking and recovery mechanisms
- Proper async/await patterns throughout

**Key Concerns:**
- Command injection vulnerability in database repair
- Massive code duplication in synergy_router.py (~1600 lines of repetitive JSON parsing)
- Dead/unreachable code in crud/synergies.py
- Hardcoded IP address in config defaults
- Community pattern endpoints are entirely stub implementations
- MQTT client lacks TLS support
- Pattern stats endpoint has ~550 lines of copy-pasted error handling
- `synergy_helpers.py` exists but is not used by `synergy_router.py`

---

## Critical Issues (Must Fix)

### C1. Command Injection in Database Repair

**File:** `src/database/integrity.py:116-123`
**Severity:** CRITICAL (OWASP A03:2021 - Injection)

The `attempt_database_repair()` function uses `shell=True` with string interpolation in `subprocess.run()`, which is a command injection vulnerability. If the `database_path` is ever influenced by user input or configuration, an attacker could execute arbitrary shell commands.

```python
# VULNERABLE - line 116
recover_cmd = f'sqlite3 "{db_path}" ".recover" | sqlite3 "{recovered_path}"'
result = subprocess.run(
    recover_cmd,
    shell=True,  # Command injection risk
    capture_output=True,
    text=True,
    timeout=300
)
```

**Fix:** Use list-based command execution without `shell=True`:
```python
# SAFE
import shutil
sqlite3_path = shutil.which("sqlite3")
if not sqlite3_path:
    logger.error("sqlite3 not found on PATH")
    return False

recover_proc = subprocess.run(
    [sqlite3_path, str(db_path), ".recover"],
    capture_output=True, text=True, timeout=300
)
if recover_proc.returncode == 0:
    import_proc = subprocess.run(
        [sqlite3_path, str(recovered_path)],
        input=recover_proc.stdout,
        capture_output=True, text=True, timeout=300
    )
```

### C2. Database Repair Endpoint Exposed Without Authentication

**File:** `src/api/health_router.py:120-158`
**Severity:** HIGH

The `POST /database/repair` endpoint is publicly accessible with no authentication. This destructive operation (can modify/replace database files) should require authentication or be restricted to internal networks only.

**Fix:** Add authentication middleware or restrict to internal-only access:
```python
@router.post("/database/repair", status_code=status.HTTP_200_OK)
async def repair_database_endpoint(
    x_internal_token: str = Header(..., alias="X-Internal-Token")
) -> dict[str, Any]:
    if x_internal_token != settings.internal_api_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    # ... rest of implementation
```

### C3. Hardcoded Private IP Address in Configuration

**File:** `src/config.py:47`
**Severity:** HIGH (Information Disclosure / Deployment Risk)

```python
ha_url: str = "http://192.168.1.86:8123"  # Home Assistant URL
```

A hardcoded private IP address in the default configuration:
1. Leaks internal network topology
2. Will not work in any deployment environment other than the developer's
3. Should use a service-discoverable hostname

**Fix:**
```python
ha_url: str = "http://homeassistant:8123"  # Use Docker service name
```

### C4. Dead/Unreachable Code in CRUD Synergies

**File:** `src/crud/synergies.py:258-265`
**Severity:** HIGH (Logic Bug)

After the `raise` on line 260, lines 261-265 are unreachable dead code. This means the `db.rollback()` cleanup on lines 262-264 will never execute:

```python
    except Exception as e:
        logger.error(f"Failed to store synergy opportunities: {e}", exc_info=True)
        raise          # <-- This exits the function
        try:           # <-- UNREACHABLE CODE
            await db.rollback()
        except Exception:
            pass
        raise          # <-- UNREACHABLE CODE
```

**Fix:** Move the rollback before the raise:
```python
    except Exception as e:
        logger.error(f"Failed to store synergy opportunities: {e}", exc_info=True)
        try:
            await db.rollback()
        except Exception:
            pass
        raise
```

---

## Major Issues (Should Fix)

### M1. Massive Code Duplication in synergy_router.py

**File:** `src/api/synergy_router.py` (~1606 lines)
**Impact:** Maintainability, Bug Risk

The file contains extreme duplication. The JSON parsing logic for synergy metadata/device_ids/chain_devices/explanation/context_breakdown is copy-pasted identically across `list_synergies()`, `get_synergy()`, `generate_automation_from_synergy()`, and `get_blueprint_matches_for_synergy()`. Each copy is ~80 lines of nearly identical code.

Additionally, `src/api/synergy_helpers.py` already contains helper functions (`safe_parse_json`, `extract_synergy_fields`, `find_synergy_by_id`) that were **designed to eliminate this duplication** but are **never imported or used** in `synergy_router.py`.

**Impact:** If a JSON parsing bug is found, it must be fixed in 4+ places. The helpers file is dead code.

**Fix:** Refactor `synergy_router.py` to use the existing `synergy_helpers.py`:
```python
from .synergy_helpers import extract_synergy_fields, find_synergy_by_id, safe_parse_json
```

### M2. Pattern Stats Endpoint - 500+ Lines of Copy-Pasted Error Handling

**File:** `src/api/pattern_router.py:226-545`
**Impact:** Maintainability

The `get_pattern_stats()` endpoint is ~320 lines long, with the stats calculation logic (lines 353-395) copy-pasted three more times in different error recovery branches (lines 410-449, lines 480-521). The same for-loop iterating patterns and calculating `by_type`, `total_confidence`, etc. appears 4 times.

**Fix:** Extract the stats calculation into a helper function:
```python
def _calculate_pattern_stats(patterns: list) -> dict:
    total_patterns = len(patterns)
    by_type = {}
    total_confidence = 0.0
    total_occurrences = 0
    unique_device_set = set()
    for p in patterns:
        # ... single implementation
    return {...}
```

### M3. Synergy Lookup by ID Loads ALL Records

**File:** `src/api/synergy_router.py:559-571`, `src/api/synergy_router.py:797-808`, `src/api/synergy_router.py:922-924`, `src/api/synergy_router.py:1079-1080`, `src/api/synergy_router.py:1540`
**Impact:** Performance

Multiple endpoints call `get_synergy_opportunities(db, limit=10000)` and then iterate through all results to find a single synergy by ID. This is an O(n) scan that loads up to 10,000 records into memory for a single lookup.

```python
# INEFFICIENT - loads 10,000 records to find one
synergies = await get_synergy_opportunities(db, limit=10000)
for s in synergies:
    if s.synergy_id == synergy_id:
        synergy = s
        break
```

**Fix:** Add a `get_synergy_by_id()` function to `crud/synergies.py`:
```python
async def get_synergy_by_id(db: AsyncSession, synergy_id: str) -> SynergyOpportunity | None:
    query = select(SynergyOpportunity).where(
        SynergyOpportunity.synergy_id == synergy_id
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()
```

### M4. MQTT Client Security Gaps

**File:** `src/clients/mqtt_client.py`
**Impact:** Security

1. **No TLS/SSL support:** The MQTT client does not configure TLS, even when connecting to `mqtts://` URLs. Line 42-49 parses the URL scheme but never sets up TLS.
2. **No certificate verification:** No `tls_set()` call is made on the paho client.
3. **Blocking sleep in async context:** Lines 107-108 use `time.sleep(0.1)` in a polling loop, which blocks the event loop. The reconnect handler on line 178 also uses `time.sleep(2)`.

**Fix for TLS:**
```python
if broker and broker.startswith('mqtts://'):
    import ssl
    self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
```

**Fix for blocking sleep:**
```python
# Use asyncio.sleep instead, or use paho-mqtt's callback-based connection
```

### M5. `logger` Used Before Definition in pattern_analysis.py

**File:** `src/scheduler/pattern_analysis.py:29-47`
**Impact:** Runtime Error

The `logger` variable is referenced on lines 33 and 43 inside `except ImportError` blocks, but `logger` is not defined until line 47. If `RelationshipDiscoveryEngine` or `TemporalSynergyDetector` fails to import, this will raise a `NameError`.

```python
# Line 33 - logger not yet defined!
except ImportError as e:
    logger.warning(f"RelationshipDiscoveryEngine not available: {e}")
# ...
# Line 47 - logger defined here
logger = logging.getLogger(__name__)
```

**Fix:** Move the `logger` definition before the try/except blocks, or use `logging.getLogger(__name__)` inline.

### M6. Deprecated SQLAlchemy API Usage

**File:** `src/database/models.py:19`
**Impact:** Future Compatibility

```python
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
```

`declarative_base()` is deprecated in SQLAlchemy 2.0. The modern approach is:
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

### M7. `datetime.utcnow()` Deprecation

**File:** `src/database/models.py:44,89`
**Impact:** Future Compatibility (Python 3.12+)

```python
created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
```

`datetime.utcnow()` is deprecated in Python 3.12+. Use timezone-aware datetime:
```python
from datetime import datetime, timezone
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
```

### M8. Missing `get()` Method on DataAPIClient

**File:** `src/api/synergy_router.py:1329`, `src/api/synergy_router.py:1401`, `src/api/synergy_router.py:1471`
**Impact:** Runtime Error

The blueprint endpoints call `data_client.get("/api/devices")`, but `DataAPIClient` in `src/clients/data_api_client.py` does not have a `get()` method. It only has `fetch_events()`, `fetch_devices()`, and `fetch_entities()`. This will raise an `AttributeError` at runtime.

**Fix:** Use `data_client.fetch_devices()` instead, or add a generic `get()` method to `DataAPIClient`.

---

## Minor Issues (Nice to Fix)

### m1. Inconsistent Port Configuration

- `config.py` line 33: `service_port: int = 8020`
- `main.py` line 320: `port=8020` (hardcoded, doesn't use `settings.service_port`)
- README states port 8024 in the task description but 8020 in all code

### m2. Emoji Usage in Log Messages

Throughout the codebase, log messages use emoji characters (lines like `logger.info("✅ Database initialized")`). While readable in console output, these characters can cause issues in some log aggregation systems and are inconsistent with structured logging best practices.

### m3. Duplicate Import of `logging` in synergy_router.py

**File:** `src/api/synergy_router.py:35-36`
```python
    import logging
    logger = logging.getLogger(__name__)
```
The `logger` is already defined on line 47. The import inside the except block creates a shadowed/duplicate logger.

### m4. `except` clauses too broad

Multiple locations use bare `except Exception` that catch and swallow important errors. For example in `crud/synergies.py:340-341`:
```python
except Exception:
    pass  # Column may not exist yet, migration will add it
```
This silently swallows all errors, not just missing column errors.

### m5. `conftest.py` - Test DB Override Doesn't Work for Async

**File:** `tests/conftest.py:118-126`

The `client` fixture overrides `get_db` with a synchronous function that returns the session directly, but `get_db` is an async generator. This override may not work correctly with FastAPI's dependency injection for async endpoints.

```python
@pytest.fixture
def client(test_db: AsyncSession):
    def override_get_db():
        return test_db  # Should be an async generator
    app.dependency_overrides[get_db] = override_get_db
```

**Fix:**
```python
async def override_get_db():
    yield test_db
```

### m6. Community Pattern Router is Entirely Stub

**File:** `src/api/community_pattern_router.py`

All 5 endpoints (list, submit, get, rate, get_ratings) are stub implementations that return empty data or always return 404. This is documented as "storage implementation pending (Phase 3.3)" but the router is registered in production, which could confuse API consumers.

### m7. Feedback Response Always Claims RL Updated

**File:** `src/api/synergy_router.py:879`
```python
"rl_updated": True  # Always returns True even if RL update failed
```

The response always says `rl_updated: True` regardless of whether the RL optimizer was actually updated (lines 860-870 catch and log the failure but don't affect the response).

### m8. `get_db()` commits on every request

**File:** `src/database/__init__.py:77-85`

The `get_db()` dependency auto-commits after every request, even for GET requests that only read data:
```python
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Commits even on GET requests
```

While not harmful for reads, this is unnecessary overhead and could cause confusion.

### m9. Test Dependencies in Production requirements.txt

**File:** `requirements.txt:43-44`
```
pytest==9.0.2
pytest-asyncio==1.3.0
```

Test dependencies should be in a separate `requirements-dev.txt` file, not in the production requirements.

### m10. `asyncio.get_event_loop()` Deprecation

**File:** `src/database/integrity.py:238`
```python
loop = asyncio.get_event_loop()
return await loop.run_in_executor(None, _repair_sync)
```

`asyncio.get_event_loop()` is deprecated in Python 3.12+. Use `asyncio.to_thread()` instead:
```python
return await asyncio.to_thread(_repair_sync)
```

---

## Enhancement Recommendations

### E1. Add Pydantic Response Models

Currently, all API endpoints return `dict[str, Any]`. Define Pydantic response models for type safety, automatic documentation, and validation:

```python
class PatternListResponse(BaseModel):
    success: bool
    data: PatternListData
    message: str

class PatternListData(BaseModel):
    patterns: list[PatternItem]
    count: int
```

### E2. Add Request Rate Limiting

The `/database/repair` and `/api/analysis/trigger` endpoints perform expensive operations but have no rate limiting. Consider adding `slowapi` or similar middleware.

### E3. Centralize Error Handling Pattern

The database corruption detection and repair logic is duplicated across `pattern_router.py` (lines 168-223 and 291-545) and `health_router.py`. Extract into a reusable decorator or middleware:

```python
@handle_database_corruption
async def list_patterns(db: AsyncSession = Depends(get_db)):
    # Just the business logic, no corruption handling
```

### E4. Add Input Validation for synergy_id

The `synergy_id` path parameter is not validated in any endpoint. Add a regex pattern to ensure it matches expected UUID format:

```python
@router.get("/{synergy_id}")
async def get_synergy(
    synergy_id: str = Path(..., regex=r"^[a-zA-Z0-9_-]+$"),
    ...
```

### E5. Connection Pooling for DataAPIClient

Each scheduler run creates a new `DataAPIClient` instance. Consider using a singleton or connection pool to reuse HTTP connections across requests.

### E6. Add Structured Logging

Replace string-formatted log messages with structured logging using `extra` parameters for better log aggregation:

```python
logger.info(
    "Stored patterns in database",
    extra={"count": stored_count, "duration_ms": elapsed}
)
```

---

## Architecture Improvement Suggestions

### A1. Use the Existing Helper Functions

The `synergy_helpers.py` module contains well-designed utility functions that would eliminate 500+ lines of duplication in `synergy_router.py`. This is the single highest-impact refactoring opportunity in the service.

### A2. Split synergy_router.py Into Multiple Routers

At ~1600 lines, `synergy_router.py` handles too many concerns:
- Synergy CRUD (list, get, stats)
- Feedback/RL
- Automation generation
- Execution tracking
- Blueprint opportunities

Split into:
- `synergy_crud_router.py` - List, get, stats
- `synergy_feedback_router.py` - Feedback, RL
- `automation_router.py` - Generation, execution tracking
- `blueprint_router.py` - Blueprint opportunities (already partially separate)

### A3. Dependency Injection for Service Instances

Multiple endpoints create new instances of services per request:
```python
# Created per request - wasteful
rl_optimizer = RLSynergyOptimizer()
explainer = ExplainableSynergyGenerator()
```

Use FastAPI's dependency injection to create singletons:
```python
def get_rl_optimizer() -> RLSynergyOptimizer:
    return _rl_optimizer_instance

@router.post("/{synergy_id}/feedback")
async def submit_feedback(
    rl_optimizer: RLSynergyOptimizer = Depends(get_rl_optimizer)
):
```

### A4. Remove or Complete Stub Endpoints

The community pattern router has 5 endpoints that do nothing. Either:
1. Remove them until the feature is implemented
2. Mark them with a clear `501 Not Implemented` status code
3. Implement the storage layer

### A5. Add Database Migration System

The codebase relies on manual migration scripts (`scripts/add_2025_synergy_fields.py`) and `hasattr()` checks for column existence. Consider adopting Alembic for proper database migrations.

---

## Testing Coverage Analysis

### Current Test Files (30 files)
- `test_main.py` - App initialization (12 tests) -- GOOD
- `test_health_router.py` - Health endpoints
- `test_pattern_analyzer.py` - Pattern detection
- `test_learning.py` - Learning modules
- `test_scheduler.py` - Scheduler
- `test_clients.py` - API/MQTT clients
- `test_crud_patterns.py` - Pattern CRUD
- `test_crud_synergies.py` - Synergy CRUD
- `test_synergy_detector.py` - Synergy detection
- Various synergy detection tests
- E2E tests

### Coverage Gaps
1. **No tests for `synergy_helpers.py`** - The utility module has no test coverage
2. **No tests for database integrity/repair** - The `integrity.py` module (330 lines) has no dedicated tests
3. **No tests for `analysis_router.py`** - The analysis trigger/status endpoints are untested
4. **No tests for blueprint router endpoints** - Blueprint opportunity endpoints lack tests
5. **No tests for `automation_metrics.py`**, `energy_savings_calculator.py`, `feedback_client.py`
6. **No negative tests for input validation** - Missing tests for malformed inputs, SQL injection attempts
7. **`conftest.py` async override** may not work correctly (see m5)

### Test Quality
- Tests use proper mocking and async patterns
- Good coverage of startup/shutdown lifecycle
- Missing integration tests for the full scheduler pipeline
- No property-based testing despite `test_pattern_detection_properties.py` existing

---

## Dependency Analysis

### Production Dependencies (requirements.txt)

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| fastapi | >=0.123.0,<0.124.0 | Outdated | Current stable is 0.115+ (2026) |
| uvicorn | >=0.32.0,<0.33.0 | OK | |
| pydantic | >=2.9.0,<3.0.0 | OK | |
| sqlalchemy | ==2.0.46 | OK | Pinned |
| aiosqlite | ==0.22.1 | OK | Pinned |
| pandas | >=2.2.0,<3.0.0 | OK | Heavy dependency for pattern analysis |
| numpy | >=1.26.0,<1.27.0 | OK | |
| scikit-learn | >=1.5.0,<2.0.0 | OK | Heavy dependency |
| scipy | >=1.16.3,<2.0.0 | OK | Heavy dependency |
| paho-mqtt | ==2.1.0 | OK | Pinned |
| apscheduler | ==3.11.2 | OK | APScheduler 4.0 is available |
| pytest* | ==9.0.2 | **WRONG** | Test dep in prod requirements |
| pytest-asyncio* | ==1.3.0 | **WRONG** | Test dep in prod requirements |

**Image Size Impact:** The combination of pandas, numpy, scikit-learn, and scipy adds ~500MB+ to the Docker image. Consider whether all are needed for production or if some are only used in optional features.

---

## Docker Review

**File:** `Dockerfile`

**Good Practices:**
- Multi-stage build (builder + production)
- Alpine base image for smaller size
- Non-root user (`appuser:1001`)
- Health check configured
- Build cache for pip

**Issues:**
1. **Line 10:** `pip install --upgrade pip==25.2` - Pinning pip to a specific version may cause build failures if the version is removed from PyPI
2. **No .dockerignore review:** The `.dockerignore` exists but should be verified to exclude `.venv/`, `tests/`, `htmlcov/`, etc.
3. **COPY shared/ ./shared/** (line 37) - Copies the entire shared directory; could be more selective
4. **No Python bytecode compilation:** Consider adding `RUN python -m compileall /app/src/` for faster startup

---

## Summary of Priorities

| Priority | Issue | Impact | Effort |
|----------|-------|--------|--------|
| 1 | C1: Command injection in db repair | Security | Low |
| 2 | C4: Dead code in crud/synergies.py | Logic bug | Low |
| 3 | C2: Unauth repair endpoint | Security | Low |
| 4 | C3: Hardcoded IP | Deployment | Low |
| 5 | M5: Logger before definition | Runtime error | Low |
| 6 | M1: Use synergy_helpers.py | Maintainability | Medium |
| 7 | M3: O(n) synergy lookup | Performance | Low |
| 8 | M4: MQTT TLS support | Security | Medium |
| 9 | M8: Missing DataAPIClient.get() | Runtime error | Low |
| 10 | M2: Deduplicate pattern stats | Maintainability | Medium |
| 11 | m9: Test deps in prod requirements | Build | Low |
| 12 | A1-A5: Architecture improvements | Long-term | High |

---

*This review was generated through a comprehensive reading of all source files, test files, configuration files, and deployment artifacts in the ai-pattern-service directory.*

---

## Fixes Applied

**Date:** 2026-02-06
**Applied by:** Claude Opus 4.6 (Automated Fix)

### Critical Issues Fixed

| Issue | Fix | File(s) |
|-------|-----|---------|
| **C1: Command injection in database repair** | Replaced `shell=True` + string interpolation with list-based `subprocess.run()` using `shutil.which("sqlite3")`. Recover and import are now two separate safe subprocess calls piped via `input=`. | `src/database/integrity.py` |
| **C2: Unauth repair endpoint** | Added `X-Internal-Token` header requirement to `POST /database/repair`. Token validated against new `settings.internal_api_token` config value. | `src/api/health_router.py`, `src/config.py` |
| **C3: Hardcoded private IP** | Changed `ha_url` default from `http://192.168.1.86:8123` to `http://homeassistant:8123` (Docker service name). | `src/config.py` |
| **C4: Dead/unreachable code** | Moved `db.rollback()` before `raise` in the outer except block of `store_synergy_opportunities()`. | `src/crud/synergies.py` |

### Major Issues Fixed

| Issue | Fix | File(s) |
|-------|-----|---------|
| **M1: Massive code duplication in synergy_router.py** | Refactored `list_synergies()`, `get_synergy()`, `generate_automation_from_synergy()`, and `get_blueprint_matches_for_synergy()` to use `extract_synergy_fields()`, `safe_parse_json()`, and `generate_xai_explanation()` from `synergy_helpers.py`. Eliminated ~500 lines of duplicated JSON parsing. | `src/api/synergy_router.py` |
| **M2: Pattern stats duplication** | Extracted `_calculate_pattern_stats()` helper function. All error recovery branches now call this single function instead of copy-pasting the stats loop. Reduced ~320 lines of duplication to one function. | `src/api/pattern_router.py` |
| **M3: O(n) synergy lookups** | Added `get_synergy_by_id()` to `crud/synergies.py` with direct `WHERE synergy_id = ?` query. Replaced 5 instances of `get_synergy_opportunities(db, limit=10000)` + loop with direct lookup. | `src/crud/synergies.py`, `src/api/synergy_router.py` |
| **M4: MQTT client TLS support** | Added `_use_tls` flag parsed from `mqtts://` or `wss://` URL schemes. Added `client.tls_set(cert_reqs=ssl.CERT_REQUIRED)` call when TLS is needed. | `src/clients/mqtt_client.py` |
| **M5: Logger before definition** | Moved `logger = logging.getLogger(__name__)` and `DeviceSynergyDetector` import before the try/except blocks for optional imports. | `src/scheduler/pattern_analysis.py` |
| **M6: Deprecated declarative_base** | Replaced `from sqlalchemy.ext.declarative import declarative_base` / `Base = declarative_base()` with `from sqlalchemy.orm import DeclarativeBase` / `class Base(DeclarativeBase): pass`. | `src/database/models.py` |
| **M7: Deprecated datetime.utcnow** | Replaced `default=datetime.utcnow` with `default=lambda: datetime.now(timezone.utc)` on both `SynergyOpportunity.created_at` and `SynergyFeedback.created_at`. | `src/database/models.py` |
| **M8: Missing DataAPIClient.get()** | Added generic `get(path, params)` method to `DataAPIClient` so blueprint endpoints can call `data_client.get("/api/devices")`. | `src/clients/data_api_client.py` |

### Minor Issues Fixed

| Issue | Fix | File(s) |
|-------|-----|---------|
| **m1: Inconsistent port config** | Changed `main.py` to use `settings.service_port` instead of hardcoded `8020`. | `src/main.py` |
| **m3: Duplicate logging import** | Removed duplicate `import logging` / `logger = ...` inside except block. Moved `logger` definition before try/except blocks. | `src/api/synergy_router.py` |
| **m5: conftest async override** | Changed `override_get_db()` from sync function returning session to async generator yielding session. | `tests/conftest.py` |
| **m7: RL updated always True** | Changed feedback response to track actual RL update result via `rl_updated` variable. Returns `False` if RL optimizer import fails or update throws. | `src/api/synergy_router.py` |
| **m9: Test deps in prod requirements** | Moved `pytest` and `pytest-asyncio` from `requirements.txt` to new `requirements-dev.txt`. | `requirements.txt`, `requirements-dev.txt` (new) |
| **m10: asyncio.get_event_loop() deprecation** | Replaced `loop = asyncio.get_event_loop(); await loop.run_in_executor(...)` with `await asyncio.to_thread(...)`. | `src/database/integrity.py` |

### Enhancement Recommendations Not Implemented (Deferred)

The following enhancement recommendations were reviewed but intentionally deferred as they represent larger architectural changes beyond the scope of this fix pass:

- **E1-E6**: Pydantic response models, rate limiting, centralized error handling decorator, input validation regex, connection pooling, structured logging
- **A1-A5**: Router splitting, dependency injection singletons, stub endpoint cleanup, Alembic migrations (A1 partially addressed via M1 refactor)
