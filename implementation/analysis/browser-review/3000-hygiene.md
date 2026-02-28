# Port 3000 – Device Health (Hygiene) Tab

**URL:** `http://localhost:3000/#hygiene`  
**Title:** HomeIQ Dashboard  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** Device health / hygiene issues (e.g. unavailable entities, duplicate names, naming issues) from admin-api or hygiene API.
- **Key UI:** List of issues with status (open, ignored, resolved); may support filter and actions (ignore, resolve).

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **API** – Uses hygiene endpoints (e.g. HygieneIssueListResponse); if request fails, show error and retry; empty list should be “No issues” not silent failure. |
| 2 | Low | **Ignore/Resolve** – If user can ignore or resolve, ensure IDs and state are persisted and don’t reappear on next load unless still valid. |
| 3 | Low | **Bulk actions** – For many issues, consider “Ignore all of type” or “Resolve all” with confirmation. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Filter | Filter by status (open/ignored/resolved), type, or device. |
| 2 | Link to 3001 | Link to AI Automation UI Name Enhancement or device explorer where relevant. |
| 3 | Accessibility | Table or list with proper headers and row semantics. |

---

## Links from this page

- **Nav:** All dashboard tabs.
