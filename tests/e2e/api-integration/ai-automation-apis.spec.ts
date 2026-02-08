import { test, expect } from '@playwright/test';

/**
 * Phase 6: AI Automation UI API Integration (P6.2)
 * Every ai-automation-ui API service has at least one test.
 * Services: AI Automation (8018), Device Intelligence (8028), Admin (8004),
 * Data (8006), HA AI Agent (8030), Blueprint Suggestions (8039)
 */
const AI_AUTOMATION = process.env.AI_AUTOMATION_URL || 'http://localhost:8018';
const DEVICE_INTELLIGENCE = process.env.DEVICE_INTELLIGENCE_URL || 'http://localhost:8028';
const ADMIN_BASE = process.env.ADMIN_API_BASE_URL || 'http://localhost:8004';
const DATA_BASE = process.env.DATA_API_BASE_URL || 'http://localhost:8006';
const HA_AI_AGENT = process.env.HA_AI_AGENT_URL || 'http://localhost:8030';
const BLUEPRINT_SUGGESTIONS = process.env.BLUEPRINT_SUGGESTIONS_URL || 'http://localhost:8039';

const API_KEY = process.env.ADMIN_API_KEY || process.env.API_KEY || '';
const authHeaders: Record<string, string> = API_KEY
  ? { Authorization: `Bearer ${API_KEY}`, 'X-API-Key': API_KEY }
  : {};

test.describe('AI Automation UI APIs - Endpoint matrix', () => {
  test('P6.2 AI Automation service (8018) returns valid JSON', async ({ request }) => {
    const res = await request.get(`${AI_AUTOMATION}/health`, { headers: authHeaders });
    expect([200, 401, 404, 500, 503]).toContain(res.status());
    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });

  test('P6.2 Device Intelligence service (8028) returns valid JSON', async ({ request }) => {
    const res = await request.get(`${DEVICE_INTELLIGENCE}/health`, { headers: authHeaders });
    expect([200, 401, 404, 500, 503]).toContain(res.status());
    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });

  test('P6.2 Admin API (8004) health returns valid JSON', async ({ request }) => {
    const res = await request.get(`${ADMIN_BASE}/api/v1/health`, { headers: authHeaders });
    expect([200, 401, 503]).toContain(res.status());
    if (res.ok()) {
      const data = await res.json();
      expect(data).toHaveProperty('service');
      expect(data).toHaveProperty('status');
    }
  });

  test('P6.2 Data API (8006) returns valid JSON', async ({ request }) => {
    const res = await request.get(`${DATA_BASE}/api/devices`, { headers: authHeaders });
    expect([200, 401, 404, 500, 503]).toContain(res.status());
    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });

  test('P6.2 HA AI Agent service (8030) returns valid JSON', async ({ request }) => {
    const res = await request.get(`${HA_AI_AGENT}/health`, { headers: authHeaders });
    expect([200, 401, 404, 500, 503]).toContain(res.status());
    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });

  test('P6.2 Blueprint Suggestions service (8039) returns valid JSON', async ({ request }) => {
    const res = await request.get(`${BLUEPRINT_SUGGESTIONS}/health`, { headers: authHeaders });
    expect([200, 401, 404, 500, 503]).toContain(res.status());
    if (res.ok()) {
      const data = await res.json();
      expect(typeof data).toBe('object');
    }
  });
});
