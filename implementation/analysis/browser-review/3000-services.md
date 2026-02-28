# Port 3000 – Services Tab

**URL:** `http://localhost:3000/#services`  
**Title:** HomeIQ Dashboard - AI-Powered Home Assistant Intelligence & Monitoring  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** List and status of services (e.g. WebSocket Ingestion, AI Automation Service, Admin API, Health Dashboard, InfluxDB, Weather API, Sports API, etc.) with health status and optional details.
- **Key UI:** Status banner (e.g. DEGRADED PERFORMANCE), KPIs, Core System Components; Services tab shows service cards with name, icon, port, status (Healthy/Degraded/Unhealthy). Expand/collapse or click for details.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | **High** | **DEGRADED PERFORMANCE** – When shown, users need to see which service(s) caused it; ensure at least one component is clearly non-Healthy and that the banner links or scrolls to the failing service. |
| 2 | Medium | **KPI drill-down** – Throughput and Latency show blue arrow icons (suggesting detail view); ensure those links work and open a meaningful modal or panel. |
| 3 | Medium | **Service list** – Long list; consider grouping (as in NAV_GROUPS) or filter by status so users can quickly find unhealthy services. |
| 4 | Low | **Port display** – Port numbers (e.g. 8001, 3000) are shown; ensure this doesn’t expose internal topology inappropriately in shared screens; consider “Internal” or hide in production. |
| 5 | Low | **Refresh scope** – Clarify whether refresh re-fetches all services or only overview; if partial, show “Refreshing…” per section. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Degradation detail | On DEGRADED, list affected service names in the banner or in an expandable section; link to corresponding service card. |
| 2 | Filter/sort | Filter by status (Healthy/Degraded/Unhealthy) and optionally by group (Core, External, etc.). |
| 3 | Service details | Ensure “View details” or expand shows logs, metrics, or last error so on-call can debug without leaving the dashboard. |
| 4 | Accessibility | Service cards should have headings and status announced (e.g. “WebSocket Ingestion, Healthy”); use aria-live for status changes. |
| 5 | Empty/error | If service list fails to load, show error message and retry instead of empty list. |

---

## Links from this page

- **Nav:** All dashboard tabs (Overview, Groups, Dependencies, Configuration, Devices, Events, etc.).
- **Actions:** Refresh, expand/collapse components, KPI detail links.

Prioritize **issue #1** so degraded state is actionable.
