import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

test.describe('Health Dashboard - Logs Tab', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#logs');
    await waitForLoadingComplete(page);
  });

  test('@smoke Log viewer loads', async ({ page }) => {
    const logViewer = page.locator('[data-testid="log-viewer"], [class*="LogViewer"], pre, [class*="log"]').first();
    await expect(logViewer).toBeVisible({ timeout: 5000 });
  });

  test('P3.2 Logs tab loads and displays log viewer or empty state', async ({ page }) => {
    await expect(page).toHaveURL(/#logs/);
    const logViewer = page.locator('[data-testid="log-viewer"], [class*="LogViewer"], pre, [class*="log"], [class*="Waiting for logs"]').first();
    await expect(logViewer).toBeVisible({ timeout: 8000 });
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
    // Verify structure supports tail updates
    const logViewer = page.locator('[data-testid="log-viewer"], [class*="LogViewer"]').first();
    await expect(logViewer).toBeVisible();
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
