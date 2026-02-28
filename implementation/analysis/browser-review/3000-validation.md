# Port 3000 – Automation Checks (Validation) Tab

**URL:** `http://localhost:3000/#validation`  
**Title:** HomeIQ Dashboard  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** Automation validation results (e.g. YAML checks, entity references, trigger/action validation) from api-automation-edge or validation service.
- **Key UI:** List of automations with pass/fail or list of issues; may link to automation spec or code.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **Data source** – Validation may come from AI automation service or automation edge; if unavailable, show “Validation unavailable” and which service. |
| 2 | Low | **Scope** – Clarify whether this is “all automations” or “automations known to HomeIQ”; link to 3001 Automations page if relevant. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Detail | Clicking an item shows rule snippet and failing check (e.g. “Entity sensor.x not found”). |
| 2 | Refresh | Button to re-run validation or show “Last run: &lt;time&gt;.” |
| 3 | Accessibility | Table or list with status and description for each row. |

---

## Links from this page

- **Nav:** All dashboard tabs.
