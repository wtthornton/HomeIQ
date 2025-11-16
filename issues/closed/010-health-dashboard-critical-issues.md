---
status: Closed
priority: Critical
service: health-dashboard
created: 2025-11-15
labels: [critical, deployment, security]
closed: 2025-11-16
resolution: >
  Hardcoded localhost calls replaced with nginx-backed routes, HA tokens removed
  from the browser via admin-api proxying, CSP + CSRF protections enforced, and
  README/env guidance updated.
---

# [CRITICAL] Health Dashboard - Deployment Blockers and Security Issues

**Use 2025 patterns, architecture and versions for decisions and ensure the Readme files are up to date.**

## Overview
The health-dashboard frontend has **CRITICAL deployment blockers** and security vulnerabilities that will prevent it from working in production Docker environments and expose sensitive credentials.

## Resolution Summary
- Replaced all hardcoded `localhost` calls with nginx-backed routes and Vite dev proxies so the UI works inside Docker/HTTPS.
- Added admin-api `/api/v1/ha-proxy/*` endpoints and updated the frontend HA client to eliminate `VITE_HA_TOKEN` usage in the browser.
- Enabled CSP plus double-submit CSRF enforcement (nginx + `homeiq_csrf` cookie) and wired the React app to auto-manage the token/header.
- Cleaned `.env` defaults, Vite proxy config, and README instructions to reflect relative routing and the new security requirements.

---

## CRITICAL Issues

### 1. **HARDCODED LOCALHOST URLs - DEPLOYMENT BLOCKER**
**Severity:** CRITICAL - Will break in Docker/Production

**Issue:** Multiple components bypass the nginx proxy and use hardcoded `localhost` URLs that won't work in containerized environments.

**Affected Files:**
- `src/components/LogTailViewer.tsx` (lines 52, 95)
  ```typescript
  const response = await fetch(`http://localhost:8015/api/v1/logs?${params}`);
  ```

- `src/components/AlertBanner.tsx` (lines 28, 48, 62)
  ```typescript
  const response = await fetch('http://localhost:8003/api/v1/alerts/active');
  ```

- `src/components/AIStats.tsx` (lines 32, 47)
- `src/components/ai/NLInput.tsx` (line 39)
- `src/components/DataSourcesPanel.tsx` (line 42)
- `src/services/api.ts` (line 134)
- `src/hooks/useEnvironmentHealth.ts` (line 11)

**Impact:** Application will fail to fetch data in production Docker containers where services are on Docker network (e.g., `http://log-aggregator:8015`), not localhost.

**Fix:** Use relative paths or nginx proxy routes:
```typescript
// Instead of:
const response = await fetch('http://localhost:8015/api/v1/logs');

// Use:
const response = await fetch('/api/v1/logs');
// Configure nginx to proxy /api/v1/logs -> http://log-aggregator:8015/api/v1/logs
```

---

### 2. **HOME ASSISTANT TOKEN EXPOSURE - SECURITY VULNERABILITY**
**Severity:** CRITICAL - Security Risk

**Location:** `src/services/haClient.ts:28`

**Issue:** Home Assistant token could be exposed in client-side JavaScript bundle.

```typescript
this.token = config?.token || import.meta.env.VITE_HA_TOKEN || '';
```

**Problem:**
- `VITE_` prefixed environment variables are bundled into the client-side JavaScript
- Any user can inspect the bundle and extract the token
- Tokens should NEVER be in frontend code

**Impact:** Complete compromise of Home Assistant API access if token is set in VITE environment.

**Fix:** Remove `VITE_HA_TOKEN` usage. Proxy all HA API calls through a backend service that holds the token securely:
```typescript
// Remove direct HA token usage
// All HA API calls should go through a backend proxy service
const response = await fetch('/api/ha-proxy/...');
```

---

## HIGH Severity Issues

### 3. **MISSING CONTENT SECURITY POLICY (CSP)**
**Severity:** HIGH - Security Best Practice

**Location:** `nginx.conf`

**Issue:** The nginx configuration includes several security headers but is **missing the critical Content-Security-Policy header**.

**Current headers:**
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# MISSING: Content-Security-Policy header
```

**Impact:** Application vulnerable to XSS attacks, clickjacking, and other injection attacks.

**Fix:** Add CSP header:
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' http://admin-api:8004 http://log-aggregator:8015 ws://admin-api:8004;" always;
```

---

## MEDIUM Severity Issues

### 4. **HARDCODED PRIVATE IP ADDRESS IN ENVIRONMENT FILES**
**Severity:** MEDIUM - Configuration Issue

**Locations:**
- `env.development` (line 13)
- `env.production` (line 13)

```bash
VITE_HA_URL=http://192.168.1.86:8123
```

**Issues:**
- Private IP `192.168.1.86` is hardcoded
- Won't work in different network environments
- Exposed to client bundle via `VITE_` prefix
- Same configuration used for both dev and production

**Fix:** Make IP configurable via runtime environment or use service discovery.

---

### 5. **NO CSRF PROTECTION ON SENSITIVE FORMS**
**Severity:** MEDIUM - Security Vulnerability

**Location:** `src/components/setup/MqttConfigForm.tsx:78-82`

**Issue:** Forms use `credentials: 'include'` but no CSRF token validation.

```typescript
const response = await fetch(CONFIG_ENDPOINT, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',  // ⚠️ Sends cookies but no CSRF token
  body: JSON.stringify(payload),
});
```

**Impact:** Vulnerable to Cross-Site Request Forgery attacks.

**Fix:** Implement CSRF token validation or use alternative authentication method.

---

### 6. **MIXED CONTENT VULNERABILITIES**
**Severity:** MEDIUM - Deployment Issue

**Issue:** Hardcoded `http://` URLs will cause mixed content warnings if dashboard served over HTTPS.

**Impact:** Browser will block HTTP requests when served over HTTPS, breaking functionality.

**Fix:** Use relative URLs or ensure protocol-relative URLs.

---

### 7. **VITE PROXY CONFIGURATION USES DOCKER HOSTNAMES**
**Severity:** MEDIUM - Development Configuration Issue

**Location:** `vite.config.ts:46, 60`

**Issue:** Uses Docker container names that only resolve inside Docker network.

```typescript
'/ws': {
  target: 'ws://homeiq-admin-dev:8004',  // Docker hostname
},
'/api': {
  target: 'http://homeiq-admin-dev:8004',  // Docker hostname
}
```

**Impact:** Development server won't work outside Docker environment.

**Fix:** Use localhost for dev, Docker hostnames for Docker-based dev environment.

---

### 8. **NO INPUT VALIDATION ON USER-CONTROLLED API PARAMETERS**
**Severity:** MEDIUM - Security Best Practice

**Issue:** Multiple components don't validate user input before sending to backend.

**Examples:**
- `LogTailViewer.tsx` line 92: search query directly inserted into URL
- `MqttConfigForm.tsx`: No client-side validation of broker URL, credentials

**Impact:** Potential for injection attacks if backend validation is insufficient.

**Fix:** Add client-side input validation.

---

## Summary

**Critical Issues: 2**
1. Hardcoded localhost URLs (deployment blocker)
2. HA Token Exposure (security vulnerability)

**High Severity: 1**
3. Missing CSP header (security vulnerability)

**Medium Severity: 5**
4. IP hardcoding
5. CSRF protection
6. Mixed content
7. Proxy config
8. Input validation

---

## IMMEDIATE ACTIONS REQUIRED

1. Replace all hardcoded localhost URLs with relative paths or nginx proxy routes
2. Remove `VITE_HA_TOKEN` usage and implement backend proxy for HA API calls
3. Add Content-Security-Policy header to nginx.conf
4. Make IP addresses configurable per environment
5. Implement CSRF protection for state-changing operations

**The frontend will NOT work in production Docker deployment without fixing issues #1 and #2.**

---

## References
- OWASP Top 10 - Security Best Practices
- CLAUDE.md - Frontend Best Practices
- Service location: `/services/health-dashboard/`
- Port: 3000
- Type: React 18 + TypeScript + Vite
