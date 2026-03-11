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

/** Analytics uses MiniChart: SVG with role="img" and aria-label containing "chart". */
const CHART_SELECTOR = '[role="img"][aria-label*="chart" i]';

test.describe('Charts -- operator trend visualization', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await navigateToAnalytics(page);
  });

  test('charts render with visible content so the operator can read trends', async ({ page }) => {
    // Analytics tab uses SVG charts (MiniChart) with role="img" and aria-label like "Events Per Minute chart".
    // If the panel shows loading/error/no data, skip or wait for at least one chart.
    const charts = page.locator(CHART_SELECTOR);
    await expect(charts.first()).toBeVisible({ timeout: 15000 });

    const chartBox = await charts.first().boundingBox();
    expect(chartBox).not.toBeNull();
    expect(chartBox!.width).toBeGreaterThan(50);
    expect(chartBox!.height).toBeGreaterThan(30);
  });

  test('hovering a chart does not crash the page', async ({ page }) => {
    const chart = page.locator(CHART_SELECTOR).first();
    await expect(chart).toBeVisible({ timeout: 15000 });

    const box = await chart.boundingBox();
    expect(box).not.toBeNull();

    await chart.hover({ position: { x: Math.floor(box!.width / 2), y: Math.floor(box!.height / 2) } });
    await new Promise((r) => setTimeout(r, 600));

    const tooltip = page.locator('[role="tooltip"], [class*="tooltip"], [class*="Tooltip"]').first();
    const tooltipVisible = await tooltip.isVisible().catch(() => false);
    if (tooltipVisible) {
      const tooltipText = await tooltip.textContent();
      expect(tooltipText?.trim().length).toBeGreaterThan(0);
    }
    await expect(chart).toBeVisible();
  });

  test('chart remains stable after data refresh cycle', async ({ page }) => {
    const chart = page.locator(CHART_SELECTOR).first();
    await expect(chart).toBeVisible({ timeout: 15000 });

    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    await new Promise(r => setTimeout(r, 6000));

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
    await new Promise((r) => setTimeout(r, 3000));

    // Filter out known benign errors to focus on real issues
    const significantErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('404') && !e.includes('429') && !e.includes('VITE_API_KEY')
        && !e.includes('Failed to load resource') && !e.includes('API Error') && !e.includes('Backend un')
        && !e.includes('Failed to fetch') && !e.includes('Error fetching')
    );
    expect(significantErrors).toHaveLength(0);
  });
});
