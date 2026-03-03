# Port 3001 (AI Automation UI) – Crawl Issues

**Source:** Playwright crawl of all routes  
**Generated:** 2026-03-03
**Base URL:** http://localhost:3001

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 6 |
| High     | 30 |
| Medium   | 0 |
| Low      | 0 |
| **Total** | **36** |

---

## Issues

### Critical

| # | Route | Category | Message |
|---|-------|----------|---------|
| 1 | `/` | network_fail | HTTP 500: http://localhost:3001/api/analysis/status |
| 2 | `/explore` | network_fail | HTTP 502: http://localhost:3001/api/automation-miner/devices/recommendations?user_devices=light,switch,sensor&limit=10 |
| 3 | `/insights` | network_fail | HTTP 500: http://localhost:3001/api/analysis/status |
| 4 | `/insights` | network_fail | HTTP 500: http://localhost:3001/api/patterns/list?min_confidence=0.7&limit=100 |
| 5 | `/insights` | network_fail | HTTP 500: http://localhost:3001/api/patterns/stats |
| 6 | `/insights` | visible_error | Visible error/warning: Failed to list patterns: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "pattern |

### High

| # | Route | Category | Message |
|---|-------|----------|---------|
| 1 | `/` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 2 | `/` | console_error | Failed to load resource: the server responded with a status of 500 (Internal Server Error) |
| 3 | `/chat` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 4 | `/explore` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 5 | `/explore` | console_error | Failed to load resource: the server responded with a status of 404 (Not Found) |
| 6 | `/explore` | console_error | Error fetching devices: Error: Failed to fetch entities     at http://localhost:3001/assets/index-58gjuWag.js:4357:2964 |
| 7 | `/explore` | console_error | Failed to load resource: the server responded with a status of 502 (Bad Gateway) |
| 8 | `/explore` | console_error | Error fetching recommendations: Error: Failed to fetch recommendations     at http://localhost:3001/assets/index-58gjuWag.js:4354:56134 |
| 9 | `/explore` | network_fail | HTTP 404: http://localhost:3001/api/entities?limit=10000 |
| 10 | `/insights` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 11 | `/insights` | console_error | Failed to load resource: the server responded with a status of 500 (Internal Server Error) |
| 12 | `/insights` | console_error | Failed to load analysis status: APIError: Failed to get analysis status: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "patterns" |
| 13 | `/insights` | console_error | Failed to load patterns: APIError: Failed to list patterns: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "patterns" does not exi |
| 14 | `/insights` | visible_error | Visible error/warning: ✕ |
| 15 | `/automations` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 16 | `/settings` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 17 | `/settings` | console_error | Failed to load resource: the server responded with a status of 404 (Not Found) |
| 18 | `/settings` | console_error | Failed to load resource: the server responded with a status of 401 (Unauthorized) |
| 19 | `/settings` | network_fail | HTTP 404: http://localhost:3001/api/settings |
| 20 | `/settings` | network_fail | HTTP 401: http://localhost:3001/api/device-intelligence/team-tracker/status |
| 21 | `/name-enhancement` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 22 | `/name-enhancement` | console_error | Refused to connect to 'http://localhost:8019/api/name-enhancement/devices/pending?limit=100' because it violates the following Content Security Policy directive: "connect-src 'self' ws: wss:".  |
| 23 | `/name-enhancement` | console_error | Fetch API cannot load http://localhost:8019/api/name-enhancement/devices/pending?limit=100. Refused to connect because it violates the document's Content Security Policy. |
| 24 | `/name-enhancement` | console_error | Refused to connect to 'http://localhost:8019/api/name-enhancement/status' because it violates the following Content Security Policy directive: "connect-src 'self' ws: wss:".  |
| 25 | `/name-enhancement` | console_error | Fetch API cannot load http://localhost:8019/api/name-enhancement/status. Refused to connect because it violates the document's Content Security Policy. |
| 26 | `/name-enhancement` | console_error | Failed to load enhancement stats: APIError: Network error: Unable to connect to http://localhost:8019/api/name-enhancement/status. Please check your connection and ensure the server is running.     at |
| 27 | `/name-enhancement` | visible_error | Visible error/warning: ✕ |
| 28 | `/name-enhancement` | visible_error | Visible error/warning: Network error: Unable to connect to http://localhost:8019/api/name-enhancement/devices/pending?limit=100. Please check your connection and ensure the  |
| 29 | `/?source=blueprints` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
| 30 | `/?source=context` | console_error | [api-client] VITE_API_KEY is not set. API requests may fail with 401. Set VITE_API_KEY at build time for production. |
