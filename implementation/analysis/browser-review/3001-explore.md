# Port 3001 – Explore Page (Discovery)

**URL:** `http://localhost:3001/explore`  
**Title:** Explore - HomeIQ  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** Automation discovery and device explorer – what you can automate and smart device recommendations.
- **Key UI:** Automation Discovery card, Device Explorer (dropdown “Choose a device”), Smart Shopping Recommendations; note banner when devices fail to load.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | **High** | **Failed to load devices** – Yellow “Note” card: “Failed to load devices. Using demo mode.” Indicates entities/devices API failure or misconfiguration; dropdown may be empty or demo-only, undermining discovery value. |
| 2 | Medium | **Explore not in mobile nav** – Sidebar has Explore under “Create,” but mobile bottom bar shows Ideas, Chat, Insights, Automations, Settings (no Explore). Mobile users cannot reach this page from the tab bar. |
| 3 | Medium | **Device dropdown** – “Choose a device” with no devices (or only demo) gives no feedback that we’re in demo mode or that the list is empty due to an error. |
| 4 | Low | **Smart Shopping Recommendations** – Section is below the fold; ensure it’s reachable and that content loads correctly in demo vs. real mode. |
| 5 | Low | **API/config** – Code uses `/api/entities` and fallback `/api/data/devices`; ensure env (e.g. VITE_API_KEY, proxy) is correct so production doesn’t silently fall back to demo. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Error handling | In addition to “Using demo mode,” add “Retry” or “Check connection” and optionally a link to Settings; log failure reason for support. |
| 2 | Mobile nav | Add Explore to the mobile bottom nav (e.g. replace one icon or add as 6th item / overflow menu) so parity with desktop. |
| 3 | Empty/demo state | When in demo mode, show a short line under the dropdown: “Showing demo devices. Connect your home to see your devices.” |
| 4 | Accessibility | Ensure “Select a device to explore” has a proper label and the dropdown is keyboard navigable and announced by screen readers. |
| 5 | Loading | Show skeleton or spinner while devices are loading; disable dropdown until loaded or explicitly in error/demo state. |

---

## Links from this page

- **In-app:** Ideas, Chat, Insights, Automations, Settings (bottom nav). Explore is not in mobile tabs.
- **Sub-content:** Device Explorer dropdown, Smart Shopping section (scroll).

Prioritize **issue #1** (device load) and **#2** (mobile nav) for a complete Explore experience.
