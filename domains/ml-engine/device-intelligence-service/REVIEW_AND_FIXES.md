# Device Intelligence Service - Code Review & Fixes

**Service**: Device Intelligence Service (Tier 3 AI/ML Core)
**Port**: 8028 (external) / 8019 (internal)
**Reviewer**: Claude Opus 4.6 Deep Code Review
**Date**: 2026-02-06
**Files Reviewed**: 50+ source files, 19 test files, Dockerfile, docker-compose.yml, requirements

---

## Service Overview

The Device Intelligence Service is a FastAPI-based microservice providing centralized device discovery, health scoring, predictive analytics (ML-powered failure prediction), device hygiene analysis, name enhancement, and device mapping intelligence for a Home Assistant integration platform. It discovers devices from Home Assistant WebSocket API and Zigbee2MQTT via MQTT, unifies them into a common model, stores them in SQLite, and exposes REST + WebSocket APIs.

**Key Components**:
- **Discovery Engine**: Multi-source device discovery (HA WebSocket API + Zigbee2MQTT MQTT)
- **Predictive Analytics**: RandomForest, LightGBM, TabPFN, River incremental learning for failure prediction
- **Device Hygiene**: Automated analysis of naming issues, missing areas, stale devices
- **Name Enhancement**: Pattern-based + optional AI-powered device name suggestions
- **Device Mappings**: Extensible handler registry for device-specific intelligence (Hue, WLED)
- **Training Scheduler**: APScheduler-based nightly model retraining

**Tech Stack**: Python 3.12, FastAPI 0.123.x, SQLAlchemy 2.0 (async SQLite), scikit-learn, LightGBM, TabPFN, River, APScheduler, Pydantic 2.12, WebSockets

---

## Code Quality Score: 5.5 / 10

| Category | Score | Notes |
|----------|-------|-------|
| Architecture | 7/10 | Good separation of concerns, clean router pattern |
| Security | 3/10 | SQL injection vulnerabilities, no authentication, XSS risks |
| Error Handling | 5/10 | Inconsistent; some areas excellent, others catch-all Exception |
| Performance | 6/10 | Good caching patterns, but memory leaks and unbounded collections |
| API Design | 6/10 | RESTful patterns, but duplicate routes and inconsistent responses |
| ML Management | 7/10 | Multiple model backends, synthetic data generation, scheduled training |
| Testing | 5/10 | Good coverage for some modules, missing for many others |
| Code Style | 6/10 | Generally consistent, but emoji logging and deprecated API usage |
| Documentation | 7/10 | Good docstrings, clear module-level docs |
| Configuration | 5/10 | Hardcoded values, port mismatches, environment leakage |

---

## Critical Priority Issues

### CRIT-1: SQL Injection in database_management.py

**File**: `src/api/database_management.py`, line 252
**Severity**: CRITICAL
**OWASP**: A03:2021 - Injection

Table names from database metadata are interpolated directly into SQL queries without sanitization. While the table names come from the database itself (not directly from user input), this pattern is dangerous because (a) table names could be manipulated via other vulnerabilities, and (b) it sets a dangerous precedent.

```python
# BEFORE (VULNERABLE)
for table in inspector.get_table_names():
    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
    count = result.scalar()
```

```python
# AFTER (SAFE)
ALLOWED_TABLES = {"devices", "device_capabilities", "device_relationships",
                  "device_health_metrics", "device_entities", "device_hygiene_issues",
                  "discovery_sessions", "cache_stats", "name_suggestions",
                  "name_preferences", "zigbee_device_metadata",
                  "team_tracker_integrations", "team_tracker_teams"}

for table in inspector.get_table_names():
    if table not in ALLOWED_TABLES:
        logger.warning(f"Skipping unknown table: {table}")
        continue
    result = await session.execute(
        text(f"SELECT COUNT(*) FROM [{table}]")  # SQLite bracket quoting
    )
    count = result.scalar()
```

### CRIT-2: SQL Injection in device_service.py bulk_upsert_devices

**File**: `src/services/device_service.py`
**Severity**: CRITICAL
**OWASP**: A03:2021 - Injection

The `bulk_upsert_devices` method builds raw SQL using dictionary keys from device data. If device data keys contain malicious SQL, this could allow injection.

```python
# BEFORE (VULNERABLE) - conceptual issue
# Dict keys used directly in SQL column references without validation
columns = ", ".join(devices_data[0].keys())
placeholders = ", ".join([f":{key}" for key in devices_data[0].keys()])
sql = f"INSERT OR REPLACE INTO devices ({columns}) VALUES ({placeholders})"
```

**Fix**: Use SQLAlchemy's parameterized `sqlite_insert` with `on_conflict_do_update` instead of raw SQL string construction, similar to how `repository.py` handles `bulk_upsert_capabilities`.

### CRIT-3: No Authentication on Destructive Endpoints

**File**: `src/api/database_management.py`
**Severity**: CRITICAL
**OWASP**: A01:2021 - Broken Access Control

Multiple endpoints that can destroy data have zero authentication:

- `POST /api/db/recreate-tables` - Drops and recreates ALL database tables
- `POST /api/db/cleanup` - Deletes data from tables
- `POST /api/db/optimize` - Runs VACUUM on database
- `POST /api/device-mappings/reload` - Reloads registry

```python
# BEFORE (NO AUTH)
@router.post("/db/recreate-tables")
async def recreate_tables():
    ...

# AFTER (WITH AUTH)
from fastapi import Depends, Header, HTTPException

async def verify_admin_token(x_admin_token: str = Header(...)):
    """Verify admin token for destructive operations."""
    expected = settings.ADMIN_API_TOKEN
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=403, detail="Invalid admin token")

@router.post("/db/recreate-tables", dependencies=[Depends(verify_admin_token)])
async def recreate_tables():
    ...
```

---

## High Priority Issues

### HIGH-1: WebSocket Test Page XSS Vulnerability

**File**: `src/api/websocket_router.py`
**Severity**: HIGH
**OWASP**: A03:2021 - Injection (XSS)

The embedded HTML test page uses `innerHTML` to render WebSocket messages without sanitization:

```javascript
// BEFORE (XSS VULNERABLE)
messagesDiv.innerHTML += '<p>' + data + '</p>';

// AFTER (SAFE)
const p = document.createElement('p');
p.textContent = data;
messagesDiv.appendChild(p);
```

### HIGH-2: MQTT Disconnect Handler Calls asyncio.create_task from Non-Async Thread

**File**: `src/clients/mqtt_client.py`
**Severity**: HIGH

The `_on_disconnect` callback is called by paho-mqtt from a non-async thread, but attempts to call `asyncio.create_task()` which will fail with a RuntimeError.

```python
# BEFORE (BROKEN)
def _on_disconnect(self, client, userdata, rc):
    if self._auto_reconnect:
        asyncio.create_task(self._reconnect())  # FAILS - not in async context

# AFTER (CORRECT)
def _on_disconnect(self, client, userdata, rc):
    if self._auto_reconnect and self._loop:
        asyncio.run_coroutine_threadsafe(self._reconnect(), self._loop)
```

### HIGH-3: Unbounded metrics_history List (Memory Leak)

**File**: `src/core/ml_metrics.py`
**Severity**: HIGH

The `metrics_history` list grows without bound, eventually consuming all available memory:

```python
# BEFORE (UNBOUNDED)
self.metrics_history: list[dict] = []

def record_metric(self, metric):
    self.metrics_history.append(metric)

# AFTER (BOUNDED)
from collections import deque

self.metrics_history: deque = deque(maxlen=10000)  # Keep last 10K entries

def record_metric(self, metric):
    self.metrics_history.append(metric)
```

### HIGH-4: No WebSocket Authentication or Connection Limits

**File**: `src/core/websocket_manager.py`
**Severity**: HIGH
**OWASP**: A01:2021 - Broken Access Control

WebSocket connections accept any client with no authentication, no rate limiting, and no connection cap. This enables denial-of-service by opening unlimited connections.

```python
# BEFORE (NO LIMITS)
async def connect(self, websocket: WebSocket, client_id: str):
    await websocket.accept()
    self.active_connections[client_id] = websocket

# AFTER (WITH LIMITS)
MAX_CONNECTIONS = 100

async def connect(self, websocket: WebSocket, client_id: str):
    if len(self.active_connections) >= self.MAX_CONNECTIONS:
        await websocket.close(code=1013, reason="Too many connections")
        return False
    await websocket.accept()
    self.active_connections[client_id] = websocket
    return True
```

### HIGH-5: Broadcast Endpoint Without Authentication

**File**: `src/api/websocket_router.py`
**Severity**: HIGH

The `/ws/broadcast/test` endpoint can send messages to ALL connected WebSocket clients with no authentication:

```python
# This endpoint should require authentication
@router.post("/ws/broadcast/test")
async def broadcast_test(message: dict):
    await websocket_manager.broadcast(json.dumps(message))
```

### HIGH-6: Predictions Router Creates Separate Analytics Engine Instance

**File**: `src/api/predictions_router.py`
**Severity**: HIGH

The `get_analytics_engine` dependency creates a new `PredictiveAnalyticsEngine()` instance on every call instead of using the one initialized and stored in `app.state.analytics_engine` during startup. This means predictions run against an untrained model.

```python
# BEFORE (CREATES NEW UNTRAINED INSTANCE)
def get_analytics_engine():
    return PredictiveAnalyticsEngine()

# AFTER (USES APP STATE)
from fastapi import Request

async def get_analytics_engine(request: Request) -> PredictiveAnalyticsEngine:
    engine = getattr(request.app.state, "analytics_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Analytics engine not initialized")
    return engine
```

---

## Medium Priority Issues

### MED-1: Duplicate Route Definitions

**File**: `src/api/discovery.py`, lines 191 and 279
**Severity**: MEDIUM

Two `@router.get("/devices")` endpoints are defined with different response models. FastAPI will only match the first one; the second is dead code.

### MED-2: Health Check Dependencies Return Hardcoded "connected"

**File**: `src/api/health.py`
**Severity**: MEDIUM

Health check dependencies always report `"connected"` status without actually testing any connections:

```python
# BEFORE (FAKE HEALTH CHECK)
async def check_database():
    return {"database": "connected"}

# AFTER (REAL HEALTH CHECK)
async def check_database():
    try:
        async for session in get_db_session():
            await session.execute(text("SELECT 1"))
            return {"database": "connected"}
    except Exception as e:
        return {"database": "disconnected", "error": str(e)}
```

### MED-3: datetime.utcnow() Usage (Deprecated)

**Files**: `src/core/predictive_analytics.py`, `src/api/name_enhancement_router.py`, `src/services/name_enhancement/batch_processor.py`, `src/services/name_enhancement/preference_learner.py`
**Severity**: MEDIUM

`datetime.utcnow()` is deprecated in Python 3.12+. Use `datetime.now(timezone.utc)` instead.

```python
# BEFORE (DEPRECATED)
from datetime import datetime
prediction["predicted_at"] = datetime.utcnow().isoformat()

# AFTER (CORRECT)
from datetime import datetime, timezone
prediction["predicted_at"] = datetime.now(timezone.utc).isoformat()
```

### MED-4: Division by Zero in devices.py

**File**: `src/api/devices.py`, line 96
**Severity**: MEDIUM

```python
# BEFORE (DIVISION BY ZERO WHEN limit=0)
page = skip // limit + 1

# AFTER (SAFE)
page = (skip // limit + 1) if limit > 0 else 1
```

### MED-5: Recommendation Sorting Compares Enum String Values

**File**: `src/core/recommendation_engine.py`
**Severity**: MEDIUM

Priority enums are sorted by string value (`"critical"` < `"high"` < `"low"` < `"medium"` alphabetically), not by actual priority.

```python
# BEFORE (INCORRECT SORT ORDER)
recommendations.sort(key=lambda r: (r.priority.value, r.confidence_score), reverse=True)

# AFTER (CORRECT SORT ORDER)
PRIORITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}
recommendations.sort(
    key=lambda r: (PRIORITY_ORDER.get(r.priority.value, 0), r.confidence_score),
    reverse=True
)
```

### MED-6: Global Mutable State Everywhere

**Files**: Multiple files use module-level global singletons
**Severity**: MEDIUM

Files like `cache.py`, `device_state_tracker.py`, `health_scorer.py`, `performance_collector.py`, `websocket_manager.py`, and `device_mappings/cache.py` all use global mutable state via module-level singleton instances. This makes testing difficult, prevents proper lifecycle management, and can cause issues with async concurrency.

**Recommendation**: Use FastAPI's dependency injection and `app.state` instead of global singletons.

### MED-7: Training Scheduler Modifies Settings Directly

**File**: `src/scheduler/training_scheduler.py`
**Severity**: MEDIUM

The training scheduler modifies `settings.ML_TRAINING_MODE` directly, which is not thread-safe and violates the principle that settings should be immutable after initialization.

### MED-8: Hardcoded IP Addresses

**File**: `src/config.py`, `docker-compose.yml`
**Severity**: MEDIUM

Hardcoded IP `192.168.1.86` for MQTT broker default and in docker-compose HA_URL. These should always come from environment variables with no default or a localhost default.

### MED-9: Missing asyncio Import in cache.py

**File**: `src/core/cache.py`
**Severity**: MEDIUM

The `start_cache_cleanup_task()` method uses `asyncio` but it is not imported at the module level. The code relies on an implicit import that may not be present.

### MED-10: Deprecated declarative_base() Usage

**File**: `src/models/database.py`
**Severity**: MEDIUM

Uses `declarative_base()` which is deprecated in SQLAlchemy 2.0. Should use the `DeclarativeBase` class pattern instead.

```python
# BEFORE (DEPRECATED)
from sqlalchemy.orm import declarative_base
Base = declarative_base()

# AFTER (MODERN)
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

### MED-11: Boolean Comparison with == True

**File**: `src/api/team_tracker_router.py`
**Severity**: MEDIUM

```python
# BEFORE (ANTI-PATTERN)
TeamTrackerTeam.is_active == True

# AFTER (CORRECT SQLAlchemy PATTERN)
TeamTrackerTeam.is_active.is_(True)
```

### MED-12: Unreachable Code in ha_client.py

**File**: `src/clients/ha_client.py`, line 173
**Severity**: MEDIUM

A `break` statement follows a `return True`, making the break unreachable:

```python
# BEFORE
return True
break  # UNREACHABLE

# AFTER
return True
```

### MED-13: Logging Level Hardcoded to DEBUG in main.py

**File**: `src/main.py`, line 39
**Severity**: MEDIUM

```python
# BEFORE (HARDCODED)
logging.basicConfig(level=logging.DEBUG, ...)

# AFTER (CONFIGURABLE)
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO), ...)
```

### MED-14: Error Messages Leaking Internal Details

**File**: `src/api/database_management.py` and others
**Severity**: MEDIUM
**OWASP**: A09:2021 - Security Logging and Monitoring Failures

Exception details are returned directly in API responses, potentially exposing internal paths, database schemas, and stack traces.

```python
# BEFORE (LEAKING)
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

# AFTER (SAFE)
except Exception as e:
    logger.error(f"Database operation failed: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Low Priority Issues

### LOW-1: Incremental Predictor Returns Hard 0/1 Probabilities

**File**: `src/core/incremental_predictor.py`
**Severity**: LOW

The `predict_proba()` method returns `[[0.0, 1.0]]` or `[[1.0, 0.0]]` instead of actual probability distributions. This defeats the purpose of probability estimation.

### LOW-2: Late Imports in name_enhancement_router.py

**File**: `src/api/name_enhancement_router.py`, lines 330 and 455
**Severity**: LOW

`asyncio` and `logging` are imported at the bottom of the file instead of the top, violating PEP 8 convention and potentially causing confusion.

### LOW-3: Port Mismatch Documentation

**Severity**: LOW

Config defaults to port 8019, docker-compose maps 8028:8019, but various documentation references may be inconsistent. The external port (8028) should be clearly documented.

### LOW-4: get_nabu_casa_ws_url Return Type Mismatch

**File**: `src/config.py`
**Severity**: LOW

Method signature says `-> str` but can return `None`:

```python
# BEFORE
def get_nabu_casa_ws_url(self) -> str:
    ...
    return None  # Type mismatch

# AFTER
def get_nabu_casa_ws_url(self) -> str | None:
    ...
```

### LOW-5: Pattern Cache in DeviceNameGenerator Unbounded

**File**: `src/services/name_enhancement/name_generator.py`
**Severity**: LOW

`self.pattern_cache: dict[str, NameSuggestion] = {}` grows without bound. Should use an LRU cache or bounded dict.

### LOW-6: DeviceMappingCache No Periodic Cleanup

**File**: `src/device_mappings/cache.py`
**Severity**: LOW

The `cleanup_expired()` method exists but is never called automatically. Expired entries only get cleaned on cache miss.

### LOW-7: _store_zigbee_metadata Logs Wrong Count

**File**: `src/core/discovery_service.py`, line 807
**Severity**: LOW

```python
# BEFORE (ALWAYS LOGS 0)
logger.info(f"Stored Zigbee2MQTT metadata for {len(metadata_to_store)} devices")
# metadata_to_store is always empty - items are added to session directly

# AFTER (CORRECT COUNT)
stored_count = sum(1 for d in unified_devices if d.zigbee_device)
logger.info(f"Stored Zigbee2MQTT metadata for {stored_count} devices")
```

### LOW-8: conftest.py Skips All Tests When Core Modules Unavailable

**File**: `tests/conftest.py`
**Severity**: LOW

The conftest unconditionally skips the entire test suite if `src.core` cannot be imported, but provides no test client fixture (several test files reference `client: TestClient` which does not exist in conftest). Tests like `test_main.py` and `test_health.py` likely fail with fixture not found errors.

### LOW-9: Emoji Logging in Production

**Files**: All source files
**Severity**: LOW

Extensive emoji usage in log messages can cause encoding issues in some log aggregation systems and makes log parsing with regex more difficult.

---

## Security Review

### OWASP Top 10 Assessment

| OWASP Category | Status | Details |
|---------------|--------|---------|
| A01: Broken Access Control | FAIL | No authentication on any endpoints, including destructive ones |
| A02: Cryptographic Failures | PASS | HA tokens handled via env vars, no custom crypto |
| A03: Injection | FAIL | SQL injection in 2 locations, XSS in WebSocket test page |
| A04: Insecure Design | WARN | No rate limiting, no request size limits |
| A05: Security Misconfiguration | WARN | CORS allows all origins via config, DEBUG logging in prod |
| A06: Vulnerable Components | PASS | Dependencies are recent versions with pinned ranges |
| A07: Auth Failures | FAIL | Zero authentication implemented |
| A08: Data Integrity Failures | WARN | No input validation on bulk operations |
| A09: Logging Failures | WARN | Error details leaked in responses, DEBUG level in prod |
| A10: SSRF | LOW RISK | HA URL from config, not user-controlled |

### Authentication Gaps

The entire service has zero authentication. Every endpoint is publicly accessible to anyone with network access, including:

1. `POST /api/db/recreate-tables` - Destroys all data
2. `POST /api/db/cleanup` - Deletes selective data
3. `POST /api/predictions/train` - Triggers resource-intensive training
4. `POST /ws/broadcast/test` - Sends messages to all WebSocket clients
5. `POST /ws/simulate` - Injects fake device data
6. `POST /api/device-mappings/reload` - Reloads handler registry
7. All device CRUD operations

### Recommendation

At minimum, implement API key authentication via header for all non-health endpoints. For destructive operations, use a separate admin token.

---

## Performance Review

### Strengths
- **Caching**: DeviceCache with TTL, in-memory caches for device mappings and name validation
- **Bulk Operations**: SQLAlchemy bulk inserts/upserts used for device storage
- **Async I/O**: Consistent async/await usage throughout
- **Connection Pooling**: Implied via SQLAlchemy async engine

### Concerns

1. **Unbounded Collections**: `metrics_history` list, `pattern_cache` dict, `errors` list in DiscoveryService all grow without bound
2. **N+1 Query Risk**: `_find_conflicts` in name_validator.py loads all devices/entities to compare names
3. **Full Table Scans**: `_find_devices_needing_enhancement` queries all devices without name_by_user
4. **New Cache Per Request**: `health_router.py` creates a new `DeviceCache()` instance in its dependency function instead of using a shared instance
5. **Synchronous ML Training**: Model training in `predictive_analytics.py` runs synchronously (numpy/sklearn are GIL-bound), blocking the event loop during training
6. **Large In-Memory State**: `discovery_service.py` holds all devices, entities, areas, and config entries in memory simultaneously

### Optimization Recommendations

1. Use `deque(maxlen=N)` for bounded collections
2. Add database indexes for frequently queried fields (name lookups for uniqueness)
3. Run ML training in a thread pool executor: `await asyncio.get_event_loop().run_in_executor(None, train_func)`
4. Implement pagination for bulk device queries
5. Share cache instances via dependency injection instead of creating new ones

---

## Test Coverage Assessment

### Test Files Found: 19

| Test File | Module Tested | Tests | Quality |
|-----------|--------------|-------|---------|
| test_main.py | Main app | 5 | Basic - needs client fixture |
| test_health.py | Health endpoints | 6 | Basic - needs client fixture |
| test_predictive_analytics.py | ML engine | 16 | Good - covers training, prediction, API |
| test_discovery_service.py | Discovery | 9 | Good - covers start/stop/status/query |
| test_hygiene_analyzer.py | Hygiene analysis | 2 | Good - covers detection and resolution |
| test_remediation_service.py | Remediation | 4 | Good - covers success and failure paths |
| test_synthetic_device_generator.py | Synthetic data | 30+ | Excellent - comprehensive range validation |
| test_ha_client.py | HA WebSocket client | Unknown | Not reviewed |
| test_model_training.py | Training pipeline | Unknown | Not reviewed |
| test_realtime_monitoring.py | Real-time monitoring | Unknown | Not reviewed |
| test_storage_api.py | Storage API | Unknown | Not reviewed |
| test_device_mappings.py | Device mappings | Unknown | Not reviewed |
| test_hue_handler.py | Hue handler | Unknown | Not reviewed |
| test_wled_handler.py | WLED handler | Unknown | Not reviewed |
| test_device_mappings_api.py | Mappings API | Unknown | Not reviewed |
| test_hygiene_router.py | Hygiene router | Unknown | Not reviewed |
| conftest.py | Test setup | N/A | Missing test client fixture |

### Coverage Gaps

1. **No tests for**: `database_management.py` (SQL injection), `websocket_router.py`, `name_enhancement_router.py`, `recommendations_router.py`, `config.py`, `mqtt_client.py`, `data_api_client.py`
2. **Missing fixture**: `client: TestClient` referenced in `test_main.py` and `test_health.py` but not defined in `conftest.py`
3. **No security tests**: No tests for input validation, injection prevention, or auth
4. **No integration tests**: No tests that exercise the full discovery -> storage -> prediction pipeline with real async I/O
5. **No load/stress tests**: No tests for concurrent WebSocket connections or bulk API operations

### Estimated Line Coverage: ~30-40%

Many core modules (config, cache, websocket_manager, recommendation_engine, performance_collector, all name_enhancement modules) have zero test coverage.

---

## Specific Code Fixes

### Fix 1: Add Authentication Middleware

**File**: `src/main.py`

```python
# ADD: API key middleware for non-health endpoints
from fastapi import Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

@app.middleware("http")
async def check_api_key(request: Request, call_next):
    """Check API key for non-health endpoints."""
    # Skip auth for health, docs, and root
    skip_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/"]
    if any(request.url.path.startswith(p) for p in skip_paths):
        return await call_next(request)

    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != settings.API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Invalid API key"})

    return await call_next(request)
```

### Fix 2: Replace SQL Injection in database_management.py

**File**: `src/api/database_management.py`

```python
# BEFORE (line ~252)
result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))

# AFTER
from sqlalchemy import inspect as sa_inspect

KNOWN_TABLES = frozenset({
    "devices", "device_capabilities", "device_relationships",
    "device_health_metrics", "device_entities", "device_hygiene_issues",
    "discovery_sessions", "cache_stats", "name_suggestions",
    "name_preferences", "zigbee_device_metadata",
    "team_tracker_integrations", "team_tracker_teams"
})

for table in inspector.get_table_names():
    if table not in KNOWN_TABLES:
        logger.warning(f"Skipping unrecognized table: {table}")
        continue
    # Use parameterized query or ORM-level count
    table_obj = sa.Table(table, sa.MetaData(), autoload_with=session.bind)
    result = await session.execute(select(func.count()).select_from(table_obj))
    count = result.scalar()
```

### Fix 3: Fix MQTT Disconnect Handler

**File**: `src/clients/mqtt_client.py`

```python
# BEFORE
def _on_disconnect(self, client, userdata, rc):
    if self._auto_reconnect:
        asyncio.create_task(self._reconnect())

# AFTER
def __init__(self, ...):
    ...
    self._loop: asyncio.AbstractEventLoop | None = None

async def connect(self):
    self._loop = asyncio.get_running_loop()
    ...

def _on_disconnect(self, client, userdata, rc):
    if self._auto_reconnect and self._loop and self._loop.is_running():
        asyncio.run_coroutine_threadsafe(self._reconnect(), self._loop)
```

### Fix 4: Fix Recommendation Priority Sorting

**File**: `src/core/recommendation_engine.py`

```python
# BEFORE
recommendations.sort(key=lambda r: (r.priority.value, r.confidence_score), reverse=True)

# AFTER
_PRIORITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
recommendations.sort(
    key=lambda r: (_PRIORITY_RANK.get(r.priority.value, 0), r.confidence_score),
    reverse=True
)
```

### Fix 5: Fix Predictions Router Dependency

**File**: `src/api/predictions_router.py`

```python
# BEFORE
def get_analytics_engine():
    return PredictiveAnalyticsEngine()

# AFTER
from fastapi import Request

async def get_analytics_engine(request: Request) -> PredictiveAnalyticsEngine:
    engine = getattr(request.app.state, "analytics_engine", None)
    if engine is None:
        # Fallback to new instance if app state not available (e.g., in tests)
        engine = PredictiveAnalyticsEngine()
        await engine.initialize_models()
    return engine
```

### Fix 6: Bound Metrics History

**File**: `src/core/ml_metrics.py`

```python
# BEFORE
self.metrics_history: list[dict] = []

# AFTER
from collections import deque
self.metrics_history: deque = deque(maxlen=10_000)
```

---

## Enhancement Recommendations

### ENH-1: Add Rate Limiting
Add rate limiting middleware using `slowapi` or a custom solution to prevent abuse of prediction and training endpoints.

### ENH-2: Add Request/Response Validation Models
Many endpoints return raw dicts. Define Pydantic response models for type safety and auto-generated API documentation.

### ENH-3: Implement Structured Logging
Replace emoji-based logging with structured JSON logging using `structlog` or Python's built-in `logging` with JSON formatter. This improves log aggregation and parsing.

### ENH-4: Add Graceful Degradation for ML Models
When the ML model is not trained, the service should clearly indicate this in health checks and prediction responses rather than silently falling back to rule-based predictions.

### ENH-5: Implement Circuit Breaker for HA Client
Add circuit breaker pattern (using `tenacity` or custom) for Home Assistant API calls to prevent cascading failures.

### ENH-6: Add Database Migrations
Alembic is in requirements but no migration scripts exist. Database schema changes currently require `recreate-tables` which destroys all data.

### ENH-7: Separate Dev Dependencies from Production
The `requirements.txt` includes `pytest`, `black`, `flake8`, `mypy` etc. These should only be in a dev requirements file. The `requirements-prod.txt` exists but should be the default used in Docker builds.

### ENH-8: Add OpenTelemetry Tracing
For a Tier 3 service with complex discovery -> ML -> prediction pipelines, distributed tracing would significantly improve observability.

---

## Dependency Audit

### Production Dependencies

| Package | Version Spec | Risk | Notes |
|---------|-------------|------|-------|
| fastapi | >=0.123.0,<0.124.0 | LOW | Pinned minor, stable |
| uvicorn[standard] | >=0.32.0,<0.33.0 | LOW | Pinned minor |
| pydantic | >=2.12.4,<3.0.0 | LOW | Wide patch range OK |
| sqlalchemy | >=2.0.44,<3.0.0 | LOW | Wide range, stable 2.x |
| aiosqlite | >=0.21.0,<0.22.0 | LOW | Pinned minor |
| httpx | >=0.28.1,<0.29.0 | LOW | Pinned minor |
| aiohttp | >=3.13.2,<4.0.0 | LOW | Wide range |
| scikit-learn | >=1.5.0,<2.0.0 | LOW | Stable |
| numpy | >=1.26.0,<1.27.0 | LOW | Pinned minor |
| pandas | >=2.2.0,<3.0.0 | LOW | Wide range |
| lightgbm | >=4.0.0,<5.0.0 | LOW | Wide range |
| tabpfn | >=2.2.0,<7.0.0 | MEDIUM | Very wide range (2.x to 6.x), potential breaking changes |
| river | >=0.21.0,<1.0.0 | MEDIUM | Pre-1.0, API may change |
| paho-mqtt | >=1.6.1,<2.0.0 | MEDIUM | paho-mqtt 2.0 has breaking API changes |
| apscheduler | >=3.10.0,<4.0.0 | MEDIUM | APScheduler 4.0 is a complete rewrite |
| openai | (in ai_suggester.py) | HIGH | Not in requirements.txt but imported |
| websockets | >=12.0,<13.0.0 | LOW | Stable |
| psutil | >=7.1.3,<8.0.0 | LOW | Stable |
| PyYAML | >=6.0.1,<7.0.0 | LOW | Stable |
| joblib | ==1.4.2 | LOW | Exact pin, check for updates |

### Issues Found

1. **openai** package is imported in `ai_suggester.py` but not listed in either requirements file
2. **tabpfn** version range is extremely wide (2.x to 6.x), risking breaking changes
3. **Dev dependencies in production requirements**: `pytest`, `black`, `isort`, `flake8`, `mypy` are in `requirements.txt` but should only be in a dev requirements file
4. **joblib** is pinned exactly to 1.4.2 while all other packages use ranges

---

## Action Items (Prioritized Checklist)

### Immediate (Security - Do Now)

- [ ] **CRIT-1**: Fix SQL injection in `database_management.py` - whitelist table names
- [ ] **CRIT-2**: Fix SQL injection in `device_service.py` - use parameterized queries
- [ ] **CRIT-3**: Add authentication to destructive endpoints (recreate-tables, cleanup, optimize)
- [ ] **HIGH-1**: Fix XSS in WebSocket test page HTML (use textContent instead of innerHTML)
- [ ] **HIGH-4**: Add WebSocket connection limits and authentication
- [ ] **HIGH-5**: Add authentication to broadcast test endpoint

### Short-Term (Stability - This Sprint)

- [ ] **HIGH-2**: Fix MQTT disconnect handler to use `run_coroutine_threadsafe`
- [ ] **HIGH-3**: Bound `metrics_history` with `deque(maxlen=N)`
- [ ] **HIGH-6**: Fix predictions router to use `app.state.analytics_engine`
- [ ] **MED-1**: Remove or differentiate duplicate `/devices` route in discovery.py
- [ ] **MED-2**: Implement real health checks that test actual connections
- [ ] **MED-3**: Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)`
- [ ] **MED-4**: Fix division by zero in devices.py
- [ ] **MED-5**: Fix recommendation priority sorting
- [ ] **MED-12**: Remove unreachable code in ha_client.py
- [ ] **MED-13**: Make log level configurable from settings
- [ ] **MED-14**: Stop leaking internal error details in API responses

### Medium-Term (Quality - Next Sprint)

- [ ] **MED-6**: Refactor global singletons to use FastAPI dependency injection
- [ ] **MED-7**: Make training scheduler settings immutable
- [ ] **MED-8**: Remove hardcoded IP addresses from config defaults
- [ ] **MED-9**: Fix asyncio import in cache.py
- [ ] **MED-10**: Migrate from `declarative_base()` to `DeclarativeBase`
- [ ] **MED-11**: Fix boolean comparison in team_tracker_router.py
- [ ] **LOW-8**: Fix conftest.py to provide test client fixture
- [ ] Add `openai` to requirements.txt (or make AI suggester truly optional)
- [ ] Separate dev dependencies from production requirements
- [ ] Add Alembic migration scripts
- [ ] Implement rate limiting on API endpoints

### Long-Term (Enhancement - Backlog)

- [ ] Add structured JSON logging (replace emoji logging)
- [ ] Add OpenTelemetry tracing for discovery pipeline
- [ ] Implement circuit breaker for HA API calls
- [ ] Add comprehensive test coverage (target 70%+)
- [ ] Add security tests (injection, auth bypass)
- [ ] Add load tests for WebSocket connections
- [ ] Run ML training in thread pool executor to avoid blocking event loop
- [ ] Implement database connection pooling tuning
- [ ] Tighten `tabpfn` version constraint
- [ ] Review and update `paho-mqtt` for 2.0 compatibility

---

*Generated by Claude Opus 4.6 Deep Code Review - 2026-02-06*
