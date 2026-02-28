# Port 3000 – Energy Tab

**URL:** `http://localhost:3000/#energy`  
**Title:** HomeIQ Dashboard  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** Energy-related metrics, correlation, or forecasts (e.g. from energy-correlator, energy-forecasting, smart meter data).
- **Key UI:** Charts or cards for consumption, cost, trends; may link to Energy Analytics services.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **Data dependency** – Depends on energy services (8015, 8016) and possibly data-api; if unavailable, show clear “Energy data unavailable” and which service to check. |
| 2 | Low | **Charts** – Ensure charts are accessible (labels, legend, optional table view); time range consistent with rest of app. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Clarity | Short description of what “energy” includes (e.g. smart meter, solar, cost). |
| 2 | Links | Link to Energy services in Services or Groups tab. |

---

## Links from this page

- **Nav:** All dashboard tabs.
