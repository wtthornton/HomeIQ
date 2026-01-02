import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';

test.describe('Health Dashboard - Tab Switching Interaction', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
  });

  test('All tabs are switchable', async ({ page }) => {
    const tabs = ['overview', 'services', 'devices', 'events', 'analytics'];
    
    for (const tabId of tabs) {
      const tab = page.locator(`[data-tab="${tabId}"], button:has-text("${tabId}"), a[href*="${tabId}"]`).first();
      await tab.click();
      await page.waitForTimeout(500);
      await expect(tab).toBeVisible();
    }
  });

  test('Keyboard navigation works', async ({ page }) => {
    // Tab through navigation
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);
    
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
    
    // Use arrow keys if supported
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(200);
  });

  test('Tab state updates URL', async ({ page }) => {
    const servicesTab = page.locator('[data-tab="services"], button:has-text("Services")').first();
    await servicesTab.click();
    await page.waitForURL(/\#services/);
    expect(page.url()).toContain('#services');
  });
});
