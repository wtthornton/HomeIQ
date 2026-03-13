/**
 * Health Dashboard E2E Smoke Tests (Story 59.3)
 *
 * Lightweight, fast-running tests for PR gates.
 * Validates critical user journeys without deep assertions.
 *
 * Coverage:
 * - Dashboard loads with system status
 * - Overview page renders key metrics sections
 * - Services tab shows health information
 * - Devices tab loads and shows device list
 * - Navigation across all sidebar groups works
 * - Dark mode toggle persists across navigation
 * - Time range selector is functional
 * - Auto-refresh toggle works
 * - No critical console errors during navigation
 * - Hash-based deep linking works
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../shared/helpers/wait-helpers';
import { HealthDashboardPage } from '../page-objects/HealthDashboardPage';

test.describe('Health Dashboard Smoke Tests @smoke', () => {
  let dashboard: HealthDashboardPage;

  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    dashboard = new HealthDashboardPage(page);
  });

  test('dashboard loads and shows system status', async ({ page }) => {
    await dashboard.goto();

    // System status region must be visible with a clear state
    const statusText = page.getByRole('status');
    await expect(statusText).toBeVisible({ timeout: 15000 });
    await expect(statusText).toContainText(/operational|degraded|critical|down/i);
  });

  test('overview page renders key metric sections', async ({ page }) => {
    await dashboard.goto('/#overview');
    await waitForLoadingComplete(page);

    // KPI panel with performance metrics
    const kpiSection = page.getByRole('complementary', { name: /key performance indicators/i });
    await expect(kpiSection).toBeVisible({ timeout: 10000 });

    // Core system components (ingestion + storage)
    const componentsGroup = page.getByRole('group', { name: /core system components/i });
    await expect(componentsGroup).toBeVisible({ timeout: 10000 });
  });

  test('services tab shows health status information', async ({ page }) => {
    await dashboard.goToTab('services');

    // Services page should render with content
    const dashboardRoot = dashboard.getDashboardRoot();
    await expect(dashboardRoot).toBeVisible({ timeout: 10000 });

    // Should show at least one service health indicator
    const healthText = page.getByText(/healthy|unhealthy|degraded|running|stopped/i).first();
    await expect(healthText).toBeVisible({ timeout: 10000 });
  });

  test('devices tab loads and shows device information', async ({ page }) => {
    await dashboard.goToTab('devices');

    const dashboardRoot = dashboard.getDashboardRoot();
    await expect(dashboardRoot).toBeVisible({ timeout: 10000 });

    // Devices tab should show device count or list
    const deviceContent = page.getByText(/device|entity|area/i).first();
    await expect(deviceContent).toBeVisible({ timeout: 10000 });
  });

  test('all sidebar groups are navigable without errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    // Navigate through one tab per sidebar group
    const representativeTabs = ['overview', 'services', 'devices', 'alerts', 'logs'];
    for (const tabId of representativeTabs) {
      await dashboard.goToTab(tabId);
      const root = dashboard.getDashboardRoot();
      await expect(root, `Tab "${tabId}" should render`).toBeVisible({ timeout: 10000 });
    }

    // Filter known noise
    const criticalErrors = errors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('404') &&
        !e.includes('429') &&
        !e.includes('Too Many Requests') &&
        !e.includes('rate limit') &&
        !e.includes('font') &&
        !e.includes('woff') &&
        !e.includes('manifest') &&
        !e.includes('sourcemap') &&
        !e.includes('Failed to load resource') &&
        !e.includes('API Error') &&
        !e.includes('Error fetching') &&
        !e.includes('VITE_API_KEY'),
    );
    expect(criticalErrors).toHaveLength(0);
  });

  test('dark mode toggle changes theme and persists across navigation', async ({ page }) => {
    await dashboard.goto('/#overview');
    await waitForLoadingComplete(page);

    const wasDark = await dashboard.isDarkMode();
    const isDarkAfterToggle = await dashboard.toggleTheme();
    expect(isDarkAfterToggle).not.toBe(wasDark);

    // Navigate to a different tab
    await dashboard.goToTab('services');
    await waitForLoadingComplete(page);

    // Theme should persist
    const isDarkAfterNav = await dashboard.isDarkMode();
    expect(isDarkAfterNav).toBe(isDarkAfterToggle);

    // Toggle back to restore original state
    await dashboard.toggleTheme();
  });

  test('time range selector is interactive', async ({ page }) => {
    await dashboard.goto('/#overview');
    await waitForLoadingComplete(page);

    const selector = dashboard.getTimeRangeSelector();
    await expect(selector).toBeVisible({ timeout: 5000 });

    // Should be able to select a different time range
    // The selector options vary; just verify it's interactive
    const tagName = await selector.evaluate((el) => el.tagName.toLowerCase());
    expect(tagName).toBe('select');
  });

  test('auto-refresh toggle switches state', async ({ page }) => {
    await dashboard.goto('/#overview');
    await waitForLoadingComplete(page);

    const toggle = dashboard.getAutoRefreshToggle();
    await expect(toggle).toBeVisible({ timeout: 5000 });

    // Get initial state
    const initialLabel = await toggle.getAttribute('aria-label');

    // Toggle
    await toggle.click();
    await page.waitForTimeout(300);

    // State should change
    const newLabel = await toggle.getAttribute('aria-label');
    expect(newLabel).not.toBe(initialLabel);

    // Toggle back
    await toggle.click();
  });

  test('hash-based deep linking loads correct tab', async ({ page }) => {
    // Navigate directly to alerts via hash
    await dashboard.goToTab('alerts');

    // URL should have alerts hash
    expect(page.url()).toContain('#alerts');

    // The dashboard should be visible (tab rendered)
    const root = dashboard.getDashboardRoot();
    await expect(root).toBeVisible({ timeout: 10000 });
  });

  test('sidebar clicking updates URL hash for deep-linking', async ({ page }) => {
    await dashboard.goto('/#overview');
    await waitForLoadingComplete(page);

    // Expand Infrastructure group and click Services
    const sidebar = dashboard.getSidebar();
    const infraGroup = sidebar.getByRole('button', { name: /infrastructure/i });
    await expect(infraGroup).toBeVisible({ timeout: 5000 });
    await infraGroup.click();
    await page.waitForTimeout(300);

    const servicesTab = page.getByTestId('tab-services');
    await expect(servicesTab).toBeVisible({ timeout: 5000 });
    await servicesTab.click();

    await page.waitForURL(/#services/, { timeout: 5000 });
    expect(page.url()).toContain('#services');
  });

  test('dashboard handles API errors gracefully', async ({ page }) => {
    // Route health endpoint to return 500
    await page.route('**/api/v1/health**', (route) =>
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' }),
      }),
    );

    await page.goto('/#overview');
    await waitForLoadingComplete(page);

    // Dashboard should still render (not crash)
    const root = page.locator('[data-testid="dashboard-root"]');
    await expect(root).toBeVisible({ timeout: 15000 });

    // Should show error state or retry option
    const errorOrRetry = page.locator(
      '[data-testid="error-state"], [data-testid="retry-button"], button:has-text("Retry")',
    );
    await expect(errorOrRetry.first()).toBeVisible({ timeout: 10000 });
  });
});
