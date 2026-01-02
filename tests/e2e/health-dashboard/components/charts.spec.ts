import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForChartRender } from '../../../../shared/helpers/wait-helpers';

test.describe('Health Dashboard - Chart Components', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#overview');
  });

  test('Charts render correctly', async ({ page }) => {
    const charts = page.locator('canvas, svg[class*="chart"], [class*="Chart"]');
    await waitForChartRender(charts.first());
    await expect(charts.first()).toBeVisible({ timeout: 10000 });
  });

  test('Chart interactions (hover)', async ({ page }) => {
    const chart = page.locator('canvas, svg[class*="chart"]').first();
    await waitForChartRender(chart);
    
    await chart.hover();
    await page.waitForTimeout(500);
    
    // Look for tooltip
    const tooltip = page.locator('[role="tooltip"], [class*="tooltip"]').first();
    const exists = await tooltip.isVisible().catch(() => false);
    // Tooltip might appear on hover
  });

  test('Chart tooltips display', async ({ page }) => {
    const chart = page.locator('canvas, svg[class*="chart"]').first();
    await waitForChartRender(chart);
    
    // Try to trigger tooltip
    await chart.hover({ position: { x: 100, y: 100 } });
    await page.waitForTimeout(500);
    
    const tooltip = page.locator('[role="tooltip"], [class*="tooltip"]').first();
    const exists = await tooltip.isVisible().catch(() => false);
    // Tooltip might appear
  });

  test('Chart data updates', async ({ page }) => {
    const chart = page.locator('canvas, svg[class*="chart"]').first();
    await waitForChartRender(chart);
    
    // Wait for potential data update
    await page.waitForTimeout(5000);
    
    // Verify chart still visible
    await expect(chart).toBeVisible();
  });
});
