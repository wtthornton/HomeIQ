---
status: Open
priority: Critical
service: admin-api
created: 2025-11-15
labels: [critical, security, authentication]
---

# [CRITICAL] Admin API Service - Authentication Bypass and Security Vulnerabilities

**Use 2025 patterns, architecture and versions for decisions and ensure the Readme files are up to date.**

## Overview
The admin-api service has **CRITICAL** security vulnerabilities including authentication bypass, unauthenticated Docker control, and credential exposure that enable complete system takeover.

---

## CRITICAL Security Issues

### 1. **AUTHENTICATION BYPASS VIA CONFIGURATION**
**Location:** `src/main.py:85`, `shared/auth.py:69-70`
**Severity:** CRITICAL

**Issue:** Authentication can be completely disabled by setting `ENABLE_AUTH=false`.

**Evidence:**
```python
# auth.py line 69-70
if not self.enable_auth:
    return self.default_user  # Returns without any validation!
```

**Impact:** When disabled, ALL "protected" endpoints become publicly accessible:
- Docker container management (start/stop/restart)
- Configuration modification
- Sensitive data access

**Risk:** Complete system takeover without credentials.

**Fix:** Remove `ENABLE_AUTH` toggle - authentication should ALWAYS be enabled in production.

---

### 2. **MISSING AUTHENTICATION ON CRITICAL ENDPOINTS**
**Location:** `src/main.py:347-371`
**Severity:** CRITICAL

**Issue:** Four routers registered WITHOUT authentication dependencies:

```python
# Lines 347-351 - Integration router with NO authentication
self.app.include_router(
    self.integration_router,
    prefix="/api/v1",
    tags=["Integration Management"]
)  # Missing: dependencies=[Depends(self.auth_manager.get_current_user)]
```

**Affected Routers:**
1. Integration Router (lines 347-351) - NO auth
2. Devices Router (lines 354-357) - NO auth
3. Metrics Router (lines 360-364) - NO auth
4. Alerts Router (lines 367-371) - NO auth

**Impact:** These endpoints are ALWAYS accessible without authentication, even when `ENABLE_AUTH=true`.

---

### 3. **UNAUTHENTICATED DOCKER CONTAINER CONTROL**
**Location:** `src/docker_endpoints.py:101-162`
**Severity:** CRITICAL

**Issue:** Docker start/stop/restart operations exposed without proper authentication.

**Dangerous Operations:**
- `POST /api/v1/docker/containers/{service_name}/start` - Start any container
- `POST /api/v1/docker/containers/{service_name}/stop` - Stop any container
- `POST /api/v1/docker/containers/{service_name}/restart` - Restart any container
- `GET /api/v1/docker/containers/{service_name}/logs` - Read container logs (may contain secrets)

**Impact:**
- Denial of Service by stopping critical services (InfluxDB, WebSocket ingestion)
- Information disclosure via container logs
- Service disruption

---

### 4. **UNRESTRICTED CONFIGURATION FILE MODIFICATION**
**Location:** `src/config_manager.py:88-166`, `src/api_key_service.py:311-350`
**Severity:** CRITICAL

**Issue:** Configuration endpoints allow writing to `.env` files, including sensitive credentials.

**Modifiable Credentials:**
- `HA_TOKEN` - Home Assistant long-lived access token
- `INFLUXDB_TOKEN` - Database credentials
- `WEATHER_API_KEY`, `AIRNOW_API_KEY`, etc.

**Evidence:**
```python
# config_manager.py line 149
with open(env_file, 'w') as f:
    f.writelines(new_lines)  # Direct write to .env files
```

**Impact:**
- Credential theft (read current tokens)
- Credential replacement (inject attacker's tokens)
- Persistent backdoor access
- Lateral movement to Home Assistant and InfluxDB

---

### 5. **SENSITIVE INFORMATION DISCLOSURE**
**Location:** `src/config_endpoints.py:58-75`
**Severity:** CRITICAL

**Issue:** `/config` endpoint exposes sensitive values when `include_sensitive=True`.

**Exposed Data:**
- All API keys and tokens
- Database credentials
- Home Assistant access tokens
- External service credentials

---

### 6. **HARDCODED DEMO CREDENTIALS**
**Location:** `src/auth.py:60-70`
**Severity:** HIGH

**Issue:** Hardcoded username/password in JWT authentication code.

**Credentials:**
- Username: `admin`
- Password: `adminpass`

**Impact:** If JWT authentication is used, these credentials provide full admin access.

**Fix:** Delete demo user, require configuration-based user management.

---

### 7. **NO RATE LIMITING**
**Location:** All endpoints
**Severity:** HIGH

**Issue:** No rate limiting on authentication attempts or API calls.

**Impact:**
- Brute force attacks on API keys
- Denial of Service via request flooding
- Resource exhaustion

---

### 8. **WEAK SHARED AUTHENTICATION**
**Location:** `shared/auth.py`
**Severity:** MEDIUM

**Issue:** Shared authentication module only supports API key authentication, lacks JWT/session features.

**Impact:** Inconsistent security model across services, single point of failure if API key is compromised.

---

## Recommendations

### Immediate Actions Required

1. **Remove `ENABLE_AUTH` toggle** - Authentication should ALWAYS be enabled
2. **Add authentication to missing routers** - Apply dependencies to all routers
3. **Remove hardcoded credentials** - Delete demo user with "adminpass"
4. **Implement rate limiting** - Add request throttling
5. **Add audit logging** - Log all Docker operations and configuration changes
6. **Restrict config file writes** - Validate and sanitize configuration updates
7. **Add input validation** - Validate service names in Docker endpoints

---

## Risk Assessment

**Overall Risk Level:** **CRITICAL**

**Attack Vector:** Unauthenticated remote access to administrative functions

**Likelihood:** HIGH (multiple bypass methods available)

**Impact:** CRITICAL (full system compromise, data theft, service disruption)

---

## References
- OWASP Top 10 - Broken Authentication
- CLAUDE.md - Security Patterns
- Service location: `/services/admin-api/`
- Port: 8003 → 8004
