import { test, expect } from '@playwright/test';

/**
 * Visual Regression Tests
 * Tests UI consistency and visual appearance across different browsers and screen sizes
 */
test.describe('Visual Regression Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Set consistent viewport size for visual tests
    await page.setViewportSize({ width: 1280, height: 720 });
  });

  test('Dashboard screen visual consistency', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Wait for dashboard to fully load
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
    await page.waitForTimeout(2000); // Allow for animations to complete
    
    // Take full page screenshot
    await expect(page).toHaveScreenshot('dashboard-full.png');
    
    // Take screenshot of header section
    const header = page.locator('[data-testid="dashboard-header"]');
    await expect(header).toHaveScreenshot('dashboard-header.png');
    
    // Take screenshot of health cards section
    const healthCards = page.locator('[data-testid="health-cards"]');
    await expect(healthCards).toHaveScreenshot('dashboard-health-cards.png');
    
    // Take screenshot of statistics chart
    const statisticsChart = page.locator('[data-testid="statistics-chart"]');
    await expect(statisticsChart).toHaveScreenshot('dashboard-statistics-chart.png');
    
    // Take screenshot of events feed
    const eventsFeed = page.locator('[data-testid="events-feed"]');
    await expect(eventsFeed).toHaveScreenshot('dashboard-events-feed.png');
  });

  test('Monitoring screen visual consistency', async ({ page }) => {
    await page.goto('http://localhost:3000/monitoring');
    await page.waitForLoadState('networkidle');
    
    // Wait for monitoring screen to fully load
    await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 15000 });
    await page.waitForTimeout(2000);
    
    // Take full page screenshot
    await expect(page).toHaveScreenshot('monitoring-full.png');
    
    // Take screenshot of service monitoring section
    const serviceMonitoring = page.locator('[data-testid="service-monitoring"]');
    await expect(serviceMonitoring).toHaveScreenshot('monitoring-services.png');
    
    // Take screenshot of performance metrics
    const performanceMetrics = page.locator('[data-testid="performance-metrics"]');
    await expect(performanceMetrics).toHaveScreenshot('monitoring-performance.png');
    
    // Take screenshot of alert management
    const alertManagement = page.locator('[data-testid="alert-management"]');
    await expect(alertManagement).toHaveScreenshot('monitoring-alerts.png');
  });

  test('Settings screen visual consistency', async ({ page }) => {
    await page.goto('http://localhost:3000/settings');
    await page.waitForLoadState('networkidle');
    
    // Wait for settings screen to fully load
    await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 15000 });
    await page.waitForTimeout(2000);
    
    // Take full page screenshot
    await expect(page).toHaveScreenshot('settings-full.png');
    
    // Take screenshot of settings navigation
    const settingsNav = page.locator('[data-testid="settings-navigation"]');
    await expect(settingsNav).toHaveScreenshot('settings-navigation.png');
    
    // Test each settings tab visually
    const tabs = ['general', 'api-config', 'notifications', 'data-retention', 'security'];
    
    for (const tab of tabs) {
      await page.click(`[data-testid="settings-tab-${tab}"]`);
      await page.waitForTimeout(1000);
      
      const tabContent = page.locator(`[data-testid="settings-content-${tab}"]`);
      await expect(tabContent).toHaveScreenshot(`settings-${tab}.png`);
    }
  });

  test('Navigation component visual consistency', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Wait for navigation to load
    await page.waitForSelector('[data-testid="navigation"]');
    
    // Take screenshot of navigation
    const navigation = page.locator('[data-testid="navigation"]');
    await expect(navigation).toHaveScreenshot('navigation.png');
    
    // Test navigation hover states
    const dashboardNav = page.locator('[data-testid="nav-dashboard"]');
    await dashboardNav.hover();
    await expect(navigation).toHaveScreenshot('navigation-dashboard-hover.png');
    
    const monitoringNav = page.locator('[data-testid="nav-monitoring"]');
    await monitoringNav.hover();
    await expect(navigation).toHaveScreenshot('navigation-monitoring-hover.png');
    
    const settingsNav = page.locator('[data-testid="nav-settings"]');
    await settingsNav.hover();
    await expect(navigation).toHaveScreenshot('navigation-settings-hover.png');
  });

  test('Health cards visual consistency', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Wait for health cards to load
    await page.waitForSelector('[data-testid="health-card"]', { timeout: 15000 });
    
    // Take individual health card screenshots
    const healthCards = page.locator('[data-testid="health-card"]');
    const cardCount = await healthCards.count();
    
    for (let i = 0; i < Math.min(cardCount, 5); i++) {
      const card = healthCards.nth(i);
      const serviceName = await card.locator('[data-testid="service-name"]').textContent();
      const sanitizedName = serviceName?.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') || `card-${i}`;
      
      await expect(card).toHaveScreenshot(`health-card-${sanitizedName}.png`);
    }
    
    // Test health card hover states
    const firstCard = healthCards.first();
    await firstCard.hover();
    await expect(firstCard).toHaveScreenshot('health-card-hover.png');
  });

  test('Mobile responsive design visual consistency', async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Wait for mobile dashboard to load
    await page.waitForSelector('[data-testid="mobile-dashboard"]', { timeout: 15000 });
    await page.waitForTimeout(2000);
    
    // Take mobile dashboard screenshot
    await expect(page).toHaveScreenshot('mobile-dashboard.png');
    
    // Test mobile navigation
    const mobileMenuButton = page.locator('[data-testid="mobile-menu-button"]');
    if (await mobileMenuButton.isVisible()) {
      await mobileMenuButton.click();
      await page.waitForTimeout(1000);
      await expect(page).toHaveScreenshot('mobile-navigation-menu.png');
    }
    
    // Test mobile monitoring screen
    await page.goto('http://localhost:3000/monitoring');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await expect(page).toHaveScreenshot('mobile-monitoring.png');
    
    // Test mobile settings screen
    await page.goto('http://localhost:3000/settings');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await expect(page).toHaveScreenshot('mobile-settings.png');
  });

  test('Tablet responsive design visual consistency', async ({ page }) => {
    // Test tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Wait for dashboard to load
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
    await page.waitForTimeout(2000);
    
    // Take tablet dashboard screenshot
    await expect(page).toHaveScreenshot('tablet-dashboard.png');
    
    // Test tablet monitoring screen
    await page.goto('http://localhost:3000/monitoring');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await expect(page).toHaveScreenshot('tablet-monitoring.png');
  });

  test('Dark theme visual consistency', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Switch to dark theme
    const themeToggle = page.locator('[data-testid="theme-toggle"]');
    await themeToggle.click();
    await page.waitForTimeout(2000);
    
    // Take dark theme screenshots
    await expect(page).toHaveScreenshot('dark-theme-dashboard.png');
    
    // Test dark theme on monitoring screen
    await page.goto('http://localhost:3000/monitoring');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await expect(page).toHaveScreenshot('dark-theme-monitoring.png');
    
    // Test dark theme on settings screen
    await page.goto('http://localhost:3000/settings');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await expect(page).toHaveScreenshot('dark-theme-settings.png');
  });

  test('Loading states visual consistency', async ({ page }) => {
    // Test loading states by intercepting API calls
    await page.route('**/api/v1/health', route => {
      // Delay response to show loading state
      setTimeout(() => route.continue(), 2000);
    });
    
    await page.goto('http://localhost:3000');
    
    // Wait for loading state to appear
    await page.waitForSelector('[data-testid="loading-skeleton"]', { timeout: 5000 });
    
    // Take screenshot of loading state
    await expect(page).toHaveScreenshot('loading-state.png');
    
    // Wait for loading to complete
    await page.waitForTimeout(3000);
    
    // Take screenshot after loading completes
    await expect(page).toHaveScreenshot('loaded-state.png');
  });

  test('Error states visual consistency', async ({ page }) => {
    // Simulate error state
    await page.route('**/api/v1/health', route => route.abort());
    
    await page.goto('http://localhost:3000');
    
    // Wait for error state to appear
    await page.waitForSelector('[data-testid="error-state"]', { timeout: 10000 });
    
    // Take screenshot of error state
    await expect(page).toHaveScreenshot('error-state.png');
    
    // Take screenshot of error message
    const errorMessage = page.locator('[data-testid="error-message"]');
    await expect(errorMessage).toHaveScreenshot('error-message.png');
  });

  test('Modal dialogs visual consistency', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Open settings modal (if available)
    const settingsButton = page.locator('[data-testid="open-settings-modal"]');
    if (await settingsButton.isVisible()) {
      await settingsButton.click();
      
      // Wait for modal to open
      await page.waitForSelector('[data-testid="settings-modal"]');
      
      // Take modal screenshot
      const modal = page.locator('[data-testid="settings-modal"]');
      await expect(modal).toHaveScreenshot('settings-modal.png');
      
      // Close modal
      await page.click('[data-testid="close-modal"]');
    }
    
    // Test export dialog
    const exportButton = page.locator('[data-testid="export-button"]');
    if (await exportButton.isVisible()) {
      await exportButton.click();
      
      // Wait for export dialog
      await page.waitForSelector('[data-testid="export-dialog"]');
      
      // Take export dialog screenshot
      const exportDialog = page.locator('[data-testid="export-dialog"]');
      await expect(exportDialog).toHaveScreenshot('export-dialog.png');
    }
  });

  test('Form elements visual consistency', async ({ page }) => {
    await page.goto('http://localhost:3000/settings');
    await page.waitForLoadState('networkidle');
    
    // Navigate to API configuration
    await page.click('[data-testid="settings-tab-api-config"]');
    await page.waitForSelector('[data-testid="settings-content-api-config"]');
    
    // Take screenshot of form elements
    const formSection = page.locator('[data-testid="settings-content-api-config"]');
    await expect(formSection).toHaveScreenshot('form-elements.png');
    
    // Test form input focus states
    const firstInput = page.locator('input').first();
    await firstInput.focus();
    await expect(formSection).toHaveScreenshot('form-input-focused.png');
    
    // Test form validation states
    const invalidInput = page.locator('[data-testid="ha-url-input"]');
    await invalidInput.fill('invalid-url');
    await invalidInput.blur();
    await expect(formSection).toHaveScreenshot('form-validation-error.png');
  });

  test('Chart components visual consistency', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Wait for chart to load
    await page.waitForSelector('[data-testid="statistics-chart"]', { timeout: 15000 });
    
    // Take screenshot of chart
    const chart = page.locator('[data-testid="statistics-chart"]');
    await expect(chart).toHaveScreenshot('chart-default.png');
    
    // Test chart toolbar interactions
    const chartToolbar = page.locator('[data-testid="chart-toolbar"]');
    if (await chartToolbar.isVisible()) {
      // Test zoom in
      const zoomInButton = page.locator('[data-testid="zoom-in"]');
      if (await zoomInButton.isVisible()) {
        await zoomInButton.click();
        await page.waitForTimeout(1000);
        await expect(chart).toHaveScreenshot('chart-zoomed-in.png');
      }
      
      // Test zoom out
      const zoomOutButton = page.locator('[data-testid="zoom-out"]');
      if (await zoomOutButton.isVisible()) {
        await zoomOutButton.click();
        await page.waitForTimeout(1000);
        await expect(chart).toHaveScreenshot('chart-zoomed-out.png');
      }
    }
  });
});
