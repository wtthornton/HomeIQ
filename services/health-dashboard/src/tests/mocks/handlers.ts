import { http, HttpResponse } from 'msw';

// Mock API response handlers for testing
export const handlers = [
  // Health endpoint (used by useHealth hook)
  http.get('http://localhost/api/health', () => {
    return HttpResponse.json({
      overall_status: 'healthy',
      timestamp: new Date().toISOString(),
      ingestion_service: {
        websocket_connection: {
          is_connected: true,
          connection_attempts: 5,
        },
        event_processing: {
          status: 'healthy',
          events_per_minute: 42,
          total_events: 12345,
          error_rate: 0.5,
        },
        influxdb_storage: {
          is_connected: true,
          write_errors: 0,
        },
        weather_enrichment: {
          api_calls: 150,
        },
      },
    });
  }),

  // Enhanced health endpoint
  http.get('http://localhost/api/v1/health', () => {
    return HttpResponse.json({
      overall_status: 'healthy',
      timestamp: new Date().toISOString(),
      ingestion_service: {
        websocket_connection: {
          is_connected: true,
          connection_attempts: 5,
        },
        event_processing: {
          status: 'healthy',
          events_per_minute: 42,
          total_events: 12345,
          error_rate: 0.5,
        },
        influxdb_storage: {
          is_connected: true,
          write_errors: 0,
        },
        weather_enrichment: {
          api_calls: 150,
        },
      },
    });
  }),

  // Statistics endpoint (used by useStatistics hook)
  http.get('http://localhost/api/v1/stats', () => {
    return HttpResponse.json({
      total_events: 12345,
      events_per_minute: 42,
      error_rate: 0.5,
      uptime_hours: 24.5,
    });
  }),

  // Data sources endpoint
  http.get('/api/v1/data-sources', () => {
    return HttpResponse.json({
      weather: { status: 'active', last_update: new Date().toISOString() },
      carbon: { status: 'active', last_update: new Date().toISOString() },
      sports: { status: 'active', last_update: new Date().toISOString() },
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
          id: 'enrichment',
          name: 'Enrichment Pipeline',
          status: 'healthy',
          dependencies: ['influxdb'],
        },
      ],
    });
  }),
];
