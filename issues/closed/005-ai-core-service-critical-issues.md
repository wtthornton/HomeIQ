---
status: Closed
priority: Critical
service: ai-core-service
created: 2025-11-15
closed: 2025-11-15
labels: [critical, security, reliability]
---

# [CRITICAL] AI Core Service - Security and Reliability Issues

**Use 2025 patterns, architecture and versions for decisions and ensure the Readme files are up to date.**

## Overview
The ai-core-service has **10 CRITICAL issues** including security vulnerabilities, resource leaks, and configuration problems that prevent safe production deployment.

---

## CRITICAL Issues

### 1. **Missing Environment File**
**Location:** `docker-compose.yml` references `infrastructure/env.ai-automation`
**Severity:** CRITICAL

**Issue:** The configuration references `infrastructure/env.ai-automation`, but this file does NOT exist. Only `env.ai-automation.template` exists.

**Impact:** Service will fail to load environment variables properly, potentially using defaults or causing startup failures.

**Fix:** Create `env.ai-automation` from template or update docker-compose to use correct file.

---

### 2. **No Authentication/Authorization**
**Location:** All API endpoints in `src/main.py`
**Severity:** CRITICAL

**Issue:** The service has ZERO authentication or authorization mechanisms.

**Impact:**
- Unauthorized access to AI operations
- Potential data exposure
- Ability to consume resources without limits
- Complete lack of access control

**Affected Endpoints:**
- `/analyze` - Unrestricted data analysis
- `/patterns` - Unrestricted pattern detection
- `/suggestions` - Unrestricted AI suggestion generation

**Fix:** Implement authentication middleware.

---

### 3. **Overly Permissive CORS Configuration**
**Location:** `src/main.py:72-78`
**Severity:** CRITICAL

**Issue:** CORS configured to allow ALL origins with credentials enabled.

```python
CORSMiddleware,
    allow_origins=["*"],        # ❌ ANY origin can call this API
    allow_credentials=True,     # ❌ Dangerous with wildcard origins
    allow_methods=["*"],
    allow_headers=["*"],
```

**Impact:**
- Cross-Site Request Forgery (CSRF) attacks possible
- Any malicious website can make requests
- Violates security best practices

**Fix:** Restrict origins to known trusted domains.

---

### 4. **Resource Leak - HTTP Client Not Closed**
**Location:** `src/orchestrator/service_manager.py:26`, `src/main.py:60`
**Severity:** CRITICAL

**Issue:** AsyncClient created but never closed during shutdown.

```python
# service_manager.py line 26
self.client = httpx.AsyncClient(timeout=30.0)  # Created

# main.py line 60 - Shutdown
yield
# Cleanup on shutdown (if needed)  # ❌ No actual cleanup!
```

**Impact:**
- Connection pool not properly released
- Socket exhaustion over time
- Memory leaks during service restarts

**Fix:** Add proper cleanup in shutdown lifecycle.

---

### 5. **Port Mismatch in Documentation**
**Location:** `README.md` vs `Dockerfile` and `docker-compose.yml`
**Severity:** CRITICAL

**Issue:** Documentation states Port 8021, but actual deployment uses Port 8018.

**Impact:**
- Developers will use wrong port
- Integration issues with dependent services
- Confusing debugging

**Fix:** Update README.md to reflect correct port 8018.

---

### 6. **Bare Except Clause**
**Location:** `src/orchestrator/service_manager.py:275`
**Severity:** CRITICAL

**Issue:** Bare `except:` catches ALL exceptions including system exits.

```python
try:
    import json
    return json.loads(response)
except:  # ❌ DANGEROUS
    return [...]
```

**Impact:**
- Can mask critical system errors
- Prevents graceful shutdown
- Makes debugging impossible

**Fix:** Use specific exception types: `except (json.JSONDecodeError, ValueError) as e:`

---

### 7. **Service Can Start with All Dependencies Down**
**Location:** `src/orchestrator/service_manager.py:38-45`
**Severity:** CRITICAL

**Issue:** Service initialization only logs warnings if AI services are unavailable but continues startup.

**Impact:**
- Service reports "healthy" but can't perform any AI operations
- All requests will fail but service stays running
- Misleading health checks

**Fix:** Fail fast if critical dependencies are unavailable.

---

### 8. **Error Messages Expose Internal Details**
**Location:** `src/main.py:158, 185, 212`
**Severity:** CRITICAL

**Issue:** Raw exception messages returned to clients.

```python
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    # ❌ Exposes full exception details to attacker
```

**Impact:** Information disclosure - helps attackers understand system internals.

**Fix:** Return generic error messages, log detailed errors server-side.

---

### 9. **No Rate Limiting**
**Location:** All endpoints in `src/main.py`
**Severity:** CRITICAL

**Issue:** Zero rate limiting on computationally expensive AI operations.

**Impact:**
- Denial of Service (DoS) attacks possible
- Resource exhaustion from single client
- Could bring down entire AI infrastructure

**Fix:** Implement rate limiting middleware.

---

### 10. **NER Service URL Conflict**
**Location:** `docker-compose.yml` and service configuration
**Severity:** CRITICAL

**Issue:** Both NER service and OpenVINO service use port 8019.

**Evidence:**
- `NER_SERVICE_URL=http://ner-service:8019`
- `OPENVINO_SERVICE_URL=http://openvino-service:8019`

**Impact:**
- Port conflict between services
- One service will fail to start

**Fix:** Assign unique ports to each service.

---

## Summary

**Total: 10 CRITICAL issues**

**Most Critical:**
- Issues #2 (no auth), #3 (CORS), #8 (info disclosure), #9 (no rate limiting) represent **severe security vulnerabilities**

---

## Immediate Actions Required

1. ✅ Fix missing environment file
2. ✅ Implement authentication/authorization
3. ✅ Restrict CORS origins
4. ✅ Add resource cleanup
5. ✅ Fix port documentation mismatch
6. ✅ Fix bare except clause
7. ✅ Implement dependency health checks
8. ✅ Sanitize error messages
9. ✅ Add rate limiting
10. ✅ Resolve port conflicts

---

## Resolution (2025-11-15)

- Created a real `infrastructure/env.ai-automation` file (and updated the template) so docker-compose references always resolve, eliminating the missing env-file failure.
- Added API key authentication, per-client rate limiting, sanitized error messages, and restricted CORS defaults in `services/ai-core-service/src/main.py`; dependency health now fails fast and the HTTP client shuts down cleanly.
- Hardened `ServiceManager` with explicit exception handling, safe JSON parsing, and a cleanup hook.
- Updated docker-compose, ai-core/ai-automation service code, and supporting scripts/docs to move the NER service to a dedicated port (`8031`) and document the ai-core port as 8018.
- Refreshed service documentation (ai-core README, root README, CLAUDE, architecture/service references) with the new security requirements and accurate port mappings.

---

## References
- CLAUDE.md - Security and Performance Patterns
- Service location: `/services/ai-core-service/`
- Port: 8018
