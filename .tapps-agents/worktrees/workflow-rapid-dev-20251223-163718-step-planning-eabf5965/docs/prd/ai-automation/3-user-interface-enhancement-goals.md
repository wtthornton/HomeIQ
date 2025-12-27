# 3. User Interface Enhancement Goals

### 3.1 Integration with Existing UI

**Existing Health Dashboard Architecture (http://localhost:3000):**

The Health Dashboard uses a proven tab-based navigation pattern with:
- 12 tabs (Overview, Services, Dependencies, Devices, Events, Logs, Sports, Data Sources, Energy, Analytics, Alerts, Configuration)
- Dark mode toggle with localStorage persistence
- Auto-refresh capability
- Time range selector
- Mobile-first responsive design
- Error boundaries for graceful failures
- Custom navigation events for cross-linking

**New AI Automation Frontend SHALL Follow Same Patterns:**

```typescript
// Match existing Dashboard.tsx structure
- Tab-based navigation (not sidebar)
- Dark mode prop passed to all components
- TabProps interface for consistency
- Error boundaries around tab content
- Custom hooks for data fetching (useHealth pattern)
- Loading skeletons (SkeletonCard components)
- Modal detail views (ServiceDetailsModal pattern)
```

**Design System Consistency:**

```typescript
// Use existing tailwind.config.js
- CSS Custom Properties (var(--color-primary))
- Design tokens: design-primary, design-success, design-warning, design-error
- Consistent shadows: shadow-design-sm/md/lg/xl
- Animation system: fade-in, slide-up, scale-in
- Dark mode class: 'dark'
- Status color system (getStatusColors helper)
```

---

### 3.2 Screens and Views

#### **Main Dashboard Structure:**

```typescript
// AI Automation Dashboard (Port 3002)
const AI_TAB_CONFIG = [
  { id: 'suggestions', label: '💡 Suggestions', icon: '💡' },
  { id: 'patterns', label: '📊 Patterns', icon: '📊' },
  { id: 'automations', label: '⚙️ Automations', icon: '⚙️' },
  { id: 'insights', label: '🔍 Insights', icon: '🔍' },
];
```

#### **Tab 1: Suggestions Browser (Primary)**

**Layout Pattern:** Card grid with modals (matches OverviewTab's CoreSystemCard)

**Features:**
- Card grid (1/2/3 columns responsive)
- Search and filter controls
- Status badges (pending/approved/deployed/rejected)
- Confidence scores (>70%, >80%, >90%)
- Click card → detail modal
- Modal shows: pattern analysis + YAML preview + approve/reject actions
- Loading skeletons (SkeletonCard pattern)

**Status Colors (from existing getStatusColors):**

```typescript
pending:  blue-100 / blue-900/30 (dark)  ⏳
approved: green-100 / green-900/30       ✅
deployed: purple-100 / purple-900/30     🚀
rejected: red-100 / red-900/30           ❌
```

#### **Tab 2: Patterns Insights**

**Layout Pattern:** Stat cards + charts (matches AnalyticsTab)

**Features:**
- Pattern detection summary (stat cards)
- Category breakdown (time-of-day/co-occurrence/anomaly)
- Pattern chart (PerformanceSparkline style)
- Confidence score indicators
- Pattern detail modals
- Filter by pattern type

#### **Tab 3: Current Automations**

**Layout Pattern:** Search + filters + list (exactly like DevicesTab)

**Features:**
- Search automations by name
- Filter by source (user-created vs AI-deployed)
- Filter by status (active/disabled)
- List view with badges (👤 User / 🤖 AI)
- Detail modal (ServiceDetailsModal pattern)
- Remove AI automations action
- Execution history and success rates
- "View in HA" links (opens HA UI)

#### **Tab 4: Insights Dashboard**

**Layout Pattern:** Hero card + system status (matches OverviewTab)

**Features:**
- Hero card: Last analysis summary
- Stat cards: Suggestions generated/approved/deployed
- API cost tracking (budget monitor)
- Acceptance rate chart
- Pattern trends (last 7 days)
- System status cards (green/yellow/red)
- Service health indicators (Data API, MQTT, LLM API)

---

### 3.3 Reusable Components from Existing Dashboard

**Components to Import/Reuse:**

```typescript
// From existing health-dashboard
import { SkeletonCard } from '../skeletons'
import { ErrorBoundary } from './ErrorBoundary'
import { AlertBanner } from './AlertBanner'

// Pattern-based components to create (matching existing style):
- SuggestionCard (like CoreSystemCard)
- SuggestionDetailModal (like ServiceDetailsModal)
- PatternChartCard (like PerformanceSparkline)
- AutomationListItem (like device list items)
- StatCard (reuse from AnalyticsTab)
```

**Proven UX Patterns to Reuse:**

1. **Search + Filter** (DevicesTab pattern)
2. **Card → Modal detail view** (ServiceDetailsModal pattern)
3. **Loading skeletons** (SkeletonCard components)
4. **Status color system** (getStatusColors helper)
5. **Error boundaries** (graceful degradation)
6. **44px touch targets** (mobile-friendly)
7. **Horizontal tab scrolling** (mobile optimization)
8. **Custom navigation events** (cross-tab linking)

---

### 3.4 Design System Specifications

**TailwindCSS Configuration (from existing health-dashboard):**

```javascript
// Use existing tailwind.config.js
colors: {
  'design-primary': 'var(--color-primary)',     // Blue
  'design-success': 'var(--color-success)',     // Green
  'design-warning': 'var(--color-warning)',     // Yellow
  'design-error': 'var(--color-error)',         // Red
  'design-info': 'var(--color-info)',           // Cyan
}

// Status colors
healthy:  green-100 / green-900/30
degraded: yellow-100 / yellow-900/30
unhealthy: red-100 / red-900/30
paused:   gray-100 / gray-700

// Animations
'fade-in': 'fadeIn 0.5s ease-in-out'
'slide-up': 'slideUp 0.3s ease-out'
'scale-in': 'scaleIn 0.2s ease-out'
```

**Typography:**

```css
H1: text-2xl sm:text-3xl font-bold
H2: text-xl sm:text-2xl font-bold
H3: text-lg font-semibold
Body: text-sm sm:text-base
Small: text-xs sm:text-sm
```

**Spacing:**

```css
gap-4: Cards on mobile
gap-6: Cards on desktop
p-4: Mobile cards
p-6: Desktop cards
p-8: Main container
```

---

### 3.5 Mobile Responsiveness

**Responsive Breakpoints (Tailwind defaults):**

```
sm: 640px   // Tablet
md: 768px   // Desktop
lg: 1024px  // Large desktop
```

**Proven patterns from existing dashboard:**

- Grid: 1 col (mobile) → 2 cols (tablet) → 3-4 cols (desktop)
- Text: text-sm (mobile) → text-base (desktop)
- Padding: p-4 (mobile) → p-6 (desktop)
- Header: stacked (mobile) → side-by-side (desktop)
- Tabs: horizontal scroll (mobile) → full width (desktop)
- Buttons: min-w-[44px] min-h-[44px] (touch-friendly)

---

### 3.6 User Experience Consistency Requirements

**UC1:** The AI Automation frontend SHALL match the existing Health Dashboard's visual design
- ✅ Same tab navigation pattern
- ✅ Same card styles (rounded-lg, shadow-lg, padding)
- ✅ Same status colors (green/yellow/red system)
- ✅ Same modal patterns (ServiceDetailsModal structure)
- ✅ Same emoji icons (💡 🚀 ⚙️ ✅ ❌)

**UC2:** The frontend SHALL reuse proven interaction patterns
- ✅ Search + filters (DevicesTab pattern)
- ✅ Click card → modal details
- ✅ Loading states (SkeletonCard components)
- ✅ Error handling (ErrorBoundary wrapper)
- ✅ Dark mode toggle (header button, localStorage)

**UC3:** The frontend SHALL maintain performance standards
- ✅ Initial load: <2 seconds
- ✅ Tab switching: Instant (no re-fetch)
- ✅ Modal animations: 200-300ms
- ✅ Auto-refresh: 30-60 seconds (optional, user-controlled)

**UC4:** The frontend SHALL provide cross-linking
- ✅ Link from Health Dashboard → AI Automation
- ✅ Link from AI Automation → Health Dashboard Devices tab
- ✅ Custom navigation events for modal cross-linking

**UC5:** The frontend SHALL be mobile-optimized
- ✅ Touch targets: 44px minimum
- ✅ Horizontal scroll tabs (works well on mobile)
- ✅ Responsive grids (1→2→3 columns)
- ✅ Stacked headers on mobile

---

