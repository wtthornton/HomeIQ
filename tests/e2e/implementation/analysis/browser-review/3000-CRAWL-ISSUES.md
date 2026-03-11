# Port 3000 (Health Dashboard) -- Crawl Issues

**Source:** Playwright crawl of all 17 routes
**Generated:** 2026-03-11
**Base URL:** http://localhost:3000

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 25 |
| Medium   | 8 |
| Low      | 0 |
| **Total** | **33** |

### Action Required

No critical issues found.
**25 HIGH issue(s) -- should be addressed soon.**

---

## Issues by Severity

### High

| # | Route | Category | Message |
|---|-------|----------|---------|
| 1 | `/#overview` | vite_config | Vite env var misconfiguration: Security warning: VITE_API_KEY is set via environment variable and will be embedded in the client bundle. This is insecure for production. Use session-based auth or nginx proxy auth instead. |
| 2 | `/#overview` | console_error | API Error for /api/v1/alerts/active: TypeError: Failed to fetch     at _y.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:40559)     at _y.getActiveAlerts (http://localhost |
| 3 | `/#overview` | console_error | Failed to fetch alerts: Error: Unable to reach backend. Check that admin-api and data-api services are running.     at _y.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41 |
| 4 | `/#overview` | console_error | Failed to load resource: the server responded with a status of 429 (Too Many Requests) |
| 5 | `/#overview` | console_error | API Error for /api/devices?limit=1000: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:300 |
| 6 | `/#overview` | console_error | Error fetching devices: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:3000/assets/js/use |
| 7 | `/#overview` | console_error | API Error for /api/entities?limit=10000: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:3 |
| 8 | `/#overview` | console_error | Error fetching entities: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:3000/assets/js/us |
| 9 | `/#overview` | console_error | API Error for /api/integrations?limit=100: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost |
| 10 | `/#overview` | console_error | Error fetching integrations: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:3000/assets/j |
| 11 | `/#overview` | console_error | API Error for /api/v1/activity: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async Oy.getCurrentActivity (http |
| 12 | `/#overview` | network_fail | Request failed: http://localhost:3000/assets/js/LoadingSpinner-CH99Hgdb.js |
| 13 | `/#overview` | network_fail | Request failed: http://localhost:3000/api/v1/alerts/active |
| 14 | `/#overview` | network_fail | Request failed: http://localhost:3000/assets/js/OverviewTab-HPcV4-E0.js |
| 15 | `/#overview` | network_fail | Request failed: http://localhost:3000/assets/js/SkeletonCard-DqJ9A0Bx.js |
| 16 | `/#overview` | network_fail | Request failed: http://localhost:3000/assets/js/ServiceDetailsModal-DDECYsAB.js |
| 17 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/devices?limit=1000 |
| 18 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/entities?limit=10000 |
| 19 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/integrations?limit=100 |
| 20 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/v1/activity |
| 21 | `/` | vite_config | Vite env var misconfiguration: Security warning: VITE_API_KEY is set via environment variable and will be embedded in the client bundle. This is insecure for production. Use session-based auth or nginx proxy auth instead. |
| 22 | `/` | console_error | Failed to load resource: the server responded with a status of 404 (Not Found) |
| 23 | `/` | console_error | API Error for /api/v1/activity: Backend unavailable. Check that admin-api and data-api services are running. |
| 24 | `/` | console_error | API Error for /api/v1/activity: Error: Backend unavailable. Check that admin-api and data-api services are running.     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:1 |
| 25 | `/` | network_fail | HTTP 404: http://localhost:3000/api/v1/activity |

### Medium

| # | Route | Category | Message |
|---|-------|----------|---------|
| 1 | `/#overview` | console_warn | Security warning: VITE_API_KEY is set via environment variable and will be embedded in the client bundle. This is insecure for production. Use session-based auth or nginx proxy auth instead. |
| 2 | `/#overview` | console_warn | Failed to decode downloaded font: http://localhost:3000/assets/css/files/inter-latin-wght-normal.woff2 |
| 3 | `/#overview` | console_warn | OTS parsing error: invalid sfntVersion: 1008821359 |
| 4 | `/#overview` | console_warn | Failed to decode downloaded font: http://localhost:3000/assets/css/files/outfit-latin-wght-normal.woff2 |
| 5 | `/` | console_warn | Failed to decode downloaded font: http://localhost:3000/assets/css/files/inter-latin-wght-normal.woff2 |
| 6 | `/` | console_warn | OTS parsing error: invalid sfntVersion: 1008821359 |
| 7 | `/` | console_warn | Failed to decode downloaded font: http://localhost:3000/assets/css/files/outfit-latin-wght-normal.woff2 |
| 8 | `/` | console_warn | Security warning: VITE_API_KEY is set via environment variable and will be embedded in the client bundle. This is insecure for production. Use session-based auth or nginx proxy auth instead. |
