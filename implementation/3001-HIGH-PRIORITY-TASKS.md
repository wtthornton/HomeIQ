# AI Automation UI (3001) – Task List

**Created:** 2026-03-02  
**Source:** 3001-ISSUES-TO-FIX.md + crawl results

---

## Completed ✓

| # | Task | Status |
|---|------|--------|
| 1 | **VITE_API_KEY** – Stop throwing at module load; log console.error in production when missing. App now loads; requests fail with 401 if key unset. | Done |
| 2 | **Remove hardcoded API key fallbacks** – SmartShopping, TeamTrackerSettings, DeviceExplorer now use `VITE_API_KEY ?? ''` only. | Done |
| 3 | **CSP violation** – Moved inline scripts to external files: `/public/aframe-stub.js`, `src/three-global.ts`. Removed vite plugin inline injection. | Done |
| 4 | **Explore in mobile nav** – Already present in Sidebar MOBILE_TABS; no change needed. | N/A |
| 5 | **Refresh Suggestions feedback** – ConversationalDashboard already has loading state and toast success/error. | N/A |

---

## Completed (this session) ✓

| # | Task | Status |
|---|------|--------|
| 3 | `/chat` – Add empty-state hint: "Start by typing below or try a suggested question." | Done |
| 4 | `/chat` – Send button: already has aria-disabled + tooltip when empty | N/A |
| 5 | `/explore` – Device dropdown: show demo-mode feedback when list is empty | Done |
| 6 | `/insights` – Patterns: already has "Run analysis first" empty state | N/A |
| 7 | `/automations` – Card already truncates; clarify Disabled vs Enable (title + aria-label) | Done |
| 8 | `/automations` – Self-Correct: add tooltip | Done |
| 9 | `/settings` – Run Time timezone clarification (local timezone) | Done |
| 10 | `/settings` – Slider: aria-valuenow, aria-valuetext | Done |
| 11 | `/` – Empty state: ConversationalDashboard already has copy | N/A |
| 12 | `/settings` – Link to Name Enhancement | Done |

## Remaining (by priority)

### Critical (backend)
| # | Task | Notes |
|---|------|-------|
| 1 | Fix suggestions API/connectivity – "Failed to list suggestions" on Ideas | Backend/API or suggestion service; check service health and logs. |

### High (backend)
| # | Task | Notes |
|---|------|-------|
| 2 | Fix devices/entities API for Explore – "Failed to load devices. Using demo mode." | Backend connectivity; entities/devices endpoint. |

### Low
| # | Task |
|---|------|
| 13 | `/` – Verify source tabs behavior when backend unavailable |
| 14 | `/chat` – Verify copy typo; Debug tab safety |
| 15 | Others – See 3001-ISSUES-TO-FIX.md |

---

## Files Changed (all sessions)

### Session 1 (VITE_API_KEY, CSP, hardcoded keys)
- `domains/frontends/ai-automation-ui/src/lib/api-client.ts` – VITE_API_KEY handling
- `domains/frontends/ai-automation-ui/src/components/discovery/SmartShopping.tsx` – API key
- `domains/frontends/ai-automation-ui/src/components/TeamTrackerSettings.tsx` – API key
- `domains/frontends/ai-automation-ui/src/components/discovery/DeviceExplorer.tsx` – API key
- `domains/frontends/ai-automation-ui/public/aframe-stub.js` – New (CSP-compliant)
- `domains/frontends/ai-automation-ui/src/three-global.ts` – New (THREE.js preload)
- `domains/frontends/ai-automation-ui/src/main.tsx` – Import three-global
- `domains/frontends/ai-automation-ui/index.html` – Inline script → external
- `domains/frontends/ai-automation-ui/vite.config.ts` – Removed aframe-stub plugin

### Session 2 (Remaining UX)
- `domains/frontends/ai-automation-ui/src/pages/HAAgentChat.tsx` – Empty-state hint
- `domains/frontends/ai-automation-ui/src/components/discovery/DeviceExplorer.tsx` – Demo-mode feedback
- `domains/frontends/ai-automation-ui/src/pages/Deployed.tsx` – Toggle/Self-Correct tooltips and aria-labels
- `domains/frontends/ai-automation-ui/src/pages/Settings.tsx` – Run Time timezone, slider aria, Name Enhancement link
- `domains/frontends/ai-automation-ui/src/pages/Discovery.tsx` – VITE_API_KEY `??` consistency
