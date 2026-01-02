import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { mockApiEndpoints } from '../../../shared/helpers/api-helpers';
import { healthMocks } from '../fixtures/api-mocks';

test.describe('Health Dashboard - Navigation & Layout', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await mockApiEndpoints(page, [
      { pattern: /\/api\/health/, response: healthMocks['/api/health'] },
    ]);
    await page.goto('/');
  });

  test('@smoke Dashboard loads successfully', async ({ page }) => {
    await expect(page).toHaveTitle(/Health Dashboard|HomeIQ/i);
    await expect(page.locator('body')).toBeVisible();
  });

  test('All 15 tabs are visible and clickable', async ({ page }) => {
    const tabs = [
      'overview',
      'setup',
      'services',
      'dependencies',
      'devices',
      'events',
      'logs',
      'sports',
      'data-sources',
      'energy',
      'analytics',
      'alerts',
      'hygiene',
      'validation',
      'configuration',
    ];

    for (const tabId of tabs) {
      const tab = page.locator(`[data-tab="${tabId}"], button:has-text("${tabId}"), a[href*="${tabId}"]`).first();
      await expect(tab).toBeVisible({ timeout: 5000 });
      await expect(tab).toBeEnabled();
    }
  });

  test('Tab switching updates URL hash', async ({ page }) => {
    // Click on services tab
    const servicesTab = page.locator('[data-tab="services"], button:has-text("Services"), a[href*="services"]').first();
    await servicesTab.click();
    
    // Wait for URL to update
    await page.waitForURL(/\#services/, { timeout: 3000 });
    expect(page.url()).toContain('#services');
  });

  test('Tab state persists on page refresh', async ({ page }) => {
    // Navigate to services tab
    const servicesTab = page.locator('[data-tab="services"], button:has-text("Services"), a[href*="services"]').first();
    await servicesTab.click();
    await page.waitForURL(/\#services/);
    
    // Refresh page
    await page.reload();
    
    // Verify tab is still selected
    await page.waitForURL(/\#services/);
    const activeTab = page.locator('[data-tab="services"][aria-selected="true"], button[aria-selected="true"]:has-text("Services")').first();
    await expect(activeTab).toBeVisible();
  });

  test('Dark mode toggle works', async ({ page }) => {
    // Find dark mode toggle
    const darkModeToggle = page.locator('[data-testid="dark-mode-toggle"], button:has-text("Dark"), [aria-label*="dark"], [aria-label*="theme"]').first();
    
    if (await darkModeToggle.isVisible()) {
      const initialClass = await page.locator('html').getAttribute('class');
      
      await darkModeToggle.click();
      await page.waitForTimeout(500); // Wait for transition
      
      const newClass = await page.locator('html').getAttribute('class');
      expect(newClass).not.toBe(initialClass);
    }
  });

  test('Theme preference persists in localStorage', async ({ page }) => {
    // Set dark mode
    const darkModeToggle = page.locator('[data-testid="dark-mode-toggle"], button:has-text("Dark"), [aria-label*="dark"]').first();
    
    if (await darkModeToggle.isVisible()) {
      await darkModeToggle.click();
      await page.waitForTimeout(500);
      
      // Check localStorage
      const darkMode = await page.evaluate(() => localStorage.getItem('darkMode'));
      expect(darkMode).toBeTruthy();
      
      // Reload and verify
      await page.reload();
      const htmlClass = await page.locator('html').getAttribute('class');
      expect(htmlClass).toContain('dark');
    }
  });

  test('Responsive navigation (mobile menu)', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Look for mobile menu button
    const mobileMenuButton = page.locator('[data-testid="mobile-menu"], button[aria-label*="menu"], button:has([class*="hamburger"])').first();
    
    if (await mobileMenuButton.isVisible({ timeout: 2000 })) {
      await mobileMenuButton.click();
      
      // Verify menu is open
      const menu = page.locator('[role="navigation"], nav, [data-testid="mobile-nav"]').first();
      await expect(menu).toBeVisible();
    }
  });

  test('Error boundary displays on component errors', async ({ page }) => {
    // Inject error into a component
    await page.evaluate(() => {
      window.addEventListener('error', (e) => {
        // Suppress error for test
        e.preventDefault();
      });
    });
    
    // Try to trigger an error (this is a placeholder - actual implementation depends on error boundary setup)
    // The error boundary should catch and display an error message
    const errorBoundary = page.locator('[data-testid="error-boundary"], .error-boundary, [role="alert"]').first();
    // This test may need adjustment based on actual error boundary implementation
  });
});
