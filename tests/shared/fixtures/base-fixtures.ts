import { test as base } from '@playwright/test';
import { setupAuthenticatedSession } from '../helpers/auth-helpers';
import type { Page } from '@playwright/test';

/**
 * Base Test Fixtures
 * Shared fixtures for all tests
 */

interface TestFixtures {
  authenticatedPage: Page;
}

/**
 * Base test with authentication
 */
export const test = base.extend<TestFixtures>({
  authenticatedPage: async ({ page }, use) => {
    await setupAuthenticatedSession(page);
    await use(page);
  },
});

export { expect } from '@playwright/test';
