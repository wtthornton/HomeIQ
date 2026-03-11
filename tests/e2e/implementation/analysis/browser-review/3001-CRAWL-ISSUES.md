# Port 3001 (AI Automation UI) -- Crawl Issues

**Source:** Playwright crawl of all routes
**Generated:** 2026-03-11
**Base URL:** http://localhost:3001

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 7 |
| High     | 32 |
| Medium   | 0 |
| Low      | 0 |
| **Total** | **39** |

---

## Issues

### Critical

| # | Route | Category | Message |
|---|-------|----------|---------|
| 1 | `/` | network_fail | HTTP 500: http://localhost:3001/api/analysis/status |
| 2 | `/chat` | network_fail | HTTP 503: http://localhost:3001/api/ha-ai-agent/v1/conversations?limit=50 |
| 3 | `/chat` | visible_error | Visible error/warning: Failed to load conversations |
| 4 | `/explore` | network_fail | HTTP 502: http://localhost:3001/api/automation-miner/devices/recommendations?user_devices=light,switch,sensor&limit=10 |
| 5 | `/insights` | network_fail | HTTP 500: http://localhost:3001/api/patterns/stats |
| 6 | `/insights` | network_fail | HTTP 500: http://localhost:3001/api/patterns/list?min_confidence=0.7&limit=100 |
| 7 | `/insights` | network_fail | HTTP 500: http://localhost:3001/api/analysis/status |

### High

| # | Route | Category | Message |
|---|-------|----------|---------|
| 1 | `/` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 2 | `/` | console_error | Failed to load resource: the server responded with a status of 500 (Internal Server Error) |
| 3 | `/chat` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 4 | `/chat` | console_error | Failed to load resource: the server responded with a status of 503 (Service Unavailable) |
| 5 | `/chat` | console_error | Failed to load conversations: APIError: Service not ready     at We (http://localhost:3001/assets/index-CRw92fyF.js:4139:117670)     at async http://localhost:3001/assets/index-CRw92fyF.js:4271:14010 |
| 6 | `/explore` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 7 | `/explore` | console_error | Failed to load resource: the server responded with a status of 404 (Not Found) |
| 8 | `/explore` | console_error | Error fetching devices: Error: Failed to fetch entities     at http://localhost:3001/assets/index-CRw92fyF.js:4267:2956 |
| 9 | `/explore` | console_error | Failed to load resource: the server responded with a status of 502 (Bad Gateway) |
| 10 | `/explore` | console_error | Error fetching recommendations: Error: Failed to fetch recommendations     at http://localhost:3001/assets/index-CRw92fyF.js:4264:55577 |
| 11 | `/explore` | network_fail | HTTP 404: http://localhost:3001/api/entities?limit=10000 |
| 12 | `/insights` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 13 | `/insights` | console_error | Failed to load resource: the server responded with a status of 500 (Internal Server Error) |
| 14 | `/insights` | console_error | Failed to load patterns: APIError: Failed to get pattern stats: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "patterns" does not |
| 15 | `/insights` | console_error | Failed to load analysis status: APIError: Failed to get analysis status: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "patterns" |
| 16 | `/insights` | visible_error | Visible error/warning: ✕ |
| 17 | `/automations` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 18 | `/settings` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 19 | `/settings` | console_error | Failed to load resource: the server responded with a status of 401 (Unauthorized) |
| 20 | `/settings` | console_error | Failed to load resource: the server responded with a status of 404 (Not Found) |
| 21 | `/settings` | network_fail | HTTP 401: http://localhost:3001/api/device-intelligence/team-tracker/status?check=true |
| 22 | `/settings` | network_fail | HTTP 404: http://localhost:3001/api/settings |
| 23 | `/name-enhancement` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 24 | `/name-enhancement` | console_error | Connecting to 'http://localhost:8019/api/name-enhancement/devices/pending?limit=100' violates the following Content Security Policy directive: "connect-src 'self' ws: wss:". The action has been blocke |
| 25 | `/name-enhancement` | console_error | Fetch API cannot load http://localhost:8019/api/name-enhancement/devices/pending?limit=100. Refused to connect because it violates the document's Content Security Policy. |
| 26 | `/name-enhancement` | console_error | Connecting to 'http://localhost:8019/api/name-enhancement/status' violates the following Content Security Policy directive: "connect-src 'self' ws: wss:". The action has been blocked. |
| 27 | `/name-enhancement` | console_error | Fetch API cannot load http://localhost:8019/api/name-enhancement/status. Refused to connect because it violates the document's Content Security Policy. |
| 28 | `/name-enhancement` | console_error | Failed to load enhancement stats: APIError: Network error: Unable to connect to http://localhost:8019/api/name-enhancement/status. Please check your connection and ensure the server is running.     at |
| 29 | `/name-enhancement` | visible_error | Visible error/warning: ✕ |
| 30 | `/name-enhancement` | visible_error | Visible error/warning: Network error: Unable to connect to http://localhost:8019/api/name-enhancement/devices/pending?limit=100. Please check your connection and ensure the  |
| 31 | `/?source=blueprints` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 32 | `/?source=context` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
