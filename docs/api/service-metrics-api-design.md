# Service Metrics API & Data Model Design

**Created:** 2026-01-14  
**Status:** API Design - Ready for Implementation  
**Epic:** Service Management Dashboard Enhancement

## API Overview

### Purpose
Define TypeScript interfaces, data models, and API contracts for service-specific metrics system.

### API Type
**Client-Side API:** TypeScript interfaces and React hooks (no new backend endpoints required)

### Base Strategy
- Leverage existing service `/health` and `/metrics` endpoints
- Frontend aggregates and transforms service responses
- Unified data model for consistent display

## TypeScript Interfaces

### Core Metrics Types

```typescript
/**
 * Unified service metrics structure
 * All service-specific metrics are transformed to this format
 */
export interface ServiceMetrics {
  serviceId: string;
  timestamp: string; // ISO 8601
  operational: OperationalMetrics;
  performance: PerformanceMetrics;
  errors: ErrorMetrics;
  resources: ResourceMetrics;
  dependencies?: DependencyMetrics;
  // Service-specific extensions
  [key: string]: any;
}

/**
 * Operational status and basic service information
 */
export interface OperationalMetrics {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'paused';
  uptime?: number; // seconds
  uptimeHuman?: string; // "1h 23m 45s"
  lastCheck?: string; // ISO 8601
  version?: string;
  [key: string]: any; // Service-specific operational metrics
}

/**
 * Performance and throughput metrics
 */
export interface PerformanceMetrics {
  requestsPerMinute?: number;
  averageResponseTime?: number; // milliseconds
  p95ResponseTime?: number; // milliseconds
  p99ResponseTime?: number; // milliseconds
  totalRequests?: number;
  eventsPerMinute?: number;
  queriesPerMinute?: number;
  [key: string]: any; // Service-specific performance metrics
}

/**
 * Error and failure metrics
 */
export interface ErrorMetrics {
  errorRate?: number; // percentage (0-100)
  totalErrors?: number;
  lastError?: string;
  failedConnections?: number;
  circuitBreakerState?: 'closed' | 'open' | 'half-open';
  failureCount?: number;
  [key: string]: any; // Service-specific error metrics
}

/**
 * Resource usage metrics (CPU, memory, etc.)
 */
export interface ResourceMetrics {
  memoryMB?: number;
  memoryPercent?: number;
  cpuPercent?: number;
  diskUsageMB?: number;
  [key: string]: any; // Service-specific resource metrics
}

/**
 * Dependency health metrics
 */
export interface DependencyMetrics {
  dependencies: DependencyHealth[];
  overallStatus: 'healthy' | 'degraded' | 'unhealthy';
}

export interface DependencyHealth {
  name: string;
  type: 'database' | 'api' | 'service' | 'external';
  status: 'healthy' | 'degraded' | 'unhealthy';
  responseTimeMs?: number;
  lastCheck?: string; // ISO 8601
  message?: string;
}
```

### Service-Specific Metrics Types

```typescript
/**
 * WebSocket Ingestion Service Metrics
 */
export interface WebSocketIngestionMetrics extends ServiceMetrics {
  connection: {
    isConnected: boolean;
    connectionAttempts: number;
    successfulConnections: number;
    failedConnections: number;
    lastConnection: string; // ISO 8601
    currentState: 'connected' | 'disconnected' | 'connecting';
  };
  subscription: {
    isSubscribed: boolean;
    totalEvents: number;
    eventsPerMinute: number;
    lastEvent: string; // ISO 8601
  };
  influxdb: {
    isConnected: boolean;
    lastWriteTime: string; // ISO 8601
    writeErrors: number;
  };
}

/**
 * Data API Service Metrics
 */
export interface DataAPIMetrics extends ServiceMetrics {
  cache: {
    hitRate: number; // percentage
    missRate: number; // percentage
    totalHits: number;
    totalMisses: number;
  };
  queries: {
    successRate: number; // percentage
    averageQueryTime: number; // milliseconds
    totalQueries: number;
  };
}

/**
 * External Data Service Metrics (Weather, Sports, etc.)
 */
export interface ExternalDataServiceMetrics extends ServiceMetrics {
  api: {
    connectionStatus: 'connected' | 'disconnected' | 'error';
    lastSuccessfulFetch: string; // ISO 8601
    fetchSuccessRate: number; // percentage
    failedFetches: number;
    totalFetches: number;
  };
  quota?: {
    callsToday: number;
    quotaLimit?: number;
    quotaPercentage?: number; // percentage
  };
  data: {
    freshness: number; // minutes since last update
    cacheAge?: number; // minutes
    lastError?: string;
  };
}

/**
 * AI Automation Service Metrics
 */
export interface AIAutomationMetrics extends ServiceMetrics {
  ai: {
    totalQueries: number;
    averageProcessingTime: number; // milliseconds
    directCalls: number;
    orchestratedCalls: number;
  };
  models: {
    totalModels: number;
    modelUsage: ModelUsage[];
  };
  costs: {
    totalCostUSD: number;
    costPerRequest: number;
    totalTokens: number;
  };
  quality: {
    nerSuccessRate: number; // percentage
    openaiSuccessRate: number; // percentage
    patternFallbackRate: number; // percentage
  };
}

export interface ModelUsage {
  modelName: string;
  totalRequests: number;
  totalTokens: number;
  totalCostUSD: number;
  avgCostPerRequest: number;
  isLocal: boolean;
  sources: string[];
}
```

### Configuration Types

```typescript
/**
 * Service metrics configuration
 * Defines how to fetch and display metrics for each service
 */
export interface ServiceMetricsConfig {
  serviceId: string;
  fetcher: ServiceMetricsFetcher;
  groups: MetricGroupConfig[];
  refreshInterval?: number; // milliseconds (default: 5000)
  cacheTTL?: number; // milliseconds (default: 3000)
  timeout?: number; // milliseconds (default: 5000)
}

/**
 * Function type for fetching service metrics
 */
export type ServiceMetricsFetcher = (
  serviceId: string
) => Promise<ServiceMetrics | null>;

/**
 * Configuration for a group of related metrics
 */
export interface MetricGroupConfig {
  title: string;
  metrics: MetricDefinition[];
  collapsible?: boolean;
  defaultExpanded?: boolean;
}

/**
 * Definition for a single metric
 */
export interface MetricDefinition {
  key: string; // Unique identifier
  label: string; // Display label
  path: string; // JSON path to value (e.g., "operational.uptime")
  formatter?: MetricFormatter; // Custom formatter function
  statusThresholds?: StatusThresholds; // Status determination
  unit?: string; // Unit label (e.g., "ms", "events/min", "%")
  type?: MetricType; // Metric type for default formatting
  description?: string; // Tooltip/help text
}

/**
 * Metric types for default formatting
 */
export type MetricType = 
  | 'number'
  | 'percentage'
  | 'time'
  | 'duration'
  | 'status'
  | 'boolean'
  | 'custom';

/**
 * Custom formatter function
 */
export type MetricFormatter = (value: any) => string;

/**
 * Status thresholds for determining metric status
 */
export interface StatusThresholds {
  good?: number | ((value: any) => boolean);
  warning?: number | ((value: any) => boolean);
  error?: number | ((value: any) => boolean);
}

/**
 * Metric status
 */
export type MetricStatus = 'good' | 'warning' | 'error' | 'unknown';
```

### Component Props Types

```typescript
/**
 * ServiceMetrics component props
 */
export interface ServiceMetricsProps {
  serviceId: string;
  darkMode: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  onError?: (error: Error) => void;
}

/**
 * MetricGroup component props
 */
export interface MetricGroupProps {
  title: string;
  metrics: MetricDefinition[];
  data: ServiceMetrics;
  darkMode: boolean;
  collapsible?: boolean;
  defaultExpanded?: boolean;
}

/**
 * MetricCard component props
 */
export interface MetricCardProps {
  definition: MetricDefinition;
  value: any;
  darkMode: boolean;
  status?: MetricStatus;
}

/**
 * StatusBadge component props
 */
export interface StatusBadgeProps {
  status: 'good' | 'warning' | 'error' | 'unknown';
  label?: string;
  darkMode: boolean;
}

/**
 * ProgressBar component props
 */
export interface ProgressBarProps {
  value: number; // 0-100
  max?: number; // default: 100
  status?: 'good' | 'warning' | 'error';
  darkMode: boolean;
  showLabel?: boolean;
}

/**
 * TrendIndicator component props
 */
export interface TrendIndicatorProps {
  trend: 'up' | 'down' | 'stable';
  value?: number;
  darkMode: boolean;
}

/**
 * TimeAgo component props
 */
export interface TimeAgoProps {
  timestamp: string; // ISO 8601
  darkMode: boolean;
  updateInterval?: number; // milliseconds (default: 60000)
}
```

### API Client Types

```typescript
/**
 * ServiceMetricsClient interface
 */
export interface ServiceMetricsClient {
  /**
   * Fetch metrics for a service
   */
  fetchMetrics(serviceId: string): Promise<ServiceMetrics | null>;
  
  /**
   * Get cached metrics if available and fresh
   */
  getCachedMetrics(serviceId: string): ServiceMetrics | null;
  
  /**
   * Clear cache for a service or all services
   */
  clearCache(serviceId?: string): void;
  
  /**
   * Check if cached metrics are expired
   */
  isExpired(serviceId: string): boolean;
}

/**
 * Cached metrics structure
 */
export interface CachedMetrics {
  data: ServiceMetrics;
  timestamp: number; // Unix timestamp
  ttl: number; // Time to live in milliseconds
}

/**
 * Fetch options
 */
export interface FetchOptions {
  timeout?: number; // milliseconds
  useCache?: boolean; // default: true
  forceRefresh?: boolean; // default: false
}
```

### Hook Return Types

```typescript
/**
 * useServiceMetrics hook return type
 */
export interface UseServiceMetricsResult {
  metrics: ServiceMetrics | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  refresh: () => Promise<void>;
  clearCache: () => void;
}

/**
 * useServiceMetrics hook options
 */
export interface UseServiceMetricsOptions {
  serviceId: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
  enabled?: boolean; // default: true
  onError?: (error: Error) => void;
}
```

## Default Formatters

### Formatter Functions

```typescript
/**
 * Default formatters for different metric types
 */
export const MetricFormatters: Record<MetricType, MetricFormatter> = {
  number: (value: number) => {
    if (value === null || value === undefined) return 'N/A';
    return value.toLocaleString();
  },
  
  percentage: (value: number) => {
    if (value === null || value === undefined) return 'N/A';
    return `${value.toFixed(1)}%`;
  },
  
  time: (value: string) => {
    if (!value) return 'N/A';
    try {
      const date = new Date(value);
      return date.toLocaleString();
    } catch {
      return 'Invalid Date';
    }
  },
  
  duration: (value: number) => {
    if (value === null || value === undefined) return 'N/A';
    const seconds = Math.floor(value);
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  },
  
  status: (value: string) => {
    if (!value) return 'Unknown';
    return value.charAt(0).toUpperCase() + value.slice(1);
  },
  
  boolean: (value: boolean) => {
    return value ? 'Yes' : 'No';
  },
  
  custom: (value: any) => {
    return String(value ?? 'N/A');
  },
};
```

## Status Determination

### Status Calculation

```typescript
/**
 * Determine metric status based on value and thresholds
 */
export function determineMetricStatus(
  value: any,
  thresholds?: StatusThresholds
): MetricStatus {
  if (!thresholds) return 'unknown';
  
  // Check error threshold
  if (thresholds.error !== undefined) {
    const errorThreshold = typeof thresholds.error === 'function'
      ? thresholds.error(value)
      : (value >= thresholds.error);
    if (errorThreshold) return 'error';
  }
  
  // Check warning threshold
  if (thresholds.warning !== undefined) {
    const warningThreshold = typeof thresholds.warning === 'function'
      ? thresholds.warning(value)
      : (value >= thresholds.warning);
    if (warningThreshold) return 'warning';
  }
  
  // Check good threshold
  if (thresholds.good !== undefined) {
    const goodThreshold = typeof thresholds.good === 'function'
      ? thresholds.good(value)
      : (value < thresholds.good);
    if (goodThreshold) return 'good';
  }
  
  return 'unknown';
}
```

## Example Configurations

### WebSocket Ingestion Configuration

```typescript
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
      ],
    },
    {
      title: 'Errors',
      metrics: [
        {
          key: 'errorRate',
          label: 'Error Rate',
          path: 'errors.errorRate',
          type: 'percentage',
          statusThresholds: {
            good: (v) => v < 1,
            warning: (v) => v >= 1 && v < 5,
            error: (v) => v >= 5,
          },
        },
        {
          key: 'circuitBreakerState',
          label: 'Circuit Breaker',
          path: 'errors.circuitBreakerState',
          type: 'status',
        },
      ],
    },
  ],
};
```

## Error Handling Types

```typescript
/**
 * Metrics fetch error
 */
export class MetricsFetchError extends Error {
  constructor(
    public serviceId: string,
    public originalError: Error,
    message?: string
  ) {
    super(message || `Failed to fetch metrics for ${serviceId}`);
    this.name = 'MetricsFetchError';
  }
}

/**
 * Metrics cache error
 */
export class MetricsCacheError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'MetricsCacheError';
  }
}
```

## Validation

### Validation Functions

```typescript
/**
 * Validate service metrics data
 */
export function validateServiceMetrics(
  data: any
): data is ServiceMetrics {
  return (
    typeof data === 'object' &&
    data !== null &&
    typeof data.serviceId === 'string' &&
    typeof data.timestamp === 'string' &&
    typeof data.operational === 'object' &&
    typeof data.performance === 'object' &&
    typeof data.errors === 'object' &&
    typeof data.resources === 'object'
  );
}

/**
 * Validate metric definition
 */
export function validateMetricDefinition(
  def: any
): def is MetricDefinition {
  return (
    typeof def === 'object' &&
    def !== null &&
    typeof def.key === 'string' &&
    typeof def.label === 'string' &&
    typeof def.path === 'string'
  );
}
```

---

**Document Status:** API Design - Ready for Implementation  
**Last Updated:** 2026-01-14
