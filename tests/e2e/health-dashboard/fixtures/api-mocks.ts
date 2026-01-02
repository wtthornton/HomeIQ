import type { MockResponse } from '../../../shared/helpers/api-helpers';
import { mockServices, mockDevices, mockEvents, mockMetrics, mockAlerts, mockSportsData, mockAnalyticsData } from './test-data';

/**
 * Health Dashboard API Mocks
 * Pre-configured API response mocks for Health Dashboard endpoints
 */

export const healthMocks: Record<string, MockResponse> = {
  '/api/health': {
    status: 200,
    body: {
      status: 'healthy',
      services: mockServices,
      timestamp: new Date().toISOString(),
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
};

export const errorMocks: Record<string, MockResponse> = {
  '/api/health': {
    status: 503,
    body: {
      error: 'Service Unavailable',
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
};

export const loadingMocks: Record<string, MockResponse> = {
  '/api/health': {
    status: 200,
    body: {
      status: 'loading',
      services: [],
    },
    delay: 5000, // Simulate slow response
  },
};
