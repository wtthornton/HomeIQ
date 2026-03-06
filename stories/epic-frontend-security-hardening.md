---
epic: frontend-security-hardening
priority: critical
status: in-progress
estimated_duration: 3-5 days
risk_level: high
source: REVIEW_AND_FIXES.md audits (2026-02-06), TAPPS security expert consultation
last_updated: 2026-03-06
---

# Epic: Frontend Security Hardening

**Status:** Open
**Priority:** Critical (P0)
**Duration:** 3-5 days
**Risk Level:** High — hardcoded API keys and CORS misconfigurations are live vulnerabilities
**Predecessor:** None — can start immediately
**Affects:** health-dashboard, ai-automation-ui, observability-dashboard

## Context

Security audits across all 3 frontends identified hardcoded API keys compiled into
client bundles, CORS wildcard with credentials, missing CSP headers, and unvalidated
user input in URL/regex contexts. These are exploitable in any deployment.

## Stories

### Story 1: Remove Hardcoded API Keys from All Frontends

**Priority:** Critical | **Estimate:** 4h | **Risk:** Low (well-scoped)

**Problem:** API keys are hardcoded as fallback values and baked into Docker build args,
extractable from browser DevTools in production.

**Files to fix:**
- `domains/frontends/ai-automation-ui/src/pages/Discovery.tsx:29` — hardcoded key fallback
- `domains/frontends/ai-automation-ui/src/api/admin.ts:49` — hardcoded key fallback
- `domains/frontends/ai-automation-ui/src/api/settings.ts:56` — hardcoded key fallback
- `domains/frontends/ai-automation-ui/src/api/preferences.ts:31` — hardcoded key fallback
- `domains/core-platform/health-dashboard/src/services/api.ts:109-117` — VITE_API_KEY in bundle
- `domains/core-platform/health-dashboard/src/components/IntegrationDetailsModal.tsx:125-133`
- Both Dockerfiles: `ENV VITE_API_KEY` persists in layer history

**Acceptance Criteria:**
- [x] Zero hardcoded API key strings in source code (grep confirms) ✅ 2026-03-06
- [x] API keys injected at runtime via nginx sub_filter or window.__ENV__ pattern ✅ 2026-03-06
- [ ] Docker images contain no API keys in any layer (`docker history` clean)
- [x] Existing functionality unchanged — all API calls still authenticate ✅ 2026-03-06
- [ ] Pre-commit hook added: grep guard for `VITE_.*KEY.*=.*['"]\w{10,}` patterns

---

### Story 2: Fix CORS Wildcard + Credentials in AI Automation UI nginx

**Priority:** Critical | **Estimate:** 2h | **Risk:** Low

**Problem:** `Access-Control-Allow-Origin: *` on every nginx proxy location combined with
`credentials: 'include'` in fetch calls allows any site to make authenticated cross-origin requests.

**Files to fix:**
- `domains/frontends/ai-automation-ui/nginx.conf` — lines 41, 72, 106, 138, 170, 202, 240

**Acceptance Criteria:**
- [x] CORS origin restricted to specific allowed origins (env-configurable) ✅ 2026-03-06 (Already implemented)
- [x] `credentials: 'include'` only used with matching `Access-Control-Allow-Origin` ✅ 2026-03-06
- [x] Preflight OPTIONS handled correctly for all proxy routes ✅ 2026-03-06
- [ ] Manual test: cross-origin request from unauthorized domain is rejected

---

### Story 3: Add Content-Security-Policy Headers

**Priority:** High | **Estimate:** 3h | **Risk:** Medium (may break inline styles/scripts)

**Problem:** No CSP header in either nginx config — XSS via injected scripts has no mitigation.

**Files to fix:**
- `domains/frontends/ai-automation-ui/nginx.conf`
- `domains/core-platform/health-dashboard/nginx.conf`

**Acceptance Criteria:**
- [x] CSP header added: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ws: wss:` ✅ 2026-03-06 (Already implemented)
- [ ] No console CSP violations when using all app features
- [ ] `X-XSS-Protection` deprecated header removed (SEC-04)
- [x] `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` confirmed present ✅ 2026-03-06

---

### Story 4: Fix Input Validation Vulnerabilities

**Priority:** High | **Estimate:** 3h | **Risk:** Low

**Problem:** Multiple unvalidated input paths:
- `haClient.ts:66-77` — user input passed to `new RegExp()` (ReDoS)
- `api.ts:373-383` — `serviceName` interpolated into URL without validation (path traversal)
- `Dashboard.tsx:48` — env var rendered as `href` without `sanitizeUrl()` (XSS)
- `MessageContent.tsx:29-105` — AI markdown rendered without `sanitizeMarkdown()`

**Acceptance Criteria:**
- [ ] RegExp input escaped via `escapeRegExp()` utility before `new RegExp()` (No vulnerable patterns found)
- [x] `serviceName` validated against allowlist pattern `^[a-zA-Z0-9_-]+$` ✅ 2026-03-06 (Already implemented in api.ts)
- [x] URLs validated via `sanitizeUrl()` before rendering in `href` ✅ 2026-03-06
- [x] ReactMarkdown wrapped with `sanitizeMarkdown()` in MessageContent ✅ 2026-03-06 (Added rehype-sanitize)
- [ ] Unit tests for each validation path

---

### Story 5: Fix CSRF Token and Auth Inconsistencies

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

**Problem:**
- `security.ts:48` — CSRF fallback uses `Math.random()` (non-cryptographic)
- Health dashboard has direct `fetch()` calls bypassing `BaseApiClient` auth
- AI UI has 10 API modules with inconsistent auth patterns

**Acceptance Criteria:**
- [x] CSRF token generation uses `crypto.getRandomValues()` ✅ 2026-03-06 (Already implemented)
- [ ] All health dashboard fetch calls routed through `BaseApiClient`
- [ ] Auth pattern consistent across AI UI API modules (addressed in Epic 3)

---

### Story 6: Secure Docker Configurations

**Priority:** Medium | **Estimate:** 1h | **Risk:** Low

**Problem:**
- Health dashboard nginx runs as root despite `appuser` being created
- Observability dashboard container runs as root (no `USER` directive)
- AI UI Docker health check hits `/` instead of lightweight `/health`
- AI UI uses `npm install` not `npm ci` (non-reproducible builds)

**Acceptance Criteria:**
- [ ] Nginx process runs as non-root user in health-dashboard
- [ ] `USER` directive added to observability-dashboard Dockerfile
- [ ] Health checks use lightweight `/health` or `/healthz` endpoints
- [ ] `npm ci` replaces `npm install` in all frontend Dockerfiles
