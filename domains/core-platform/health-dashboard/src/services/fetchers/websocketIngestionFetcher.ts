/**
 * WebSocket Ingestion Service Metrics Fetcher
 * 
 * Fetches and transforms metrics from websocket-ingestion service
 * 
 * Prototype: Basic implementation
 */

import type { WebSocketIngestionMetrics } from '../../types/serviceMetrics';

const WEBSOCKET_INGESTION_URL = process.env.REACT_APP_WEBSOCKET_INGESTION_URL || 'http://localhost:8001';
const FETCH_TIMEOUT = 5000; // 5 seconds

/**
 * Health endpoint response structure
 */
interface HealthResponse {
  status?: string;
  service?: string;
  uptime?: string;
  uptime_seconds?: number;
  timestamp?: string;
  connection?: {
    is_running?: boolean;
    connection_attempts?: number;
    successful_connections?: number;
    failed_connections?: number;
    last_successful?: string;
    last_error?: string;
    current_state?: string;
  };
  subscription?: {
    is_subscribed?: boolean;
    total_events_received?: number;
    event_rate_per_minute?: number;
    last_event?: string;
    last_event_time?: string;
  };
  circuit_breaker?: {
    state?: string;
    failure_count?: number;
  };
  performance?: {
    memory_mb?: number;
    cpu_percent?: number;
  };
}

/**
 * Transform health response to operational metrics
 */
function transformOperationalMetrics(data: HealthResponse, serviceId: string): WebSocketIngestionMetrics['operational'] {
  const isHealthy = data.status === 'healthy' || data.connection?.is_running === true;
  
  return {
    status: isHealthy ? 'healthy' : 'unhealthy',
    uptime: data.uptime_seconds ?? 0,
    uptimeHuman: data.uptime ?? '0:00:00',
    lastCheck: data.timestamp ?? new Date().toISOString(),
    connectionStatus: data.connection?.is_running ? 'connected' : 'disconnected',
    connectionAttempts: data.connection?.connection_attempts ?? 0,
    lastConnection: data.connection?.last_successful ?? data.timestamp ?? new Date().toISOString(),
  };
}

/**
 * Transform health response to performance metrics
 */
function transformPerformanceMetrics(data: HealthResponse): WebSocketIngestionMetrics['performance'] {
  return {
    eventsPerMinute: data.subscription?.event_rate_per_minute ?? 0,
    totalEvents: data.subscription?.total_events_received ?? 0,
    lastEvent: data.subscription?.last_event_time ?? data.subscription?.last_event ?? null,
  };
}

/**
 * Transform health response to error metrics
 */
function transformErrorMetrics(data: HealthResponse): WebSocketIngestionMetrics['errors'] {
  return {
    errorRate: 0, // Calculate if available
    failedConnections: data.connection?.failed_connections ?? 0,
    lastError: data.connection?.last_error ?? null,
    circuitBreakerState: (data.circuit_breaker?.state as 'closed' | 'open' | 'half-open') ?? 'closed',
    failureCount: data.circuit_breaker?.failure_count ?? 0,
  };
}

/**
 * Transform health response to resource metrics
 */
function transformResourceMetrics(data: HealthResponse): WebSocketIngestionMetrics['resources'] {
  return {
    memoryMB: data.performance?.memory_mb ?? 0,
    cpuPercent: data.performance?.cpu_percent ?? 0,
  };
}

/**
 * Transform health response to connection metrics
 */
function transformConnectionMetrics(data: HealthResponse): WebSocketIngestionMetrics['connection'] {
  return {
    isConnected: data.connection?.is_running ?? false,
    connectionAttempts: data.connection?.connection_attempts ?? 0,
    successfulConnections: data.connection?.successful_connections ?? 0,
    failedConnections: data.connection?.failed_connections ?? 0,
    lastConnection: data.connection?.last_successful ?? data.timestamp ?? new Date().toISOString(),
    currentState: data.connection?.is_running ? 'connected' : 'disconnected',
  };
}

/**
 * Transform health response to subscription metrics
 */
function transformSubscriptionMetrics(data: HealthResponse): WebSocketIngestionMetrics['subscription'] {
  return {
    isSubscribed: data.subscription?.is_subscribed ?? false,
    totalEvents: data.subscription?.total_events_received ?? 0,
    eventsPerMinute: data.subscription?.event_rate_per_minute ?? 0,
    lastEvent: data.subscription?.last_event_time ?? data.subscription?.last_event ?? new Date().toISOString(),
  };
}

/**
 * Fetch and transform WebSocket Ingestion service metrics
 * 
 * @param serviceId - The service identifier
 * @returns Promise resolving to WebSocketIngestionMetrics or null on error
 */
export async function fetchWebSocketIngestionMetrics(
  serviceId: string
): Promise<WebSocketIngestionMetrics | null> {
  try {
    const response = await fetch(`${WEBSOCKET_INGESTION_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: AbortSignal.timeout(FETCH_TIMEOUT),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: HealthResponse = await response.json();

    // Transform response to unified format using helper functions
    const metrics: WebSocketIngestionMetrics = {
      serviceId,
      timestamp: new Date().toISOString(),
      operational: transformOperationalMetrics(data, serviceId),
      performance: transformPerformanceMetrics(data),
      errors: transformErrorMetrics(data),
      resources: transformResourceMetrics(data),
      connection: transformConnectionMetrics(data),
      subscription: transformSubscriptionMetrics(data),
      influxdb: {
        isConnected: true, // TODO: Get from dependency check
        lastWriteTime: new Date().toISOString(), // TODO: Get actual write time
        writeErrors: 0, // TODO: Get actual error count
      },
    };

    return metrics;
  } catch (error) {
    console.error(`Failed to fetch WebSocket Ingestion metrics:`, error);
    return null;
  }
}
