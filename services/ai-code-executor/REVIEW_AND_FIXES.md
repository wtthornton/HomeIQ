# AI Code Executor Service - Deep Code Review

**Review Date:** 2026-02-06
**Reviewer:** Automated Deep Review (Tier 7 Service Audit)
**Service:** `services/ai-code-executor/`
**Port:** 8030
**Purpose:** Secure Python code execution sandbox for MCP (Model Context Protocol) workflows

---

## Service Overview

The ai-code-executor service provides a sandboxed Python execution environment for trusted HomeIQ tooling. It uses RestrictedPython for AST-level code restriction, Linux resource limits (RLIMIT) for process containment, subprocess isolation via `multiprocessing.spawn`, and a static code validator for pre-execution safety checks.

**Architecture:**
```
Client (X-Executor-Token auth)
    -> POST /execute
FastAPI controller (code validation)
    -> AST + size checks
MCPSandbox (semaphore guard)
    -> subprocess fork (spawn)
PythonSandbox worker
    -> RestrictedPython + import whitelist + resource limits
Result serialized back to client
```

**Files Reviewed:**
- `src/main.py` (237 lines) - FastAPI application and endpoints
- `src/config.py` (120 lines) - Pydantic settings
- `src/executor/sandbox.py` (393 lines) - Core sandbox execution engine
- `src/executor/mcp_sandbox.py` (64 lines) - MCP wrapper around sandbox
- `src/mcp/homeiq_tools.py` (32 lines) - MCP tool registry (disabled)
- `src/security/code_validator.py` (108 lines) - Static code analysis
- `src/middleware.py` (87 lines) - Logging and metrics middleware
- `Dockerfile` (56 lines) - Multi-stage Alpine build
- `requirements.txt` (12 lines) - Python dependencies
- `tests/test_api.py` (300 lines) - API integration tests
- `tests/test_code_validator.py` (241 lines) - Validator unit tests
- `tests/test_config.py` (197 lines) - Config unit tests
- `tests/test_mcp_sandbox.py` (234 lines) - MCP sandbox tests
- `tests/test_sandbox_security.py` (208 lines) - Security tests
- `tests/test_middleware.py` (137 lines) - Middleware tests
- `src/executor/sandbox.backup_20251229_102558.py` (391 lines) - Stale backup file

---

## Findings Summary

| Severity | Count | Category |
|----------|-------|----------|
| **Critical** | 3 | Security sandbox bypasses, token comparison vulnerability |
| **High** | 5 | Sandbox escape vectors, missing security controls |
| **Medium** | 8 | Code quality, configuration, error handling |
| **Low** | 6 | Dead code, naming, minor improvements |

---

## Critical Findings

### C1. Timing-Safe Token Comparison Missing

**File:** `src/main.py:118`
**Severity:** CRITICAL
**Category:** Security - Authentication

The API token comparison uses a simple `!=` operator, which is vulnerable to timing side-channel attacks. An attacker can measure response times to progressively brute-force the token byte-by-byte.

```python
# CURRENT (vulnerable) - src/main.py:118
if not x_executor_token or x_executor_token != settings.api_token:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing executor token",
    )
```

**Fix:** Use `hmac.compare_digest()` for constant-time comparison:
```python
import hmac

def verify_api_token(x_executor_token: str | None = Header(default=None, alias="X-Executor-Token")):
    if not settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API token not configured",
        )
    if not x_executor_token or not hmac.compare_digest(x_executor_token, settings.api_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing executor token",
        )
```

---

### C2. RestrictedPython `compile_restricted` Return Value Not Properly Guarded

**File:** `src/executor/sandbox.py:159-161`
**Severity:** CRITICAL
**Category:** Security - Sandbox Integrity

The code checks `byte_code.errors` but `compile_restricted` in RestrictedPython 8.x returns a `CompileResult` object whose `.code` attribute can be `None` when compilation fails, even if `.errors` is an empty list in some edge cases. The subsequent `exec(byte_code.code, safe_env)` would raise a `TypeError` rather than being caught cleanly.

More importantly, RestrictedPython's `compile_restricted` in exec mode does NOT restrict all dangerous patterns. It primarily prevents attribute access patterns but does NOT prevent all code generation tricks (e.g., string concatenation to build forbidden names, `getattr` on whitelisted objects to reach forbidden attributes).

```python
# CURRENT - src/executor/sandbox.py:159-167
byte_code = compile_restricted(code, filename="<sandbox>", mode="exec")
if byte_code.errors:
    _write_result(False, None, f"Compilation errors: {byte_code.errors}")
    return

safe_env = _build_execution_env(context, set(config["allowed_imports"]))

with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
    exec(byte_code.code, safe_env)
```

**Fix:** Add a guard for `byte_code.code is None` and also check warnings:
```python
byte_code = compile_restricted(code, filename="<sandbox>", mode="exec")
if byte_code.errors:
    _write_result(False, None, f"Compilation errors: {byte_code.errors}")
    return
if byte_code.code is None:
    _write_result(False, None, "Compilation produced no executable code")
    return
```

---

### C3. `getattr` Available in Sandbox Enables Attribute Access Bypass

**File:** `src/executor/sandbox.py:62-93` and `src/security/code_validator.py:10-34`
**Severity:** CRITICAL
**Category:** Security - Sandbox Escape

Although `FORBIDDEN_NAMES` blocks direct use of names like `__class__`, `__subclasses__`, etc., and the custom builtins do not expose `getattr`/`type`/`isinstance`, the RestrictedPython compilation itself generates `_getattr_` and `_getitem_` guard functions. When these are absent from the execution environment, RestrictedPython will raise `NameError` for guarded attribute accesses, but some code patterns may bypass this.

Specifically, if `_getattr_` is not explicitly defined in the execution environment, RestrictedPython will block guarded attribute access. However, `_getiter_`, `_getitem_`, and `_write_` guards are also needed. Without explicit definitions, some patterns may produce confusing errors rather than clean security blocks.

**The builtins include `Exception` and `ValueError` as class objects.** These can be used to traverse the MRO:
```python
# Potential bypass: using allowed Exception classes to reach object.__subclasses__
# RestrictedPython guards attribute access, but the depth of defense depends
# on whether _getattr_ is properly configured
```

**Fix:** Explicitly define RestrictedPython guard functions in the execution environment:
```python
def _build_execution_env(context: dict[str, Any], allowed_imports: set[str]) -> dict[str, Any]:
    env: dict[str, Any] = {
        "__builtins__": _build_safe_builtins(allowed_imports),
        "__name__": "__sandbox__",
        "__package__": None,
        # RestrictedPython guard functions
        "_getattr_": _guarded_getattr,
        "_getitem_": _guarded_getitem,
        "_getiter_": iter,  # Allow iteration
        "_write_": lambda obj: obj,  # Allow writes to safe containers
        "_inplacevar_": _guarded_inplacevar,
    }
    env.update(context)
    return env

def _guarded_getattr(obj, name):
    """Block access to dunder and private attributes."""
    if name.startswith('_'):
        raise AttributeError(f"Access to '{name}' is blocked in sandbox")
    return getattr(obj, name)

def _guarded_getitem(obj, key):
    """Allow standard container access."""
    return obj[key]

def _guarded_inplacevar(op, x, y):
    """Handle in-place operations safely."""
    return op(x, y)
```

---

## High Findings

### H1. `time` Module Allowed via Import Whitelist Enables Timeout Evasion

**File:** `src/executor/sandbox.py:199-208`
**Severity:** HIGH
**Category:** Security - Resource Limits

The default allowed imports include `functools` and `itertools`, but the tests at `tests/test_mcp_sandbox.py:136-139` and `tests/test_sandbox_security.py:134-138` show `time` being imported inside sandbox code. While `time` is not in the default whitelist (`json`, `datetime`, `math`, `re`, `typing`, `collections`, `itertools`, `functools`), the `datetime` module is allowed and can be used for CPU-burning loops. More critically, `itertools` allows `itertools.count()` which creates infinite iterators.

The RLIMIT_CPU should catch infinite CPU loops, but `RLIMIT_FSIZE` set to 0 means any attempt to write even a single byte to a file will kill the process with SIGXFSZ - which is correct behavior but could cause confusing error messages.

**Fix:** Consider adding documentation about which allowed modules can be used for resource abuse, and ensure RLIMIT_CPU is always set low enough to prevent CPU hogging.

---

### H2. User Context Overrides MCP Tool Context Without Warning

**File:** `src/executor/mcp_sandbox.py:57-61`
**Severity:** HIGH
**Category:** Security - Context Injection

User-provided context is merged after MCP tool context using `dict.update()`, meaning a user can override any MCP-injected context key:

```python
# CURRENT - src/executor/mcp_sandbox.py:57-61
merged_context: dict[str, Any] = {}
if self._tool_context:
    merged_context.update(self._tool_context)
if context:
    merged_context.update(context)  # User context overwrites MCP context!
```

While MCP network tools are currently disabled (so `_tool_context` is empty), when they are enabled in the future, user context would be able to override tool functions with malicious values.

**Fix:** Reverse the merge order or raise on conflict:
```python
merged_context: dict[str, Any] = {}
if context:
    merged_context.update(context)
if self._tool_context:
    # MCP tool context takes precedence - cannot be overridden by user
    for key in self._tool_context:
        if key in merged_context:
            logger.warning("User context key '%s' shadowed by MCP tool", key)
    merged_context.update(self._tool_context)
```

---

### H3. Subprocess Stdout/Stderr Capture Unbounded

**File:** `src/executor/sandbox.py:134-135`
**Severity:** HIGH
**Category:** Security - Resource Exhaustion

The `StringIO` buffers used for stdout/stderr capture have no size limit. A sandboxed program that prints millions of characters will consume unbounded memory in the subprocess before RLIMIT_AS kills it, but the captured content is serialized to the result queue and then returned to the parent process, potentially causing memory exhaustion in the parent.

```python
# CURRENT - src/executor/sandbox.py:134-135
stdout_capture = io.StringIO()
stderr_capture = io.StringIO()
```

**Fix:** Use a bounded wrapper or truncate before serialization:
```python
MAX_OUTPUT_BYTES = 64 * 1024  # 64KB max per stream

class BoundedStringIO(io.StringIO):
    def __init__(self, max_bytes=MAX_OUTPUT_BYTES):
        super().__init__()
        self._max_bytes = max_bytes
        self._bytes_written = 0

    def write(self, s):
        if self._bytes_written >= self._max_bytes:
            return 0
        remaining = self._max_bytes - self._bytes_written
        truncated = s[:remaining]
        self._bytes_written += len(truncated.encode('utf-8'))
        return super().write(truncated)
```

---

### H4. `return_value` Serialization Not Validated

**File:** `src/executor/sandbox.py:167`
**Severity:** HIGH
**Category:** Security - Data Exfiltration

The return value (`safe_env.get("_", None)`) is placed directly into the result queue without validating its type or size. If sandboxed code assigns a large or complex object to `_`, it will be pickled for the queue and then potentially serialized to JSON in the response. This could cause:
1. Memory exhaustion via large return values
2. Pickle deserialization issues
3. Exposure of internal objects if a module object is assigned to `_`

```python
# CURRENT - src/executor/sandbox.py:167
_write_result(True, safe_env.get("_", None), None)
```

**Fix:** Validate and bound the return value:
```python
MAX_RETURN_VALUE_SIZE = 64 * 1024  # 64KB

def _sanitize_return_value(value):
    """Ensure return value is JSON-serializable and bounded."""
    try:
        serialized = json.dumps(value, default=str)
        if len(serialized) > MAX_RETURN_VALUE_SIZE:
            return f"[Return value truncated: {len(serialized)} bytes exceeds {MAX_RETURN_VALUE_SIZE} limit]"
        return value
    except (TypeError, ValueError):
        return str(value)[:MAX_RETURN_VALUE_SIZE]
```

---

### H5. Error Messages Leak Internal Details to API Clients

**File:** `src/main.py:227`
**Severity:** HIGH
**Category:** Security - Information Disclosure

The `/execute` endpoint's catch-all exception handler exposes raw exception messages to the client:

```python
# CURRENT - src/main.py:225-227
except Exception as e:
    logger.error(f"Execution failed: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(e)) from e
```

This can leak internal paths, library versions, and stack trace information that aids attackers.

**Fix:** Return a generic error message to the client while logging the full detail:
```python
except Exception as e:
    logger.error(f"Execution failed: {e}", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail="Internal execution error. Check service logs for details.",
    ) from e
```

---

## Medium Findings

### M1. Stale Backup File in Repository

**File:** `src/executor/sandbox.backup_20251229_102558.py`
**Severity:** MEDIUM
**Category:** Code Quality - Dead Code

A full backup copy of `sandbox.py` exists in the repository. The file is identical to the current `sandbox.py`. This adds confusion, increases the attack surface review burden, and could be shipped in Docker images if the `.dockerignore` is misconfigured.

**Fix:** Delete the backup file. Use `git` for version history instead:
```bash
rm services/ai-code-executor/src/executor/sandbox.backup_20251229_102558.py
```

---

### M2. Metrics Module Not Thread-Safe

**File:** `src/middleware.py:15-22, 73-81`
**Severity:** MEDIUM
**Category:** Code Quality - Concurrency

The global `_metrics` dictionary is mutated from async request handlers without any locking. While Python's GIL prevents data corruption for simple operations, uvicorn can run with multiple workers, and `+=` on floats is not atomic.

```python
# CURRENT - src/middleware.py:73-81
def record_execution(success: bool, execution_time: float, memory_used_mb: float) -> None:
    _metrics["total_executions"] += 1  # Not atomic
    if success:
        _metrics["successful_executions"] += 1
    else:
        _metrics["failed_executions"] += 1
    _metrics["total_execution_time"] += execution_time
    _metrics["total_memory_used"] += memory_used_mb
```

**Fix:** Use `threading.Lock` or `asyncio.Lock`, or switch to `prometheus_client` Counters (already a dependency):
```python
from prometheus_client import Counter, Histogram

EXECUTION_COUNT = Counter('executor_executions_total', 'Total executions', ['status'])
EXECUTION_TIME = Histogram('executor_execution_seconds', 'Execution time')
MEMORY_USED = Histogram('executor_memory_mb', 'Memory used per execution')
```

---

### M3. Health Endpoint Always Returns "healthy" Even When Sandbox Fails

**File:** `src/main.py:145-159`
**Severity:** MEDIUM
**Category:** API Design - Health Check

The health check always returns `"status": "healthy"` regardless of sandbox initialization state. If the sandbox fails to initialize (e.g., missing dependencies), the health endpoint will still report healthy, misleading orchestrators and load balancers.

```python
# CURRENT - src/main.py:145-159
@app.get("/health")
async def health_check():
    record_request()
    mcp_initialized = False
    if sandbox is not None:
        mcp_initialized = sandbox.is_initialized()

    return {
        "status": "healthy",  # Always "healthy"
        "service": settings.service_name,
        "version": "1.0.0",
        "mcp_initialized": mcp_initialized
    }
```

**Fix:** Return degraded status when sandbox is not initialized:
```python
@app.get("/health")
async def health_check():
    record_request()
    mcp_initialized = sandbox.is_initialized() if sandbox else False
    is_healthy = sandbox is not None and mcp_initialized

    return {
        "status": "healthy" if is_healthy else "degraded",
        "service": settings.service_name,
        "version": "1.0.0",
        "mcp_initialized": mcp_initialized,
    }
```

---

### M4. Missing `__init__.py` for Security Module

**File:** `src/security/` (directory)
**Severity:** MEDIUM
**Category:** Code Quality - Module Structure

The `src/security/` directory has no `__init__.py` file. While Python 3 supports namespace packages, an explicit `__init__.py` is the project convention (other subpackages have one) and ensures consistent import behavior.

**Fix:** Create `src/security/__init__.py`:
```python
"""Security module - Code validation and sandboxing controls."""
from .code_validator import CodeValidator, CodeValidatorConfig, CodeValidationError

__all__ = ['CodeValidator', 'CodeValidatorConfig', 'CodeValidationError']
```

---

### M5. Configuration Uses `class Config` Instead of `model_config` (Pydantic V2)

**File:** `src/config.py:115-117`
**Severity:** MEDIUM
**Category:** Code Quality - Deprecated Pattern

The Settings class uses the Pydantic V1 `class Config` inner class. With Pydantic V2 (which is the installed version per `pydantic>=2.9.0`), the recommended pattern is `model_config`:

```python
# CURRENT - src/config.py:115-117
class Config:
    env_file = ".env"
    case_sensitive = False
```

**Fix:** Use `model_config`:
```python
model_config = {"env_file": ".env", "case_sensitive": False}
```

---

### M6. CORS Configuration Allows `allow_methods` Beyond What's Needed

**File:** `src/main.py:101-107`
**Severity:** MEDIUM
**Category:** Security - CORS

The CORS configuration allows `OPTIONS` explicitly (it's handled automatically by the middleware) and allows `GET` for the execute endpoint which only uses `POST`. While the FastAPI route decorator limits actual handling, the CORS preflight will advertise these methods.

```python
# CURRENT - src/main.py:101-107
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS", "GET"],
    allow_headers=["Authorization", "Content-Type", "X-Executor-Token"],
)
```

This is low risk given the origin allowlist, but follows least-privilege principle.

---

### M7. `allowed_imports` Allowlist in Validator Uses Sandbox Config, but Validator and Sandbox Could Drift

**File:** `src/main.py:68-73`
**Severity:** MEDIUM
**Category:** Code Quality - Configuration Coupling

The code validator receives `allowed_imports` from `sandbox_config.allowed_imports`. If someone creates a `CodeValidator` with a different set of allowed imports than the sandbox's `_safe_import`, validated code could still fail at runtime, or worse, the validator could be more permissive than the sandbox.

```python
# CURRENT - src/main.py:68-73
code_validator = CodeValidator(
    CodeValidatorConfig(
        max_bytes=settings.max_code_bytes,
        max_ast_nodes=settings.max_ast_nodes,
        allowed_imports=sandbox_config.allowed_imports,  # Must match sandbox
    )
)
```

This is currently correct but fragile. If the sandbox config or validator config is constructed independently, they could diverge.

**Fix:** Consider making `allowed_imports` a single source of truth, perhaps on the `Settings` object itself.

---

### M8. No Rate Limiting on `/execute` Endpoint

**File:** `src/main.py:169-227`
**Severity:** MEDIUM
**Category:** Security - Denial of Service

While the semaphore in `MCPSandbox` limits concurrent executions to 2, there is no rate limiting on the API endpoint itself. An attacker with a valid token could queue thousands of requests, overwhelming the FastAPI event loop and causing memory exhaustion from queued coroutines.

**Fix:** Add a rate limiter (e.g., `slowapi` or a simple in-memory token bucket):
```python
# Simple approach: reject if too many pending executions
@app.post("/execute", ...)
async def execute_code(request: ExecuteRequest):
    if sandbox._execution_guard.locked():
        raise HTTPException(status_code=429, detail="Too many concurrent executions")
    # ... existing code
```

---

## Low Findings

### L1. F-String Used in Logger Calls (Performance)

**Files:** `src/main.py:43-48,80,195,209,213,226`, `src/executor/sandbox.py:357,361,363,376,383,389`
**Severity:** LOW
**Category:** Code Quality - Performance

Multiple logger calls use f-strings instead of `%s` formatting. With f-strings, the string interpolation happens even when the log level is disabled, wasting CPU cycles.

```python
# CURRENT - src/main.py:43
logger.info(f"Service: {settings.service_name}")

# BETTER
logger.info("Service: %s", settings.service_name)
```

---

### L2. Middleware `request.client` Could Be `None`

**File:** `src/middleware.py:35`
**Severity:** LOW
**Category:** Error Handling - Edge Case

The middleware logs `request.client.host` with a ternary fallback, but this is correct. No issue here, though it's worth noting that in test environments `request.client` is often `None`.

---

### L3. Test Fixture Reuses Module-Level Globals Unsafely

**File:** `tests/test_api.py:44-71`
**Severity:** LOW
**Category:** Testing - Test Isolation

The test fixture modifies module-level globals (`src.main.sandbox` and `src.main.code_validator`) which can cause test pollution between test runs.

```python
# CURRENT - tests/test_api.py:69-71
import src.main as main_module
main_module.sandbox = sandbox
main_module.code_validator = code_validator
```

**Fix:** Use a proper dependency injection pattern or reset globals in fixture teardown.

---

### L4. Test Metrics State Bleeds Between Tests

**File:** `tests/test_middleware.py:23-86`
**Severity:** LOW
**Category:** Testing - Test Isolation

The `_metrics` dictionary in `src/middleware.py` is a module-level mutable global. Tests that call `record_request()` or `record_execution()` modify it permanently, causing later tests to see accumulated state. For example, `test_get_metrics_initial_state` will fail if run after other tests that modify metrics.

**Fix:** Add a `reset_metrics()` function and call it in a fixture:
```python
def reset_metrics():
    for key in _metrics:
        _metrics[key] = 0 if isinstance(_metrics[key], int) else 0.0
```

---

### L5. Dockerfile `HEALTHCHECK` Uses Python Import Instead of curl

**File:** `Dockerfile:52-53`
**Severity:** LOW
**Category:** Docker - Best Practice

The healthcheck runs a Python process importing httpx, which is heavier than using the `curl` that's already installed:

```dockerfile
# CURRENT
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8030/health', timeout=5.0)"
```

**Fix:** Use curl instead (already installed in the image):
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8030/health || exit 1
```

---

### L6. README Documents Incorrect Default for `EXECUTOR_API_TOKEN`

**File:** `README.md:87`
**Severity:** LOW
**Category:** Documentation - Accuracy

The README says the default for `EXECUTOR_API_TOKEN` is `local-dev-token`, but the actual code default in `src/config.py:76` is an empty string `""`. The validator warns for both, but the documentation is misleading.

```markdown
# README.md:87
| `EXECUTOR_API_TOKEN` | `local-dev-token` | Shared secret for all callers |
```

**Fix:** Update the README to reflect the actual default:
```markdown
| `EXECUTOR_API_TOKEN` | (empty) | Shared secret for all callers (REQUIRED) |
```

---

## Enhancement Suggestions

### E1. Add Audit Logging for All Execution Requests

Currently, execution requests are logged at INFO level with only the code length. For a security-sensitive code execution service, every request should include a structured audit log entry with:
- Timestamp
- Source IP
- Code hash (SHA-256)
- Code length
- Context keys (not values)
- Execution result (success/failure)
- Execution time
- Token identifier (first/last 4 chars only)

### E2. Add Prometheus Metrics Endpoint

The service already depends on `prometheus-client` but only uses a simple dict-based metrics system. Switch to proper Prometheus counters/histograms and expose a `/metrics` endpoint in Prometheus exposition format.

### E3. Add Request ID Tracking

Generate a unique request ID for each execution request and propagate it through all log messages. This enables tracing a single request through sandbox subprocess logs.

### E4. Consider Adding Docker `--read-only` and `--no-new-privileges`

The Dockerfile runs as non-root (good), but the deployment documentation doesn't mention running with `--read-only` filesystem and `--no-new-privileges`. These Docker security flags would add defense-in-depth:

```bash
docker run --rm -p 8030:8030 \
  --read-only \
  --security-opt=no-new-privileges \
  --tmpfs /tmp:noexec,nosuid,size=64m \
  -e EXECUTOR_API_TOKEN=secure-token \
  homeiq-code-executor
```

### E5. Consider seccomp Profile for Docker Container

For maximum sandbox security, a custom seccomp profile could restrict the system calls available to the container, further limiting the attack surface even if the Python sandbox is bypassed.

---

## Prioritized Action Plan

### Immediate (Before Next Deployment)

| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 1 | **C1** - Add `hmac.compare_digest()` for token comparison | 5 min | Eliminates timing attack vector |
| 2 | **C3** - Add RestrictedPython guard functions (`_getattr_`, etc.) | 30 min | Closes sandbox escape via attribute traversal |
| 3 | **C2** - Guard `byte_code.code is None` | 5 min | Prevents potential `exec(None)` crash |
| 4 | **H5** - Sanitize error messages returned to clients | 10 min | Prevents information disclosure |
| 5 | **H3** - Bound stdout/stderr capture | 20 min | Prevents memory exhaustion via print bombing |

### Short-Term (Within 1 Sprint)

| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 6 | **H4** - Validate and bound return values | 20 min | Prevents memory/pickle attacks via `_` |
| 7 | **H2** - Fix MCP context merge order | 10 min | Prevents future context override attacks |
| 8 | **M1** - Delete stale backup file | 2 min | Reduces confusion and attack surface |
| 9 | **M3** - Fix health check to report actual status | 10 min | Improves operational visibility |
| 10 | **M8** - Add basic rate limiting | 30 min | Prevents DoS via request flooding |

### Medium-Term (Within 2 Sprints)

| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 11 | **M2** - Use thread-safe metrics or prometheus_client | 1 hr | Prevents metric corruption |
| 12 | **M4** - Add `security/__init__.py` | 5 min | Consistency |
| 13 | **M5** - Migrate `class Config` to `model_config` | 10 min | Follows Pydantic V2 best practice |
| 14 | **L4** - Fix test state bleeding | 30 min | Reliable test suite |
| 15 | **E1** - Add structured audit logging | 2 hr | Security observability |
| 16 | **E2** - Implement proper Prometheus metrics | 2 hr | Production monitoring |

---

## Security Architecture Summary

**Strengths:**
- Multi-layer defense: static validation -> RestrictedPython -> subprocess isolation -> RLIMIT
- Linux-only enforcement prevents running without OS-level sandboxing
- Network MCP tools correctly disabled by default with a hard raise when enabled
- Import whitelist is conservative (8 safe stdlib modules)
- Context sanitization blocks non-primitive types and dunder keys
- Subprocess uses `spawn` context (not `fork`) preventing parent state leakage
- Non-root Docker user with minimal Alpine base
- CORS locked down to localhost by default
- API token required for execution endpoint

**Weaknesses:**
- RestrictedPython guard functions not explicitly configured in execution environment
- No output/return-value size bounds
- Token comparison vulnerable to timing attacks
- Error messages leak internal details
- No rate limiting beyond semaphore
- No audit trail for execution requests
- No container-level security hardening documented (seccomp, read-only fs)
