# Port 3000 (Health Dashboard) -- Crawl Issues

**Source:** Playwright crawl of all 17 routes
**Generated:** 2026-03-13
**Base URL:** http://localhost:3000

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 62 |
| Medium   | 8 |
| Low      | 0 |
| **Total** | **70** |

### Action Required

No critical issues found.
**62 HIGH issue(s) -- should be addressed soon.**

---

## Issues by Severity

### High

| # | Route | Category | Message |
|---|-------|----------|---------|
| 1 | `/#overview` | vite_config | Vite env var misconfiguration: Security warning: VITE_API_KEY is set via environment variable and will be embedded in the client bundle. This is insecure for production. Use session-based auth or nginx proxy auth instead. |
| 2 | `/#overview` | console_error | Failed to load resource: the server responded with a status of 429 (Too Many Requests) |
| 3 | `/#overview` | console_error | API Error for /api/v1/alerts/active: Error: HTTP 429: Too Many Requests     at Hy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async _ (http://localhost:30 |
| 4 | `/#overview` | console_error | Failed to fetch alerts: Error: HTTP 429: Too Many Requests     at Hy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async _ (http://localhost:3000/assets/js/ |
| 5 | `/#overview` | console_error | API Error for /api/v1/docker/containers: Error: HTTP 429: Too Many Requests     at Hy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async d (http://localhos |
| 6 | `/#overview` | console_error | Failed to fetch containers: Error: HTTP 429: Too Many Requests     at Hy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async d (http://localhost:3000/assets |
| 7 | `/#overview` | console_error | API Error for /api/v1/health/services: Error: HTTP 429: Too Many Requests     at Hy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async Hy.getAllDataSources |
| 8 | `/#overview` | console_error | Failed to fetch data sources: Error: HTTP 429: Too Many Requests     at Hy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async Hy.getAllDataSources (http:// |
| 9 | `/#overview` | console_error | API Error for /api/entities?limit=10000: Error: HTTP 429: Too Many Requests     at jy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async http://localhost:3 |
| 10 | `/#overview` | console_error | Error fetching entities: Error: HTTP 429: Too Many Requests     at jy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async http://localhost:3000/assets/js/us |
| 11 | `/#overview` | console_error | API Error for /api/integrations?limit=100: Error: HTTP 429: Too Many Requests     at jy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async http://localhost |
| 12 | `/#overview` | console_error | Error fetching integrations: Error: HTTP 429: Too Many Requests     at jy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async http://localhost:3000/assets/j |
| 13 | `/#overview` | console_error | Failed to load resource: the server responded with a status of 404 (Not Found) |
| 14 | `/#overview` | console_error | API Error for /api/v1/activity: Backend unavailable. Check that admin-api and data-api services are running. |
| 15 | `/#overview` | console_error | API Error for /api/v1/activity: Error: Backend unavailable. Check that admin-api and data-api services are running.     at jy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:1 |
| 16 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/v1/alerts/active |
| 17 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/v1/docker/containers |
| 18 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/v1/health/services |
| 19 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/entities?limit=10000 |
| 20 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/integrations?limit=100 |
| 21 | `/#overview` | network_fail | HTTP 404: http://localhost:3000/api/v1/activity |
| 22 | `/#overview` | visible_error | Visible error/warning: 441.5 ms avg |
| 23 | `/#services` | visible_error | Visible error/warning: 441.5 ms avg |
| 24 | `/#groups` | visible_error | Visible error/warning: 441.5 ms avg |
| 25 | `/#dependencies` | visible_error | Visible error/warning: 441.5 ms avg |
| 26 | `/#configuration` | visible_error | Visible error/warning: 441.5 ms avg |
| 27 | `/#devices` | visible_error | Visible error/warning: 441.5 ms avg |
| 28 | `/#events` | visible_error | Visible error/warning: 441.5 ms avg |
| 29 | `/#data-sources` | visible_error | Visible error/warning: 441.5 ms avg |
| 30 | `/#energy` | visible_error | Visible error/warning: 441.5 ms avg |
| 31 | `/#sports` | visible_error | Visible error/warning: 441.5 ms avg |
| 32 | `/#alerts` | visible_error | Visible error/warning: 441.5 ms avg |
| 33 | `/#hygiene` | visible_error | Visible error/warning: 441.5 ms avg |
| 34 | `/#validation` | visible_error | Visible error/warning: 441.5 ms avg |
| 35 | `/#evaluation` | visible_error | Visible error/warning: 441.5 ms avg |
| 36 | `/#logs` | visible_error | Visible error/warning: 441.5 ms avg |
| 37 | `/#analytics` | visible_error | Visible error/warning: 441.5 ms avg |
| 38 | `/` | vite_config | Vite env var misconfiguration: Security warning: VITE_API_KEY is set via environment variable and will be embedded in the client bundle. This is insecure for production. Use session-based auth or nginx proxy auth instead. |
| 39 | `/` | console_error | Failed to load resource: the server responded with a status of 429 (Too Many Requests) |
| 40 | `/` | console_error | API Error for /api/v1/alerts/active: Error: HTTP 429: Too Many Requests     at Hy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async _ (http://localhost:30 |
| 41 | `/` | console_error | Failed to fetch alerts: Error: HTTP 429: Too Many Requests     at Hy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async _ (http://localhost:3000/assets/js/ |
| 42 | `/` | console_error | API Error for /api/devices?limit=1000: Error: HTTP 429: Too Many Requests     at jy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async http://localhost:300 |
| 43 | `/` | console_error | Error fetching devices: Error: HTTP 429: Too Many Requests     at jy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async http://localhost:3000/assets/js/use |
| 44 | `/` | console_error | API Error for /api/v1/docker/containers: Error: HTTP 429: Too Many Requests     at Hy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async d (http://localhos |
| 45 | `/` | console_error | Failed to fetch containers: Error: HTTP 429: Too Many Requests     at Hy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async d (http://localhost:3000/assets |
| 46 | `/` | console_error | API Error for /api/v1/stats?period=1h: Error: HTTP 429: Too Many Requests     at Hy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386) |
| 47 | `/` | console_error | Statistics fetch error: Error: HTTP 429: Too Many Requests     at Hy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386) |
| 48 | `/` | console_error | API Error for /api/v1/health/services: Error: HTTP 429: Too Many Requests     at Hy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async Hy.getAllDataSources |
| 49 | `/` | console_error | Failed to fetch data sources: Error: HTTP 429: Too Many Requests     at Hy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async Hy.getAllDataSources (http:// |
| 50 | `/` | console_error | API Error for /api/integrations?limit=100: Error: HTTP 429: Too Many Requests     at jy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async http://localhost |
| 51 | `/` | console_error | Error fetching integrations: Error: HTTP 429: Too Many Requests     at jy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async http://localhost:3000/assets/j |
| 52 | `/` | console_error | API Error for /api/v1/activity: Error: HTTP 429: Too Many Requests     at jy.fetchWithErrorHandling (http://localhost:3000/assets/js/main-B0LzPsfY.js:10:41386)     at async jy.getCurrentActivity (http |
| 53 | `/` | network_fail | HTTP 429: http://localhost:3000/api/v1/alerts/active |
| 54 | `/` | network_fail | HTTP 429: http://localhost:3000/api/devices?limit=1000 |
| 55 | `/` | network_fail | HTTP 429: http://localhost:3000/api/v1/docker/containers |
| 56 | `/` | network_fail | HTTP 429: http://localhost:3000/api/v1/stats?period=1h |
| 57 | `/` | network_fail | HTTP 429: http://localhost:3000/api/v1/health/services |
| 58 | `/` | network_fail | HTTP 429: http://localhost:3000/api/integrations?limit=100 |
| 59 | `/` | network_fail | HTTP 429: http://localhost:3000/api/v1/activity |
| 60 | `/` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 61 | `/` | visible_error | Visible error/warning: ⚠️ |
| 62 | `/` | visible_error | Visible error/warning: DEGRADED PERFORMANCE |

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
