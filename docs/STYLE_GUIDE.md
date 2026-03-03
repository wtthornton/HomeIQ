# HomeIQ Design System Style Guide

> Version 3.0.0 | March 2026
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
12. [Modern CSS Features (2026)](#modern-css-features-2026)
13. [Utility Classes](#utility-classes)
14. [Source Files & Drift Warnings](#source-files--drift-warnings)

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

See [docs/frontend-terminology.md](frontend-terminology.md) for canonical terminology across all apps.

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
| Accent Glow | `--accent-glow` | `rgba(20, 184, 166, 0.12)` | Teal ambient glow |
| Text Primary | `--text-primary` | `#fafafa` | Headings, body |
| Text Secondary | `--text-secondary` | `#d4d4d8` | Descriptions |
| Text Tertiary | `--text-tertiary` | `#a1a1aa` | Labels |
| Text Muted | `--text-muted` | `#71717a` | Placeholders |

#### Interactive State Tokens (Dark)

| Token | CSS Variable | Value | Usage |
|---|---|---|---|
| Hover Background | `--hover-bg` | `rgba(63, 63, 90, 0.3)` | Element hover state |
| Active Background | `--active-bg` | `rgba(63, 63, 90, 0.5)` | Element active/pressed state |
| Focus Ring | `--focus-ring` | `rgba(20, 184, 166, 0.5)` | Focus-visible outline |

#### Glow Tokens (Dark)

| Token | CSS Variable | Value | Usage |
|---|---|---|---|
| Success Glow | `--success-glow` | `rgba(34, 197, 94, 0.15)` | Success state ambient glow |
| Accent Glow | `--accent-glow` | `rgba(20, 184, 166, 0.12)` | Brand color ambient glow |

### Light Theme

| Token | CSS Variable | Value | Usage |
|---|---|---|---|
| Background Primary | `--bg-primary` | `#f8f9fc` | Page background |
| Background Secondary | `--bg-secondary` | `#f0f1f5` | Card backgrounds |
| Background Tertiary | `--bg-tertiary` | `#e5e7ed` | Elevated surfaces |
| Card Background | `--card-bg` | `rgba(255, 255, 255, 0.92)` | Card fills |
| Card Background Alt | `--card-bg-alt` | `rgba(245, 245, 250, 0.95)` | Card gradient end |
| Card Border | `--card-border` | `rgba(0, 0, 0, 0.08)` | Card strokes |
| Accent Primary | `--accent-primary` | `#0d9488` | Teal (darker for contrast) |
| Accent Secondary | `--accent-secondary` | `#b8941f` | Gold (darker for contrast) |
| Accent Glow | `--accent-glow` | `rgba(13, 148, 136, 0.1)` | Teal ambient glow |
| Text Primary | `--text-primary` | `#1a1a2e` | Headings, body |
| Text Secondary | `--text-secondary` | `#4a4a5e` | Descriptions |
| Text Tertiary | `--text-tertiary` | `#6b6b80` | Labels |
| Text Muted | `--text-muted` | `#9ca3af` | Placeholders |

#### Interactive State Tokens (Light)

| Token | CSS Variable | Value |
|---|---|---|
| Hover Background | `--hover-bg` | `rgba(0, 0, 0, 0.04)` |
| Active Background | `--active-bg` | `rgba(0, 0, 0, 0.08)` |
| Focus Ring | `--focus-ring` | `rgba(13, 148, 136, 0.5)` |

#### Light Elevation Shadows

| Token | Value |
|---|---|
| Surface shadow | `0 1px 3px rgba(0, 0, 0, 0.06)` |
| Raised shadow | `0 4px 12px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(13, 148, 136, 0.06)` |
| Floating shadow | `0 8px 24px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(13, 148, 136, 0.08)` |

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

### Smart Home Domain Colors (Health Dashboard — HSL)

| Domain | HSL Variable | Usage |
|---|---|---|
| Weather | `--accent-weather: 199 89% 48%` | Weather data cards |
| Sports | `--accent-sports: 168 76% 40%` (dark: `42%`) | Sports integration |
| Automation | `--accent-automation: 45 93% 47%` | Automation features |
| Energy | `--accent-energy: 142 71% 45%` | Energy analytics |

### Health Dashboard Color Notation

The Health Dashboard uses **HSL values** (via Tailwind/shadcn convention), while the AI Automation UI uses **hex/rgba values**. Both systems are aligned in perceived color:

| Role | AI Automation UI (hex) | Health Dashboard (HSL) |
|---|---|---|
| Primary (dark) | `#14b8a6` | `168 76% 42%` |
| Primary (light) | `#0d9488` | `168 76% 40%` |
| Gold accent | `#d4a847` | `43 70% 48%` |

---

## Typography

### Font Stack

| Role | Font Family | CSS Variable | Fallbacks |
|---|---|---|---|
| **Display** (headings) | Outfit Variable | `--font-display` | Inter, system-ui, sans-serif |
| **Body** (UI text) | Inter Variable | `--font-sans` | system-ui, -apple-system, sans-serif |
| **Mono** (code, metrics) | JetBrains Mono Variable | `--font-mono` | SF Mono, ui-monospace, monospace |

All fonts loaded as variable fonts via `@fontsource-variable/*`.

### Size Scale

| Token | Size | Pixels | Usage |
|---|---|---|---|
| `--text-xs` / `--font-size-xs` | `0.6875rem` | 11px | Tiny labels |
| `--text-sm` / `--font-size-sm` | `0.75rem` | 12px | Small text |
| `--text-base` / `--font-size-base` | `0.875rem` | **14px** (base) | Body text |
| `--font-size-md` | `0.875rem` | 14px | Alias for base |
| `--text-lg` / `--font-size-lg` | `1rem` | 16px | Subheadings, h4 |
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
| `--font-weight-medium` | 500 | Labels, subtle emphasis, h5-h6 |
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
| `--tracking-tighter` | -0.03em | Extra-tight display text |
| `--tracking-tight` | -0.015em | Headings (display font) |
| `--tracking-normal` | 0 | Body text |
| `--tracking-wide` | 0.02em | Labels |
| `--tracking-wider` | 0.04em | Uppercase labels |
| `--tracking-widest` | 0.08em | All-caps tiny labels |

### Typography Classes

```css
/* Display/Heading hierarchy (AI Automation UI) */
.ds-title-hero     { font-size: 2rem;    font-weight: 700; letter-spacing: -0.025em; }
.ds-title-section  { font-size: 1.5rem;  font-weight: 700; letter-spacing: -0.025em; }
.ds-title-card     { font-size: 1.25rem; font-weight: 700; letter-spacing: -0.025em; }

/* Body text (AI Automation UI) */
.ds-text-body      { font-size: 1rem;      font-weight: 400; line-height: 1.6; }
.ds-text-label     { font-size: 0.8125rem; font-weight: 600; letter-spacing: 0.05em; }

/* Tailwind component classes (Health Dashboard) */
.text-display  → text-2xl font-bold tracking-tight font-display
.text-h1       → text-xl font-bold font-display
.text-h2       → text-lg font-semibold font-display
.text-h3       → text-base font-semibold font-display
.text-body     → text-sm leading-normal
.text-small    → text-xs text-muted-foreground
.text-tiny     → text-[11px] text-muted-foreground
.text-label    → text-xs font-semibold tracking-wide text-muted-foreground

/* Metric values */
.metric-value  → font-mono, tabular-nums, bold, tracking-tight
.tabular-nums  → font-variant-numeric: tabular-nums

/* Label text (Health Dashboard — fonts.css) */
.label-text    → font-size-xs, medium weight, uppercase, tracking-wider
```

### Font Features

```css
body {
  font-feature-settings: 'kern' 1, 'liga' 1, 'calt' 1, 'cv11' 1;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

/* Monospace elements disable kerning */
code, pre, kbd, samp, .font-mono {
  font-feature-settings: 'kern' 0, 'liga' 1, 'calt' 1;
  font-size: 0.9em;
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
  -webkit-backdrop-filter: blur(12px);
}
```

### Shadow Scale (AI Automation UI)

| Token | Value |
|---|---|
| `--shadow-card` | `0 4px 6px -1px rgba(0,0,0,0.3), 0 0 0 1px rgba(63,63,90,0.3)` |
| `--shadow-button` | `0 1px 3px 0 rgba(0,0,0,0.2)` |
| `--shadow-hover` | `0 4px 12px -2px rgba(0,0,0,0.25)` |

### Shadow Scale (Health Dashboard — theme-aware)

Light mode values shown; dark mode uses higher opacity (0.25–0.35).

| Token | Value (light) |
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

### Core Animations

| Animation | Duration | Effect |
|---|---|---|
| `fadeIn` | 300ms | Opacity 0→1 + translateY(10px→0) |
| `fadeInScale` | 400ms | Opacity + scale(0.95→1) |
| `slideUp` | 300ms | translateY(20px→0) |
| `slideDown` | 400ms | translateY(-20px→0) |
| `slideInFromRight` | 300ms | translateX(100%→0) |
| `slideInFromLeft` | 300ms | translateX(-100%→0) |
| `scaleIn` | 200ms | scale(0.95→1) + opacity |
| `scaleOut` | 200ms | scale(1→0.95) + opacity |
| `modalFadeIn` | 200ms | Overlay opacity |
| `modalSlideIn` | 300ms | translateY(100px) + scale(0.9→1) |
| `countUp` | 400ms | Opacity + scale(1.1→1) for metric updates |
| `drawLine` | 1s | Sparkline SVG stroke draw |

### Effect Animations

| Animation | Duration | Effect |
|---|---|---|
| `shimmer` | 2s infinite | Loading skeleton gradient sweep |
| `pulseRing` | 1.5s infinite | Ring scale 0.8→1.5, fading out |
| `float` | 3s infinite | Gentle vertical bob (-8px) |
| `glow` | 2s infinite | Opacity pulse (0.6→1→0.6) |
| `wiggle` | 1s infinite | Rotate -3deg to 3deg |
| `tilt` | 10s infinite | Subtle 0.5deg rotation |
| `bounceSubtle` | 600ms | Small bounce (-4px) |
| `pulseGlow` | 2s infinite | Box-shadow pulse using primary color |

### Component Animations (Radix UI / shadcn)

| Animation | Duration | Effect |
|---|---|---|
| `accordion-down` | 200ms | Height 0 → auto |
| `accordion-up` | 200ms | Height auto → 0 |
| `collapsible-down` | 200ms | Height 0 → auto |
| `collapsible-up` | 200ms | Height auto → 0 |

### Tailwind Animation Utilities (Health Dashboard)

```css
/* Speed variants */
animate-fade-in-faster  → fadeIn 0.15s
animate-fade-in-fast    → fadeIn 0.2s
animate-fade-in         → fadeIn 0.4s
animate-fade-in-slow    → fadeIn 0.8s
animate-slide-up-fast   → slideUp 0.15s
animate-slide-up        → slideUp 0.3s
animate-slide-up-slow   → slideUp 0.5s
animate-scale-in        → scaleIn 0.2s
animate-shimmer         → shimmer 2s infinite
animate-pulse-glow      → pulseGlow 2s infinite
animate-spin-slow       → spin 3s infinite
```

### Stagger Pattern

```css
.stagger-item { opacity: 0; animation: fadeIn 0.4s ease-out forwards; }
.stagger-item:nth-child(1) { animation-delay: 0.05s; }
.stagger-item:nth-child(2) { animation-delay: 0.1s; }
/* ...increments of 50ms up to child 6 */
```

### Transition Utilities (Health Dashboard — animations.css)

```css
.transition-all-smooth       → all 0.3s cubic-bezier(0.4, 0, 0.2, 1)
.transition-transform-smooth → transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)
.transition-colors-smooth    → background-color/color/border-color 0.2s ease
```

### Card Hover Effect

```css
.card-hover-lift:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}
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
.card-base  → bg-card rounded border border-border shadow-sm transition-colors duration-150
.card-hover → card-base + hover:border-gray-400 cursor-pointer

/* AI Automation UI */
.ds-card    → gradient bg, 1px border, blur(12px), padding 32px

/* Status-aware cards (uses :has() selector) */
.card:has(.status-healthy) → border-left: 4px solid hsl(var(--status-healthy))
.card:has(.status-warning) → border-left: 4px solid hsl(var(--status-warning))
.card:has(.status-error)   → border-left: 4px solid hsl(var(--status-critical))

/* Corner accents — DISABLED (too decorative) */
.ds-card-corner-accent* → display: none
```

### Inputs

```css
/* AI Automation UI */
.ds-input {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-md);         /* 4px */
  padding: 0.75rem 1rem;
  color: var(--text-primary);
  transition: all 0.2s ease-in-out;
}
.ds-input:focus {
  border-color: rgba(59, 130, 246, 0.5);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* Health Dashboard */
.input-base → w-full px-2.5 py-1.5 border border-input rounded
              bg-background text-sm
              focus:ring-2 focus:ring-ring focus:border-transparent
```

### Modals

```css
.ds-modal-overlay {
  background: linear-gradient(135deg, rgba(10,14,39,0.95), rgba(26,31,58,0.95));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  z-index: 50;
}
.ds-modal-content {
  max-width: 28rem;
  border-radius: var(--radius-xl);    /* 8px */
  padding: var(--spacing-xl);
  box-shadow: var(--shadow-card);
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
| `2xl` | 1536px | Wide containers (max: 1400px) |

#### Height-Based Breakpoints

| Breakpoint | Query | Usage |
|---|---|---|
| `tall-sm` | `(min-height: 640px)` | Taller-than-mobile layouts |
| `tall-md` | `(min-height: 768px)` | Standard desktop height |
| `tall-lg` | `(min-height: 1024px)` | Tall displays |

#### Composite Breakpoints

| Breakpoint | Query | Usage |
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
/* Webkit browsers */
::-webkit-scrollbar       { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #475569; border-radius: 4px; }

/* Standard (Firefox) */
.scrollbar-hide { scrollbar-width: none; }

/* Cross-browser hide */
.scrollbar-hide::-webkit-scrollbar { display: none; }
```

---

## Accessibility

### WCAG 2.2 AA Compliance

All apps target WCAG 2.2 AA minimum:
- **Text contrast**: 4.5:1 for normal text, 3:1 for large text (18pt+ or 14pt+ bold)
- **UI components**: 3:1 contrast ratio for interactive elements
- **Target size**: Minimum 24x24 CSS pixels for interactive targets (WCAG 2.2 SC 2.5.8)
- **Focus appearance**: Visible focus indicator with sufficient area and contrast

### Focus-Visible System

```css
:focus-visible {
  outline: 2px solid var(--focus-ring);     /* rgba(20, 184, 166, 0.5) */
  outline-offset: 2px;
}
:focus:not(:focus-visible) { outline: none; }

/* Additional utility (animations.css) */
.focus-visible-ring:focus-visible {
  outline: 2px solid #14b8a6;
  outline-offset: 2px;
}
```

### Skip-to-Content Link

```css
.skip-to-content {
  position: absolute; top: -40px;
  background: var(--accent-primary);
  color: var(--bg-primary);
  padding: 8px 16px;
  z-index: 100;
  font-size: 0.875rem;
  font-weight: 600;
  transition: top 0.2s;
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
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

### Print Styles

```css
@media print {
  .no-print { display: none !important; }
  body { background: white; color: black; }
}
```

### ARIA Patterns

- All nav items include `ariaLabel` attributes
- Sidebar uses `<nav>` landmark element
- Mobile bottom tabs include role and label
- Accordion/collapsible components use Radix UI primitives for built-in ARIA

---

## Theme Modes

### 3 Modes (Health Dashboard)

| Mode | Activation | Description |
|---|---|---|
| **Light** | `:root` (default) | Clean white/gray backgrounds, teal `168 76% 40%` |
| **Dark** | `.dark` class | Deep blue-black `235 40% 4%`, teal `168 76% 42%` |
| **Ambient** | `.ambient` class | Ultra-dark `224 40% 3%`, reduced saturation, softer shadows |

#### Ambient Theme Details

The ambient mode is designed for low-light dashboard viewing (wall-mounted displays, night mode):

| Token | Ambient Value | Difference from Dark |
|---|---|---|
| Background | `224 40% 3%` | Even darker, warmer undertone |
| Foreground | `0 0% 85%` | Reduced brightness (not pure white) |
| Primary | `168 65% 38%` | Reduced saturation (-11%) and lightness |
| Gold accent | `43 60% 42%` | Reduced saturation (-10%) |
| Status healthy | `142 55% 35%` | Significantly desaturated |
| Status warning | `45 70% 42%` | Reduced saturation |
| Shadows | `0.35–0.45` opacity | Higher opacity for depth on ultra-dark bg |

### 2 Modes (AI Automation UI)

| Mode | Activation | Description |
|---|---|---|
| **Dark** | Default | `--bg-primary: #0a0a0f`, teal `#14b8a6` |
| **Light** | `[data-theme="light"]` / `.light` | `--bg-primary: #f8f9fc`, teal `#0d9488` |

### Theme Switching

- Health Dashboard: class-based (`dark`, `ambient`) on root element
- AI Automation UI: `data-theme` attribute + `.light` class
- Both persist theme preference via `localStorage`

---

## Modern CSS Features (2026)

Features already in use or recommended for adoption. See [The State of CSS in 2026](https://www.codercops.com/blog/state-of-css-2026) and [The Modern CSS Toolkit 2026](https://www.nickpaolini.com/blog/modern-css-toolkit-2026) for browser support data.

### In Use

#### CSS `@layer` (Cascade Layers)

The Health Dashboard uses `@layer base`, `@layer components`, and `@layer utilities` for cascade control:

```css
@layer base { /* CSS variables, element defaults */ }
@layer components { /* Cards, buttons, badges, elevation */ }
@layer utilities { /* Status tints, focus rings, grids */ }
```

#### Container Queries

Used in Health Dashboard for component-level responsive design:

```css
@container (min-width: 768px) {
  .container-responsive {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
  }
}
```

Container queries have ~92% global support and are the 2026 standard for component-based responsive layouts.

#### View Transitions API

Progressive enhancement for page/tab transitions:

```css
@supports (view-transition-name: none) {
  ::view-transition-old(root),
  ::view-transition-new(root) {
    animation-duration: 0.3s;
    animation-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  }
}
```

#### `:has()` Selector

Used for status-aware card styling without JavaScript:

```css
.card:has(.status-healthy) { border-left: 4px solid hsl(var(--status-healthy)); }
```

### Recommended for Adoption

#### `color-mix()` for Alpha Variants

Replace manual rgba values with `color-mix()` to simplify the color system:

```css
/* Current: manual rgba */
--accent-glow: rgba(20, 184, 166, 0.12);

/* 2026 recommended: color-mix() */
--accent-glow: color-mix(in oklch, var(--accent-primary) 12%, transparent);
```

`color-mix()` is baseline 2023 with 95%+ global support.

#### `oklch()` Color Space

The perceptually uniform color space recommended for 2026 design systems. Produces more consistent palette generation than HSL:

```css
/* Future: define palette in oklch for perceptual uniformity */
--accent-primary: oklch(0.72 0.15 175);   /* teal */
--accent-secondary: oklch(0.74 0.12 85);  /* gold */
```

#### `text-wrap: balance`

Prevents orphaned words in headings (baseline 2024):

```css
h1, h2, h3 { text-wrap: balance; }
```

#### `scrollbar-color` / `scrollbar-width`

Standard scrollbar styling (replaces webkit-only pseudo-elements):

```css
* {
  scrollbar-color: #475569 transparent;
  scrollbar-width: thin;
}
```

---

## Utility Classes

### Status Background Tints (Health Dashboard)

```css
.bg-status-healthy-subtle  → bg-status-healthy/5
.bg-status-warning-subtle  → bg-status-warning/5
.bg-status-critical-subtle → bg-status-critical/5
```

### Border Utilities

```css
.border-accent-left → border-l-2
```

### Focus Utilities

```css
.focus-ring → focus:ring-2 focus:ring-ring focus:ring-offset-1
```

### Glow Effects (Disabled)

```css
/* Intentionally disabled — too decorative for data-dense dashboards */
.glow-primary, .glow-success, .glow-warning, .glow-error { /* no-op */ }
```

### Background Utilities

```css
.ds-bg-gradient-primary → background: var(--bg-primary)
.ds-grid-bg             → Subtle 40px grid overlay at 5% opacity
.ds-glow-primary        → 1px border using var(--card-border)
```

---

## Source Files & Drift Warnings

### Source of Truth Files

| File | App | Purpose |
|---|---|---|
| `domains/frontends/ai-automation-ui/src/styles/design-system.css` | Automation UI | CSS variables, utility classes, elevation |
| `domains/frontends/ai-automation-ui/tailwind.config.js` | Automation UI | Tailwind theme extensions |
| `domains/frontends/ai-automation-ui/src/index.css` | Automation UI | Base styles, scrollbars |
| `domains/core-platform/health-dashboard/src/styles/fonts.css` | Health Dashboard | Typography system, font imports |
| `domains/core-platform/health-dashboard/src/styles/animations.css` | Health Dashboard | Keyframes, animation utilities |
| `domains/core-platform/health-dashboard/src/index.css` | Health Dashboard | CSS variables, component classes, elevation |
| `domains/core-platform/health-dashboard/tailwind.config.js` | Health Dashboard | Full Tailwind config, breakpoints, animations |
| `domains/frontends/observability-dashboard/src/main.py` | Ops Dashboard | Streamlit page config, navigation |
| `docs/frontend-terminology.md` | All | Terminology reference |

### Known Drift: `designSystem.ts`

> **WARNING**: `domains/frontends/ai-automation-ui/src/utils/designSystem.ts` is **STALE** and does NOT match `design-system.css`. It still contains the pre-redesign blue palette (`#3b82f6`), old background colors (`#0a0e27`), old border radii, and "2025 design" comments. **Do not use this file as a source of truth.** The CSS file (`design-system.css`) is canonical. This TypeScript file needs a full rewrite to align with the current design system.

| Issue | `designSystem.ts` (stale) | `design-system.css` (correct) |
|---|---|---|
| Primary accent | `#3b82f6` (blue) | `#14b8a6` (teal) |
| Background primary | `#0a0e27` | `#0a0a0f` |
| Background secondary | `#1a1f3a` | `#12121a` |
| Card border | `rgba(51, 65, 85, 0.5)` | `rgba(63, 63, 90, 0.5)` |
| Success color | `#10b981` | `#22c55e` |
| Border radius md | `0.5rem` (8px) | `0.25rem` (4px) |
| Border radius lg | `0.75rem` (12px) | `0.375rem` (6px) |
| Shadows | Blue-tinted | Neutral |
| Corner accents | Active | **Disabled** in CSS |

---

*Last audited: March 2, 2026 against all source CSS, Tailwind configs, and implementation files.*
