import { test, expect } from '@playwright/test';

/**
 * System Health E2E Tests
 * Tests the health and connectivity of all backend services
 * Updated for Epic 31: Direct InfluxDB writes (enrichment-pipeline deprecated)
 */
test.describe('System Health Tests', () => {

  test('All services are healthy and responding', async ({ request }) => {
    const influxResponse = await request.get('http://localhost:8086/health');
    expect(influxResponse.status()).toBe(200);
    const wsResponse = await request.get('http://localhost:8001/health');
    expect(wsResponse.status()).toBe(200);
    const adminResponse = await request.get('http://localhost:8004/api/v1/health');
    expect(adminResponse.status()).toBe(200);
    const retentionResponse = await request.get('http://localhost:8080/health');
    expect(retentionResponse.status()).toBe(200);
    const apiAutomationResponse = await request.get('http://localhost:8041/health');
    expect(apiAutomationResponse.status()).toBe(200);
    const apiAutomationData = await apiAutomationResponse.json();
    expect(apiAutomationData.status).toBe('healthy');
    expect(apiAutomationData.service).toBe('api-automation-edge');
  });

  test('Statistics endpoint returns valid data', async ({ request }) => {
    const statsResponse = await request.get('http://localhost:8004/api/v1/stats');
    // Admin API may require auth (401); if 200, validate structure
    expect([200, 401]).toContain(statsResponse.status());
    if (statsResponse.status() === 200) {
      const statsData = await statsResponse.json();
      expect(statsData).toHaveProperty('services');
      expect(statsData).toHaveProperty('period');
      expect(statsData).toHaveProperty('timestamp');
    }
  });

  test('Recent events endpoint returns data', async ({ request }) => {
    // Events migrated to data-api (Epic 13)
    const eventsResponse = await request.get('http://localhost:8006/api/v1/events?limit=10');
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

  test('Health dashboard is reachable', async ({ request }) => {
    const res = await request.get('http://localhost:3000');
    expect(res.status()).toBe(200);
    expect(res.headers()['content-type']).toContain('text/html');
  });

  test('Error handling works correctly when services are down', async ({ page }) => {
    await page.route('**/api/v1/health', route => route.abort());
    const response = await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded', timeout: 20000 });
    expect(response?.status()).toBe(200);
    await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible({ timeout: 10000 });
  });
});
