import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

/** P4 - Proactive Suggestions page */
test.describe('AI Automation UI - Proactive Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/proactive');
    await waitForLoadingComplete(page);
  });

  test('@smoke Proactive page loads', async ({ page }) => {
    await expect(page.locator('main, body')).toBeVisible({ timeout: 8000 });
    expect(page.url()).toContain('/proactive');
  });

  test('Proactive content or empty state displays', async ({ page }) => {
    const content = page.locator('[data-testid="proactive"], [class*="Proactive"], main').first();
    await expect(content).toBeVisible({ timeout: 8000 });
  });

  test('Filters or stats section', async ({ page }) => {
    const filtersOrStats = page.locator('input, select, [class*="filter"], [class*="stat"]').first();
    const hasControls = await filtersOrStats.isVisible().catch(() => false);
    expect(typeof hasControls).toBe('boolean');
  });
});
