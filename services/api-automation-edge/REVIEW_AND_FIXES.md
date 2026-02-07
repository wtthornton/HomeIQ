# API Automation Edge Service - Deep Code Review

**Service**: api-automation-edge (Tier 7)
**Port**: 8025
**Reviewer**: Claude Opus 4.6
**Date**: 2026-02-06
**Files Reviewed**: 40+ source files across 10 modules

---

## Service Overview

The API Automation Edge Service is a FastAPI-based automation engine that transitions Home Assistant automations from YAML-based to typed, versioned automation specs. It provides:

- **Capability Graph**: Discovers and maintains entity/service inventory from Home Assistant
- **Validation Pipeline**: Target resolution, service compatibility, policy gates
- **Execution Engine**: Idempotent executor with retry, circuit breaker, confirmation
- **Task Queue**: Async execution via Huey SQLite backend
- **Rollout Management**: Canary rollouts, rollback, kill switch
- **Security**: Encrypted secrets, webhook HMAC validation

---

## Findings

### CRITICAL Severity

#### C1. CORS Wildcard Allows All Origins
**File**: `src/main.py:37-43`
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
**Issue**: `allow_origins=["*"]` combined with `allow_credentials=True` is a security vulnerability. Per the CORS spec, when credentials are included, the browser will refuse to expose the response if `Access-Control-Allow-Origin` is `*`. However, some middleware implementations work around this by reflecting the `Origin` header, which effectively allows any site to make authenticated cross-origin requests.

**Fix**: Restrict allowed origins to known hosts.
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{settings.service_port}",
        "http://localhost:3000",  # health-dashboard
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

---

#### C2. Default Encryption Password/Salt in SecretsManager
**File**: `src/security/secrets_manager.py:45-46`
```python
password = os.getenv("SECRETS_PASSWORD", "default-password-change-in-production")
salt = os.getenv("SECRETS_SALT", "default-salt").encode()
```
**Issue**: Hardcoded default password and salt. If `SECRETS_ENCRYPTION_KEY` and `SECRETS_PASSWORD` env vars are not set, encryption uses a well-known key. Any attacker who reads the source code can decrypt all stored secrets.

**Fix**: Fail loudly if no encryption key is configured.
```python
password = os.getenv("SECRETS_PASSWORD")
salt = os.getenv("SECRETS_SALT")
if not password or not salt:
    raise ValueError(
        "SECRETS_PASSWORD and SECRETS_SALT environment variables must be set. "
        "Do not use default values in production."
    )
```

---

#### C3. Webhook Secret Key Defaults to Empty String
**File**: `src/security/webhook_validator.py:35`
```python
self.secret_key = secret_key or os.getenv("WEBHOOK_SECRET_KEY", "").encode()
```
**Issue**: If `WEBHOOK_SECRET_KEY` is not set, the HMAC signing key is an empty byte string. This makes all webhook signature validation trivially bypassable since the HMAC of any payload with an empty key is deterministic and publicly computable.

**Fix**: Require the secret key to be set.
```python
self.secret_key = (secret_key or os.getenv("WEBHOOK_SECRET_KEY", "")).encode()
if not self.secret_key:
    logger.warning("WEBHOOK_SECRET_KEY not set - webhook validation will be ineffective")
```

---

#### C4. No Authentication on API Endpoints
**File**: `src/api/execution_router.py`, `src/api/spec_router.py`, `src/api/observability_router.py`
**Issue**: All API endpoints lack authentication/authorization. Any network-reachable client can:
- Execute automations (`POST /api/execute/{spec_id}`)
- Activate the kill switch (`POST /api/observability/kill-switch/pause`)
- Create/modify automation specs (`POST /api/specs`)
- Cancel queued tasks (`POST /api/tasks/{task_id}/cancel`)

**Fix**: Add API key or JWT middleware.
```python
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials

# Then use as dependency:
@router.post("/{spec_id}", dependencies=[Depends(verify_api_key)])
```

---

### HIGH Severity

#### H1. Duplicate Component Initialization Creates Divergent State
**File**: `src/api/execution_router.py:33-43`
```python
# Initialize components
spec_registry = SpecRegistry(settings.database_url)
rest_client = HARestClient()
websocket_client = None  # Will be initialized on startup
capability_graph = CapabilityGraph(rest_client)
validator = Validator(capability_graph, rest_client)
executor = Executor(rest_client, websocket_client)
kill_switch = KillSwitch()
```
**Issue**: The execution router creates its own instances of `SpecRegistry`, `HARestClient`, `CapabilityGraph`, `Validator`, `Executor`, and `KillSwitch` at module import time, completely separate from the instances created in `main.py:startup()`. This means:
- The router's `capability_graph` is never initialized (no `await capability_graph.initialize()`)
- The router's `websocket_client` is always `None`
- Kill switch state in the router is different from the one in `observability_router.py`
- Multiple `SpecRegistry` instances create separate DB sessions

The same issue exists in `src/task_queue/execution_wrapper.py:38-66` which creates yet another set of global components.

**Fix**: Use FastAPI dependency injection or `app.state` to share singleton instances.
```python
# In main.py startup:
app.state.rest_client = rest_client
app.state.capability_graph = capability_graph
# etc.

# In routers, use Depends:
from fastapi import Request

def get_executor(request: Request):
    return request.app.state.executor
```

---

#### H2. Kill Switch State Not Shared Across Instances
**File**: `src/api/observability_router.py:17`, `src/api/execution_router.py:40`, `src/task_queue/execution_wrapper.py:31`
```python
# observability_router.py
kill_switch = KillSwitch()

# execution_router.py
kill_switch = KillSwitch()

# execution_wrapper.py
_kill_switch = KillSwitch()
```
**Issue**: Three separate `KillSwitch()` instances. Pausing via the observability router only affects its local instance. The execution router and task queue wrapper have their own kill switch instances that remain unpaused. The kill switch is effectively non-functional.

**Fix**: Share a single `KillSwitch` instance (see H1 fix above).

---

#### H3. Deprecated `on_event` Lifecycle Handlers
**File**: `src/main.py:80,120`
```python
@app.on_event("startup")
async def startup() -> None:
    ...

@app.on_event("shutdown")
async def shutdown() -> None:
    ...
```
**Issue**: `@app.on_event("startup")` and `@app.on_event("shutdown")` are deprecated in modern FastAPI (since 0.100+). They should be replaced with lifespan context managers.

**Fix**:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    rest_client = HARestClient()
    # ... initialization
    yield
    # Shutdown
    await websocket_client.disconnect()

app = FastAPI(lifespan=lifespan)
```

---

#### H4. Synchronous Event Loop Creation in Huey Workers
**File**: `src/task_queue/execution_wrapper.py:128-136`
```python
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
validation_result = None
try:
    validation_result = loop.run_until_complete(
        validator.validate(spec, perform_preflight=False)
    )
finally:
    loop.close()
```
**Issue**: Creates two new event loops per task execution (one for validation, one for execution). This:
1. Is expensive for every task
2. `asyncio.set_event_loop(loop)` modifies thread-global state, causing race conditions in multi-threaded Huey workers
3. Loses connection pooling benefits since the httpx client's event loop context is lost

**Fix**: Create a single event loop per worker thread, or use `asyncio.run()`.
```python
async def _execute_async(spec_id, trigger_data, home_id, correlation_id):
    # All async operations in one coroutine
    validation_result = await validator.validate(spec, perform_preflight=False)
    execution_result = await executor.execute(...)
    return execution_result

# Single event loop call
result = asyncio.run(_execute_async(spec_id, trigger_data, home_id, correlation_id))
```

---

#### H5. Idempotency Store is In-Memory Only
**File**: `src/execution/action_executor.py:50`
```python
self.idempotency_store: Dict[str, Dict[str, float]] = {}
```
**Issue**: The idempotency store is an in-memory dictionary. On service restart, all idempotency keys are lost, allowing duplicate executions. In the task queue scenario (H1), there are multiple ActionExecutor instances each with their own empty store.

**Fix**: Use the SQLite database or a shared store for idempotency keys.

---

#### H6. Explainer Store Grows Unboundedly
**File**: `src/observability/explainer.py:26`
```python
self.explanations: Dict[str, Dict[str, Any]] = {}
```
**Issue**: The `explanations` dictionary grows without bound. Every execution adds an entry keyed by `correlation_id`, but entries are never removed. Over time this will consume increasing memory, eventually causing OOM.

**Fix**: Add TTL-based eviction or cap the size.
```python
from collections import OrderedDict

class Explainer:
    MAX_EXPLANATIONS = 1000

    def __init__(self):
        self.explanations: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def record_decision_factors(self, correlation_id, ...):
        if len(self.explanations) >= self.MAX_EXPLANATIONS:
            self.explanations.popitem(last=False)  # Remove oldest
        self.explanations[correlation_id] = {...}
```

---

#### H7. `reconnect_latencies` List Grows Unboundedly
**File**: `src/clients/ha_websocket_client.py:79`
```python
self.reconnect_latencies: list[float] = []
```
**Issue**: Every reconnection appends to this list. The `get_metrics()` method only returns the last 10, but the list itself is never trimmed. Long-running instances will accumulate a large list.

**Fix**: Cap the list size.
```python
MAX_LATENCY_HISTORY = 100

def reconnect(self):
    ...
    self.reconnect_latencies.append(latency)
    if len(self.reconnect_latencies) > self.MAX_LATENCY_HISTORY:
        self.reconnect_latencies = self.reconnect_latencies[-self.MAX_LATENCY_HISTORY:]
```

---

### MEDIUM Severity

#### M1. Config Uses Both Pydantic BaseSettings and os.getenv
**File**: `src/config.py:14-70`
```python
class Settings(BaseSettings):
    service_port: int = int(os.getenv("SERVICE_PORT", "8025"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    ha_url: Optional[str] = os.getenv("HA_URL") or os.getenv("HOME_ASSISTANT_URL")
```
**Issue**: The class extends `pydantic_settings.BaseSettings` which already reads from environment variables automatically, but all fields manually call `os.getenv()`. This defeats the purpose of BaseSettings and can cause confusing precedence issues (the `os.getenv` defaults run at import time, before `.env` files are loaded).

**Fix**: Use standard pydantic_settings patterns.
```python
class Settings(BaseSettings):
    service_port: int = 8025
    log_level: str = "INFO"
    ha_url: Optional[str] = None
    ha_token: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )
```

---

#### M2. SpecVersion Model Defined Twice
**File**: `src/registry/database.py:12-24` and `src/registry/spec_registry.py:24-50`
```python
# database.py
class SpecVersion(Base):
    __tablename__ = "spec_versions"
    ...

# spec_registry.py
class SpecVersion(Base):
    __tablename__ = "spec_versions"
    ...
```
**Issue**: The `SpecVersion` model is defined in both `database.py` and `spec_registry.py` with the same `__tablename__`. The `database.py` version imports `Base` from `spec_registry.py`, creating a circular dependency. The `database.py` version also lacks the `to_dict()` method.

**Fix**: Remove `database.py` or consolidate the model definition into a single file.

---

#### M3. Confirmation Watcher Never Unsubscribes
**File**: `src/execution/confirmation_watcher.py:119-121`
```python
finally:
    # Clean up subscription (would need to unsubscribe - simplified for now)
    pass
```
**Issue**: Each call to `wait_for_confirmation()` creates a new WebSocket subscription but never unsubscribes. Over time, this accumulates subscriptions, each consuming memory and CPU to process events.

**Fix**: Implement unsubscribe logic.

---

#### M4. Confirmation Watcher Only Monitors First Entity
**File**: `src/execution/confirmation_watcher.py:152`
```python
# Watch first entity (could watch all)
entity_id = entity_ids[0]
```
**Issue**: For high-risk actions targeting multiple entities, only the first entity is monitored for confirmation. If the first entity confirms but others fail, the action is still considered confirmed.

**Fix**: Monitor all entities or at least document this as a known limitation.

---

#### M5. `_redact_secrets` May False-Positive on Valid Data
**File**: `src/clients/ha_rest_client.py:103-105`
```python
if len(data) > 20 and all(c.isalnum() or c in '-_' for c in data):
    return "[REDACTED]"
```
**Issue**: Any string longer than 20 characters containing only alphanumeric, dash, or underscore characters gets redacted. This would redact entity IDs like `sensor.energy_production_total_daily` or friendly names like `Living-Room-Temperature-Sensor`.

**Fix**: Only redact strings that match token-like patterns more specifically.
```python
# Only redact if it looks like a hex token or base64 token
import re
TOKEN_PATTERN = re.compile(r'^[a-f0-9]{32,}$|^ey[A-Za-z0-9_-]{20,}$')
if TOKEN_PATTERN.match(data):
    return "[REDACTED]"
```

---

#### M6. `health_router.py` Iterates Huey Generators Destructively
**File**: `src/api/health_router.py:47-48`
```python
pending_count = len(list(pending_tasks))
scheduled_count = len(list(scheduled_tasks))
```
**Issue**: `huey.pending()` and `huey.scheduled()` may return generators. Calling `list()` on them consumes the generator entirely into memory. For large queues this could be expensive. The same pattern appears in `task_router.py:135-141` and `task_router.py:274-278`.

**Fix**: Use a counter or limit the iteration.

---

#### M7. No Input Validation on `spec_id` and `home_id` Path Parameters
**File**: `src/api/execution_router.py:47-48`, `src/api/spec_router.py:24,44`
```python
async def execute_spec(spec_id: str, ...):
async def create_spec(spec: dict, home_id: str = settings.home_id):
```
**Issue**: The `spec_id` and `home_id` parameters are raw strings with no validation. Malicious values could potentially be used for SQL injection (SQLAlchemy parameterizes queries so this is mitigated), or for path traversal if these values are ever used in file paths.

**Fix**: Add regex validation via Pydantic models or Path constraints.
```python
from fastapi import Path as PathParam

@router.post("/{spec_id}")
async def execute_spec(
    spec_id: str = PathParam(..., regex=r"^[a-zA-Z0-9_-]+$"),
    ...
):
```

---

#### M8. `execute_spec` Does Not Validate `trigger_data` Schema
**File**: `src/api/execution_router.py:48`
```python
trigger_data: Optional[dict] = None,
```
**Issue**: The `trigger_data` parameter accepts any dictionary with no validation. Arbitrary data flows through to the execution engine and is stored in the explainer.

**Fix**: Define a Pydantic model for trigger data.

---

#### M9. Error Budget Window Not Properly Tracked
**File**: `src/rollout/rollback_manager.py:96,126`
```python
budget["error_count"] += 1
# ...
# Reset window if needed (simplified - would need proper time tracking)
# For now, just check count
if budget["error_count"] >= budget["max_errors"]:
```
**Issue**: The error budget has `window_start` and `window_seconds` fields but never uses them. The error count accumulates forever and will eventually trigger a rollback regardless of the time window.

**Fix**: Implement sliding window error counting.

---

#### M10. `datetime.utcnow()` Deprecated
**File**: `src/registry/spec_registry.py:34,148,283`
```python
created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
# ...
deployed_at=datetime.utcnow() if deploy else None,
```
**Issue**: `datetime.utcnow()` is deprecated in Python 3.12+. It returns a naive datetime without timezone info.

**Fix**: Use `datetime.now(timezone.utc)`.
```python
from datetime import datetime, timezone
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
```

---

#### M11. Circuit Breaker Not Integrated with Executor
**File**: `src/execution/retry_manager.py` and `src/execution/executor.py`
**Issue**: `CircuitBreaker` is defined and exported but never instantiated or used in the `Executor` or `ActionExecutor`. The circuit breaker pattern exists in code but provides no protection.

**Fix**: Integrate the circuit breaker into the `ActionExecutor`.

---

#### M12. Test Import Paths Are Wrong for Queue Tests
**File**: `tests/queue/test_huey_config.py:26`
```python
from src.queue.huey_config import get_huey_instance
```
**Issue**: The import path is `src.queue.huey_config` but the actual module is at `src.task_queue.huey_config`. All three queue test files have the wrong import path, meaning these tests always skip due to ImportError.

**Fix**: Update imports to `src.task_queue.huey_config`, `src.task_queue.scheduler`, `src.task_queue.tasks`.

---

### LOW Severity

#### L1. Rollback Scripts Committed to Repository
**File**: `rollback_influxdb_20260205_143941.sh`, `rollback_tenacity_20260205_143941.sh`
**Issue**: Migration rollback scripts with hardcoded Windows paths (`C:\cursor\HomeIQ\...`) are committed to the repository. These are developer-specific artifacts that should be gitignored.

**Fix**: Add `rollback_*.sh` to `.gitignore` or delete these files.

---

#### L2. Dockerfile CMD Does Not Use Uvicorn Properly
**File**: `Dockerfile:61`
```dockerfile
CMD ["python", "-m", "src.main"]
```
**Issue**: This runs `src/main.py` as `__main__`, which calls `uvicorn.run()` without `--workers` or `--reload` flags. The `if __name__ == "__main__"` block in `main.py` runs uvicorn inline, which doesn't support graceful shutdown signals properly in Docker.

**Fix**: Use uvicorn as the entrypoint directly.
```dockerfile
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8025"]
```

---

#### L3. Unused `re` Import in `ha_rest_client.py`
**File**: `src/clients/ha_rest_client.py:8`
```python
import re
```
**Issue**: The `re` module is imported and used only in `_redact_url()`. However, the `_redact_secrets` function could benefit from using `re` instead of string matching. Minor import that's technically used, but the `_redact_url` pattern is simplistic.

---

#### L4. `Callable` and `Set` Types Not Imported from `typing` Consistently
**File**: Various files use `set()` for type hints but import `Set` from typing, or use `list[...]` syntax while also importing `List`.
**Issue**: Mixed use of Python 3.9+ built-in generics (`list[...]`, `set[...]`, `tuple[...]`) and `typing` module imports (`List`, `Set`, `Dict`). While functional, it's inconsistent.

**Fix**: Pick one style consistently (prefer built-in generics for Python 3.12).

---

#### L5. `schedule_router.py` Creates Duplicate `SpecRegistry`
**File**: `src/api/schedule_router.py:28`
```python
spec_registry = SpecRegistry(settings.database_url)
```
**Issue**: Another independent `SpecRegistry` instance (same issue as H1 but lower impact since it's read-only).

---

#### L6. Health Endpoint Path is `/health` Not `/health/`
**File**: `src/api/health_router.py:14,27`
```python
router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
async def health_check():
```
**Issue**: The health check is at `/health` (no trailing slash), but the Dockerfile HEALTHCHECK uses `http://localhost:8025/health` which matches. Minor but the empty string path in `@router.get("")` is slightly unusual.

---

#### L7. `ruff_cache` Directories Committed
**File**: Multiple `.ruff_cache/` directories under `src/`
**Issue**: Ruff linter cache directories are committed to the repository. These are build artifacts.

**Fix**: Add `.ruff_cache/` to `.gitignore`.

---

#### L8. `_create_log_entry` Creates Unnecessary LogRecord
**File**: `src/observability/logger.py:70-75`
```python
entry = {
    "timestamp": logging.Formatter().formatTime(
        logging.LogRecord("", 0, "", 0, message, (), None),
        datefmt="%Y-%m-%d %H:%M:%S"
    ),
```
**Issue**: Creates a dummy `LogRecord` and `Formatter` just to get a formatted timestamp. This is unnecessarily complex.

**Fix**: Use `datetime.now().strftime("%Y-%m-%d %H:%M:%S")`.

---

#### L9. `StructuredLogger` Correlation ID Not Thread-Safe
**File**: `src/observability/logger.py:33-38`
```python
def set_correlation_id(self, correlation_id: Optional[str] = None):
    self._correlation_id = correlation_id or str(uuid.uuid4())
    return self._correlation_id
```
**Issue**: The correlation ID is stored as an instance variable. When used in concurrent task queue workers (Huey threads), different tasks can overwrite each other's correlation IDs.

**Fix**: Use `contextvars.ContextVar` for thread-safe context.
```python
import contextvars
_correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'correlation_id', default=None
)
```

---

## Test Coverage Gaps

| Module | Has Tests | Coverage Assessment |
|--------|-----------|-------------------|
| `validation/target_resolver.py` | Yes | Good - 12 test cases |
| `validation/policy_validator.py` | Yes | Good - 13 test cases |
| `task_queue/` | Partial | Wrong import paths, all tests skip |
| `clients/` | No | No unit tests |
| `execution/` | No | No unit tests |
| `capability/` | No | No unit tests |
| `registry/` | No | No unit tests (fixture only) |
| `rollout/` | No | No unit tests |
| `security/` | No | No unit tests |
| `observability/` | No | No unit tests |
| `api/` (routers) | No | No integration tests |

**Critical gap**: The execution engine, capability graph, and security modules have zero test coverage.

---

## Enhancement Suggestions

### E1. Add Request Rate Limiting
The API has no rate limiting. A misbehaving client could flood the service with execution requests.

### E2. Add Prometheus Metrics Endpoint
The service collects metrics to InfluxDB but has no `/metrics` endpoint for Prometheus scraping, which is the standard for container orchestration.

### E3. Implement Proper Dependency Injection
Replace module-level global instances with FastAPI's dependency injection system. This would solve H1, H2, L5, and make the code more testable.

### E4. Add Database Migrations
The service uses `Base.metadata.create_all()` for schema creation. For production, Alembic migrations should be used (already in requirements.txt but not configured).

### E5. Add Structured Error Responses
Error responses are inconsistent - some return `{"errors": [...]}`, some return `{"detail": "..."}`, some return `{"error": "..."}`.

### E6. Implement Graceful Shutdown for Task Queue
The Huey consumer thread is started as a daemon thread. On shutdown, in-flight tasks may be interrupted without completing.

---

## Prioritized Action Plan

### Priority 1 - Security (Do Immediately)
1. **C4**: Add API authentication middleware
2. **C1**: Restrict CORS origins
3. **C2**: Remove default encryption password/salt
4. **C3**: Require webhook secret key

### Priority 2 - Correctness (Do This Sprint)
5. **H1/H2**: Fix duplicate component initialization (use DI)
6. **H4**: Fix event loop creation in Huey workers
7. **M12**: Fix broken test import paths
8. **M11**: Integrate circuit breaker with executor
9. **H5**: Persist idempotency store

### Priority 3 - Reliability (Next Sprint)
10. **H6**: Add TTL eviction to explainer store
11. **H7**: Cap reconnect latency list
12. **M3**: Implement subscription cleanup in confirmation watcher
13. **M9**: Implement sliding window error budget
14. **H3**: Migrate to lifespan context manager

### Priority 4 - Quality (Ongoing)
15. **M1**: Fix config to use pydantic_settings properly
16. **M2**: Remove duplicate SpecVersion model
17. **M10**: Replace deprecated `datetime.utcnow()`
18. **L2**: Fix Dockerfile CMD
19. **L1/L7**: Clean up committed artifacts
20. Add unit tests for untested modules (execution, capability, security, registry, rollout)
