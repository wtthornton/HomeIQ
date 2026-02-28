# Port 3001 – Insights Page

**URL:** `http://localhost:3001/insights`  
**Title:** Insights - HomeIQ  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** ML-detected patterns and cross-device opportunities.
- **Key UI:** Sub-tabs – Usage Patterns (default), Device Connections, Room View. Patterns view shows “Detected Patterns” with “What Are Patterns?” and “Why Patterns Matter” content; Connections and Room View use the Synergies component.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **Patterns content** – “Past 30 days” is stated; if no events exist, no empty state or “Run analysis first” message was verified; ensure patterns view handles no-data gracefully. |
| 2 | Medium | **Device Connections / Room View** – Both render the same Synergies component; different labels suggest different visualizations or filters. Confirm that switching tabs actually changes content or filters; if not, consider merging or clarifying. |
| 3 | Low | **Tab semantics** – Sub-tabs (Usage Patterns, Device Connections, Room View) should use aria-selected/aria-current and keyboard navigation (arrow keys) for consistency with Sidebar. |
| 4 | Low | **Long copy** – “Why Patterns Matter” bullet list is dense; consider progressive disclosure or shorter summary with expand for detail. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Empty state | When no patterns exist, show “No patterns yet” with short explanation (e.g. “We need at least 30 days of events”) and link to Events or Data Feeds if relevant. |
| 2 | Synergies | Differentiate Device Connections vs. Room View (e.g. by filter, layout, or data slice) so the two tabs feel distinct. |
| 3 | Accessibility | Ensure sub-tab strip is a tablist with proper roles and focus management; heading hierarchy (h1 Insights, h2 for each section) is correct. |
| 4 | Performance | If patterns/synergies load from API, show loading state and avoid layout shift when data arrives. |
| 5 | Export** | If Patterns or Synergies support export (CSV/JSON), surface it clearly and ensure it works when data is empty. |

---

## Links from this page

- **In-app:** Ideas, Chat, Insights (current), Automations, Settings (bottom nav).
- **Sub-views:** Usage Patterns (default), Device Connections, Room View (same route, client-side tab switch).

No critical bugs observed; focus on empty states and tab differentiation.
