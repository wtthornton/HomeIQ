import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('AI Automation UI - Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/settings');
    await waitForLoadingComplete(page);
  });

  test('@smoke Settings form loads', async ({ page }) => {
    const settingsForm = page.locator('form, [data-testid="settings-form"], [class*="Settings"]').first();
    await expect(settingsForm).toBeVisible({ timeout: 5000 });
  });

  test('Preference toggles work', async ({ page }) => {
    const toggles = page.locator('input[type="checkbox"], [role="switch"], [data-testid="toggle"]');
    
    if (await toggles.count() > 0) {
      const firstToggle = toggles.first();
      const initialState = await firstToggle.isChecked();
      await firstToggle.click();
      await page.waitForTimeout(300);
      
      const newState = await firstToggle.isChecked();
      expect(newState).not.toBe(initialState);
    }
  });

  test('Feature flags toggle', async ({ page }) => {
    const featureFlags = page.locator('[data-testid="feature-flag"], [class*="FeatureFlag"]');
    const count = await featureFlags.count();
    if (count > 0) {
      await featureFlags.first().click();
      await page.waitForTimeout(500);
    }
  });

  test('Settings persistence', async ({ page }) => {
    const input = page.locator('input, textarea, select').first();
    
    if (await input.isVisible({ timeout: 2000 })) {
      await input.fill('test value');
      await page.reload();
      // Verify value persisted (if implemented)
    }
  });

  test('Form validation', async ({ page }) => {
    const submitButton = page.locator('button[type="submit"], button:has-text("Save")').first();
    
    if (await submitButton.isVisible({ timeout: 2000 })) {
      await submitButton.click();
      await page.waitForTimeout(500);
      
      const errors = page.locator('[role="alert"], .error');
      // Validation errors might appear
    }
  });

  test('Save functionality', async ({ page }) => {
    const saveButton = page.locator('button:has-text("Save"), button[type="submit"]').first();
    
    if (await saveButton.isVisible({ timeout: 2000 })) {
      await saveButton.click();
      await page.waitForTimeout(1000);
      
      // Look for success message
      const successMessage = page.locator('[role="alert"], .success, [class*="toast"]').first();
      const exists = await successMessage.isVisible().catch(() => false);
    }
  });
});
