# Playwright Documentation Cache
# Version: 1.56.0
# Last Updated: 2025-10-12
# Source: Context7 (/microsoft/playwright)

## Overview
Playwright is a framework for Web Testing and Automation. It allows testing Chromium, Firefox and WebKit with a single API. This cache contains focused documentation on testing, automation, assertions, and configuration for version 1.56.0.

## Testing Framework

### Core Concepts
- **Cross-browser testing**: Chromium, Firefox, WebKit support
- **Test isolation**: Independent test execution with fresh contexts
- **Automatic waiting**: Smart wait strategies for reliable tests
- **Parallel execution**: Concurrent test running for speed
- **Screenshot comparison**: Visual regression testing
- **Video recording**: Test execution recording
- **Trace viewer**: Powerful debugging tool

### Test Configuration with defineConfig

**Basic Configuration:**
```javascript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  timeout: 30000,
  globalTimeout: 600000,
  reporter: 'list',
  testDir: './tests',
  
  // Parallel execution
  fullyParallel: true,
  
  // CI-specific settings
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
});
```

**Advanced Configuration:**
```js
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  // Test directory
  testDir: 'tests',
  
  // Output directory for artifacts
  outputDir: 'test-results',
  
  // Global setup/teardown
  globalSetup: require.resolve('./global-setup'),
  globalTeardown: require.resolve('./global-teardown'),
  
  // Each test timeout
  timeout: 30000,
  
  // Reporter
  reporter: 'html',
  
  use: {
    // Base URL for navigation
    baseURL: 'http://localhost:3000',
    
    // Trace collection
    trace: 'on-first-retry',
  },
  
  // Browser projects
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  
  // Integrated web server
  webServer: {
    command: 'npm run start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

### Quiet Mode
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  quiet: !!process.env.CI, // Suppress stdout/stderr in CI
});
```

## Assertions and Expect API

### Expect Configuration

**Global Assertion Timeout:**
```js
import { defineConfig } from '@playwright/test';

export default defineConfig({
  expect: {
    // Maximum time expect() should wait
    timeout: 5000,
    
    // Screenshot comparison thresholds
    toHaveScreenshot: {
      maxDiffPixels: 10,
    },
    
    // Snapshot comparison thresholds
    toMatchSnapshot: {
      maxDiffPixelRatio: 0.1,
    },
  },
});
```

**Python Global Timeout:**
```python
from playwright.sync_api import expect

expect.set_options(timeout=10_000)
```

**C# Global Timeout (NUnit):**
```csharp
using Microsoft.Playwright;
using Microsoft.Playwright.NUnit;
using NUnit.Framework;

[TestFixture]
public class Tests : PageTest
{
    [OneTimeSetUp]
    public void GlobalSetup()
    {
        SetDefaultExpectTimeout(10_000);
    }
}
```

### Custom Expect Instances

**Slow Expectations:**
```javascript
const slowExpect = expect.configure({ timeout: 10000 });
await slowExpect(locator).toHaveText('Submit');
```

**Soft Assertions:**
```javascript
// Configure soft assertions
const softExpect = expect.configure({ soft: true });
await softExpect(locator).toHaveText('Submit');

// Or use inline
await expect.soft(page.getByTestId('status')).toHaveText('Success');
await expect.soft(page.getByTestId('eta')).toHaveText('1 day');

// Check for soft assertion failures
expect(test.info().errors).toHaveLength(0);
```

### Locator Assertions

**Common Assertions:**
```java
// Visibility
PlaywrightAssertions.assertThat(locator).isVisible();

// Text content
await expect(locator).toHaveText('Expected text');

// Attribute values
await expect(locator).toHaveAttribute('href', '/path');

// Count
await expect(locators).toHaveCount(5);
```

## Browser Automation

### Page Interaction
- **Navigation**: `page.goto()`, back/forward navigation
- **Element selection**: `page.locator()`, `page.getByRole()`, etc.
- **User actions**: `click()`, `fill()`, `hover()`, `press()`
- **Form filling**: Input field interactions
- **File uploads**: File selection and upload
- **Keyboard shortcuts**: Keyboard interaction

### Element Handling
- **Locators**: Element selection strategies (CSS, text, role)
- **Wait strategies**: Auto-waiting for elements
- **Element properties**: Getting attributes and text
- **Element state**: Checking visibility, enabled, etc.
- **Element actions**: Performing actions on elements
- **Element lists**: Handling multiple elements

## Test Fixtures and Options

### Use Options and Context
```javascript
test('should inherit use options', async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  
  expect(await page.evaluate(() => navigator.userAgent)).toBe('some custom ua');
  expect(await page.evaluate(() => window.innerWidth)).toBe(100);
  
  await context.close();
});
```

### Custom Fixtures
```typescript
import { test as base } from '@playwright/test';

type MyFixtures = {
  database: Database;
};

export const test = base.extend<MyFixtures>({
  database: async ({}, use) => {
    const db = await Database.connect();
    await use(db);
    await db.close();
  },
});

export { expect } from '@playwright/test';
```

## Accessibility Testing

### AxeBuilder Integration

**Creating Shared Fixture:**
```typescript
import { test as base } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

type AxeFixture = {
  makeAxeBuilder: () => AxeBuilder;
};

export const test = base.extend<AxeFixture>({
  makeAxeBuilder: async ({ page }, use) => {
    const makeAxeBuilder = () => new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .exclude('#commonly-reused-element-with-known-issue');

    await use(makeAxeBuilder);
  }
});

export { expect } from '@playwright/test';
```

**Using Accessibility Tests:**
```javascript
const { test, expect } = require('./axe-test');

test('example using custom fixture', async ({ page, makeAxeBuilder }) => {
  await page.goto('https://your-site.com/');

  const accessibilityScanResults = await makeAxeBuilder()
      .include('#specific-element-under-test')
      .analyze();

  expect(accessibilityScanResults.violations).toEqual([]);
});
```

### ATTAcomm Accessibility Framework

**Basic Test Setup:**
```JavaScript
setup({explicit_timeout: true, explicit_done: true });

var theTest = new ATTAcomm({
  "steps": [{
    "element": "test",
    "test": {
      "ATK": [["property", "name", "is", "Expected Value"]],
      "AXAPI": [["property", "AXDescription", "is", "Expected Value"]],
      "IAccessible2": [["property", "accName", "is", "Expected Value"]],
      "UIA": [["property", "Name", "is", "Expected Value"]]
    },
    "title": "step 1",
    "type": "test"
  }],
  "title": "Accessibility Test Case"
});
```

## Custom Matchers

### Extending Expect with Custom Matchers

**Define Custom Matchers:**
```typescript
import { expect as baseExpect } from '@playwright/test';

export const expect = baseExpect.extend({
  async toHaveDatabaseUser(database: Database, expected: string) {
    const users = await database.getUsers();
    const pass = users.includes(expected);
    
    return {
      message: () => pass 
        ? `Expected database not to have user ${expected}`
        : `Expected database to have user ${expected}`,
      pass,
    };
  },
});
```

**Using Custom Matchers:**
```typescript
import { test, expect } from './fixtures';

test('passes', async ({ database }) => {
  await expect(database).toHaveDatabaseUser('admin');
});
```

## Best Practices

### Test Organization
1. Use Page Object Model for reusable components
2. Create custom fixtures for shared setup
3. Group related tests in files
4. Use meaningful test descriptions
5. Keep tests independent and isolated

### Assertion Strategy
1. Use auto-retrying assertions (`expect(locator)`)
2. Configure appropriate timeouts
3. Use soft assertions for non-critical checks
4. Create custom matchers for domain-specific assertions
5. Check soft assertion failures before critical operations

### Configuration Best Practices
1. Use `baseURL` for relative navigation
2. Configure retries for flaky test handling
3. Use different workers for CI vs local
4. Enable trace on first retry for debugging
5. Use project-specific configurations for different browsers

### Performance Optimization
1. Use `fullyParallel: true` when tests are independent
2. Limit workers in CI for stability
3. Use `reuseExistingServer` for faster local runs
4. Configure appropriate timeouts
5. Use screenshot comparison thresholds to avoid flaky tests

## Debugging and Tracing

### Trace Collection
```js
use: {
  trace: 'on-first-retry', // or 'on', 'off', 'retain-on-failure'
}
```

### Screenshot on Failure
```js
use: {
  screenshot: 'only-on-failure',
}
```

### Video Recording
```js
use: {
  video: 'retain-on-failure',
}
```

## Migration Notes (1.56.0)

### New Features
- Enhanced accessibility testing support
- Improved trace viewer
- Better screenshot comparison algorithms
- Advanced configuration options
- Custom matcher improvements

### Breaking Changes
- Check official release notes for version-specific breaking changes

## Multi-Language Support

Playwright supports:
- **JavaScript/TypeScript**: Primary language with full feature set
- **Python**: `playwright-python` package
- **Java**: `playwright-java` package
- **C#/.NET**: `playwright-dotnet` package

Each language has its own assertion syntax and configuration patterns, but core concepts remain consistent.

## Common Patterns

### Login Once, Use Everywhere
```javascript
// global-setup.js
export default async function globalSetup() {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  
  await page.goto('https://example.com/login');
  await page.fill('#username', 'admin');
  await page.fill('#password', 'password');
  await page.click('button[type="submit"]');
  
  await context.storageState({ path: 'auth.json' });
  await browser.close();
}
```

```javascript
// Use authenticated state
use: {
  storageState: 'auth.json',
}
```

### API Testing
```javascript
test('API test', async ({ request }) => {
  const response = await request.post('/api/users', {
    data: { name: 'John' }
  });
  
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  expect(data.name).toBe('John');
});
```

### Mobile Emulation
```javascript
projects: [
  {
    name: 'Mobile Chrome',
    use: { ...devices['Pixel 5'] },
  },
]
```

## Resources

- Official Docs: https://playwright.dev
- GitHub: https://github.com/microsoft/playwright
- Discord: https://aka.ms/playwright/discord
