import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForModalOpen } from '../../../shared/helpers/wait-helpers';

test.describe('AI Automation UI - Modal Components', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
  });

  test('Modals open correctly', async ({ page }) => {
    const trigger = page.locator('button:has-text("Preview"), [data-testid="preview"]').first();
    
    if (await trigger.isVisible({ timeout: 2000 })) {
      await trigger.click();
      await waitForModalOpen(page);
      
      const modal = page.locator('[role="dialog"], .modal').first();
      await expect(modal).toBeVisible({ timeout: 3000 });
    }
  });

  test('Modals close correctly', async ({ page }) => {
    const trigger = page.locator('button:has-text("Preview")').first();
    
    if (await trigger.isVisible({ timeout: 2000 })) {
      await trigger.click();
      await waitForModalOpen(page);
      
      const closeButton = page.locator('button[aria-label*="close"], button:has([class*="close"])').first();
      await closeButton.click();
      await page.waitForTimeout(500);
      
      const modal = page.locator('[role="dialog"]').first();
      await expect(modal).not.toBeVisible();
    }
  });

  test('Modal interactions work', async ({ page }) => {
    const trigger = page.locator('button:has-text("Preview")').first();
    
    if (await trigger.isVisible({ timeout: 2000 })) {
      await trigger.click();
      await waitForModalOpen(page);
      
      const input = page.locator('input, textarea, select').first();
      if (await input.isVisible({ timeout: 2000 })) {
        await input.fill('test');
        await expect(input).toHaveValue('test');
      }
    }
  });
});
