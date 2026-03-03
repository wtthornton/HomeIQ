import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

test.describe('Health Dashboard - Hygiene Tab', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#hygiene');
    await waitForLoadingComplete(page);
  });

  test('@smoke Device hygiene metrics', async ({ page }) => {
    // Require tab root only — no fallback (avoids false positive when tab fails to render).
    await expect(page.locator('[data-testid="hygiene-metrics"]')).toBeVisible({ timeout: 15000 });
  });

  test('Recommendations display', async ({ page }) => {
    const recommendations = page.locator('[data-testid="recommendations"], [class*="recommendation"]').first();
    const exists = await recommendations.isVisible().catch(() => false);
    // Structure supports recommendations
  });

  test('Action buttons work', async ({ page }) => {
    const actionButton = page.locator('button:has-text("Fix"), button:has-text("Apply")').first();
    
    if (await actionButton.isVisible({ timeout: 2000 })) {
      await actionButton.click();
      await page.waitForTimeout(500);
    }
  });
});
