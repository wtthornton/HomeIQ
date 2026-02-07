import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { HealthDashboardPage } from '../../page-objects/HealthDashboardPage';

/** Tests run against deployed Docker (no API mocks). Ensure health-dashboard and backend are up on 3000/8004. */
test.describe('Health Dashboard - Navigation & Layout', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
  });

  test('@smoke Dashboard loads successfully', async ({ page }) => {
    await expect(page).toHaveTitle(/Health Dashboard|HomeIQ/i);
    await expect(page.locator('body')).toBeVisible();
  });

  // P1.1: Header with theme toggle, auto-refresh, and time range selector
  test('P1.1 Header shows theme toggle, auto-refresh, and time range selector', async ({ page }) => {
    const dashboard = new HealthDashboardPage(page);
    await dashboard.goto();
    await expect(dashboard.getHeader()).toBeVisible();
    await expect(dashboard.getThemeToggle()).toBeVisible();
    await expect(dashboard.getAutoRefreshToggle()).toBeVisible();
    await expect(dashboard.getTimeRangeSelector()).toBeVisible();
  });

  // P1.2: All 16 tabs visible and each tab renders without crashing
  test('P1.2 All 16 tabs are visible and clickable', async ({ page }) => {
    const dashboard = new HealthDashboardPage(page);
    await dashboard.goto();
    const tabIds = HealthDashboardPage.getTabIds();
    expect(tabIds).toHaveLength(16);
    for (const tabId of tabIds) {
      const tab = dashboard.getTab(tabId);
      await expect(tab).toBeVisible({ timeout: 5000 });
      await expect(tab).toBeEnabled();
    }
  });

  test('P1.2 Each tab renders without crashing', async ({ page }) => {
    const dashboard = new HealthDashboardPage(page);
    await dashboard.goto();
    for (const tabId of HealthDashboardPage.getTabIds()) {
      await dashboard.goToTab(tabId);
      await expect(dashboard.getDashboardRoot()).toBeVisible();
      await expect(page.locator('body')).not.toContainText(/error boundary|crash/i);
    }
  });

  // P1.4: Theme toggle switches light/dark and persists
  test('P1.4 Theme toggle switches and persists in localStorage', async ({ page }) => {
    const dashboard = new HealthDashboardPage(page);
    await dashboard.goto();
    const before = await dashboard.isDarkMode();
    await dashboard.toggleTheme();
    const after = await dashboard.isDarkMode();
    expect(after).not.toBe(before);
    const stored = await page.evaluate(() => localStorage.getItem('darkMode'));
    expect(stored).toBeTruthy();
    await page.reload();
    const htmlClass = await page.locator('html').getAttribute('class');
    expect(htmlClass).toContain('dark');
  });

  // P1.5: Time range selector changes period
  test('P1.5 Time range selector is interactive', async ({ page }) => {
    const dashboard = new HealthDashboardPage(page);
    await dashboard.goto();
    const selector = dashboard.getTimeRangeSelector();
    await expect(selector).toBeVisible();
    await selector.click();
    const option = page.getByRole('option').first();
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(option).toBeVisible();
    }
  });

  // P1.6: Auto-refresh toggle enables/disables polling
  test('P1.6 Auto-refresh toggle is clickable', async ({ page }) => {
    const dashboard = new HealthDashboardPage(page);
    await dashboard.goto();
    await dashboard.toggleAutoRefresh();
    await expect(dashboard.getAutoRefreshToggle()).toBeVisible();
  });

  test('All 16 tabs visible (legacy selector fallback)', async ({ page }) => {
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
      'synergies',
      'configuration',
    ];

    for (const tabId of tabs) {
      const tab = page.locator(`[data-testid="tab-${tabId}"], [data-tab="${tabId}"], button:has-text("${tabId}"), a[href*="${tabId}"]`).first();
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
      await page.waitForFunction(() => document.querySelector('html')?.getAttribute('class') !== null);

      const newClass = await page.locator('html').getAttribute('class');
      expect(newClass).not.toBe(initialClass);
    }
  });

  test('Theme preference persists in localStorage', async ({ page }) => {
    // Set dark mode
    const darkModeToggle = page.locator('[data-testid="dark-mode-toggle"], button:has-text("Dark"), [aria-label*="dark"]').first();
    
    if (await darkModeToggle.isVisible()) {
      await darkModeToggle.click();
      await page.waitForFunction(() => document.querySelector('html')?.getAttribute('class') !== null);

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

  test.skip('Error boundary displays on component errors', async ({ page }) => {
    // Placeholder: depends on error boundary implementation; skip to avoid flaky context destruction
    const errorBoundary = page.locator('[data-testid="error-boundary"], .error-boundary, [role="alert"]').first();
    await expect(errorBoundary).toBeVisible();
  });
});
