# Port 3000 – Alerts Tab

**URL:** `http://localhost:3000/#alerts`  
**Title:** HomeIQ Dashboard  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** Active alerts or notifications (e.g. service down, threshold breached, hygiene issues).
- **Key UI:** List or cards of alerts with severity, message, time, optional acknowledge/dismiss; may integrate with AlertBanner or admin-api.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **Source of truth** – Alerts may come from multiple sources (admin-api, hygiene, validation); ensure no duplicate or stale alerts; show “Source” if useful. |
| 2 | Medium | **Empty vs. loading** – Distinguish “No active alerts” from “Alerts loading” or “Failed to load alerts.” |
| 3 | Low | **Ack/dismiss** – If alerts can be acknowledged, ensure state is persisted and reflected in Overview/Services where relevant. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Severity | Use color + icon + text (e.g. “Critical”, “Warning”) so not relying on color alone. |
| 2 | Filter | Filter by severity or source; optional “Resolved” view. |
| 3 | Accessibility | Each alert has a heading and role=alert or aria-live for new alerts. |

---

## Links from this page

- **Nav:** All dashboard tabs.
- **Possible:** Link to Hygiene, Validation, or specific service from alert.
