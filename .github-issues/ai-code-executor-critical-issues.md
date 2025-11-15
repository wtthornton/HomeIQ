# [CRITICAL] AI Code Executor Service - Multiple Security Vulnerabilities

**Use 2025 patterns, architecture and versions for decisions and ensure the Readme files are up to date.**

## ⚠️ SECURITY WARNING

**DO NOT deploy this service in production.** The service has **12 CRITICAL security vulnerabilities** that allow complete sandbox escape, arbitrary code execution, and full system compromise.

---

## Overview
The AI code executor service has fundamental security flaws that make it unsafe for production use. Multiple trivially exploitable vulnerabilities enable sandbox escape and unrestricted access to internal services.

---

## CRITICAL Security Vulnerabilities

### 1. **Sandbox Escape via Object Introspection**
**Location:** `src/executor/sandbox.py:161-189`
**Severity:** CRITICAL

**Issue:** The "safe" builtins include `type` and `isinstance`, enabling complete sandbox escape.

```python
safe_env = {
    '__builtins__': {
        'isinstance': isinstance,
        'type': type,  # ← CRITICAL: Enables introspection attack
    }
}
```

**Exploit Example:**
```python
for cls in type.__subclasses__(type):
    if cls.__name__ == 'catch_warnings':
        import os, subprocess
        subprocess.call(['rm', '-rf', '/'])
```

**Impact:** Complete bypass of RestrictedPython, full system access.

---

### 2. **sys.path Injection Allows Arbitrary Module Loading**
**Location:** `src/executor/mcp_sandbox.py:70-76`
**Severity:** CRITICAL

**Issue:** Service injects workspace path into user code WITHOUT proper isolation.

```python
setup_code = f"""
import sys
if '{workspace_path}/servers' not in sys.path:
    sys.path.insert(0, '{workspace_path}/servers')
"""
full_code = setup_code + "\n" + code
```

**Exploit:** User can override sys module or manipulate sys.path to load malicious modules.

**Impact:** Import restriction bypass, arbitrary code execution.

---

### 3. **Context Injection Vulnerability**
**Location:** `src/executor/sandbox.py:193`
**Severity:** CRITICAL

**Issue:** User context directly merged into execution environment without validation.

```python
safe_env.update(context)  # ← No validation of context objects
```

**Impact:** If context contains ANY objects with `__dict__`, `__class__`, `__globals__`, they provide escape vectors.

---

### 4. **Missing Documented Security Features**
**Location:** README.md vs actual implementation
**Severity:** CRITICAL

**Issue:** README claims security features that DON'T EXIST.

**README Claims (line 34):**
- "RestrictedPython - AST-level code restrictions" ✓ (but insufficient)
- "Resource Limits" ✓ (but bypassable)
- "Whitelist Imports" ✗ **NOT IMPLEMENTED**
- "Docker Isolation" ⚠ (no AppArmor/seccomp)
- "No Network Access" ✗ **FALSE - has full network**

**Files that don't exist:**
- `security/code_validator.py` ← DOES NOT EXIST
- `monitoring/metrics.py` ← DOES NOT EXIST

**Impact:** False sense of security, missing critical protections.

---

### 5. **Resource Limits Are Ineffective**
**Location:** `src/executor/sandbox.py:197-217`
**Severity:** CRITICAL

**Issues:**
```python
def _set_resource_limits(self):
    if sys.platform != 'linux':
        logger.warning("Resource limits only supported on Linux")
        return  # ← No limits on macOS/Windows
```

**Problems:**
1. No limits on non-Linux platforms
2. Limits applied AFTER compilation (unbounded compile-time attacks)
3. `RLIMIT_AS` doesn't prevent memory-mapped files or fork() bombs
4. `max_concurrent_executions=2` config is **NEVER enforced** in code

**Impact:** Resource exhaustion DoS attacks.

---

### 6. **No Code Size or Complexity Limits**
**Location:** `src/main.py:114-155`
**Severity:** CRITICAL

**Issue:** No validation of incoming code.

**Attack Vector:**
```python
{
    "code": "x = 'A' * 10**9"  # 1GB string allocation
}
```

**Impact:** Memory exhaustion, service crash.

---

### 7. **Import Restrictions Completely Bypassable**
**Location:** `src/executor/sandbox.py:48-51`
**Severity:** CRITICAL

**Issue:** The `allowed_imports` whitelist is defined but **NEVER ENFORCED**.

```python
self.allowed_imports = allowed_imports or {
    'json', 'datetime', 'math', 're', 'typing',
    'collections', 'itertools', 'functools'
}
# ← This list is defined but NEVER CHECKED
```

**Impact:** Users can import ANY module that's installed or in workspace.

---

### 8. **Unrestricted Network Access to Internal Services**
**Location:** `src/mcp/homeiq_tools.py:12-14`
**Severity:** CRITICAL

**Issue:** Code can access entire internal network.

```python
DATA_API_URL = "http://data-api:8006"
AI_AUTOMATION_URL = "http://ai-automation-service:8024"
DEVICE_INTELLIGENCE_URL = "http://device-intelligence-service:8028"
```

**Problem:** No authentication, authorization, or access control. Executed code can:
- Query all device data
- Access all automation patterns
- Pivot to other microservices
- Potentially reach external network

**Impact:** Complete data breach, lateral movement.

---

### 9. **CORS Allows Cross-Site Code Execution**
**Location:** `src/main.py:74-80`
**Severity:** CRITICAL

**Issue:** ANY website can call this service.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ← ANY website can call this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impact:** Remote code execution via CSRF attack from malicious website.

---

### 10. **No Request Authentication**
**Location:** `src/main.py:114-155`
**Severity:** CRITICAL

**Issue:** The `/execute` endpoint has ZERO authentication.

**Impact:** Anyone on the network can execute arbitrary code.

---

### 11. **Timeout Bypass via Blocking Operations**
**Location:** `src/executor/sandbox.py:117-125, 219-229`
**Severity:** CRITICAL

**Issue:** Timeout applied to asyncio task, but code runs in thread executor.

```python
result = await asyncio.wait_for(
    self._execute_code(byte_code.code, safe_env),
    timeout=self.config.timeout_seconds
)

async def _execute_code(self, code, env: Dict[str, Any]) -> Any:
    return await loop.run_in_executor(None, _run)  # ← Runs in thread
```

**Problem:** If thread enters infinite CPU loop, asyncio timeout may not work. Thread continues running.

**Impact:** Resource exhaustion via infinite loops.

---

### 12. **RestrictedPython Alone Is Insufficient**
**Location:** `src/executor/sandbox.py:88-93`
**Severity:** HIGH

**Issue:** RestrictedPython only restricts AST compilation. It does NOT prevent:
- Access to already-imported modules in `sys.modules`
- Object introspection via `__dict__`, `__class__`, `__bases__`
- Type confusion attacks
- Unicode/encoding attacks

**Known Bypass:**
```python
{}.__class__.__bases__[0].__subclasses__()
```

**Impact:** Sandbox escape despite RestrictedPython.

---

## Summary of Critical Findings

| Issue | Severity | Exploitable | Impact |
|-------|----------|-------------|---------|
| Object introspection escape | CRITICAL | ✓ Yes | Full system access |
| sys.path injection | CRITICAL | ✓ Yes | Arbitrary module loading |
| Context injection | CRITICAL | ✓ Yes | Sandbox escape |
| Missing security features | CRITICAL | N/A | False security claims |
| Ineffective resource limits | CRITICAL | ✓ Yes | DoS attacks |
| No code size limits | CRITICAL | ✓ Yes | Memory exhaustion |
| Import bypass | CRITICAL | ✓ Yes | Unrestricted imports |
| Unrestricted network access | CRITICAL | ✓ Yes | Data breach |
| CORS misconfiguration | CRITICAL | ✓ Yes | CSRF RCE |
| No authentication | CRITICAL | ✓ Yes | Unauthorized access |
| Timeout bypass | CRITICAL | ✓ Yes | Resource exhaustion |
| RestrictedPython insufficient | HIGH | ✓ Yes | Sandbox escape |

**Total: 12 exploitable vulnerabilities**

---

## Recommendation

**DO NOT deploy this service in production.** The security model is fundamentally flawed with multiple trivially exploitable vulnerabilities that allow:

1. Complete sandbox escape
2. Arbitrary code execution with full system privileges
3. Unrestricted access to internal services
4. Resource exhaustion attacks
5. Cross-site request forgery

**The service requires a complete security redesign before it can be safely used.**

---

## Required Security Improvements

If this service must be used, the following are **MINIMUM** requirements:

1. Remove `type` from safe builtins
2. Implement proper import whitelisting enforcement
3. Validate all context objects before adding to environment
4. Add authentication and authorization
5. Restrict CORS to known origins
6. Implement network isolation (no internal service access)
7. Add code size and complexity limits
8. Use proper sandboxing (Docker with AppArmor/seccomp, or gVisor)
9. Implement resource limits that actually work
10. Add comprehensive monitoring and alerting

**Even with these fixes, code execution services are inherently risky and should be carefully evaluated.**

---

## References
- OWASP Top 10 - Injection, Broken Authentication, Security Misconfiguration
- CLAUDE.md - Security Best Practices
- Service location: `/services/ai-code-executor/`
- Port: (not yet in production docker-compose)
