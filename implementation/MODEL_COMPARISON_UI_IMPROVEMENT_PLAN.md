# Model Comparison UI Improvement Plan

**Date:** 2025-11-19  
**Status:** Planning  
**Goal:** Fix Model Comparison display and enhance UI with 2025 design patterns

## Issues Identified

1. **Model Comparison Not Displaying**
   - Condition requires `modelComparison.models.length > 0`
   - Data may not be loading or models array is empty
   - No loading/error states for model comparison data

2. **UI/UX Issues**
   - Table layout could be more modern (2025 patterns)
   - Missing visual hierarchy and spacing
   - No empty state when no data
   - Recommendations section could be more prominent
   - Missing visual indicators for cost savings

3. **Design Pattern Alignment**
   - Should match existing modal design system
   - Use consistent card-based layouts
   - Better use of color coding and badges
   - Improved typography and spacing

## 2025 Design Patterns to Apply

### 1. Card-Based Layout
- Use card components for model stats
- Consistent padding and spacing
- Subtle shadows/borders for depth

### 2. Data Visualization
- Progress bars for cost comparison
- Color-coded badges for model types
- Visual indicators for recommendations

### 3. Responsive Design
- Mobile-friendly table (horizontal scroll or cards)
- Adaptive grid layouts
- Touch-friendly interactions

### 4. Modern Typography
- Clear hierarchy (h5, h6, body, caption)
- Consistent font weights
- Proper line heights

### 5. Color System
- Semantic colors (success, warning, info)
- Dark mode support
- Accessible contrast ratios

## Implementation Plan

### Phase 1: Fix Data Loading
1. ✅ Add error handling for model comparison fetch
2. ✅ Add loading state indicator
3. ✅ Show empty state when no models
4. ✅ Debug why data isn't loading

### Phase 2: Improve Table Design
1. ✅ Replace basic table with modern card-based layout
2. ✅ Add visual cost comparison bars
3. ✅ Improve model name display with badges
4. ✅ Add hover states and interactions

### Phase 3: Enhance Recommendations
1. ✅ Make recommendations more prominent
2. ✅ Add visual icons/indicators
3. ✅ Improve cost savings display
4. ✅ Add actionable insights

### Phase 4: Polish & Accessibility
1. ✅ Ensure keyboard navigation
2. ✅ Add ARIA labels
3. ✅ Test dark mode
4. ✅ Verify responsive behavior

## Files to Modify

1. `services/health-dashboard/src/components/ServiceDetailsModal.tsx`
   - Fix conditional rendering
   - Improve Model Comparison section UI
   - Add loading/error states

2. `services/health-dashboard/src/components/ServicesTab.tsx`
   - Ensure model comparison data is fetched
   - Add error handling

3. `services/health-dashboard/src/services/api.ts`
   - Verify API endpoint configuration
   - Add proper error handling

## Success Criteria

- ✅ Model Comparison section displays when data is available
- ✅ Shows empty state when no models
- ✅ Modern, card-based layout
- ✅ Clear visual hierarchy
- ✅ Recommendations are prominent
- ✅ Works in dark mode
- ✅ Responsive on mobile
- ✅ Accessible (keyboard, screen readers)

