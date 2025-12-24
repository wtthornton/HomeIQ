# Story 26.3: Pattern Visualization E2E Tests

## Status
Draft

## Story

**As a** QA engineer,
**I want** comprehensive E2E tests for pattern visualization and analysis features,
**so that** we can ensure users can effectively view, filter, and analyze detected automation patterns with readable device names and interactive charts.

## Acceptance Criteria

1. **Test Coverage:** 5 E2E tests for pattern visualization, <1 minute execution, zero flaky tests
2. **Pattern Display Tests:** View time-of-day patterns, view co-occurrence patterns, readable device names (not hash IDs), confidence scores displayed
3. **Filtering Tests:** Filter by device, filter by time range, filter by confidence level, filter by pattern type
4. **Chart Interaction Tests:** Chart renders correctly, hover tooltips work, click interactions, zoom/pan functionality (if applicable)
5. **Performance:** Handles 100+ patterns, charts render in <2 seconds, no console errors

## Tasks / Subtasks

- [ ] **Task 1:** Create test file `ai-automation-patterns.spec.ts` with Page Object Models
- [ ] **Task 2:** Implement pattern display tests (time-of-day, co-occurrence, device names, confidence)
- [ ] **Task 3:** Implement filtering tests (device, time, confidence, type)
- [ ] **Task 4:** Implement chart interaction tests (render, tooltips, clicks, zoom)
- [ ] **Task 5:** Performance and validation tests (100+ patterns, render speed, console errors)

## Dev Notes

**Pattern Page Components:**
- `PatternsPage.tsx` - Main pattern list
- `PatternChart.tsx` - Chart.js visualization
- `FilterPills.tsx` - Filter controls

**Data Structure:**
```typescript
interface Pattern {
  id: string;
  pattern_type: 'time-of-day' | 'co-occurrence';
  devices: string[];  // Device friendly names
  time_range?: string;
  confidence: 'high' | 'medium' | 'low';
  occurrences: number;
  created_at: string;
}
```

**Key Test Example:**
```typescript
test('view patterns with readable device names', async ({ page }) => {
  const patternsPage = new PatternsPage(page);
  await patternsPage.goto();
  
  // Verify patterns load
  const patterns = await patternsPage.getPatternList();
  await expect(patterns).toHaveCount({ min: 1 });
  
  // Verify device names are readable (not hashes)
  const firstPattern = patterns.first();
  const deviceText = await firstPattern.getByTestId('pattern-devices').textContent();
  
  // Should contain readable names like "Living Room Light"
  expect(deviceText).not.toMatch(/[a-f0-9]{32}/);  // Not hash IDs
  expect(deviceText).toMatch(/[A-Z][a-z]/);  // Readable text
});

test('filter patterns by confidence level', async ({ page }) => {
  const patternsPage = new PatternsPage(page);
  await patternsPage.goto();
  
  // Filter to high confidence only
  await patternsPage.filterByConfidence('high');
  
  // Verify all visible patterns are high confidence
  const patterns = await patternsPage.getPatternList();
  for (const pattern of await patterns.all()) {
    await expect(pattern).toContainText('high');
  }
});

test('chart renders correctly', async ({ page }) => {
  const patternsPage = new PatternsPage(page);
  await patternsPage.goto();
  
  // Verify chart canvas exists
  const chart = page.locator('canvas').first();
  await expect(chart).toBeVisible();
  
  // Verify chart has data
  const chartData = await page.evaluate(() => {
    const canvas = document.querySelector('canvas');
    const ctx = canvas?.getContext('2d');
    return ctx !== null;
  });
  expect(chartData).toBe(true);
});
```

**Required data-testid Attributes:**
- `patterns-container`
- `pattern-item`
- `pattern-devices`
- `filter-confidence`
- `filter-device`
- `filter-type`
- `pattern-chart`

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-18 | 1.0 | Initial story creation | BMad Master |

## Dev Agent Record
(To be filled by dev agent)

## File List
**New Files:**
- `tests/e2e/ai-automation-patterns.spec.ts`

**Modified Files:**
- `services/ai-automation-ui/src/pages/Patterns.tsx` (add data-testid)
- `services/ai-automation-ui/src/components/PatternChart.tsx` (add data-testid)

## QA Results
(To be filled by QA agent)

