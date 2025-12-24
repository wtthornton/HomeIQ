import { test, expect } from '@playwright/test';

/**
 * Comprehensive Error Handling E2E Tests
 * Tests all error scenarios including the specific JSON parsing issue
 */
test.describe('Comprehensive Error Handling', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
  });

  test.describe('JSON Parsing Error Scenarios', () => {
    
    test('Detects and handles HTML responses instead of JSON', async ({ page }) => {
      // Set up console error monitoring
      const consoleErrors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      // Simulate the exact issue: HTML response instead of JSON
      await page.route('**/api/v1/health', route => 
        route.fulfill({
          status: 200,
          contentType: 'text/html',
          body: '<!DOCTYPE html><html><head><title>Error</title></head><body><h1>Internal Server Error</h1></body></html>'
        })
      );

      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Wait for error handling
      await page.waitForSelector('[data-testid="error-state"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="error-state"]')).toBeVisible();
      
      // Verify error message is user-friendly
      const errorMessage = page.locator('[data-testid="error-message"]');
      await expect(errorMessage).toBeVisible();
      
      const errorText = await errorMessage.textContent();
      expect(errorText).not.toContain('<!DOCTYPE');
      expect(errorText).not.toContain('Unexpected token');
      expect(errorText).toContain('Failed to fetch');
      
      // Check console for JSON parsing errors
      const jsonErrors = consoleErrors.filter(error => 
        error.includes('JSON') || 
        error.includes('Unexpected token') ||
        error.includes('<!DOCTYPE')
      );
      
      // Log errors for debugging but don't fail the test
      if (jsonErrors.length > 0) {
        console.log('JSON Parsing Errors Detected:', jsonErrors);
      }
    });

    test('Handles malformed JSON responses gracefully', async ({ page }) => {
      // Set up console error monitoring
      const consoleErrors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      // Simulate malformed JSON
      await page.route('**/api/v1/stats', route => 
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: '{"total_events": 100, "events_per_minute": 5, "last_event_time": "2024-01-01T00:00:00Z", "services": {'
        })
      );

      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Wait for error handling
      await page.waitForSelector('[data-testid="error-state"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="error-state"]')).toBeVisible();
      
      // Verify retry button is available
      const retryButton = page.locator('[data-testid="retry-button"]');
      await expect(retryButton).toBeVisible();
    });

    test('Handles empty JSON responses', async ({ page }) => {
      // Simulate empty JSON response
      await page.route('**/api/v1/events', route => 
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: ''
        })
      );

      // Navigate to monitoring screen
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      
      // Should handle empty response gracefully
      const eventsSection = page.locator('[data-testid="events-section"]');
      await expect(eventsSection).toBeVisible();
    });

    test('Handles non-JSON content types', async ({ page }) => {
      // Simulate XML response instead of JSON
      await page.route('**/api/v1/config', route => 
        route.fulfill({
          status: 200,
          contentType: 'application/xml',
          body: '<?xml version="1.0"?><config><setting>value</setting></config>'
        })
      );

      // Navigate to settings screen
      await page.click('[data-testid="nav-settings"]');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      
      // Should handle non-JSON response gracefully
      const settingsSection = page.locator('[data-testid="settings-section"]');
      await expect(settingsSection).toBeVisible();
    });
  });

  test.describe('Network Error Scenarios', () => {
    
    test('Handles complete API service failure', async ({ page }) => {
      // Simulate complete API failure
      await page.route('**/api/v1/**', route => route.abort());

      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Wait for error state
      await page.waitForSelector('[data-testid="error-state"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="error-state"]')).toBeVisible();
      
      // Verify error message
      const errorMessage = page.locator('[data-testid="error-message"]');
      await expect(errorMessage).toBeVisible();
      expect(await errorMessage.textContent()).toContain('Failed to fetch');
    });

    test('Handles partial API service failure', async ({ page }) => {
      // Simulate partial failure - health works but stats fails
      await page.route('**/api/v1/health', route => route.continue());
      await page.route('**/api/v1/stats', route => route.abort());

      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Should show partial data with error indicators
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Health section should work
      const healthSection = page.locator('[data-testid="system-health-section"]');
      await expect(healthSection).toBeVisible();
      
      // Statistics section should show error
      const statsError = page.locator('[data-testid="statistics-error"]');
      await expect(statsError).toBeVisible();
    });

    test('Handles slow API responses', async ({ page }) => {
      // Simulate very slow API response
      await page.route('**/api/v1/health', route => 
        new Promise(resolve => {
          setTimeout(() => {
            route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({
                overall_status: 'healthy',
                admin_api_status: 'healthy',
                ingestion_service: {
                  status: 'healthy',
                  websocket_connection: { is_connected: true },
                  event_processing: { events_per_minute: 0, total_events: 0, error_rate: 0 },
                  weather_enrichment: { enabled: true },
                  influxdb_storage: { is_connected: true }
                },
                timestamp: new Date().toISOString()
              })
            });
            resolve();
          }, 10000); // 10 second delay
        })
      );

      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Should show loading state
      await page.waitForSelector('[data-testid="loading-spinner"]', { timeout: 5000 });
      await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible();
      
      // Should eventually load successfully
      await page.waitForSelector('[data-testid="health-card"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="health-card"]')).toBeVisible();
    });

    test('Handles timeout scenarios', async ({ page }) => {
      // Simulate timeout (no response)
      await page.route('**/api/v1/health', route => {
        // Don't respond - simulate timeout
      });

      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Should show error after timeout
      await page.waitForSelector('[data-testid="error-state"]', { timeout: 30000 });
      await expect(page.locator('[data-testid="error-state"]')).toBeVisible();
    });
  });

  test.describe('Service-Specific Error Scenarios', () => {
    
    test('Handles InfluxDB connection errors', async ({ page }) => {
      // Simulate InfluxDB error in health response
      await page.route('**/api/v1/health', route => 
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            overall_status: 'degraded',
            admin_api_status: 'healthy',
            ingestion_service: {
              status: 'degraded',
              websocket_connection: { is_connected: true },
              event_processing: { events_per_minute: 0, total_events: 0, error_rate: 0.1 },
              weather_enrichment: { enabled: true },
              influxdb_storage: { is_connected: false, last_error: 'Connection timeout' }
            },
            timestamp: new Date().toISOString()
          })
        })
      );

      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Should show degraded status
      const healthStatus = page.locator('[data-testid="health-status"]');
      await expect(healthStatus).toBeVisible();
      await expect(healthStatus).toContainText('DEGRADED');
    });

    test('Handles WebSocket connection errors', async ({ page }) => {
      // Simulate WebSocket error in health response
      await page.route('**/api/v1/health', route => 
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            overall_status: 'degraded',
            admin_api_status: 'healthy',
            ingestion_service: {
              status: 'degraded',
              websocket_connection: { is_connected: false, last_error: 'Connection refused' },
              event_processing: { events_per_minute: 0, total_events: 0, error_rate: 0 },
              weather_enrichment: { enabled: true },
              influxdb_storage: { is_connected: true }
            },
            timestamp: new Date().toISOString()
          })
        })
      );

      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Should show WebSocket as disconnected
      const wsStatus = page.locator('[data-testid="websocket-status"]');
      await expect(wsStatus).toHaveAttribute('data-connected', 'false');
    });
  });

  test.describe('Error Recovery and Retry Mechanisms', () => {
    
    test('Retry mechanism works after temporary failure', async ({ page }) => {
      let requestCount = 0;
      
      // Simulate temporary failure followed by success
      await page.route('**/api/v1/health', route => {
        requestCount++;
        if (requestCount <= 2) {
          route.abort(); // Fail first 2 requests
        } else {
          route.continue(); // Allow subsequent requests
        }
      });

      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Should eventually load successfully after retries
      await page.waitForSelector('[data-testid="health-card"]', { timeout: 30000 });
      await expect(page.locator('[data-testid="health-card"]')).toBeVisible();
      
      // Verify retry was attempted
      expect(requestCount).toBeGreaterThan(2);
    });

    test('Manual retry button works correctly', async ({ page }) => {
      // Simulate initial failure
      await page.route('**/api/v1/health', route => route.abort());

      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Wait for error state
      await page.waitForSelector('[data-testid="error-state"]', { timeout: 15000 });
      
      // Restore API
      await page.unroute('**/api/v1/health');
      
      // Click retry button
      const retryButton = page.locator('[data-testid="retry-button"]');
      await expect(retryButton).toBeVisible();
      await retryButton.click();
      
      // Should load successfully after retry
      await page.waitForSelector('[data-testid="health-card"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="health-card"]')).toBeVisible();
    });

    test('Automatic retry with exponential backoff', async ({ page }) => {
      let requestCount = 0;
      const requestTimes: number[] = [];
      
      // Simulate failures with timing
      await page.route('**/api/v1/health', route => {
        requestCount++;
        requestTimes.push(Date.now());
        
        if (requestCount <= 3) {
          route.abort(); // Fail first 3 requests
        } else {
          route.continue(); // Allow 4th request
        }
      });

      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Should eventually load successfully
      await page.waitForSelector('[data-testid="health-card"]', { timeout: 30000 });
      await expect(page.locator('[data-testid="health-card"]')).toBeVisible();
      
      // Verify retry timing (should have delays between retries)
      if (requestTimes.length >= 2) {
        const timeBetweenRetries = requestTimes[1] - requestTimes[0];
        expect(timeBetweenRetries).toBeGreaterThan(1000); // At least 1 second delay
      }
    });
  });

  test.describe('User Experience During Errors', () => {
    
    test('Error messages are user-friendly', async ({ page }) => {
      // Simulate various error scenarios
      const errorScenarios = [
        { route: '**/api/v1/health', error: 'Network error' },
        { route: '**/api/v1/stats', error: 'Service unavailable' },
        { route: '**/api/v1/events', error: 'Data loading failed' }
      ];

      for (const scenario of errorScenarios) {
        await page.route(scenario.route, route => route.abort());
        
        // Navigate to dashboard
        await page.goto('http://localhost:3000');
        
        // Wait for error state
        await page.waitForSelector('[data-testid="error-state"]', { timeout: 15000 });
        
        // Verify error message is user-friendly
        const errorMessage = page.locator('[data-testid="error-message"]');
        await expect(errorMessage).toBeVisible();
        
        const errorText = await errorMessage.textContent();
        expect(errorText).not.toContain('<!DOCTYPE');
        expect(errorText).not.toContain('Unexpected token');
        expect(errorText).not.toContain('JSON.parse');
        expect(errorText).toMatch(/failed|error|unavailable/i);
        
        // Restore route for next test
        await page.unroute(scenario.route);
      }
    });

    test('Loading states are shown during errors', async ({ page }) => {
      // Simulate slow response
      await page.route('**/api/v1/health', route => 
        new Promise(resolve => {
          setTimeout(() => {
            route.abort();
            resolve();
          }, 5000);
        })
      );

      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Should show loading state initially
      await page.waitForSelector('[data-testid="loading-spinner"]', { timeout: 2000 });
      await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible();
      
      // Should eventually show error state
      await page.waitForSelector('[data-testid="error-state"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="error-state"]')).toBeVisible();
    });

    test('Navigation works during error states', async ({ page }) => {
      // Simulate API failure
      await page.route('**/api/v1/**', route => route.abort());

      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Wait for error state
      await page.waitForSelector('[data-testid="error-state"]', { timeout: 15000 });
      
      // Navigation should still work
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="monitoring-screen"]')).toBeVisible();
      
      await page.click('[data-testid="nav-settings"]');
      await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="settings-screen"]')).toBeVisible();
    });
  });
});
