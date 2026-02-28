# Port 3000 – Analytics Tab

**URL:** `http://localhost:3000/#analytics`  
**Title:** HomeIQ Dashboard  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** Analytics views (e.g. event volume, latency distribution, usage over time) from InfluxDB or admin-api.
- **Key UI:** Charts (time series, histograms); may support time range and metric selection.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **Data source** – Ensure analytics queries are bounded (time range, limit); avoid full table scans or timeouts. |
| 2 | Low | **Empty state** – If no data in range, show “No data in selected period” and suggest different range or check ingestion. |
| 3 | Low | **Performance** – Heavy charts can slow the tab; consider lazy load or simplified view by default. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Time range | Presets (1h, 24h, 7d, 30d) and custom range with clear timezone. |
| 2 | Export | Optional export of chart data (CSV/JSON). |
| 3 | Accessibility | Chart titles and axis labels; optional data table for screen readers. |

---

## Links from this page

- **Nav:** All dashboard tabs.
