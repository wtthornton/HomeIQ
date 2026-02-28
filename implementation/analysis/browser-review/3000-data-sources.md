# Port 3000 – Data Feeds Tab

**URL:** `http://localhost:3000/#data-sources`  
**Title:** HomeIQ Dashboard  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** Status and metrics of data sources (e.g. Home Assistant, Weather, Sports, Energy, InfluxDB).
- **Key UI:** Cards or table per data source with health, last successful fetch, error count, optional config or link to service.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **Health definition** – Each source (sports, weather, etc.) may have different health logic; document and ensure “Healthy” means data is flowing. |
| 2 | Low | **Stale data** – Show “Last successful: &lt;time&gt;” so users can tell if a source stopped updating. |
| 3 | Low | **Errors** – If a source has recent errors, show count or last error message without exposing sensitive detail. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Drill-down | Link to Services tab for the backing service of each source. |
| 2 | Accessibility | Each source card has a heading and status; use aria-live if status updates. |

---

## Links from this page

- **Nav:** All dashboard tabs.
