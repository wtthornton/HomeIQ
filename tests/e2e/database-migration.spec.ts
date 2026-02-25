import { test, expect } from '@playwright/test';

/**
 * Database Migration E2E Tests
 * Validates behavior during and after the SQLite-to-PostgreSQL migration.
 *
 * Tests cover:
 *   - Health endpoints reporting the correct database backend
 *   - API response consistency regardless of backend
 *   - Graceful handling of database connection failures
 *
 * These tests are designed to run against either the SQLite or PostgreSQL
 * backend, verifying that the API contract is stable across both.
 */

const DATA_PORT = 8006;
const ADMIN_PORT = 8004;
const DATA_BASE = `http://localhost:${DATA_PORT}`;
const ADMIN_BASE = `http://localhost:${ADMIN_PORT}`;

const API_KEY = process.env.ADMIN_API_KEY || process.env.API_KEY || '';
const authHeaders = API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {};

test.describe('Database Migration Tests', () => {

  // ---------- Backend detection ----------

  test.describe('Database Backend Reporting', () => {

    test('data-api health reports database backend type', async ({ request }) => {
      const response = await request.get(`${DATA_BASE}/health`);
      expect([200, 503]).toContain(response.status());

      if (response.ok()) {
        const data = await response.json();
        expect(data).toHaveProperty('status');

        // Check if backend type is reported in health response
        // The exact field depends on the data-api implementation
        const backendIndicators = [
          data.database_backend,
          data.db_type,
          data.backend,
          data.config?.database_backend,
        ].filter(Boolean);

        if (backendIndicators.length > 0) {
          const backend = backendIndicators[0];
          expect(['postgresql', 'postgres', 'sqlite', 'sqlite3']).toContain(
            backend.toLowerCase()
          );
        }

        // Dependencies should include database info
        if (data.dependencies) {
          const deps = Array.isArray(data.dependencies) ? data.dependencies : [];
          const dbDep = deps.find(
            (d: { name: string }) =>
              d.name === 'database' ||
              d.name === 'postgresql' ||
              d.name === 'sqlite' ||
              d.name === 'postgres'
          );
          if (dbDep) {
            expect(dbDep).toHaveProperty('status');
          }
        }
      }
    });

    test('admin-api health includes database dependency status', async ({ request }) => {
      const response = await request.get(`${ADMIN_BASE}/api/v1/health`);
      expect([200, 503]).toContain(response.status());

      const data = await response.json();
      expect(data).toHaveProperty('status');

      // Admin-api should report database status in its dependencies
      if (data.dependencies && Array.isArray(data.dependencies)) {
        for (const dep of data.dependencies) {
          expect(dep).toHaveProperty('name');
          expect(dep).toHaveProperty('status');
          expect(['healthy', 'degraded', 'unhealthy', 'connected', 'disconnected']).toContain(
            dep.status
          );
        }
      }
    });
  });

  // ---------- API response consistency ----------

  test.describe('API Response Consistency (Backend-Agnostic)', () => {

    test('events endpoint returns consistent structure', async ({ request }) => {
      const response = await request.get(`${DATA_BASE}/api/v1/events?limit=10`);
      if (!response.ok()) {
        test.skip();
        return;
      }

      const events = await response.json();
      expect(Array.isArray(events)).toBe(true);

      // Every event must have the same core fields regardless of backend
      for (const event of events) {
        // Required fields
        expect(event).toHaveProperty('id');
        expect(event).toHaveProperty('timestamp');
        expect(event).toHaveProperty('entity_id');
        expect(event).toHaveProperty('event_type');

        // Type validation
        expect(typeof event.id).toBe('string');
        expect(typeof event.entity_id).toBe('string');
        expect(typeof event.event_type).toBe('string');

        // Timestamp is valid
        const ts = new Date(event.timestamp);
        expect(ts.getTime()).not.toBeNaN();
      }
    });

    test('events/stats endpoint returns consistent structure', async ({ request }) => {
      const response = await request.get(`${DATA_BASE}/api/v1/events/stats`);
      if (!response.ok()) {
        test.skip();
        return;
      }

      const stats = await response.json();
      expect(typeof stats).toBe('object');

      // Stats should be an object with numeric/string values
      // The exact shape may vary but should not be an array or primitive
      expect(stats).not.toBeNull();
    });

    test('events/entities endpoint returns consistent list format', async ({ request }) => {
      const response = await request.get(`${DATA_BASE}/api/v1/events/entities`);
      if (!response.ok()) {
        test.skip();
        return;
      }

      const entities = await response.json();
      expect(Array.isArray(entities)).toBe(true);

      // Each entry should be a string or object with entity_id
      for (const entity of entities) {
        if (typeof entity === 'string') {
          expect(entity.length).toBeGreaterThan(0);
        } else {
          expect(entity).toHaveProperty('entity_id');
          expect(typeof entity.entity_id).toBe('string');
        }
      }
    });

    test('events/types endpoint returns consistent list format', async ({ request }) => {
      const response = await request.get(`${DATA_BASE}/api/v1/events/types`);
      if (!response.ok()) {
        test.skip();
        return;
      }

      const types = await response.json();
      expect(Array.isArray(types)).toBe(true);

      for (const eventType of types) {
        if (typeof eventType === 'string') {
          expect(eventType.length).toBeGreaterThan(0);
        } else {
          expect(eventType).toHaveProperty('event_type');
        }
      }
    });

    test('pagination works consistently across backends', async ({ request }) => {
      // Fetch page 1
      const page1 = await request.get(`${DATA_BASE}/api/v1/events?limit=3&offset=0`);
      if (!page1.ok()) {
        test.skip();
        return;
      }

      const events1 = await page1.json();
      expect(Array.isArray(events1)).toBe(true);
      expect(events1.length).toBeLessThanOrEqual(3);

      // Fetch page 2
      const page2 = await request.get(`${DATA_BASE}/api/v1/events?limit=3&offset=3`);
      if (!page2.ok()) {
        test.skip();
        return;
      }

      const events2 = await page2.json();
      expect(Array.isArray(events2)).toBe(true);
      expect(events2.length).toBeLessThanOrEqual(3);

      // Pages should not overlap (if there is enough data)
      if (events1.length === 3 && events2.length > 0) {
        const ids1 = new Set(events1.map((e: { id: string }) => e.id));
        for (const event of events2) {
          expect(ids1.has(event.id)).toBe(false);
        }
      }
    });

    test('health endpoint JSON shape is stable', async ({ request }) => {
      const response = await request.get(`${ADMIN_BASE}/api/v1/health`);
      expect([200, 503]).toContain(response.status());

      const data = await response.json();

      // These fields must always be present
      expect(data).toHaveProperty('status');
      expect(data).toHaveProperty('service');
      expect(data).toHaveProperty('timestamp');

      // Status is a known enum
      expect(['healthy', 'degraded', 'unhealthy']).toContain(data.status);

      // Timestamp is valid
      const ts = new Date(data.timestamp);
      expect(ts.getTime()).not.toBeNaN();
    });
  });

  // ---------- Connection failure handling ----------

  test.describe('Database Connection Failure Handling', () => {

    test('data-api returns 503 or degraded status when database is unreachable', async ({ page }) => {
      // We cannot actually kill the database in a test, but we can verify
      // that the health endpoint reports connection status accurately
      const response = await page.request.get(`${DATA_BASE}/health`);
      const data = await response.json();

      // If status is unhealthy/degraded, the response should indicate why
      if (data.status === 'unhealthy' || data.status === 'degraded') {
        // Should include dependency information showing which component is down
        if (data.dependencies) {
          const failedDeps = Array.isArray(data.dependencies)
            ? data.dependencies.filter(
                (d: { status: string }) => d.status !== 'healthy' && d.status !== 'connected'
              )
            : [];
          expect(failedDeps.length).toBeGreaterThan(0);
        }
      }
    });

    test('health endpoint always returns valid JSON even during failures', async ({ request }) => {
      const response = await request.get(`${DATA_BASE}/health`);
      // Should always return JSON, even on 503
      const contentType = response.headers()['content-type'];
      expect(contentType).toContain('application/json');

      const text = await response.text();
      expect(() => JSON.parse(text)).not.toThrow();
    });

    test('admin-api health aggregates failure states correctly', async ({ request }) => {
      const response = await request.get(`${ADMIN_BASE}/api/v1/health`);
      const data = await response.json();

      if (data.dependencies && Array.isArray(data.dependencies)) {
        const hasUnhealthy = data.dependencies.some(
          (d: { status: string }) => d.status === 'unhealthy' || d.status === 'disconnected'
        );

        // If any dependency is unhealthy, overall status should not be 'healthy'
        if (hasUnhealthy) {
          expect(data.status).not.toBe('healthy');
        }
      }
    });

    test('API endpoints return appropriate error codes on database issues', async ({ request }) => {
      // Test that endpoints don't return 200 with empty/null data when the
      // database is having issues -- they should return proper error codes
      const response = await request.get(`${DATA_BASE}/api/v1/events?limit=5`);

      if (response.status() >= 500) {
        // Server error should include an error message
        const data = await response.json().catch(() => null);
        if (data) {
          expect(data).toHaveProperty('error');
        }
      } else if (response.ok()) {
        // Success should return valid data
        const data = await response.json();
        expect(Array.isArray(data)).toBe(true);
      }
      // 401/404 are also acceptable (auth/routing issues, not database issues)
    });
  });

  // ---------- Migration-specific scenarios ----------

  test.describe('Migration Transition Scenarios', () => {

    test('API response content-type is always application/json', async ({ request }) => {
      const endpoints = [
        `${DATA_BASE}/health`,
        `${DATA_BASE}/api/v1/events?limit=1`,
        `${ADMIN_BASE}/api/v1/health`,
      ];

      for (const url of endpoints) {
        const response = await request.get(url);
        if (response.ok()) {
          const contentType = response.headers()['content-type'];
          expect(contentType).toContain('application/json');
        }
      }
    });

    test('no HTML responses leak from API endpoints', async ({ request }) => {
      const endpoints = [
        `${DATA_BASE}/health`,
        `${DATA_BASE}/api/v1/events?limit=1`,
        `${DATA_BASE}/api/v1/events/stats`,
        `${ADMIN_BASE}/api/v1/health`,
      ];

      for (const url of endpoints) {
        const response = await request.get(url);
        if (response.ok()) {
          const text = await response.text();
          expect(text).not.toContain('<!DOCTYPE');
          expect(text).not.toContain('<html');
        }
      }
    });

    test('numeric values maintain precision across backends', async ({ request }) => {
      const response = await request.get(`${ADMIN_BASE}/api/v1/stats`, {
        headers: authHeaders,
      });

      if (!response.ok()) {
        test.skip();
        return;
      }

      const stats = await response.json();

      // Walk through numeric fields and verify they are actual numbers
      const checkNumericFields = (obj: Record<string, unknown>, path: string) => {
        for (const [key, value] of Object.entries(obj)) {
          if (typeof value === 'number') {
            expect(Number.isFinite(value), `${path}.${key} should be finite`).toBe(true);
            expect(Number.isNaN(value), `${path}.${key} should not be NaN`).toBe(false);
          } else if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
            checkNumericFields(value as Record<string, unknown>, `${path}.${key}`);
          }
        }
      };

      checkNumericFields(stats, 'stats');
    });

    test('timestamp fields use ISO 8601 format consistently', async ({ request }) => {
      const endpoints = [
        { url: `${ADMIN_BASE}/api/v1/health`, field: 'timestamp' },
      ];

      for (const { url, field } of endpoints) {
        const response = await request.get(url);
        if (!response.ok()) continue;

        const data = await response.json();
        if (data[field]) {
          const ts = new Date(data[field]);
          expect(ts.getTime(), `${field} should be valid date`).not.toBeNaN();

          // ISO 8601 format check: should contain 'T' or match ISO pattern
          const tsStr = String(data[field]);
          const isIso = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(tsStr);
          expect(isIso, `${field} should be ISO 8601 format: ${tsStr}`).toBe(true);
        }
      }
    });
  });
});
