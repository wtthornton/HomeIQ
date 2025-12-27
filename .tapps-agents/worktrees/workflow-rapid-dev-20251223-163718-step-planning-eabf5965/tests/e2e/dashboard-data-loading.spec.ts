import { test, expect } from '@playwright/test';

/**
 * Dashboard Data Loading Validation Tests
 * Tests that the dashboard loads data correctly without JSON parsing errors
 */
test.describe('Dashboard Data Loading Validation', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard and wait for initial load
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Critical Data Loading Tests', () => {
    
    test('Dashboard loads without JSON parsing errors', async ({ page }) => {
      // Set up console error monitoring
      const consoleErrors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      // Wait for dashboard to fully load
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Wait for data to load (health cards should be visible)
      await page.waitForSelector('[data-testid="health-card"]', { timeout: 20000 });
      
      // Check for JSON parsing errors
      const jsonErrors = consoleErrors.filter(error => 
        error.includes('JSON') || 
        error.includes('Unexpected token') ||
        error.includes('<!DOCTYPE')
      );
      
      expect(jsonErrors).toHaveLength(0);
      
      if (jsonErrors.length > 0) {
        console.log('JSON Parsing Errors Found:', jsonErrors);
      }
    });

    test('Health data loads and displays correctly', async ({ page }) => {
      // Wait for health section to load
      await page.waitForSelector('[data-testid="system-health-section"]', { timeout: 15000 });
      
      // Verify health cards are present and have data
      const healthCards = page.locator('[data-testid="health-card"]');
      await expect(healthCards).toHaveCount({ min: 1 });
      
      // Verify each health card has required elements
      const cardCount = await healthCards.count();
      for (let i = 0; i < cardCount; i++) {
        const card = healthCards.nth(i);
        await expect(card.locator('[data-testid="health-card-title"]')).toBeVisible();
        await expect(card.locator('[data-testid="health-card-status"]')).toBeVisible();
        await expect(card.locator('[data-testid="health-card-value"]')).toBeVisible();
      }
      
      // Verify no error states are displayed
      const errorStates = page.locator('[data-testid="error-state"]');
      await expect(errorStates).toHaveCount(0);
    });

    test('Statistics data loads without errors', async ({ page }) => {
      // Wait for statistics to load
      await page.waitForSelector('[data-testid="statistics-section"]', { timeout: 15000 });
      
      // Verify statistics are displayed
      const statisticsCards = page.locator('[data-testid="statistics-card"]');
      await expect(statisticsCards).toHaveCount({ min: 1 });
      
      // Verify statistics have valid data
      for (let i = 0; i < await statisticsCards.count(); i++) {
        const card = statisticsCards.nth(i);
        const value = card.locator('[data-testid="statistic-value"]');
        await expect(value).toBeVisible();
        
        // Verify value is not an error message
        const valueText = await value.textContent();
        expect(valueText).not.toContain('Error');
        expect(valueText).not.toContain('Failed');
        expect(valueText).not.toContain('<!DOCTYPE');
      }
    });

    test('Events data loads without errors', async ({ page }) => {
      // Navigate to monitoring screen where events are displayed
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
      
      // Wait for events to load
      await page.waitForSelector('[data-testid="events-section"]', { timeout: 15000 });
      
      // Verify events are displayed (could be empty but should not show errors)
      const eventsList = page.locator('[data-testid="events-list"]');
      await expect(eventsList).toBeVisible();
      
      // Check for error states in events
      const eventErrors = page.locator('[data-testid="events-error"]');
      await expect(eventErrors).toHaveCount(0);
    });

    test('Real-time updates work without JSON errors', async ({ page }) => {
      // Get initial timestamp
      const initialTimestamp = await page.locator('[data-testid="last-updated"]').textContent();
      
      // Set up console error monitoring for the update period
      const consoleErrors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });
      
      // Wait for potential updates (30 seconds)
      await page.waitForTimeout(30000);
      
      // Check for JSON parsing errors during updates
      const jsonErrors = consoleErrors.filter(error => 
        error.includes('JSON') || 
        error.includes('Unexpected token') ||
        error.includes('<!DOCTYPE')
      );
      
      expect(jsonErrors).toHaveLength(0);
      
      // Verify timestamp updated or dashboard is still responsive
      const currentTimestamp = await page.locator('[data-testid="last-updated"]').textContent();
      expect(currentTimestamp).toMatch(/\d{2}:\d{2}:\d{2}/);
    });
  });

  test.describe('API Response Validation', () => {
    
    test('All API endpoints return valid JSON', async ({ page }) => {
      const apiEndpoints = [
        '/api/v1/health',
        '/api/v1/stats',
        '/api/v1/events?limit=10',
        '/api/v1/config'
      ];
      
      for (const endpoint of apiEndpoints) {
        const response = await page.request.get(`http://localhost:3000${endpoint}`);
        expect(response.status()).toBe(200);
        
        // Verify Content-Type is JSON
        const contentType = response.headers()['content-type'];
        expect(contentType).toContain('application/json');
        
        // Verify response can be parsed as JSON
        const data = await response.json();
        expect(data).toBeDefined();
        expect(typeof data).toBe('object');
        
        // Verify response doesn't contain HTML
        const responseText = await response.text();
        expect(responseText).not.toContain('<!DOCTYPE');
        expect(responseText).not.toContain('<html');
      }
    });

    test('API responses have expected structure', async ({ page }) => {
      // Test health endpoint structure
      const healthResponse = await page.request.get('http://localhost:3000/api/v1/health');
      const healthData = await healthResponse.json();
      
      expect(healthData).toHaveProperty('overall_status');
      expect(healthData).toHaveProperty('timestamp');
      expect(healthData).toHaveProperty('ingestion_service');
      
      // Test stats endpoint structure
      const statsResponse = await page.request.get('http://localhost:3000/api/v1/stats');
      const statsData = await statsResponse.json();
      
      expect(statsData).toHaveProperty('total_events');
      expect(statsData).toHaveProperty('events_per_minute');
      expect(statsData).toHaveProperty('last_event_time');
      
      // Test events endpoint structure
      const eventsResponse = await page.request.get('http://localhost:3000/api/v1/events?limit=5');
      const eventsData = await eventsResponse.json();
      
      expect(Array.isArray(eventsData)).toBe(true);
    });
  });

  test.describe('Error State Detection', () => {
    
    test('Detects and reports JSON parsing errors', async ({ page }) => {
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
      
      // Check for specific JSON parsing errors
      const jsonParsingErrors = consoleErrors.filter(error => 
        error.includes('Unexpected token') ||
        error.includes('JSON.parse') ||
        error.includes('<!DOCTYPE')
      );
      
      if (jsonParsingErrors.length > 0) {
        console.log('JSON Parsing Errors Detected:', jsonParsingErrors);
        // This test should fail if JSON parsing errors are found
        expect(jsonParsingErrors).toHaveLength(0);
      }
    });

    test('Error states are displayed correctly when APIs fail', async ({ page }) => {
      // Simulate API failure
      await page.route('**/api/v1/health', route => route.abort());
      
      // Navigate to dashboard
      await page.goto('http://localhost:3000');
      
      // Wait for error state to appear
      await page.waitForSelector('[data-testid="error-state"]', { timeout: 15000 });
      
      // Verify error message is user-friendly
      const errorMessage = page.locator('[data-testid="error-message"]');
      await expect(errorMessage).toBeVisible();
      
      const errorText = await errorMessage.textContent();
      expect(errorText).not.toContain('<!DOCTYPE');
      expect(errorText).not.toContain('Unexpected token');
      expect(errorText).toContain('Failed to fetch');
    });

    test('Retry mechanism works correctly', async ({ page }) => {
      // Simulate temporary API failure
      let requestCount = 0;
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
      
      // Wait for retry to succeed
      await page.waitForSelector('[data-testid="health-card"]', { timeout: 30000 });
      
      // Verify dashboard loaded successfully after retry
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    });
  });

  test.describe('Performance and Reliability', () => {
    
    test('Dashboard loads within acceptable time limits', async ({ page }) => {
      const startTime = Date.now();
      
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="health-card"]', { timeout: 15000 });
      
      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(15000); // Should load within 15 seconds
      
      console.log(`Dashboard loaded in ${loadTime}ms`);
    });

    test('Multiple rapid navigations work without errors', async ({ page }) => {
      // Set up console error monitoring
      const consoleErrors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });
      
      // Perform multiple rapid navigations
      for (let i = 0; i < 5; i++) {
        await page.goto('http://localhost:3000');
        await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
        
        await page.click('[data-testid="nav-monitoring"]');
        await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
        
        await page.click('[data-testid="nav-settings"]');
        await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
      }
      
      // Check for JSON parsing errors
      const jsonErrors = consoleErrors.filter(error => 
        error.includes('JSON') || 
        error.includes('Unexpected token') ||
        error.includes('<!DOCTYPE')
      );
      
      expect(jsonErrors).toHaveLength(0);
    });
  });
});
