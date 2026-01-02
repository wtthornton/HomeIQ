# E2E Testing Guide

Comprehensive guide for writing and maintaining Playwright E2E tests.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Test Structure](#test-structure)
3. [Writing Tests](#writing-tests)
4. [Best Practices](#best-practices)
5. [Debugging](#debugging)
6. [CI/CD Integration](#cicd-integration)

## Getting Started

### Prerequisites

- Node.js 18+
- Playwright installed (`npm install -D @playwright/test`)
- Services running (or use webServer config)

### Installation

```bash
# Install Playwright browsers
npx playwright install

# Or install specific browser
npx playwright install chromium
```

## Test Structure

### Directory Organization

Tests are organized by service and test type:

```
tests/e2e/
├── health-dashboard/
│   ├── pages/           # Page-level tests
│   ├── components/      # Component tests
│   ├── interactions/    # User interaction tests
│   └── accessibility/   # A11y tests
└── ai-automation-ui/
    ├── pages/           # Page-level tests
    ├── components/      # Component tests
    └── workflows/       # End-to-end workflows
```

### Test File Naming

- Use descriptive names: `dashboard.spec.ts`, `services.spec.ts`
- Group related tests: `tabs/overview.spec.ts`
- Use kebab-case for directories

## Writing Tests

### Basic Test Pattern

```typescript
import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
    await waitForLoadingComplete(page);
  });

  test('@smoke Feature works correctly', async ({ page }) => {
    // Arrange
    const button = page.locator('button:has-text("Click Me")');
    
    // Act
    await button.click();
    
    // Assert
    await expect(page.locator('.result')).toBeVisible();
  });
});
```

### Using Test Tags

```typescript
test('@smoke Critical path test', async ({ page }) => {
  // Runs on every commit
});

test('@regression Full feature test', async ({ page }) => {
  // Runs on PR
});

test('@integration End-to-end workflow', async ({ page }) => {
  // Workflow test
});
```

### API Mocking

```typescript
import { mockApiEndpoints } from '../../../shared/helpers/api-helpers';
import { automationMocks } from '../../fixtures/api-mocks';

test.beforeEach(async ({ page }) => {
  await mockApiEndpoints(page, [
    { pattern: /\/api\/suggestions/, response: automationMocks['/api/suggestions'] },
    { pattern: /\/api\/chat/, response: automationMocks['/api/chat'] },
  ]);
});
```

### Error Simulation

```typescript
import { mockApiError } from '../../../shared/helpers/api-helpers';

test('Error handling works', async ({ page }) => {
  await mockApiError(page, /\/api\/suggestions/, 500);
  await page.reload();
  
  const errorMessage = page.locator('[role="alert"]');
  await expect(errorMessage).toBeVisible();
});
```

### Waiting for Elements

```typescript
import { waitForStable, waitForLoadingComplete, waitForModalOpen } from '../../../shared/helpers/wait-helpers';

// Wait for element to be stable
await waitForStable(locator);

// Wait for loading to complete
await waitForLoadingComplete(page);

// Wait for modal to open
await waitForModalOpen(page);
```

## Best Practices

### 1. Use Descriptive Selectors

```typescript
// ✅ Good - Specific and stable
page.locator('[data-testid="submit-button"]')
page.locator('button:has-text("Submit")')

// ❌ Bad - Fragile
page.locator('.btn-primary')
page.locator('div > div > button')
```

### 2. Use Page Object Model for Complex Pages

```typescript
class DashboardPage {
  constructor(private page: Page) {}
  
  async navigateToTab(tabName: string) {
    await this.page.locator(`[data-tab="${tabName}"]`).click();
  }
  
  async getServiceCount() {
    return await this.page.locator('[data-testid="service-card"]').count();
  }
}
```

### 3. Avoid Hard-Coded Waits

```typescript
// ❌ Bad
await page.waitForTimeout(5000);

// ✅ Good
await page.waitForSelector('[data-testid="result"]');
await waitForLoadingComplete(page);
```

### 4. Use Test Isolation

```typescript
// Each test gets a fresh context
test('Test 1', async ({ page }) => {
  // Fresh page state
});

test('Test 2', async ({ page }) => {
  // Fresh page state (not affected by Test 1)
});
```

### 5. Clean Up After Tests

```typescript
test.afterEach(async ({ page }) => {
  // Clean up if needed
  await page.evaluate(() => localStorage.clear());
});
```

### 6. Use Fixtures for Common Setup

```typescript
// tests/shared/fixtures/base-fixtures.ts
export const test = base.extend<TestFixtures>({
  authenticatedPage: async ({ page }, use) => {
    await setupAuthenticatedSession(page);
    await use(page);
  },
});
```

## Debugging

### Run in Debug Mode

```bash
npm run test:e2e:debug
```

### Use Playwright Inspector

```bash
PWDEBUG=1 npm run test:e2e
```

### View Screenshots and Videos

Failed tests automatically capture:
- Screenshots: `test-results/`
- Videos: `test-results/`
- Traces: `test-results/`

View traces:
```bash
npx playwright show-trace test-results/trace.zip
```

### Console Logging

```typescript
test('Debug test', async ({ page }) => {
  page.on('console', msg => console.log(msg.text()));
  page.on('request', request => console.log(request.url()));
  page.on('response', response => console.log(response.url(), response.status()));
});
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run E2E tests
  run: |
    npm run test:e2e
    npx playwright show-report
```

### Test Reports

Reports are generated automatically:
- HTML: `playwright-report/index.html`
- JSON: `test-results/results.json`
- JUnit: `test-results/results.xml`

## Common Patterns

### Testing Forms

```typescript
test('Form submission works', async ({ page }) => {
  await page.fill('input[name="email"]', 'test@example.com');
  await page.fill('input[name="password"]', 'password123');
  await page.click('button[type="submit"]');
  
  await expect(page.locator('.success-message')).toBeVisible();
});
```

### Testing Modals

```typescript
test('Modal opens and closes', async ({ page }) => {
  await page.click('button:has-text("Open Modal")');
  await waitForModalOpen(page);
  
  await expect(page.locator('[role="dialog"]')).toBeVisible();
  
  await page.click('button[aria-label="Close"]');
  await expect(page.locator('[role="dialog"]')).not.toBeVisible();
});
```

### Testing Navigation

```typescript
test('Navigation works', async ({ page }) => {
  await page.click('nav a[href="/patterns"]');
  await expect(page).toHaveURL(/\/patterns/);
});
```

### Testing Async Operations

```typescript
test('Async operation completes', async ({ page }) => {
  await page.click('button:has-text("Load Data")');
  
  // Wait for API response
  await page.waitForResponse(response => 
    response.url().includes('/api/data') && response.status() === 200
  );
  
  await expect(page.locator('[data-testid="data"]')).toBeVisible();
});
```

## Troubleshooting

### Tests Flaking

- Use proper waits instead of timeouts
- Wait for network idle when needed
- Use stable selectors
- Check for race conditions

### Tests Too Slow

- Run tests in parallel
- Use test isolation
- Mock external APIs
- Optimize selectors

### Selectors Not Found

- Check element visibility
- Wait for element to appear
- Verify selector is correct
- Check if element is in iframe

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [API Reference](https://playwright.dev/docs/api/class-test)
