# Port 3001 – Ideas Page

**URL:** `http://localhost:3001/`  
**Title:** Ideas - HomeIQ  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** AI-generated automation ideas from multiple sources (From Your Data, From Context, From Blueprints).
- **Key UI:** Source tabs, Automation Suggestions card (with count and Refresh), status filters (New / Editing / Ready / Deployed), “New!” natural-language editing card.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | **Critical** | **Failed to load suggestions** – Red error card: “Failed to list suggestions. Check server logs for details.” Core feature (suggestions list) is broken; backend/API or connectivity to suggestion service (e.g. proactive/agent) likely failing. |
| 2 | High | **0 suggestions** across all status filters (New, Editing, Ready, Deployed) – Either no data or a consequence of issue #1. Users cannot evaluate the suggestions workflow until loading succeeds. |
| 3 | Medium | **Refresh Suggestions** – No clear loading state or success/error feedback when clicked; if the API still fails, user gets no inline explanation. |
| 4 | Low | **Empty state** – When there are 0 suggestions, no empty-state copy (e.g. “No suggestions yet – we’ll suggest automations based on your data”) to set expectations. |
| 5 | Low | **Source tabs** – “From Context” and “From Blueprints” were not fully exercised with real data; behavior when backend is unavailable is unknown (same error vs. different messaging). |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Error handling | Show a retry button and/or “Check connection” in the error card; link to Settings or docs if API key/config might be wrong. |
| 2 | Loading | Add skeleton or spinner for the suggestions list and for “Refresh Suggestions”; disable Refresh while a request is in flight. |
| 3 | Empty state | When count is 0 and there is no error, show short copy explaining how suggestions are generated and when to expect them. |
| 4 | Accessibility | Ensure source tabs and status filters have clear focus styles and aria-current/aria-selected where appropriate. |
| 5 | Telemetry | Log suggestion load success/failure and filter usage to prioritize backend fixes and UX. |

---

## Links from this page

- **In-app:** Chat, Insights, Automations, Settings (bottom nav); Ideas is current.
- **Sub-views:** Same route with `?source=context` or `?source=blueprints` (From Context, From Blueprints).

Fix **issue #1** first so the rest of the Ideas flow can be tested and refined.
