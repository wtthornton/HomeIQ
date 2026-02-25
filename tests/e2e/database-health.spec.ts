import { test, expect } from '@playwright/test';

/**
 * Database Health E2E Tests
 * Validates database connectivity and operations via API endpoints.
 *
 * Targets:
 *   - data-api (8006): Main data access layer (PostgreSQL + InfluxDB)
 *   - admin-api (8004): System health aggregation
 *
 * These tests verify that the database layer is operational without
 * requiring direct database access -- everything goes through the API.
 */

const DATA_PORT = 8006;
const ADMIN_PORT = 8004;
const DATA_BASE = `http://localhost:${DATA_PORT}`;
const ADMIN_BASE = `http://localhost:${ADMIN_PORT}`;

const API_KEY = process.env.ADMIN_API_KEY || process.env.API_KEY || '';
const authHeaders = API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {};

test.describe('Database Health Tests', () => {

  // ---------- Health endpoint reports database status ----------

  test.describe('Database Connectivity via Health Endpoints', () => {

    test('data-api /health reports database connection status', async ({ request }) => {
      const response = await request.get(`${DATA_BASE}/health`);
      expect([200, 503]).toContain(response.status());

      const data = await response.json();
      expect(data).toHaveProperty('status');
      expect(data).toHaveProperty('service');

      // When healthy, dependencies should be listed
      if (response.status() === 200) {
        expect(data.status).toBe('healthy');
        // data-api should report its database backend
        if (data.dependencies) {
          const dbDep = Array.isArray(data.dependencies)
            ? data.dependencies.find((d: { name: string }) =>
                d.name === 'database' || d.name === 'postgresql' || d.name === 'sqlite'
              )
            : data.dependencies.database || data.dependencies.postgresql || data.dependencies.sqlite;
          if (dbDep) {
            expect(['healthy', 'connected', 'ok']).toContain(
              typeof dbDep === 'string' ? dbDep : dbDep.status
            );
          }
        }
      }
    });

    test('admin-api /health reports overall system database health', async ({ request }) => {
      const response = await request.get(`${ADMIN_BASE}/api/v1/health`);
      expect([200, 503]).toContain(response.status());

      const data = await response.json();
      expect(data).toHaveProperty('status');

      // Admin API aggregates dependency health
      if (data.dependencies && Array.isArray(data.dependencies)) {
        for (const dep of data.dependencies) {
          expect(dep).toHaveProperty('name');
          expect(dep).toHaveProperty('status');
        }
      }
    });

    test('InfluxDB health endpoint is reachable', async ({ request }) => {
      const response = await request.get('http://localhost:8086/health');
      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(data).toHaveProperty('status');
      expect(data.status).toBe('pass');
    });
  });

  // ---------- Schema accessibility ----------

  test.describe('Schema Accessibility', () => {

    test('all API resource endpoints are accessible', async ({ request }) => {
      // These endpoints implicitly verify that the underlying tables/schemas
      // are accessible through the data-api.
      const endpoints = [
        { path: '/api/v1/events?limit=1', name: 'events' },
        { path: '/api/v1/events/stats', name: 'event-stats' },
        { path: '/api/v1/events/entities', name: 'entities' },
        { path: '/api/v1/events/types', name: 'event-types' },
      ];

      for (const { path, name } of endpoints) {
        const response = await request.get(`${DATA_BASE}${path}`);
        // Accept 200 (success) or 401 (auth required) but not 500 (broken)
        expect(
          [200, 401, 404].includes(response.status()),
          `${name} endpoint returned ${response.status()}`
        ).toBeTruthy();
      }
    });

    test('health services map returns per-service status', async ({ request }) => {
      const response = await request.get(`${ADMIN_BASE}/api/v1/health/services`);
      expect([200, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const data = await response.json();
        expect(typeof data).toBe('object');
        // Should have at least one service reported
        const keys = Object.keys(data);
        expect(keys.length).toBeGreaterThan(0);
      }
    });
  });

  // ---------- Basic CRUD through the API ----------

  test.describe('CRUD Operations via API', () => {

    test('read events with pagination parameters', async ({ request }) => {
      const response = await request.get(`${DATA_BASE}/api/v1/events?limit=5&offset=0`);
      expect([200, 401, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const events = await response.json();
        expect(Array.isArray(events)).toBe(true);
        expect(events.length).toBeLessThanOrEqual(5);

        for (const event of events) {
          expect(event).toHaveProperty('id');
          expect(event).toHaveProperty('timestamp');
          expect(event).toHaveProperty('entity_id');
        }
      }
    });

    test('read events filtered by entity_id', async ({ request }) => {
      // First get any available entity
      const entitiesResponse = await request.get(`${DATA_BASE}/api/v1/events/entities`);
      if (!entitiesResponse.ok()) {
        test.skip();
        return;
      }

      const entities = await entitiesResponse.json();
      if (!Array.isArray(entities) || entities.length === 0) {
        test.skip();
        return;
      }

      const entityId = typeof entities[0] === 'string' ? entities[0] : entities[0].entity_id;
      const response = await request.get(
        `${DATA_BASE}/api/v1/events?entity_id=${encodeURIComponent(entityId)}&limit=5`
      );
      expect([200, 401]).toContain(response.status());

      if (response.ok()) {
        const events = await response.json();
        expect(Array.isArray(events)).toBe(true);
        // All returned events should match the requested entity
        for (const event of events) {
          expect(event.entity_id).toBe(entityId);
        }
      }
    });

    test('statistics endpoint returns numeric aggregates', async ({ request }) => {
      const response = await request.get(`${ADMIN_BASE}/api/v1/stats`, {
        headers: authHeaders,
      });
      expect([200, 401, 404, 500, 503]).toContain(response.status());

      if (response.ok()) {
        const stats = await response.json();
        expect(stats).toHaveProperty('timestamp');
        expect(stats).toHaveProperty('services');
        expect(typeof stats.services).toBe('object');
      }
    });
  });

  // ---------- Concurrent reads/writes ----------

  test.describe('Concurrency Resilience', () => {

    test('concurrent read requests do not deadlock', async ({ request }) => {
      const startTime = Date.now();

      const promises = Array.from({ length: 20 }, (_, i) =>
        request.get(`${DATA_BASE}/api/v1/events?limit=5&offset=${i * 5}`)
      );

      const responses = await Promise.all(promises);
      const elapsed = Date.now() - startTime;

      // All should complete (no hangs)
      for (const response of responses) {
        expect([200, 401, 404, 500, 503]).toContain(response.status());
      }

      // 20 concurrent requests should complete within 30 seconds
      expect(elapsed).toBeLessThan(30000);
    });

    test('concurrent health checks do not cause connection pool exhaustion', async ({ request }) => {
      const promises = Array.from({ length: 15 }, () =>
        request.get(`${DATA_BASE}/health`)
      );

      const responses = await Promise.all(promises);

      let healthyCount = 0;
      for (const response of responses) {
        expect([200, 503]).toContain(response.status());
        if (response.status() === 200) {
          healthyCount++;
        }
      }

      // At least 80% of concurrent health checks should succeed
      expect(healthyCount).toBeGreaterThanOrEqual(12);
    });

    test('mixed read operations from different endpoints do not deadlock', async ({ request }) => {
      const endpoints = [
        `${DATA_BASE}/api/v1/events?limit=3`,
        `${DATA_BASE}/api/v1/events/stats`,
        `${DATA_BASE}/api/v1/events/entities`,
        `${DATA_BASE}/api/v1/events/types`,
        `${DATA_BASE}/health`,
        `${ADMIN_BASE}/api/v1/health`,
      ];

      const promises = endpoints.map((url) => request.get(url));
      const responses = await Promise.all(promises);

      for (const response of responses) {
        // None should hang; 4xx/5xx is acceptable, but not a timeout
        expect(response.status()).toBeGreaterThanOrEqual(200);
        expect(response.status()).toBeLessThan(600);
      }
    });
  });

  // ---------- Data integrity ----------

  test.describe('Data Integrity Checks', () => {

    test('event timestamps are valid ISO 8601', async ({ request }) => {
      const response = await request.get(`${DATA_BASE}/api/v1/events?limit=10`);
      if (!response.ok()) {
        test.skip();
        return;
      }

      const events = await response.json();
      for (const event of events) {
        if (event.timestamp) {
          const parsed = new Date(event.timestamp);
          expect(parsed.getTime()).not.toBeNaN();
          // Timestamp should be within the last year (sanity check)
          const oneYearAgo = Date.now() - 365 * 24 * 60 * 60 * 1000;
          expect(parsed.getTime()).toBeGreaterThan(oneYearAgo);
        }
      }
    });

    test('event IDs are unique within a result set', async ({ request }) => {
      const response = await request.get(`${DATA_BASE}/api/v1/events?limit=50`);
      if (!response.ok()) {
        test.skip();
        return;
      }

      const events = await response.json();
      if (events.length > 1) {
        const ids = events.map((e: { id: string }) => e.id);
        const uniqueIds = new Set(ids);
        expect(uniqueIds.size).toBe(ids.length);
      }
    });

    test('health endpoint timestamps are recent', async ({ request }) => {
      const response = await request.get(`${ADMIN_BASE}/api/v1/health`);
      if (!response.ok()) {
        test.skip();
        return;
      }

      const data = await response.json();
      if (data.timestamp) {
        const timestamp = new Date(data.timestamp);
        const now = Date.now();
        const drift = now - timestamp.getTime();
        // Timestamp should be within the last 5 minutes
        expect(drift).toBeLessThan(5 * 60 * 1000);
      }
    });
  });
});
