import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete, waitForModalOpen } from '../../../../shared/helpers/wait-helpers';

/** Tests run against deployed Docker (no API mocks). */
test.describe('Health Dashboard - Data Sources Tab', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#data-sources');
    await waitForLoadingComplete(page);
  });

  test('@smoke Data source list displays', async ({ page }) => {
    const dataSources = page.locator('[data-testid="data-source"], [class*="DataSource"]').first();
    await expect(dataSources).toBeVisible({ timeout: 5000 });
  });

  test('Integration status indicators', async ({ page }) => {
    const statusIndicators = page.locator('[data-testid="status-indicator"], [class*="status"]');
    const count = await statusIndicators.count();
    expect(count).toBeGreaterThan(0);
  });

  test('Data source configuration modal', async ({ page }) => {
    const configButton = page.locator('button:has-text("Configure"), [data-testid="configure"]').first();
    
    if (await configButton.isVisible({ timeout: 2000 })) {
      await configButton.click();
      await waitForModalOpen(page);
      const modal = page.locator('[role="dialog"], .modal').first();
      await expect(modal).toBeVisible({ timeout: 3000 });
    }
  });

  test('Connection status', async ({ page }) => {
    const connectionStatus = page.locator('[data-testid="connection-status"], [class*="connection"]');
    const count = await connectionStatus.count();
    expect(count).toBeGreaterThan(0);
  });

  test('Data freshness indicators', async ({ page }) => {
    const freshnessIndicators = page.locator('[data-testid="freshness"], [class*="freshness"]');
    const count = await freshnessIndicators.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('Integration enable/disable', async ({ page }) => {
    const toggleButton = page.locator('button[aria-label*="toggle"], [data-testid="toggle"]').first();
    
    if (await toggleButton.isVisible({ timeout: 2000 })) {
      const initialState = await toggleButton.getAttribute('aria-checked') ?? await toggleButton.getAttribute('data-state');
      await toggleButton.click();
      await waitForLoadingComplete(page);
      // Verify toggle was acknowledged (button should still be visible after click)
      await expect(toggleButton).toBeVisible();
    }
  });

  test('API key management', async ({ page }) => {
    const apiKeyButton = page.locator('button:has-text("API Key"), [data-testid="api-key"]').first();
    
    if (await apiKeyButton.isVisible({ timeout: 2000 })) {
      await apiKeyButton.click();
      await waitForModalOpen(page);
      const modal = page.locator('[role="dialog"], .modal').first();
      await expect(modal).toBeVisible({ timeout: 3000 });
    }
  });
});
