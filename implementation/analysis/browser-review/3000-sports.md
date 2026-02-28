# Port 3000 – Sports Tab

**URL:** `http://localhost:3000/#sports`  
**Title:** HomeIQ Dashboard  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** Sports data status (e.g. Team Tracker, live games, scores) from sports-api or data-api sports endpoints.
- **Key UI:** Live games, scores, or status of sports integration; may show last sync or health of sports data source.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **API** – Sports data may come from data-api (proxy) or sports-api (8005); if both exist, clarify which this tab uses; handle 503 or empty gracefully. |
| 2 | Low | **Empty season** – Off-season or no configured teams can yield empty state; show “No live games” or “Configure Team Tracker” instead of generic error. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | UX | Link to Team Tracker / HA config or to implementation docs (e.g. superbowl_teamtracker_lights_guide) if relevant. |
| 2 | Accessibility | Scores and team names in structured format for screen readers. |

---

## Links from this page

- **Nav:** All dashboard tabs.
