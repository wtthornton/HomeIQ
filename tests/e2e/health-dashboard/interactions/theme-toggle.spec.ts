import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';

test.describe('Health Dashboard - Theme Toggle Interaction', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
  });

  test('Light/dark mode switching', async ({ page }) => {
    const darkModeToggle = page.getByTestId('theme-toggle').or(page.locator('[data-testid="dark-mode-toggle"], button[aria-label*="dark"]')).first();
    
    if (await darkModeToggle.isVisible({ timeout: 2000 })) {
      const initialClass = await page.locator('html').getAttribute('class');
      
      await darkModeToggle.click();
      await page.waitForTimeout(500);
      
      const newClass = await page.locator('html').getAttribute('class');
      expect(newClass).not.toBe(initialClass);
      
      // Toggle back
      await darkModeToggle.click();
      await page.waitForTimeout(500);
      
      const finalClass = await page.locator('html').getAttribute('class');
      expect(finalClass).toBe(initialClass);
    }
  });

  test('Theme preference persists', async ({ page }) => {
    const darkModeToggle = page.getByTestId('theme-toggle').or(page.locator('[data-testid="dark-mode-toggle"]')).first();
    
    if (await darkModeToggle.isVisible({ timeout: 2000 })) {
      await darkModeToggle.click();
      await page.waitForTimeout(500);
      
      const darkMode = await page.evaluate(() => localStorage.getItem('darkMode'));
      expect(darkMode).toBeTruthy();
      
      await page.reload();
      const htmlClass = await page.locator('html').getAttribute('class');
      expect(htmlClass).toContain('dark');
    }
  });
});
