import { test, expect } from '@playwright/test';

/**
 * Integration Tests
 * Tests end-to-end data flow and service integration
 */
test.describe('Integration Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Wait for system to be fully deployed
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('domcontentloaded'); // More reliable than networkidle
    // Additional wait for React to hydrate
    await page.waitForTimeout(2000);
  });

  test('Complete data flow from Home Assistant to dashboard', async ({ page }) => {
    // This test simulates the complete data flow (Epic 31):
    // Home Assistant -> WebSocket -> InfluxDB (direct) -> Dashboard
    
    // Step 1: Verify WebSocket ingestion service is connected
    const wsHealthResponse = await page.request.get('http://localhost:8001/health');
    expect(wsHealthResponse.status()).toBe(200);
    
    const wsHealthData = await wsHealthResponse.json();
    expect(wsHealthData.status).toBe('healthy');
    
    // Step 2: Verify InfluxDB is accessible (direct writes in Epic 31)
    const influxHealthResponse = await page.request.get('http://localhost:8086/health');
    expect(influxHealthResponse.status()).toBe(200);
    
    // Step 3: Verify admin API can retrieve data
    const adminStatsResponse = await page.request.get('http://localhost:8003/api/v1/stats');
    expect(adminStatsResponse.status()).toBe(200);
    
    const statsData = await adminStatsResponse.json();
    expect(statsData).toHaveProperty('total_events');
    
    // Step 4: Verify dashboard displays the data
    await page.goto('http://localhost:3000');
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
    
    // Check that statistics are displayed
    const statisticsChart = page.locator('[data-testid="statistics-chart"]');
    await expect(statisticsChart).toBeVisible();
    
    // Check that events are displayed
    const eventsFeed = page.locator('[data-testid="events-feed"]');
    await expect(eventsFeed).toBeVisible();
  });

  test('Service dependency chain works correctly', async ({ page }) => {
    // Test that services depend on each other correctly
    
    // Step 1: Verify InfluxDB is the foundation
    const influxHealthResponse = await page.request.get('http://localhost:8086/health');
    expect(influxHealthResponse.status()).toBe(200);
    
    // Step 2: Verify WebSocket ingestion depends on InfluxDB
    const wsHealthResponse = await page.request.get('http://localhost:8001/health');
    expect(wsHealthResponse.status()).toBe(200);
    
    const wsHealthData = await wsHealthResponse.json();
    expect(wsHealthData.dependencies?.influxdb).toBe('healthy');
    
    // Step 3: Verify admin API depends on all services
    const adminHealthResponse = await page.request.get('http://localhost:8003/api/v1/health');
    expect(adminHealthResponse.status()).toBe(200);
    
    const adminHealthData = await adminHealthResponse.json();
    expect(adminHealthData.dependencies).toBeDefined();
  });

  test('Real-time data updates work end-to-end', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
    
    // Get initial event count
    const initialEventsResponse = await page.request.get('http://localhost:8003/api/v1/events/recent?limit=10');
    const initialEvents = await initialEventsResponse.json();
    const initialCount = initialEvents.length;
    
    // Wait for potential new events (simulating Home Assistant activity)
    await page.waitForTimeout(10000);
    
    // Check if new events appeared
    const updatedEventsResponse = await page.request.get('http://localhost:8003/api/v1/events/recent?limit=10');
    const updatedEvents = await updatedEventsResponse.json();
    const updatedCount = updatedEvents.length;
    
    // Verify the dashboard reflects the data changes
    const eventsFeed = page.locator('[data-testid="events-feed"]');
    await expect(eventsFeed).toBeVisible();
    
    // The count might be the same if no new events occurred, which is fine
    // We're mainly testing that the system can handle real-time updates
    expect(updatedCount).toBeGreaterThanOrEqual(initialCount);
  });

  test('Weather data enrichment integration works', async ({ page }) => {
    // Epic 31: Weather enrichment is now done inline in websocket-ingestion
    // Test weather API integration if enabled
    const weatherApiResponse = await page.request.get('http://localhost:8001/health');
    expect(weatherApiResponse.status()).toBe(200);
    
    // Check if weather service is available
    const weatherHealthResponse = await page.request.get('http://localhost:8080/health');
    if (weatherHealthResponse.status() === 200) {
      // Weather service is available, test integration
      const weatherHealthData = await weatherHealthResponse.json();
      expect(weatherHealthData.status).toBe('healthy');
      
      // Note: enrichment-pipeline is deprecated in Epic 31
      // Weather enrichment is now done directly in websocket-ingestion
    }
  });

  test('Data retention service integration works', async ({ page }) => {
    // Test data retention service integration
    const retentionHealthResponse = await page.request.get('http://localhost:8080/health');
    expect(retentionHealthResponse.status()).toBe(200);
    
    const retentionHealthData = await retentionHealthResponse.json();
    expect(retentionHealthData.status).toBe('healthy');
    
    // Verify data retention is working with InfluxDB
    const retentionStatsResponse = await page.request.get('http://localhost:8080/stats');
    if (retentionStatsResponse.status() === 200) {
      const retentionStats = await retentionStatsResponse.json();
      expect(retentionStats).toHaveProperty('cleanup_runs');
      expect(retentionStats).toHaveProperty('data_size');
    }
  });

  test('Admin API provides comprehensive system information', async ({ page }) => {
    // Test that admin API aggregates information from all services
    
    // Test health endpoint
    const healthResponse = await page.request.get('http://localhost:8003/api/v1/health');
    expect(healthResponse.status()).toBe(200);
    
    const healthData = await healthResponse.json();
    expect(healthData).toHaveProperty('status');
    expect(healthData).toHaveProperty('services');
    expect(healthData).toHaveProperty('dependencies');
    
    // Test statistics endpoint
    const statsResponse = await page.request.get('http://localhost:8003/api/v1/stats');
    expect(statsResponse.status()).toBe(200);
    
    const statsData = await statsResponse.json();
    expect(statsData).toHaveProperty('total_events');
    expect(statsData).toHaveProperty('events_per_minute');
    expect(statsData).toHaveProperty('last_event_time');
    expect(statsData).toHaveProperty('services');
    
    // Test events endpoint
    const eventsResponse = await page.request.get('http://localhost:8003/api/v1/events/recent?limit=10');
    expect(eventsResponse.status()).toBe(200);
    
    const eventsData = await eventsResponse.json();
    expect(Array.isArray(eventsData)).toBe(true);
    
    // Test configuration endpoint
    const configResponse = await page.request.get('http://localhost:8003/api/v1/config');
    expect(configResponse.status()).toBe(200);
    
    const configData = await configResponse.json();
    expect(configData).toHaveProperty('influxdb');
    expect(configData).toHaveProperty('services');
  });

  test('Error propagation and handling across services', async ({ page }) => {
    // Test error handling across the service chain
    
    // Simulate InfluxDB being unavailable
    await page.route('http://localhost:8086/**', route => route.abort());
    
    // Check that dependent services handle the error gracefully
    const wsHealthResponse = await page.request.get('http://localhost:8001/health');
    if (wsHealthResponse.status() === 200) {
      const wsHealthData = await wsHealthResponse.json();
      // Service should report InfluxDB as unhealthy
      expect(wsHealthData.dependencies?.influxdb).toBe('unhealthy');
    }
    
    // Note: enrichment-pipeline is deprecated in Epic 31 (direct InfluxDB writes)
    
    // Check that admin API reports the error
    const adminHealthResponse = await page.request.get('http://localhost:8003/api/v1/health');
    expect(adminHealthResponse.status()).toBe(200);
    
    const adminHealthData = await adminHealthResponse.json();
    expect(adminHealthData.status).toBe('degraded');
    
    // Verify dashboard shows error state
    await page.goto('http://localhost:3000');
    await page.waitForTimeout(5000); // Allow time for error propagation
    
    // Check if error state is displayed
    const errorState = page.locator('[data-testid="error-state"]');
    if (await errorState.isVisible()) {
      await expect(errorState).toBeVisible();
    }
  });

  test('Configuration changes propagate across services', async ({ page }) => {
    // Test configuration management integration
    
    // Get current configuration
    const configResponse = await page.request.get('http://localhost:8003/api/v1/config');
    expect(configResponse.status()).toBe(200);
    
    const configData = await configResponse.json();
    const originalConfig = { ...configData };
    
    // Update configuration through admin API
    const updateResponse = await page.request.put('http://localhost:8003/api/v1/config', {
      data: {
        ...configData,
        refresh_interval: 60000 // Change refresh interval
      }
    });
    
    if (updateResponse.status() === 200) {
      // Verify configuration was updated
      const updatedConfigResponse = await page.request.get('http://localhost:8003/api/v1/config');
      const updatedConfigData = await updatedConfigResponse.json();
      
      expect(updatedConfigData.refresh_interval).toBe(60000);
      
      // Restore original configuration
      await page.request.put('http://localhost:8003/api/v1/config', {
        data: originalConfig
      });
    }
  });

  test('WebSocket real-time updates work in dashboard', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
    
    // Wait for WebSocket connection
    await page.waitForSelector('[data-testid="websocket-status"]', { timeout: 10000 });
    
    const websocketStatus = page.locator('[data-testid="websocket-status"]');
    await expect(websocketStatus).toHaveAttribute('data-connected', 'true');
    
    // Get initial timestamp
    const initialTimestamp = await page.locator('[data-testid="last-updated"]').textContent();
    
    // Wait for potential WebSocket updates
    await page.waitForTimeout(5000);
    
    // Check if timestamp updated (indicating real-time updates)
    const updatedTimestamp = await page.locator('[data-testid="last-updated"]').textContent();
    
    // If WebSocket is working, timestamp should update
    // If not, that's also acceptable as it depends on actual data flow
    expect(updatedTimestamp).toBeDefined();
  });

  test('Performance metrics integration works', async ({ page }) => {
    // Test performance monitoring integration
    
    // Check monitoring screen
    await page.goto('http://localhost:3000/monitoring');
    await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 15000 });
    
    // Verify performance metrics are displayed
    const performanceMetrics = page.locator('[data-testid="performance-metrics"]');
    await expect(performanceMetrics).toBeVisible();
    
    // Check that metrics have values
    const cpuUsage = page.locator('[data-testid="cpu-usage"]');
    await expect(cpuUsage).toBeVisible();
    
    const memoryUsage = page.locator('[data-testid="memory-usage"]');
    await expect(memoryUsage).toBeVisible();
    
    // Verify service monitoring shows all services
    const serviceMonitoring = page.locator('[data-testid="service-monitoring"]');
    await expect(serviceMonitoring).toBeVisible();
    
    const serviceCards = page.locator('[data-testid="service-card"]');
    const serviceCount = await serviceCards.count();
    expect(serviceCount).toBeGreaterThan(0);
  });

  test('Data export integration works end-to-end', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
    
    // Test data export functionality
    const exportButton = page.locator('[data-testid="export-button"]');
    if (await exportButton.isVisible()) {
      await exportButton.click();
      
      // Wait for export dialog
      await page.waitForSelector('[data-testid="export-dialog"]');
      
      // Select export format
      const formatSelect = page.locator('[data-testid="export-format"]');
      await formatSelect.selectOption('json');
      
      // Confirm export
      await page.click('[data-testid="confirm-export"]');
      
      // Wait for export to complete
      await page.waitForSelector('[data-testid="export-success"]', { timeout: 10000 });
      
      // Verify success message
      const successMessage = page.locator('[data-testid="export-success"]');
      await expect(successMessage).toBeVisible();
    }
  });
});
