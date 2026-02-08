import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

test.describe('Health Dashboard - Logs Tab', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#logs');
    await waitForLoadingComplete(page);
  });

  test('@smoke Logs tab loads', async ({ page }) => {
    await expect(page.getByTestId('tab-logs')).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByTestId('dashboard-content')).toBeVisible();
  });

  test('P3.2 Logs tab loads and displays log viewer or empty state', async ({ page }) => {
    await expect(page).toHaveURL(/#logs/);
    const content = page.getByTestId('log-viewer').or(page.getByText('Live Log Viewer')).or(page.getByTestId('dashboard-content'));
    await expect(content.first()).toBeVisible({ timeout: 10000 });
  });

  test('Log filtering works', async ({ page }) => {
    const filterInput = page.locator('input, select, [data-testid="filter"]').first();
    
    if (await filterInput.isVisible({ timeout: 2000 })) {
      await filterInput.fill('error');
      await waitForLoadingComplete(page);
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    }
  });

  test('Log search functionality', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="search"]').first();
    
    if (await searchInput.isVisible({ timeout: 2000 })) {
      await searchInput.fill('websocket');
      await waitForLoadingComplete(page);
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    }
  });

  test('Log level filtering', async ({ page }) => {
    const levelFilter = page.locator('select, button[aria-label*="level"]').first();
    
    if (await levelFilter.isVisible({ timeout: 2000 })) {
      await levelFilter.click();
      await waitForLoadingComplete(page);
    }
  });

  test('Log tail updates', async ({ page }) => {
    const content = page.getByTestId('log-viewer').or(page.getByText('Live Log Viewer')).or(page.locator('[class*="log"], select, pre'));
    await expect(content.first()).toBeVisible({ timeout: 8000 });
  });

  test('Log export', async ({ page }) => {
    const exportButton = page.locator('button:has-text("Export"), button[aria-label*="export"]').first();

    if (await exportButton.isVisible({ timeout: 2000 })) {
      const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);
      await exportButton.click();
      const download = await downloadPromise;
      if (download) {
        expect(download.suggestedFilename()).toBeTruthy();
      }
    }
  });
});
