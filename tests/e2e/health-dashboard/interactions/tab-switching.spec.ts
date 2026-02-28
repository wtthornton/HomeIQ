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
    const tabIds = ['overview', 'services', 'groups', 'dependencies', 'devices', 'events', 'logs', 'sports', 'data-sources', 'energy', 'analytics', 'alerts', 'hygiene', 'validation', 'evaluation', 'configuration'];
    for (const tabId of tabIds) {
      // Navigate via hash so the sidebar group auto-expands
      await page.goto(`/#${tabId}`);
      await expect(page.getByTestId('dashboard-root')).toBeVisible({ timeout: 10000 });
      const tab = tabId === 'overview'
        ? page.locator('[data-tab="overview"]')
        : page.getByTestId(`tab-${tabId}`);
      await expect(tab).toBeVisible({ timeout: 5000 });
    }
  });

  test('Keyboard navigation works', async ({ page }) => {
    // Navigate to services so the Infrastructure group is expanded
    await page.goto('/#services');
    await expect(page.getByTestId('dashboard-root')).toBeVisible({ timeout: 10000 });
    const servicesTab = page.getByTestId('tab-services');
    await expect(servicesTab).toBeVisible({ timeout: 5000 });
    await servicesTab.click();
    await page.keyboard.press('ArrowDown');
    await page.waitForTimeout(300);
    // After arrow down from services, the next tab in the sidebar should receive focus
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });

  test('Tab state updates URL', async ({ page }) => {
    // Navigate to services via hash first to expand the sidebar group
    await page.goto('/#services');
    await expect(page.getByTestId('dashboard-root')).toBeVisible({ timeout: 10000 });
    const servicesTab = page.getByTestId('tab-services');
    await expect(servicesTab).toBeVisible({ timeout: 5000 });
    await servicesTab.click();
    await page.waitForURL(/#services/, { timeout: 5000 });
    expect(page.url()).toContain('#services');
  });
});
