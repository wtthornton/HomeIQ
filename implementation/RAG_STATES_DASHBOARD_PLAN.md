# RAG States Dashboard Tracking Plan

**Created:** 2025-01-XX  
**Status:** Planning  
**Target:** HA Ingestor Dashboard (Port 3000)

## Overview

Plan to add Red/Amber/Green (RAG) state tracking to the HA Ingestor Dashboard, leveraging existing components and 2025 patterns. RAG states will provide at-a-glance health indicators for the ingestion pipeline and related services.

## Current State Analysis

### Existing Components & Patterns
- ✅ `CoreSystemCard` - Status cards with green/yellow/red indicators
- ✅ `SystemStatusHero` - Hero section with overall status
- ✅ `StatusCard` - Generic status card component
- ✅ `ConnectionStatusIndicator` - Connection state indicators
- ✅ Health monitoring hooks (`useHealth`, `useStatistics`)
- ✅ API service layer (`apiService.getEnhancedHealth()`)
- ✅ Status color system (green/yellow/red with dark mode support)

### Available Data Sources
- `apiService.getEnhancedHealth()` - Service health with dependencies
- `apiService.getStatistics()` - Metrics including websocket-ingestion stats
- `apiService.getServicesHealth()` - Individual service health status
- Real-time metrics endpoint (`/real-time-metrics`)

## Option 1: Integrated RAG Status Card (Recommended ⭐)

**Approach:** Add a dedicated RAG status card to the Overview tab, positioned alongside existing Core System Components.

### Implementation Details

**Location:** `OverviewTab.tsx` - After Core System Components section

**Component:** New `RAGStatusCard.tsx` component

**Features:**
- Single card showing overall RAG state (Red/Amber/Green)
- Breakdown by component:
  - WebSocket Connection (RAG)
  - Event Processing (RAG)
  - Data Storage (RAG)
  - Overall System (RAG)
- Click to expand for detailed metrics
- Real-time updates (30s polling)
- Dark mode support

**Visual Design:**
```
┌─────────────────────────────────────┐
│ 🚦 RAG Status Monitor               │
├─────────────────────────────────────┤
│ Overall: 🟢 GREEN                   │
│                                     │
│ WebSocket:     🟢 GREEN            │
│ Processing:    🟢 GREEN            │
│ Storage:       🟡 AMBER            │
│                                     │
│ [View Details →]                    │
└─────────────────────────────────────┘
```

**Pros:**
- ✅ Minimal UI changes
- ✅ Leverages existing card patterns
- ✅ Clear, focused information
- ✅ Easy to implement
- ✅ Consistent with existing design

**Cons:**
- ⚠️ Requires new component creation
- ⚠️ Limited space for detailed metrics

**Estimated Effort:** 4-6 hours

---

## Option 2: Enhanced Core System Cards with RAG Indicators

**Approach:** Enhance existing `CoreSystemCard` components to include RAG state indicators alongside current status.

### Implementation Details

**Location:** `CoreSystemCard.tsx` - Add RAG indicator badge

**Changes:**
- Add RAG state calculation based on metrics thresholds
- Display RAG badge (🟢/🟡/🔴) next to status badge
- Tooltip showing RAG calculation details
- Color-coded border based on RAG state

**Visual Design:**
```
┌─────────────────────────────────────┐
│ 🔌 INGESTION          ✅ Healthy 🟢 │
│ WebSocket Connection                 │
├─────────────────────────────────────┤
│ Events per Hour                      │
│ 1,234 evt/h                          │
│                                     │
│ Total Events                         │
│ 45,678 events                        │
│                                     │
│ RAG: 🟢 GREEN                        │
└─────────────────────────────────────┘
```

**RAG Calculation Logic:**
- 🟢 GREEN: All metrics within normal thresholds
- 🟡 AMBER: One or more metrics approaching limits
- 🔴 RED: Critical thresholds exceeded

**Pros:**
- ✅ No new UI components needed
- ✅ RAG visible at a glance
- ✅ Leverages existing card infrastructure
- ✅ Minimal code changes

**Cons:**
- ⚠️ Less prominent than dedicated card
- ⚠️ May clutter existing cards
- ⚠️ Requires threshold configuration

**Estimated Effort:** 3-4 hours

---

## Option 3: RAG Status Bar in Header

**Approach:** Add a compact RAG status indicator to the dashboard header, always visible.

### Implementation Details

**Location:** `Dashboard.tsx` - Header section

**Component:** New `RAGStatusBar.tsx` component

**Features:**
- Compact horizontal bar showing overall RAG state
- Click to expand dropdown with component breakdown
- Real-time updates
- Positioned next to theme toggle/refresh controls

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────┐
│ 🏠 HomeIQ Dashboard    [🟢 RAG: GREEN] [🌙] [🔄] [1h ▼]    │
└─────────────────────────────────────────────────────────────┘
```

**Expanded View:**
```
┌─────────────────────────────────────┐
│ 🚦 RAG Status                       │
├─────────────────────────────────────┤
│ Overall: 🟢 GREEN                   │
│                                     │
│ WebSocket:     🟢 GREEN            │
│ Processing:    🟢 GREEN            │
│ Storage:       🟡 AMBER            │
│                                     │
│ Last Updated: 12:34:56             │
└─────────────────────────────────────┘
```

**Pros:**
- ✅ Always visible (no tab switching)
- ✅ Minimal screen space
- ✅ Quick status check
- ✅ Modern pattern (status bars)

**Cons:**
- ⚠️ Limited space for details
- ⚠️ May be overlooked in header
- ⚠️ Requires header layout adjustment

**Estimated Effort:** 5-7 hours

---

## Option 4: Dedicated RAG Monitoring Tab

**Approach:** Create a new tab specifically for RAG state monitoring with comprehensive metrics and history.

### Implementation Details

**Location:** New `RAGTab.tsx` in `tabs/` directory

**Features:**
- Comprehensive RAG dashboard
- Historical RAG state trends (charts)
- Component-level RAG breakdown
- Threshold configuration
- Alert history for RAG state changes
- Export RAG reports

**Visual Design:**
```
┌─────────────────────────────────────────────────────────┐
│ 🚦 RAG Status Monitor                                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Overall Status: 🟢 GREEN                                 │
│                                                          │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐                │
│ │ WebSocket│ │Processing │ │ Storage  │                │
│ │ 🟢 GREEN │ │🟢 GREEN  │ │🟡 AMBER  │                │
│ └──────────┘ └──────────┘ └──────────┘                │
│                                                          │
│ RAG History (Last 24 Hours)                              │
│ [Chart showing RAG state over time]                     │
│                                                          │
│ Component Details                                        │
│ [Expandable sections with metrics]                     │
└─────────────────────────────────────────────────────────┘
```

**Pros:**
- ✅ Comprehensive monitoring
- ✅ Historical tracking
- ✅ Detailed metrics
- ✅ Professional monitoring dashboard
- ✅ Room for future enhancements

**Cons:**
- ⚠️ Requires tab navigation
- ⚠️ More complex implementation
- ⚠️ Higher development effort
- ⚠️ May be overkill for simple RAG tracking

**Estimated Effort:** 12-16 hours

---

## Option 5: Hybrid Approach (Composite Solution)

**Approach:** Combine Option 1 (RAG Card) + Option 3 (Header Bar) for maximum visibility.

### Implementation Details

**Components:**
1. Compact RAG indicator in header (always visible)
2. Detailed RAG card on Overview tab (expandable details)
3. Optional: RAG tab for historical analysis (future enhancement)

**Visual Flow:**
```
Header: [🟢 RAG: GREEN] → Quick status
   ↓
Overview Tab: [RAG Status Card] → Detailed breakdown
   ↓
RAG Tab (future): Historical analysis & trends
```

**Pros:**
- ✅ Best of both worlds
- ✅ Quick status + detailed view
- ✅ Scalable for future enhancements
- ✅ Follows progressive disclosure pattern

**Cons:**
- ⚠️ More implementation work
- ⚠️ Requires coordination between components
- ⚠️ Slightly more complex

**Estimated Effort:** 8-10 hours

---

## Recommendation: Option 1 (Integrated RAG Status Card) ⭐

### Rationale

1. **Balanced Approach:** Provides clear RAG visibility without overwhelming the UI
2. **Leverages Existing Patterns:** Uses proven `CoreSystemCard` pattern
3. **Quick Implementation:** Minimal code changes, fast to deliver
4. **User-Friendly:** Clear, focused information where users expect it
5. **Extensible:** Can evolve into Option 5 (Hybrid) later if needed

### Implementation Steps

1. **Create RAG Calculation Logic**
   - Define thresholds for RAG states
   - Create utility function `calculateRAGState(metrics)`
   - Map service health to RAG states

2. **Create RAGStatusCard Component**
   - Follow `CoreSystemCard` pattern
   - Display overall RAG + component breakdown
   - Add expandable details modal

3. **Integrate into OverviewTab**
   - Add RAG card after Core System Components
   - Wire up data fetching (use existing hooks)
   - Add real-time updates

4. **Add RAG Types**
   - Extend `types/health.ts` with RAG types
   - Add RAG state enum

5. **Testing**
   - Unit tests for RAG calculation logic
   - Component tests for RAGStatusCard
   - Integration tests for OverviewTab

### RAG Calculation Logic

```typescript
type RAGState = 'green' | 'amber' | 'red';

interface RAGThresholds {
  websocket: {
    green: { latency: 50, errorRate: 0.5 };
    amber: { latency: 100, errorRate: 2.0 };
  };
  processing: {
    green: { throughput: 100, queueSize: 10 };
    amber: { throughput: 50, queueSize: 50 };
  };
  storage: {
    green: { latency: 20, errorRate: 0.1 };
    amber: { latency: 50, errorRate: 1.0 };
  };
}

function calculateRAGState(
  component: 'websocket' | 'processing' | 'storage',
  metrics: ComponentMetrics,
  thresholds: RAGThresholds
): RAGState {
  const componentThresholds = thresholds[component];
  
  // Check if any metric exceeds red threshold
  if (metrics.latency > componentThresholds.amber.latency * 2 ||
      metrics.errorRate > componentThresholds.amber.errorRate * 2) {
    return 'red';
  }
  
  // Check if any metric exceeds amber threshold
  if (metrics.latency > componentThresholds.amber.latency ||
      metrics.errorRate > componentThresholds.amber.errorRate) {
    return 'amber';
  }
  
  return 'green';
}
```

### Component Structure

```
RAGStatusCard/
├── RAGStatusCard.tsx          # Main component
├── RAGStatusCard.test.tsx     # Component tests
├── RAGDetailsModal.tsx        # Expandable details modal
└── utils/
    └── ragCalculations.ts     # RAG calculation logic
```

### API Integration

```typescript
// Use existing hooks
const { health } = useHealth(30000);
const { statistics } = useStatistics('1h', 30000);
const enhancedHealth = useEnhancedHealth(); // New hook or use existing

// Calculate RAG states
const ragStates = useMemo(() => {
  return {
    websocket: calculateRAGState('websocket', websocketMetrics, thresholds),
    processing: calculateRAGState('processing', processingMetrics, thresholds),
    storage: calculateRAGState('storage', storageMetrics, thresholds),
    overall: calculateOverallRAG(componentRAGStates)
  };
}, [health, statistics, enhancedHealth]);
```

---

## Alternative: Option 5 (Hybrid) for Future Enhancement

If Option 1 proves successful and users request more visibility, evolve to Option 5:
- Add header indicator (Option 3)
- Keep Overview card (Option 1)
- Add historical tab (Option 4) if needed

---

## Technical Considerations

### Data Sources
- ✅ `apiService.getEnhancedHealth()` - Service dependencies
- ✅ `apiService.getStatistics()` - Metrics (websocket-ingestion)
- ✅ `apiService.getServicesHealth()` - Individual services
- ⚠️ May need new endpoint for RAG-specific metrics

### Performance
- Use `useMemo` for RAG calculations
- Debounce rapid updates
- Cache thresholds configuration
- Lazy load detailed modal

### Accessibility
- ARIA labels for RAG states
- Color-blind friendly (icons + text)
- Keyboard navigation
- Screen reader announcements

### Dark Mode
- Leverage existing dark mode patterns
- Test RAG colors in both themes
- Ensure sufficient contrast

---

## Next Steps

1. **Review & Approve Plan** - Stakeholder review
2. **Define Thresholds** - Set RAG state thresholds
3. **Create Component** - Implement RAGStatusCard
4. **Integrate** - Add to OverviewTab
5. **Test** - Unit + integration tests
6. **Deploy** - Release to production

---

## Files to Create/Modify

### New Files
- `services/health-dashboard/src/components/RAGStatusCard.tsx`
- `services/health-dashboard/src/components/RAGDetailsModal.tsx`
- `services/health-dashboard/src/utils/ragCalculations.ts`
- `services/health-dashboard/src/types/rag.ts`
- `services/health-dashboard/src/components/__tests__/RAGStatusCard.test.tsx`

### Modified Files
- `services/health-dashboard/src/components/tabs/OverviewTab.tsx`
- `services/health-dashboard/src/types/health.ts` (extend with RAG types)
- `services/health-dashboard/src/services/api.ts` (if new endpoint needed)

---

## Success Metrics

- ✅ RAG states visible on Overview tab
- ✅ Real-time updates (30s polling)
- ✅ Clear visual indicators (🟢🟡🔴)
- ✅ Expandable details available
- ✅ Dark mode support
- ✅ Mobile responsive
- ✅ Accessibility compliant

---

## References

- Existing components: `CoreSystemCard.tsx`, `SystemStatusHero.tsx`
- Health types: `types/health.ts`
- API service: `services/api.ts`
- Dashboard structure: `components/Dashboard.tsx`

