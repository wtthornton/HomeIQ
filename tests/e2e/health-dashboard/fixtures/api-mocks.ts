import type { MockResponse } from '../../../shared/helpers/api-helpers';
import { mockServices, mockDevices, mockEvents, mockMetrics, mockAlerts, mockSportsData, mockAnalyticsData, mockSynergies } from './test-data';

/**
 * Health Dashboard API Mocks
 * Pre-configured API response mocks for Health Dashboard endpoints.
 *
 * Mock shapes align with actual admin-api (8004) and data-api (8006) contracts:
 *   /api/v1/health  → { service, status, timestamp, dependencies[] }
 *   /api/v1/stats   → { timestamp, period, metrics[], trends[], alerts[], services{} }
 */

export const healthMocks: Record<string, MockResponse> = {
  '/api/health': {
    status: 200,
    body: {
      service: 'admin-api',
      status: 'healthy',
      timestamp: '2026-01-01T00:00:00.000Z',
      dependencies: mockServices.map((s) => ({
        name: s.name,
        status: s.status,
        response_time_ms: 25,
      })),
    },
  },
  '/api/services': {
    status: 200,
    body: {
      services: mockServices,
      total: mockServices.length,
    },
  },
  '/api/devices': {
    status: 200,
    body: {
      devices: mockDevices,
      total: mockDevices.length,
    },
  },
  '/api/entities': {
    status: 200,
    body: {
      entities: mockDevices.flatMap((d) => d.entities),
      total: mockDevices.reduce((sum, d) => sum + d.entities.length, 0),
    },
  },
  '/api/events': {
    status: 200,
    body: {
      events: mockEvents,
      total: mockEvents.length,
    },
  },
  '/api/metrics': {
    status: 200,
    body: mockMetrics,
  },
  '/api/alerts': {
    status: 200,
    body: {
      alerts: mockAlerts,
      total: mockAlerts.length,
    },
  },
  '/api/sports': {
    status: 200,
    body: mockSportsData,
  },
  '/api/analytics': {
    status: 200,
    body: mockAnalyticsData,
  },
  '/api/v1/synergies/list': {
    status: 200,
    body: { data: { synergies: mockSynergies } },
  },
  // v1 API variants (match actual admin-api response shapes)
  '/api/v1/health': {
    status: 200,
    body: {
      service: 'admin-api',
      status: 'healthy',
      timestamp: '2026-01-01T00:00:00.000Z',
      dependencies: mockServices.map((s) => ({
        name: s.name,
        status: s.status,
        response_time_ms: 25,
      })),
    },
  },
  '/api/v1/health/services': {
    status: 200,
    body: { services: mockServices, total: mockServices.length },
  },
  '/api/v1/stats': {
    status: 200,
    body: {
      timestamp: '2026-01-01T00:00:00.000Z',
      period: '24h',
      metrics: [
        { name: 'total_events', value: mockMetrics.total_events },
        { name: 'active_devices', value: mockMetrics.active_devices },
      ],
      trends: [],
      alerts: [],
      services: Object.fromEntries(
        mockServices.map((s) => [s.id, { status: s.status, port: s.port }])
      ),
    },
  },
  '/api/v1/alerts/active': {
    status: 200,
    body: { alerts: mockAlerts, total: mockAlerts.length },
  },
  '/api/v1/events': {
    status: 200,
    body: { events: mockEvents, total: mockEvents.length },
  },
  '/api/v1/docker/containers': {
    status: 200,
    body: { containers: [], total: 0 },
  },
  '/api/v1/real-time-metrics': {
    status: 200,
    body: mockMetrics,
  },
};

export const errorMocks: Record<string, MockResponse> = {
  '/api/health': {
    status: 503,
    body: {
      service: 'admin-api',
      status: 'unhealthy',
      timestamp: '2026-01-01T00:00:00.000Z',
      message: 'Unable to connect to services',
    },
  },
  '/api/services': {
    status: 500,
    body: {
      error: 'Internal Server Error',
      message: 'Failed to fetch services',
    },
  },
  '/api/v1/health': {
    status: 503,
    body: {
      service: 'admin-api',
      status: 'unhealthy',
      timestamp: '2026-01-01T00:00:00.000Z',
      message: 'Unable to connect to services',
    },
  },
  '/api/v1/stats': {
    status: 500,
    body: {
      error: 'Internal Server Error',
      message: 'Failed to fetch statistics',
    },
  },
};

export const loadingMocks: Record<string, MockResponse> = {
  '/api/health': {
    status: 200,
    body: {
      service: 'admin-api',
      status: 'healthy',
      timestamp: '2026-01-01T00:00:00.000Z',
      dependencies: [],
    },
    delay: 5000,
  },
};
