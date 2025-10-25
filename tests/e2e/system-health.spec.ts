import { test, expect } from '@playwright/test';

/**
 * System Health E2E Tests
 * Tests the health and connectivity of all backend services
 * Updated for Epic 31: Direct InfluxDB writes (enrichment-pipeline deprecated)
 */
test.describe('System Health Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Wait for system to be fully deployed
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
  });

  test('All services are healthy and responding', async ({ page }) => {
    // Test InfluxDB health
    const influxResponse = await page.request.get('http://localhost:8086/health');
    expect(influxResponse.status()).toBe(200);
    
    // Test WebSocket ingestion service (Epic 31: direct InfluxDB writes)
    const wsResponse = await page.request.get('http://localhost:8001/health');
    expect(wsResponse.status()).toBe(200);
    
    // Test Admin API service
    const adminResponse = await page.request.get('http://localhost:8003/api/v1/health');
    expect(adminResponse.status()).toBe(200);
    
    // Test Data retention service
    const retentionResponse = await page.request.get('http://localhost:8080/health');
    expect(retentionResponse.status()).toBe(200);
  });

  test('Health dashboard displays system status correctly', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('http://localhost:3000');
    
    // Wait for health data to load
    await page.waitForSelector('[data-testid="health-card"]', { timeout: 10000 });
    
    // Verify health indicators are present
    const healthCards = page.locator('[data-testid="health-card"]');
    await expect(healthCards).toHaveCount(5); // All 5 services
    
    // Check that all services show healthy status
    const healthyIndicators = page.locator('[data-testid="status-indicator"][data-status="healthy"]');
    await expect(healthyIndicators).toHaveCount(5);
  });

  test('Statistics endpoint returns valid data', async ({ page }) => {
    const statsResponse = await page.request.get('http://localhost:8003/api/v1/stats');
    expect(statsResponse.status()).toBe(200);
    
    const statsData = await statsResponse.json();
    expect(statsData).toHaveProperty('total_events');
    expect(statsData).toHaveProperty('events_per_minute');
    expect(statsData).toHaveProperty('last_event_time');
    expect(statsData).toHaveProperty('services');
  });

  test('Recent events endpoint returns data', async ({ page }) => {
    const eventsResponse = await page.request.get('http://localhost:8003/api/v1/events/recent?limit=10');
    expect(eventsResponse.status()).toBe(200);
    
    const eventsData = await eventsResponse.json();
    expect(Array.isArray(eventsData)).toBe(true);
    
    if (eventsData.length > 0) {
      const event = eventsData[0];
      expect(event).toHaveProperty('id');
      expect(event).toHaveProperty('timestamp');
      expect(event).toHaveProperty('entity_id');
      expect(event).toHaveProperty('event_type');
    }
  });

  test('WebSocket connection establishes successfully', async ({ page }) => {
    await page.goto('http://localhost:3000');
    
    // Wait for WebSocket connection indicator
    await page.waitForSelector('[data-testid="websocket-status"]', { timeout: 10000 });
    
    // Check connection status
    const connectionStatus = page.locator('[data-testid="websocket-status"]');
    await expect(connectionStatus).toHaveAttribute('data-connected', 'true');
  });

  test('Error handling works correctly when services are down', async ({ page }) => {
    // This test would require stopping services temporarily
    // For now, we'll test the error display UI components
    
    await page.goto('http://localhost:3000');
    
    // Simulate network error by intercepting requests
    await page.route('**/api/v1/health', route => route.abort());
    
    // Wait for error state to appear
    await page.waitForSelector('[data-testid="error-state"]', { timeout: 10000 });
    
    // Verify error message is displayed
    const errorMessage = page.locator('[data-testid="error-message"]');
    await expect(errorMessage).toBeVisible();
  });
});
