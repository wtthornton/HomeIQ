# HomeIQ Issues Tracker

**Created:** 2025-11-15
**Total Issues:** 12
**Status:** All Open

---

## Issue Index

All issues are currently in **Open** status and marked as **Critical** priority.

| # | Issue | Service | Priority | Key Labels |
|---|-------|---------|----------|------------|
| [001](001-websocket-ingestion-critical-issues.md) | WebSocket Ingestion Service - Multiple Critical Issues | websocket-ingestion | Critical | reliability, security, performance |
| [002](002-data-api-critical-issues.md) | Data API Service - Security Vulnerabilities and Resource Leaks | data-api | Critical | security, injection |
| [003](003-ai-automation-service-critical-issues.md) | AI Automation Service - Security Vulnerabilities | ai-automation-service | Critical | security, authentication |
| [004](004-admin-api-critical-issues.md) | Admin API Service - Authentication Bypass and Security Vulnerabilities | admin-api | Critical | security, authentication |
| [005](005-ai-core-service-critical-issues.md) | AI Core Service - Security and Reliability Issues | ai-core-service | Critical | security, reliability |
| [006](006-ml-service-critical-issues.md) | ML Service - Memory Leaks and Security Vulnerabilities | ml-service | Critical | memory-leak, security |
| [007](007-device-intelligence-service-critical-issues.md) | Device Intelligence Service - Code Errors and Resource Leaks | device-intelligence-service | Critical | bug, reliability |
| [008](008-openvino-service-critical-issues.md) | OpenVINO Service - Race Conditions and Memory Management Issues | openvino-service | Critical | race-condition, memory-leak |
| [009](009-weather-api-critical-issues.md) | Weather API Service - Blocking I/O and Silent Failures | weather-api | Critical | performance, reliability |
| [010](010-health-dashboard-critical-issues.md) | Health Dashboard - Deployment Blockers and Security Issues | health-dashboard | Critical | deployment, security |
| [011](011-energy-correlator-critical-issues.md) | Energy Correlator Service - N+1 Query Problem and Performance Issues | energy-correlator | Critical | performance, n+1-query |
| [012](012-ai-code-executor-critical-issues.md) | AI Code Executor Service - Multiple Security Vulnerabilities | ai-code-executor | Critical | security, sandbox-escape, **do-not-deploy** |

---

## Issues by Category

### 🔐 Security (8 issues)
- [002](002-data-api-critical-issues.md) - Flux injection vulnerabilities
- [003](003-ai-automation-service-critical-issues.md) - No authentication, safety bypass
- [004](004-admin-api-critical-issues.md) - Authentication bypass
- [005](005-ai-core-service-critical-issues.md) - No auth, CORS misconfiguration
- [006](006-ml-service-critical-issues.md) - No input validation, DoS
- [010](010-health-dashboard-critical-issues.md) - Token exposure, deployment blockers
- [012](012-ai-code-executor-critical-issues.md) - **⚠️ DO NOT DEPLOY** - Sandbox escape

### ⚡ Performance (4 issues)
- [001](001-websocket-ingestion-critical-issues.md) - Memory growth, lock contention
- [009](009-weather-api-critical-issues.md) - Blocking I/O in async
- [011](011-energy-correlator-critical-issues.md) - N+1 query explosion

### 💾 Memory Leaks (3 issues)
- [006](006-ml-service-critical-issues.md) - StandardScaler state accumulation
- [008](008-openvino-service-critical-issues.md) - Model cleanup, race conditions

### 🐛 Code Errors (2 issues)
- [001](001-websocket-ingestion-critical-issues.md) - Entity deletion crash
- [007](007-device-intelligence-service-critical-issues.md) - Missing imports, incorrect async

### 🚀 Deployment Blockers (2 issues)
- [001](001-websocket-ingestion-critical-issues.md) - Missing dependency
- [010](010-health-dashboard-critical-issues.md) - Hardcoded localhost URLs

---

## Priority Actions

### IMMEDIATE (Will cause crashes/failures)
1. **[001]** Fix entity deletion crash in websocket-ingestion
2. **[001]** Add missing InfluxDB dependency
3. **[007]** Fix missing `bindparam` import in device-intelligence
4. **[010]** Fix hardcoded localhost URLs in health-dashboard
5. **[012]** DO NOT DEPLOY ai-code-executor (12 security flaws)

### URGENT (Security vulnerabilities)
1. **[002]** Fix Flux injection in data-api (15+ locations)
2. **[003]** Add authentication to ai-automation-service
3. **[004]** Fix authentication bypass in admin-api
4. **[005]** Add authentication to ai-core-service
5. **[006]** Add input validation to ml-service

### HIGH (Performance/Reliability)
1. **[011]** Fix N+1 query explosion in energy-correlator
2. **[008]** Fix race conditions in openvino-service
3. **[006]** Fix memory leaks in ml-service
4. **[009]** Fix blocking I/O in weather-api

---

## Issue File Format

Each issue file contains:
- **Frontmatter metadata** (YAML)
  - `status`: Current status (Open/In Progress/Closed)
  - `priority`: Priority level (Critical/High/Medium/Low)
  - `service`: Affected service name
  - `created`: Date created
  - `labels`: Categorization tags
- **Issue title**
- **Overview** - Summary of issues found
- **Detailed findings** - Specific issues with locations, severity, impact, and fixes
- **Recommended actions** - Prioritized action items
- **References** - Related documentation and service info

---

## How to Update Issue Status

To mark an issue as resolved:

1. Open the issue file (e.g., `001-websocket-ingestion-critical-issues.md`)
2. Update the frontmatter:
   ```yaml
   ---
   status: Closed
   priority: Critical
   service: websocket-ingestion
   created: 2025-11-15
   resolved: 2025-11-XX
   labels: [critical, reliability, security, performance]
   ---
   ```
3. Add resolution notes at the end of the file
4. Commit the changes

---

## Statistics

**Total Issues:** 12
**Open:** 12
**In Progress:** 0
**Closed:** 0

**By Priority:**
- Critical: 12
- High: 0
- Medium: 0
- Low: 0

**By Service Type:**
- Core Services: 3 (websocket-ingestion, data-api, admin-api)
- AI Services: 5 (ai-automation, ai-core, ml-service, openvino, ai-code-executor)
- Infrastructure: 2 (device-intelligence, energy-correlator)
- Frontend: 1 (health-dashboard)
- Data Enrichment: 1 (weather-api)

---

## References

- **Source Analysis:** `.github-issues/` directory
- **CLAUDE.md:** HomeIQ coding standards and patterns
- **Service Documentation:** `docs/api/API_REFERENCE.md`

**Note:** Use 2025 patterns, architecture and versions for decisions and ensure the Readme files are up to date.
