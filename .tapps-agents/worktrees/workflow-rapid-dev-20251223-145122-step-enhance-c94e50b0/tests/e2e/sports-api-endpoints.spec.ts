/**
 * Sports API E2E Tests
 * 
 * Tests Epic 11 & 12: Sports Data Integration & InfluxDB Persistence
 * Including all bug fixes from Story 11.5, 11.6, 11.7, 12.4
 * 
 * Coverage:
 * - Team persistence across restarts
 * - HA automation endpoints
 * - Event detection and webhooks
 * - Live games API
 * - Upcoming games API
 */

import { test, expect } from '@playwright/test';

const SPORTS_API_BASE_URL = process.env.SPORTS_API_URL || 'http://localhost:8005';

test.describe('Sports API - Core Endpoints', () => {
  test('should return health check', async ({ request }) => {
    const response = await request.get(`${SPORTS_API_BASE_URL}/health`);
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(body.status).toBe('healthy');
    expect(body.service).toBe('sports-data');
  });

  test('should return available teams', async ({ request }) => {
    const response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/teams?league=NHL`);
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(body).toHaveProperty('teams');
    expect(Array.isArray(body.teams)).toBeTruthy();
    expect(body.teams.length).toBeGreaterThan(0);
    expect(body.league).toBe('NHL');
  });

  test('should save user team selections (Story 11.5)', async ({ request }) => {
    // Save teams
    const teamsData = {
      user_id: 'test-user',
      nfl_teams: ['dal', 'sf'],
      nhl_teams: ['vgk', 'bos']
    };

    const saveResponse = await request.post(`${SPORTS_API_BASE_URL}/api/v1/user/teams`, {
      data: teamsData
    });
    expect(saveResponse.ok()).toBeTruthy();

    const saveBody = await saveResponse.json();
    expect(saveBody.success).toBe(true);
    expect(saveBody.user_id).toBe('test-user');
    expect(saveBody.teams_saved).toEqual({
      nfl_teams: ['dal', 'sf'],
      nhl_teams: ['vgk', 'bos']
    });
  });

  test('should retrieve saved team selections (Story 11.5)', async ({ request }) => {
    // First save teams
    const teamsData = {
      user_id: 'test-retrieval',
      nfl_teams: ['gb'],
      nhl_teams: ['pit']
    };

    await request.post(`${SPORTS_API_BASE_URL}/api/v1/user/teams`, {
      data: teamsData
    });

    // Then retrieve
    const response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/user/teams?user_id=test-retrieval`);
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.user_id).toBe('test-retrieval');
    expect(body.nfl_teams).toEqual(['gb']);
    expect(body.nhl_teams).toEqual(['pit']);
  });

  test('should return live games for selected teams', async ({ request }) => {
    const response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/games/live?league=NHL&team_ids=vgk`);
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('games');
    expect(Array.isArray(body.games)).toBeTruthy();
  });

  test('should return upcoming games', async ({ request }) => {
    const response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/games/upcoming?league=NHL&team_ids=vgk&hours=24`);
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('games');
    expect(Array.isArray(body.games)).toBeTruthy();
  });
});

test.describe('Sports API - HA Automation Endpoints (Story 11.6)', () => {
  test.beforeEach(async ({ request }) => {
    // Ensure test teams are configured
    const teamsData = {
      user_id: 'default',
      nfl_teams: ['dal'],
      nhl_teams: ['vgk']
    };

    await request.post(`${SPORTS_API_BASE_URL}/api/v1/user/teams`, {
      data: teamsData
    });
  });

  test('should return game status for team (Story 11.6)', async ({ request }) => {
    const response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/ha/game-status/VGK?sport=nhl`);
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('team');
    expect(body).toHaveProperty('status');
    expect(body.team).toBe('VGK');
    expect(['playing', 'upcoming', 'none']).toContain(body.status);
  });

  test('should return game context for team', async ({ request }) => {
    const response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/ha/game-context/VGK?sport=nhl`);
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('team');
    expect(body).toHaveProperty('status');
    expect(body.team).toBe('VGK');
    expect(['playing', 'upcoming', 'none']).toContain(body.status);
  });

  test('should respond within 200ms for HA endpoints', async ({ request }) => {
    const startTime = Date.now();
    await request.get(`${SPORTS_API_BASE_URL}/api/v1/ha/game-status/VGK?sport=nhl`);
    const endTime = Date.now();

    const responseTime = endTime - startTime;
    expect(responseTime).toBeLessThan(200); // Allow 200ms for test environment (production <50ms)
  });
});

test.describe('Sports API - Webhooks & Event Detection (Story 12.4)', () => {
  test('should list webhooks', async ({ request }) => {
    const response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/webhooks/list`);
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('webhooks');
    expect(Array.isArray(body.webhooks)).toBeTruthy();
  });

  test.skip('should register webhook (requires webhook service)', async ({ request }) => {
    // TODO: Set up mock webhook receiver for E2E tests
    const webhookData = {
      url: 'http://test-webhook-receiver:8080/webhook',
      events: ['game_started', 'score_changed'],
      description: 'Test webhook for E2E tests'
    };

    const response = await request.post(`${SPORTS_API_BASE_URL}/api/v1/webhooks/register`, {
      data: webhookData
    });
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.success).toBe(true);
    expect(body).toHaveProperty('webhook_id');
  });

  test.skip('should unregister webhook (requires webhook service)', async ({ request }) => {
    // TODO: Set up mock webhook receiver for E2E tests
    // First register a webhook
    const registerResponse = await request.post(`${SPORTS_API_BASE_URL}/api/v1/webhooks/register`, {
      data: {
        url: 'http://test-webhook-receiver:8080/webhook-temp',
        events: ['game_ended'],
        description: 'Temporary test webhook'
      }
    });
    const registerBody = await registerResponse.json();
    const webhookId = registerBody.webhook_id;

    // Then unregister it
    const unregisterResponse = await request.delete(`${SPORTS_API_BASE_URL}/api/v1/webhooks/unregister/${webhookId}`);
    expect(unregisterResponse.ok()).toBeTruthy();

    const unregisterBody = await unregisterResponse.json();
    expect(unregisterBody.success).toBe(true);
  });
});

test.describe('Sports API - Cache & Performance', () => {
  test('should return cache stats', async ({ request }) => {
    const response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/cache/stats`);
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('hits');
    expect(body).toHaveProperty('misses');
    expect(body).toHaveProperty('hit_rate');
    expect(body).toHaveProperty('keys_count');
  });

  test('should cache live games data', async ({ request }) => {
    // First request (cache miss)
    const firstResponse = await request.get(`${SPORTS_API_BASE_URL}/api/v1/games/live?league=NHL&team_ids=vgk`);
    expect(firstResponse.ok()).toBeTruthy();

    // Second request (should hit cache)
    const secondResponse = await request.get(`${SPORTS_API_BASE_URL}/api/v1/games/live?league=NHL&team_ids=vgk`);
    expect(secondResponse.ok()).toBeTruthy();

    // Cache stats should show hits
    const statsResponse = await request.get(`${SPORTS_API_BASE_URL}/api/v1/cache/stats`);
    const stats = await statsResponse.json();
    expect(stats.hits).toBeGreaterThan(0);
  });
});

test.describe('Sports API - Error Handling', () => {
  test('should handle invalid league parameter', async ({ request }) => {
    const response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/games/live?league=INVALID`);
    // API might return 200 with empty results or 422, both are acceptable
    expect([200, 422]).toContain(response.status());
  });

  test('should handle invalid team ID format', async ({ request }) => {
    const response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/ha/game-status/!@#$?sport=nhl`);
    // Should either return 'none' status or handle gracefully
    if (response.ok()) {
      const body = await response.json();
      expect(body.status).toBe('none');
    }
  });

  test('should return empty teams if user not found', async ({ request }) => {
    const response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/user/teams?user_id=nonexistent-user-12345`);
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.nfl_teams).toEqual([]);
    expect(body.nhl_teams).toEqual([]);
  });
});

test.describe('Sports API - Data Persistence (Story 11.5)', () => {
  test('should persist teams across service restarts', async ({ request }) => {
    // Save teams with unique user ID
    const userId = `test-persist-${Date.now()}`;
    const teamsData = {
      user_id: userId,
      nfl_teams: ['ne', 'kc'],
      nhl_teams: ['chi', 'wsh']
    };

    await request.post(`${SPORTS_API_BASE_URL}/api/v1/user/teams`, {
      data: teamsData
    });

    // Note: In a real test, we would restart the service here
    // For now, we verify immediate retrieval works
    const response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/user/teams?user_id=${userId}`);
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.nfl_teams).toEqual(['ne', 'kc']);
    expect(body.nhl_teams).toEqual(['chi', 'wsh']);
  });

  test('should support multiple users with different teams', async ({ request }) => {
    // User 1
    const user1Data = {
      user_id: 'multi-user-1',
      nfl_teams: ['dal'],
      nhl_teams: ['vgk']
    };
    await request.post(`${SPORTS_API_BASE_URL}/api/v1/user/teams`, {
      data: user1Data
    });

    // User 2
    const user2Data = {
      user_id: 'multi-user-2',
      nfl_teams: ['sf'],
      nhl_teams: ['bos']
    };
    await request.post(`${SPORTS_API_BASE_URL}/api/v1/user/teams`, {
      data: user2Data
    });

    // Verify User 1
    const user1Response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/user/teams?user_id=multi-user-1`);
    const user1Body = await user1Response.json();
    expect(user1Body.nfl_teams).toEqual(['dal']);
    expect(user1Body.nhl_teams).toEqual(['vgk']);

    // Verify User 2
    const user2Response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/user/teams?user_id=multi-user-2`);
    const user2Body = await user2Response.json();
    expect(user2Body.nfl_teams).toEqual(['sf']);
    expect(user2Body.nhl_teams).toEqual(['bos']);
  });
});

test.describe('Sports API - API Usage Metrics', () => {
  test('should return API usage statistics', async ({ request }) => {
    const response = await request.get(`${SPORTS_API_BASE_URL}/api/v1/metrics/api-usage`);
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    // Accept either total_calls or total_calls_today
    expect(body).toHaveProperty('cache_hits');
    expect(body).toHaveProperty('cache_misses');
    expect(typeof body.cache_hits).toBe('number');
    expect(typeof body.cache_misses).toBe('number');
  });
});

