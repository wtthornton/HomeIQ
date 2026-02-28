# Port 3000 – Groups Tab

**URL:** `http://localhost:3000/#groups`  
**Title:** HomeIQ Dashboard  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** View services grouped by category (e.g. Core Platform, Data Collectors, Energy Analytics, Blueprints, Pattern Analysis, Device Management, ML Engine).
- **Key UI:** Group cards or sections with aggregate status (e.g. Healthy/Degraded/Empty); expand to see member services and ports.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **Group status** – Aggregate status (e.g. “Degraded” when one service in group is down) must be correct; ensure logic matches Overview and Services. |
| 2 | Medium | **Empty groups** – If a group has no services or all unknown, “Empty” or “No services” state should be clear so it’s not mistaken for a loading failure. |
| 3 | Low | **Expand/collapse** – State (expanded/collapsed) should be keyboard accessible and persist during session if desired. |
| 4 | Low | **Port in list** – Same as Services: optional hide of port in production if needed. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Drill-down | Clicking a group could filter Services tab or expand in place to show service list with links to service detail. |
| 2 | Counts | Show “3/5 healthy” or “2 degraded” per group for quick scan. |
| 3 | Accessibility | Group headings and status must be announced; use aria-expanded for expandable sections. |

---

## Links from this page

- **Nav:** All dashboard tabs.
- **In-page:** Group headers, expand to see services.
