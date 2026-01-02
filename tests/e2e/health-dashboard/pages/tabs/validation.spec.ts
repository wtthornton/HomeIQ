import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

test.describe('Health Dashboard - Validation Tab', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#validation');
    await waitForLoadingComplete(page);
  });

  test('@smoke Validation results display', async ({ page }) => {
    const results = page.locator('[data-testid="validation-results"], [class*="results"]').first();
    await expect(results).toBeVisible({ timeout: 5000 });
  });

  test('Validation runs trigger', async ({ page }) => {
    const runButton = page.locator('button:has-text("Run"), button:has-text("Validate")').first();
    
    if (await runButton.isVisible({ timeout: 2000 })) {
      await runButton.click();
      await page.waitForTimeout(2000);
      
      const results = page.locator('[data-testid="validation-results"]').first();
      await expect(results).toBeVisible();
    }
  });

  test('Results filtering', async ({ page }) => {
    const filterInput = page.locator('input, select, [data-testid="filter"]').first();
    
    if (await filterInput.isVisible({ timeout: 2000 })) {
      await filterInput.fill('error');
      await page.waitForTimeout(500);
    }
  });
});
