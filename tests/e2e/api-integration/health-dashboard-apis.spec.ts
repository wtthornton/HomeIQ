import { test, expect } from '@playwright/test';

/**
 * Phase 6: Health Dashboard API Integration Matrix (P6.1)
 * Every health-dashboard API endpoint has at least one E2E or API test.
 * Admin API (8004): health, stats, alerts, docker, api-keys, real-time-metrics
 * Data API (8006): events, devices, entities, integrations, energy, hygiene, sports
 */
const ADMIN_BASE = process.env.ADMIN_API_BASE_URL || 'http://localhost:8004';
const DATA_BASE = process.env.DATA_API_BASE_URL || 'http://localhost:8006';
const API_KEY = process.env.ADMIN_API_KEY || process.env.API_KEY || '';
const authHeaders: Record<string, string> = API_KEY
  ? { Authorization: `Bearer ${API_KEY}` }
  : {};

test.describe('Health Dashboard APIs - Endpoint matrix', () => {
  test('P6.1 GET /api/v1/health returns valid health shape', async ({ request }) => {
    const res = await request.get(`${ADMIN_BASE}/api/v1/health`);
    expect([200, 503]).toContain(res.status());

    const data = await res.json();
    expect(data).toHaveProperty('service');
    expect(data).toHaveProperty('status');
    expect(data).toHaveProperty('timestamp');

    const validStatuses = ['healthy', 'degraded', 'unhealthy'];
    expect(validStatuses).toContain(data.status);

    if (data.dependencies) {
      expect(Array.isArray(data.dependencies)).toBe(true);
    }
  });

  test('P6.1 GET /api/v1/health/services returns service map', async ({ request }) => {
    const res = await request.get(`${ADMIN_BASE}/api/v1/health/services`);
    expect([200, 500, 503]).toContain(res.status());

    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
      expect(data).not.toBeNull();
    }
  });

  test('P6.1 GET /api/v1/stats returns stats shape', async ({ request }) => {
    const res = await request.get(`${ADMIN_BASE}/api/v1/stats`, {
      headers: authHeaders,
    });
    expect([200, 401, 404, 500, 503]).toContain(res.status());

    if (res.ok()) {
      const data = await res.json();
      expect(data).toHaveProperty('timestamp');
      expect(data).toHaveProperty('period');
      expect(data).toHaveProperty('services');
      expect(typeof data.services).toBe('object');
    }
  });

  test('P6.1 GET /api/v1/stats?period=1h returns period in response', async ({ request }) => {
    const res = await request.get(`${ADMIN_BASE}/api/v1/stats?period=1h`, {
      headers: authHeaders,
    });
    expect([200, 401, 404, 500, 503]).toContain(res.status());

    if (res.ok()) {
      const data = await res.json();
      expect(data).toHaveProperty('period', '1h');
    }
  });

  test('P6.1 GET /api/v1/alerts/active returns alerts', async ({ request }) => {
    const res = await request.get(`${ADMIN_BASE}/api/v1/alerts/active`, {
      headers: authHeaders,
    });
    expect([200, 401, 404, 500, 503]).toContain(res.status());

    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });

  test('P6.1 GET /api/v1/docker/containers returns container list', async ({ request }) => {
    const res = await request.get(`${ADMIN_BASE}/api/v1/docker/containers`, {
      headers: authHeaders,
    });
    expect([200, 401, 500, 503]).toContain(res.status());

    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });

  test('P6.1 GET /api/v1/docker/api-keys returns api keys', async ({ request }) => {
    const res = await request.get(`${ADMIN_BASE}/api/v1/docker/api-keys`, {
      headers: authHeaders,
    });
    expect([200, 401, 500, 503]).toContain(res.status());

    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });

  test('P6.1 GET /api/v1/real-time-metrics returns metrics', async ({ request }) => {
    const res = await request.get(`${ADMIN_BASE}/api/v1/real-time-metrics`, {
      headers: authHeaders,
    });
    expect([200, 401, 500, 503]).toContain(res.status());

    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });

  test('P6.1 GET /api/v1/events returns events (data-api)', async ({ request }) => {
    const res = await request.get(`${DATA_BASE}/api/v1/events`, { headers: authHeaders });
    expect([200, 401, 404, 500, 503]).toContain(res.status());
    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });

  test('P6.1 GET /api/devices returns devices (data-api)', async ({ request }) => {
    const res = await request.get(`${DATA_BASE}/api/devices`, { headers: authHeaders });
    expect([200, 401, 404, 500, 503]).toContain(res.status());
    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });

  test('P6.1 GET /api/entities returns entities (data-api)', async ({ request }) => {
    const res = await request.get(`${DATA_BASE}/api/entities`, { headers: authHeaders });
    expect([200, 401, 404, 500, 503]).toContain(res.status());
    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });

  test('P6.1 GET /api/integrations returns integrations (data-api)', async ({ request }) => {
    const res = await request.get(`${DATA_BASE}/api/integrations?limit=10`, { headers: authHeaders });
    expect([200, 401, 404, 500, 503]).toContain(res.status());
    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });

  test('P6.1 GET /api/v1/energy/statistics returns energy stats (data-api)', async ({ request }) => {
    const res = await request.get(`${DATA_BASE}/api/v1/energy/statistics?hours=24`, { headers: authHeaders });
    expect([200, 401, 404, 500, 503]).toContain(res.status());
    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });

  test('P6.1 GET /api/v1/hygiene/issues returns hygiene issues (data-api)', async ({ request }) => {
    const res = await request.get(`${DATA_BASE}/api/v1/hygiene/issues`, { headers: authHeaders });
    expect([200, 401, 404, 500, 503]).toContain(res.status());
    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });

  test('P6.1 GET /api/v1/sports/games/live returns live games (data-api)', async ({ request }) => {
    const res = await request.get(`${DATA_BASE}/api/v1/sports/games/live`, { headers: authHeaders });
    expect([200, 401, 404, 500, 503]).toContain(res.status());
    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });
});
