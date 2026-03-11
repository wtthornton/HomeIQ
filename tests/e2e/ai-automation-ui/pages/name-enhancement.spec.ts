/**
 * Name Enhancement Page (Epic 49.12)
 * Route: /name-enhancement — Name Enhancement dashboard for entity/device name suggestions.
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('Name Enhancement — /name-enhancement', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/name-enhancement');
    await waitForLoadingComplete(page);
  });

  test('name-enhancement route loads with main content or title', async ({ page }) => {
    await expect(page).toHaveTitle(/Name Enhancement|HomeIQ/i);
    const main = page.locator('main');
    await expect(main).toBeVisible({ timeout: 10000 });
    const heading = page.getByRole('heading', { level: 1 });
    const hasHeading = await heading.first().isVisible({ timeout: 5000 }).catch(() => false);
    expect(hasHeading, 'Page should show a main heading').toBe(true);
  });
});
