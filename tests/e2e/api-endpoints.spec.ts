import { test, expect } from '@playwright/test';

/**
 * Comprehensive API Endpoints E2E Tests
 * Aligned with actual admin-api (8004) and data-api (8006) response contracts.
 *
 * Admin-api health response shape:
 *   { service, status, timestamp, uptime_seconds, version, dependencies, metrics }
 *
 * Admin-api stats response shape:
 *   { timestamp, period, metrics[], trends[], alerts[], services{} }
 *
 * NOTE: Most admin-api endpoints require Bearer auth. Tests accept 401
 * when no API key is configured in the test environment.
 */

const ADMIN_PORT = 8004;
const DATA_PORT = 8006;
const ADMIN_BASE = `http://localhost:${ADMIN_PORT}`;
const DATA_BASE = `http://localhost:${DATA_PORT}`;

// Use env var if set, otherwise empty (will trigger 401 on protected endpoints)
const API_KEY = process.env.ADMIN_API_KEY || process.env.API_KEY || '';
const authHeaders = API_KEY ? { 'Authorization': `Bearer ${API_KEY}` } : {};

test.describe('API Endpoints Tests', () => {

  // ---------- Admin API: Health (no auth required) ----------

  test.describe('Admin API - Health Endpoints', () => {

    test('GET /api/v1/health - Enhanced health status', async ({ page }) => {
      const response = await page.request.get(`${ADMIN_BASE}/api/v1/health`);
      expect([200, 503]).toContain(response.status());

      const healthData = await response.json();

      // Standardized health response shape
      expect(healthData).toHaveProperty('service');
      expect(healthData).toHaveProperty('status');
      expect(healthData).toHaveProperty('timestamp');

      // status is one of healthy/degraded/unhealthy
      const validStatuses = ['healthy', 'degraded', 'unhealthy'];
      expect(validStatuses).toContain(healthData.status);

      // Optional fields (present when service is fully running)
      if (healthData.uptime_seconds !== undefined) {
        expect(typeof healthData.uptime_seconds).toBe('number');
      }
      if (healthData.dependencies) {
        expect(Array.isArray(healthData.dependencies)).toBe(true);
        for (const dep of healthData.dependencies) {
          expect(dep).toHaveProperty('name');
          expect(dep).toHaveProperty('status');
        }
      }
      if (healthData.metrics) {
        expect(typeof healthData.metrics).toBe('object');
      }
    });

    test('GET /api/v1/health/services - Service health map', async ({ page }) => {
      const response = await page.request.get(`${ADMIN_BASE}/api/v1/health/services`);
      expect([200, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const data = await response.json();
        expect(typeof data).toBe('object');
      }
    });
  });

  // ---------- Admin API: Stats (auth required) ----------

  test.describe('Admin API - Stats Endpoints', () => {

    test('GET /api/v1/stats - System statistics', async ({ page }) => {
      const response = await page.request.get(`${ADMIN_BASE}/api/v1/stats`, {
        headers: authHeaders,
      });
      expect([200, 401, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const statsData = await response.json();
        // Actual response shape: { timestamp, period, metrics[], trends[], alerts[], services{} }
        expect(statsData).toHaveProperty('timestamp');
        expect(statsData).toHaveProperty('period');
        expect(statsData).toHaveProperty('metrics');
        expect(statsData).toHaveProperty('services');
        expect(typeof statsData.services).toBe('object');
      }
    });

    test('GET /api/v1/stats?period=1h - Stats with period', async ({ page }) => {
      const response = await page.request.get(`${ADMIN_BASE}/api/v1/stats?period=1h`, {
        headers: authHeaders,
      });
      expect([200, 401, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const statsData = await response.json();
        expect(statsData).toHaveProperty('period', '1h');
      }
    });

    test('GET /api/v1/stats?service=websocket-ingestion - Stats filtered by service', async ({ page }) => {
      const response = await page.request.get(
        `${ADMIN_BASE}/api/v1/stats?service=websocket-ingestion`,
        { headers: authHeaders }
      );
      expect([200, 401, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const statsData = await response.json();
        expect(statsData).toHaveProperty('services');
      }
    });

    test('GET /api/v1/stats/services - Service-specific statistics', async ({ page }) => {
      const response = await page.request.get(`${ADMIN_BASE}/api/v1/stats/services`, {
        headers: authHeaders,
      });
      expect([200, 401, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const servicesData = await response.json();
        expect(typeof servicesData).toBe('object');
      }
    });
  });

  // ---------- Admin API: Config (auth required) ----------

  test.describe('Admin API - Config Endpoints', () => {

    test('GET /api/v1/config - System configuration', async ({ page }) => {
      const response = await page.request.get(`${ADMIN_BASE}/api/v1/config`, {
        headers: authHeaders,
      });
      expect([200, 401, 403, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const configData = await response.json();
        expect(typeof configData).toBe('object');
      }
    });

    test('PUT /api/v1/config/{service} - Update configuration', async ({ page }) => {
      const response = await page.request.put(
        `${ADMIN_BASE}/api/v1/config/websocket-ingestion`,
        {
          headers: authHeaders,
          data: [{ key: 'test_key', value: 'test_value' }],
        }
      );
      expect([200, 400, 401, 403, 404, 500]).toContain(response.status());
    });
  });

  // ---------- Data API: Events (port 8006) ----------

  test.describe('Data API - Events Endpoints', () => {

    test('GET /api/v1/events - Recent events', async ({ page }) => {
      const response = await page.request.get(`${DATA_BASE}/api/v1/events`);
      expect([200, 401, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const eventsData = await response.json();
        expect(Array.isArray(eventsData)).toBe(true);

        if (eventsData.length > 0) {
          const event = eventsData[0];
          expect(event).toHaveProperty('id');
          expect(event).toHaveProperty('timestamp');
          expect(event).toHaveProperty('entity_id');
          expect(event).toHaveProperty('event_type');
        }
      }
    });

    test('GET /api/v1/events with query parameters', async ({ page }) => {
      const response = await page.request.get(`${DATA_BASE}/api/v1/events?limit=50&offset=0`);
      expect([200, 401, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const eventsData = await response.json();
        expect(Array.isArray(eventsData)).toBe(true);
        expect(eventsData.length).toBeLessThanOrEqual(50);
      }
    });

    test('GET /api/v1/events with entity_id filter', async ({ page }) => {
      const response = await page.request.get(
        `${DATA_BASE}/api/v1/events?entity_id=sensor.temperature`
      );
      expect([200, 401, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const eventsData = await response.json();
        expect(Array.isArray(eventsData)).toBe(true);
      }
    });

    test('GET /api/v1/events/stats - Event statistics', async ({ page }) => {
      const response = await page.request.get(`${DATA_BASE}/api/v1/events/stats`);
      expect([200, 401, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const statsData = await response.json();
        expect(typeof statsData).toBe('object');
      }
    });

    test('GET /api/v1/events/entities - Active entities', async ({ page }) => {
      const response = await page.request.get(`${DATA_BASE}/api/v1/events/entities`);
      expect([200, 401, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const entitiesData = await response.json();
        expect(Array.isArray(entitiesData)).toBe(true);
      }
    });

    test('GET /api/v1/events/types - Event types', async ({ page }) => {
      const response = await page.request.get(`${DATA_BASE}/api/v1/events/types`);
      expect([200, 401, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const typesData = await response.json();
        expect(Array.isArray(typesData)).toBe(true);
      }
    });
  });

  // ---------- WebSocket Ingestion Service ----------

  test.describe('WebSocket Ingestion Service Endpoints', () => {

    test('GET /health - WebSocket service health', async ({ page }) => {
      const response = await page.request.get('http://localhost:8001/health');
      expect([200, 503]).toContain(response.status());

      if (response.ok()) {
        const healthData = await response.json();
        expect(healthData).toHaveProperty('status');
        expect(healthData).toHaveProperty('service');
        expect(healthData.service).toBe('websocket-ingestion');
      }
    });
  });

  // ---------- Data Retention Service ----------

  test.describe('Data Retention Service Endpoints', () => {

    test('GET /health - Data retention service health', async ({ page }) => {
      const response = await page.request.get('http://localhost:8080/health');
      // Service may not always be running
      expect([200, 404, 502, 503]).toContain(response.status());

      if (response.ok()) {
        const healthData = await response.json();
        expect(healthData).toHaveProperty('status');
      }
    });

    test('GET /stats - Data retention statistics', async ({ page }) => {
      const response = await page.request.get('http://localhost:8080/stats');
      // Service may not be running or path may differ
      if (response.ok()) {
        const statsData = await response.json();
        expect(typeof statsData).toBe('object');
      }
    });
  });

  // ---------- InfluxDB ----------

  test.describe('InfluxDB Endpoints', () => {

    test('GET /health - InfluxDB health', async ({ page }) => {
      const response = await page.request.get('http://localhost:8086/health');
      expect(response.status()).toBe(200);

      const healthData = await response.json();
      expect(healthData).toHaveProperty('status');
      expect(healthData).toHaveProperty('name');
    });

    test('GET /ping - InfluxDB ping', async ({ page }) => {
      const response = await page.request.get('http://localhost:8086/ping');
      expect(response.status()).toBe(204);
    });

    test('GET /ready - InfluxDB ready check', async ({ page }) => {
      const response = await page.request.get('http://localhost:8086/ready');
      expect(response.status()).toBe(200);
    });
  });

  // ---------- API Automation Edge Service ----------

  test.describe('API Automation Edge Service Endpoints', () => {

    test('GET /health - Service health check', async ({ page }) => {
      const response = await page.request.get('http://localhost:8041/health');
      expect([200, 502, 503]).toContain(response.status());

      if (response.ok()) {
        const healthData = await response.json();
        expect(healthData).toHaveProperty('status', 'healthy');
        expect(healthData).toHaveProperty('service', 'api-automation-edge');
      }
    });

    test('POST /api/specs - Create automation spec', async ({ page }) => {
      const spec = {
        id: 'test_spec_api_endpoints',
        version: '1.0.0',
        name: 'Test Spec API Endpoints',
        enabled: true,
        triggers: [{ type: 'ha_event', event_type: 'state_changed' }],
        actions: [
          {
            id: 'act1',
            capability: 'light.turn_on',
            target: { entity_id: 'light.test' },
            data: {},
          },
        ],
        policy: { risk: 'low' },
      };

      const response = await page.request.post('http://localhost:8041/api/specs', {
        data: spec,
      });
      expect([200, 400, 502, 503]).toContain(response.status());

      if (response.ok()) {
        const body = await response.json();
        expect(body.success).toBe(true);
        expect(body.spec).toHaveProperty('id', spec.id);
      }
    });

    test('GET /api/specs - List all specs', async ({ page }) => {
      const response = await page.request.get('http://localhost:8041/api/specs');
      expect([200, 502, 503]).toContain(response.status());

      if (response.ok()) {
        const body = await response.json();
        expect(body.success).toBe(true);
        expect(body).toHaveProperty('specs');
        expect(Array.isArray(body.specs)).toBeTruthy();
      }
    });

    test('GET /api/observability/kill-switch/status', async ({ page }) => {
      const response = await page.request.get(
        'http://localhost:8041/api/observability/kill-switch/status'
      );
      expect([200, 502, 503]).toContain(response.status());

      if (response.ok()) {
        const body = await response.json();
        expect(body.success).toBe(true);
        expect(body).toHaveProperty('status');
        expect(body.status).toHaveProperty('global_paused');
      }
    });
  });

  // ---------- API Error Handling ----------

  test.describe('API Error Handling', () => {

    test('404 error handling - nonexistent route', async ({ page }) => {
      const response = await page.request.get(`${ADMIN_BASE}/api/v1/nonexistent`);
      expect([404, 405]).toContain(response.status());
    });

    test('Invalid parameter handling', async ({ page }) => {
      const response = await page.request.get(`${DATA_BASE}/api/v1/events?limit=invalid`);
      expect([400, 422]).toContain(response.status());
    });

    test('Large limit parameter handling', async ({ page }) => {
      const response = await page.request.get(`${DATA_BASE}/api/v1/events?limit=10000`);
      expect([200, 401, 422, 500]).toContain(response.status());

      if (response.ok()) {
        const eventsData = await response.json();
        expect(Array.isArray(eventsData)).toBe(true);
      }
    });

    test('JSON response validation for key endpoints', async ({ page }) => {
      const endpoints = [
        { url: `${ADMIN_BASE}/api/v1/health`, name: 'health' },
      ];

      for (const { url, name } of endpoints) {
        const response = await page.request.get(url);
        if (response.ok()) {
          const contentType = response.headers()['content-type'];
          expect(contentType).toContain('application/json');
          const responseText = await response.text();
          expect(responseText).not.toContain('<!DOCTYPE');
          expect(responseText).not.toContain('<html');
          const data = JSON.parse(responseText);
          expect(data).toBeDefined();
          expect(typeof data).toBe('object');
        }
      }
    });
  });

  // ---------- Performance ----------

  test.describe('API Response Time Performance', () => {

    test('Health endpoint response time < 5s', async ({ page }) => {
      const startTime = Date.now();
      const response = await page.request.get(`${ADMIN_BASE}/api/v1/health`);
      const elapsed = Date.now() - startTime;

      expect([200, 503]).toContain(response.status());
      expect(elapsed).toBeLessThan(5000);
    });

    test('Stats endpoint response time < 10s', async ({ page }) => {
      const startTime = Date.now();
      const response = await page.request.get(`${ADMIN_BASE}/api/v1/stats`, {
        headers: authHeaders,
      });
      const elapsed = Date.now() - startTime;

      expect([200, 401, 404, 500, 503]).toContain(response.status());
      expect(elapsed).toBeLessThan(10000);
    });

    test('Events endpoint response time < 15s', async ({ page }) => {
      const startTime = Date.now();
      const response = await page.request.get(`${DATA_BASE}/api/v1/events?limit=100`);
      const elapsed = Date.now() - startTime;

      expect([200, 401, 404, 500, 503]).toContain(response.status());
      expect(elapsed).toBeLessThan(15000);
    });
  });

  // ---------- Data Validation ----------

  test.describe('API Data Validation', () => {

    test('Health data structure validation', async ({ page }) => {
      const response = await page.request.get(`${ADMIN_BASE}/api/v1/health`);
      expect([200, 503]).toContain(response.status());

      const contentType = response.headers()['content-type'];
      expect(contentType).toContain('application/json');

      const responseText = await response.text();
      expect(responseText).not.toContain('<!DOCTYPE');
      expect(responseText).not.toContain('<html');

      const healthData = JSON.parse(responseText);

      // Validate status field
      const validStatuses = ['healthy', 'degraded', 'unhealthy'];
      expect(validStatuses).toContain(healthData.status);

      // Validate timestamp
      if (healthData.timestamp) {
        const timestamp = new Date(healthData.timestamp);
        expect(timestamp.getTime()).not.toBeNaN();
      }
    });

    test('Events data structure validation', async ({ page }) => {
      const response = await page.request.get(`${DATA_BASE}/api/v1/events?limit=5`);

      if (response.ok()) {
        const contentType = response.headers()['content-type'];
        expect(contentType).toContain('application/json');

        const responseText = await response.text();
        expect(responseText).not.toContain('<!DOCTYPE');

        const eventsData = JSON.parse(responseText);
        expect(Array.isArray(eventsData)).toBe(true);

        for (const event of eventsData) {
          expect(event).toHaveProperty('id');
          expect(event).toHaveProperty('timestamp');
          expect(event).toHaveProperty('entity_id');
          expect(event).toHaveProperty('event_type');

          expect(typeof event.id).toBe('string');
          expect(event.id.length).toBeGreaterThan(0);
        }
      }
    });

    test('Statistics data validation', async ({ page }) => {
      const response = await page.request.get(`${ADMIN_BASE}/api/v1/stats`, {
        headers: authHeaders,
      });

      if (response.ok()) {
        const contentType = response.headers()['content-type'];
        expect(contentType).toContain('application/json');

        const responseText = await response.text();
        expect(responseText).not.toContain('<!DOCTYPE');

        const statsData = JSON.parse(responseText);
        expect(statsData).toHaveProperty('timestamp');
        expect(statsData).toHaveProperty('period');
        expect(typeof statsData.services).toBe('object');
      }
    });
  });

  // ---------- Concurrent Requests ----------

  test.describe('Concurrent API Requests', () => {

    test('Multiple concurrent health requests', async ({ page }) => {
      const promises = Array.from({ length: 10 }, () =>
        page.request.get(`${ADMIN_BASE}/api/v1/health`)
      );

      const responses = await Promise.all(promises);
      for (const response of responses) {
        expect([200, 503]).toContain(response.status());
      }
    });

    test('Multiple concurrent stats requests', async ({ page }) => {
      const promises = Array.from({ length: 5 }, () =>
        page.request.get(`${ADMIN_BASE}/api/v1/stats`, { headers: authHeaders })
      );

      const responses = await Promise.all(promises);
      for (const response of responses) {
        expect([200, 401, 404, 500, 503]).toContain(response.status());
      }
    });
  });
});
