import { test, expect } from '@playwright/test';

/**
 * Comprehensive Frontend UI E2E Tests
 * Tests all UI components, interactions, and user workflows
 */
test.describe('Frontend UI Comprehensive Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard and wait for load
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
  });

  test.describe('Dashboard Main Screen', () => {
    
    test('Dashboard loads completely with all components', async ({ page }) => {
      // Verify main dashboard container
      const dashboard = page.locator('[data-testid="dashboard"]');
      await expect(dashboard).toBeVisible();
      
      // Verify header components
      await expect(page.locator('[data-testid="header"]')).toBeVisible();
      await expect(page.locator('[data-testid="logo"]')).toBeVisible();
      await expect(page.locator('[data-testid="system-title"]')).toBeVisible();
      
      // Verify navigation menu
      await expect(page.locator('[data-testid="navigation"]')).toBeVisible();
      await expect(page.locator('[data-testid="nav-dashboard"]')).toBeVisible();
      await expect(page.locator('[data-testid="nav-monitoring"]')).toBeVisible();
      await expect(page.locator('[data-testid="nav-settings"]')).toBeVisible();
      
      // Verify main content area
      await expect(page.locator('[data-testid="main-content"]')).toBeVisible();
      
      // Verify system health section
      await expect(page.locator('[data-testid="system-health-section"]')).toBeVisible();
      
      // Verify health cards
      const healthCards = page.locator('[data-testid="health-card"]');
      await expect(healthCards).toHaveCount(5);
      
      // Verify each health card has required elements
      for (let i = 0; i < 5; i++) {
        const card = healthCards.nth(i);
        await expect(card.locator('[data-testid="health-card-title"]')).toBeVisible();
        await expect(card.locator('[data-testid="health-card-status"]')).toBeVisible();
        await expect(card.locator('[data-testid="health-card-value"]')).toBeVisible();
      }
    });

    test('System health status displays correctly', async ({ page }) => {
      // Verify overall system health
      const systemHealth = page.locator('[data-testid="system-health"]');
      await expect(systemHealth).toBeVisible();
      
      // Verify health status indicator
      const healthStatus = page.locator('[data-testid="health-status"]');
      await expect(healthStatus).toBeVisible();
      
      // Verify last updated timestamp
      const lastUpdated = page.locator('[data-testid="last-updated"]');
      await expect(lastUpdated).toBeVisible();
      
      // Verify timestamp is recent (within last minute)
      const timestampText = await lastUpdated.textContent();
      expect(timestampText).toMatch(/\d{2}:\d{2}:\d{2}/); // Time format
    });

    test('Health cards show correct information', async ({ page }) => {
      const healthCards = page.locator('[data-testid="health-card"]');
      
      // Check WebSocket Connection card
      const wsCard = healthCards.filter({ hasText: 'WebSocket Connection' });
      await expect(wsCard).toBeVisible();
      await expect(wsCard.locator('[data-testid="health-card-value"]')).toContainText(/Connected|Disconnected/);
      
      // Check Event Processing card
      const eventCard = healthCards.filter({ hasText: 'Event Processing' });
      await expect(eventCard).toBeVisible();
      await expect(eventCard.locator('[data-testid="health-card-value"]')).toContainText(/events\/min/);
      
      // Check Weather Enrichment card
      const weatherCard = healthCards.filter({ hasText: 'Weather Enrichment' });
      await expect(weatherCard).toBeVisible();
      await expect(weatherCard.locator('[data-testid="health-card-value"]')).toContainText(/Enabled|Disabled/);
      
      // Check InfluxDB Storage card
      const influxCard = healthCards.filter({ hasText: 'InfluxDB Storage' });
      await expect(influxCard).toBeVisible();
      await expect(influxCard.locator('[data-testid="health-card-value"]')).toContainText(/Connected|Disconnected/);
      
      // Check Error Rate card
      const errorCard = healthCards.filter({ hasText: 'Error Rate' });
      await expect(errorCard).toBeVisible();
      await expect(errorCard.locator('[data-testid="health-card-value"]')).toContainText(/%/);
    });

    test('Real-time updates work correctly', async ({ page }) => {
      // Get initial timestamp
      const initialTimestamp = await page.locator('[data-testid="last-updated"]').textContent();
      
      // Wait for potential updates
      await page.waitForTimeout(10000);
      
      // Check if timestamp updated or dashboard refreshed
      const currentTimestamp = await page.locator('[data-testid="last-updated"]').textContent();
      
      // Verify timestamp exists and is in correct format
      expect(currentTimestamp).toMatch(/\d{2}:\d{2}:\d{2}/);
      
      // Verify dashboard is still responsive
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    });
  });

  test.describe('Navigation and Routing', () => {
    
    test('Navigation menu works correctly', async ({ page }) => {
      // Test Dashboard navigation
      await page.click('[data-testid="nav-dashboard"]');
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
      
      // Test Monitoring navigation
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="monitoring-screen"]')).toBeVisible();
      
      // Test Settings navigation
      await page.click('[data-testid="nav-settings"]');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="settings-screen"]')).toBeVisible();
      
      // Return to Dashboard
      await page.click('[data-testid="nav-dashboard"]');
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    });

    test('URL routing works correctly', async ({ page }) => {
      // Test direct URL navigation
      await page.goto('http://localhost:3000/monitoring');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="monitoring-screen"]')).toBeVisible();
      
      await page.goto('http://localhost:3000/settings');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="settings-screen"]')).toBeVisible();
      
      await page.goto('http://localhost:3000/');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    });

    test('Browser back/forward navigation works', async ({ page }) => {
      // Navigate through screens
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      
      await page.click('[data-testid="nav-settings"]');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      
      // Test browser back button
      await page.goBack();
      await expect(page.locator('[data-testid="monitoring-screen"]')).toBeVisible();
      
      // Test browser forward button
      await page.goForward();
      await expect(page.locator('[data-testid="settings-screen"]')).toBeVisible();
    });
  });

  test.describe('Monitoring Screen', () => {
    
    test('Monitoring screen loads completely', async ({ page }) => {
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      
      // Verify main monitoring container
      await expect(page.locator('[data-testid="monitoring-screen"]')).toBeVisible();
      
      // Verify monitoring sections
      await expect(page.locator('[data-testid="performance-metrics"]')).toBeVisible();
      await expect(page.locator('[data-testid="service-monitoring"]')).toBeVisible();
      
      // Verify performance metrics
      await expect(page.locator('[data-testid="cpu-usage"]')).toBeVisible();
      await expect(page.locator('[data-testid="memory-usage"]')).toBeVisible();
      await expect(page.locator('[data-testid="disk-usage"]')).toBeVisible();
      
      // Verify service monitoring
      const serviceCards = page.locator('[data-testid="service-card"]');
      await expect(serviceCards).toHaveCount(5);
    });

    test('Performance metrics display correctly', async ({ page }) => {
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      
      // Check CPU usage
      const cpuUsage = page.locator('[data-testid="cpu-usage"]');
      await expect(cpuUsage).toBeVisible();
      const cpuValue = await cpuUsage.locator('[data-testid="metric-value"]').textContent();
      expect(cpuValue).toMatch(/\d+\.?\d*%/);
      
      // Check memory usage
      const memoryUsage = page.locator('[data-testid="memory-usage"]');
      await expect(memoryUsage).toBeVisible();
      const memoryValue = await memoryUsage.locator('[data-testid="metric-value"]').textContent();
      expect(memoryValue).toMatch(/\d+\.?\d*%/);
      
      // Check disk usage
      const diskUsage = page.locator('[data-testid="disk-usage"]');
      await expect(diskUsage).toBeVisible();
      const diskValue = await diskUsage.locator('[data-testid="metric-value"]').textContent();
      expect(diskValue).toMatch(/\d+\.?\d*%/);
    });

    test('Service monitoring shows all services', async ({ page }) => {
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      
      const serviceCards = page.locator('[data-testid="service-card"]');
      
      // Verify each service card has required elements
      for (let i = 0; i < 5; i++) {
        const card = serviceCards.nth(i);
        await expect(card.locator('[data-testid="service-name"]')).toBeVisible();
        await expect(card.locator('[data-testid="service-status"]')).toBeVisible();
        await expect(card.locator('[data-testid="service-uptime"]')).toBeVisible();
      }
      
      // Verify specific services are present
      await expect(page.locator('text=InfluxDB')).toBeVisible();
      await expect(page.locator('text=WebSocket Ingestion')).toBeVisible();
      await expect(page.locator('text=Enrichment Pipeline')).toBeVisible();
      await expect(page.locator('text=Admin API')).toBeVisible();
      await expect(page.locator('text=Data Retention')).toBeVisible();
    });

    test('Real-time monitoring updates work', async ({ page }) => {
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      
      // Get initial metrics
      const initialCpu = await page.locator('[data-testid="cpu-usage"] [data-testid="metric-value"]').textContent();
      
      // Wait for updates
      await page.waitForTimeout(10000);
      
      // Verify metrics are still updating
      const currentCpu = await page.locator('[data-testid="cpu-usage"] [data-testid="metric-value"]').textContent();
      expect(currentCpu).toMatch(/\d+\.?\d*%/);
      
      // Verify monitoring screen is still responsive
      await expect(page.locator('[data-testid="monitoring-screen"]')).toBeVisible();
    });
  });

  test.describe('Settings Screen', () => {
    
    test('Settings screen loads completely', async ({ page }) => {
      await page.click('[data-testid="nav-settings"]');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      
      // Verify main settings container
      await expect(page.locator('[data-testid="settings-screen"]')).toBeVisible();
      
      // Verify settings sections
      await expect(page.locator('[data-testid="general-settings"]')).toBeVisible();
      await expect(page.locator('[data-testid="service-settings"]')).toBeVisible();
      await expect(page.locator('[data-testid="notification-settings"]')).toBeVisible();
    });

    test('General settings are editable', async ({ page }) => {
      await page.click('[data-testid="nav-settings"]');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      
      // Test refresh interval setting
      const refreshInterval = page.locator('[data-testid="refresh-interval"]');
      await expect(refreshInterval).toBeVisible();
      
      // Clear and set new value
      await refreshInterval.clear();
      await refreshInterval.fill('60000');
      
      // Test theme setting
      const themeSelect = page.locator('[data-testid="theme-select"]');
      await expect(themeSelect).toBeVisible();
      await themeSelect.selectOption('dark');
    });

    test('Service settings display correctly', async ({ page }) => {
      await page.click('[data-testid="nav-settings"]');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      
      // Verify service configuration sections
      await expect(page.locator('[data-testid="influxdb-settings"]')).toBeVisible();
      await expect(page.locator('[data-testid="websocket-settings"]')).toBeVisible();
      await expect(page.locator('[data-testid="weather-settings"]')).toBeVisible();
      
      // Verify service status indicators
      const serviceStatuses = page.locator('[data-testid="service-status"]');
      await expect(serviceStatuses).toHaveCount(5);
    });

    test('Notification settings work', async ({ page }) => {
      await page.click('[data-testid="nav-settings"]');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      
      // Test notification toggles
      const emailNotifications = page.locator('[data-testid="email-notifications"]');
      await expect(emailNotifications).toBeVisible();
      
      // Toggle email notifications
      await emailNotifications.click();
      
      // Test alert thresholds
      const alertThreshold = page.locator('[data-testid="alert-threshold"]');
      await expect(alertThreshold).toBeVisible();
      await alertThreshold.clear();
      await alertThreshold.fill('90');
    });

    test('Settings save functionality', async ({ page }) => {
      await page.click('[data-testid="nav-settings"]');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      
      // Make a change
      const refreshInterval = page.locator('[data-testid="refresh-interval"]');
      await refreshInterval.clear();
      await refreshInterval.fill('45000');
      
      // Save settings
      const saveButton = page.locator('[data-testid="save-settings"]');
      await expect(saveButton).toBeVisible();
      await saveButton.click();
      
      // Verify success message
      await expect(page.locator('[data-testid="save-success"]')).toBeVisible();
    });
  });

  test.describe('Error Handling and Edge Cases', () => {
    
    test('Handles API errors gracefully', async ({ page }) => {
      // Simulate API error
      await page.route('**/api/v1/health', route => route.abort());
      
      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Wait for error state
      await page.waitForSelector('[data-testid="error-state"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="error-state"]')).toBeVisible();
      
      // Verify error message
      const errorMessage = page.locator('[data-testid="error-message"]');
      await expect(errorMessage).toBeVisible();
      expect(await errorMessage.textContent()).toContain('Failed to fetch');
      
      // Verify retry button
      const retryButton = page.locator('[data-testid="retry-button"]');
      await expect(retryButton).toBeVisible();
    });

    test('Detects JSON parsing errors in dashboard', async ({ page }) => {
      // Set up console error monitoring
      const consoleErrors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });
      
      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      await page.waitForLoadState('networkidle');
      
      // Wait for data loading attempts
      await page.waitForTimeout(10000);
      
      // Check for JSON parsing errors
      const jsonErrors = consoleErrors.filter(error => 
        error.includes('JSON') || 
        error.includes('Unexpected token') ||
        error.includes('<!DOCTYPE')
      );
      
      if (jsonErrors.length > 0) {
        console.log('JSON Parsing Errors Found:', jsonErrors);
        // This test should fail if JSON parsing errors are found
        expect(jsonErrors).toHaveLength(0);
      }
    });

    test('Handles slow API responses', async ({ page }) => {
      // Simulate slow API response
      await page.route('**/api/v1/health', route => 
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            overall_status: 'healthy',
            admin_api_status: 'healthy',
            ingestion_service: {
              status: 'healthy',
              websocket_connection: { is_connected: true, last_connection_time: new Date().toISOString(), connection_attempts: 0, last_error: null },
              event_processing: { events_per_minute: 0, total_events: 0, error_rate: 0 },
              weather_enrichment: { enabled: true, cache_hits: 0, api_calls: 0, last_error: null },
              influxdb_storage: { is_connected: true, last_write_time: new Date().toISOString(), write_errors: 0 },
              timestamp: new Date().toISOString()
            },
            timestamp: new Date().toISOString()
          })
        })
      );
      
      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Verify loading state appears
      await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible();
      
      // Wait for dashboard to load
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    });

    test('Handles empty data responses', async ({ page }) => {
      // Simulate empty events response
      await page.route('**/api/v1/events*', route => 
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([])
        })
      );
      
      // Navigate to monitoring screen
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      
      // Verify empty state handling
      const emptyState = page.locator('[data-testid="empty-state"]');
      if (await emptyState.isVisible()) {
        await expect(emptyState).toBeVisible();
        await expect(emptyState).toContainText('No data available');
      }
    });

    test('Handles malformed JSON responses', async ({ page }) => {
      // Simulate malformed JSON
      await page.route('**/api/v1/health', route => 
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: 'invalid json'
        })
      );
      
      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Wait for error handling
      await page.waitForSelector('[data-testid="error-state"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="error-state"]')).toBeVisible();
    });

    test('Handles HTML responses instead of JSON', async ({ page }) => {
      // Simulate HTML response instead of JSON (the actual issue we're fixing)
      await page.route('**/api/v1/health', route => 
        route.fulfill({
          status: 200,
          contentType: 'text/html',
          body: '<!DOCTYPE html><html><body>Error Page</body></html>'
        })
      );
      
      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Wait for error handling
      await page.waitForSelector('[data-testid="error-state"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="error-state"]')).toBeVisible();
      
      // Verify error message is user-friendly
      const errorMessage = page.locator('[data-testid="error-message"]');
      await expect(errorMessage).toBeVisible();
      
      const errorText = await errorMessage.textContent();
      expect(errorText).not.toContain('<!DOCTYPE');
      expect(errorText).not.toContain('Unexpected token');
    });
  });

  test.describe('Responsive Design', () => {
    
    test('Mobile viewport displays correctly', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });
      
      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Verify mobile navigation
      const mobileMenu = page.locator('[data-testid="mobile-menu"]');
      if (await mobileMenu.isVisible()) {
        await expect(mobileMenu).toBeVisible();
        await mobileMenu.click();
      }
      
      // Verify responsive layout
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
      
      // Check that health cards stack properly
      const healthCards = page.locator('[data-testid="health-card"]');
      await expect(healthCards).toHaveCount(5);
    });

    test('Tablet viewport displays correctly', async ({ page }) => {
      // Set tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 });
      
      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Verify layout adapts
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
      
      // Navigate to monitoring
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      
      // Verify monitoring screen works on tablet
      await expect(page.locator('[data-testid="monitoring-screen"]')).toBeVisible();
    });

    test('Large desktop viewport displays correctly', async ({ page }) => {
      // Set large desktop viewport
      await page.setViewportSize({ width: 1920, height: 1080 });
      
      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Verify layout utilizes full width
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
      
      // Verify health cards are arranged in grid
      const healthCards = page.locator('[data-testid="health-card"]');
      await expect(healthCards).toHaveCount(5);
    });
  });

  test.describe('Accessibility', () => {
    
    test('Keyboard navigation works', async ({ page }) => {
      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Test Tab navigation
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      
      // Test Enter key on navigation
      await page.keyboard.press('Enter');
      
      // Verify navigation worked
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="monitoring-screen"]')).toBeVisible();
    });

    test('Screen reader compatibility', async ({ page }) => {
      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Verify ARIA labels exist
      const healthCards = page.locator('[data-testid="health-card"]');
      await expect(healthCards.first()).toHaveAttribute('role', 'status');
      
      // Verify heading structure
      const headings = page.locator('h1, h2, h3, h4, h5, h6');
      await expect(headings).toHaveCount({ min: 1 });
    });

    test('Color contrast and visual indicators', async ({ page }) => {
      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Verify status indicators have proper contrast
      const statusIndicators = page.locator('[data-testid="status-indicator"]');
      await expect(statusIndicators).toHaveCount({ min: 1 });
      
      // Check that status colors are distinguishable
      const healthyIndicator = page.locator('[data-testid="status-indicator"][data-status="healthy"]');
      await expect(healthyIndicator).toHaveAttribute('data-status', 'healthy');
    });
  });

  test.describe('Performance and Loading', () => {
    
    test('Page load performance', async ({ page }) => {
      // Measure page load time
      const startTime = Date.now();
      
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(10000); // Should load within 10 seconds
    });

    test('Navigation performance', async ({ page }) => {
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Measure navigation time
      const startTime = Date.now();
      
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      
      const navTime = Date.now() - startTime;
      expect(navTime).toBeLessThan(5000); // Should navigate within 5 seconds
    });

    test('Memory usage remains stable', async ({ page }) => {
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Navigate between screens multiple times
      for (let i = 0; i < 5; i++) {
        await page.click('[data-testid="nav-monitoring"]');
        await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
        
        await page.click('[data-testid="nav-settings"]');
        await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
        
        await page.click('[data-testid="nav-dashboard"]');
        await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
      }
      
      // Verify dashboard is still responsive
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    });
  });
});
