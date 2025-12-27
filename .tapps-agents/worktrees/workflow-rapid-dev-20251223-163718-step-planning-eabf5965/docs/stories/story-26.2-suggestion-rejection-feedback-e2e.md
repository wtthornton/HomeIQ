# Story 26.2: Suggestion Rejection & Feedback E2E Tests

## Status
Draft

## Story

**As a** QA engineer,
**I want** comprehensive E2E tests for the suggestion rejection and feedback workflow,
**so that** we can ensure users can effectively reject unwanted suggestions, provide feedback, and prevent similar suggestions from appearing.

## Acceptance Criteria

1. **Test Coverage:**
   - Minimum 4 E2E tests for rejection workflow
   - All tests use web-first assertions
   - Tests run in <1 minute with parallel execution
   - Zero flaky tests (100% pass rate)

2. **Rejection Workflow Tests:**
   - Test: Reject suggestion with feedback reason
   - Test: Verify suggestion is hidden from list
   - Test: Check feedback is persisted to database
   - Test: Verify similar suggestions are filtered
   - Handle all rejection reasons (Not useful, Too complex, Already exists, Other)

3. **Feedback Collection:**
   - Verify feedback modal appears on rejection
   - Test all feedback reason options
   - Test custom feedback text input
   - Verify required field validation
   - Test cancel vs confirm actions

4. **UI State Management:**
   - Suggestion disappears from list after rejection
   - Rejection count updates correctly
   - Toast notifications appear with correct messages
   - No errors in console
   - State persists after page refresh

5. **Error Handling:**
   - Test API failure during rejection
   - Test network timeout scenarios
   - Verify error messages are user-friendly
   - Ensure UI doesn't break on error

## Tasks / Subtasks

- [ ] **Task 1: Create Test File and Setup** (AC: 1)
  - [ ] Create `tests/e2e/ai-automation-rejection-workflow.spec.ts`
  - [ ] Import required Page Object Models
  - [ ] Set up beforeEach with mock data
  - [ ] Configure parallel execution

- [ ] **Task 2: Implement Rejection Workflow Tests** (AC: 2)
  - [ ] Test: Reject suggestion with feedback
  - [ ] Test: Verify suggestion hidden from list
  - [ ] Test: Feedback persisted to database
  - [ ] Test: Similar suggestions filtered
  - [ ] Add assertions for each rejection reason

- [ ] **Task 3: Implement Feedback Collection Tests** (AC: 3)
  - [ ] Test feedback modal appearance
  - [ ] Test all feedback reason options
  - [ ] Test custom feedback text input
  - [ ] Test required field validation
  - [ ] Test cancel vs confirm actions

- [ ] **Task 4: UI State Management Tests** (AC: 4)
  - [ ] Verify suggestion removal from list
  - [ ] Check rejection count updates
  - [ ] Validate toast notifications
  - [ ] Test state persistence after refresh
  - [ ] Check console for errors

- [ ] **Task 5: Error Handling Tests** (AC: 5)
  - [ ] Mock API failure scenarios
  - [ ] Test network timeout
  - [ ] Verify error message display
  - [ ] Ensure UI stability on error

## Dev Notes

### Project Context

**AI Automation UI:**
- Rejection workflow: Dashboard → Reject button → Feedback modal → Confirm
- Feedback reasons: "Not useful", "Too complex", "Already exists", "Other"
- Custom feedback: Optional text field for "Other" reason
- API endpoint: `POST /api/suggestions/{id}/reject`

**Backend Behavior:**
- Rejection marks suggestion as `rejected=true` in database
- Feedback stored in `rejection_feedback` field
- Similar suggestions filtered using pattern similarity algorithm
- Rejected suggestions hidden from default view

**UI Components:**
- `SuggestionCard.tsx` - Contains reject button
- `FeedbackModal.tsx` - Feedback collection dialog
- `Dashboard.tsx` - Main suggestion list

### Test Implementation Examples

**Test 1: Reject Suggestion with Feedback**
```typescript
import { test, expect } from '@playwright/test';
import { DashboardPage } from './page-objects/DashboardPage';
import { mockSuggestionsEndpoint, mockRejectEndpoint } from './utils/api-mocks';
import { MockDataGenerator } from './utils/mock-data-generators';

test.describe('Suggestion Rejection Workflow', () => {
  let dashboardPage: DashboardPage;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    
    // Mock API with suggestions
    const suggestions = MockDataGenerator.generateSuggestions({ count: 5 });
    await mockSuggestionsEndpoint(page, suggestions);
    await mockRejectEndpoint(page, true);
    
    await dashboardPage.goto();
  });

  test('reject suggestion with feedback', async ({ page }) => {
    // Step 1: Get initial suggestion count
    const initialCount = await dashboardPage.getSuggestionCount();
    expect(initialCount).toBeGreaterThan(0);
    
    // Step 2: Click reject on first suggestion
    await dashboardPage.rejectSuggestion(0);
    
    // Step 3: Verify feedback modal appears
    const feedbackModal = page.getByTestId('feedback-modal');
    await expect(feedbackModal).toBeVisible();
    
    // Step 4: Select feedback reason
    await page.getByRole('radio', { name: 'Not useful' }).click();
    
    // Step 5: Confirm rejection
    await page.getByRole('button', { name: 'Confirm' }).click();
    
    // Step 6: Verify success toast
    await expect(page.getByTestId('toast-success')).toBeVisible();
    await expect(page.getByTestId('toast-success')).toContainText('rejected');
    
    // Step 7: Verify suggestion removed from list
    const newCount = await dashboardPage.getSuggestionCount();
    expect(newCount).toBe(initialCount - 1);
  });

  test('verify suggestion hidden from list', async ({ page }) => {
    // Get first suggestion ID
    const suggestionId = await dashboardPage.getSuggestionId(0);
    
    // Reject it
    await dashboardPage.rejectSuggestion(0);
    await page.getByRole('radio', { name: 'Too complex' }).click();
    await page.getByRole('button', { name: 'Confirm' }).click();
    
    // Wait for toast to disappear
    await expect(page.getByTestId('toast-success')).toBeHidden();
    
    // Verify suggestion no longer in list
    const suggestionCard = page.getByTestId(`suggestion-${suggestionId}`);
    await expect(suggestionCard).not.toBeVisible();
  });

  test('feedback persisted to database', async ({ page }) => {
    // Intercept rejection API call
    let capturedFeedback: any = null;
    
    await page.route('**/api/suggestions/*/reject', async (route) => {
      const request = route.request();
      capturedFeedback = JSON.parse(request.postData() || '{}');
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });
    
    // Reject with custom feedback
    await dashboardPage.rejectSuggestion(0);
    await page.getByRole('radio', { name: 'Other' }).click();
    await page.getByPlaceholder('Provide feedback').fill('Custom reason here');
    await page.getByRole('button', { name: 'Confirm' }).click();
    
    // Verify feedback was sent to API
    expect(capturedFeedback).toBeDefined();
    expect(capturedFeedback.reason).toBe('Other');
    expect(capturedFeedback.feedback_text).toBe('Custom reason here');
  });

  test('similar suggestions filtered', async ({ page }) => {
    // Mock API to return similar suggestions
    const suggestions = [
      {
        id: 'sug-1',
        title: 'Turn off lights at bedtime',
        pattern_type: 'time-of-day',
        category: 'energy',
      },
      {
        id: 'sug-2',
        title: 'Turn off lights at 11 PM',  // Similar
        pattern_type: 'time-of-day',
        category: 'energy',
      },
      {
        id: 'sug-3',
        title: 'Morning coffee automation',  // Different
        pattern_type: 'co-occurrence',
        category: 'convenience',
      },
    ];
    
    await mockSuggestionsEndpoint(page, suggestions);
    await page.reload();
    
    // Initial count
    let count = await dashboardPage.getSuggestionCount();
    expect(count).toBe(3);
    
    // Reject first suggestion
    await dashboardPage.rejectSuggestion(0);
    await page.getByRole('radio', { name: 'Not useful' }).click();
    await page.getByRole('button', { name: 'Confirm' }).click();
    
    // Wait for filtering
    await page.waitForTimeout(1000);
    
    // Mock API should now filter similar
    await mockSuggestionsEndpoint(page, [suggestions[2]]);  // Only different one
    await page.reload();
    
    // Verify count reduced (both similar suggestions gone)
    count = await dashboardPage.getSuggestionCount();
    expect(count).toBe(1);
  });
});
```

**Test 2: Feedback Modal Interaction**
```typescript
test.describe('Feedback Collection', () => {
  test('feedback modal appearance and interactions', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.goto();
    
    // Click reject
    await dashboardPage.rejectSuggestion(0);
    
    // Verify modal
    const modal = page.getByTestId('feedback-modal');
    await expect(modal).toBeVisible();
    await expect(modal).toContainText('Why are you rejecting this suggestion?');
    
    // Verify all reason options exist
    await expect(page.getByRole('radio', { name: 'Not useful' })).toBeVisible();
    await expect(page.getByRole('radio', { name: 'Too complex' })).toBeVisible();
    await expect(page.getByRole('radio', { name: 'Already exists' })).toBeVisible();
    await expect(page.getByRole('radio', { name: 'Other' })).toBeVisible();
    
    // Verify buttons
    await expect(page.getByRole('button', { name: 'Cancel' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Confirm' })).toBeEnabled();
  });

  test('custom feedback text for Other reason', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.goto();
    await dashboardPage.rejectSuggestion(0);
    
    // Select Other
    await page.getByRole('radio', { name: 'Other' }).click();
    
    // Text field should appear
    const textField = page.getByPlaceholder('Provide feedback');
    await expect(textField).toBeVisible();
    
    // Enter custom text
    await textField.fill('My custom reason for rejection');
    
    // Confirm
    await page.getByRole('button', { name: 'Confirm' }).click();
    
    // Verify success
    await expect(page.getByTestId('toast-success')).toBeVisible();
  });

  test('required field validation', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.goto();
    await dashboardPage.rejectSuggestion(0);
    
    // Try to confirm without selecting reason
    const confirmButton = page.getByRole('button', { name: 'Confirm' });
    await expect(confirmButton).toBeDisabled();
    
    // Select reason
    await page.getByRole('radio', { name: 'Not useful' }).click();
    
    // Button should be enabled
    await expect(confirmButton).toBeEnabled();
  });

  test('cancel action closes modal', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.goto();
    
    const initialCount = await dashboardPage.getSuggestionCount();
    
    // Reject and cancel
    await dashboardPage.rejectSuggestion(0);
    await page.getByRole('button', { name: 'Cancel' }).click();
    
    // Modal should close
    await expect(page.getByTestId('feedback-modal')).not.toBeVisible();
    
    // Suggestion should still be in list
    const newCount = await dashboardPage.getSuggestionCount();
    expect(newCount).toBe(initialCount);
  });
});
```

**Test 3: Error Handling**
```typescript
test.describe('Rejection Error Handling', () => {
  test('handle API failure during rejection', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);
    
    // Mock failure
    await page.route('**/api/suggestions/*/reject', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Database connection failed',
        }),
      });
    });
    
    await dashboardPage.goto();
    await dashboardPage.rejectSuggestion(0);
    await page.getByRole('radio', { name: 'Not useful' }).click();
    await page.getByRole('button', { name: 'Confirm' }).click();
    
    // Verify error toast
    await expect(page.getByTestId('toast-error')).toBeVisible();
    await expect(page.getByTestId('toast-error')).toContainText('failed');
    
    // Modal should close
    await expect(page.getByTestId('feedback-modal')).not.toBeVisible();
    
    // Suggestion should still be in list
    const suggestionCard = page.getByTestId('suggestion-card').first();
    await expect(suggestionCard).toBeVisible();
  });

  test('handle network timeout', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);
    
    // Mock slow response
    await page.route('**/api/suggestions/*/reject', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 10000));
      await route.fulfill({ status: 200 });
    });
    
    await dashboardPage.goto();
    await dashboardPage.rejectSuggestion(0);
    await page.getByRole('radio', { name: 'Not useful' }).click();
    await page.getByRole('button', { name: 'Confirm' }).click();
    
    // Should show loading state
    await expect(page.getByTestId('loading-spinner')).toBeVisible();
    
    // Should timeout and show error
    await expect(page.getByTestId('toast-error')).toBeVisible({ timeout: 15000 });
  });
});
```

### Required UI Components

**Add data-testid attributes:**
- `feedback-modal` - Feedback collection modal
- `feedback-reason-{reason}` - Each radio button option
- `feedback-text-input` - Custom feedback text field
- `feedback-cancel-button` - Cancel button
- `feedback-confirm-button` - Confirm button
- `toast-success` - Success notification
- `toast-error` - Error notification

### Testing

**Test File Location:** `tests/e2e/ai-automation-rejection-workflow.spec.ts`

**Test Standards:**
- TypeScript for all tests
- Use Page Object Models
- Web-first assertions throughout
- Mock all API endpoints
- Test both success and error paths

**Expected Test Count:** 4 comprehensive tests minimum

**Testing Framework:** Playwright 1.56.0

**Test Execution:**
```bash
npx playwright test tests/e2e/ai-automation-rejection-workflow.spec.ts
```

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-18 | 1.0 | Initial story creation | BMad Master |

## Dev Agent Record

### Agent Model Used
(To be filled by dev agent)

### Debug Log References
(To be filled by dev agent)

### Completion Notes List
(To be filled by dev agent)

### File List
**Expected Files Created/Modified:**

**New Files:**
- `tests/e2e/ai-automation-rejection-workflow.spec.ts`

**Modified Files:**
- `services/ai-automation-ui/src/components/SuggestionCard.tsx` (add data-testid)
- `services/ai-automation-ui/src/components/FeedbackModal.tsx` (add data-testid)

**Dependencies:**
- Page Object Models from Story 25.1
- Mock utilities from Story 25.2

## QA Results
(To be filled by QA agent)

