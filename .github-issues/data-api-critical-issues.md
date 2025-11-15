# [CRITICAL] Data API Service - Security Vulnerabilities and Resource Leaks

**Use 2025 patterns, architecture and versions for decisions and ensure the Readme files are up to date.**

## Overview
Analysis of the data-api service has revealed **CRITICAL SECURITY VULNERABILITIES** including Flux injection attacks, resource leaks, and authentication bypass risks across 15+ locations.

---

## CRITICAL Security Vulnerabilities

### 1. **Flux Query Injection Vulnerabilities**
**Locations:** Multiple files - `events_endpoints.py`, `devices_endpoints.py`, `energy_endpoints.py`
**Severity:** CRITICAL

**Issue:** User input directly interpolated into Flux queries without sanitization, allowing attackers to execute arbitrary queries.

**Examples:**
- `events_endpoints.py:428-434` - `context_id` parameter unsanitized
- `events_endpoints.py:462` - `entity_id` directly interpolated
- `energy_endpoints.py:110-528` - ALL endpoints use unsanitized input

```python
# Vulnerable code:
filter_entity_clause = f'  |> filter(fn: (r) => r["entity_id"] == "{entity_id}")\n'
```

**Impact:**
- Data breach - unauthorized access to any data in InfluxDB
- Bypass filters and access controls
- Potential DoS attacks

**Fix:** Apply `sanitize_flux_value()` to ALL user inputs in Flux queries. The function exists but is only used in 6 out of ~30 injection points.

**Affected Endpoints:**
- `/api/v1/events/automation-trace/{context_id}`
- `/api/v1/events/{event_id}`
- `/energy/correlations`
- `/energy/device-impact/{entity_id}`
- `/energy/top-consumers`
- All energy endpoints (100-528 in energy_endpoints.py)

---

### 2. **Inconsistent Input Sanitization**
**Locations:** Across all endpoint files
**Severity:** CRITICAL

**Issue:** The `sanitize_flux_value()` function exists but is inconsistently applied, creating false sense of security.

**Evidence:**
- `events_endpoints.py` sanitizes SOME parameters but NOT context_id or entity_id
- `devices_endpoints.py` sanitizes field names but NOT filter values
- `energy_endpoints.py` sanitizes NOTHING
- Helper functions (lines 718-757 in devices_endpoints.py) completely unsanitized

**Impact:** Partial protection is worse than no protection - creates false security assumptions.

---

## CRITICAL Resource Leaks

### 3. **InfluxDB Clients Not Properly Closed**
**Locations:** `events_endpoints.py`, `devices_endpoints.py`, `energy_endpoints.py`
**Severity:** HIGH

**Issue:** InfluxDB clients created but not guaranteed to close on exceptions.

**Examples:**
- `events_endpoints.py:423` - client created inside try, exception handling doesn't guarantee closure
- `devices_endpoints.py:280` - client only closed at line 340, exception at 352 bypasses it
- `energy_endpoints.py` - EVERY endpoint creates client without try/finally pattern

**Impact:**
- Connection pool exhaustion
- Memory leaks
- Service degradation over time

**Fix:** Use try/finally blocks for ALL InfluxDB client usage:
```python
client = None
try:
    client = get_influxdb_client()
    # ... operations ...
finally:
    if client:
        client.close()
```

---

## HIGH Severity Issues

### 4. **Authentication Bypass Risk**
**Location:** `main.py:111`
**Severity:** MEDIUM-HIGH

**Issue:** Only exact string "true" enables auth. Truthy values like "1" or "yes" DISABLE it.

```python
self.enable_auth = os.getenv('ENABLE_AUTH', 'true').lower() == 'true'
```

**Risk:** Accidental misconfiguration could disable authentication in production.

---

### 5. **Potential DoS via Unbounded Query Parameters**
**Locations:** `events_endpoints.py:139`, `analytics_endpoints.py:163`
**Severity:** MEDIUM

**Issue:** No validation on parameters like `duration` (could be 999999999) causing resource exhaustion.

**Impact:** DoS attacks, performance issues.

---

### 6. **Database Transaction Rollback Issues**
**Location:** `database.py:120-128`
**Severity:** MEDIUM

**Issue:** Partial commit failures may not fully restore consistency.

---

## Summary Table

| Issue | Severity | Count | Files Affected |
|-------|----------|-------|----------------|
| Flux Injection | CRITICAL | 15+ locations | events_endpoints, energy_endpoints, devices_endpoints |
| Resource Leaks | HIGH | 12+ endpoints | All endpoint files |
| Inconsistent Sanitization | CRITICAL | Entire codebase | All files |
| Auth Bypass Risk | MEDIUM-HIGH | 1 location | main.py |
| Unbounded Queries | MEDIUM | 5+ endpoints | Multiple files |

---

## Immediate Remediation Priorities

1. **URGENT:** Apply `sanitize_flux_value()` to ALL Flux query parameters
2. **URGENT:** Implement proper resource management with try/finally for ALL InfluxDB clients
3. **HIGH:** Add validation for query parameters (duration, range, limit values)
4. **HIGH:** Fix authentication configuration to reject invalid values
5. **MEDIUM:** Add transaction boundaries and error handling for database operations

---

## Files Requiring Immediate Attention

- `/home/user/HomeIQ/services/data-api/src/energy_endpoints.py` - ENTIRE FILE vulnerable
- `/home/user/HomeIQ/services/data-api/src/events_endpoints.py` - Lines 382-489, 729-944, 946-1059
- `/home/user/HomeIQ/services/data-api/src/devices_endpoints.py` - Lines 254-359, 463-600, 718-757

---

## References
- OWASP Top 10 - Injection Attacks
- CLAUDE.md - Database Optimization & Security Patterns
- Service location: `/services/data-api/`
