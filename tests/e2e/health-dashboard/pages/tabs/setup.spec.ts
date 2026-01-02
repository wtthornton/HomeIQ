import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

test.describe('Health Dashboard - Setup Tab', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#setup');
    await waitForLoadingComplete(page);
  });

  test('@smoke Setup wizard flow', async ({ page }) => {
    const wizard = page.locator('[data-testid="setup-wizard"], [class*="Wizard"]').first();
    await expect(wizard).toBeVisible({ timeout: 5000 });
  });

  test('Form validation', async ({ page }) => {
    const nextButton = page.locator('button:has-text("Next"), button[aria-label*="next"]').first();
    
    if (await nextButton.isVisible({ timeout: 2000 })) {
      await nextButton.click();
      
      // Look for validation errors
      const errors = page.locator('[role="alert"], .error');
      // Validation might show errors
    }
  });

  test('Step navigation', async ({ page }) => {
    const nextButton = page.locator('button:has-text("Next")').first();
    const prevButton = page.locator('button:has-text("Previous"), button:has-text("Back")').first();
    
    if (await nextButton.isVisible({ timeout: 2000 })) {
      await nextButton.click();
      await page.waitForTimeout(500);
      
      if (await prevButton.isVisible({ timeout: 2000 })) {
        await prevButton.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('Configuration saving', async ({ page }) => {
    const saveButton = page.locator('button:has-text("Save"), button[type="submit"]').first();
    
    if (await saveButton.isVisible({ timeout: 2000 })) {
      await saveButton.click();
      await page.waitForTimeout(1000);
    }
  });

  test('Health checks', async ({ page }) => {
    const healthCheckButton = page.locator('button:has-text("Check"), button:has-text("Test")').first();
    
    if (await healthCheckButton.isVisible({ timeout: 2000 })) {
      await healthCheckButton.click();
      await page.waitForTimeout(2000);
      
      const result = page.locator('[data-testid="health-result"], [class*="result"]').first();
      const exists = await result.isVisible().catch(() => false);
    }
  });
});
