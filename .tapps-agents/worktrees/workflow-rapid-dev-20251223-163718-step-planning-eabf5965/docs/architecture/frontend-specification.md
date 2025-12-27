# Front-End Specification & UI Standards

**Version**: 3.0  
**Last Updated**: November 30, 2025  
**Status**: Production-Ready  
**Based On**: Streamlined UI Redesign, AI Automation UX Improvements & 2025 Modern Design Patterns

---

## 📋 Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Design System](#design-system)
3. [Component Patterns](#component-patterns)
4. [Layout Patterns](#layout-patterns)
5. [Accessibility Standards](#accessibility-standards)
6. [Animation Guidelines](#animation-guidelines)
7. [Performance Best Practices](#performance-best-practices)
8. [Reusable Components](#reusable-components)

---

## Design Philosophy

### Core Principles

1. **Streamlined & Professional**
   - Clean, compact interfaces that maximize information density
   - Minimal visual noise and excessive decorations
   - Professional enterprise-ready appearance
   - Efficient use of screen real estate

2. **Glanceable Information Architecture**
   - Most critical information visible above the fold
   - Users should understand system state in < 5 seconds
   - Progressive disclosure: summary first, details on demand

3. **Single Source of Truth**
   - Never duplicate information
   - One metric = one display location
   - Consistency across all tabs

4. **Visual Hierarchy First**
   - Primary info: Largest, most prominent
   - Secondary info: Supporting, contextual
   - Tertiary info: Available via interaction

5. **Actionable Data Only**
   - Show metrics that inform decisions
   - Hide vanity metrics
   - Provide clear next actions

6. **Accessibility is Non-Negotiable**
   - WCAG 2.1 AA compliance minimum
   - Keyboard navigation for all interactions
   - Screen reader compatible
   - Reduced motion support

### Anti-Patterns (What We Avoid)

1. **Bubbly Design Elements**
   - ❌ Excessive rounded corners (rounded-xl, rounded-2xl)
   - ❌ Overly large buttons and pills
   - ❌ Nested rounded elements
   - ❌ Playful gradients and animations

2. **Visual Clutter**
   - ❌ Too many shadows and effects
   - ❌ Excessive padding and spacing
   - ❌ Decorative elements that don't serve function
   - ❌ Complex hover animations

3. **Inconsistent Sizing**
   - ❌ Inconsistent button sizes
   - ❌ Varying text sizes without hierarchy
   - ❌ Misaligned spacing

---

## Design System

### 2025 Modern Design Patterns (NEW)

The latest design system incorporates modern 2025 UI/UX patterns for enhanced user experience:

#### Collapsible Sections Pattern
**Use Case**: Statistics, filters, and information sections that can be hidden to save space

**Implementation**:
```tsx
const [showSection, setShowSection] = useState(true);

<motion.div className="rounded-2xl overflow-hidden transition-all duration-300 
  bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 
  border border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm">
  {/* Header with toggle */}
  <motion.div className="p-4 border-b border-blue-500/20">
    <div className="flex items-center justify-between">
      <h2 className="text-lg font-bold">Section Title</h2>
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setShowSection(!showSection)}
        className="px-4 py-2 rounded-xl font-medium text-sm transition-all
          bg-gradient-to-r from-blue-600 to-purple-600 text-white 
          shadow-lg shadow-blue-500/30"
      >
        <motion.span
          animate={{ rotate: showSection ? 180 : 0 }}
          transition={{ duration: 0.3, ease: "easeInOut" }}
        >
          {showSection ? '▲' : '▼'}
        </motion.span>
        {showSection ? 'Hide' : 'Show'}
      </motion.button>
    </div>
  </motion.div>

  {/* Collapsible Content */}
  <AnimatePresence>
    {showSection && (
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
        className="overflow-hidden"
      >
        <div className="p-6 bg-slate-900/40 backdrop-blur-sm">
          {/* Content here */}
        </div>
      </motion.div>
    )}
  </AnimatePresence>
</motion.div>
```

**Key Features**:
- Smooth height animation (0.4s cubic-bezier easing)
- Rotating arrow indicator
- Gradient button backgrounds
- Glassmorphism effects (backdrop-blur-sm)
- Space-efficient when collapsed

#### Glassmorphism Effects
**Use Case**: Modern frosted glass appearance for cards and overlays

**Implementation**:
```tsx
className="bg-slate-900/40 backdrop-blur-sm border border-blue-500/20"
// or
className="bg-white/60 backdrop-blur-sm border border-blue-200/50"
```

**Patterns**:
- Dark mode: `bg-slate-900/40` or `bg-slate-800/60` with `backdrop-blur-sm`
- Light mode: `bg-white/60` or `bg-white/80` with `backdrop-blur-sm`
- Border: `border-blue-500/20` (dark) or `border-blue-200/50` (light)

#### Gradient Backgrounds
**Use Case**: Hero sections, cards, and buttons with modern gradient aesthetics

**Dark Mode Gradients**:
```tsx
// Card gradient
className="bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20"

// Button gradient
className="bg-gradient-to-r from-blue-600 to-purple-600"

// Text gradient
className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent"
```

**Light Mode Gradients**:
```tsx
// Card gradient
className="bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50"

// Button gradient
className="bg-gradient-to-r from-blue-500 to-purple-500"

// Text gradient
className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent"
```

#### Modern Animation Patterns
**Smooth Transitions**:
```tsx
// Standard transition
transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}

// Hover effects
whileHover={{ scale: 1.05 }}
whileTap={{ scale: 0.95 }}

// Rotating icons
animate={{ rotate: isOpen ? 180 : 0 }}
transition={{ duration: 0.3, ease: "easeInOut" }}
```

**Easing Functions**:
- Standard: `cubic-bezier(0.4, 0, 0.2, 1)` - Smooth, natural
- EaseInOut: `ease-in-out` - Balanced acceleration
- Bounce: `cubic-bezier(0.16, 1, 0.3, 1)` - Playful entrance

#### Enhanced Shadow System
**Modern Shadow Patterns**:
```tsx
// Card shadow with color
className="shadow-2xl shadow-blue-900/20"

// Button shadow
className="shadow-lg shadow-blue-500/30"

// Layered shadows
boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.8), 
           0 0 0 1px rgba(59, 130, 246, 0.2),
           0 0 100px rgba(59, 130, 246, 0.1)"
```

### Color Palette

#### Status Colors
```typescript
const statusColors = {
  // Success/Healthy
  healthy: {
    light: '#10B981',  // green-500
    dark: '#34D399',   // green-400
    bg: {
      light: '#ECFDF5', // green-50
      dark: '#064E3B20' // green-900/20
    },
    border: {
      light: '#6EE7B7', // green-300
      dark: '#047857'   // green-700
    }
  },
  
  // Warning/Degraded
  degraded: {
    light: '#F59E0B',  // yellow-500
    dark: '#FBBF24',   // yellow-400
    bg: {
      light: '#FFFBEB', // yellow-50
      dark: '#78350F20' // yellow-900/20
    },
    border: {
      light: '#FCD34D', // yellow-300
      dark: '#B45309'   // yellow-700
    }
  },
  
  // Error/Unhealthy
  error: {
    light: '#EF4444',  // red-500
    dark: '#F87171',   // red-400
    bg: {
      light: '#FEF2F2', // red-50
      dark: '#7F1D1D20' // red-900/20
    },
    border: {
      light: '#FCA5A5', // red-300
      dark: '#991B1B'   // red-700
    }
  },
  
  // Paused/Inactive
  paused: {
    light: '#6B7280',  // gray-500
    dark: '#9CA3AF',   // gray-400
    bg: {
      light: '#F9FAFB', // gray-50
      dark: '#1F293820' // gray-800/50
    },
    border: {
      light: '#D1D5DB', // gray-300
      dark: '#4B5563'   // gray-600
    }
  },
  
  // Info/Neutral
  info: {
    light: '#3B82F6',  // blue-500
    dark: '#60A5FA',   // blue-400
    bg: {
      light: '#EFF6FF', // blue-50
      dark: '#1E3A8A20' // blue-900/20
    },
    border: {
      light: '#93C5FD', // blue-300
      dark: '#1E40AF'   // blue-700
    }
  }
};
```

#### Semantic Colors
```css
/* Primary Actions */
--color-primary: #3B82F6;       /* blue-500 */
--color-primary-hover: #2563EB; /* blue-600 */

/* Backgrounds */
--bg-light: #F9FAFB;            /* gray-50 */
--bg-dark: #111827;             /* gray-900 */
--bg-card-light: #FFFFFF;       /* white */
--bg-card-dark: #1F2937;        /* gray-800 */

/* Borders */
--border-light: #E5E7EB;        /* gray-200 */
--border-dark: #374151;         /* gray-700 */

/* Text */
--text-primary-light: #111827;  /* gray-900 */
--text-primary-dark: #F9FAFB;   /* gray-50 */
--text-secondary-light: #6B7280; /* gray-500 */
--text-secondary-dark: #9CA3AF;  /* gray-400 */
```

### Typography

#### Font Scale
```css
/* Headings */
.text-hero:     3xl (36px) - System hero status
.text-h1:       2xl (24px) - Page titles
.text-h2:       xl (20px)  - Section headers
.text-h3:       lg (18px)  - Card titles
.text-h4:       base (16px) - Subsection headers

/* Body */
.text-body:     sm (14px)  - Body text
.text-caption:  xs (12px)  - Labels, captions
.text-micro:    xs (11px)  - Footnotes

/* Metrics */
.text-metric-lg: 3xl (36px) - Large metrics
.text-metric-md: 2xl (24px) - Medium metrics
.text-metric-sm: lg (18px)  - Small metrics
```

#### Font Weights
```css
font-bold:      700 - Primary headings, metrics
font-semibold:  600 - Secondary headings
font-medium:    500 - Labels, buttons
font-normal:    400 - Body text
```

#### Line Heights
```css
leading-tight:  1.25 - Headings
leading-normal: 1.5  - Body text
leading-relaxed: 1.75 - Long-form content
```

### Spacing System (Streamlined)

#### Scale (Tailwind) - Updated for Efficiency
```css
0:   0px
1:   4px   (0.25rem) - Micro spacing
2:   8px   (0.5rem)  - Small gaps
3:   12px  (0.75rem) - Standard gaps
4:   16px  (1rem)    - Component padding
6:   24px  (1.5rem)  - Section spacing
8:   32px  (2rem)    - Large sections
```

#### Streamlined Component Spacing
```css
/* Cards - Reduced padding */
card-padding:      p-4 (16px) - was p-6
card-gap:          gap-4 (16px) - was gap-6

/* Sections - Compact spacing */
section-margin:    mb-4 (16px) - was mb-8
section-padding:   py-3 (12px) - was py-6

/* Grids - Tighter spacing */
grid-gap:          gap-4 (16px) - was gap-6
grid-cols:         1/2/3/4 based on breakpoint

/* Micro-spacing - Consistent */
item-spacing:      space-y-1 (4px) - was space-y-2
inline-spacing:    space-x-1 (4px) - was space-x-2

/* Headers - Minimal height */
header-height:     h-12 (48px) - was h-16
header-padding:    px-4 py-2 (16px 8px)
```

#### Space Efficiency Guidelines
- **Headers**: Use `h-12` instead of `h-16` (25% reduction)
- **Padding**: Use `p-4` instead of `p-6` (33% reduction)
- **Margins**: Use `mb-4` instead of `mb-8` (50% reduction)
- **Gaps**: Use `gap-4` instead of `gap-6` (33% reduction)
- **Micro-spacing**: Use `space-y-1` instead of `space-y-2` (50% reduction)

### Shadows (Streamlined)

```css
/* Minimal Shadow Usage */
shadow-sm:   Small elevation (cards) - PREFERRED
shadow:      Default card shadow - USE SPARINGLY
shadow-lg:   AVOID - Too heavy for streamlined design
shadow-xl:   AVOID - Too heavy for streamlined design

/* Preferred Approach */
border:      Simple 1px borders instead of shadows
no-shadow:   Clean, flat design preferred
subtle:      Use shadows only when necessary for hierarchy

/* Custom Shadows - Minimal */
.card-shadow: 0 1px 2px rgba(0,0,0,0.05) - Very subtle
.card-hover-shadow: AVOID - Use border changes instead

/* Anti-Pattern */
❌ shadow-lg, shadow-xl - Too heavy and bubbly
❌ Complex multi-layer shadows
❌ Shadows on every element
```

### Border Radius (Streamlined Standards)

```css
/* NEW STREAMLINED STANDARDS */
rounded:     4px  - Standard elements (buttons, inputs)
rounded-md:  6px  - Cards, containers
rounded-lg:  8px  - Hero sections only
rounded-xl:  AVOID - Too bubbly
rounded-2xl: AVOID - Too bubbly
rounded-full: AVOID - Only for circular elements (avatars)

/* PREFERRED PATTERNS */
border:      Simple 1px borders instead of rounded corners
sharp:       Clean rectangular elements when appropriate
```

---

## Streamlined Component Standards

### Button Standards (NEW)

#### Primary Action Buttons
```tsx
// ✅ CORRECT: Compact, professional
<button className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors">
  Primary Action
</button>

// ❌ AVOID: Bubbly, oversized
<button className="px-6 py-3.5 rounded-xl font-semibold bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-600 shadow-lg hover:shadow-xl">
  Primary Action
</button>
```

#### Secondary Action Buttons
```tsx
// ✅ CORRECT: Clean, minimal
<button className="px-3 py-2 bg-gray-200 hover:bg-gray-300 text-gray-900 text-sm font-medium transition-colors">
  Secondary Action
</button>
```

#### Status Filter Pills
```tsx
// ✅ CORRECT: Compact, clean
<button className="px-3 py-1 text-sm font-medium bg-blue-500 text-white">
  Status
  <span className="ml-1 px-1 text-xs bg-white/20">17</span>
</button>

// ❌ AVOID: Bubbly, oversized
<button className="px-6 py-3 rounded-xl font-semibold shadow-lg">
  Status
  <span className="ml-2 px-2 py-0.5 rounded-full text-xs">17</span>
</button>
```

### Navigation Standards

#### Compact Navigation Bar
```tsx
// ✅ CORRECT: Minimal height, clean spacing
<nav className="h-12 border-b shadow-sm">
  <div className="flex justify-between items-center h-12">
    <div className="flex items-center gap-2">
      <div className="text-xl">🤖</div>
      <div className="text-sm font-semibold">HA AutomateAI</div>
    </div>
    <div className="flex items-center gap-1">
      <Link className="px-3 py-1 text-sm font-medium">Tab</Link>
    </div>
  </div>
</nav>

// ❌ AVOID: Excessive height and spacing
<nav className="h-16 border-b shadow-lg">
  <div className="flex justify-between items-center h-16">
    <div className="flex items-center gap-3">
      <div className="text-3xl">🤖</div>
      <div className="text-lg font-semibold">HA AutomateAI</div>
    </div>
  </div>
</nav>
```

### Card Standards

#### Streamlined Cards
```tsx
// ✅ CORRECT: Clean borders, minimal padding
<div className="border overflow-hidden bg-white">
  <div className="p-4 border-b bg-gray-50">
    <h3 className="text-lg font-semibold">Title</h3>
  </div>
  <div className="p-4">
    Content
  </div>
</div>

// ❌ AVOID: Excessive rounding and shadows
<div className="rounded-2xl shadow-xl bg-white">
  <div className="p-6 rounded-t-2xl bg-gradient-to-r from-blue-50 to-purple-50">
    <h3 className="text-xl font-bold">Title</h3>
  </div>
</div>
```

### Header Standards

#### Compact Page Headers
```tsx
// ✅ CORRECT: Minimal height, essential info only
<div className="border-b pb-3">
  <div className="flex items-center justify-between">
    <div className="flex items-center gap-4">
      <h1 className="text-lg font-semibold">Page Title</h1>
      <span className="text-sm text-gray-500">17 items</span>
    </div>
    <div className="flex items-center gap-3">
      <div className="w-2 h-2 bg-green-500" />
      <span className="text-sm">Ready</span>
      <button className="px-4 py-2 bg-white border text-sm">Action</button>
    </div>
  </div>
</div>

// ❌ AVOID: Excessive height and spacing
<div className="py-8 mb-8">
  <div className="flex items-center justify-between">
    <div className="flex items-center gap-6">
      <h1 className="text-3xl font-bold">Page Title</h1>
      <span className="text-lg text-gray-600">17 items</span>
    </div>
  </div>
</div>
```

---

## Component Patterns

### 1. Status Indicator Pattern

**Use Case**: Display health/operational status

**Anatomy**:
```tsx
<StatusIndicator
  status="operational" | "degraded" | "error"
  size="sm" | "md" | "lg"
  showLabel={boolean}
  animated={boolean}
/>
```

**Implementation**:
```tsx
const StatusIndicator = ({ status, size = 'md', showLabel = true, animated = false }) => {
  const config = {
    operational: { icon: '🟢', label: 'Operational', color: 'text-green-600' },
    degraded: { icon: '🟡', label: 'Degraded', color: 'text-yellow-600' },
    error: { icon: '🔴', label: 'Error', color: 'text-red-600' }
  };
  
  return (
    <div className={`flex items-center space-x-2 ${config[status].color}`}>
      <span className={animated ? 'animate-pulse' : ''}>{config[status].icon}</span>
      {showLabel && <span>{config[status].label}</span>}
    </div>
  );
};
```

**Real Example**: `SystemStatusHero.tsx` (lines 82-111)

---

### 2. Metric Card Pattern

**Use Case**: Display key metrics and KPIs

**Anatomy**:
```tsx
<MetricCard
  title="Events per Minute"
  value={124}
  unit="evt/min"
  trend="up" | "down" | "stable"
  status="good" | "warning" | "error"
  subtitle="Last hour average"
  onClick={handleClick}
/>
```

**Visual Structure**:
```
┌─────────────────────┐
│ Title          [⚡] │ ← Icon/Indicator
├─────────────────────┤
│ 124 evt/min         │ ← Large value
│ ↗️ +12%             │ ← Trend (optional)
│ Last hour average   │ ← Subtitle (optional)
└─────────────────────┘
```

**Color Logic**:
- Value color based on `status` prop
- Green (good), Yellow (warning), Red (error)
- Trend arrow color matches direction

**Real Example**: `CoreSystemCard.tsx` (lines 87-169)

---

### 3. Hero Section Pattern

**Use Case**: Primary focal point for dashboard

**Layout**:
```
┌──────────────────────────────────────────────┐
│ ┌──────────────┐  ┌──────────────────────┐  │
│ │   PRIMARY    │  │   SUPPORTING KPIS    │  │
│ │   STATUS     │  │   Metric 1: Value    │  │
│ │   (60%)      │  │   Metric 2: Value    │  │
│ │              │  │   Metric 3: Value    │  │
│ └──────────────┘  └──────────────────────┘  │
└──────────────────────────────────────────────┘
```

**Grid Layout**:
- Desktop: 60/40 split (3/5 + 2/5 columns)
- Tablet: 50/50 split
- Mobile: Stacked (100% each)

**Visual Characteristics**:
- Large status indicator (3xl text, 6xl icon)
- Colored background matching status
- Border width: 2px (more prominent)
- Shadow: lg (elevated appearance)
- Animation: fade-in-scale on load

**Real Example**: `SystemStatusHero.tsx` (complete component)

---

### 4. Interactive Card Pattern

**Use Case**: Clickable cards that expand for details

**States**:
1. **Default**: Card with summary info
2. **Hover**: Lift effect + shadow increase
3. **Focus**: Blue ring (keyboard nav)
4. **Active/Expanded**: Modal with details

**Implementation**:
```tsx
<div
  onClick={handleExpand}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleExpand();
    }
  }}
  role="button"
  tabIndex={0}
  aria-label="Service card - click for details"
  className="card-hover-lift transition-all-smooth cursor-pointer"
>
  {/* Card content */}
</div>
```

**Accessibility Requirements**:
- `role="button"` for semantic meaning
- `tabIndex={0}` for keyboard focus
- `aria-label` describing the action
- Keyboard handler for Enter/Space
- Visual focus indicator

**Real Example**: `CoreSystemCard.tsx` (lines 87-105)

---

### 5. Modal/Dialog Pattern

**Use Case**: Display detailed information or forms

**Structure**:
```tsx
<div role="dialog" aria-modal="true" className="modal-container">
  {/* Backdrop */}
  <div className="modal-backdrop" onClick={onClose} />
  
  {/* Modal Content */}
  <div className="modal-content animate-modal-content">
    {/* Header */}
    <div className="modal-header">
      <h3 id="modal-title">Title</h3>
      <button onClick={onClose} aria-label="Close">×</button>
    </div>
    
    {/* Body */}
    <div className="modal-body">
      Content
    </div>
    
    {/* Footer */}
    <div className="modal-footer">
      <button onClick={onClose}>Close</button>
    </div>
  </div>
</div>
```

**Accessibility Requirements**:
- Focus trapping (Tab cycles within modal)
- Auto-focus on open (usually close button)
- Escape key closes
- `aria-labelledby` and `aria-describedby`
- Backdrop click closes

**Real Example**: `ServiceDetailsModal.tsx` (complete component)

---

### 6. Sparkline/Chart Pattern

**Use Case**: Lightweight performance visualization

**When to Use Sparkline**:
- ✅ Trend visualization (not precise values)
- ✅ Quick glance patterns
- ✅ Embedded in other components
- ✅ Real-time monitoring

**When to Use Full Chart**:
- Detailed analysis (Analytics tab)
- User needs precise values
- Multiple data series
- Complex interactions (zoom, pan)

**Sparkline Implementation**:
```tsx
// Use native SVG (not Chart.js for sparklines)
<svg width="100%" height={80} viewBox="0 0 600 80">
  <path
    d={generatePath(dataPoints)}
    stroke="#3B82F6"
    strokeWidth="2"
    fill="none"
    className="sparkline-path"  // Animated draw
  />
</svg>
```

**Real Example**: `PerformanceSparkline.tsx` (lines 143-195)

---

### 7. Trend Indicator Pattern

**Use Case**: Show if metric is improving/degrading

**Visual Language**:
- ↗️ Increasing (green) - Positive trend
- ↘️ Decreasing (red) - Negative trend
- ➡️ Stable (gray) - Minimal change

**Threshold Logic**:
```typescript
const threshold = 5; // 5% change triggers up/down
const change = ((current - previous) / previous) * 100;

if (Math.abs(change) < threshold) return 'stable';
if (change > 0) return 'up';
return 'down';
```

**Placement**:
- Next to metrics (inline)
- Small, subtle (not overpowering)
- Optional percentage display

**Real Example**: `TrendIndicator.tsx` (complete component)

---

## Layout Patterns

### 1. Dashboard Grid System

#### Responsive Breakpoints
```css
sm:  640px   - Small tablets
md:  768px   - Tablets
lg:  1024px  - Desktops
xl:  1280px  - Large desktops
2xl: 1536px  - Extra large screens
```

#### Grid Patterns
```tsx
// 4-column grid (responsive)
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
  {items.map(item => <Card key={item.id} {...item} />)}
</div>

// 3-column grid (system components)
<div className="grid grid-cols-1 md:grid-cols-3 gap-6">
  {components.map(c => <CoreSystemCard key={c.id} {...c} />)}
</div>

// 2-column split (hero pattern)
<div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
  <div className="lg:col-span-3">{/* 60% */}</div>
  <div className="lg:col-span-2">{/* 40% */}</div>
</div>
```

### 2. Section Pattern

**Standard Section Structure**:
```tsx
<div className="mb-8">
  {/* Header */}
  <h2 className={`text-xl font-semibold mb-4 ${textColor}`}>
    {icon} Section Title
  </h2>
  
  {/* Content */}
  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
    {content}
  </div>
</div>
```

**Spacing**:
- Section bottom margin: `mb-8` (32px)
- Header bottom margin: `mb-4` (16px)
- Content gap: `gap-6` (24px)

### 3. Container/Max Width

```tsx
// Page container
<main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
  {/* Content */}
</main>
```

**Max widths**:
- `max-w-7xl` (1280px) - Standard dashboard
- `max-w-6xl` (1152px) - Narrower content
- `max-w-4xl` (896px) - Forms, settings

---

## Accessibility Standards

### WCAG 2.1 AA Compliance

#### 1. **Color Contrast**
- **Normal text** (< 18pt): 4.5:1 minimum
- **Large text** (≥ 18pt): 3:1 minimum
- **UI components**: 3:1 minimum

**Testing**:
```bash
# All color combinations tested
Green on white: 4.8:1 ✅
Yellow on white: 4.6:1 ✅
Red on white: 5.2:1 ✅
Blue on white: 4.7:1 ✅
```

#### 2. **Keyboard Navigation**

**Requirements**:
- All interactive elements tabbable
- Logical tab order
- Focus visible (outline/ring)
- No keyboard traps (except modals)
- Enter/Space activates buttons

**Pattern**:
```tsx
<button
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  }}
  className="focus-visible-ring"
  aria-label="Descriptive action"
>
  Button Text
</button>
```

#### 3. **ARIA Labels**

**Regions**:
```tsx
<div role="region" aria-label="System status overview">
<nav role="navigation" aria-label="Quick actions">
<main role="main">
```

**Live Regions**:
```tsx
<div aria-live="polite" aria-atomic="true">
  {/* Status updates announced to screen readers */}
</div>
```

**Dialogs**:
```tsx
<div 
  role="dialog" 
  aria-modal="true"
  aria-labelledby="dialog-title"
  aria-describedby="dialog-description"
>
```

#### 4. **Focus Management**

**Modal Pattern**:
```typescript
useEffect(() => {
  if (isOpen) {
    // Store previously focused element
    const previouslyFocused = document.activeElement;
    
    // Focus first element in modal
    closeButtonRef.current?.focus();
    
    // Restore focus on close
    return () => {
      (previouslyFocused as HTMLElement)?.focus();
    };
  }
}, [isOpen]);
```

**Focus Trap**:
```typescript
const handleKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Tab') {
    const focusable = modal.querySelectorAll('button, [href], input, select');
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
};
```

#### 5. **Screen Reader Support**

**Best Practices**:
- Descriptive link text (not "click here")
- Label all form inputs
- Provide alternative text for visual elements
- Use semantic HTML (header, nav, main, etc.)
- Hide decorative images with `aria-hidden="true"`

---

## Animation Guidelines

### Animation Principles

1. **Purposeful** - Animations should guide attention or provide feedback
2. **Subtle** - Don't distract from content
3. **Fast** - 200-400ms duration (not sluggish)
4. **Easing** - Use cubic-bezier for natural feel
5. **Respectful** - Honor `prefers-reduced-motion`

### Standard Animations

#### Entrance Animations
```css
/* Fade in with slight scale */
@keyframes fadeInScale {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.animate-fade-in-scale {
  animation: fadeInScale 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
```

#### Hover Effects
```css
/* Card lift on hover */
.card-hover-lift:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}
```

#### Modal Animations
```css
/* Modal slide in from bottom */
@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: translateY(100px) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
```

#### Stagger Animations
```css
/* Sequential reveal for lists */
.stagger-item {
  opacity: 0;
  animation: fadeIn 0.4s ease-out forwards;
}

.stagger-item:nth-child(1) { animation-delay: 0.05s; }
.stagger-item:nth-child(2) { animation-delay: 0.1s; }
.stagger-item:nth-child(3) { animation-delay: 0.15s; }
```

### Reduced Motion Support

**Always include**:
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## Performance Best Practices

### 1. React.memo Usage

**When to Use**:
- Component re-renders frequently
- Props change infrequently
- Rendering is expensive (calculations, DOM)

**Pattern**:
```tsx
const MyComponent: React.FC<Props> = ({ prop1, prop2 }) => {
  // Component logic
  return <div>...</div>;
};

export default React.memo(MyComponent);
```

**Real Examples**:
- `SystemStatusHero` - Only update when metrics change
- `CoreSystemCard` - Only update when service data changes
- `PerformanceSparkline` - Only update when data points change

### 2. useMemo for Calculations

**When to Use**:
- Expensive calculations (loops, filters, sorts)
- Derived data from props/state
- Recalculated on every render

**Pattern**:
```tsx
const expensiveValue = useMemo(() => {
  return heavyCalculation(data);
}, [data]); // Only recalculate when data changes
```

**Real Example**: Sparkline path calculation (lines 42-76)

### 3. useCallback for Handlers

**When to Use**:
- Callbacks passed to memoized children
- Event handlers that create closures

**Pattern**:
```tsx
const handleClick = useCallback(() => {
  doSomething(id);
}, [id]); // Only recreate when id changes
```

### 4. Bundle Size Optimization

**Strategies**:
- ✅ Use lightweight SVG for charts (not Chart.js for simple visualizations)
- ✅ Lazy load modals/dialogs
- ✅ Code split by route/tab
- ✅ Tree-shake unused code
- ✅ Optimize images

**Target**:
- Main bundle: < 350 kB gzipped
- Initial load: < 100 kB critical CSS/JS
- Time to Interactive: < 2 seconds

---

## Reusable Components

### Core Component Library

#### 1. SystemStatusHero
**File**: `src/components/SystemStatusHero.tsx`  
**Purpose**: Primary system status display  
**Props**: status, uptime, throughput, latency, errorRate, trends  
**Reusable**: Yes, for any system overview

#### 2. CoreSystemCard
**File**: `src/components/CoreSystemCard.tsx`  
**Purpose**: Display system component with metrics  
**Props**: title, icon, service, status, metrics, uptime  
**Reusable**: Yes, for any service/component display

#### 3. PerformanceSparkline
**File**: `src/components/PerformanceSparkline.tsx`  
**Purpose**: Lightweight trend visualization  
**Props**: data, current, peak, average, unit  
**Reusable**: Yes, for any time-series metric

#### 4. TrendIndicator
**File**: `src/components/TrendIndicator.tsx`  
**Purpose**: Show metric change direction  
**Props**: current, previous, showPercentage  
**Reusable**: Yes, for any numeric metric

#### 5. ServiceDetailsModal
**File**: `src/components/ServiceDetailsModal.tsx`  
**Purpose**: Detail view dialog  
**Props**: title, icon, service, status, details  
**Reusable**: Yes, for any detail display

### Component Composition Pattern

**Example: Building a new dashboard tab**
```tsx
import { SystemStatusHero } from '../components/SystemStatusHero';
import { CoreSystemCard } from '../components/CoreSystemCard';
import { PerformanceSparkline } from '../components/PerformanceSparkline';

export const NewDashboardTab = ({ darkMode }) => {
  return (
    <>
      {/* Hero section */}
      <SystemStatusHero {...heroProps} />
      
      {/* Component cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <CoreSystemCard {...card1Props} />
        <CoreSystemCard {...card2Props} />
        <CoreSystemCard {...card3Props} />
      </div>
      
      {/* Performance chart */}
      <PerformanceSparkline {...chartProps} />
    </>
  );
};
```

---

## Dashboard Tab Standards

### Tab Structure Template

Every tab should follow this structure:

```tsx
export const TabName: React.FC<TabProps> = ({ darkMode }) => {
  // 1. State management
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // 2. Data fetching
  useEffect(() => {
    fetchData();
  }, []);
  
  // 3. Calculations
  const metrics = calculateMetrics(data);
  
  return (
    <>
      {/* Critical Alerts (if applicable) */}
      {alerts && <AlertBanner alerts={alerts} />}
      
      {/* Primary Section - Hero or main content */}
      <div className="mb-8">
        <h2>Primary Section</h2>
        {/* Most important content */}
      </div>
      
      {/* Secondary Section - Supporting info */}
      <div className="mb-8">
        <h2>Secondary Section</h2>
        {/* Supporting content */}
      </div>
      
      {/* Tertiary Section - Actions or details */}
      <div className="mb-8">
        <h2>Quick Actions</h2>
        {/* Buttons, links, etc. */}
      </div>
      
      {/* Footer (optional) */}
    </>
  );
};
```

### Section Ordering Priority

1. **Critical Alerts** - Always at top if present
2. **Status/Hero** - Primary system state
3. **Key Metrics** - Most important numbers
4. **Visualizations** - Charts, graphs
5. **Data Tables/Lists** - Detailed data
6. **Actions** - Buttons, navigation
7. **Footer** - Metadata, links

---

## Form & Input Patterns

### Input Field Pattern

```tsx
<div className="form-group">
  <label 
    htmlFor="input-id"
    className={`block text-sm font-medium mb-2 ${textColor}`}
  >
    Field Label
  </label>
  <input
    id="input-id"
    type="text"
    className={`
      w-full px-4 py-2 rounded-lg border
      focus-visible-ring transition-colors
      ${darkMode 
        ? 'bg-gray-700 border-gray-600 text-white' 
        : 'bg-white border-gray-300 text-gray-900'}
    `}
    aria-describedby="input-help"
  />
  <p id="input-help" className="text-xs text-gray-500 mt-1">
    Helper text
  </p>
</div>
```

### Button Patterns

#### Primary Button
```tsx
<button className={`
  px-6 py-3 rounded-lg font-medium
  transition-colors-smooth focus-visible-ring
  ${darkMode 
    ? 'bg-blue-600 hover:bg-blue-700 text-white' 
    : 'bg-blue-600 hover:bg-blue-700 text-white'}
`}>
  Primary Action
</button>
```

#### Secondary Button
```tsx
<button className={`
  px-6 py-3 rounded-lg font-medium
  transition-colors-smooth focus-visible-ring
  ${darkMode 
    ? 'bg-gray-700 hover:bg-gray-600 text-white' 
    : 'bg-gray-100 hover:bg-gray-200 text-gray-900'}
`}>
  Secondary Action
</button>
```

#### Icon Button
```tsx
<button className={`
  p-2.5 rounded-lg min-w-[44px] min-h-[44px]
  transition-colors focus-visible-ring
  ${darkMode 
    ? 'bg-gray-700 hover:bg-gray-600' 
    : 'bg-gray-100 hover:bg-gray-200'}
`}>
  {icon}
</button>
```

**Touch Target**: Minimum 44x44px (WCAG AAA)

---

## Status Visualization Patterns

### Health Status Display

**3-State System**:
- 🟢 **Operational/Healthy** - All systems normal
- 🟡 **Degraded/Warning** - Some issues, still functional
- 🔴 **Error/Critical** - Immediate attention needed

**Additional States**:
- ⏸️ **Paused/Inactive** - Intentionally stopped
- ❓ **Unknown** - Cannot determine status
- 🔵 **Info** - Informational, non-critical

### Badge Components

```tsx
// Status badge
<span className={`
  inline-flex items-center px-3 py-1 rounded-full
  text-xs font-medium
  ${statusColor}
`}>
  {icon} {label}
</span>

// Count badge
<span className="
  inline-flex items-center justify-center
  w-6 h-6 rounded-full bg-red-500 text-white
  text-xs font-bold
">
  {count}
</span>
```

---

## Data Visualization Guidelines

### When to Use Each Visualization

#### Sparkline
- **Purpose**: Show trend at a glance
- **Use For**: Events/min, throughput, latency
- **Size**: Small (80px height)
- **Interaction**: Minimal (maybe hover tooltip)

#### Bar Chart
- **Purpose**: Compare values across categories
- **Use For**: Service comparisons, event type distribution
- **Size**: Medium (200-300px height)
- **Interaction**: Hover for exact values

#### Line Chart
- **Purpose**: Show change over time with precision
- **Use For**: Analytics, detailed performance analysis
- **Size**: Large (400+ px height)
- **Interaction**: Zoom, pan, tooltips

#### Table
- **Purpose**: Exact values, sortable data
- **Use For**: Event logs, device lists, detailed metrics
- **Size**: Variable
- **Interaction**: Sort, filter, pagination

---

## Loading States

### Skeleton Pattern

```tsx
<div className={`
  animate-pulse rounded-lg
  ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}
  h-24 w-full
`} />
```

**Usage**:
- Show during initial data load
- Maintain layout structure
- Match actual component size
- Graceful degradation

### Spinner Pattern

```tsx
<div className="flex items-center justify-center">
  <div className="
    animate-spin rounded-full h-8 w-8
    border-b-2 border-blue-500
  " />
</div>
```

**When to Use**:
- Inline loading (buttons)
- Small areas
- Quick operations (< 2s expected)

---

## Error States

### Error Display Pattern

```tsx
<div className={`
  rounded-lg p-4 border
  ${darkMode 
    ? 'bg-red-900/20 border-red-500/50 text-red-200' 
    : 'bg-red-50 border-red-300 text-red-800'}
`}>
  <div className="flex items-start space-x-3">
    <span className="text-xl">⚠️</span>
    <div>
      <h4 className="font-semibold mb-1">Error Title</h4>
      <p className="text-sm">Error description</p>
      {retryButton}
    </div>
  </div>
</div>
```

### Empty States

```tsx
<div className="text-center py-12">
  <span className="text-6xl mb-4 block">📭</span>
  <h3 className={`text-lg font-semibold mb-2 ${textColor}`}>
    No data available
  </h3>
  <p className={`text-sm ${mutedColor}`}>
    Description of why empty and what to do
  </p>
  {actionButton}
</div>
```

---

## Dark Mode Implementation

### Theme Toggle Pattern

```tsx
const [darkMode, setDarkMode] = useState(false);

// Apply to document
useEffect(() => {
  if (darkMode) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}, [darkMode]);
```

### Dark Mode Classes

**Pattern**:
```tsx
className={`
  ${darkMode ? 'dark-mode-class' : 'light-mode-class'}
`}

// Or use Tailwind dark: variant
className="bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
```

### Color Selection Guide

**Text**:
- Light: gray-900 (nearly black)
- Dark: gray-50 (nearly white)
- Muted Light: gray-500
- Muted Dark: gray-400

**Backgrounds**:
- Light: white, gray-50
- Dark: gray-900, gray-800

**Borders**:
- Light: gray-200, gray-300
- Dark: gray-700, gray-600

---

## Mobile Responsiveness

### Touch Target Standards

**Minimum Sizes**:
- Buttons: 44x44px (WCAG AAA)
- Interactive cards: 44px min-height
- Tap areas: No overlap, clear boundaries

### Mobile Layout Adaptations

```tsx
// Desktop: Side-by-side
// Mobile: Stacked
<div className="flex flex-col sm:flex-row gap-4">
  <div className="flex-1">Left</div>
  <div className="flex-1">Right</div>
</div>

// Desktop: 3 columns
// Tablet: 2 columns
// Mobile: 1 column
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {items}
</div>

// Hide on mobile
<div className="hidden md:block">Desktop only</div>

// Show only on mobile
<div className="md:hidden">Mobile only</div>
```

### Horizontal Scrolling Pattern

```tsx
<div className="overflow-x-auto scrollbar-hide">
  <div className="flex space-x-2 min-w-max">
    {tabs.map(tab => <TabButton key={tab} />)}
  </div>
</div>
```

---

## Icon Usage

### Icon System

**Current**: Emoji icons (no external library needed)

**Advantages**:
- ✅ Zero dependencies
- ✅ Universal support
- ✅ No font/SVG loading
- ✅ Accessible (proper fallback text)

**Standard Icons**:
```typescript
const iconMap = {
  // Status
  success: '✅',
  warning: '⚠️',
  error: '❌',
  info: 'ℹ️',
  
  // Components
  ingestion: '🔌',
  processing: '⚙️',
  storage: '🗄️',
  database: '🗄️',
  api: '🔌',
  
  // Actions
  refresh: '🔄',
  settings: '⚙️',
  logs: '📜',
  dependencies: '🔗',
  devices: '📱',
  events: '📡',
  
  // Trends
  trending_up: '📈',
  trending_down: '📉',
  trending_flat: '➡️',
  
  // Misc
  home: '🏠',
  alert: '🚨',
  sports: '🏈',
  weather: '🌤️',
  calendar: '📅'
};
```

**Future**: If more complex icons needed, use Heroicons (TailwindCSS ecosystem)

---

## Component API Standards

### Props Interface Pattern

```typescript
export interface ComponentNameProps {
  // Required props first
  title: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  
  // Optional props with defaults
  darkMode?: boolean;
  className?: string;
  
  // Callbacks
  onClick?: () => void;
  onExpand?: () => void;
  
  // Complex objects
  metrics?: {
    primary: MetricValue;
    secondary: MetricValue;
  };
}
```

### Default Props Pattern

```tsx
const ComponentName: React.FC<Props> = ({
  required,
  optional = defaultValue,
  darkMode = false,
  className = ''
}) => {
  // Component logic
};
```

---

## Testing Patterns

### Component Testing (Vitest)

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ComponentName } from './ComponentName';

describe('ComponentName', () => {
  it('renders with required props', () => {
    render(<ComponentName title="Test" status="healthy" />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });
  
  it('supports dark mode', () => {
    const { container } = render(
      <ComponentName darkMode={true} />
    );
    expect(container.firstChild).toHaveClass('dark-mode-class');
  });
  
  it('handles click events', () => {
    const handleClick = vi.fn();
    render(<ComponentName onClick={handleClick} />);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledOnce();
  });
});
```

### Accessibility Testing

```typescript
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

it('has no accessibility violations', async () => {
  const { container } = render(<ComponentName />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

---

## Code Organization

### File Structure

```
src/
├── components/
│   ├── SystemStatusHero.tsx      # Hero components
│   ├── CoreSystemCard.tsx        # Card components
│   ├── PerformanceSparkline.tsx  # Visualization components
│   ├── ServiceDetailsModal.tsx   # Modal components
│   ├── TrendIndicator.tsx        # Utility components
│   └── tabs/
│       └── OverviewTab.tsx       # Tab containers
├── hooks/
│   ├── useHealth.ts              # Data fetching hooks
│   ├── useStatistics.ts
│   └── usePerformanceHistory.ts  # Utility hooks
├── services/
│   └── api.ts                    # API clients
├── types/
│   ├── index.ts                  # Type definitions
│   └── health.ts
└── styles/
    ├── animations.css            # Animation system
    └── dashboard-grid.css        # Layout utilities
```

### Import Order

```tsx
// 1. External dependencies
import React, { useState, useEffect } from 'react';

// 2. Internal hooks
import { useHealth } from '../../hooks/useHealth';

// 3. Components
import { SystemStatusHero } from '../SystemStatusHero';

// 4. Types
import { TabProps } from './types';

// 5. Utilities/Services
import { apiService } from '../../services/api';
```

---

## Deployment Checklist

### Before Deploying New UI

- [ ] TypeScript compilation succeeds (`npm run build`)
- [ ] No linter errors (`npm run lint`)
- [ ] Component tests pass (`npm run test`)
- [ ] E2E tests pass (`npm run test:e2e`)
- [ ] Accessibility audit clean (no axe violations)
- [ ] Dark mode works correctly
- [ ] Mobile responsive (test on 375px, 768px, 1024px)
- [ ] Keyboard navigation works
- [ ] Loading states implemented
- [ ] Error states implemented
- [ ] Performance acceptable (< 2s TTI)

### Build Commands

```bash
# Development build
cd services/health-dashboard
npm run dev

# Production build
npm run build

# Test
npm run test

# Lint
npm run lint

# E2E tests
npm run test:e2e
```

### Docker Deployment

```bash
# Rebuild and restart
docker-compose up -d --build health-dashboard

# View logs
docker logs -f homeiq-dashboard

# Verify health
curl http://localhost:3000/
```

---

## Future Enhancements Backlog

### Planned Improvements

1. **Component Library Expansion**
   - Table component with sorting/filtering
   - Chart component with zoom/pan
   - Form wizard component
   - Toast notification system

2. **Advanced Visualizations**
   - Heatmaps for time-based patterns
   - Gantt charts for timeline views
   - Network graphs for dependencies

3. **User Customization**
   - Draggable dashboard widgets
   - Saved layouts/preferences
   - Custom metric thresholds

4. **Offline Support**
   - Service worker for caching
   - Offline-first architecture
   - Local storage for preferences

---

## Reference Implementation

### Overview Tab
**Location**: `services/health-dashboard/src/components/tabs/OverviewTab.tsx`  
**Status**: ✅ Production-ready reference implementation  
**Features**: All patterns documented above

**Use this as the template for new tabs**:
- Hero section pattern
- Card grid layouts
- Sparkline integration
- Modal interactions
- Accessibility complete
- Animations smooth
- Performance optimized

### Component Examples

All components in the Overview tab serve as reference implementations:
- `SystemStatusHero.tsx` - Hero pattern
- `CoreSystemCard.tsx` - Interactive card pattern
- `PerformanceSparkline.tsx` - Visualization pattern
- `ServiceDetailsModal.tsx` - Modal pattern
- `TrendIndicator.tsx` - Utility component pattern

---

## Quick Start: Building a New Tab

### Step-by-Step Guide

1. **Copy the OverviewTab template**
2. **Replace the hero section** with tab-specific content
3. **Update the grid sections** with your data
4. **Reuse CoreSystemCard** for similar displays
5. **Add PerformanceSparkline** if showing trends
6. **Follow the accessibility checklist**
7. **Add animations** using standard classes
8. **Test with keyboard only**
9. **Test dark mode**
10. **Build and deploy**

---

## Resources & References

### Internal Documentation
- **Overview Tab UX Review**: `implementation/overview-tab-ux-review.md`
- **Phase 1-3 Implementation**: `implementation/overview-tab-phase*-complete.md`
- **Animation System**: `services/health-dashboard/src/styles/animations.css`
- **UX Patterns**: `docs/kb/ux-pattern-quick-reference.md`

### External Resources
- **Tailwind CSS**: https://tailwindcss.com/docs
- **React Accessibility**: https://react.dev/learn/accessibility
- **WCAG 2.1**: https://www.w3.org/WAI/WCAG21/quickref/
- **ARIA Patterns**: https://www.w3.org/WAI/ARIA/apg/

---

## Appendix: Design Tokens

### Complete Token System

```typescript
export const designTokens = {
  colors: {
    status: {
      healthy: '#10B981',
      degraded: '#F59E0B',
      error: '#EF4444',
      paused: '#6B7280',
      info: '#3B82F6'
    }
  },
  
  spacing: {
    cardPadding: '24px',
    sectionMargin: '32px',
    gridGap: '24px',
    microSpacing: '8px'
  },
  
  typography: {
    fontSizes: {
      hero: '36px',
      h1: '24px',
      h2: '20px',
      h3: '18px',
      body: '14px',
      caption: '12px'
    },
    fontWeights: {
      bold: 700,
      semibold: 600,
      medium: 500,
      normal: 400
    }
  },
  
  shadows: {
    card: '0 1px 3px rgba(0,0,0,0.12)',
    hover: '0 20px 25px rgba(0,0,0,0.1)',
    modal: '0 25px 50px rgba(0,0,0,0.25)'
  },
  
  animation: {
    duration: {
      fast: '200ms',
      normal: '300ms',
      slow: '400ms'
    },
    easing: {
      smooth: 'cubic-bezier(0.4, 0, 0.2, 1)',
      bounce: 'cubic-bezier(0.16, 1, 0.3, 1)'
    }
  }
};
```

---

**This specification serves as the definitive guide for all front-end development in the HA Ingestor Dashboard.**

Use the Overview Tab as the reference implementation, and follow these patterns for consistency, accessibility, and quality across all UI components.

---

*Last Updated: November 30, 2025 - Enhanced with 2025 Modern Design Patterns (Collapsible Sections, Glassmorphism, Gradients)*

