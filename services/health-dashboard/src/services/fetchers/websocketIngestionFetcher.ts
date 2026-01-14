/**
 * WebSocket Ingestion Service Metrics Fetcher
 * 
 * Fetches and transforms metrics from websocket-ingestion service
 * 
 * Prototype: Basic implementation
 */

import type { WebSocketIngestionMetrics } from '../../types/serviceMetrics';

const WEBSOCKET_INGESTION_URL = process.env.REACT_APP_WEBSOCKET_INGESTION_URL || 'http://localhost:8001';

export async function fetchWebSocketIngestionMetrics(
  serviceId: string
): Promise<WebSocketIngestionMetrics | null> {
  try {
    const response = await fetch(`${WEBSOCKET_INGESTION_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Transform response to unified format
    const metrics: WebSocketIngestionMetrics = {
      serviceId,
      timestamp: new Date().toISOString(),
      operational: {
        status: data.connection?.is_running ? 'healthy' : 'unhealthy',
        uptime: data.uptime_seconds,
        uptimeHuman: data.uptime,
        lastCheck: data.timestamp,
        connectionStatus: data.connection?.current_state || 'unknown',
        connectionAttempts: data.connection?.connection_attempts || 0,
        lastConnection: data.connection?.last_successful || null,
      },
      performance: {
        eventsPerMinute: data.subscription?.event_rate_per_minute || 0,
        totalEvents: data.subscription?.total_events_received || 0,
        lastEvent: data.subscription?.last_event || null,
      },
      errors: {
        errorRate: 0, // Calculate if available
        failedConnections: data.connection?.failed_connections || 0,
        lastError: data.connection?.last_error || null,
        circuitBreakerState: data.circuit_breaker?.state || 'closed',
        failureCount: data.circuit_breaker?.failure_count || 0,
      },
      resources: {
        memoryMB: data.performance?.memory_mb || 0,
        cpuPercent: data.performance?.cpu_percent || 0,
      },
      connection: {
        isConnected: data.connection?.is_running || false,
        connectionAttempts: data.connection?.connection_attempts || 0,
        successfulConnections: data.connection?.successful_connections || 0,
        failedConnections: data.connection?.failed_connections || 0,
        lastConnection: data.connection?.last_successful || new Date().toISOString(),
        currentState: data.connection?.current_state || 'disconnected',
      },
      subscription: {
        isSubscribed: data.subscription?.is_subscribed || false,
        totalEvents: data.subscription?.total_events_received || 0,
        eventsPerMinute: data.subscription?.event_rate_per_minute || 0,
        lastEvent: data.subscription?.last_event || new Date().toISOString(),
      },
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
