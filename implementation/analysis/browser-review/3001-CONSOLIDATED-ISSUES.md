# Port 3001 (AI Automation UI) – Consolidated Issues

**Source:** Playwright MCP crawl of all routes + existing per-page browser reviews  
**Generated:** 2026-03-02  
**Routes covered:** `/`, `/chat`, `/explore`, `/insights`, `/automations`, `/settings`, `/name-enhancement`

---

## Critical

| # | Route | Description |
|---|-------|-------------|
| 1 | All | **App crash in production** – Console: `Uncaught Error: VITE_API_KEY is required in production mode. Please set the environment variable.` When built/run in production or preview without `VITE_API_KEY`, the app throws on load and renders a blank page. |
| 2 | `/` | **Failed to load suggestions** – Red error: "Failed to list suggestions. Check server logs for details." Core feature broken; backend/API or suggestion service connectivity failing. |

---

## High

| # | Route | Description |
|---|-------|-------------|
| 3 | `/` | **0 suggestions** across all filters (New, Editing, Ready, Deployed) – Either no data or consequence of #2. Users cannot evaluate suggestions until loading succeeds. |
| 4 | `/explore` | **Failed to load devices** – Yellow "Note": "Failed to load devices. Using demo mode." Entities/devices API failure; dropdown empty or demo-only, undermining discovery. |
| 5 | `/explore` | **Explore missing from mobile nav** – Sidebar has Explore; mobile bottom bar shows Ideas, Chat, Insights, Automations, Settings (no Explore). Mobile users cannot reach this page. |

---

## Medium

| # | Route | Description |
|---|-------|-------------|
| 6 | All | **Content Security Policy** – Console: inline script violates `script-src 'self'` (aframe-stub / THREE.js preload). May block features or cause inconsistent behavior. |
| 7 | `/` | **Refresh Suggestions** – No loading state or success/error feedback when clicked. |
| 8 | `/chat` | **Send button** – Appears disabled when input empty (expected) but visual state could be clearer (aria-disabled + tooltip "Type a message to send"). |
| 9 | `/chat` | **Empty state** – Add hint: "Start by typing below or try a suggested question." |
| 10 | `/explore` | **Device dropdown** – "Choose a device" with no/demo devices gives no feedback that we're in demo mode or that list is empty due to error. |
| 11 | `/insights` | **Patterns content** – If no events exist, no empty state or "Run analysis first" message; handle no-data gracefully. |
| 12 | `/insights` | **Device Connections vs Room View** – Both use Synergies; confirm switching tabs changes content; if not, merge or clarify. |
| 13 | `/automations` | **Card overflow** – Long automation names (e.g. "Super Bowl - Kickoff Flash…") can break layout; add truncation or tooltip. |
| 14 | `/automations` | **Disabled vs Enable** – Two buttons can be confusing; clarify state (e.g. "Currently disabled" + single "Enable"). |
| 15 | `/settings` | **Run Time** – Ensure value is saved and persisted; clarify timezone (user local vs server). |
| 16 | `/settings` | **Slider** – Minimum Confidence Threshold; ensure label/value association (aria-valuenow, aria-valuetext) and persistence. |

---

## Low

| # | Route | Description |
|---|-------|-------------|
| 17 | `/` | **Empty state** – When 0 suggestions and no error, add copy explaining how suggestions are generated. |
| 18 | `/` | **Source tabs** – "From Context" and "From Blueprints" behavior when backend unavailable not verified. |
| 19 | `/chat` | **Copy verify** – Ensure "Assistant devices and create automations" (not "create sation") in live UI. |
| 20 | `/chat` | **Debug / New Chat tabs** – Verify Debug doesn't expose sensitive data in production. |
| 21 | `/chat` | **Search conversations** – With 0 conversations, add placeholder or empty result message. |
| 22 | `/explore` | **Smart Shopping** – Ensure section loads correctly in demo vs real mode. |
| 23 | `/explore` | **API/config** – Ensure env (VITE_API_KEY, proxy) is correct so production doesn't silently fall back to demo. |
| 24 | `/insights` | **Sub-tabs** – Use aria-selected/aria-current and keyboard navigation for Usage Patterns, Device Connections, Room View. |
| 25 | `/insights` | **Long copy** – "Why Patterns Matter" is dense; consider progressive disclosure. |
| 26 | `/automations` | **Last triggered** – Confirm timezone; consider relative time ("2 hours ago") with tooltip for exact. |
| 27 | `/automations` | **Trigger / Re-deploy** – Add optional confirmation for Trigger; clarify "Overwrite in HA?" for Re-deploy. |
| 28 | `/automations` | **Self-Correct** – Add tooltip or brief explanation of purpose. |
| 29 | `/settings` | **Maximum Suggestions Per Run** – Add min/max/step (e.g. 1–50) and validation. |
| 30 | `/settings` | **Save / Apply** – Ensure reachable and visible or sticky when page scrollable. |
| 31 | `/settings` | **Name Enhancement** – `/name-enhancement` exists but no link from Settings; add if settings-related. |

---

## Security

| # | Route | Description |
|---|-------|-------------|
| 32 | Multiple | **Hardcoded API key fallback** – `SmartShopping.tsx`, `TeamTrackerSettings.tsx`, `DeviceExplorer.tsx` use `'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR'` as fallback when VITE_API_KEY is unset. Remove hardcoded key; use env only or fail explicitly. |

---

## Suggested order of fixes

1. **#1** – Ensure VITE_API_KEY is set in production/preview or provide dev-friendly fallback for local dev
2. **#32** – Remove hardcoded API key fallbacks (security)
3. **#2** – Fix suggestions API/connectivity
4. **#4** – Fix devices/entities API for Explore
5. **#5** – Add Explore to mobile bottom nav
6. **#6** – Resolve CSP violation for inline scripts (aframe-stub / THREE.js)
