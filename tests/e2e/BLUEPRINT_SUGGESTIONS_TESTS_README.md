# Blueprint Suggestions - Playwright UI/UX Tests

Comprehensive end-to-end tests for the Blueprint Suggestions page at `http://localhost:3001/blueprint-suggestions`.

## Overview

These tests cover the complete user experience of the Blueprint Suggestions feature, including:

- **Page Load & Navigation** - Initial page load, URL verification, element visibility
- **Stats Display** - Statistics cards, numeric values, updates after actions
- **Filters** - Min score, use case, status, blueprint ID filters and combinations
- **Suggestion Cards** - Display, content, matched devices, button states
- **Accept/Decline Actions** - User interactions, navigation, status updates
- **Generate Form** - Form visibility, field interactions, submission
- **Delete All** - Confirmation dialog, deletion flow
- **Pagination** - Navigation between pages, button states
- **Loading & Empty States** - Loading indicators, empty state messages
- **Error Handling** - API error scenarios, error toasts
- **Accessibility** - Heading structure, button labels, form labels
- **User Journeys** - Complete workflows from start to finish

## Test Files

- **`blueprint-suggestions.spec.ts`** - Main test suite
- **`page-objects/BlueprintSuggestionsPage.ts`** - Page Object Model for interactions

## Running Tests

### Run All Blueprint Suggestions Tests

```bash
# From tests/e2e directory
npx playwright test blueprint-suggestions.spec.ts

# Or from project root
npx playwright test tests/e2e/blueprint-suggestions.spec.ts
```

### Run Specific Test Suites

```bash
# Page load tests only
npx playwright test blueprint-suggestions.spec.ts -g "Page Load"

# Filter tests only
npx playwright test blueprint-suggestions.spec.ts -g "Filters"

# Accept/Decline tests only
npx playwright test blueprint-suggestions.spec.ts -g "Accept/Decline"

# Smoke tests (critical path)
npx playwright test blueprint-suggestions.spec.ts -g "@smoke"
```

### Run in Different Modes

```bash
# Debug mode (step through tests)
npx playwright test blueprint-suggestions.spec.ts --debug

# UI mode (interactive test runner)
npx playwright test blueprint-suggestions.spec.ts --ui

# Headed mode (see browser)
npx playwright test blueprint-suggestions.spec.ts --headed

# Specific browser
npx playwright test blueprint-suggestions.spec.ts --project=chromium
```

## Prerequisites

1. **Services Running**: The AI Automation UI must be running on `http://localhost:3001`
2. **Blueprint Suggestion Service**: Backend service must be available and responding
3. **Test Data**: Some tests require existing suggestions (they will skip if none available)

## Test Structure

### Page Object Model

The `BlueprintSuggestionsPage` class provides a clean interface for all interactions:

```typescript
import { BlueprintSuggestionsPage } from './page-objects/BlueprintSuggestionsPage';

test('example', async ({ page }) => {
  const blueprintPage = new BlueprintSuggestionsPage(page);
  
  // Navigate
  await blueprintPage.goto();
  
  // Filter suggestions
  await blueprintPage.setMinScoreFilter(0.8);
  await blueprintPage.setUseCaseFilter('security');
  
  // Interact with suggestions
  await blueprintPage.acceptSuggestion(0);
  await blueprintPage.waitForSuccessToast(/accepted/i);
});
```

### Test Organization

Tests are organized into logical groups:

1. **Page Load and Navigation** - Basic page functionality
2. **Stats Display** - Statistics cards and updates
3. **Filters** - All filter types and combinations
4. **Suggestion Cards** - Card display and content
5. **Accept/Decline Actions** - User actions and feedback
6. **Generate Form** - Form interactions and submission
7. **Delete All** - Deletion flow with confirmation
8. **Pagination** - Page navigation
9. **Loading and Empty States** - State management
10. **Error Handling** - Error scenarios
11. **Accessibility** - A11y compliance
12. **User Journeys** - Complete workflows

## Key Test Scenarios

### Critical Path (@smoke)

1. **Page loads successfully** - Verifies basic page functionality
2. **Accept suggestion** - Tests core accept workflow
3. **Complete user journey** - End-to-end workflow test

### Filter Tests

- Min score filter (0-100%)
- Use case filter (convenience, security, energy, comfort)
- Status filter (pending, accepted, declined)
- Blueprint ID filter (text search)
- Multiple filters combined

### Interaction Tests

- Accept suggestion → Navigate to HA Agent
- Decline suggestion → Update status
- Generate suggestions → Update list
- Delete all → Confirmation → Empty state

### Edge Cases

- Empty state when no suggestions
- Disabled buttons for accepted/declined suggestions
- Pagination on first/last page
- API error handling

## Page Object Methods

### Navigation
- `goto()` - Navigate to page
- `waitForPageReady()` - Wait for initial load

### Stats
- `getTotalStat()` - Get total suggestions count
- `getPendingStat()` - Get pending count
- `getAcceptedStat()` - Get accepted count
- `getAverageScoreStat()` - Get average score

### Filters
- `setMinScoreFilter(value)` - Set min score (0-1)
- `setUseCaseFilter(useCase)` - Filter by use case
- `setStatusFilter(status)` - Filter by status
- `setBlueprintIdFilter(id)` - Filter by blueprint ID

### Suggestions
- `getSuggestionCount()` - Get number of suggestions
- `getSuggestionCard(index)` - Get suggestion card by index
- `getSuggestionData(index)` - Get structured data from card
- `acceptSuggestion(index)` - Accept a suggestion
- `declineSuggestion(index)` - Decline a suggestion

### Generate Form
- `toggleGenerateForm()` - Show/hide form
- `fillGenerateForm(params)` - Fill form fields
- `submitGenerateForm()` - Submit generation request

### Pagination
- `goToNextPage()` - Navigate to next page
- `goToPreviousPage()` - Navigate to previous page
- `getPaginationInfo()` - Get pagination text

### Utilities
- `waitForToast(message)` - Wait for toast notification
- `waitForSuccessToast()` - Wait for success toast
- `waitForErrorToast()` - Wait for error toast
- `deleteAllSuggestions(confirm)` - Delete all with confirmation

## Test Data Requirements

### Required for Full Test Coverage

1. **Suggestions in Database**:
   - At least 1 pending suggestion (for accept/decline tests)
   - Suggestions with different scores (for filter tests)
   - Suggestions with different use cases
   - More than 50 suggestions (for pagination tests)

2. **Backend Services**:
   - Blueprint suggestion service running on port 8032
   - Data API service available
   - Blueprint index service available

### Test Skipping

Tests automatically skip when:
- No suggestions available (for interaction tests)
- Pagination not needed (for pagination tests)
- Specific conditions not met

## Debugging Failed Tests

### Common Issues

1. **Service Not Running**
   ```
   Error: net::ERR_CONNECTION_REFUSED
   ```
   **Solution**: Ensure AI Automation UI is running on `http://localhost:3001`

2. **Timeout Errors**
   ```
   Timeout 10000ms exceeded
   ```
   **Solution**: Increase timeout or check network conditions

3. **Element Not Found**
   ```
   Locator not found
   ```
   **Solution**: Check if page structure changed, update selectors

### Debug Commands

```bash
# Run with debug output
DEBUG=pw:api npx playwright test blueprint-suggestions.spec.ts

# Run specific test in debug mode
npx playwright test blueprint-suggestions.spec.ts -g "Page loads" --debug

# Show test trace
npx playwright show-trace trace.zip
```

### Screenshots and Videos

Failed tests automatically capture:
- **Screenshots**: `test-results/blueprint-suggestions-*.png`
- **Videos**: `test-results/blueprint-suggestions-*.webm`
- **Traces**: `test-results/blueprint-suggestions-*.zip`

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run Blueprint Suggestions Tests
  run: |
    cd tests/e2e
    npx playwright test blueprint-suggestions.spec.ts
    npx playwright show-report
```

### Test Reports

Reports are generated automatically:
- **HTML**: `playwright-report/index.html`
- **JSON**: `test-results/results.json`
- **JUnit**: `test-results/results.xml`

## Maintenance

### When to Update Tests

1. **UI Changes**: Update selectors when page structure changes
2. **New Features**: Add tests for new functionality
3. **Bug Fixes**: Add regression tests for fixed bugs
4. **API Changes**: Update API interaction patterns

### Best Practices

1. **Use Page Object Model**: All interactions through `BlueprintSuggestionsPage`
2. **Wait for States**: Always wait for loading/ready states
3. **Handle Edge Cases**: Test empty states, errors, edge conditions
4. **Tag Tests**: Use `@smoke` for critical path tests
5. **Skip When Appropriate**: Skip tests when prerequisites not met

## Related Documentation

- **Component**: `services/ai-automation-ui/src/pages/BlueprintSuggestions.tsx`
- **API Client**: `services/ai-automation-ui/src/services/blueprintSuggestionsApi.ts`
- **Backend Service**: `services/blueprint-suggestion-service/`
- **E2E Testing Guide**: `tests/E2E_TESTING_GUIDE.md`

## Test Coverage Summary

| Category | Tests | Status |
|----------|-------|--------|
| Page Load | 4 | ✅ |
| Stats Display | 2 | ✅ |
| Filters | 5 | ✅ |
| Suggestion Cards | 6 | ✅ |
| Accept/Decline | 4 | ✅ |
| Generate Form | 6 | ✅ |
| Delete All | 3 | ✅ |
| Pagination | 5 | ✅ |
| Loading/Empty | 2 | ✅ |
| Error Handling | 1 | ✅ |
| Accessibility | 3 | ✅ |
| User Journeys | 2 | ✅ |
| **Total** | **43** | ✅ |

## Contributing

When adding new tests:

1. Follow existing Page Object Model pattern
2. Add appropriate test tags (`@smoke`, `@regression`, etc.)
3. Include both positive and negative test cases
4. Update this README with new test scenarios
5. Ensure tests are resilient (handle missing data gracefully)
