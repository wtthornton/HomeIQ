# Port 3001 (AI Automation UI) – Single Issues List

**Source:** Playwright crawl (2026-03-02) + prior browser reviews  
**Routes covered:** `/`, `/chat`, `/explore`, `/insights`, `/automations`, `/settings`, `/name-enhancement`, `/?source=blueprints`, `/?source=context`  
**Base URL:** http://localhost:3001

**Crawl findings:** CSP violation confirmed on all 9 routes. No navigation failures. No visible "Failed to load" errors during crawl (backend may have been available).

---

## Critical (fix first)

| # | Route | Issue |
|---|-------|-------|
| 1 | All | **App crash in production** – `VITE_API_KEY is required in production mode` when built/run without env var; renders blank page. Ensure env is set or provide dev fallback. |
| 2 | `/` | **Failed to load suggestions** – Red error: "Failed to list suggestions. Check server logs for details." Core feature broken; API/connectivity failing. |
| 3 | Multiple | **Hardcoded API key fallback** – `SmartShopping.tsx`, `TeamTrackerSettings.tsx`, `DeviceExplorer.tsx` use hardcoded key when VITE_API_KEY unset. Remove; use env only or fail explicitly. |

---

## High

| # | Route | Issue |
|---|-------|-------|
| 4 | All | **Content Security Policy** – Inline script violates `script-src 'self'` (aframe-stub / THREE.js preload). Add hash or move to external script. *Confirmed by crawl on all routes.* |
| 5 | `/` | **0 suggestions** – No data across filters (New, Editing, Ready, Deployed); users cannot evaluate until loading works. |
| 6 | `/explore` | **Failed to load devices** – "Failed to load devices. Using demo mode." Entities API failure; dropdown empty or demo-only. |
| 7 | `/explore` | **Explore missing from mobile nav** – Sidebar has Explore; mobile bottom bar shows Ideas, Chat, Insights, Automations, Settings only. Add Explore for mobile. |

---

## Medium

| # | Route | Issue |
|---|-------|-------|
| 8 | `/` | **Refresh Suggestions** – No loading state or success/error feedback when clicked. |
| 9 | `/chat` | **Send button** – Add aria-disabled + tooltip "Type a message to send" for clearer state. |
| 10 | `/chat` | **Empty state** – Add hint: "Start by typing below or try a suggested question." |
| 11 | `/explore` | **Device dropdown** – "Choose a device" with no/demo devices; no feedback that we're in demo mode or list is empty due to error. |
| 12 | `/insights` | **Patterns content** – Add empty state or "Run analysis first" when no events exist. |
| 13 | `/insights` | **Device Connections vs Room View** – Confirm tab switching changes content; merge or clarify if redundant. |
| 14 | `/automations` | **Card overflow** – Long automation names break layout; add truncation or tooltip. |
| 15 | `/automations` | **Disabled vs Enable** – Clarify state (e.g. "Currently disabled" + single "Enable"). |
| 16 | `/settings` | **Run Time** – Ensure value is saved; clarify timezone (user local vs server). |
| 17 | `/settings` | **Slider** – Minimum Confidence Threshold; add aria-valuenow, aria-valuetext; ensure persistence. |

---

## Low

| # | Route | Issue |
|---|-------|-------|
| 18 | `/` | **Empty state** – When 0 suggestions and no error, add copy explaining how suggestions are generated. |
| 19 | `/` | **Source tabs** – Verify "From Context" and "From Blueprints" behavior when backend unavailable. |
| 20 | `/chat` | **Copy** – Verify "Assistant devices and create automations" typo ("create sation") in live UI. |
| 21 | `/chat` | **Debug tab** – Verify Debug doesn't expose sensitive data in production. |
| 22 | `/chat` | **Search conversations** – With 0 conversations, add placeholder or empty result message. |
| 23 | `/explore` | **Smart Shopping** – Ensure section loads correctly in demo vs real mode. |
| 24 | `/explore` | **API/config** – Ensure env correct so production doesn't silently fall back to demo. |
| 25 | `/insights` | **Sub-tabs** – Use aria-selected/aria-current and keyboard nav for Usage Patterns, Device Connections, Room View. |
| 26 | `/insights` | **Long copy** – "Why Patterns Matter" is dense; consider progressive disclosure. |
| 27 | `/automations` | **Last triggered** – Confirm timezone; consider relative time ("2 hours ago") with tooltip for exact. |
| 28 | `/automations` | **Trigger / Re-deploy** – Add optional confirmation for Trigger; clarify "Overwrite in HA?" for Re-deploy. |
| 29 | `/automations` | **Self-Correct** – Add tooltip or brief explanation of purpose. |
| 30 | `/settings` | **Maximum Suggestions Per Run** – Add min/max/step (e.g. 1–50) and validation. |
| 31 | `/settings` | **Save / Apply** – Ensure reachable and visible or sticky when page scrollable. |
| 32 | `/settings` | **Name Enhancement** – `/name-enhancement` exists but no link from Settings; add if settings-related. |

---

## Suggested fix order

1. **#1** – VITE_API_KEY in production
2. **#3** – Remove hardcoded API key fallbacks
3. **#2** – Fix suggestions API/connectivity
4. **#4** – Resolve CSP violation (inline scripts)
5. **#6** – Fix devices/entities API for Explore
6. **#7** – Add Explore to mobile bottom nav
7. **#8–17** – Medium-priority UX and feedback
8. **#18–32** – Low-priority polish
