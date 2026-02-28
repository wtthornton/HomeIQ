---
epic: browser-review-health-dashboard
priority: high
status: in-progress
estimated_duration: 2-3 weeks
risk_level: medium
source: implementation/analysis/browser-review/*.md (2026-02-28)
---

# Epic: Browser Review – Health Dashboard Fixes (Port 3000)

**Status:** In Progress (Stories 1-2 Complete)
**Priority:** High (P1)
**Duration:** 2-3 weeks
**Risk Level:** Medium
**Source:** Playwright MCP browser review, Feb 2026
**Affects:** domains/core-platform/health-dashboard

## Context

A Playwright MCP review of http://localhost:3000/ documented issues and enhancements for every tab (Overview, Services, Groups, Dependencies, Configuration, Devices, Events, Data Feeds, Energy, Sports, Alerts, Device Health, Automation Checks, AI Performance, Logs, Analytics). Per-tab details live in `implementation/analysis/browser-review/3000-*.md`.

## Stories

### Story 1: Fix Overview – KPI Loading (Critical)

**Priority:** Critical | **Estimate:** 8h | **Risk:** Medium

**Problem:** Throughput, Latency, and Error Rate often show "Loading…"; only Uptime may display. KPI data source (admin-api/metrics) not responding or slow.

**Files:** OverviewTab, useStatistics, KPI components

**Acceptance Criteria:**
- [x] All four KPIs (Uptime, Throughput, Latency, Error Rate) load and display values when backend is available
- [x] On timeout/failure: show "Unavailable" (orange text) instead of perpetual "Loading…" via `KPIValue` component with 3 states
- [x] Retry button in KPI header bar; `fetchWithTimeout(10s)` in useHealth + useStatistics hooks
- [ ] Status consistency: Overview and Services use same status logic (worst component vs. ingestion-only); document derivation

---

### Story 2: Logs Tab – Secret Sanitization (Security)

**Priority:** Critical | **Estimate:** 6h | **Risk:** High if skipped

**Problem:** Log content must be sanitized (no API keys, tokens, passwords); redact or omit sensitive fields before display.

**Files:** LogsTab, admin-api log endpoint, any log aggregation

**Acceptance Criteria:**
- [x] Log content sanitized: `sanitizeLogMessage()` with 7 regex patterns (Bearer, API keys, Authorization, passwords, connection strings, tokens, secrets)
- [x] No secrets in browser-visible log output — sanitization applied in fetchLogs, searchLogs, and copyLog
- [x] Sanitization rules documented in SECRET_PATTERNS array with inline comments; 11 tests covering all patterns
- [ ] Volume: default to last N lines or short time window; pagination or "Load more"

---

### Story 3: Services & Status Consistency

**Priority:** High | **Estimate:** 6h | **Risk:** Low

**Problem:** DEGRADED PERFORMANCE banner doesn't indicate which service(s) caused it; KPI drill-down links (Throughput, Latency) may not work.

**Acceptance Criteria:**
- [ ] DEGRADED banner lists affected service names or links to them
- [ ] KPI detail links (Throughput, Latency) open meaningful modal or panel
- [ ] Filter services by status (Healthy/Degraded/Unhealthy)
- [ ] Timestamp: "Last updated" shows timezone (e.g. "10:13 PM local") or relative ("Updated 0s ago")

---

### Story 4: Configuration & Data Tabs – Security & UX

**Priority:** High | **Estimate:** 4h | **Risk:** Medium

**Problem:** Configuration tab must never display secrets; Devices, Events, Data Feeds, Energy, Sports need error handling and empty states.

**Acceptance Criteria:**
- [ ] Configuration: No API keys, passwords, tokens; mask or omit; audit all displayed keys
- [ ] Devices/Events: Clear error and retry when API fails; empty state when no data
- [ ] Data Feeds: Health definition documented; "Last successful" time shown
- [ ] Sports: Handle off-season/empty; "No live games" vs. generic error

---

### Story 5: Remaining Tabs – Error Handling & Accessibility

**Priority:** Medium | **Estimate:** 8h | **Risk:** Low

**Problem:** Groups, Dependencies, Alerts, Hygiene, Validation, Evaluation, Analytics need consistent error handling, empty states, and accessibility.

**Acceptance Criteria:**
- [ ] Groups: Empty group state clear; "3/5 healthy" counts
- [ ] Dependencies: Legend and broken-dep highlighting
- [ ] Alerts: Filter by severity; ack/dismiss state persisted
- [ ] Hygiene, Validation, Evaluation: Error handling and empty states
- [ ] Analytics: Bounded queries; empty state; optional table fallback for charts
