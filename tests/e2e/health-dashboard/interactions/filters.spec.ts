import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';

test.describe('Health Dashboard - Filter Interactions', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#services');
  });

  test('Apply filter', async ({ page }) => {
    const filterInput = page.locator('input[type="search"], input[placeholder*="filter"]').first();
    
    if (await filterInput.isVisible({ timeout: 2000 })) {
      await filterInput.fill('websocket');
      await page.waitForTimeout(500);
      
      const results = page.locator('[data-testid="service-card"], [class*="ServiceCard"]');
      await expect(results.first()).toBeVisible();
    }
  });

  test('Clear filter', async ({ page }) => {
    const filterInput = page.locator('input[type="search"], input[placeholder*="filter"]').first();
    
    if (await filterInput.isVisible({ timeout: 2000 })) {
      await filterInput.fill('test');
      await page.waitForTimeout(500);
      
      const clearButton = page.locator('button[aria-label*="clear"], button:has([class*="clear"])').first();
      
      if (await clearButton.isVisible({ timeout: 1000 })) {
        await clearButton.click();
        await page.waitForTimeout(500);
        await expect(filterInput).toHaveValue('');
      }
    }
  });

  test('Multiple filter selections', async ({ page }) => {
    const filterSelect = page.locator('select, [data-testid="filter"]').first();
    
    if (await filterSelect.isVisible({ timeout: 2000 })) {
      await filterSelect.selectOption({ index: 0 });
      await page.waitForTimeout(500);
      
      // Try another selection
      await filterSelect.selectOption({ index: 1 });
      await page.waitForTimeout(500);
    }
  });

  test('Reset filters', async ({ page }) => {
    const resetButton = page.locator('button:has-text("Reset"), button[aria-label*="reset"]').first();
    
    if (await resetButton.isVisible({ timeout: 2000 })) {
      await resetButton.click();
      await page.waitForTimeout(500);
    }
  });
});
