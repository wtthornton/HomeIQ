# Port 3000 (Health Dashboard) -- Crawl Issues

**Source:** Playwright crawl of all 17 routes
**Generated:** 2026-03-11
**Base URL:** http://localhost:3000

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 94 |
| Medium   | 8 |
| Low      | 0 |
| **Total** | **102** |

### Action Required

No critical issues found.
**94 HIGH issue(s) -- should be addressed soon.**

---

## Issues by Severity

### High

| # | Route | Category | Message |
|---|-------|----------|---------|
| 1 | `/#overview` | vite_config | Vite env var misconfiguration: Security warning: VITE_API_KEY is set via environment variable and will be embedded in the client bundle. This is insecure for production. Use session-based auth or nginx proxy auth instead. |
| 2 | `/#overview` | console_error | API Error for /api/v1/alerts/active: TypeError: Failed to fetch     at _y.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:40559)     at _y.getActiveAlerts (http://localhost |
| 3 | `/#overview` | console_error | Failed to fetch alerts: Error: Unable to reach backend. Check that admin-api and data-api services are running.     at _y.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41 |
| 4 | `/#overview` | console_error | Failed to load resource: the server responded with a status of 429 (Too Many Requests) |
| 5 | `/#overview` | console_error | API Error for /api/v1/stats?period=1h: Error: HTTP 429: Too Many Requests     at _y.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087) |
| 6 | `/#overview` | console_error | Statistics fetch error: Error: HTTP 429: Too Many Requests     at _y.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087) |
| 7 | `/#overview` | console_error | API Error for /api/entities?limit=10000: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:3 |
| 8 | `/#overview` | console_error | Error fetching entities: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:3000/assets/js/us |
| 9 | `/#overview` | console_error | API Error for /api/integrations?limit=100: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost |
| 10 | `/#overview` | console_error | Error fetching integrations: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:3000/assets/j |
| 11 | `/#overview` | console_error | API Error for /api/v1/activity: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async Oy.getCurrentActivity (http |
| 12 | `/#overview` | console_error | API Error for /api/devices?limit=1000: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:300 |
| 13 | `/#overview` | console_error | Error fetching devices: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:3000/assets/js/use |
| 14 | `/#overview` | network_fail | Request failed: http://localhost:3000/api/v1/alerts/active |
| 15 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/v1/stats?period=1h |
| 16 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/entities?limit=10000 |
| 17 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/integrations?limit=100 |
| 18 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/v1/activity |
| 19 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/devices?limit=1000 |
| 20 | `/#overview` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 21 | `/#overview` | visible_error | Visible error/warning: ⚠️ |
| 22 | `/#overview` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 23 | `/#services` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 24 | `/#services` | visible_error | Visible error/warning: ⚠️ |
| 25 | `/#services` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 26 | `/#groups` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 27 | `/#groups` | visible_error | Visible error/warning: ⚠️ |
| 28 | `/#groups` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 29 | `/#dependencies` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 30 | `/#dependencies` | visible_error | Visible error/warning: ⚠️ |
| 31 | `/#dependencies` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 32 | `/#configuration` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 33 | `/#configuration` | visible_error | Visible error/warning: ⚠️ |
| 34 | `/#configuration` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 35 | `/#devices` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 36 | `/#devices` | visible_error | Visible error/warning: ⚠️ |
| 37 | `/#devices` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 38 | `/#events` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 39 | `/#events` | visible_error | Visible error/warning: ⚠️ |
| 40 | `/#events` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 41 | `/#data-sources` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 42 | `/#data-sources` | visible_error | Visible error/warning: ⚠️ |
| 43 | `/#data-sources` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 44 | `/#energy` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 45 | `/#energy` | visible_error | Visible error/warning: ⚠️ |
| 46 | `/#energy` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 47 | `/#sports` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 48 | `/#sports` | visible_error | Visible error/warning: ⚠️ |
| 49 | `/#sports` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 50 | `/#alerts` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 51 | `/#alerts` | visible_error | Visible error/warning: ⚠️ |
| 52 | `/#alerts` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 53 | `/#hygiene` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 54 | `/#hygiene` | visible_error | Visible error/warning: ⚠️ |
| 55 | `/#hygiene` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 56 | `/#validation` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 57 | `/#validation` | visible_error | Visible error/warning: ⚠️ |
| 58 | `/#validation` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 59 | `/#evaluation` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 60 | `/#evaluation` | visible_error | Visible error/warning: ⚠️ |
| 61 | `/#evaluation` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 62 | `/#logs` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 63 | `/#logs` | visible_error | Visible error/warning: ⚠️ |
| 64 | `/#logs` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 65 | `/#analytics` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 66 | `/#analytics` | visible_error | Visible error/warning: ⚠️ |
| 67 | `/#analytics` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |
| 68 | `/` | vite_config | Vite env var misconfiguration: Security warning: VITE_API_KEY is set via environment variable and will be embedded in the client bundle. This is insecure for production. Use session-based auth or nginx proxy auth instead. |
| 69 | `/` | console_error | Failed to load resource: the server responded with a status of 429 (Too Many Requests) |
| 70 | `/` | console_error | API Error for /api/v1/docker/containers: Error: HTTP 429: Too Many Requests     at _y.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async o (http://localhos |
| 71 | `/` | console_error | Failed to fetch containers: Error: HTTP 429: Too Many Requests     at _y.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async o (http://localhost:3000/assets |
| 72 | `/` | console_error | API Error for /api/v1/stats?period=1h: Error: HTTP 429: Too Many Requests     at _y.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087) |
| 73 | `/` | console_error | Statistics fetch error: Error: HTTP 429: Too Many Requests     at _y.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087) |
| 74 | `/` | console_error | API Error for /api/v1/health/services: Error: HTTP 429: Too Many Requests     at _y.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async _y.getAllDataSources |
| 75 | `/` | console_error | Failed to fetch data sources: Error: HTTP 429: Too Many Requests     at _y.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async _y.getAllDataSources (http:// |
| 76 | `/` | console_error | API Error for /api/integrations?limit=100: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost |
| 77 | `/` | console_error | Error fetching integrations: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:3000/assets/j |
| 78 | `/` | console_error | API Error for /api/devices?limit=1000: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:300 |
| 79 | `/` | console_error | Error fetching devices: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:3000/assets/js/use |
| 80 | `/` | console_error | API Error for /api/entities?limit=10000: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:3 |
| 81 | `/` | console_error | Error fetching entities: Error: HTTP 429: Too Many Requests     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:10:41087)     at async http://localhost:3000/assets/js/us |
| 82 | `/` | console_error | Failed to load resource: the server responded with a status of 404 (Not Found) |
| 83 | `/` | console_error | API Error for /api/v1/activity: Backend unavailable. Check that admin-api and data-api services are running. |
| 84 | `/` | console_error | API Error for /api/v1/activity: Error: Backend unavailable. Check that admin-api and data-api services are running.     at Oy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-CHVWOtyF.js:1 |
| 85 | `/` | network_fail | HTTP 429: http://localhost:3000/api/v1/docker/containers |
| 86 | `/` | network_fail | HTTP 429: http://localhost:3000/api/v1/stats?period=1h |
| 87 | `/` | network_fail | HTTP 429: http://localhost:3000/api/v1/health/services |
| 88 | `/` | network_fail | HTTP 429: http://localhost:3000/api/integrations?limit=100 |
| 89 | `/` | network_fail | HTTP 429: http://localhost:3000/api/devices?limit=1000 |
| 90 | `/` | network_fail | HTTP 429: http://localhost:3000/api/entities?limit=10000 |
| 91 | `/` | network_fail | HTTP 404: http://localhost:3000/api/v1/activity |
| 92 | `/` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 93 | `/` | visible_error | Visible error/warning: ⚠️ |
| 94 | `/` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |

### Medium

| # | Route | Category | Message |
|---|-------|----------|---------|
| 1 | `/#overview` | console_warn | Security warning: VITE_API_KEY is set via environment variable and will be embedded in the client bundle. This is insecure for production. Use session-based auth or nginx proxy auth instead. |
| 2 | `/#overview` | console_warn | Failed to decode downloaded font: http://localhost:3000/assets/css/files/outfit-latin-wght-normal.woff2 |
| 3 | `/#overview` | console_warn | OTS parsing error: invalid sfntVersion: 1008821359 |
| 4 | `/#overview` | console_warn | Failed to decode downloaded font: http://localhost:3000/assets/css/files/inter-latin-wght-normal.woff2 |
| 5 | `/` | console_warn | Failed to decode downloaded font: http://localhost:3000/assets/css/files/inter-latin-wght-normal.woff2 |
| 6 | `/` | console_warn | OTS parsing error: invalid sfntVersion: 1008821359 |
| 7 | `/` | console_warn | Failed to decode downloaded font: http://localhost:3000/assets/css/files/outfit-latin-wght-normal.woff2 |
| 8 | `/` | console_warn | Security warning: VITE_API_KEY is set via environment variable and will be embedded in the client bundle. This is insecure for production. Use session-based auth or nginx proxy auth instead. |
