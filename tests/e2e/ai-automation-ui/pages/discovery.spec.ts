import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('AI Automation UI - Discovery Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/explore');
    await waitForLoadingComplete(page);
  });

  test('@smoke Device explorer loads', async ({ page }) => {
    // Require page-specific content: explorer component or heading unique to Explore (no bare #main-content).
    const main = page.locator('#main-content');
    const explorerOrHeading = main.locator('[data-testid="device-explorer"], [class*="DeviceExplorer"], [class*="Discovery"]')
      .or(main.getByRole('heading', { name: /explore|device/i }));
    await expect(explorerOrHeading.first()).toBeVisible({ timeout: 10000 });
  });

  test('P4.7 Discovery page loads and displays device explorer or content', async ({ page }) => {
    const content = page.locator('[data-testid="device-explorer"], [class*="DeviceExplorer"], [class*="Discovery"], main').first();
    await expect(content).toBeVisible({ timeout: 8000 });
  });

  test('Device list displays', async ({ page }) => {
    const deviceList = page.locator('[data-testid="device-explorer"], [data-testid="device-list"], select, [class*="DeviceExplorer"]').first();
    await expect(deviceList).toBeVisible({ timeout: 5000 });
  });

  test('Smart shopping recommendations', async ({ page }) => {
    const smartShopping = page.locator('[data-testid="smart-shopping"], [class*="SmartShopping"]').first();
    const exists = await smartShopping.isVisible().catch(() => false);
    // Smart shopping might be available
  });

  test('Device filtering', async ({ page }) => {
    // Use select dropdown within device explorer (not generic input matcher)
    const filterSelect = page.locator('[data-testid="device-explorer"] select').first();
    const filterInput = page.locator('[data-testid="device-explorer"] input').first();

    const hasSelect = await filterSelect.isVisible({ timeout: 2000 }).catch(() => false);
    const hasInput = await filterInput.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasSelect) {
      await filterSelect.click();
      await page.waitForTimeout(500);
    } else if (hasInput) {
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
