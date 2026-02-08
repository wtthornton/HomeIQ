import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('Health Dashboard - Tab Switching Interaction', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
    await waitForLoadingComplete(page);
    await expect(page.getByTestId('dashboard-root')).toBeVisible({ timeout: 15000 });
  });

  test('All 16 tabs are switchable', async ({ page }) => {
    const tabIds = ['overview', 'setup', 'services', 'dependencies', 'devices', 'events', 'logs', 'sports', 'data-sources', 'energy', 'analytics', 'alerts', 'hygiene', 'validation', 'synergies', 'configuration'];
    for (const tabId of tabIds) {
      const tab = page.getByTestId(`tab-${tabId}`);
      await expect(tab).toBeVisible({ timeout: 5000 });
      await tab.scrollIntoViewIfNeeded();
      await tab.click();
      await page.waitForTimeout(400);
      await expect(tab).toHaveAttribute('aria-selected', 'true');
    }
  });

  test('Keyboard navigation works', async ({ page }) => {
    const servicesTab = page.getByTestId('tab-services');
    await servicesTab.click();
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(300);
    const depsTab = page.getByTestId('tab-dependencies');
    await expect(depsTab).toHaveAttribute('aria-selected', 'true');
  });

  test('Tab state updates URL', async ({ page }) => {
    const servicesTab = page.getByTestId('tab-services');
    await servicesTab.click();
    await page.waitForURL(/#services/, { timeout: 5000 });
    expect(page.url()).toContain('#services');
  });
});
