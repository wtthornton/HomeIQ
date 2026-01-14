/**
 * Service Metrics Configuration
 * 
 * Centralized configuration for service-specific metrics
 * 
 * Prototype: WebSocket Ingestion configuration only
 */

import type { ServiceMetrics } from '../types/serviceMetrics';
import { fetchWebSocketIngestionMetrics } from '../services/fetchers/websocketIngestionFetcher';

export type ServiceMetricsFetcher = (
  serviceId: string
) => Promise<ServiceMetrics | null>;

export interface MetricDefinition {
  key: string;
  label: string;
  path: string; // JSON path to value (e.g., "operational.uptime")
  formatter?: (value: any) => string;
  statusThresholds?: {
    good?: number | ((value: any) => boolean);
    warning?: number | ((value: any) => boolean);
    error?: number | ((value: any) => boolean);
  };
  unit?: string;
  type?: 'number' | 'percentage' | 'time' | 'status' | 'custom';
}

export interface MetricGroupConfig {
  title: string;
  metrics: MetricDefinition[];
}

export interface ServiceMetricsConfig {
  serviceId: string;
  fetcher: ServiceMetricsFetcher;
  groups: MetricGroupConfig[];
  refreshInterval?: number;
  cacheTTL?: number;
}

/**
 * WebSocket Ingestion Metrics Configuration
 */
export const websocketIngestionConfig: ServiceMetricsConfig = {
  serviceId: 'websocket-ingestion',
  fetcher: fetchWebSocketIngestionMetrics,
  refreshInterval: 5000,
  cacheTTL: 3000,
  groups: [
    {
      title: 'Connection Status',
      metrics: [
        {
          key: 'connectionStatus',
          label: 'Connection Status',
          path: 'connection.currentState',
          type: 'status',
          formatter: (v) => v === 'connected' ? 'Connected' : 'Disconnected',
        },
        {
          key: 'connectionAttempts',
          label: 'Connection Attempts',
          path: 'connection.connectionAttempts',
          type: 'number',
        },
        {
          key: 'lastConnection',
          label: 'Last Connection',
          path: 'connection.lastConnection',
          type: 'time',
        },
      ],
    },
    {
      title: 'Event Processing',
      metrics: [
        {
          key: 'eventsPerMinute',
          label: 'Events Per Minute',
          path: 'performance.eventsPerMinute',
          type: 'number',
          unit: 'events/min',
          statusThresholds: {
            good: (v) => v > 0,
            warning: (v) => v === 0,
          },
        },
        {
          key: 'totalEvents',
          label: 'Total Events',
          path: 'subscription.totalEvents',
          type: 'number',
        },
        {
          key: 'lastEvent',
          label: 'Last Event',
          path: 'subscription.lastEvent',
          type: 'time',
        },
      ],
    },
    {
      title: 'Errors',
      metrics: [
        {
          key: 'failedConnections',
          label: 'Failed Connections',
          path: 'errors.failedConnections',
          type: 'number',
          statusThresholds: {
            good: (v) => v === 0,
            warning: (v) => v > 0 && v < 5,
            error: (v) => v >= 5,
          },
        },
        {
          key: 'circuitBreakerState',
          label: 'Circuit Breaker',
          path: 'errors.circuitBreakerState',
          type: 'status',
          formatter: (v) => {
            const state = v || 'closed';
            return state.charAt(0).toUpperCase() + state.slice(1);
          },
          statusThresholds: {
            good: (v) => v === 'closed',
            warning: (v) => v === 'half-open',
            error: (v) => v === 'open',
          },
        },
        {
          key: 'lastError',
          label: 'Last Error',
          path: 'errors.lastError',
          type: 'custom',
          formatter: (v) => v || 'None',
        },
      ],
    },
    {
      title: 'Resources',
      metrics: [
        {
          key: 'memoryMB',
          label: 'Memory Usage',
          path: 'resources.memoryMB',
          type: 'number',
          unit: 'MB',
        },
        {
          key: 'cpuPercent',
          label: 'CPU Usage',
          path: 'resources.cpuPercent',
          type: 'percentage',
          statusThresholds: {
            good: (v) => v < 50,
            warning: (v) => v >= 50 && v < 80,
            error: (v) => v >= 80,
          },
        },
      ],
    },
  ],
};

/**
 * Service metrics configuration registry
 */
export const SERVICE_METRICS_CONFIG: Record<string, ServiceMetricsConfig> = {
  'websocket-ingestion': websocketIngestionConfig,
  // Add other services here as they're implemented
};

/**
 * Get configuration for a service
 */
export function getServiceMetricsConfig(serviceId: string): ServiceMetricsConfig | null {
  return SERVICE_METRICS_CONFIG[serviceId] || null;
}
