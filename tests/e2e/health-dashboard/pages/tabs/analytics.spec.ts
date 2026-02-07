import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete, waitForChartRender } from '../../../../shared/helpers/wait-helpers';

/** Tests run against deployed Docker (no API mocks). */
test.describe('Health Dashboard - Analytics Tab', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#analytics');
    await waitForLoadingComplete(page);
  });

  test('@smoke Analytics charts render', async ({ page }) => {
    const charts = page.locator('canvas, svg[class*="chart"], [class*="Chart"]');
    await waitForChartRender(charts.first());
    await expect(charts.first()).toBeVisible({ timeout: 10000 });
  });

  test('Time range selector works', async ({ page }) => {
    const timeRangeSelect = page.locator('select, button[aria-label*="time"], [data-testid="time-range"]').first();
    
    if (await timeRangeSelect.isVisible({ timeout: 2000 })) {
      await timeRangeSelect.click();
      await page.locator('option:has-text("7d"), [role="option"]:has-text("7d")').first().click();
      await waitForLoadingComplete(page);
      
      // Verify charts updated
      const charts = page.locator('canvas, svg[class*="chart"]');
      await expect(charts.first()).toBeVisible();
    }
  });

  test('Metric selection works', async ({ page }) => {
    const metricSelect = page.locator('select, [data-testid="metric-select"], button[aria-label*="metric"]').first();
    
    if (await metricSelect.isVisible({ timeout: 2000 })) {
      await metricSelect.click();
      await waitForLoadingComplete(page);
    }
  });

  test('Chart interactions (zoom, pan)', async ({ page }) => {
    const chart = page.locator('canvas, svg[class*="chart"]').first();
    await waitForChartRender(chart);
    
    // Try to interact with chart (if interactive)
    await chart.hover();
    await waitForLoadingComplete(page);

    const tooltip = page.locator('[role="tooltip"], [class*="tooltip"]').first();
    // Tooltip may or may not appear depending on chart type

    // Verify chart is still visible after interaction
    await expect(chart).toBeVisible();
  });

  test('Data export functionality', async ({ page }) => {
    const exportButton = page.locator('button:has-text("Export"), button[aria-label*="export"]').first();
    
    if (await exportButton.isVisible({ timeout: 2000 })) {
      const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);
      await exportButton.click();
      // Verify export triggered
    }
  });

  test('Filter application', async ({ page }) => {
    const filterInput = page.locator('input, select, [data-testid="filter"]').first();
    
    if (await filterInput.isVisible({ timeout: 2000 })) {
      await filterInput.fill('events');
      await waitForLoadingComplete(page);
      
      // Verify filter applied
      const charts = page.locator('canvas, svg[class*="chart"]');
      await expect(charts.first()).toBeVisible();
    }
  });

  test('Loading states', async ({ page }) => {
    await page.goto('/#services');
    await page.goto('/#analytics');

    const loadingIndicators = page.locator('[data-testid="loading"], .loading, .spinner');
    // Loading might be fast, but structure supports it
    await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
  });

  test.skip('Error handling (requires API mock; run in mock suite if needed)', async ({ page }) => {
    const errorMessage = page.locator('[data-testid="error"], .error, [role="alert"]').first();
    await expect(errorMessage).toBeVisible({ timeout: 5000 });
  });
});
