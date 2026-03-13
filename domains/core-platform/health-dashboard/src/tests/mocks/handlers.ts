import { http, HttpResponse } from 'msw';

// Mock API response handlers for testing
export const handlers = [
  // Health endpoint (used by useHealth hook)
  http.get('/api/health', () => {
    return HttpResponse.json({
      service: 'websocket-ingestion',
      status: 'healthy',
      timestamp: new Date().toISOString(),
      uptime_seconds: 86400,
      version: '1.0.0',
      dependencies: [],
      metrics: {
        uptime_seconds: 86400,
        uptime_human: '24h',
        start_time: new Date().toISOString(),
        current_time: new Date().toISOString(),
      },
    });
  }),

  // Enhanced health endpoint
  http.get('/api/v1/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      service: 'websocket-ingestion',
      timestamp: new Date().toISOString(),
      uptime_seconds: 86400,
      version: '1.0.0',
      dependencies: [],
      metrics: {
        uptime_seconds: 86400,
        uptime_human: '24h',
        start_time: new Date().toISOString(),
        current_time: new Date().toISOString(),
      },
    });
  }),

  // Statistics endpoint (used by useStatistics hook)
  http.get('/api/v1/stats', () => {
    return HttpResponse.json({
      timestamp: new Date().toISOString(),
      period: '1h',
      metrics: {
        'websocket-ingestion': {
          events_per_minute: 42,
          error_rate: 0.5,
          response_time_ms: 15,
          connection_attempts: 5,
          total_events_received: 12345,
        },
      },
      trends: {},
      alerts: [],
      source: 'mock',
    });
  }),

  // Data sources endpoint
  http.get('/api/v1/data-sources', () => {
    return HttpResponse.json({
      weather: { status: 'active', last_update: new Date().toISOString() },
      carbon: { status: 'active', last_update: new Date().toISOString() },
      sports: { status: 'active', last_update: new Date().toISOString() },
      blueprintIndex: { status: 'active', last_update: new Date().toISOString() },
      ruleRecommendation: { status: 'active', last_update: new Date().toISOString() },
    });
  }),

  // Services endpoint
  http.get('/api/v1/services', () => {
    return HttpResponse.json({
      services: [
        {
          id: 'websocket',
          name: 'WebSocket Ingestion',
          status: 'healthy',
          dependencies: ['influxdb'],
        },
        {
          id: 'data-api',
          name: 'Data API',
          status: 'healthy',
          dependencies: ['influxdb'],
        },
      ],
    });
  }),

  // Services health endpoint (used by Dashboard)
  http.get('/api/v1/health/services', () => {
    return HttpResponse.json({});
  }),

  // Health groups endpoint
  http.get('/api/v1/health/groups', () => {
    return HttpResponse.json({});
  }),

  // Active alerts endpoint (used by Dashboard)
  http.get('/api/v1/alerts/active', () => {
    return HttpResponse.json([]);
  }),

  // Alerts summary endpoint
  http.get('/api/v1/alerts/summary', () => {
    return HttpResponse.json({ total: 0, critical: 0, warning: 0, info: 0 });
  }),

  // Docker containers endpoint
  http.get('/api/v1/docker/containers', () => {
    return HttpResponse.json([]);
  }),

  // Devices endpoint
  http.get('/api/devices', () => {
    return HttpResponse.json({ devices: [] });
  }),

  // Entities endpoint
  http.get('/api/entities', () => {
    return HttpResponse.json({ entities: [] });
  }),

  // Activity endpoint
  http.get('/api/v1/activity', () => {
    return HttpResponse.json([]);
  }),

  // Energy endpoint
  http.get('/api/v1/energy', () => {
    return HttpResponse.json({
      current: { consumption_watts: 1200, solar_watts: 800, grid_watts: 400 },
      daily: [],
    });
  }),

  // Events endpoint
  http.get('/api/v1/events', () => {
    return HttpResponse.json({ events: [], total: 0 });
  }),

  // Integrations endpoint
  http.get('/api/v1/integrations', () => {
    return HttpResponse.json({ integrations: [] });
  }),

  // RAG status endpoint
  http.get('/api/v1/rag/status', () => {
    return HttpResponse.json({ status: 'available', documents: 0, last_indexed: null });
  }),

  // Memory status endpoint
  http.get('/api/v1/memory/status', () => {
    return HttpResponse.json({ status: 'available', entries: 0 });
  }),

  // Configuration endpoint
  http.get('/api/v1/configuration', () => {
    return HttpResponse.json({ settings: {} });
  }),
];

// Error response handlers — use with server.use() in individual tests
export const errorHandlers = {
  health500: http.get('/api/health', () => {
    return HttpResponse.json({ error: 'Internal server error' }, { status: 500 });
  }),
  health401: http.get('/api/health', () => {
    return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }),
  stats404: http.get('/api/v1/stats', () => {
    return HttpResponse.json({ error: 'Not found' }, { status: 404 });
  }),
  services503: http.get('/api/v1/services', () => {
    return HttpResponse.json({ error: 'Service unavailable' }, { status: 503 });
  }),
  devices500: http.get('/api/devices', () => {
    return HttpResponse.json({ error: 'Internal server error' }, { status: 500 });
  }),
  networkError: http.get('/api/health', () => {
    return HttpResponse.error();
  }),
};
