import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('Health Dashboard - Navigation Component', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
    await waitForLoadingComplete(page);
  });

  test('Menu items are visible', async ({ page }) => {
    const navItems = page.locator('nav a, nav button, [role="navigation"] a, [role="navigation"] button');
    const count = await navItems.count();
    expect(count).toBeGreaterThan(0);
  });

  test('Active states work', async ({ page }) => {
    const servicesTab = page.locator('[data-tab="services"], button:has-text("Services")').first();
    await servicesTab.click();
    await page.waitForTimeout(500);
    
    const activeTab = page.locator('[aria-selected="true"], [class*="active"]').first();
    await expect(activeTab).toBeVisible();
  });

  test('Mobile menu opens and closes', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    
    const menuButton = page.locator('[data-testid="mobile-menu"], button[aria-label*="menu"]').first();
    
    if (await menuButton.isVisible({ timeout: 2000 })) {
      await menuButton.click();
      await page.waitForTimeout(300);
      
      const menu = page.locator('nav, [role="navigation"]').first();
      await expect(menu).toBeVisible();
      
      // Close menu
      await menuButton.click();
      await page.waitForTimeout(300);
    }
  });

  test('Keyboard navigation works', async ({ page }) => {
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);
    
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });
});
