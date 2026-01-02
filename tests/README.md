# E2E Test Suite

Comprehensive Playwright test suite for HomeIQ UI services.

## Overview

This test suite provides comprehensive end-to-end testing for both UI services:

- **Health Dashboard** (Port 3000) - 15 tabs, 40+ components
- **AI Automation UI** (Port 3001) - 9 routes/pages, 50+ components

## Test Structure

```
tests/
├── e2e/
│   ├── health-dashboard/          # Health Dashboard tests
│   │   ├── fixtures/              # Test data and API mocks
│   │   ├── pages/                 # Page-level tests
│   │   ├── components/            # Component tests
│   │   ├── interactions/          # Interaction tests
│   │   └── accessibility/         # A11y tests
│   └── ai-automation-ui/          # AI Automation UI tests
│       ├── fixtures/              # Test data and API mocks
│       ├── pages/                 # Page-level tests
│       ├── components/            # Component tests
│       └── workflows/             # End-to-end workflows
├── shared/
│   ├── helpers/                   # Shared utilities
│   └── fixtures/                  # Shared fixtures
└── playwright.config.ts           # Root configuration
```

## Running Tests

### Health Dashboard

```bash
cd services/health-dashboard
npm run test:e2e                 # Run all tests
npm run test:e2e:ui              # Run with UI mode
npm run test:e2e:headed          # Run in headed mode
npm run test:e2e:debug           # Run in debug mode
npm run test:e2e:smoke           # Run smoke tests only
npm run test:e2e:chromium       # Run in Chromium only
npm run test:e2e:report         # Show test report
```

### AI Automation UI

```bash
cd services/ai-automation-ui
npm run test:e2e                 # Run all tests
npm run test:e2e:ui              # Run with UI mode
npm run test:e2e:headed          # Run in headed mode
npm run test:e2e:debug           # Run in debug mode
npm run test:e2e:smoke           # Run smoke tests only
npm run test:e2e:chromium       # Run in Chromium only
npm run test:e2e:report         # Show test report
```

### All Tests (Root)

```bash
# From project root
npx playwright test              # Run all tests
npx playwright test --ui         # Run with UI mode
npx playwright test --grep @smoke # Run smoke tests
```

## Test Tags

- `@smoke` - Critical path tests (run on every commit)
- `@regression` - Full feature tests (run on PR)
- `@component` - Component-level tests
- `@integration` - Workflow tests
- `@a11y` - Accessibility tests
- `@slow` - Long-running tests

## Test Coverage

### Health Dashboard

- ✅ All 15 tabs tested
- ✅ Navigation and layout
- ✅ Component interactions
- ✅ Forms and modals
- ✅ Charts and visualizations
- ✅ Accessibility compliance

### AI Automation UI

- ✅ All 9 pages/routes tested
- ✅ Conversational dashboard
- ✅ Chat interface
- ✅ Automation workflows
- ✅ Component interactions
- ✅ End-to-end user flows

## Writing Tests

### Basic Test Structure

```typescript
import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
  });

  test('@smoke Feature works', async ({ page }) => {
    // Test implementation
    await expect(page.locator('selector')).toBeVisible();
  });
});
```

### Using API Mocks

```typescript
import { mockApiEndpoints } from '../../../shared/helpers/api-helpers';
import { automationMocks } from '../../fixtures/api-mocks';

test.beforeEach(async ({ page }) => {
  await mockApiEndpoints(page, [
    { pattern: /\/api\/suggestions/, response: automationMocks['/api/suggestions'] },
  ]);
});
```

### Using Wait Helpers

```typescript
import { waitForLoadingComplete, waitForModalOpen } from '../../../shared/helpers/wait-helpers';

await waitForLoadingComplete(page);
await waitForModalOpen(page);
```

## CI/CD Integration

Tests are configured to run in CI/CD pipelines:

- **Smoke tests** run on every commit
- **Full suite** runs on pull requests
- **Accessibility tests** run nightly
- **Reports** are generated and uploaded

## Debugging

1. Run tests in debug mode: `npm run test:e2e:debug`
2. Use Playwright Inspector to step through tests
3. Check screenshots and videos in `test-results/`
4. View trace files in Playwright Trace Viewer

## Documentation

- [E2E Testing Guide](E2E_TESTING_GUIDE.md) - Detailed testing guide
- [Test Coverage](TEST_COVERAGE.md) - Coverage documentation
