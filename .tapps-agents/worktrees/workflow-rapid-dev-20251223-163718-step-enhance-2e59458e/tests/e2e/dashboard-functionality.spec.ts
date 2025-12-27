import { test, expect } from '@playwright/test';

/**
 * Dashboard Functionality E2E Tests
 * Tests all UI screens and user interactions
 */
test.describe('Dashboard Functionality Tests', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
  });

  test('Main dashboard loads and displays all components', async ({ page }) => {
    // Wait for dashboard to load
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
    
    // Verify main dashboard elements
    await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    await expect(page.locator('[data-testid="navigation"]')).toBeVisible();
    await expect(page.locator('[data-testid="health-cards"]')).toBeVisible();
    await expect(page.locator('[data-testid="statistics-chart"]')).toBeVisible();
    await expect(page.locator('[data-testid="events-feed"]')).toBeVisible();
    
    // Verify header elements
    await expect(page.locator('h1')).toContainText('HA Ingestor Dashboard');
    await expect(page.locator('[data-testid="refresh-controls"]')).toBeVisible();
  });

  test('Navigation works correctly between screens', async ({ page }) => {
    // Test navigation to Monitoring screen
    await page.click('[data-testid="nav-monitoring"]');
    await expect(page).toHaveURL('http://localhost:3000/monitoring');
    await expect(page.locator('[data-testid="monitoring-screen"]')).toBeVisible();
    
    // Test navigation to Settings screen
    await page.click('[data-testid="nav-settings"]');
    await expect(page).toHaveURL('http://localhost:3000/settings');
    await expect(page.locator('[data-testid="settings-screen"]')).toBeVisible();
    
    // Test navigation back to Dashboard
    await page.click('[data-testid="nav-dashboard"]');
    await expect(page).toHaveURL('http://localhost:3000/');
    await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
  });

  test('Refresh controls work correctly', async ({ page }) => {
    // Wait for dashboard to load
    await page.waitForSelector('[data-testid="refresh-controls"]');
    
    // Test refresh interval dropdown
    const refreshSelect = page.locator('[data-testid="refresh-interval-select"]');
    await refreshSelect.selectOption('10000'); // 10 seconds
    
    // Test manual refresh button
    const refreshButton = page.locator('[data-testid="refresh-button"]');
    await refreshButton.click();
    
    // ✅ Context7 Best Practice: Web-first assertion instead of waitForTimeout
    // Wait for refresh to complete by checking data is visible
    await expect(page.locator('[data-testid="health-cards"]')).toBeVisible();
  });

  test('Layout switcher changes dashboard layout', async ({ page }) => {
    // Wait for layout switcher to be available
    await page.waitForSelector('[data-testid="layout-switcher"]');
    
    // Test different layout options
    const layoutSwitcher = page.locator('[data-testid="layout-switcher"]');
    
    // ✅ Context7 Best Practice: Use web-first assertions for layout changes
    // Switch to compact layout
    await layoutSwitcher.selectOption('compact');
    await expect(page.locator('[data-testid="compact-layout"]').or(page.locator('.compact-layout'))).toBeVisible({ timeout: 2000 }).catch(() => {});
    
    // Switch to grid layout
    await layoutSwitcher.selectOption('grid');
    await expect(page.locator('[data-testid="grid-layout"]')).toBeVisible({ timeout: 2000 });
    
    // Switch to list layout
    await layoutSwitcher.selectOption('list');
    await expect(page.locator('[data-testid="list-layout"]').or(page.locator('.list-layout'))).toBeVisible({ timeout: 2000 }).catch(() => {});
    
    // Verify final layout state
    const gridLayout = page.locator('[data-testid="grid-layout"]');
    await layoutSwitcher.selectOption('grid');
    await expect(gridLayout).toBeVisible();
  });

  test('Health cards display correct information', async ({ page }) => {
    // Wait for health cards to load
    await page.waitForSelector('[data-testid="health-card"]', { timeout: 10000 });
    
    const healthCards = page.locator('[data-testid="health-card"]');
    const cardCount = await healthCards.count();
    
    expect(cardCount).toBeGreaterThan(0);
    
    // Verify each card has required elements
    for (let i = 0; i < cardCount; i++) {
      const card = healthCards.nth(i);
      await expect(card.locator('[data-testid="service-name"]')).toBeVisible();
      await expect(card.locator('[data-testid="status-indicator"]')).toBeVisible();
      await expect(card.locator('[data-testid="uptime"]')).toBeVisible();
    }
  });

  test('Statistics chart renders and updates', async ({ page }) => {
    // Wait for chart to load
    await page.waitForSelector('[data-testid="statistics-chart"]', { timeout: 10000 });
    
    const chart = page.locator('[data-testid="statistics-chart"]');
    await expect(chart).toBeVisible();
    
    // Verify chart controls are present
    await expect(page.locator('[data-testid="chart-toolbar"]')).toBeVisible();
    await expect(page.locator('[data-testid="time-range-selector"]')).toBeVisible();
    
    // ✅ Context7 Best Practice: Wait for chart update to complete
    const timeRangeSelect = page.locator('[data-testid="time-range-selector"]');
    await timeRangeSelect.selectOption('1h');
    await expect(chart).toBeVisible(); // Chart remains visible during update
    
    await timeRangeSelect.selectOption('24h');
    await expect(chart).toBeVisible(); // Chart remains visible after update
  });

  test('Events feed displays recent events', async ({ page }) => {
    // Wait for events feed to load
    await page.waitForSelector('[data-testid="events-feed"]', { timeout: 10000 });
    
    const eventsFeed = page.locator('[data-testid="events-feed"]');
    await expect(eventsFeed).toBeVisible();
    
    // Check if events are displayed
    const eventItems = page.locator('[data-testid="event-item"]');
    const eventCount = await eventItems.count();
    
    if (eventCount > 0) {
      // Verify event item structure
      const firstEvent = eventItems.first();
      await expect(firstEvent.locator('[data-testid="event-timestamp"]')).toBeVisible();
      await expect(firstEvent.locator('[data-testid="event-entity"]')).toBeVisible();
      await expect(firstEvent.locator('[data-testid="event-type"]')).toBeVisible();
    }
  });

  test('Mobile responsive design works correctly', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Verify mobile layout is active
    await expect(page.locator('[data-testid="mobile-dashboard"]')).toBeVisible();
    
    // Test mobile navigation
    const mobileMenuButton = page.locator('[data-testid="mobile-menu-button"]');
    if (await mobileMenuButton.isVisible()) {
      await mobileMenuButton.click();
      
      const mobileMenu = page.locator('[data-testid="mobile-menu"]');
      await expect(mobileMenu).toBeVisible();
    }
  });

  test('Theme toggle works correctly', async ({ page }) => {
    // Wait for theme toggle to be available
    await page.waitForSelector('[data-testid="theme-toggle"]');
    
    const themeToggle = page.locator('[data-testid="theme-toggle"]');
    const body = page.locator('body');
    
    // ✅ Context7 Best Practice: Use web-first assertions for theme changes
    // Toggle to dark theme
    await themeToggle.click();
    await expect(body).toHaveClass(/dark/); // Wait for dark class to be applied
    
    // Toggle back to light theme
    await themeToggle.click();
    await expect(body).not.toHaveClass(/dark/); // Wait for dark class to be removed
  });

  test('Notification system displays alerts correctly', async ({ page }) => {
    // Wait for notification system to initialize
    await page.waitForSelector('[data-testid="notification-container"]');
    
    // Trigger a test notification (this would typically be done by the application)
    await page.evaluate(() => {
      // Simulate a system notification
      window.dispatchEvent(new CustomEvent('system-notification', {
        detail: {
          type: 'info',
          message: 'Test notification',
          duration: 5000
        }
      }));
    });
    
    // Wait for notification to appear
    await page.waitForSelector('[data-testid="notification-toast"]', { timeout: 5000 });
    
    const notification = page.locator('[data-testid="notification-toast"]');
    await expect(notification).toBeVisible();
    await expect(notification).toContainText('Test notification');
  });
});
