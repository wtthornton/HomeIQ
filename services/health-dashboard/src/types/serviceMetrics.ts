/**
 * Service Metrics Type Definitions
 * 
 * Core types for service-specific metrics system
 */

/**
 * Unified service metrics structure
 */
export interface ServiceMetrics {
  serviceId: string;
  timestamp: string; // ISO 8601
  operational: OperationalMetrics;
  performance: PerformanceMetrics;
  errors: ErrorMetrics;
  resources: ResourceMetrics;
  dependencies?: DependencyMetrics;
  [key: string]: any; // Service-specific extensions
}

export interface OperationalMetrics {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'paused';
  uptime?: number; // seconds
  uptimeHuman?: string; // "1h 23m 45s"
  lastCheck?: string; // ISO 8601
  version?: string;
  [key: string]: any;
}

export interface PerformanceMetrics {
  requestsPerMinute?: number;
  averageResponseTime?: number; // milliseconds
  p95ResponseTime?: number;
  p99ResponseTime?: number;
  totalRequests?: number;
  eventsPerMinute?: number;
  queriesPerMinute?: number;
  [key: string]: any;
}

export interface ErrorMetrics {
  errorRate?: number; // percentage (0-100)
  totalErrors?: number;
  lastError?: string;
  failedConnections?: number;
  circuitBreakerState?: 'closed' | 'open' | 'half-open';
  failureCount?: number;
  [key: string]: any;
}

export interface ResourceMetrics {
  memoryMB?: number;
  memoryPercent?: number;
  cpuPercent?: number;
  diskUsageMB?: number;
  [key: string]: any;
}

export interface DependencyMetrics {
  dependencies: DependencyHealth[];
  overallStatus: 'healthy' | 'degraded' | 'unhealthy';
}

export interface DependencyHealth {
  name: string;
  type: 'database' | 'api' | 'service' | 'external';
  status: 'healthy' | 'degraded' | 'unhealthy';
  responseTimeMs?: number;
  lastCheck?: string;
  message?: string;
}

/**
 * Metric status
 */
export type MetricStatus = 'good' | 'warning' | 'error' | 'unknown';

/**
 * Service-specific metrics types
 */
export interface WebSocketIngestionMetrics extends ServiceMetrics {
  connection: {
    isConnected: boolean;
    connectionAttempts: number;
    successfulConnections: number;
    failedConnections: number;
    lastConnection: string;
    currentState: 'connected' | 'disconnected' | 'connecting';
  };
  subscription: {
    isSubscribed: boolean;
    totalEvents: number;
    eventsPerMinute: number;
    lastEvent: string;
  };
  influxdb: {
    isConnected: boolean;
    lastWriteTime: string;
    writeErrors: number;
  };
}
