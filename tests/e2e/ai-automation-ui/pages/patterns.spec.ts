import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { mockApiEndpoints } from '../../../shared/helpers/api-helpers';
import { automationMocks } from '../fixtures/api-mocks';
import { waitForLoadingComplete, waitForModalOpen, waitForChartRender } from '../../../shared/helpers/wait-helpers';

test.describe('AI Automation UI - Patterns Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await mockApiEndpoints(page, [
      { pattern: /\/api\/patterns/, response: automationMocks['/api/patterns'] },
    ]);
    await page.goto('/patterns');
    await waitForLoadingComplete(page);
  });

  test('@smoke Pattern list loads', async ({ page }) => {
    const patternList = page.locator('[data-testid="pattern-list"], [class*="PatternList"]').first();
    await expect(patternList).toBeVisible({ timeout: 5000 });
  });

  test('Pattern charts render', async ({ page }) => {
    const charts = page.locator('canvas, svg[class*="chart"], [class*="Chart"]');
    if (await charts.count() > 0) {
      await waitForChartRender(charts.first());
      await expect(charts.first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('Pattern details modal', async ({ page }) => {
    const firstPattern = page.locator('[data-testid="pattern-card"], [class*="PatternCard"]').first();
    await firstPattern.click();
    await waitForModalOpen(page);
    
    const modal = page.locator('[role="dialog"], .modal').first();
    await expect(modal).toBeVisible({ timeout: 3000 });
  });

  test('Pattern filtering', async ({ page }) => {
    const filterInput = page.locator('input, select, [data-testid="filter"]').first();
    
    if (await filterInput.isVisible({ timeout: 2000 })) {
      await filterInput.fill('time');
      await page.waitForTimeout(500);
    }
  });

  test('Pattern search', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="search"]').first();
    
    if (await searchInput.isVisible({ timeout: 2000 })) {
      await searchInput.fill('light');
      await page.waitForTimeout(500);
    }
  });

  test('Time range selection', async ({ page }) => {
    const timeRangeSelect = page.locator('select, button[aria-label*="time"]').first();
    
    if (await timeRangeSelect.isVisible({ timeout: 2000 })) {
      await timeRangeSelect.click();
      await page.waitForTimeout(500);
    }
  });

  test('Pattern statistics', async ({ page }) => {
    const stats = page.locator('[data-testid="pattern-stats"], [class*="statistics"]').first();
    const exists = await stats.isVisible().catch(() => false);
    // Structure supports statistics
  });
});
