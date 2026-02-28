# Port 3001 – Automations Page (Deployed)

**URL:** `http://localhost:3001/automations`  
**Title:** Automations - HomeIQ  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** Manage automations deployed to Home Assistant.
- **Key UI:** List of automation cards (e.g. Super Bowl Kickoff Flash, SEA Score Flash) with entity ID, last triggered time, actions: Disabled/Enable, Trigger, Re-deploy, Show Code, Self-Correct.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **Card overflow** – Long automation names or IDs can cause layout issues; “Super Bowl - Kickoff Flash (Starts -15s, Runs 30s)” is long; ensure truncation or wrapping with tooltip for full text. |
| 2 | Medium | **Disabled vs Enable** – Two buttons (Disabled badge and Enable) can be confusing; ensure state is clear (e.g. “Currently disabled” + single “Enable” button) and that double-click doesn’t toggle twice. |
| 3 | Low | **Last triggered** – Format “2/8/2026, 3:29:45 PM” – confirm timezone (user vs. server); consider relative time (“2 hours ago”) with tooltip for exact time. |
| 4 | Low | **Trigger / Re-deploy** – No confirmation for Trigger (could cause real-world effect); Re-deploy should clarify “Overwrite in HA?” if applicable. |
| 5 | Low | **Self-Correct** – Purpose and what it does (e.g. fix YAML, re-validate) should be clear in UI or tooltip. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Layout | Use consistent card height or truncation with “Show more”; ensure buttons wrap or stay in a single row on small screens. |
| 2 | State | Single source of truth for enabled/disabled; one primary action (Enable or Disable) per card to avoid ambiguity. |
| 3 | Safety | Optional confirmation for Trigger (“Run this automation now?”); for Re-deploy, brief explanation of what will be overwritten. |
| 4 | Accessibility | Each card should have a heading (automation name); buttons need aria-labels (e.g. “Enable Super Bowl Kickoff Flash”). |
| 5 | Empty state | If no deployed automations, show “No automations deployed yet” and link to Ideas or Chat to create one. |
| 6 | Filter/sort | Add filter by name/entity or sort by last triggered to manage large lists. |

---

## Links from this page

- **In-app:** Ideas, Chat, Insights, Automations (current), Settings (bottom nav).
- **Actions per card:** Enable, Trigger, Re-deploy, Show Code, Self-Correct.

No critical blocking issues; improve clarity of state and safety of destructive actions.
