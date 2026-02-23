# Refactoring Plan - Story 32.1
**Date:** October 20, 2025  
**Components:** AnalyticsPanel, AlertsPanel

---

## Current Complexity Analysis

### AnalyticsPanel.tsx
- **Lines:** 351 (target: ≤100 per function)
- **Complexity:** 54 (target: ≤15)
- **Issues:**
  - Arrow function too long
  - Complexity too high
  - Missing return types (3 functions)
  - React Hook dependency warning
  - Nested ternary
  - Unused type definition
  - Explicit `any` type

**Extraction Candidates:**
1. **Custom Hook:** `useAnalyticsData` - data fetching logic (lines 66-92)
2. **Helper Functions:** `getTrendIcon`, `getTrendColor` (lines 94-117)
3. **Sub-Components:**
   - `AnalyticsSummaryCard` - summary statistics
   - `AnalyticsMetricCard` - individual metric display
   - `AnalyticsChart` - chart rendering
   - `AnalyticsFilters` - time range selection
   - `AnalyticsLoadingState` - loading skeleton
   - `AnalyticsErrorState` - error display

### AlertsPanel.tsx
- **Lines:** 390 (target: ≤100 per function)
- **Complexity:** 44 + 22 (line 266) (target: ≤15)
- **Issues:**
  - Arrow function too long
  - Two high-complexity sections
  - Missing return types (5 functions)
  - Unused imports
  - String concatenation instead of template literal
  - Nested ternary

**Extraction Candidates:**
1. **Custom Hook:** Alert management already exists in `useAlerts`
2. **Helper Functions:** `getSeverityColor`, `getSeverityIcon`, `formatTimestamp` (lines 28-72)
3. **Sub-Components:**
   - `AlertCard` - individual alert display
   - `AlertFilters` - severity/service filters
   - `AlertStats` - alert statistics
   - `AlertActions` - acknowledge/resolve buttons
   - `AlertEmptyState` - no alerts display

---

## Refactoring Sequence

### Phase 1: AnalyticsPanel (Priority)
1. Create `hooks/useAnalyticsData.ts`
2. Create `utils/analyticsHelpers.ts` for helper functions
3. Create sub-components in `components/analytics/`:
   - `AnalyticsSummaryCard.tsx`
   - `AnalyticsMetricCard.tsx`
   - `AnalyticsFilters.tsx`
   - `AnalyticsLoadingState.tsx`
   - `AnalyticsErrorState.tsx`
4. Refactor main `AnalyticsPanel.tsx` to use extracted components

### Phase 2: AlertsPanel
1. Create `utils/alertHelpers.ts` for helper functions
2. Create sub-components in `components/alerts/`:
   - `AlertCard.tsx`
   - `AlertFilters.tsx`
   - `AlertStats.tsx`
   - `AlertEmptyState.tsx`
3. Refactor main `AlertsPanel.tsx` to use extracted components

### Phase 3: Testing & Validation
1. Run Vitest tests
2. Run Playwright E2E tests
3. Manual QA
4. Verify ESLint compliance

---

## File Structure

```
domains/core-platform/health-dashboard/src/
├── hooks/
│   └── useAnalyticsData.ts (NEW)
├── utils/
│   ├── analyticsHelpers.ts (NEW)
│   └── alertHelpers.ts (NEW)
├── components/
│   ├── analytics/ (NEW DIRECTORY)
│   │   ├── AnalyticsSummaryCard.tsx
│   │   ├── AnalyticsMetricCard.tsx
│   │   ├── AnalyticsFilters.tsx
│   │   ├── AnalyticsLoadingState.tsx
│   │   └── AnalyticsErrorState.tsx
│   ├── alerts/ (NEW DIRECTORY)
│   │   ├── AlertCard.tsx
│   │   ├── AlertFilters.tsx
│   │   ├── AlertStats.tsx
│   │   └── AlertEmptyState.tsx
│   ├── AnalyticsPanel.tsx (REFACTORED)
│   └── AlertsPanel.tsx (REFACTORED)
```

---

## Success Criteria

- [ ] AnalyticsPanel complexity ≤15
- [ ] AlertsPanel complexity ≤15
- [ ] All components <100 lines
- [ ] All functions have return types
- [ ] ESLint warnings eliminated
- [ ] All tests pass
- [ ] UI functionality unchanged

**Status:** In Progress  
**Current Phase:** Phase 1 - AnalyticsPanel Refactoring

