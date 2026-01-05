import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForModalOpen } from '../../../shared/helpers/wait-helpers';

test.describe('Health Dashboard - Modal Components', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#services');
  });

  test('Modal opens on trigger', async ({ page }) => {
    const trigger = page.locator('[data-testid="service-card"], [class*="ServiceCard"]').first();
    await trigger.click();
    await waitForModalOpen(page);
    
    const modal = page.locator('[role="dialog"], .modal').first();
    await expect(modal).toBeVisible({ timeout: 3000 });
  });

  test('Modal closes on close button', async ({ page }) => {
    const trigger = page.locator('[data-testid="service-card"]').first();
    await trigger.click();
    await waitForModalOpen(page);
    
    const closeButton = page.locator('button[aria-label*="close"], button:has([class*="close"])').first();
    await closeButton.click();
    await page.waitForTimeout(500);
    
    const modal = page.locator('[role="dialog"]').first();
    await expect(modal).not.toBeVisible();
  });

  test('Modal closes on backdrop click', async ({ page }) => {
    const trigger = page.locator('[data-testid="service-card"]').first();
    await trigger.click();
    await waitForModalOpen(page);
    
    const backdrop = page.locator('.modal-backdrop, [class*="backdrop"], [class*="overlay"]').first();
    
    if (await backdrop.isVisible({ timeout: 2000 })) {
      await backdrop.click({ position: { x: 10, y: 10 } });
      await page.waitForTimeout(500);
      
      const modal = page.locator('[role="dialog"]').first();
      await expect(modal).not.toBeVisible();
    }
  });

  test('Modal closes on ESC key', async ({ page }) => {
    const trigger = page.locator('[data-testid="service-card"]').first();
    await trigger.click();
    await waitForModalOpen(page);
    
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    
    const modal = page.locator('[role="dialog"]').first();
    await expect(modal).not.toBeVisible();
  });

  test('Modal interactions work', async ({ page }) => {
    const trigger = page.locator('[data-testid="service-card"]').first();
    await trigger.click();
    await waitForModalOpen(page);
    
    const input = page.locator('input, textarea, select').first();
    
    if (await input.isVisible({ timeout: 2000 })) {
      await input.fill('test');
      await expect(input).toHaveValue('test');
    }
  });
});
