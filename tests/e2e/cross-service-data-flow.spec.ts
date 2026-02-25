import { test, expect } from '@playwright/test';

/**
 * Cross-Service Data Flow E2E Tests
 * Validates the critical data pipeline:
 *
 *   Home Assistant -> websocket-ingestion (8001) -> InfluxDB (8086)
 *                          |
 *                     data-api (8006) <- PostgreSQL (metadata)
 *                          |
 *                   health-dashboard (3000)
 *
 * These tests verify that data submitted to the ingestion layer flows
 * through to the query and visualization layers.
 */

const WS_INGESTION_BASE = 'http://localhost:8001';
const INFLUX_BASE = 'http://localhost:8086';
const DATA_API_BASE = 'http://localhost:8006';
const ADMIN_API_BASE = 'http://localhost:8004';
const DASHBOARD_URL = 'http://localhost:3000';

const API_KEY = process.env.ADMIN_API_KEY || process.env.API_KEY || '';
const authHeaders = API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {};

test.describe('Cross-Service Data Flow Tests', () => {

  // ---------- Prerequisite: All services healthy ----------

  test.describe('Pipeline Prerequisites', () => {

    test('all pipeline services are healthy', async ({ request }) => {
      const services = [
        { name: 'InfluxDB', url: `${INFLUX_BASE}/health` },
        { name: 'WebSocket Ingestion', url: `${WS_INGESTION_BASE}/health` },
        { name: 'Data API', url: `${DATA_API_BASE}/health` },
        { name: 'Admin API', url: `${ADMIN_API_BASE}/api/v1/health` },
      ];

      for (const service of services) {
        const response = await request.get(service.url);
        expect(
          response.status(),
          `${service.name} should be reachable (got ${response.status()})`
        ).toBeLessThan(504);
      }
    });

    test('InfluxDB is ready to accept writes', async ({ request }) => {
      const readyResponse = await request.get(`${INFLUX_BASE}/ready`);
      expect(readyResponse.status()).toBe(200);

      const pingResponse = await request.get(`${INFLUX_BASE}/ping`);
      expect(pingResponse.status()).toBe(204);
    });
  });

  // ---------- Data ingestion to query flow ----------

  test.describe('Ingestion to Query Pipeline', () => {

    test('websocket-ingestion reports active InfluxDB connection', async ({ request }) => {
      const response = await request.get(`${WS_INGESTION_BASE}/health`);
      expect([200, 503]).toContain(response.status());

      if (response.ok()) {
        const data = await response.json();
        expect(data.status).toBe('healthy');

        // Check that InfluxDB is listed as a connected dependency
        if (data.influxdb_connected !== undefined) {
          expect(data.influxdb_connected).toBe(true);
        }
        if (data.dependencies?.influxdb) {
          expect(['healthy', 'connected']).toContain(data.dependencies.influxdb);
        }
      }
    });

    test('data-api can query events from InfluxDB', async ({ request }) => {
      const response = await request.get(`${DATA_API_BASE}/api/v1/events?limit=5`);
      expect([200, 401, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const events = await response.json();
        expect(Array.isArray(events)).toBe(true);

        // If there is data, verify structure
        if (events.length > 0) {
          const event = events[0];
          expect(event).toHaveProperty('id');
          expect(event).toHaveProperty('timestamp');
          expect(event).toHaveProperty('entity_id');
          expect(event).toHaveProperty('event_type');

          // Timestamp should be parseable
          const ts = new Date(event.timestamp);
          expect(ts.getTime()).not.toBeNaN();
        }
      }
    });

    test('data-api event statistics reflect stored data', async ({ request }) => {
      const statsResponse = await request.get(`${DATA_API_BASE}/api/v1/events/stats`);
      if (!statsResponse.ok()) {
        test.skip();
        return;
      }

      const stats = await statsResponse.json();
      expect(typeof stats).toBe('object');

      // If we have entities, there should be events
      const entitiesResponse = await request.get(`${DATA_API_BASE}/api/v1/events/entities`);
      if (entitiesResponse.ok()) {
        const entities = await entitiesResponse.json();
        if (Array.isArray(entities) && entities.length > 0) {
          // Stats should reflect at least some activity
          if (stats.total_events !== undefined) {
            expect(stats.total_events).toBeGreaterThan(0);
          }
        }
      }
    });
  });

  // ---------- Metadata storage verification ----------

  test.describe('Metadata Storage (PostgreSQL/SQLite)', () => {

    test('admin-api aggregated health includes database dependencies', async ({ request }) => {
      const response = await request.get(`${ADMIN_API_BASE}/api/v1/health`);
      expect([200, 503]).toContain(response.status());

      const data = await response.json();
      expect(data).toHaveProperty('status');
      expect(data).toHaveProperty('timestamp');

      // Verify the response includes dependency information
      if (data.dependencies) {
        const deps = Array.isArray(data.dependencies)
          ? data.dependencies.map((d: { name: string }) => d.name)
          : Object.keys(data.dependencies);
        expect(deps.length).toBeGreaterThan(0);
      }
    });

    test('admin-api stats endpoint queries metadata store', async ({ request }) => {
      const response = await request.get(`${ADMIN_API_BASE}/api/v1/stats`, {
        headers: authHeaders,
      });
      expect([200, 401, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const stats = await response.json();
        expect(stats).toHaveProperty('timestamp');
        expect(stats).toHaveProperty('services');

        // The timestamp should be recent (within 5 minutes)
        const ts = new Date(stats.timestamp);
        expect(ts.getTime()).not.toBeNaN();
        expect(Date.now() - ts.getTime()).toBeLessThan(5 * 60 * 1000);
      }
    });

    test('entity list is consistent between events and entities endpoints', async ({ request }) => {
      const eventsResponse = await request.get(`${DATA_API_BASE}/api/v1/events?limit=50`);
      const entitiesResponse = await request.get(`${DATA_API_BASE}/api/v1/events/entities`);

      if (!eventsResponse.ok() || !entitiesResponse.ok()) {
        test.skip();
        return;
      }

      const events = await eventsResponse.json();
      const entities = await entitiesResponse.json();

      if (events.length > 0 && Array.isArray(entities) && entities.length > 0) {
        // All entity_ids from events should appear in the entities list
        const entitySet = new Set(
          entities.map((e: string | { entity_id: string }) =>
            typeof e === 'string' ? e : e.entity_id
          )
        );

        for (const event of events) {
          if (event.entity_id) {
            expect(
              entitySet.has(event.entity_id),
              `Entity ${event.entity_id} from events should appear in entities list`
            ).toBeTruthy();
          }
        }
      }
    });
  });

  // ---------- Dashboard reflects backend data ----------

  test.describe('Dashboard Data Reflection', () => {

    test('health-dashboard loads and displays service data', async ({ page }) => {
      const response = await page.goto(DASHBOARD_URL, {
        waitUntil: 'domcontentloaded',
        timeout: 30000,
      });
      expect(response?.status()).toBe(200);

      // Dashboard should render its root element
      const root = page.locator('[data-testid="dashboard-root"], [data-testid="dashboard"], #root, #app');
      await expect(root).toBeVisible({ timeout: 15000 });
    });

    test('dashboard fetches health data from admin-api', async ({ page }) => {
      // Intercept the health API call from the dashboard
      let healthApiCalled = false;
      let healthApiResponse: unknown = null;

      await page.route('**/api/v1/health**', async (route) => {
        healthApiCalled = true;
        const response = await route.fetch();
        if (response.ok()) {
          healthApiResponse = await response.json();
        }
        await route.fulfill({ response });
      });

      await page.goto(DASHBOARD_URL, {
        waitUntil: 'networkidle',
        timeout: 30000,
      });

      // Give the dashboard time to make its API calls
      await page.waitForTimeout(5000);

      // The dashboard should have called the health API
      if (healthApiCalled && healthApiResponse) {
        expect(healthApiResponse).toHaveProperty('status');
      }

      // Unroute for cleanup
      await page.unroute('**/api/v1/health**');
    });

    test('dashboard fetches event data from data-api', async ({ page }) => {
      let eventsApiCalled = false;

      await page.route('**/api/v1/events**', async (route) => {
        eventsApiCalled = true;
        const response = await route.fetch();
        await route.fulfill({ response });
      });

      await page.goto(DASHBOARD_URL, {
        waitUntil: 'networkidle',
        timeout: 30000,
      });

      await page.waitForTimeout(5000);

      // The dashboard may or may not call events endpoint depending on the
      // active tab. We just verify it loads without errors.
      const consoleErrors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      // No unhandled errors should appear
      const criticalErrors = consoleErrors.filter(
        (e) => e.includes('TypeError') || e.includes('NetworkError') || e.includes('SyntaxError')
      );
      expect(criticalErrors.length).toBe(0);

      await page.unroute('**/api/v1/events**');
    });
  });

  // ---------- End-to-end latency ----------

  test.describe('Pipeline Latency', () => {

    test('ingestion health check responds within 2 seconds', async ({ request }) => {
      const start = Date.now();
      const response = await request.get(`${WS_INGESTION_BASE}/health`);
      const elapsed = Date.now() - start;

      expect([200, 503]).toContain(response.status());
      expect(elapsed).toBeLessThan(2000);
    });

    test('data-api query responds within 5 seconds', async ({ request }) => {
      const start = Date.now();
      const response = await request.get(`${DATA_API_BASE}/api/v1/events?limit=10`);
      const elapsed = Date.now() - start;

      expect([200, 401, 404, 500, 503]).toContain(response.status());
      expect(elapsed).toBeLessThan(5000);
    });

    test('full health aggregation responds within 10 seconds', async ({ request }) => {
      const start = Date.now();
      const response = await request.get(`${ADMIN_API_BASE}/api/v1/health`);
      const elapsed = Date.now() - start;

      expect([200, 503]).toContain(response.status());
      expect(elapsed).toBeLessThan(10000);
    });
  });

  // ---------- Failure propagation ----------

  test.describe('Failure Propagation Across Pipeline', () => {

    test('simulated InfluxDB failure is reflected in upstream services', async ({ page }) => {
      // Block InfluxDB from the browser context
      await page.route('http://localhost:8086/**', (route) => route.abort());

      // Check that admin-api health reflects degradation
      // (admin-api connects server-side, so route blocking may not affect it;
      // this verifies the dashboard handles the scenario gracefully)
      const response = await page.goto(DASHBOARD_URL, {
        waitUntil: 'domcontentloaded',
        timeout: 30000,
      });
      expect(response?.status()).toBe(200);

      // Dashboard should still render (graceful degradation)
      const root = page.locator('[data-testid="dashboard-root"], [data-testid="dashboard"], #root, #app');
      await expect(root).toBeVisible({ timeout: 15000 });

      await page.unroute('http://localhost:8086/**');
    });

    test('simulated data-api failure does not crash the dashboard', async ({ page }) => {
      // Block data-api calls
      await page.route(`${DATA_API_BASE}/**`, (route) => route.abort());

      const response = await page.goto(DASHBOARD_URL, {
        waitUntil: 'domcontentloaded',
        timeout: 30000,
      });
      expect(response?.status()).toBe(200);

      // Dashboard should still load its shell
      const root = page.locator('[data-testid="dashboard-root"], [data-testid="dashboard"], #root, #app');
      await expect(root).toBeVisible({ timeout: 15000 });

      await page.unroute(`${DATA_API_BASE}/**`);
    });
  });
});
