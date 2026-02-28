# Port 3000 – Dependencies Tab

**URL:** `http://localhost:3000/#dependencies`  
**Title:** HomeIQ Dashboard  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** Show dependency graph or list between services (e.g. websocket-ingestion → InfluxDB, data-api → InfluxDB).
- **Key UI:** Likely a graph or table of “Service A depends on Service B”; may show health of dependency chain.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **Data source** – If dependencies are hardcoded or static, they may drift from actual topology; consider deriving from config or runtime where possible. |
| 2 | Low | **Graph UX** – If rendered as a graph, ensure it’s readable (zoom, pan, legend) and doesn’t overwhelm on large deployments. |
| 3 | Low | **Broken deps** – If a dependency is down, highlight the dependent service and the broken link. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Clarity | Legend for edge meaning (e.g. “calls,” “writes to”); color or icon for healthy vs. broken dependency. |
| 2 | Accessibility | Provide table or list view as alternative to graph for screen readers. |

---

## Links from this page

- **Nav:** All dashboard tabs.
