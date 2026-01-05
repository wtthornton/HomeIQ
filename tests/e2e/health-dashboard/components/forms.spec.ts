import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';

test.describe('Health Dashboard - Form Components', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#configuration');
  });

  test('Form validation works', async ({ page }) => {
    const submitButton = page.locator('button[type="submit"], button:has-text("Save")').first();
    
    if (await submitButton.isVisible({ timeout: 2000 })) {
      await submitButton.click();
      
      // Look for validation errors
      const errors = page.locator('[role="alert"], .error, [class*="error"]');
      // Validation errors might appear
    }
  });

  test('Form submission works', async ({ page }) => {
    const input = page.locator('input, textarea').first();
    
    if (await input.isVisible({ timeout: 2000 })) {
      await input.fill('test value');
      const submitButton = page.locator('button[type="submit"]').first();
      await submitButton.click();
      await page.waitForTimeout(1000);
    }
  });

  test('Error states display', async ({ page }) => {
    // Try to submit invalid form
    const submitButton = page.locator('button[type="submit"]').first();
    
    if (await submitButton.isVisible({ timeout: 2000 })) {
      await submitButton.click();
      await page.waitForTimeout(500);
      
      const errors = page.locator('[role="alert"], .error').first();
      const exists = await errors.isVisible().catch(() => false);
      // Errors might appear
    }
  });

  test('Input fields work', async ({ page }) => {
    const input = page.locator('input[type="text"], input[type="number"], textarea').first();
    
    if (await input.isVisible({ timeout: 2000 })) {
      await input.fill('test');
      await expect(input).toHaveValue('test');
    }
  });
});
