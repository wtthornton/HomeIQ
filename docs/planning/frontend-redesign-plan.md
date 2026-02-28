# HomeIQ Frontend Redesign Plan

**Created:** 2026-02-25
**Status:** COMPLETED (Feb 26, 2026)
**Scope:** All 3 frontend apps (AI Automation UI, Health Dashboard, Observability Dashboard)

---

## 2026 Design Audit — Current vs. Trend Alignment

### What We Already Have Right
- **Dark-mode-first**: Our design system (`design-system.css`) defaults to dark slate (`#09090b`) — aligns with 2026's dark-as-standard movement
- **Tight spacing / density**: Tighter spacing variables already defined — matches SaaS dashboard density best practices
- **Reduced motion support**: `prefers-reduced-motion` media query in place
- **Backdrop blur on cards**: Glass-morphism via `backdrop-filter: blur(12px)` — partially aligns with 2026's Liquid Glass trend
- **System font stack**: Performance-first typography choice

### What Needs to Change

| Area | Current State | 2026 Gap |
|---|---|---|
| **Color palette** | Industrial slate + amber/orange (`#f97316`) | 2026 favors teal, soft gold, and neo earth tones as accents. Amber/orange reads as "warning" not "brand." Shift primary accent to **Teal** (`#14b8a6`) with amber reserved for warnings. |
| **Navigation** | Flat top bar with 11 items (AI UI) / 18 tabs (Health) | 2026: sidebar for 5+ items, progressive disclosure, grouped sub-navigation. Max 5-7 top-level items. |
| **Light mode** | Toggle exists but design system only defines dark vars | 2026: both modes are expected with proper variable sets. Need full light-mode palette. |
| **Depth & layering** | Flat cards with subtle borders | 2026 Liquid Glass: translucent surfaces, layered z-depth, soft ambient shadows. Add glass-tier elevation system. |
| **Motion** | Framer Motion used inconsistently | 2026: purposeful micro-interactions (tab transitions, card entrance, data updates). Standardize a motion library. |
| **Typography** | 13px base, uppercase section titles | 2026: slightly larger base (14-15px), less uppercase, more contrast between heading weights. |
| **Gradient usage** | Minimal (card bg only) | 2026: cinematic gradients on hero sections, mesh gradients on backgrounds — subtle, not rainbow. |
| **Accessibility** | Some aria-labels, no focus-visible system | 2026: WCAG 2.2 AA minimum, focus-visible rings, skip-to-content, color-independent indicators. |
| **Personalization** | None | 2026: widget reordering, role-based default views, remembered preferences beyond dark mode. |
| **Mobile nav** | Horizontal scroll tabs | 2026: bottom tab bar for primary actions (thumb zone). |

### Recommended New Palette

```
Dark Mode (Primary):
  --bg-primary:     #0a0a0f       (deeper blue-black, less zinc)
  --bg-secondary:   #12121a       (hint of blue undertone)
  --bg-tertiary:    #1e1e2a       (elevated surface)

  --accent-primary: #14b8a6       (teal — trust, intelligence, calm)
  --accent-secondary: #d4a847     (honeyed gold — warmth, premium)
  --accent-glow:    rgba(20, 184, 166, 0.12)

  --success:        #22c55e       (keep)
  --warning:        #f59e0b       (shift amber here — its natural role)
  --error:          #ef4444       (keep)
  --info:           #38bdf8       (sky blue, not orange)

Light Mode (Full set needed):
  --bg-primary:     #f8f9fc       (cloud dancer white, not harsh)
  --bg-secondary:   #f0f1f5       (soft grey)
  --bg-tertiary:    #e5e7ed       (elevated surface)
  --card-bg:        rgba(255, 255, 255, 0.92)
  --accent-primary: #0d9488       (teal, slightly darker for contrast)
  --text-primary:   #1a1a2e       (near-black, blue undertone)
  --text-secondary: #4a4a5e
```

---

## Epic Overview

| Epic | Name | Scope |
|---|---|---|
| **FR-1** | Design System Evolution | Shared palette, tokens, components, motion |
| **FR-2** | AI Automation UI Restructure | Navigation, page consolidation, new layout |
| **FR-3** | Health Dashboard Restructure | Grouped tabs, sidebar nav, progressive disclosure |
| **FR-4** | Observability Dashboard Modernize | Streamlit tab consolidation, consistent branding |
| **FR-5** | Cross-App Shell & Consistency | Unified header, app switcher, shared footer |
| **FR-6** | Accessibility & Responsive | WCAG 2.2 AA, mobile bottom nav, focus system |

---

## Epic FR-1: Design System Evolution

**Goal:** Establish a unified, 2026-aligned design foundation shared across all 3 apps.

### FR-1.1: Color Palette Refresh
- Replace amber/orange primary accent with teal (`#14b8a6` dark / `#0d9488` light)
- Move amber to warning-only role (`--warning: #f59e0b`)
- Define `--info` as sky blue (`#38bdf8`), not orange
- Add honeyed gold as secondary accent for premium/highlight moments
- Update all CSS custom properties in `design-system.css`
- Create semantic token aliases: `--color-brand`, `--color-danger`, `--color-caution`, `--color-positive`, `--color-neutral`

### FR-1.2: Full Light Mode Palette
- Define complete light-mode variable set (backgrounds, cards, text, borders)
- Use `prefers-color-scheme` media query as default, with manual toggle override
- Cloud Dancer-inspired whites (`#f8f9fc`) — warm, not clinical
- Test all existing components in light mode for contrast compliance (WCAG AA 4.5:1 minimum)

### FR-1.3: Liquid Glass Elevation System
- Define 3 elevation tiers: `surface`, `raised`, `floating`
- `surface`: solid bg, 1px border, no blur
- `raised`: translucent bg, `backdrop-filter: blur(16px)`, soft shadow
- `floating`: deeper translucency, `blur(24px)`, stronger shadow, subtle border glow
- Apply tiers to cards, modals, dropdowns, tooltips
- Add subtle ambient shadow using accent-tinted `box-shadow` (not colored glow — controlled energy)

### FR-1.4: Typography Scale Update
- Increase base font from 13px to 14px
- Reduce uppercase usage — section titles to sentence case with heavier weight (700) instead
- Define type scale: `--text-xs` (12px), `--text-sm` (13px), `--text-base` (14px), `--text-lg` (16px), `--text-xl` (20px), `--text-2xl` (24px), `--text-3xl` (32px)
- Tighten letter-spacing on headings (`-0.02em`), loosen on small text (`+0.01em`)

### FR-1.5: Motion Standards
- Define 3 motion tokens: `--motion-fast` (150ms), `--motion-normal` (250ms), `--motion-slow` (400ms)
- Standardize easing: `cubic-bezier(0.4, 0, 0.2, 1)` for enter, `cubic-bezier(0.4, 0, 1, 1)` for exit
- Card entrance: fade-up with stagger (50ms between siblings)
- Tab transitions: cross-fade content, slide active indicator
- Data update: number counters animate on change, charts morph smoothly
- All animations honor `prefers-reduced-motion`

### FR-1.6: Shared Component Library Extraction
- Extract common components used across apps: Button, Card, Badge, StatusDot, Metric, Modal, Tooltip, Tabs, Sidebar
- Package as `@homeiq/ui` or co-locate in `libs/homeiq-ui/`
- Ensure components accept `variant`, `size`, and `elevation` props
- Storybook catalog (optional — defer if not immediately needed)

---

## Epic FR-2: AI Automation UI Restructure

**Goal:** Reduce 11 flat tabs to 6 primary + 2 utility with grouped sub-navigation and clearer labels.

### FR-2.1: Sidebar Navigation Migration
- Replace top nav bar with collapsible sidebar (left rail)
- Sidebar items: icon + label (expanded) or icon-only (collapsed)
- Sidebar groups: "Create" section and "Manage" section and "Configure" section
- Mobile: convert sidebar to bottom tab bar (5 primary items in thumb zone)
- Persist collapsed/expanded state in localStorage
- Keyboard: arrow keys to navigate, Enter to select, Escape to collapse

### FR-2.2: Merge Suggestion Sources → "Ideas" Page
- Combine "Suggestions" (ConversationalDashboard), "Proactive" (ProactiveSuggestions), and "Blueprint Suggestions" into one page
- New page name: **Ideas**
- Internal tab strip: "From Your Data" | "From Blueprints" | "From Context"
- Shared card layout across all 3 sub-views (accept/decline/refine actions)
- Unified filter bar (source type, confidence, status, category)
- Sub-tab selection persisted in URL query param (`?source=blueprints`)

### FR-2.3: Merge Patterns + Synergies → "Insights" Page
- Combine "Patterns" and "Synergies" into one page
- New page name: **Insights**
- Internal tab strip: "Usage Patterns" | "Device Connections" | "Room View"
- "Usage Patterns" = existing pattern explorer (charts, list, details modal)
- "Device Connections" = existing synergy grid + network graph
- "Room View" = existing room map view from synergies
- Shared search bar and confidence filter across sub-views

### FR-2.4: Rename and Simplify Remaining Pages
- "Agent" → **Chat** (route: `/chat`)
  - Update nav label, aria-labels, page title, breadcrumb
  - Add subtitle: "Ask your home assistant anything"
- "Deployed" → **Automations** (route: `/automations`)
  - Update nav label and all references
  - Add subtitle: "Your live automations"
- "Discovery" → **Explore** (route: `/explore`)
  - Update nav label
  - Add subtitle: "What can you automate next?"

### FR-2.5: Merge Settings + Admin
- Combine Settings and Admin into one page with sections
- New page name: **Settings** (route: `/settings`)
- Sections (vertical accordion or tabs within):
  - "Preferences" — AI model config, enabled categories, dark mode, team tracker
  - "System" — service status, training runs, GNN training, overview stats
  - "Configuration" — admin config display
- Remove separate `/admin` route (redirect to `/settings?section=system`)

### FR-2.6: Demote "Names" to Utility
- Move "Name Enhancement" out of primary nav
- Access via: Settings → "Device Names" section, or an icon-button on the Explore page
- Keep `/name-enhancement` route for direct linking but remove from sidebar

### FR-2.7: Update App Identity
- Current: "HA AutomateAI"
- New: **HomeIQ** (matches the project name, shorter, cleaner)
- Update logo text, footer, page titles, and `<title>` tag
- Footer text: "HomeIQ — AI-Powered Smart Home Intelligence"

---

## Epic FR-3: Health Dashboard Restructure

**Goal:** Reduce 18 flat tabs to 5 grouped sections with sub-tabs and sidebar navigation.

### FR-3.1: Sidebar Navigation with Groups
- Replace horizontal tab bar with sidebar navigation
- 5 top-level groups, each expandable to show sub-pages:
  ```
  Overview
  Infrastructure
    ├── Services
    ├── Groups
    ├── Dependencies
    └── Configuration
  Devices & Data
    ├── Devices
    ├── Events
    ├── Data Feeds      (was "Data Sources")
    ├── Energy
    └── Sports
  Quality
    ├── Alerts
    ├── Device Health   (was "Device Hygiene")
    ├── Automation Checks (was "HA Validation")
    └── AI Performance  (was "Agent Evaluation")
  Logs & Analytics
    ├── Logs
    └── Analytics
  ```
- Collapse sub-items by default; expand active group
- Mobile: drawer menu with same hierarchy

### FR-3.2: Merge Overview + Setup & Health
- Fold "Setup & Health" content into the "Overview" page
- Overview structure:
  - Top row: connection status badges (HA, InfluxDB, PostgreSQL)
  - Second row: key metric cards (services up, devices, events/min, error rate)
  - Third row: recent alerts summary + quick links to deep-dive pages
- Remove standalone "Setup & Health" tab entirely

### FR-3.3: Remove Synergies Tab
- Synergies belongs only in AI Automation UI → "Insights" page
- Remove `synergies` tab from health dashboard
- Remove synergies component imports and lazy-loaded module

### FR-3.4: Rename Sub-Tabs for Clarity
- "Device Hygiene" → **Device Health** — rename label, component file, all references
- "HA Validation" → **Automation Checks** — rename label, component file, all references
- "Agent Evaluation" → **AI Performance** — rename label, component file, all references
- "Data Sources" → **Data Feeds** — rename label, component file, all references
- "Setup & Health" → **Connection Status** (before merge into Overview)

### FR-3.5: Add Dashboard Header & Identity
- Add branded header: "HomeIQ Health" with auto-refresh toggle and dark mode toggle
- Match the palette and typography from FR-1 design system
- Show last-refreshed timestamp in header

---

## Epic FR-4: Observability Dashboard Modernize

**Goal:** Consolidate 5 Streamlit pages to 3 focused views and remove wasted "Home" page.

### FR-4.1: Remove Home Page
- Eliminate standalone "Home" page (currently just shows config URLs)
- Move config status into a collapsible sidebar section labeled "Connections"
- Set "Traces" as the default landing page

### FR-4.2: Merge Trace Visualization + Automation Debugging → "Traces"
- New page name: **Traces**
- Add a toggle/filter at the top: "All Services" | "Automations Only"
- "All Services" mode = current trace_visualization.py behavior
- "Automations Only" mode = current automation_debugging.py behavior (filters to ai-automation-service, shows flow visualization)
- Automation flow view becomes an expandable detail panel within the trace list, not a separate page
- Shared sidebar filters (service, time range, trace ID, correlation ID)
- Merge `_query_automation_traces` and `_query_traces` into one function with a `service_filter` param

### FR-4.3: Rename Service Performance → "Performance"
- Rename tab label from "Service Performance" to **Performance**
- Update page header from "Service Performance Monitoring" to "Performance"
- Subtitle: "Service health, latency, and error rates"
- No structural changes needed — content is solid

### FR-4.4: Rename Real-Time Monitoring → "Live"
- Rename tab label from "Real-Time Monitoring" to **Live**
- Update page header from "Real-Time Observability" to "Live"
- Subtitle: "Streaming traces and anomaly detection"
- No structural changes — content is solid

### FR-4.5: Update Streamlit Branding
- Update `page_title` from "HomeIQ Observability Dashboard" to "HomeIQ Ops"
- Update main title to "HomeIQ Ops"
- Subtitle: "Internal observability and debugging"
- Sidebar title: "Navigation" → remove (Streamlit radio is self-explanatory)

---

## Epic FR-5: Cross-App Shell & Consistency

**Goal:** Provide a unified experience when switching between the 3 frontend apps.

### FR-5.1: Cross-App Switcher
- Add a small app-switcher element in each app's sidebar/header
- Options: "HomeIQ" (AI UI), "Health" (Health Dashboard), "Ops" (Observability)
- Shows current app as active, others as links
- Consistent position across all 3 apps (top-left corner)

### FR-5.2: Unified Footer
- Same footer across AI Automation UI and Health Dashboard:
  - "HomeIQ — AI-Powered Smart Home Intelligence"
  - Links: API Docs | Documentation | GitHub
- Remove cost reference ("~$0.075/month") from footer — belongs in Settings/Admin

### FR-5.3: Consistent Terminology Glossary
- Establish shared term definitions across all 3 apps:
  - "Automations" (not "Deployed", not "Automation Debugging")
  - "Devices" (not "Entities" in user-facing text)
  - "Suggestions" vs "Ideas" — "Ideas" in nav, "suggestions" in body text is acceptable
  - "Health" always refers to status/uptime, never "Hygiene"
- Document in `docs/frontend-terminology.md` as reference for all future UI work

---

## Epic FR-6: Accessibility & Responsive

**Goal:** Meet WCAG 2.2 AA across all apps and modernize mobile layouts.

### FR-6.1: Focus-Visible System
- Define `--focus-ring` in teal (`rgba(20, 184, 166, 0.5)`) for both modes
- Apply `:focus-visible` outline to all interactive elements
- Remove all `:focus { outline: none }` without replacement
- Add skip-to-content link at top of each app

### FR-6.2: Color-Independent Indicators
- Audit all status indicators (health dots, error badges, success/fail)
- Add icon or shape alongside color: checkmark for success, X for error, triangle for warning, circle for info
- Ensure 4.5:1 contrast ratio for all text on both light and dark backgrounds

### FR-6.3: Mobile Bottom Tab Bar (AI Automation UI)
- Replace horizontal scroll nav on mobile with fixed bottom tab bar
- 5 tabs in bottom bar: Home | Ideas | Chat | Insights | Automations
- "Explore", "Settings" accessible via hamburger menu or "More" tab
- Icons required for bottom bar items (use simple line icons, not emoji)
- Active state: filled icon + teal accent underline

### FR-6.4: Mobile Drawer (Health Dashboard)
- Replace horizontal scroll on mobile with hamburger → full-screen drawer
- Same grouped hierarchy as desktop sidebar (FR-3.1)
- Smooth slide-in animation, overlay backdrop

### FR-6.5: Responsive Cards & Grids
- Audit all card grids across both React apps
- Ensure single-column layout at `<640px`, two-column at `640-1024px`, three+ at `>1024px`
- Cards should not horizontally overflow on any viewport

---

## Dependency Map

```
FR-1 (Design System) ← must complete first
  ├── FR-2 (AI Automation UI) — depends on FR-1.1, FR-1.2, FR-1.3
  ├── FR-3 (Health Dashboard) — depends on FR-1.1, FR-1.2, FR-1.4
  ├── FR-4 (Observability) — depends on FR-1.1 (palette only)
  └── FR-6 (Accessibility) — depends on FR-1.2, FR-1.5
FR-5 (Cross-App Shell) — depends on FR-2.1, FR-3.1 (sidebar pattern established)
```

## Recommended Execution Order

1. **FR-1** (Design System) — foundation, unblocks everything
2. **FR-4** (Observability) — smallest scope, quick win, validates new palette
3. **FR-2** (AI Automation UI) — highest user impact
4. **FR-3** (Health Dashboard) — parallel with FR-2 if resourced
5. **FR-6** (Accessibility) — layer on top of new layouts
6. **FR-5** (Cross-App Shell) — finishing touch

## Story Point Estimates

| Epic | Stories | Est. Points |
|---|---|---|
| FR-1 | 6 | 21 |
| FR-2 | 7 | 34 |
| FR-3 | 5 | 21 |
| FR-4 | 5 | 13 |
| FR-5 | 3 | 8 |
| FR-6 | 5 | 21 |
| **Total** | **31 stories** | **118 points** |

---

## Sources & References

- [12 UI/UX Design Trends That Will Dominate 2026](https://www.index.dev/blog/ui-ux-design-trends)
- [9 Dashboard Design Principles 2026 — DesignRush](https://www.designrush.com/agency/ui-ux-design/dashboard/trends/dashboard-design-principles)
- [UI Color Trends 2026 — Updivision](https://updivision.com/blog/post/ui-color-trends-to-watch-in-2026)
- [Top Web Design Trends 2026 — Figma](https://www.figma.com/resource-library/web-design-trends/)
- [SaaS Design Trends & Best Practices 2026 — JetBase](https://jetbase.io/blog/saas-design-trends-best-practices)
- [Smart SaaS Dashboard Design Guide 2026 — F1Studioz](https://f1studioz.com/blog/smart-saas-dashboard-design/)
- [Color Trends 2026: Trending Palettes — AND Academy](https://www.andacademy.com/resources/blog/graphic-design/color-trends-for-designers/)
- [Dark Mode Design Converts Better: 2026 Guide — Digital Silk](https://www.digitalsilk.com/digital-trends/dark-mode-design-guide/)
- [Top Nav vs Side Nav — Medium](https://medium.com/design-bootcamp/top-nav-v-s-side-nav-how-to-decide-b07d1f81712a)
- [Smart Home Dashboard UX Design — Developex](https://developex.com/blog/smart-home-dashboard-ux-design/)
- [Home Assistant 2026.1 Release](https://www.home-assistant.io/blog/2026/01/07/release-20261)
- [Admin Dashboard Guide 2026 — WeWeb](https://www.weweb.io/blog/admin-dashboard-ultimate-guide-templates-examples)
