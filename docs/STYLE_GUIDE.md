# HomeIQ Design System Style Guide

> Version 2.0.0 | February 2026
> Applies to: Health Dashboard, AI Automation UI, Observability Dashboard

---

## Table of Contents

1. [Brand Identity](#brand-identity)
2. [Color System](#color-system)
3. [Typography](#typography)
4. [Spacing & Layout](#spacing--layout)
5. [Border Radius](#border-radius)
6. [Elevation & Shadows](#elevation--shadows)
7. [Motion & Animation](#motion--animation)
8. [Components](#components)
9. [Layout Patterns](#layout-patterns)
10. [Accessibility](#accessibility)
11. [Theme Modes](#theme-modes)
12. [Source Files](#source-files)

---

## Brand Identity

| Property | Value |
|---|---|
| **Product name** | HomeIQ |
| **Dashboard app** | Health Dashboard (`:3000`) |
| **Automation app** | AI Automation UI (`:3001`) — previously "HA AutomateAI" |
| **Ops app** | HomeIQ Ops (`:8501`) — Streamlit-based observability |
| **Primary accent** | Teal `#14b8a6` |
| **Secondary accent** | Gold `#d4a847` |
| **Design philosophy** | Data-dense, industrial, liquid glass elevation, dark-first |

---

## Color System

### Dark Theme (Default)

| Token | CSS Variable | Value | Usage |
|---|---|---|---|
| Background Primary | `--bg-primary` | `#0a0a0f` | Page background |
| Background Secondary | `--bg-secondary` | `#12121a` | Card backgrounds |
| Background Tertiary | `--bg-tertiary` | `#1e1e2a` | Elevated surfaces |
| Card Background | `--card-bg` | `rgba(18, 18, 26, 0.95)` | Card fills |
| Card Background Alt | `--card-bg-alt` | `rgba(30, 30, 42, 0.95)` | Card gradient end |
| Card Border | `--card-border` | `rgba(63, 63, 90, 0.5)` | Card strokes |
| Accent Primary | `--accent-primary` | `#14b8a6` | Buttons, links, focus rings |
| Accent Secondary | `--accent-secondary` | `#d4a847` | Gold highlights |
| Text Primary | `--text-primary` | `#fafafa` | Headings, body |
| Text Secondary | `--text-secondary` | `#d4d4d8` | Descriptions |
| Text Tertiary | `--text-tertiary` | `#a1a1aa` | Labels |
| Text Muted | `--text-muted` | `#71717a` | Placeholders |

### Light Theme

| Token | CSS Variable | Value |
|---|---|---|
| Background Primary | `--bg-primary` | `#f8f9fc` |
| Background Secondary | `--bg-secondary` | `#f0f1f5` |
| Background Tertiary | `--bg-tertiary` | `#e5e7ed` |
| Card Background | `--card-bg` | `rgba(255, 255, 255, 0.92)` |
| Card Border | `--card-border` | `rgba(0, 0, 0, 0.08)` |
| Accent Primary | `--accent-primary` | `#0d9488` |
| Text Primary | `--text-primary` | `#1a1a2e` |
| Text Secondary | `--text-secondary` | `#4a4a5e` |

### Status Colors

| Status | Dark | Light | Indicator |
|---|---|---|---|
| Success / Healthy | `#22c55e` | `#16a34a` | `✓` prefix |
| Warning | `#f59e0b` | `#d97706` | `⚠` prefix |
| Error / Critical | `#ef4444` | `#dc2626` | `✗` prefix |
| Info | `#38bdf8` | `#0284c7` | `ℹ` prefix |

### Semantic Aliases

```css
--color-brand:    var(--accent-primary);
--color-danger:   var(--error);
--color-caution:  var(--warning);
--color-positive: var(--success);
--color-neutral:  var(--text-muted);
```

### Smart Home Domain Colors (Health Dashboard)

| Domain | HSL Variable | Usage |
|---|---|---|
| Weather | `--accent-weather: 199 89% 48%` | Weather data cards |
| Sports | `--accent-sports: 168 76% 40%` | Sports integration |
| Automation | `--accent-automation: 45 93% 47%` | Automation features |
| Energy | `--accent-energy: 142 71% 45%` | Energy analytics |

---

## Typography

### Font Stack

| Role | Font Family | CSS Variable | Fallbacks |
|---|---|---|---|
| **Display** (headings) | Outfit Variable | `--font-display` | Inter, system-ui, sans-serif |
| **Body** (UI text) | Inter Variable | `--font-sans` | system-ui, -apple-system, sans-serif |
| **Mono** (code, metrics) | JetBrains Mono Variable | `--font-mono` | SF Mono, ui-monospace, monospace |

### Size Scale

| Token | Size | Pixels | Usage |
|---|---|---|---|
| `--text-xs` / `--font-size-xs` | `0.6875rem` | 11px | Tiny labels |
| `--text-sm` / `--font-size-sm` | `0.75rem` | 12px | Small text |
| `--text-base` / `--font-size-base` | `0.875rem` | **14px** (base) | Body text |
| `--text-lg` / `--font-size-lg` | `1rem` | 16px | Subheadings |
| `--text-xl` / `--font-size-xl` | `1.125rem` | 18px | h3 |
| `--text-2xl` / `--font-size-2xl` | `1.25rem` | 20px | h2, card titles |
| `--text-3xl` / `--font-size-3xl` | `1.5rem` | 24px | h1, section titles |
| `--font-size-4xl` | `1.875rem` | 30px | Hero display |
| `--font-size-5xl` | `2.25rem` | 36px | Hero display |

### Weight Scale

| Token | Weight | Usage |
|---|---|---|
| `--font-weight-light` | 300 | De-emphasized text |
| `--font-weight-normal` | 400 | Body text |
| `--font-weight-medium` | 500 | Labels, subtle emphasis |
| `--font-weight-semibold` | 600 | h3-h4, button text |
| `--font-weight-bold` | 700 | h1-h2, display text |
| `--font-weight-extrabold` | 800 | Hero emphasis |

### Line Height Scale

| Token | Value | Usage |
|---|---|---|
| `--leading-none` | 1 | Single-line display |
| `--leading-tight` | 1.2 | Headings |
| `--leading-snug` | 1.35 | Compact body |
| `--leading-normal` | 1.45 | Default body |
| `--leading-relaxed` | 1.6 | Readable paragraphs |

### Letter Spacing

| Token | Value | Usage |
|---|---|---|
| `--tracking-tight` | -0.015em | Headings (display font) |
| `--tracking-normal` | 0 | Body text |
| `--tracking-wide` | 0.02em | Labels |
| `--tracking-wider` | 0.04em | Uppercase labels |
| `--tracking-widest` | 0.08em | All-caps tiny labels |

### Typography Classes

```css
/* Display/Heading hierarchy */
.ds-title-hero     { font-size: 2rem;    font-weight: 700; }
.ds-title-section   { font-size: 1.5rem;  font-weight: 700; }
.ds-title-card      { font-size: 1.25rem; font-weight: 700; }

/* Body text */
.ds-text-body       { font-size: 1rem;      font-weight: 400; line-height: 1.6; }
.ds-text-label      { font-size: 0.8125rem; font-weight: 600; letter-spacing: 0.05em; }

/* Tailwind component classes (Health Dashboard) */
.text-display  → text-2xl font-bold tracking-tight font-display
.text-h1       → text-xl font-bold font-display
.text-h2       → text-lg font-semibold font-display
.text-h3       → text-base font-semibold font-display
.text-body     → text-sm leading-normal
.text-small    → text-xs text-muted-foreground
.text-tiny     → text-[11px] text-muted-foreground

/* Metric values */
.metric-value  → font-mono, tabular-nums, bold, tracking-tight
.tabular-nums  → font-variant-numeric: tabular-nums
```

### Font Features

```css
body {
  font-feature-settings: 'kern' 1, 'liga' 1, 'calt' 1, 'cv11' 1;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
```

---

## Spacing & Layout

### Base Unit: 4px (0.25rem)

**AI Automation UI** (CSS variables):

| Token | Value |
|---|---|
| `--spacing-xs` | `0.125rem` (2px) |
| `--spacing-sm` | `0.375rem` (6px) |
| `--spacing-md` | `0.75rem` (12px) |
| `--spacing-lg` | `1rem` (16px) |
| `--spacing-xl` | `1.5rem` (24px) |
| `--spacing-2xl` | `2rem` (32px) |
| `--spacing-3xl` | `2.5rem` (40px) |

**Health Dashboard** (Tailwind component classes):

| Class | Tailwind | Pixels |
|---|---|---|
| `.spacing-xs` | `space-y-1` | 4px |
| `.spacing-sm` | `space-y-1.5` | 6px |
| `.spacing-md` | `space-y-2` | 8px |
| `.spacing-lg` | `space-y-3` | 12px |
| `.spacing-xl` | `space-y-4` | 16px |
| `.gap-tight` | `gap-2` | 8px |
| `.gap-normal` | `gap-3` | 12px |
| `.gap-loose` | `gap-4` | 16px |

---

## Border Radius

Tighter, more intentional — no pill shapes except full-round badges.

| Token | Value | Pixels |
|---|---|---|
| `--radius-sm` | `0.125rem` | 2px |
| `--radius-md` / Default | `0.25rem` | 4px |
| `--radius-lg` | `0.375rem` | 6px |
| `--radius-xl` | `0.5rem` | 8px |
| `--radius-full` | `9999px` | Pill/circle |

---

## Elevation & Shadows

### Liquid Glass Elevation System (3 Tiers)

| Tier | Class | Background | Blur | Shadow |
|---|---|---|---|---|
| **Surface** | `.ds-surface` / `.elevation-surface` | `var(--card-bg)` | 0px | `0 1px 3px rgba(0,0,0,0.2)` |
| **Raised** | `.ds-raised` / `.elevation-raised` | `rgba(18,18,26, 0.85)` | 16px | `0 4px 12px rgba(0,0,0,0.3), 0 0 0 1px rgba(20,184,166,0.08)` |
| **Floating** | `.ds-floating` / `.elevation-floating` | `rgba(18,18,26, 0.75)` | 24px | `0 8px 24px rgba(0,0,0,0.4), 0 0 0 1px rgba(20,184,166,0.12)` |

### Card Style

```css
.ds-card {
  background: linear-gradient(135deg, var(--card-bg) 0%, var(--card-bg-alt) 100%);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-lg);    /* 6px */
  box-shadow: var(--shadow-card);
  padding: var(--spacing-2xl);         /* 32px */
  backdrop-filter: blur(12px);
}
```

### Shadow Scale (Health Dashboard)

| Token | Value |
|---|---|
| `--shadow-sm` | `0 1px 2px 0 rgb(0 0 0 / 0.04)` |
| `--shadow` | `0 1px 3px 0 rgb(0 0 0 / 0.08), 0 1px 2px -1px rgb(0 0 0 / 0.08)` |
| `--shadow-md` | `0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.06)` |
| `--shadow-lg` | `0 10px 15px -3px rgb(0 0 0 / 0.08), 0 4px 6px -4px rgb(0 0 0 / 0.06)` |
| `--shadow-xl` | `0 20px 25px -5px rgb(0 0 0 / 0.08), 0 8px 10px -6px rgb(0 0 0 / 0.06)` |

---

## Motion & Animation

### Motion Tokens

| Token | Duration | Usage |
|---|---|---|
| `--motion-fast` | `150ms` | Hover states, toggles |
| `--motion-normal` | `250ms` | Page transitions, reveals |
| `--motion-slow` | `400ms` | Complex animations |

### Easing Curves

| Token | Curve | Usage |
|---|---|---|
| `--ease-enter` | `cubic-bezier(0.4, 0, 0.2, 1)` | Elements appearing |
| `--ease-exit` | `cubic-bezier(0.4, 0, 1, 1)` | Elements leaving |
| `ease-spring` | `cubic-bezier(0.68, -0.55, 0.265, 1.55)` | Playful bounces |
| `ease-bounce` | `cubic-bezier(0.68, -0.6, 0.32, 1.6)` | Emphasized bounces |

### Standard Animations

| Animation | Duration | Effect |
|---|---|---|
| `fadeIn` | 300ms | Opacity 0→1 + translateY(10px→0) |
| `fadeInScale` | 400ms | Opacity + scale(0.95→1) |
| `slideUp` | 300ms | translateY(20px→0) |
| `slideDown` | 400ms | translateY(-20px→0) |
| `modalFadeIn` | 200ms | Overlay opacity |
| `modalSlideIn` | 300ms | translateY(100px) + scale(0.9→1) |
| `shimmer` | 2s infinite | Loading skeleton effect |
| `drawLine` | 1s | Sparkline SVG stroke draw |

### Stagger Pattern

```css
.stagger-item { opacity: 0; animation: fadeIn 0.4s ease-out forwards; }
.stagger-item:nth-child(1) { animation-delay: 0.05s; }
.stagger-item:nth-child(2) { animation-delay: 0.1s; }
/* ...increments of 50ms up to child 6 */
```

### Reduced Motion

All apps respect `prefers-reduced-motion: reduce` — animations collapse to 0.01ms.

---

## Components

### Buttons

| Variant | Class | Background | Text |
|---|---|---|---|
| **Primary** | `.ds-btn-primary` / `.btn-primary` | `--accent-primary` (#14b8a6) | Dark bg color |
| **Secondary** | `.ds-btn-secondary` / `.btn-secondary` | `rgba(30, 41, 59, 0.8)` | `--text-secondary` |
| **Danger** | `.ds-btn-danger` / `.btn-danger` | `linear-gradient(#ef4444, #dc2626)` | White |
| **Success** | `.btn-success` | `--status-healthy` | White |

Button properties:
- Padding: `0.5rem 1rem` (primary), `0.75rem 1.5rem` (secondary/danger)
- Border radius: `--radius-md` (4px)
- Active state: `scale(0.98)`
- Transition: `150ms ease-out`

### Badges

```css
.badge-success → px-1.5 py-0.5 rounded text-xs font-medium bg-status-healthy/15 text-status-healthy
.badge-warning → px-1.5 py-0.5 rounded text-xs font-medium bg-status-warning/15 text-status-warning
.badge-error   → px-1.5 py-0.5 rounded text-xs font-medium bg-status-critical/15 text-status-critical
.badge-info    → px-1.5 py-0.5 rounded text-xs font-medium bg-info/15 text-info
```

All badges include `::before` pseudo-element icons (check, warning, cross, info) for color-independent accessibility.

### Cards

```css
/* Health Dashboard */
.card-base  → bg-card rounded border border-border shadow-sm transition-colors
.card-hover → card-base + hover:border-gray-400 cursor-pointer

/* AI Automation UI */
.ds-card    → gradient bg, 1px border, blur(12px), padding 32px

/* Status-aware cards */
.card:has(.status-healthy) → border-left: 4px solid hsl(var(--status-healthy))
.card:has(.status-warning) → border-left: 4px solid hsl(var(--status-warning))
.card:has(.status-error)   → border-left: 4px solid hsl(var(--status-critical))
```

### Inputs

```css
.ds-input / .input-base {
  background: rgba(30, 41, 59, 0.6);     /* dark theme */
  border: 1px solid var(--card-border);
  border-radius: var(--radius-md);         /* 4px */
  padding: 0.75rem 1rem;
  color: var(--text-primary);
  transition: 150ms;
}

/* Focus state */
:focus → ring-2 ring-ring (teal) border-transparent
```

### Modals

```css
.ds-modal-overlay {
  background: linear-gradient(135deg, rgba(10,14,39,0.95), rgba(26,31,58,0.95));
  backdrop-filter: blur(12px);
  z-index: 50;
}
.ds-modal-content {
  max-width: 28rem;
  border-radius: var(--radius-xl);    /* 8px */
  padding: var(--spacing-xl);
}
```

### Progress Bar

```css
.ds-progress-bar  → height: 0.5rem, rounded-full, border
.ds-progress-fill → background: var(--accent-primary), rounded-full
```

---

## Layout Patterns

### Sidebar Navigation (AI Automation UI)

- Desktop: collapsible left rail, 3 sections (Create, Manage, Configure)
- 6 items total: Ideas, Chat, Explore, Insights, Automations, Settings
- Collapsed state persisted in `localStorage`
- Mobile: fixed bottom tab bar with 5 items

### Sidebar Navigation (Health Dashboard)

- Desktop: grouped sidebar with 5 sections
- Mobile: bottom drawer navigation
- Theme toggle (dark/light/ambient) in sidebar

### Observability Dashboard (Streamlit)

- Sidebar radio navigation: Traces, Performance, Live
- Cross-app switcher in sidebar (links to all 3 apps)

### Cross-App Switcher

All 3 apps include a cross-app navigation element:
- Health Dashboard: `http://localhost:3000`
- AI Automation UI: `http://localhost:3001`
- Observability Dashboard: `http://localhost:8501`

### Responsive Breakpoints

| Breakpoint | Width | Usage |
|---|---|---|
| `sm` | 640px | 2-column card grid |
| `md` | 768px | Sidebar visible |
| `lg` | 1024px | 3-column card grid |
| `xl` | 1280px | Full dashboard layout |
| `2xl` | 1536px | Wide containers |

| Special Breakpoint | Query | Usage |
|---|---|---|
| `dashboard` | `(min-width: 1024px) and (min-height: 768px)` | Dashboard optimization |
| `dashboard-wide` | `(min-width: 1280px) and (min-height: 800px)` | Wide dashboard |
| `portrait` / `landscape` | Orientation | Mobile layout switching |

### Responsive Card Grid

```css
.card-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: 1fr;                          /* mobile */
}
@media (min-width: 640px)  { grid-template-columns: repeat(2, 1fr); }
@media (min-width: 1024px) { grid-template-columns: repeat(3, 1fr); }
```

### Scrollbar Styling

```css
::-webkit-scrollbar       { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #475569; border-radius: 4px; }
.scrollbar-hide           { scrollbar-width: none; }
```

---

## Accessibility

### Focus-Visible System

```css
:focus-visible {
  outline: 2px solid var(--focus-ring);     /* rgba(20, 184, 166, 0.5) */
  outline-offset: 2px;
}
:focus:not(:focus-visible) { outline: none; }
```

### Skip-to-Content Link

```css
.skip-to-content {
  position: absolute; top: -40px;
  background: var(--accent-primary);
  color: var(--bg-primary);
  z-index: 100;
}
.skip-to-content:focus { top: 0; }
```

### Color-Independent Status Indicators

Badges use `::before` pseudo-element icons so meaning doesn't rely solely on color:
- Success: `✓` (`\2713`)
- Warning: `⚠` (`\26A0`)
- Error: `✗` (`\2717`)
- Info: `ℹ` (`\2139`)

### High Contrast Mode

```css
@media (prefers-contrast: high) {
  .card-base   { border: 2px solid currentColor; }
  .btn-primary { border: 2px solid currentColor; }
}
```

### Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

### ARIA Patterns

- All nav items include `ariaLabel` attributes
- Sidebar uses `<nav>` landmark element
- Mobile bottom tabs include role and label

---

## Theme Modes

### 3 Modes (Health Dashboard)

| Mode | Activation | Description |
|---|---|---|
| **Light** | `:root` (default) | Clean white/gray backgrounds, teal `168 76% 40%` |
| **Dark** | `.dark` class | Deep blue-black `#0a0a0f`, teal `168 76% 42%` |
| **Ambient** | `.ambient` class | Ultra-dark `224 40% 3%`, reduced saturation, softer shadows |

### 2 Modes (AI Automation UI)

| Mode | Activation | Description |
|---|---|---|
| **Dark** | Default | `--bg-primary: #0a0a0f`, teal `#14b8a6` |
| **Light** | `[data-theme="light"]` / `.light` | `--bg-primary: #f8f9fc`, teal `#0d9488` |

### Theme Switching

- Health Dashboard: class-based (`dark`, `ambient`)
- AI Automation UI: `data-theme` attribute + class
- Both persist theme preference via `localStorage`

---

## Source Files

| File | App | Purpose |
|---|---|---|
| `domains/frontends/ai-automation-ui/src/styles/design-system.css` | Automation UI | CSS variables, utility classes, elevation |
| `domains/frontends/ai-automation-ui/src/utils/designSystem.ts` | Automation UI | TypeScript constants and helper functions |
| `domains/frontends/ai-automation-ui/tailwind.config.js` | Automation UI | Tailwind theme extensions |
| `domains/frontends/ai-automation-ui/src/index.css` | Automation UI | Base styles, scrollbars |
| `domains/core-platform/health-dashboard/src/styles/fonts.css` | Health Dashboard | Typography system, font imports |
| `domains/core-platform/health-dashboard/src/styles/animations.css` | Health Dashboard | Keyframes, animation utilities |
| `domains/core-platform/health-dashboard/src/index.css` | Health Dashboard | CSS variables, component classes, elevation |
| `domains/core-platform/health-dashboard/tailwind.config.js` | Health Dashboard | Full Tailwind config, breakpoints, animations |
| `domains/frontends/observability-dashboard/src/main.py` | Ops Dashboard | Streamlit page config, navigation |
| `docs/frontend-terminology.md` | All | Terminology reference |
