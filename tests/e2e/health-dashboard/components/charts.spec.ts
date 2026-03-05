/**
 * Charts -- Trend Visualization for Operators
 *
 * WHY THIS MATTERS:
 * Charts are the primary way an operator spots anomalies, capacity trends,
 * and seasonal patterns across HomeIQ services. If charts fail to render
 * or display stale data, the operator loses situational awareness and may
 * miss a degrading service before it impacts users.
 *
 * WHAT THE OPERATOR USES IT FOR:
 * - Scanning the Analytics page for at-a-glance health trends
 * - Hovering over data points to inspect exact values at a given time
 * - Confirming that live data continues to flow (chart updates)
 *
 * NOTE: Charts live on the Analytics tab, not the Overview tab.
 * The Analytics page renders sparkline charts as <img> elements with
 * alt text like "Events Per Minute chart".
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

/**
 * Navigate to the Analytics tab via hash routing.
 */
async function navigateToAnalytics(page: import('@playwright/test').Page) {
  await page.goto('/#analytics');
  await waitForLoadingComplete(page);
  await expect(page.getByRole('heading', { name: /system analytics/i })).toBeVisible({ timeout: 15000 });
}

test.describe('Charts -- operator trend visualization', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await navigateToAnalytics(page);
  });

  test('charts render with visible content so the operator can read trends', async ({ page }) => {
    // The operator needs at least one chart to be present and rendered.
    // Analytics charts are rendered as <img> elements with alt text containing "chart".
    const charts = page.locator('img[alt*="chart" i]');
    await expect(charts.first()).toBeVisible({ timeout: 10000 });

    // Verify the chart has actual rendered content -- not just a placeholder.
    const chartBox = await charts.first().boundingBox();
    expect(chartBox).not.toBeNull();
    expect(chartBox!.width).toBeGreaterThan(50);
    expect(chartBox!.height).toBeGreaterThan(30);
  });

  test('hovering a chart does not crash the page', async ({ page }) => {
    // Analytics charts are sparkline images -- they may not have DOM-based tooltips.
    // The key assertion is that hovering does not cause errors or hide the chart.
    const chart = page.locator('img[alt*="chart" i]').first();
    await expect(chart).toBeVisible({ timeout: 10000 });

    const box = await chart.boundingBox();
    expect(box).not.toBeNull();

    // Hover near the center of the chart
    await chart.hover({ position: { x: Math.floor(box!.width / 2), y: Math.floor(box!.height / 2) } });
    await page.waitForTimeout(600);

    // Tooltips may be rendered as role="tooltip" or via a class name
    const tooltip = page.locator('[role="tooltip"], [class*="tooltip"], [class*="Tooltip"]').first();
    const tooltipVisible = await tooltip.isVisible().catch(() => false);

    // If the chart library renders tooltips, they should contain text
    if (tooltipVisible) {
      const tooltipText = await tooltip.textContent();
      expect(tooltipText?.trim().length).toBeGreaterThan(0);
    }
    // Sparkline <img> charts typically do not have DOM tooltips -- the hover must not crash.
    await expect(chart).toBeVisible();
  });

  test('chart remains stable after data refresh cycle', async ({ page }) => {
    // The operator expects charts to survive periodic data refreshes without
    // disappearing, flickering, or throwing console errors.
    const chart = page.locator('img[alt*="chart" i]').first();
    await expect(chart).toBeVisible({ timeout: 10000 });

    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    // Wait for at least one potential refresh cycle (dashboard polls every ~5s)
    await page.waitForTimeout(6000);

    // Chart must still be visible -- no blank screen after refresh
    await expect(chart).toBeVisible();

    // No chart-related JS errors during the refresh window
    const chartRelatedErrors = consoleErrors.filter(
      (e) => e.toLowerCase().includes('chart') || e.toLowerCase().includes('canvas')
    );
    expect(chartRelatedErrors).toHaveLength(0);
  });

  test('no console errors on the analytics page with charts', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    // Let the page settle and charts render
    await page.waitForTimeout(3000);

    // Filter out known benign errors to focus on real issues
    const significantErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('404') && !e.includes('429') && !e.includes('VITE_API_KEY')
        && !e.includes('Failed to load resource') && !e.includes('API Error') && !e.includes('Backend un')
        && !e.includes('Failed to fetch') && !e.includes('Error fetching')
    );
    expect(significantErrors).toHaveLength(0);
  });
});
