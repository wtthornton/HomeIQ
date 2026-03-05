# Port 3001 (AI Automation UI) – Crawl Issues

**Source:** Playwright crawl of all routes  
**Generated:** 2026-03-05
**Base URL:** http://localhost:3001

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 6 |
| High     | 25 |
| Medium   | 0 |
| Low      | 0 |
| **Total** | **31** |

---

## Issues

### Critical

| # | Route | Category | Message |
|---|-------|----------|---------|
| 1 | `/chat` | network_fail | HTTP 503: http://localhost:3001/api/ha-ai-agent/v1/conversations?limit=50 |
| 2 | `/chat` | visible_error | Visible error/warning: Failed to load conversations |
| 3 | `/explore` | network_fail | HTTP 502: http://localhost:3001/api/automation-miner/devices/recommendations?user_devices=light,switch,sensor&limit=10 |
| 4 | `/insights` | network_fail | HTTP 500: http://localhost:3001/api/patterns/stats |
| 5 | `/insights` | network_fail | HTTP 500: http://localhost:3001/api/patterns/list?min_confidence=0.7&limit=100 |
| 6 | `/insights` | network_fail | HTTP 500: http://localhost:3001/api/analysis/status |

### High

| # | Route | Category | Message |
|---|-------|----------|---------|
| 1 | `/chat` | console_error | Failed to load resource: the server responded with a status of 503 (Service Unavailable) |
| 2 | `/chat` | console_error | Failed to load conversations: APIError: Service not ready     at We (http://localhost:3001/assets/index-BHq964gL.js:4139:117609)     at async http://localhost:3001/assets/index-BHq964gL.js:4271:14010 |
| 3 | `/chat` | network_fail | Request failed: http://localhost:3001/api/suggestions/list?limit=50 |
| 4 | `/chat` | network_fail | Request failed: http://localhost:3001/api/suggestions/refresh/status |
| 5 | `/chat` | network_fail | Request failed: http://localhost:3001/api/analysis/status |
| 6 | `/explore` | console_error | Failed to load resource: the server responded with a status of 404 (Not Found) |
| 7 | `/explore` | console_error | Error fetching devices: Error: Failed to fetch entities     at http://localhost:3001/assets/index-BHq964gL.js:4267:2999 |
| 8 | `/explore` | console_error | Failed to load resource: the server responded with a status of 502 (Bad Gateway) |
| 9 | `/explore` | console_error | Error fetching recommendations: Error: Failed to fetch recommendations     at http://localhost:3001/assets/index-BHq964gL.js:4264:55698 |
| 10 | `/explore` | network_fail | HTTP 404: http://localhost:3001/api/entities?limit=10000 |
| 11 | `/insights` | console_error | Failed to load resource: the server responded with a status of 500 (Internal Server Error) |
| 12 | `/insights` | console_error | Failed to load patterns: APIError: Failed to get pattern stats: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "patterns" does not |
| 13 | `/insights` | console_error | Failed to load analysis status: APIError: Failed to get analysis status: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "patterns" |
| 14 | `/insights` | visible_error | Visible error/warning: ✕ |
| 15 | `/settings` | console_error | Failed to load resource: the server responded with a status of 401 (Unauthorized) |
| 16 | `/settings` | console_error | Failed to load resource: the server responded with a status of 404 (Not Found) |
| 17 | `/settings` | network_fail | HTTP 401: http://localhost:3001/api/device-intelligence/team-tracker/status?check=true |
| 18 | `/settings` | network_fail | HTTP 404: http://localhost:3001/api/settings |
| 19 | `/name-enhancement` | console_error | Connecting to 'http://localhost:8019/api/name-enhancement/devices/pending?limit=100' violates the following Content Security Policy directive: "connect-src 'self' ws: wss:". The action has been blocke |
| 20 | `/name-enhancement` | console_error | Fetch API cannot load http://localhost:8019/api/name-enhancement/devices/pending?limit=100. Refused to connect because it violates the document's Content Security Policy. |
| 21 | `/name-enhancement` | console_error | Connecting to 'http://localhost:8019/api/name-enhancement/status' violates the following Content Security Policy directive: "connect-src 'self' ws: wss:". The action has been blocked. |
| 22 | `/name-enhancement` | console_error | Fetch API cannot load http://localhost:8019/api/name-enhancement/status. Refused to connect because it violates the document's Content Security Policy. |
| 23 | `/name-enhancement` | console_error | Failed to load enhancement stats: APIError: Network error: Unable to connect to http://localhost:8019/api/name-enhancement/status. Please check your connection and ensure the server is running.     at |
| 24 | `/name-enhancement` | visible_error | Visible error/warning: ✕ |
| 25 | `/name-enhancement` | visible_error | Visible error/warning: Network error: Unable to connect to http://localhost:8019/api/name-enhancement/devices/pending?limit=100. Please check your connection and ensure the  |
