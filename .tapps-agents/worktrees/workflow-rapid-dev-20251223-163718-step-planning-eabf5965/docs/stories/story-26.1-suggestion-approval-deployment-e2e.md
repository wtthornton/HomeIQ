# Story 26.1: Suggestion Approval & Deployment E2E Tests

## Status
Draft

## Story

**As a** QA engineer,
**I want** comprehensive end-to-end tests for the AI automation suggestion approval and deployment workflow,
**so that** we can ensure users can reliably browse, approve, and deploy automation suggestions to Home Assistant without manual testing.

## Acceptance Criteria

1. **Test Suite Implementation:**
   - Minimum 6 E2E tests covering approval workflow
   - All tests use Playwright web-first assertions
   - Tests run in <2 minutes with parallel execution
   - Zero flaky tests (100% pass rate in 10 consecutive runs)

2. **Workflow Coverage:**
   - Complete workflow: Browse suggestions → Filter → Approve → Deploy → Verify
   - Filter by category (energy, comfort, security, convenience)
   - Filter by confidence level (high, medium, low)
   - Search suggestions by keyword
   - Handle deployment errors gracefully
   - Verify deployed automation in Home Assistant

3. **Test Quality:**
   - Use Page Object Models for reusability
   - Mock external dependencies (OpenAI, MQTT)
   - Implement proper test isolation (beforeEach hooks)
   - Include both success and error scenarios
   - Follow Playwright best practices from Context7 research

4. **Integration:**
   - Tests integrated into `run-docker-tests.sh`
   - Run as part of CI/CD pipeline
   - Generate test coverage report
   - Zero impact on existing E2E tests (17 files must still pass)

5. **Documentation:**
   - Test file includes descriptive test names
   - Code comments explain complex assertions
   - README updated with examples
   - Test data fixtures documented

## Tasks / Subtasks

- [ ] **Task 1: Create Test File and Page Object Models** (AC: 1, 3)
  - [ ] Create `tests/e2e/ai-automation-approval-workflow.spec.ts`
  - [ ] Implement `DashboardPage` Page Object Model
  - [ ] Implement `DeployedPage` Page Object Model
  - [ ] Add `data-testid` attributes to AI automation UI components
  - [ ] Create test fixtures for mock suggestion data

- [ ] **Task 2: Implement Core Workflow Tests** (AC: 2, 3)
  - [ ] Test: Complete approval and deployment workflow (happy path)
  - [ ] Test: Filter suggestions by category
  - [ ] Test: Filter suggestions by confidence level
  - [ ] Test: Search suggestions by keyword
  - [ ] Implement beforeEach hook for test isolation
  - [ ] Use web-first assertions throughout

- [ ] **Task 3: Implement Error Handling Tests** (AC: 2, 3)
  - [ ] Test: Handle deployment errors gracefully
  - [ ] Test: Verify deployed automation in Deployed tab
  - [ ] Mock API error responses
  - [ ] Verify error toast notifications

- [ ] **Task 4: Performance and Reliability** (AC: 1, 3)
  - [ ] Configure parallel execution
  - [ ] Optimize test execution time (<2 minutes)
  - [ ] Run tests 10 times to verify no flakiness
  - [ ] Add proper timeout handling

- [ ] **Task 5: Integration and Documentation** (AC: 4, 5)
  - [ ] Add tests to `run-docker-tests.sh`
  - [ ] Update `tests/e2e/README.md` with examples
  - [ ] Verify all existing tests still pass
  - [ ] Generate coverage report

## Dev Notes

### Project Context

**Source:** `docs/architecture/source-tree.md`, `docs/architecture/tech-stack.md`

**AI Automation UI Location:**
- Service: `services/ai-automation-ui/`
- Port: 3001
- Technology: React 18.2.0 + TypeScript + Vite
- State Management: Zustand (`src/store.ts`)
- Routing: React Router (`src/pages/`)
- Pages: Dashboard, Patterns, Deployed, Settings

**AI Automation Backend:**
- Service: `services/ai-automation-service/`
- Port: 8018
- API Endpoints:
  - `GET /api/suggestions` - List all suggestions
  - `POST /api/deploy/{id}` - Deploy automation to HA
  - `POST /api/analysis/trigger` - Manual analysis trigger
- Database: SQLite (`data/ai-automation.db`)

**Existing E2E Test Infrastructure:**
- Location: `tests/e2e/`
- Configuration: `tests/e2e/docker-deployment.config.ts`
- Test runner: `tests/e2e/run-docker-tests.sh`
- Current coverage: Health Dashboard (localhost:3000) only

**Key Integration Points:**
- Home Assistant MQTT for deployment
- InfluxDB for historical data
- OpenAI API for suggestion generation (mock in tests)
- Data API (port 8006) for device/entity queries

### Playwright Best Practices (from Context7 Research)

**1. Web-First Assertions (MANDATORY):**
```typescript
// ✅ CORRECT - auto-wait and retry
await expect(page.getByText('Approved')).toBeVisible();

// ❌ INCORRECT - no waiting
expect(await page.getByText('Approved').isVisible()).toBe(true);
```

**2. User-Facing Locators (MANDATORY):**
```typescript
// ✅ CORRECT - role-based, resilient
page.getByRole('button', { name: 'Approve' });
page.getByTestId('suggestion-card');

// ❌ INCORRECT - CSS selectors (fragile)
page.locator('.btn-approve');
```

**3. Test Isolation:**
```typescript
test.beforeEach(async ({ page }) => {
  // Fresh state for each test
  await page.goto('http://localhost:3001');
  // Mock API responses for determinism
  await page.route('**/api/suggestions', mockSuggestionsHandler);
});
```

**4. Page Object Model Pattern:**
```typescript
class DashboardPage {
  constructor(private page: Page) {}
  
  async goto() {
    await this.page.goto('http://localhost:3001');
  }
  
  async getSuggestionCards() {
    return this.page.getByTestId('suggestion-card');
  }
  
  async approveSuggestion(index: number) {
    const card = this.page.getByTestId('suggestion-card').nth(index);
    await card.getByRole('button', { name: 'Approve' }).click();
  }
}
```

### Component Structure to Test

**AI Automation UI Components:**
- `src/pages/Dashboard.tsx` - Main suggestion list
- `src/components/SuggestionCard.tsx` - Individual suggestion
- `src/components/FilterPills.tsx` - Category/confidence filters
- `src/components/SearchBar.tsx` - Keyword search
- `src/components/BatchActions.tsx` - Approve/reject buttons
- `src/services/api.ts` - API client (mock this)

**Required data-testid Attributes:**
Add to AI automation UI components:
- `suggestion-card` - Suggestion card container
- `approve-button` - Approve button
- `deploy-button` - Deploy button
- `filter-category` - Category filter
- `filter-confidence` - Confidence filter
- `search-input` - Search input
- `toast-success` - Success notification
- `toast-error` - Error notification

### Testing

**Test File Location:** `tests/e2e/ai-automation-approval-workflow.spec.ts`

**Page Object Location:** `tests/e2e/page-objects/`
- `DashboardPage.ts`
- `DeployedPage.ts`

**Test Standards:**
- Use TypeScript for all test files
- Follow existing test naming conventions
- Use `test.describe` for test grouping
- Implement `beforeEach` for setup
- Use `test.slow()` for tests >30 seconds
- Parallel execution: `test.describe.configure({ mode: 'parallel' })`

**Testing Framework:** Playwright 1.56.0
- Auto-wait for elements (no manual `waitFor`)
- Web-first assertions (`toBeVisible`, `toHaveText`, etc.)
- Screenshot on failure (automatic)
- Video recording on failure (automatic)

**Mock Data Strategy:**
Create `tests/e2e/fixtures/suggestions.ts` with:
- Sample suggestions (3-5 different types)
- Different confidence levels
- Various categories
- Realistic AI-generated descriptions

**Success Validation:**
- Verify toast notifications appear
- Check deployed automation in Deployed tab
- Validate API calls were made
- Confirm UI state updates correctly

**Error Scenarios to Test:**
- Home Assistant connection failure
- MQTT publish error
- Invalid suggestion ID
- Network timeout
- API rate limiting

### Critical Implementation Notes

1. **Add data-testid attributes to AI automation UI:**
   - Modify `services/ai-automation-ui/src/components/SuggestionCard.tsx`
   - Modify `services/ai-automation-ui/src/pages/Dashboard.tsx`
   - Follow existing pattern from health dashboard

2. **Mock External Dependencies:**
   - OpenAI API (should not make real calls)
   - MQTT broker (mock notifications)
   - Home Assistant API (mock deployment)

3. **Test Isolation:**
   - Each test should start with clean state
   - Use mock data, not real database
   - Clear localStorage between tests

4. **Performance:**
   - Run tests in parallel
   - Keep test execution under 2 minutes total
   - Use `test.describe.configure({ mode: 'parallel' })`

### Testing

**Test Coverage Requirements:**
- All tests in this story file must pass
- Existing 17 E2E test files must still pass
- No regression in health dashboard tests
- Test execution time <2 minutes

**Testing Tools:**
- Playwright 1.56.0
- TypeScript 5.2.2
- Playwright Test Runner

**Test Execution:**
```bash
# Run only AI automation tests
npx playwright test tests/e2e/ai-automation-approval-workflow.spec.ts

# Run all E2E tests
./tests/e2e/run-docker-tests.sh

# Run with UI mode (debugging)
npx playwright test --ui
```

**Test Report:**
- HTML report: `test-results/html-report/index.html`
- Screenshots: `test-results/` (on failure)
- Videos: `test-results/` (on failure)

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
- `tests/e2e/ai-automation-approval-workflow.spec.ts` (new)
- `tests/e2e/page-objects/DashboardPage.ts` (new)
- `tests/e2e/page-objects/DeployedPage.ts` (new)
- `tests/e2e/fixtures/suggestions.ts` (new)
- `services/ai-automation-ui/src/components/SuggestionCard.tsx` (modified - add data-testid)
- `services/ai-automation-ui/src/pages/Dashboard.tsx` (modified - add data-testid)
- `tests/e2e/README.md` (modified - add AI automation section)
- `tests/e2e/run-docker-tests.sh` (modified - include new tests)

## QA Results
(To be filled by QA agent)

