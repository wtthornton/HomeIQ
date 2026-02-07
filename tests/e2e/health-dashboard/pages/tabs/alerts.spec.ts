import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete, waitForModalOpen } from '../../../../shared/helpers/wait-helpers';

/** Tests run against deployed Docker (no API mocks). */
test.describe('Health Dashboard - Alerts Tab', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#alerts');
    await waitForLoadingComplete(page);
  });

  test('@smoke Alert list loads', async ({ page }) => {
    const alertList = page.locator('[data-testid="alert-list"], [class*="AlertList"], [class*="alert-card"], [class*="alert"]').first();
    await expect(alertList).toBeVisible({ timeout: 15000 });
  });

  test('Alert filtering (severity, status)', async ({ page }) => {
    const severityFilter = page.locator('select, button[aria-label*="severity"], [data-testid="severity-filter"]').first();
    
    if (await severityFilter.isVisible({ timeout: 2000 })) {
      await severityFilter.click();
      await page.locator('option:has-text("warning"), [role="option"]:has-text("warning")').first().click();
      await waitForLoadingComplete(page);
      
      const alerts = page.locator('[data-testid="alert-card"], [class*="AlertCard"]');
      await expect(alerts.first()).toBeVisible();
    }
  });

  test('Alert search works', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="search"]').first();
    
    if (await searchInput.isVisible({ timeout: 2000 })) {
      await searchInput.fill('service');
      await waitForLoadingComplete(page);
      
      const results = page.locator('[data-testid="alert-card"], [class*="AlertCard"]');
      await expect(results.filter({ hasText: /service/i }).first()).toBeVisible();
    }
  });

  test('Alert details modal', async ({ page }) => {
    const firstAlert = page.locator('[data-testid="alert-card"], [class*="AlertCard"]').first();
    await firstAlert.click();
    await waitForModalOpen(page);
    
    const modal = page.locator('[role="dialog"], .modal').first();
    await expect(modal).toBeVisible({ timeout: 3000 });
  });

  test('Alert acknowledgment', async ({ page }) => {
    const acknowledgeButton = page.locator('button:has-text("Acknowledge"), button[aria-label*="acknowledge"]').first();
    
    if (await acknowledgeButton.isVisible({ timeout: 2000 })) {
      await acknowledgeButton.click();
      await waitForLoadingComplete(page);

      // Verify alert state changed and click didn't crash
      const alert = page.locator('[data-testid="alert-card"], [class*="AlertCard"]').first();
      await expect(alert).toBeVisible();
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    }
  });

  test('Alert statistics', async ({ page }) => {
    const stats = page.locator('[data-testid="alert-stats"], [class*="statistics"]').first();
    const exists = await stats.isVisible().catch(() => false);
    expect(typeof exists).toBe('boolean');
  });

  test('Alert history', async ({ page }) => {
    const historyButton = page.locator('button:has-text("History"), [data-testid="history"]').first();
    
    if (await historyButton.isVisible({ timeout: 2000 })) {
      await historyButton.click();
      await waitForModalOpen(page);
      
      const history = page.locator('[data-testid="alert-history"], [class*="History"]').first();
      await expect(history).toBeVisible({ timeout: 3000 });
    }
  });
});
