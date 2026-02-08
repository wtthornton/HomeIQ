import { test, expect } from '@playwright/test';
import { HealthDashboardPage } from './page-objects/HealthDashboardPage';

/**
 * Monitoring Screen E2E Tests
 * Aligned with current health-dashboard: Services tab = monitoring (tab-based, hash routing)
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

  test('Services tab displays content', async ({ page }) => {
    const content = page.locator('[data-testid="dashboard-content"]');
    await expect(content).toBeVisible({ timeout: 10000 });
    const bodyText = await page.locator('body').textContent();
    expect(bodyText?.length).toBeGreaterThan(100);
  });

  test.skip('Performance metrics display (legacy selector)', async ({ page }) => {
    await page.waitForSelector('[data-testid="performance-metrics"]');
    
    // Verify key performance indicators
    await expect(page.locator('[data-testid="cpu-usage"]')).toBeVisible();
    await expect(page.locator('[data-testid="memory-usage"]')).toBeVisible();
    await expect(page.locator('[data-testid="disk-usage"]')).toBeVisible();
    await expect(page.locator('[data-testid="network-io"]')).toBeVisible();
    
    // Verify metrics have values
    const cpuUsage = page.locator('[data-testid="cpu-usage"] [data-testid="metric-value"]');
    await expect(cpuUsage).toBeVisible();
    
    const memoryUsage = page.locator('[data-testid="memory-usage"] [data-testid="metric-value"]');
    await expect(memoryUsage).toBeVisible();
  });

  test.skip('Real-time updates work correctly (legacy)', async ({ page }) => {
    await page.waitForSelector('[data-testid="service-monitoring"]');
    const initialTimestamp = await page.locator('[data-testid="last-updated"]').textContent();
    await page.waitForTimeout(5000);
    const updatedTimestamp = await page.locator('[data-testid="last-updated"]').textContent();
    expect(updatedTimestamp).not.toBe(initialTimestamp);
  });

  test.skip('Service details modal (legacy selectors)', async ({ page }) => {
    // Wait for service cards to load
    await page.waitForSelector('[data-testid="service-card"]');
    
    // Click on first service card to open details
    const firstServiceCard = page.locator('[data-testid="service-card"]').first();
    await firstServiceCard.click();
    
    // Wait for modal to open
    await page.waitForSelector('[data-testid="service-details-modal"]');
    
    // Verify modal content
    const modal = page.locator('[data-testid="service-details-modal"]');
    await expect(modal).toBeVisible();
    await expect(modal.locator('[data-testid="service-name"]')).toBeVisible();
    await expect(modal.locator('[data-testid="service-logs"]')).toBeVisible();
    await expect(modal.locator('[data-testid="service-config"]')).toBeVisible();
    
    // Close modal
    await page.click('[data-testid="close-modal"]');
    await expect(modal).not.toBeVisible();
  });

  test.skip('Alert management (legacy selectors)', async ({ page }) => {
    await page.waitForSelector('[data-testid="alert-management"]');
    const alertsList = page.locator('[data-testid="alerts-list"]');
    await expect(alertsList).toBeVisible();
  });

  test.skip('Log viewer (legacy selectors)', async ({ page }) => {
    // Wait for log viewer section
    await page.waitForSelector('[data-testid="log-viewer"]');
    
    // Verify log viewer controls
    await expect(page.locator('[data-testid="log-service-selector"]')).toBeVisible();
    await expect(page.locator('[data-testid="log-level-filter"]')).toBeVisible();
    await expect(page.locator('[data-testid="log-search"]')).toBeVisible();
    
    // Test service selector
    const serviceSelector = page.locator('[data-testid="log-service-selector"]');
    await serviceSelector.selectOption('websocket-ingestion');
    
    // Wait for logs to load
    await page.waitForTimeout(2000);
    
    // Verify logs are displayed
    const logEntries = page.locator('[data-testid="log-entry"]');
    const logCount = await logEntries.count();
    
    if (logCount > 0) {
      const firstLog = logEntries.first();
      await expect(firstLog.locator('[data-testid="log-timestamp"]')).toBeVisible();
      await expect(firstLog.locator('[data-testid="log-level"]')).toBeVisible();
      await expect(firstLog.locator('[data-testid="log-message"]')).toBeVisible();
    }
  });

  test.skip('Export functionality (legacy selectors)', async ({ page }) => {
    // Wait for monitoring screen to load
    await page.waitForSelector('[data-testid="monitoring-screen"]');
    
    // Find and click export button
    const exportButton = page.locator('[data-testid="export-monitoring-data"]');
    await exportButton.click();
    
    // Wait for export dialog
    await page.waitForSelector('[data-testid="export-dialog"]');
    
    // Select export format
    const formatSelect = page.locator('[data-testid="export-format"]');
    await formatSelect.selectOption('json');
    
    // Click export button in dialog
    await page.click('[data-testid="confirm-export"]');
    
    // Wait for download to start (this would typically trigger a download)
    await page.waitForTimeout(2000);
  });

  test('Services tab is responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:3000/#services');
    await page.waitForLoadState('domcontentloaded');
    const dashboard = new HealthDashboardPage(page);
    await expect(dashboard.getDashboardRoot()).toBeVisible({ timeout: 15000 });
  });

  test.skip('Error states (legacy)', async ({ page }) => {
    await page.route('**/api/v1/monitoring/**', route => route.abort());
    await page.goto('http://localhost:3000/#services');
    
    // Wait for error state to appear
    await page.waitForSelector('[data-testid="monitoring-error"]', { timeout: 10000 });
    
    // Verify error message is displayed
    const errorMessage = page.locator('[data-testid="monitoring-error"]');
    await expect(errorMessage).toBeVisible();
    
    // Verify retry button is available
    const retryButton = page.locator('[data-testid="retry-monitoring"]');
    await expect(retryButton).toBeVisible();
    
    // Test retry functionality
    await retryButton.click();
    await page.waitForTimeout(2000);
  });
});
