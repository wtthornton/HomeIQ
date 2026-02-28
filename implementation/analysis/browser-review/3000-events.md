# Port 3000 – Events Tab

**URL:** `http://localhost:3000/#events`  
**Title:** HomeIQ Dashboard  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** View recent or filtered Home Assistant / InfluxDB events (state changes, triggers).
- **Key UI:** Table or timeline of events with time, entity_id, state, attributes; may support time range and filter.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **Data volume** – Event streams can be large; default to last N minutes or capped results; avoid loading thousands of rows at once. |
| 2 | Medium | **Time range** – Ensure time picker or preset (1h, 24h, 7d) is clear and timezone is consistent with rest of dashboard. |
| 3 | Low | **Empty state** – If no events in range, show “No events in selected period” and suggest widening range or checking ingestion. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Filter | Filter by entity_id, domain, state; optional search. |
| 2 | Export | Optional export (CSV/JSON) for selected range. |
| 3 | Live tail | Optional auto-refresh or “Live” mode for recent events (with pause). |

---

## Links from this page

- **Nav:** All dashboard tabs.
- **Possible:** Link to Devices or Data Feeds.
