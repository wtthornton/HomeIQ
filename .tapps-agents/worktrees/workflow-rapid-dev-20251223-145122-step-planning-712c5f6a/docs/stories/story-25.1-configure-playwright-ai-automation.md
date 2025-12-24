# Story 25.1: Configure Playwright for AI Automation UI Testing

## Status
Draft

## Story

**As a** QA engineer,
**I want** Playwright E2E test infrastructure configured to support AI Automation UI testing,
**so that** we can write reliable end-to-end tests for the AI automation workflows without duplicating test infrastructure or breaking existing tests.

## Acceptance Criteria

1. **Test Configuration:**
   - AI Automation UI base URL (localhost:3001) added to test config
   - Health checks for ai-automation-service (port 8018) in global setup
   - Test fixtures created for AI automation-specific needs
   - Configuration backward compatible with existing tests

2. **Page Object Models:**
   - `DashboardPage.ts` - Dashboard interactions (browse, filter, approve)
   - `PatternsPage.ts` - Pattern visualization and filtering
   - `DeployedPage.ts` - Deployed automations management
   - `SettingsPage.ts` - Configuration management
   - All POMs follow Playwright best practices (Context7 research)

3. **Test Helpers:**
   - Mock data generator for suggestions
   - Mock data generator for patterns
   - Custom assertion helpers for AI automation states
   - API mocking utilities

4. **Smoke Tests:**
   - Test 1: AI Automation UI loads and renders
   - Test 2: Can navigate to all 4 pages (Dashboard, Patterns, Deployed, Settings)
   - Both tests pass reliably

5. **Validation:**
   - All existing E2E tests still pass (17 files)
   - New smoke tests pass in CI/CD
   - Zero breaking changes to existing test infrastructure
   - Documentation updated with setup guide

## Tasks / Subtasks

- [ ] **Task 1: Update Test Configuration** (AC: 1)
  - [ ] Add AI Automation UI URL to `docker-deployment.config.ts`
  - [ ] Add ai-automation-service health check to `docker-global-setup.ts`
  - [ ] Create test fixtures file `tests/e2e/fixtures/ai-automation.ts`
  - [ ] Test backward compatibility with existing tests

- [ ] **Task 2: Create Page Object Models** (AC: 2)
  - [ ] Create `tests/e2e/page-objects/DashboardPage.ts`
  - [ ] Create `tests/e2e/page-objects/PatternsPage.ts`
  - [ ] Create `tests/e2e/page-objects/DeployedPage.ts`
  - [ ] Create `tests/e2e/page-objects/SettingsPage.ts`
  - [ ] Implement common methods using web-first assertions
  - [ ] Add JSDoc comments to all public methods

- [ ] **Task 3: Create Test Helpers and Utilities** (AC: 3)
  - [ ] Create `tests/e2e/utils/mock-data-generators.ts`
  - [ ] Implement suggestion mock data generator
  - [ ] Implement pattern mock data generator
  - [ ] Create custom assertion helpers
  - [ ] Create API mocking utilities

- [ ] **Task 4: Implement Smoke Tests** (AC: 4)
  - [ ] Create `tests/e2e/ai-automation-smoke.spec.ts`
  - [ ] Test: AI Automation UI loads successfully
  - [ ] Test: Navigate to all 4 pages
  - [ ] Verify tests pass locally and in CI/CD

- [ ] **Task 5: Validation and Documentation** (AC: 5)
  - [ ] Run all existing E2E tests (verify no regression)
  - [ ] Update `tests/e2e/README.md` with AI automation setup
  - [ ] Document Page Object Models with examples
  - [ ] Create setup guide for AI automation testing

## Dev Notes

### Project Context

**Source:** `docs/architecture/source-tree.md`, `docs/architecture/tech-stack.md`

**Existing E2E Test Infrastructure:**
- Location: `tests/e2e/`
- Configuration: `tests/e2e/docker-deployment.config.ts`
- Global setup: `tests/e2e/docker-global-setup.ts`
- Global teardown: `tests/e2e/docker-global-teardown.ts`
- Test runner: `tests/e2e/run-docker-tests.sh`
- Existing coverage: 17 test files for Health Dashboard (localhost:3000)

**Technology Stack:**
- E2E Framework: Playwright 1.56.0
- Language: TypeScript 5.2.2
- Test Runner: Playwright Test
- Existing patterns: Page Object Models, Docker helpers, fixtures

**Services Under Test:**
- **AI Automation UI:** Port 3001 (React 18.2.0 + Vite)
- **ai-automation-service:** Port 8018 (FastAPI backend)
- **Health Dashboard:** Port 3000 (existing tests)

**Integration Points:**
- InfluxDB: Port 8086
- Data API: Port 8006
- Admin API: Port 8003

### Playwright Best Practices (from Context7 Research)

**1. Configuration Best Practices:**
```typescript
// tests/e2e/docker-deployment.config.ts
export default defineConfig({
  use: {
    // Base URL for each service
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    
    // Web-first assertion timeouts
    actionTimeout: 10000,
    navigationTimeout: 15000,
    
    // Screenshots and videos on failure
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
  },
  
  // Parallel execution
  fullyParallel: true,
  workers: process.env.CI ? 2 : 4,
  
  // Retry flaky tests
  retries: process.env.CI ? 2 : 1,
  
  // Projects for different services
  projects: [
    {
      name: 'health-dashboard',
      use: { baseURL: 'http://localhost:3000' },
    },
    {
      name: 'ai-automation',
      use: { baseURL: 'http://localhost:3001' },
    },
  ],
});
```

**2. Page Object Model Pattern (MANDATORY):**
```typescript
// tests/e2e/page-objects/DashboardPage.ts
import { Page, expect } from '@playwright/test';

export class DashboardPage {
  constructor(private page: Page) {}

  // Navigation
  async goto() {
    await this.page.goto('http://localhost:3001');
    // Wait for page to be ready
    await expect(this.page.getByTestId('dashboard-container')).toBeVisible();
  }

  // Getters with web-first assertions
  async getSuggestionCards() {
    return this.page.getByTestId('suggestion-card');
  }

  // Actions
  async approveSuggestion(index: number) {
    const card = this.page.getByTestId('suggestion-card').nth(index);
    await card.getByRole('button', { name: 'Approve' }).click();
  }

  // Filters
  async filterByCategory(category: string) {
    await this.page.getByRole('combobox', { name: 'Category' }).selectOption(category);
    // Wait for filtered results
    await this.page.waitForLoadState('networkidle');
  }
}
```

**3. Test Fixtures:**
```typescript
// tests/e2e/fixtures/ai-automation.ts
export interface Suggestion {
  id: string;
  title: string;
  description: string;
  category: 'energy' | 'comfort' | 'security' | 'convenience';
  confidence: 'high' | 'medium' | 'low';
  pattern_type: 'time-of-day' | 'co-occurrence';
  approved: boolean;
}

export const mockSuggestions: Suggestion[] = [
  {
    id: 'sug-1',
    title: 'Turn off lights at 11 PM',
    description: 'Detected consistent manual light shutdown at 11 PM every night',
    category: 'energy',
    confidence: 'high',
    pattern_type: 'time-of-day',
    approved: false,
  },
  // ... more mock data
];
```

**4. Web-First Assertions (MANDATORY):**
```typescript
// ✅ CORRECT - auto-wait and retry
await expect(page.getByTestId('dashboard-container')).toBeVisible();
await expect(page.getByText('Suggestions')).toBeVisible();

// ❌ INCORRECT - no waiting
expect(await page.getByTestId('dashboard-container').isVisible()).toBe(true);
```

### File Structure to Create

```
tests/e2e/
├── page-objects/              # NEW
│   ├── DashboardPage.ts       # Dashboard POM
│   ├── PatternsPage.ts        # Patterns POM
│   ├── DeployedPage.ts        # Deployed POM
│   └── SettingsPage.ts        # Settings POM
├── utils/
│   ├── docker-test-helpers.ts # EXISTING
│   └── mock-data-generators.ts # NEW
├── fixtures/
│   └── ai-automation.ts       # NEW
├── ai-automation-smoke.spec.ts # NEW
├── docker-deployment.config.ts # MODIFY
├── docker-global-setup.ts     # MODIFY
└── README.md                  # MODIFY
```

### Required Changes to Existing Files

**1. docker-deployment.config.ts:**
```typescript
// Add AI Automation project
projects: [
  {
    name: 'health-dashboard',
    use: { baseURL: 'http://localhost:3000' },
    testMatch: /dashboard-.*\.spec\.ts/,
  },
  {
    name: 'ai-automation',  // NEW
    use: { baseURL: 'http://localhost:3001' },
    testMatch: /ai-automation-.*\.spec\.ts/,
  },
],
```

**2. docker-global-setup.ts:**
```typescript
// Add ai-automation-service health check
const services = [
  { name: 'InfluxDB', url: 'http://localhost:8086/health' },
  { name: 'Admin API', url: 'http://localhost:8003/api/v1/health' },
  { name: 'Health Dashboard', url: 'http://localhost:3000' },
  { name: 'AI Automation Service', url: 'http://localhost:8018/health' },  // NEW
  { name: 'AI Automation UI', url: 'http://localhost:3001' },  // NEW
];
```

### DashboardPage Methods to Implement

```typescript
class DashboardPage {
  // Navigation
  async goto(): Promise<void>
  
  // Getters
  async getSuggestionCards(): Promise<Locator>
  async getSuggestionById(id: string): Promise<Locator>
  async getFilterDropdown(name: string): Promise<Locator>
  
  // Actions
  async approveSuggestion(index: number): Promise<void>
  async rejectSuggestion(index: number): Promise<void>
  async deploySuggestion(id: string): Promise<void>
  
  // Filters
  async filterByCategory(category: string): Promise<void>
  async filterByConfidence(level: string): Promise<void>
  async searchSuggestions(keyword: string): Promise<void>
  
  // Assertions
  async expectSuggestionCount(count: number): Promise<void>
  async expectNoSuggestions(): Promise<void>
  async expectSuccessToast(message: string): Promise<void>
}
```

### Mock Data Generator Structure

```typescript
// tests/e2e/utils/mock-data-generators.ts

export interface MockDataOptions {
  count?: number;
  category?: string;
  confidence?: string;
}

export class MockDataGenerator {
  static generateSuggestions(options?: MockDataOptions): Suggestion[] {
    // Generate realistic mock suggestions
  }
  
  static generatePatterns(options?: MockDataOptions): Pattern[] {
    // Generate realistic mock patterns
  }
  
  static generateDeployedAutomations(options?: MockDataOptions): Automation[] {
    // Generate realistic mock automations
  }
}
```

### Critical Implementation Notes

1. **Preserve Existing Test Infrastructure:**
   - DO NOT modify existing test files
   - DO NOT change existing Page Object Models
   - Add new configuration, don't replace

2. **Service Health Checks:**
   - Verify ai-automation-service is running before tests
   - Fail fast if service unavailable
   - Clear error messages

3. **Page Object Model Standards:**
   - Use TypeScript interfaces for type safety
   - Add JSDoc comments for all public methods
   - Follow async/await patterns consistently
   - Use web-first assertions in all methods

4. **Test Isolation:**
   - Each test should be independent
   - Use mock data, not real database
   - Clear state between tests

### Testing

**Test File Location:** `tests/e2e/ai-automation-smoke.spec.ts`

**Test Standards:**
- Use TypeScript 5.2.2
- Follow existing naming conventions
- Use `test.describe` for grouping
- Implement `beforeEach` for setup

**Smoke Test 1: UI Loads**
```typescript
test('AI Automation UI loads successfully', async ({ page }) => {
  const dashboardPage = new DashboardPage(page);
  await dashboardPage.goto();
  
  // Verify page loaded
  await expect(page.getByTestId('dashboard-container')).toBeVisible();
  await expect(page.getByText('Suggestions')).toBeVisible();
});
```

**Smoke Test 2: Navigation**
```typescript
test('Can navigate to all pages', async ({ page }) => {
  // Dashboard
  await page.goto('http://localhost:3001');
  await expect(page.getByTestId('dashboard-container')).toBeVisible();
  
  // Patterns
  await page.goto('http://localhost:3001/patterns');
  await expect(page.getByTestId('patterns-container')).toBeVisible();
  
  // Deployed
  await page.goto('http://localhost:3001/deployed');
  await expect(page.getByTestId('deployed-container')).toBeVisible();
  
  // Settings
  await page.goto('http://localhost:3001/settings');
  await expect(page.getByTestId('settings-container')).toBeVisible();
});
```

**Test Execution:**
```bash
# Run smoke tests only
npx playwright test tests/e2e/ai-automation-smoke.spec.ts

# Run all tests (verify no regression)
npx playwright test

# Run with specific browser
npx playwright test --project=chromium
```

### Testing

**Validation Requirements:**
- New smoke tests pass (2 tests)
- All existing E2E tests pass (17 files)
- No changes to existing test behavior
- Test execution time <30 seconds for smoke tests

**Testing Tools:**
- Playwright 1.56.0
- TypeScript 5.2.2
- Playwright Test Runner

**Regression Testing:**
Run full suite to ensure no breaking changes:
```bash
npx playwright test tests/e2e/
```

Expected: All 19 test files pass (17 existing + 2 new smoke tests)

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
- `tests/e2e/page-objects/DashboardPage.ts`
- `tests/e2e/page-objects/PatternsPage.ts`
- `tests/e2e/page-objects/DeployedPage.ts`
- `tests/e2e/page-objects/SettingsPage.ts`
- `tests/e2e/utils/mock-data-generators.ts`
- `tests/e2e/fixtures/ai-automation.ts`
- `tests/e2e/ai-automation-smoke.spec.ts`

**Modified Files:**
- `tests/e2e/docker-deployment.config.ts` (add AI automation project)
- `tests/e2e/docker-global-setup.ts` (add service health checks)
- `tests/e2e/README.md` (add AI automation testing section)

**No Changes:**
- All existing E2E test files (17 files)
- Existing Page Object Models
- Existing test utilities

## QA Results
(To be filled by QA agent)

