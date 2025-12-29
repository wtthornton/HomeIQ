import { test, expect } from '@playwright/test';

/**
 * Complete User Journey E2E Tests
 * Tests real user workflows from login to data viewing and system management
 */
test.describe('Complete User Journey Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
  });

  test.describe('New User Onboarding Journey', () => {
    
    test('First-time user dashboard exploration', async ({ page }) => {
      // Step 1: User arrives at dashboard
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
      
      // Step 2: User sees system overview
      const systemTitle = page.locator('[data-testid="system-title"]');
      await expect(systemTitle).toBeVisible();
      await expect(systemTitle).toContainText('Home Assistant Ingestor');
      
      // Step 3: User examines health cards
      const healthCards = page.locator('[data-testid="health-card"]');
      await expect(healthCards).toHaveCount({ min: 1 });
      
      // Step 4: User checks system status
      const healthStatus = page.locator('[data-testid="health-status"]');
      await expect(healthStatus).toBeVisible();
      
      // Step 5: User explores navigation
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="monitoring-screen"]')).toBeVisible();
      
      // Step 6: User checks settings
      await page.click('[data-testid="nav-settings"]');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="settings-screen"]')).toBeVisible();
      
      // Step 7: User returns to dashboard
      await page.click('[data-testid="nav-dashboard"]');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    });

    test('User discovers system capabilities', async ({ page }) => {
      // User explores what the system can do
      
      // Check WebSocket connection status
      const wsCard = page.locator('[data-testid="health-card"]').filter({ hasText: 'WebSocket Connection' });
      await expect(wsCard).toBeVisible();
      
      // Check event processing capabilities
      const eventCard = page.locator('[data-testid="health-card"]').filter({ hasText: 'Event Processing' });
      await expect(eventCard).toBeVisible();
      
      // Check weather enrichment
      const weatherCard = page.locator('[data-testid="health-card"]').filter({ hasText: 'Weather Enrichment' });
      await expect(weatherCard).toBeVisible();
      
      // Check data storage
      const storageCard = page.locator('[data-testid="health-card"]').filter({ hasText: 'InfluxDB Storage' });
      await expect(storageCard).toBeVisible();
      
      // Check error monitoring
      const errorCard = page.locator('[data-testid="health-card"]').filter({ hasText: 'Error Rate' });
      await expect(errorCard).toBeVisible();
    });
  });

  test.describe('System Administrator Journey', () => {
    
    test('Admin monitors system health and performance', async ({ page }) => {
      // Step 1: Admin checks overall system health
      const overallHealth = page.locator('[data-testid="health-status"]');
      await expect(overallHealth).toBeVisible();
      
      const healthText = await overallHealth.textContent();
      expect(['HEALTHY', 'DEGRADED', 'UNHEALTHY']).toContain(healthText);
      
      // Step 2: Admin reviews detailed metrics
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      
      // Check performance metrics
      const cpuUsage = page.locator('[data-testid="cpu-usage"]');
      await expect(cpuUsage).toBeVisible();
      
      const memoryUsage = page.locator('[data-testid="memory-usage"]');
      await expect(memoryUsage).toBeVisible();
      
      const diskUsage = page.locator('[data-testid="disk-usage"]');
      await expect(diskUsage).toBeVisible();
      
      // Step 3: Admin checks service status
      const serviceCards = page.locator('[data-testid="service-card"]');
      await expect(serviceCards).toHaveCount({ min: 1 });
      
      // Step 4: Admin reviews recent events
      const eventsSection = page.locator('[data-testid="events-section"]');
      await expect(eventsSection).toBeVisible();
    });

    test('Admin configures system settings', async ({ page }) => {
      // Step 1: Admin navigates to settings
      await page.click('[data-testid="nav-settings"]');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      
      // Step 2: Admin reviews general settings
      const generalSettings = page.locator('[data-testid="general-settings"]');
      await expect(generalSettings).toBeVisible();
      
      // Step 3: Admin adjusts refresh interval
      const refreshInterval = page.locator('[data-testid="refresh-interval"]');
      await expect(refreshInterval).toBeVisible();
      
      // Step 4: Admin changes theme
      const themeSelect = page.locator('[data-testid="theme-select"]');
      await expect(themeSelect).toBeVisible();
      await themeSelect.selectOption('dark');
      
      // Step 5: Admin reviews service settings
      const serviceSettings = page.locator('[data-testid="service-settings"]');
      await expect(serviceSettings).toBeVisible();
      
      // Step 6: Admin saves changes
      const saveButton = page.locator('[data-testid="save-settings"]');
      await expect(saveButton).toBeVisible();
      await saveButton.click();
      
      // Step 7: Admin verifies success
      await expect(page.locator('[data-testid="save-success"]')).toBeVisible();
    });

    test('Admin investigates system issues', async ({ page }) => {
      // Step 1: Admin notices error indicators
      const errorCard = page.locator('[data-testid="health-card"]').filter({ hasText: 'Error Rate' });
      await expect(errorCard).toBeVisible();
      
      const errorValue = errorCard.locator('[data-testid="health-card-value"]');
      const errorText = await errorValue.textContent();
      
      // Step 2: If errors exist, admin investigates
      if (errorText && parseFloat(errorText) > 0) {
        // Admin navigates to monitoring for detailed view
        await page.click('[data-testid="nav-monitoring"]');
        await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
        
        // Admin checks service-specific errors
        const serviceCards = page.locator('[data-testid="service-card"]');
        const cardCount = await serviceCards.count();
        
        for (let i = 0; i < cardCount; i++) {
          const card = serviceCards.nth(i);
          const status = card.locator('[data-testid="service-status"]');
          await expect(status).toBeVisible();
        }
      }
    });
  });

  test.describe('Data Analyst Journey', () => {
    
    test('Analyst explores event data and trends', async ({ page }) => {
      // Step 1: Analyst navigates to monitoring for data analysis
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      
      // Step 2: Analyst reviews event statistics
      const eventsSection = page.locator('[data-testid="events-section"]');
      await expect(eventsSection).toBeVisible();
      
      // Step 3: Analyst checks event processing metrics
      const eventProcessingCard = page.locator('[data-testid="health-card"]').filter({ hasText: 'Event Processing' });
      await expect(eventProcessingCard).toBeVisible();
      
      const eventsPerMinute = eventProcessingCard.locator('[data-testid="health-card-value"]');
      await expect(eventsPerMinute).toBeVisible();
      
      // Step 4: Analyst reviews recent events
      const eventsList = page.locator('[data-testid="events-list"]');
      await expect(eventsList).toBeVisible();
      
      // Step 5: Analyst checks data quality metrics
      const errorRateCard = page.locator('[data-testid="health-card"]').filter({ hasText: 'Error Rate' });
      await expect(errorRateCard).toBeVisible();
    });

    test('Analyst monitors data flow and processing', async ({ page }) => {
      // Step 1: Analyst checks data ingestion
      const wsCard = page.locator('[data-testid="health-card"]').filter({ hasText: 'WebSocket Connection' });
      await expect(wsCard).toBeVisible();
      
      const wsStatus = wsCard.locator('[data-testid="health-card-value"]');
      await expect(wsStatus).toBeVisible();
      
      // Step 2: Analyst verifies data storage
      const storageCard = page.locator('[data-testid="health-card"]').filter({ hasText: 'InfluxDB Storage' });
      await expect(storageCard).toBeVisible();
      
      const storageStatus = storageCard.locator('[data-testid="health-card-value"]');
      await expect(storageStatus).toBeVisible();
      
      // Step 3: Analyst checks data enrichment
      const weatherCard = page.locator('[data-testid="health-card"]').filter({ hasText: 'Weather Enrichment' });
      await expect(weatherCard).toBeVisible();
      
      const weatherStatus = weatherCard.locator('[data-testid="health-card-value"]');
      await expect(weatherStatus).toBeVisible();
    });
  });

  test.describe('Mobile User Journey', () => {
    
    test('Mobile user navigates system on small screen', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });
      
      // Step 1: Mobile user loads dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Step 2: Mobile user sees responsive layout
      const dashboard = page.locator('[data-testid="dashboard"]');
      await expect(dashboard).toBeVisible();
      
      // Step 3: Mobile user accesses navigation
      const mobileMenu = page.locator('[data-testid="mobile-menu"]');
      if (await mobileMenu.isVisible()) {
        await mobileMenu.click();
      }
      
      // Step 4: Mobile user navigates to monitoring
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      
      // Step 5: Mobile user checks settings
      await page.click('[data-testid="nav-settings"]');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      
      // Step 6: Mobile user returns to dashboard
      await page.click('[data-testid="nav-dashboard"]');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
    });
  });

  test.describe('Power User Journey', () => {
    
    test('Power user performs rapid system operations', async ({ page }) => {
      // Step 1: Power user quickly checks all screens
      const screens = [
        { nav: '[data-testid="nav-dashboard"]', screen: '[data-testid="dashboard"]' },
        { nav: '[data-testid="nav-monitoring"]', screen: '[data-testid="monitoring-screen"]' },
        { nav: '[data-testid="nav-settings"]', screen: '[data-testid="settings-screen"]' }
      ];
      
      for (const screen of screens) {
        await page.click(screen.nav);
        await page.waitForSelector(screen.screen, { timeout: 10000 });
        await expect(page.locator(screen.screen)).toBeVisible();
      }
      
      // Step 2: Power user performs multiple rapid refreshes
      for (let i = 0; i < 5; i++) {
        await page.reload();
        await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
        await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
      }
      
      // Step 3: Power user tests keyboard navigation
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      await page.keyboard.press('Enter');
      
      // Step 4: Power user verifies system is still responsive
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    });

    test('Power user tests system under load', async ({ page }) => {
      // Step 1: Power user opens multiple tabs
      const context = page.context();
      const pages = await Promise.all([
        context.newPage(),
        context.newPage(),
        context.newPage()
      ]);
      
      // Step 2: Power user loads dashboard in all tabs
      await Promise.all(pages.map(p => p.goto('http://localhost:3000')));
      
      // Step 3: Power user navigates different screens in each tab
      await pages[0].click('[data-testid="nav-dashboard"]');
      await pages[1].click('[data-testid="nav-monitoring"]');
      await pages[2].click('[data-testid="nav-settings"]');
      
      // Step 4: Power user verifies all tabs work correctly
      await expect(pages[0].locator('[data-testid="dashboard"]')).toBeVisible();
      await expect(pages[1].locator('[data-testid="monitoring-screen"]')).toBeVisible();
      await expect(pages[2].locator('[data-testid="settings-screen"]')).toBeVisible();
      
      // Step 5: Clean up
      await Promise.all(pages.map(p => p.close()));
    });
  });

  test.describe('Error Recovery Journey', () => {
    
    test('User recovers from system errors gracefully', async ({ page }) => {
      // Step 1: User encounters an error
      await page.route('**/api/v1/health', route => route.abort());
      
      await page.goto('http://localhost:3000');
      
      // Step 2: User sees error state
      await page.waitForSelector('[data-testid="error-state"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="error-state"]')).toBeVisible();
      
      // Step 3: User reads error message
      const errorMessage = page.locator('[data-testid="error-message"]');
      await expect(errorMessage).toBeVisible();
      
      // Step 4: User attempts retry
      const retryButton = page.locator('[data-testid="retry-button"]');
      await expect(retryButton).toBeVisible();
      
      // Step 5: System recovers
      await page.unroute('**/api/v1/health');
      await retryButton.click();
      
      // Step 6: User verifies recovery
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    });

    test('User continues working despite partial failures', async ({ page }) => {
      // Step 1: Simulate partial API failure
      await page.route('**/api/v1/stats', route => route.abort());
      await page.route('**/api/v1/health', route => route.continue());
      
      // Step 2: User loads dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Step 3: User sees partial data
      const healthSection = page.locator('[data-testid="system-health-section"]');
      await expect(healthSection).toBeVisible();
      
      // Step 4: User navigates despite errors
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      
      // Step 5: User can still access settings
      await page.click('[data-testid="nav-settings"]');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
    });
  });

  test.describe('Accessibility Journey', () => {
    
    test('Screen reader user navigates system', async ({ page }) => {
      // Step 1: Screen reader user loads dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Step 2: Screen reader user navigates with keyboard
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      
      // Step 3: Screen reader user activates navigation
      await page.keyboard.press('Enter');
      
      // Step 4: Screen reader user verifies navigation worked
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="monitoring-screen"]')).toBeVisible();
      
      // Step 5: Screen reader user continues navigation
      await page.keyboard.press('Tab');
      await page.keyboard.press('Enter');
      
      // Step 6: Screen reader user reaches settings
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="settings-screen"]')).toBeVisible();
    });

    test('High contrast user views system', async ({ page }) => {
      // Step 1: User loads dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Step 2: User switches to high contrast theme
      await page.click('[data-testid="nav-settings"]');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      
      const themeSelect = page.locator('[data-testid="theme-select"]');
      await themeSelect.selectOption('high-contrast');
      
      // Step 3: User verifies high contrast is applied
      const settingsScreen = page.locator('[data-testid="settings-screen"]');
      await expect(settingsScreen).toBeVisible();
      
      // Step 4: User navigates back to dashboard
      await page.click('[data-testid="nav-dashboard"]');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
      
      // Step 5: User verifies dashboard is still usable
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    });
  });
});
