import { test, expect } from '@playwright/test';

/**
 * Performance Tests
 * Tests system performance, load times, and responsiveness
 */
test.describe('Performance Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Set consistent viewport for performance tests
    await page.setViewportSize({ width: 1280, height: 720 });
  });

  test('Dashboard loads within acceptable time', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('http://localhost:3000');
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
    
    const loadTime = Date.now() - startTime;
    
    // Dashboard should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
    
    console.log(`Dashboard load time: ${loadTime}ms`);
  });

  test('API endpoints respond within acceptable time', async ({ page }) => {
    const endpoints = [
      'http://localhost:8086/health',
      'http://localhost:8001/health',
      'http://localhost:8002/health',
      'http://localhost:8004/api/v1/health',
      'http://localhost:8080/health'
    ];
    
    for (const endpoint of endpoints) {
      const startTime = Date.now();
      
      const response = await page.request.get(endpoint);
      expect(response.status()).toBe(200);
      
      const responseTime = Date.now() - startTime;
      
      // API endpoints should respond within 2 seconds
      expect(responseTime).toBeLessThan(2000);
      
      console.log(`${endpoint} response time: ${responseTime}ms`);
    }
  });

  test('Statistics API performs well under load', async ({ page }) => {
    const concurrentRequests = 10;
    const promises = [];
    
    const startTime = Date.now();
    
    // Make multiple concurrent requests to statistics endpoint
    for (let i = 0; i < concurrentRequests; i++) {
      promises.push(
        page.request.get('http://localhost:8004/api/v1/stats')
          .then(response => {
            expect(response.status()).toBe(200);
            return response.json();
          })
      );
    }
    
    const results = await Promise.all(promises);
    const totalTime = Date.now() - startTime;
    
    // All requests should complete within 10 seconds
    expect(totalTime).toBeLessThan(10000);
    
    // Verify all responses are valid
    results.forEach(data => {
      expect(data).toHaveProperty('total_events');
      expect(data).toHaveProperty('events_per_minute');
    });
    
    console.log(`Statistics API load test: ${concurrentRequests} concurrent requests completed in ${totalTime}ms`);
  });

  test('Events API handles pagination efficiently', async ({ page }) => {
    const pageSizes = [10, 50, 100, 500];
    
    for (const pageSize of pageSizes) {
      const startTime = Date.now();
      
      const response = await page.request.get(`http://localhost:8006/api/v1/events?limit=${pageSize}`);
      expect(response.status()).toBe(200);
      
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
      
      const responseTime = Date.now() - startTime;
      
      // Response time should scale reasonably with page size
      const maxAllowedTime = pageSize * 5; // 5ms per item
      expect(responseTime).toBeLessThan(maxAllowedTime);
      
      console.log(`Events API with limit ${pageSize}: ${responseTime}ms`);
    }
  });

  test('Dashboard real-time updates perform well', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
    
    // Measure time for initial data load
    const initialLoadStart = Date.now();
    await page.waitForSelector('[data-testid="health-cards"]');
    await page.waitForSelector('[data-testid="statistics-chart"]');
    await page.waitForSelector('[data-testid="events-feed"]');
    const initialLoadTime = Date.now() - initialLoadStart;
    
    // Initial load should complete within 3 seconds
    expect(initialLoadTime).toBeLessThan(3000);
    
    // Test refresh performance
    const refreshStart = Date.now();
    await page.click('[data-testid="refresh-button"]');
    await page.waitForTimeout(2000); // Wait for refresh to complete
    const refreshTime = Date.now() - refreshStart;
    
    // Refresh should complete within 2 seconds
    expect(refreshTime).toBeLessThan(2000);
    
    console.log(`Dashboard initial load: ${initialLoadTime}ms, refresh: ${refreshTime}ms`);
  });

  test('Navigation between screens is fast', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
    
    // Test navigation to monitoring
    const monitoringStart = Date.now();
    await page.click('[data-testid="nav-monitoring"]');
    await page.waitForSelector('[data-testid="monitoring-screen"]');
    const monitoringTime = Date.now() - monitoringStart;
    
    expect(monitoringTime).toBeLessThan(2000);
    
    // Test navigation to settings
    const settingsStart = Date.now();
    await page.click('[data-testid="nav-settings"]');
    await page.waitForSelector('[data-testid="settings-screen"]');
    const settingsTime = Date.now() - settingsStart;
    
    expect(settingsTime).toBeLessThan(2000);
    
    // Test navigation back to dashboard
    const dashboardStart = Date.now();
    await page.click('[data-testid="nav-dashboard"]');
    await page.waitForSelector('[data-testid="dashboard"]');
    const dashboardTime = Date.now() - dashboardStart;
    
    expect(dashboardTime).toBeLessThan(2000);
    
    console.log(`Navigation times - Monitoring: ${monitoringTime}ms, Settings: ${settingsTime}ms, Dashboard: ${dashboardTime}ms`);
  });

  test('Chart rendering and interaction performance', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForSelector('[data-testid="statistics-chart"]', { timeout: 15000 });
    
    // Measure chart rendering time
    const chartRenderStart = Date.now();
    await page.waitForSelector('[data-testid="statistics-chart"]');
    const chartRenderTime = Date.now() - chartRenderStart;
    
    // Chart should render within 2 seconds
    expect(chartRenderTime).toBeLessThan(2000);
    
    // Test chart interaction performance
    const chartToolbar = page.locator('[data-testid="chart-toolbar"]');
    if (await chartToolbar.isVisible()) {
      // Test time range changes
      const timeRangeStart = Date.now();
      const timeRangeSelect = page.locator('[data-testid="time-range-selector"]');
      await timeRangeSelect.selectOption('24h');
      await page.waitForTimeout(1000); // Wait for chart update
      const timeRangeTime = Date.now() - timeRangeStart;
      
      expect(timeRangeTime).toBeLessThan(3000);
      
      console.log(`Chart render: ${chartRenderTime}ms, time range change: ${timeRangeTime}ms`);
    }
  });

  test('Large datasets are handled efficiently', async ({ page }) => {
    // Test with larger event limits
    const largeLimits = [100, 500, 1000];
    
    for (const limit of largeLimits) {
      const startTime = Date.now();
      
      const response = await page.request.get(`http://localhost:8006/api/v1/events?limit=${limit}`);
      expect(response.status()).toBe(200);
      
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
      
      const responseTime = Date.now() - startTime;
      
      // Response time should scale reasonably
      const maxAllowedTime = limit * 3; // 3ms per item
      expect(responseTime).toBeLessThan(maxAllowedTime);
      
      console.log(`Large dataset test (${limit} items): ${responseTime}ms`);
    }
  });

  test('Memory usage remains stable during extended use', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
    
    // Get initial memory usage
    const initialMemory = await page.evaluate(() => {
      return (performance as any).memory?.usedJSHeapSize || 0;
    });
    
    // Perform multiple operations to test memory stability
    for (let i = 0; i < 10; i++) {
      // Navigate between screens
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForTimeout(500);
      await page.click('[data-testid="nav-settings"]');
      await page.waitForTimeout(500);
      await page.click('[data-testid="nav-dashboard"]');
      await page.waitForTimeout(500);
      
      // Refresh data
      await page.click('[data-testid="refresh-button"]');
      await page.waitForTimeout(1000);
    }
    
    // Get final memory usage
    const finalMemory = await page.evaluate(() => {
      return (performance as any).memory?.usedJSHeapSize || 0;
    });
    
    // Memory usage should not increase dramatically
    const memoryIncrease = finalMemory - initialMemory;
    const maxAllowedIncrease = initialMemory * 0.5; // 50% increase max
    
    if (initialMemory > 0) {
      expect(memoryIncrease).toBeLessThan(maxAllowedIncrease);
    }
    
    console.log(`Memory usage - Initial: ${initialMemory}, Final: ${finalMemory}, Increase: ${memoryIncrease}`);
  });

  test('Concurrent user simulation performs well', async ({ browser }) => {
    const concurrentUsers = 5;
    const pages = [];
    
    // Create multiple browser contexts
    for (let i = 0; i < concurrentUsers; i++) {
      const context = await browser.newContext();
      const page = await context.newPage();
      pages.push(page);
    }
    
    const startTime = Date.now();
    
    // Simulate concurrent users accessing the dashboard
    const promises = pages.map(async (page, index) => {
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Simulate user interactions
      await page.click('[data-testid="nav-monitoring"]');
      await page.waitForTimeout(1000);
      await page.click('[data-testid="nav-settings"]');
      await page.waitForTimeout(1000);
      await page.click('[data-testid="nav-dashboard"]');
      await page.waitForTimeout(1000);
      
      return index;
    });
    
    const results = await Promise.all(promises);
    const totalTime = Date.now() - startTime;
    
    // All users should complete their sessions within reasonable time
    expect(totalTime).toBeLessThan(30000); // 30 seconds max
    
    // Clean up
    for (const page of pages) {
      await page.context().close();
    }
    
    console.log(`Concurrent users test: ${concurrentUsers} users completed in ${totalTime}ms`);
  });

  test('WebSocket connection and message handling performance', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForSelector('[data-testid="websocket-status"]', { timeout: 10000 });
    
    // Measure WebSocket connection time
    const connectionStart = Date.now();
    const websocketStatus = page.locator('[data-testid="websocket-status"]');
    await expect(websocketStatus).toHaveAttribute('data-connected', 'true');
    const connectionTime = Date.now() - connectionStart;
    
    // WebSocket should connect within 5 seconds
    expect(connectionTime).toBeLessThan(5000);
    
    // Test message handling performance
    const messageStart = Date.now();
    
    // Simulate WebSocket messages
    await page.evaluate(() => {
      // Trigger multiple WebSocket message events
      for (let i = 0; i < 10; i++) {
        window.dispatchEvent(new CustomEvent('websocket-message', {
          detail: {
            type: 'state_changed',
            data: { entity_id: `test.entity.${i}`, state: 'on' }
          }
        }));
      }
    });
    
    await page.waitForTimeout(1000); // Allow time for message processing
    const messageTime = Date.now() - messageStart;
    
    // Message processing should be fast
    expect(messageTime).toBeLessThan(2000);
    
    console.log(`WebSocket connection: ${connectionTime}ms, message handling: ${messageTime}ms`);
  });

  test('Database query performance is acceptable', async ({ page }) => {
    // Test different query patterns and their performance
    
    const queries = [
      'http://localhost:8006/api/v1/events?limit=10',
      'http://localhost:8006/api/v1/events?limit=50&offset=0',
      'http://localhost:8006/api/v1/events?limit=100&entity_id=sensor.temperature',
      'http://localhost:8004/api/v1/stats?time_range=1h',
      'http://localhost:8004/api/v1/stats?time_range=24h'
    ];
    
    for (const query of queries) {
      const startTime = Date.now();
      
      const response = await page.request.get(query);
      expect(response.status()).toBe(200);
      
      const data = await response.json();
      expect(data).toBeDefined();
      
      const queryTime = Date.now() - startTime;
      
      // Database queries should complete within 3 seconds
      expect(queryTime).toBeLessThan(3000);
      
      console.log(`Database query ${query}: ${queryTime}ms`);
    }
  });

  test('Mobile performance is acceptable', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    const startTime = Date.now();
    
    await page.goto('http://localhost:3000');
    await page.waitForSelector('[data-testid="mobile-dashboard"]', { timeout: 15000 });
    
    const mobileLoadTime = Date.now() - startTime;
    
    // Mobile should load within 4 seconds (slightly more tolerance for mobile)
    expect(mobileLoadTime).toBeLessThan(4000);
    
    // Test mobile navigation performance
    const navStart = Date.now();
    await page.click('[data-testid="nav-monitoring"]');
    await page.waitForSelector('[data-testid="monitoring-screen"]');
    const navTime = Date.now() - navStart;
    
    expect(navTime).toBeLessThan(2500);
    
    console.log(`Mobile load: ${mobileLoadTime}ms, navigation: ${navTime}ms`);
  });
});
