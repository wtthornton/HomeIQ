# Port 3000 – Devices Tab

**URL:** `http://localhost:3000/#devices`  
**Title:** HomeIQ Dashboard  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** List devices (from data-api / Home Assistant) with status, area, and possibly last seen.
- **Key UI:** Table or cards of devices; may support search, filter by area/domain, and link to device detail or events.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **Data source** – Uses data-api (port 8006); if API fails, show error and retry; avoid empty table with no message. |
| 2 | Medium | **Large lists** – If many devices, add pagination or virtual scroll; ensure performance doesn’t degrade. |
| 3 | Low | **Last seen** – Timezone and “stale” threshold (e.g. device offline if no event in 24h) should be consistent and documented. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Filter/search | Filter by name, area, domain; search by device_id or friendly name. |
| 2 | Export | Optional CSV/JSON export for device list. |
| 3 | Accessibility | Table should have proper headers and scope; sortable columns with aria-sort. |

---

## Links from this page

- **Nav:** All dashboard tabs.
- **Possible:** Link to Events or Device Health for a given device.
