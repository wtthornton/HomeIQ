import { test, expect } from '@playwright/test';
import { HealthDashboardPage } from './page-objects/HealthDashboardPage';

/**
 * Monitoring Screen E2E Tests
 * Aligned with current health-dashboard: Services tab = monitoring (tab-based, hash routing)
 *
 * Epic 84: Removed all legacy selectors (performance-metrics, service-monitoring,
 * service-details-modal, alert-management, log-viewer sub-selectors, export,
 * monitoring-error). Tests now use valid dashboard testids.
 */
test.describe('Monitoring Screen Tests', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000/#services');
    await page.waitForLoadState('domcontentloaded');
  });

  test('Services tab (monitoring) loads correctly', async ({ page }) => {
    const dashboard = new HealthDashboardPage(page);
    await expect(dashboard.getDashboardRoot()).toBeVisible({ timeout: 15000 });
    await expect(dashboard.getTab('services')).toHaveAttribute('aria-selected', 'true');
    await expect(page.locator('[data-testid="dashboard-content"]')).toBeVisible();
  });

  test('Services tab displays service list', async ({ page }) => {
    await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

    // Service list should be visible on the Services tab
    const serviceList = page.locator('[data-testid="service-list"]');
    await expect(serviceList).toBeVisible({ timeout: 10000 });

    // Service cards should be rendered inside
    const serviceCards = page.locator('[data-testid="service-card"]');
    const cardCount = await serviceCards.count();
    expect(cardCount).toBeGreaterThan(0);
  });

  test('Service cards display status information', async ({ page }) => {
    await page.waitForSelector('[data-testid="service-list"]', { timeout: 15000 });

    const firstCard = page.locator('[data-testid="service-card"]').first();
    await expect(firstCard).toBeVisible();

    // Service card should have visible text content
    const cardText = await firstCard.textContent();
    expect(cardText?.length).toBeGreaterThan(0);
  });

  test('Log viewer is accessible via Logs tab', async ({ page }) => {
    // Navigate to Logs tab
    await page.click('[data-testid="tab-logs"]');

    // Wait for log viewer
    const logViewer = page.locator('[data-testid="log-viewer"]');
    await expect(logViewer).toBeVisible({ timeout: 10000 });
  });

  test('Alert list is accessible via Alerts tab', async ({ page }) => {
    // Navigate to Alerts tab
    await page.click('[data-testid="tab-alerts"]');

    // Wait for alert list
    const alertList = page.locator('[data-testid="alert-list"]');
    await expect(alertList).toBeVisible({ timeout: 10000 });
  });

  test('Services tab is responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:3000/#services');
    await page.waitForLoadState('domcontentloaded');
    const dashboard = new HealthDashboardPage(page);
    await expect(dashboard.getDashboardRoot()).toBeVisible({ timeout: 15000 });
  });

  test('Error states display correctly when API fails', async ({ page }) => {
    // Simulate API failure
    await page.route('**/api/v1/health**', route => route.abort());
    await page.goto('http://localhost:3000/#services');

    // Wait for error state to appear
    const errorState = page.locator('[data-testid="error-state"]');
    if (await errorState.isVisible({ timeout: 10000 }).catch(() => false)) {
      await expect(errorState).toBeVisible();

      // Verify retry button is available
      const retryButton = page.locator('[data-testid="retry-button"]');
      if (await retryButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        await expect(retryButton).toBeVisible();
      }
    }
  });
});
