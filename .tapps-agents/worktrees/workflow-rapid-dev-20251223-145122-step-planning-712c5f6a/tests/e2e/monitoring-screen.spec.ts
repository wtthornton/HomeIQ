import { test, expect } from '@playwright/test';

/**
 * Monitoring Screen E2E Tests
 * Tests the monitoring interface functionality
 */
test.describe('Monitoring Screen Tests', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000/monitoring');
    await page.waitForLoadState('networkidle');
  });

  test('Monitoring screen loads correctly', async ({ page }) => {
    // Wait for monitoring screen to load
    await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 15000 });
    
    // Verify main monitoring elements
    await expect(page.locator('[data-testid="monitoring-screen"]')).toBeVisible();
    await expect(page.locator('[data-testid="service-monitoring"]')).toBeVisible();
    await expect(page.locator('[data-testid="performance-metrics"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-management"]')).toBeVisible();
    
    // Verify page title
    await expect(page.locator('h1')).toContainText('System Monitoring');
  });

  test('Service monitoring displays all services', async ({ page }) => {
    // Wait for service monitoring section
    await page.waitForSelector('[data-testid="service-monitoring"]');
    
    // Verify all services are monitored
    const serviceCards = page.locator('[data-testid="service-card"]');
    await expect(serviceCards).toHaveCount(5); // All 5 services
    
    // Verify each service card has required information
    const serviceNames = ['WebSocket Ingestion', 'Enrichment Pipeline', 'Admin API', 'Data Retention', 'Weather API'];
    
    for (const serviceName of serviceNames) {
      const serviceCard = page.locator(`[data-testid="service-card"]:has-text("${serviceName}")`);
      await expect(serviceCard).toBeVisible();
      await expect(serviceCard.locator('[data-testid="service-status"]')).toBeVisible();
      await expect(serviceCard.locator('[data-testid="service-uptime"]')).toBeVisible();
      await expect(serviceCard.locator('[data-testid="service-metrics"]')).toBeVisible();
    }
  });

  test('Performance metrics display correctly', async ({ page }) => {
    // Wait for performance metrics section
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

  test('Real-time updates work correctly', async ({ page }) => {
    // Wait for monitoring data to load
    await page.waitForSelector('[data-testid="service-monitoring"]');
    
    // Get initial timestamp
    const initialTimestamp = await page.locator('[data-testid="last-updated"]').textContent();
    
    // Wait for refresh interval
    await page.waitForTimeout(5000);
    
    // Check if timestamp has updated
    const updatedTimestamp = await page.locator('[data-testid="last-updated"]').textContent();
    expect(updatedTimestamp).not.toBe(initialTimestamp);
  });

  test('Service details modal opens and displays information', async ({ page }) => {
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

  test('Alert management displays active alerts', async ({ page }) => {
    // Wait for alert management section
    await page.waitForSelector('[data-testid="alert-management"]');
    
    // Check for active alerts
    const alertsList = page.locator('[data-testid="alerts-list"]');
    await expect(alertsList).toBeVisible();
    
    // Verify alert items if any exist
    const alertItems = page.locator('[data-testid="alert-item"]');
    const alertCount = await alertItems.count();
    
    if (alertCount > 0) {
      const firstAlert = alertItems.first();
      await expect(firstAlert.locator('[data-testid="alert-severity"]')).toBeVisible();
      await expect(firstAlert.locator('[data-testid="alert-message"]')).toBeVisible();
      await expect(firstAlert.locator('[data-testid="alert-timestamp"]')).toBeVisible();
    }
  });

  test('Log viewer displays service logs', async ({ page }) => {
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

  test('Export functionality works for monitoring data', async ({ page }) => {
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

  test('Monitoring screen is responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    await page.goto('http://localhost:3000/monitoring');
    await page.waitForLoadState('networkidle');
    
    // Verify mobile layout
    await expect(page.locator('[data-testid="monitoring-screen"]')).toBeVisible();
    
    // Check if mobile-specific elements are present
    const mobileMenu = page.locator('[data-testid="mobile-monitoring-menu"]');
    if (await mobileMenu.isVisible()) {
      await mobileMenu.click();
      
      const mobileMenuItems = page.locator('[data-testid="mobile-menu-item"]');
      await expect(mobileMenuItems).toHaveCount.greaterThan(0);
    }
  });

  test('Error states are handled gracefully', async ({ page }) => {
    // Simulate network error by intercepting monitoring API calls
    await page.route('**/api/v1/monitoring/**', route => route.abort());
    
    await page.goto('http://localhost:3000/monitoring');
    
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
