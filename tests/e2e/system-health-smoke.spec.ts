import { test, expect } from '@playwright/test';

/**
 * System Health Smoke Tests - 100% Pass Guarantee
 * Tests only core services required by docker-global-setup.
 * Use with smoke-100percent.config.ts for CI/CD gates.
 *
 * Epic 31: Direct InfluxDB writes (enrichment-pipeline deprecated)
 */
test.describe('System Health Smoke Tests', () => {
  test('Core services are healthy', async ({ request }) => {
    const influxResponse = await request.get('http://localhost:8086/health');
    expect(influxResponse.status()).toBe(200);

    const wsResponse = await request.get('http://localhost:8001/health');
    expect(wsResponse.status()).toBe(200);

    const adminResponse = await request.get('http://localhost:8004/api/v1/health');
    expect(adminResponse.status()).toBe(200);
  });

  test('Health dashboard is reachable', async ({ request }) => {
    const res = await request.get('http://localhost:3000');
    expect(res.status()).toBe(200);
    expect(res.headers()['content-type']).toContain('text/html');
  });

  test('Data API returns events', async ({ request }) => {
    const eventsResponse = await request.get(
      'http://localhost:8006/api/v1/events?limit=10'
    );
    expect(eventsResponse.status()).toBe(200);
    const eventsData = await eventsResponse.json();
    expect(Array.isArray(eventsData)).toBe(true);
  });
});
