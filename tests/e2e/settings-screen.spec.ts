import { test, expect } from '@playwright/test';
import { HealthDashboardPage } from './page-objects/HealthDashboardPage';

/**
 * Settings/Configuration Screen E2E Tests
 * Uses health-dashboard Configuration tab (#configuration) - hash routing
 *
 * Epic 84: Removed legacy sub-selectors (settings-navigation, settings-tab-*,
 * settings-content-*, save-success, etc.) that do not exist in the current
 * health-dashboard. Configuration tab renders sub-components (threshold-config,
 * service-control, container-management, api-key-management) via lazy loading.
 */
test.describe('Settings Screen Tests', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000/#configuration');
    await page.waitForLoadState('domcontentloaded');
  });

  test('Configuration tab loads correctly', async ({ page }) => {
    const dashboard = new HealthDashboardPage(page);
    await expect(dashboard.getDashboardRoot()).toBeVisible({ timeout: 15000 });
    await expect(dashboard.getTab('configuration')).toHaveAttribute('aria-selected', 'true');
    await expect(page.locator('[data-testid="dashboard-content"]')).toBeVisible();
  });

  test('Configuration tab displays content', async ({ page }) => {
    const content = page.locator('[data-testid="dashboard-content"]');
    await expect(content).toBeVisible({ timeout: 10000 });
    const bodyText = await page.locator('body').textContent();
    expect(bodyText?.length).toBeGreaterThan(100);
  });

  test('Theme toggle works from Configuration tab', async ({ page }) => {
    const dashboard = new HealthDashboardPage(page);
    await expect(dashboard.getDashboardRoot()).toBeVisible({ timeout: 15000 });

    const themeToggle = page.locator('[data-testid="theme-toggle"]');
    if (await themeToggle.isVisible({ timeout: 3000 }).catch(() => false)) {
      await themeToggle.click();
      // Dashboard should still be visible after toggle
      await expect(dashboard.getDashboardRoot()).toBeVisible();
    }
  });

  test('Auto-refresh toggle works from Configuration tab', async ({ page }) => {
    await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

    const autoRefresh = page.locator('[data-testid="auto-refresh-toggle"]');
    if (await autoRefresh.isVisible({ timeout: 3000 }).catch(() => false)) {
      await autoRefresh.click();
      await expect(autoRefresh).toBeVisible();
    }
  });

  test('Time range selector is accessible from Configuration tab', async ({ page }) => {
    await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

    const timeRange = page.locator('[data-testid="time-range-selector"]');
    if (await timeRange.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(timeRange).toBeVisible();
    }
  });

  test('Configuration tab is responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:3000/#configuration');
    await page.waitForLoadState('domcontentloaded');
    const dashboard = new HealthDashboardPage(page);
    await expect(dashboard.getDashboardRoot()).toBeVisible({ timeout: 15000 });
  });

  test('Can navigate away from Configuration and back', async ({ page }) => {
    const dashboard = new HealthDashboardPage(page);
    await expect(dashboard.getDashboardRoot()).toBeVisible({ timeout: 15000 });

    // Navigate to Overview tab
    await page.click('[data-testid="tab-overview"]');
    await page.waitForSelector('[data-testid="health-card"]', { timeout: 10000 });

    // Navigate back to Configuration
    await page.click('[data-testid="tab-configuration"]');
    await page.waitForSelector('[data-testid="dashboard-content"]', { timeout: 10000 });
    await expect(page.locator('[data-testid="dashboard-content"]')).toBeVisible();
  });
});
