# Port 3000 – Overview Tab

**URL:** `http://localhost:3000/#overview`  
**Title:** HomeIQ Dashboard - AI-Powered Home Assistant Intelligence & Monitoring  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** High-level system status and KPIs.
- **Key UI:** Status banner (e.g. “ALL SYSTEMS OPERATIONAL” or “DEGRADED PERFORMANCE”), “Last updated” time, Key Performance Indicators (Uptime, Throughput, Latency, Error Rate), Core System Components (e.g. INGESTION – WebSocket Connection – Healthy). Header: hamburger menu, title, dark mode toggle, refresh.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | **High** | **KPI loading** – Throughput, Latency, and Error Rate often show “Loading…” with three dots; only Uptime may show a value. Suggests KPI data source (admin-api or metrics) not responding or slow; users cannot assess health at a glance. |
| 2 | Medium | **Status inconsistency** – Overview can show “ALL SYSTEMS OPERATIONAL” while Services tab shows “DEGRADED PERFORMANCE”; clarify how overall status is derived (e.g. worst component vs. ingestion-only). |
| 3 | Medium | **Last updated** – Timestamp (e.g. “10:13:27 PM”) doesn’t indicate timezone; could be server or local – should be explicit for on-call. |
| 4 | Low | **Core components** – Only INGESTION visible in viewport; expand/collapse or scroll needed for other components; ensure all critical components are visible or clearly listed. |
| 5 | Low | **Refresh** – No loading indicator on refresh; user may click again thinking it didn’t work. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | KPI fallback | If KPI request fails or times out, show “Unavailable” or “Check backend” instead of perpetual “Loading…”; add retry or link to Services. |
| 2 | Status logic | Document and optionally show how overall status is computed (e.g. “Based on ingestion + data-api”); align Overview and Services messaging. |
| 3 | Timestamp | Use “Last updated: 10:13 PM local” or ISO with timezone; consider relative “Updated 0s ago.” |
| 4 | Accessibility | Status banner and KPI cards should have proper headings and live region for updates; ensure color isn’t the only indicator (e.g. “Healthy” text + icon). |
| 5 | Refresh UX | Disable or show spinner on refresh button while request is in flight; optional auto-refresh interval with pause control. |

---

## Links from this page

- **Header:** Hamburger (sidebar), Dark mode, Refresh.
- **Nav:** Overview (current), Services, Groups, Dependencies, Configuration, Devices, Events, Data Feeds, Energy, Sports, Alerts, Device Health, Automation Checks, AI Performance, Logs, Analytics.

Fix **issue #1** (KPI loading) so Overview is a reliable at-a-glance health view.
