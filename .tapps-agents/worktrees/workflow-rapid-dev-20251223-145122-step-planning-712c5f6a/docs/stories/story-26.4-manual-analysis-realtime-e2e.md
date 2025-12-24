# Story 26.4: Manual Analysis & Real-Time Updates E2E Tests

## Status
Draft

## Story

**As a** QA engineer,
**I want** comprehensive E2E tests for manual analysis triggering and real-time UI updates,
**so that** we can ensure users can manually trigger analysis jobs and see real-time progress and results without page refresh.

## Acceptance Criteria

1. **Test Coverage:** 5 E2E tests for manual analysis workflow, <2 minutes execution (includes wait time)
2. **Trigger Tests:** Manual trigger button works, API call successful, progress indicator appears, job ID returned
3. **Progress Monitoring:** Progress bar updates, status messages accurate, estimated time displayed, can cancel job
4. **Real-Time Updates:** New suggestions appear automatically, UI updates without refresh, WebSocket connection working, MQTT notification received
5. **Error Handling:** Handle trigger failures, handle job timeouts, handle WebSocket disconnection, user-friendly error messages

## Tasks / Subtasks

- [ ] **Task 1:** Create test file `ai-automation-analysis.spec.ts` with mock analysis job
- [ ] **Task 2:** Implement trigger tests (button, API, progress, job ID)
- [ ] **Task 3:** Implement progress monitoring tests (progress bar, status, time, cancel)
- [ ] **Task 4:** Implement real-time update tests (suggestions appear, UI updates, WebSocket, MQTT)
- [ ] **Task 5:** Implement error handling tests (failures, timeouts, disconnection)

## Dev Notes

**Analysis Workflow:**
1. User clicks "Trigger Analysis" button
2. POST `/api/analysis/trigger` → Returns `{job_id, estimated_duration}`
3. Progress modal shows with status updates
4. Poll `/api/analysis/status/{job_id}` every 2 seconds
5. On completion, new suggestions appear
6. MQTT notification sent to Home Assistant

**Key Test Example:**
```typescript
test('trigger manual analysis and monitor progress', async ({ page }) => {
  const dashboardPage = new DashboardPage(page);
  await dashboardPage.goto();
  
  // Mock analysis endpoints
  await page.route('**/api/analysis/trigger', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        status: 'started',
        job_id: 'job-123',
        estimated_duration: 120
      })
    });
  });
  
  await page.route('**/api/analysis/status/job-123', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        status: 'running',
        progress: 50,
        message: 'Analyzing patterns...'
      })
    });
  });
  
  // Trigger analysis
  await page.getByRole('button', { name: 'Trigger Analysis' }).click();
  
  // Verify progress modal
  await expect(page.getByTestId('analysis-progress-modal')).toBeVisible();
  await expect(page.getByText('Analyzing patterns...')).toBeVisible();
  
  // Verify progress bar
  const progressBar = page.getByTestId('progress-bar');
  await expect(progressBar).toHaveAttribute('value', '50');
});

test('new suggestions appear after analysis', async ({ page }) => {
  const dashboardPage = new DashboardPage(page);
  
  // Initial suggestions
  await mockSuggestionsEndpoint(page, [
    { id: 'sug-1', title: 'Old suggestion' }
  ]);
  await dashboardPage.goto();
  
  let count = await dashboardPage.getSuggestionCount();
  expect(count).toBe(1);
  
  // Trigger analysis
  await mockAnalysisTriggerEndpoint(page);
  await page.getByRole('button', { name: 'Trigger Analysis' }).click();
  
  // Wait for completion, then mock new suggestions
  await page.waitForTimeout(3000);
  await mockSuggestionsEndpoint(page, [
    { id: 'sug-1', title: 'Old suggestion' },
    { id: 'sug-2', title: 'New suggestion' }
  ]);
  
  // UI should auto-refresh
  await page.waitForTimeout(1000);
  count = await dashboardPage.getSuggestionCount();
  expect(count).toBe(2);
});
```

**Required data-testid Attributes:**
- `trigger-analysis-button`
- `analysis-progress-modal`
- `progress-bar`
- `progress-status`
- `cancel-analysis-button`

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-18 | 1.0 | Initial story creation | BMad Master |

## Dev Agent Record
(To be filled by dev agent)

## File List
**New Files:**
- `tests/e2e/ai-automation-analysis.spec.ts`

**Modified Files:**
- `services/ai-automation-ui/src/components/AnalysisStatusButton.tsx` (add data-testid)

## QA Results
(To be filled by QA agent)

