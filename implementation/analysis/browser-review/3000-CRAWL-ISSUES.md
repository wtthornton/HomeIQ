# Port 3000 (Health Dashboard) – Crawl Issues

**Source:** Playwright crawl of all routes  
**Generated:** 2026-03-03
**Base URL:** http://localhost:3000

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 56 |
| Medium   | 1 |
| Low      | 1 |
| **Total** | **58** |

---

## Issues

### High

| # | Route | Category | Message |
|---|-------|----------|---------|
| 1 | `/#overview` | console_error | Failed to load resource: the server responded with a status of 429 (Too Many Requests) |
| 2 | `/#overview` | console_error | API Error for /api/v1/alerts/active: Error: HTTP 429: Too Many Requests     at AdminApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15)     at async fetchAlerts (http:// |
| 3 | `/#overview` | console_error | Failed to fetch alerts: Error: HTTP 429: Too Many Requests     at AdminApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15)     at async fetchAlerts (http://localhost:300 |
| 4 | `/#overview` | console_error | API Error for /api/v1/health/services: Error: HTTP 429: Too Many Requests     at AdminApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15)     at async AdminApiClient.get |
| 5 | `/#overview` | console_error | Failed to fetch data sources: Error: HTTP 429: Too Many Requests     at AdminApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15)     at async AdminApiClient.getAllDataSo |
| 6 | `/#overview` | console_error | API Error for /api/v1/stats?period=1h: Error: HTTP 429: Too Many Requests     at AdminApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15) |
| 7 | `/#overview` | console_error | Statistics fetch error: Error: HTTP 429: Too Many Requests     at AdminApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15) |
| 8 | `/#overview` | console_error | API Error for /api/devices?limit=1000: Error: HTTP 429: Too Many Requests     at DataApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15)     at async http://localhost:30 |
| 9 | `/#overview` | console_error | Error fetching devices: Error: HTTP 429: Too Many Requests     at DataApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15)     at async http://localhost:3000/src/hooks/us |
| 10 | `/#overview` | console_error | API Error for /api/v1/docker/containers: Error: HTTP 429: Too Many Requests     at AdminApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15)     at async fetchContainers  |
| 11 | `/#overview` | console_error | Failed to fetch containers: Error: HTTP 429: Too Many Requests     at AdminApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15)     at async fetchContainers (http://local |
| 12 | `/#overview` | console_error | API Error for /api/entities?limit=10000: Error: HTTP 429: Too Many Requests     at DataApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15)     at async http://localhost: |
| 13 | `/#overview` | console_error | Error fetching entities: Error: HTTP 429: Too Many Requests     at DataApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15)     at async http://localhost:3000/src/hooks/u |
| 14 | `/#overview` | console_error | API Error for /api/integrations?limit=100: Error: HTTP 429: Too Many Requests     at DataApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15)     at async http://localhos |
| 15 | `/#overview` | console_error | Error fetching integrations: Error: HTTP 429: Too Many Requests     at DataApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15)     at async http://localhost:3000/src/hoo |
| 16 | `/#overview` | console_error | API Error for /api/v1/activity: Error: HTTP 429: Too Many Requests     at DataApiClient.fetchWithErrorHandling (http://localhost:3000/src/services/api.ts:84:15)     at async DataApiClient.getCurrentAc |
| 17 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/v1/alerts/active |
| 18 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/v1/health/services |
| 19 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/v1/stats?period=1h |
| 20 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/devices?limit=1000 |
| 21 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/v1/docker/containers |
| 22 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/entities?limit=10000 |
| 23 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/integrations?limit=100 |
| 24 | `/#overview` | network_fail | HTTP 429: http://localhost:3000/api/v1/activity |
| 25 | `/#overview` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 26 | `/#overview` | visible_error | Visible error/warning: ⚠️ |
| 27 | `/#services` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 28 | `/#services` | visible_error | Visible error/warning: ⚠️ |
| 29 | `/#groups` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 30 | `/#groups` | visible_error | Visible error/warning: ⚠️ |
| 31 | `/#dependencies` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 32 | `/#dependencies` | visible_error | Visible error/warning: ⚠️ |
| 33 | `/#configuration` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 34 | `/#configuration` | visible_error | Visible error/warning: ⚠️ |
| 35 | `/#devices` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 36 | `/#devices` | visible_error | Visible error/warning: ⚠️ |
| 37 | `/#events` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 38 | `/#events` | visible_error | Visible error/warning: ⚠️ |
| 39 | `/#data-sources` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 40 | `/#data-sources` | visible_error | Visible error/warning: ⚠️ |
| 41 | `/#energy` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 42 | `/#energy` | visible_error | Visible error/warning: ⚠️ |
| 43 | `/#sports` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 44 | `/#sports` | visible_error | Visible error/warning: ⚠️ |
| 45 | `/#alerts` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 46 | `/#alerts` | visible_error | Visible error/warning: ⚠️ |
| 47 | `/#hygiene` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 48 | `/#hygiene` | visible_error | Visible error/warning: ⚠️ |
| 49 | `/#validation` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 50 | `/#validation` | visible_error | Visible error/warning: ⚠️ |
| 51 | `/#evaluation` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 52 | `/#evaluation` | visible_error | Visible error/warning: ⚠️ |
| 53 | `/#logs` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 54 | `/#logs` | visible_error | Visible error/warning: ⚠️ |
| 55 | `/#analytics` | visible_error | Visible error/warning: HTTP 429: Too Many Requests |
| 56 | `/#analytics` | visible_error | Visible error/warning: ⚠️ |

### Medium

| # | Route | Category | Message |
|---|-------|----------|---------|
| 1 | `/#overview` | console_warn | Security warning: VITE_API_KEY is set via environment variable and will be embedded in the client bundle. This is insecure for production. Use session-based auth or nginx proxy auth instead. |

### Low

| # | Route | Category | Message |
|---|-------|----------|---------|
| 1 | `/` | network_fail | Navigation failed or timed out: http://localhost:3000/ |
