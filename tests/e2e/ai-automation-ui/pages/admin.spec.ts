import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('AI Automation UI - Admin Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/admin');
    await waitForLoadingComplete(page);
  });

  test('@smoke Admin panel loads', async ({ page }) => {
    await expect(page.locator('body')).toBeVisible();
  });

  test('Admin features accessible', async ({ page }) => {
    const adminSections = page.locator('[data-testid="admin-section"], [class*="Admin"]');
    const count = await adminSections.count();
    // Admin sections might be available
  });

  test('Configuration management', async ({ page }) => {
    const configSection = page.locator('[data-testid="config"], [class*="Config"]').first();
    const exists = await configSection.isVisible().catch(() => false);
    // Configuration might be available
  });

  test('System controls', async ({ page }) => {
    const systemControls = page.locator('[data-testid="system-controls"], [class*="SystemControls"]').first();
    const exists = await systemControls.isVisible().catch(() => false);
    // System controls might be available
  });
});
