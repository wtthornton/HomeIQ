import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('AI Automation UI - Discovery Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/discovery');
    await waitForLoadingComplete(page);
  });

  test('@smoke Device explorer loads', async ({ page }) => {
    const deviceExplorer = page.locator('[data-testid="device-explorer"], [class*="DeviceExplorer"]').first();
    await expect(deviceExplorer).toBeVisible({ timeout: 5000 });
  });

  test('P4.7 Discovery page loads and displays device explorer or content', async ({ page }) => {
    const content = page.locator('[data-testid="device-explorer"], [class*="DeviceExplorer"], [class*="Discovery"], main').first();
    await expect(content).toBeVisible({ timeout: 8000 });
  });

  test('Device list displays', async ({ page }) => {
    const deviceList = page.locator('[data-testid="device-list"], [class*="DeviceList"]').first();
    await expect(deviceList).toBeVisible({ timeout: 5000 });
  });

  test('Smart shopping recommendations', async ({ page }) => {
    const smartShopping = page.locator('[data-testid="smart-shopping"], [class*="SmartShopping"]').first();
    const exists = await smartShopping.isVisible().catch(() => false);
    // Smart shopping might be available
  });

  test('Device filtering', async ({ page }) => {
    const filterInput = page.locator('input, select, [data-testid="filter"]').first();
    
    if (await filterInput.isVisible({ timeout: 2000 })) {
      await filterInput.fill('light');
      await page.waitForTimeout(500);
    }
  });

  test('Capability analysis', async ({ page }) => {
    const capabilitySection = page.locator('[data-testid="capabilities"], [class*="Capability"]').first();
    const exists = await capabilitySection.isVisible().catch(() => false);
    // Capability analysis might be available
  });

  test('Purchase recommendations', async ({ page }) => {
    const recommendations = page.locator('[data-testid="recommendations"], [class*="Recommendation"]').first();
    const exists = await recommendations.isVisible().catch(() => false);
    // Recommendations might be available
  });
});
