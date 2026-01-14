# Service-Specific Metrics - Technical Design

**Created:** 2026-01-14  
**Status:** Technical Design - Ready for Implementation  
**Epic:** Service Management Dashboard Enhancement

## Architecture Overview

### System Architecture Pattern
**Pattern:** Client-Side Aggregation with Service Endpoints  
**Rationale:** 
- Services already expose `/health` and `/metrics` endpoints
- Frontend aggregates metrics from multiple services
- No need for additional backend aggregation layer
- Reduces latency and complexity

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Health Dashboard (React)                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           ServicesTab Component                      │  │
│  │  - Service list                                       │  │
│  │  - Service selection                                 │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      ServiceDetailsModal Component                  │  │
│  │  - Service header                                    │  │
│  │  - ServiceMetrics component                         │  │
│  │  - Service footer                                   │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      ServiceMetrics Component                        │  │
│  │  - useServiceMetrics hook                            │  │
│  │  - MetricGroup components                            │  │
│  │  - Real-time updates                                 │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │   ServiceMetricsClient (API Client)                   │  │
│  │  - Fetch metrics from services                       │  │
│  │  - Cache management                                  │  │
│  │  - Error handling                                    │  │
│  │  - Fallback logic                                    │  │
│  └──────────────────┬───────────────────────────────────┘  │
└──────────────────────┼──────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   Service Endpoints          │
        │  - /health                   │
        │  - /metrics                  │
        │  - /api/v1/services/health   │
        └──────────────────────────────┘
```

## Data Flow

### Metrics Fetching Flow

```
1. User opens ServiceDetailsModal
   │
   ▼
2. ServiceMetrics component mounts
   │
   ▼
3. useServiceMetrics hook initializes
   │
   ▼
4. ServiceMetricsClient.fetchMetrics(serviceId)
   │
   ├─► Check cache (if available and fresh)
   │   └─► Return cached metrics
   │
   └─► Fetch from service endpoint
       │
       ├─► Success: Parse and cache metrics
       │   └─► Return metrics
       │
       └─► Failure: Fallback to generic metrics
           └─► Return generic metrics
```

### Real-Time Update Flow

```
1. Modal is open + auto-refresh enabled
   │
   ▼
2. useServiceMetrics sets up interval (5-10s)
   │
   ▼
3. On interval:
   │
   ├─► Fetch fresh metrics
   │
   ├─► Update cache
   │
   └─► Update component state
       └─► Re-render with new metrics
```

## Technology Stack

### Frontend
- **Framework:** React 18+ with TypeScript
- **State Management:** React Hooks (useState, useEffect, useMemo)
- **HTTP Client:** Fetch API (or existing apiService)
- **Caching:** In-memory cache with TTL
- **Styling:** Tailwind CSS (existing)
- **Accessibility:** ARIA labels, keyboard navigation

### Backend (Existing)
- **Services:** FastAPI (Python)
- **Endpoints:** `/health`, `/metrics`
- **Health Aggregation:** Admin API (`/api/v1/services/health`)

## Component Design

### ServiceMetricsClient

**Purpose:** Centralized API client for fetching service metrics

**Location:** `services/health-dashboard/src/services/serviceMetricsClient.ts`

**Responsibilities:**
- Fetch metrics from service endpoints
- Cache metrics with TTL
- Handle errors and timeouts
- Provide fallback to generic metrics
- Transform service-specific responses to unified format

**Interface:**
```typescript
interface ServiceMetricsClient {
  fetchMetrics(serviceId: string): Promise<ServiceMetrics>;
  getCachedMetrics(serviceId: string): ServiceMetrics | null;
  clearCache(serviceId?: string): void;
}
```

### useServiceMetrics Hook

**Purpose:** React hook for managing service metrics state and updates

**Location:** `services/health-dashboard/src/hooks/useServiceMetrics.ts`

**Responsibilities:**
- Manage metrics state
- Handle real-time updates
- Manage loading/error states
- Cleanup on unmount

**Interface:**
```typescript
interface UseServiceMetricsResult {
  metrics: ServiceMetrics | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  refresh: () => Promise<void>;
}
```

### ServiceMetrics Component

**Purpose:** Main component for displaying service-specific metrics

**Location:** `services/health-dashboard/src/components/ServiceMetrics.tsx`

**Responsibilities:**
- Render metric groups
- Handle metric grouping and organization
- Display loading/error states
- Support real-time updates

### MetricGroup Component

**Purpose:** Display a group of related metrics

**Location:** `services/health-dashboard/src/components/MetricGroup.tsx`

**Responsibilities:**
- Render group title
- Render multiple MetricCard components
- Handle group-level styling

### MetricCard Component

**Purpose:** Display a single metric with label, value, and status

**Location:** `services/health-dashboard/src/components/MetricCard.tsx`

**Responsibilities:**
- Display metric label and value
- Show status indicator (good/warning/error)
- Format values with units
- Support different metric types (number, percentage, time, etc.)

### Supporting Components

- **StatusBadge:** Visual status indicator (green/yellow/red)
- **ProgressBar:** Percentage visualization
- **TrendIndicator:** Up/down arrows for trends
- **TimeAgo:** Relative time display ("2 minutes ago")

## Data Models

### TypeScript Interfaces

```typescript
// Core Metrics Types
interface ServiceMetrics {
  serviceId: string;
  timestamp: string;
  operational: OperationalMetrics;
  performance: PerformanceMetrics;
  errors: ErrorMetrics;
  resources: ResourceMetrics;
  [key: string]: any; // Service-specific metrics
}

interface OperationalMetrics {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'paused';
  uptime?: number;
  uptimeHuman?: string;
  lastCheck?: string;
  [key: string]: any;
}

interface PerformanceMetrics {
  requestsPerMinute?: number;
  averageResponseTime?: number;
  p95ResponseTime?: number;
  p99ResponseTime?: number;
  totalRequests?: number;
  [key: string]: any;
}

interface ErrorMetrics {
  errorRate?: number;
  totalErrors?: number;
  lastError?: string;
  [key: string]: any;
}

interface ResourceMetrics {
  memoryMB?: number;
  cpuPercent?: number;
  [key: string]: any;
}

// Configuration Types
interface ServiceMetricsConfig {
  serviceId: string;
  fetcher: (serviceId: string) => Promise<ServiceMetrics>;
  groups: MetricGroupConfig[];
  refreshInterval?: number;
  cacheTTL?: number;
}

interface MetricGroupConfig {
  title: string;
  metrics: MetricDefinition[];
}

interface MetricDefinition {
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

// Component Props
interface ServiceMetricsProps {
  serviceId: string;
  darkMode: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface MetricGroupProps {
  title: string;
  metrics: MetricDefinition[];
  data: ServiceMetrics;
  darkMode: boolean;
}

interface MetricCardProps {
  definition: MetricDefinition;
  value: any;
  darkMode: boolean;
}
```

## Service-Specific Fetchers

### Fetcher Pattern

Each service has a dedicated fetcher function that:
1. Calls the appropriate endpoint (`/health` or `/metrics`)
2. Transforms the response to unified `ServiceMetrics` format
3. Handles service-specific data structures
4. Returns null on error (triggers fallback)

### Example: WebSocket Ingestion Fetcher

```typescript
async function fetchWebSocketIngestionMetrics(
  serviceId: string
): Promise<ServiceMetrics | null> {
  try {
    const response = await fetch('http://localhost:8001/health');
    const data = await response.json();
    
    return {
      serviceId,
      timestamp: new Date().toISOString(),
      operational: {
        status: data.connection?.is_running ? 'healthy' : 'unhealthy',
        uptime: data.uptime_seconds,
        uptimeHuman: data.uptime,
        lastCheck: data.timestamp,
        connectionStatus: data.connection?.current_state,
        connectionAttempts: data.connection?.connection_attempts,
        lastConnection: data.connection?.last_successful,
      },
      performance: {
        eventsPerMinute: data.subscription?.event_rate_per_minute,
        totalEvents: data.subscription?.total_events_received,
        lastEvent: data.subscription?.last_event,
      },
      errors: {
        errorRate: 0, // Calculate from data if available
        failedConnections: data.connection?.failed_connections,
        lastError: data.connection?.last_error,
        circuitBreakerState: data.circuit_breaker?.state,
        failureCount: data.circuit_breaker?.failure_count,
      },
      resources: {
        memoryMB: data.performance?.memory_mb,
        cpuPercent: data.performance?.cpu_percent,
      },
      influxdb: {
        isConnected: true, // From dependency check
        lastWriteTime: new Date().toISOString(),
        writeErrors: 0,
      },
    };
  } catch (error) {
    console.error(`Failed to fetch metrics for ${serviceId}:`, error);
    return null;
  }
}
```

## Configuration System

### Service Metrics Configuration

**Location:** `services/health-dashboard/src/config/serviceMetricsConfig.ts`

**Purpose:** Centralized configuration for all service metrics

**Structure:**
```typescript
export const SERVICE_METRICS_CONFIG: Record<string, ServiceMetricsConfig> = {
  'websocket-ingestion': {
    serviceId: 'websocket-ingestion',
    fetcher: fetchWebSocketIngestionMetrics,
    groups: [
      {
        title: 'Connection Status',
        metrics: [
          {
            key: 'connectionStatus',
            label: 'Connection Status',
            path: 'operational.connectionStatus',
            type: 'status',
            formatter: (v) => v === 'connected' ? 'Connected' : 'Disconnected',
          },
          {
            key: 'connectionAttempts',
            label: 'Connection Attempts',
            path: 'operational.connectionAttempts',
            type: 'number',
          },
          // ... more metrics
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
          // ... more metrics
        ],
      },
      // ... more groups
    ],
    refreshInterval: 5000,
    cacheTTL: 3000,
  },
  // ... other services
};
```

## Caching Strategy

### Cache Implementation

**Location:** `services/health-dashboard/src/services/metricsCache.ts`

**Strategy:**
- In-memory cache with TTL per service
- Cache key: `serviceId`
- TTL: Configurable per service (default: 3-5 seconds)
- Cache invalidation: On manual refresh or TTL expiry

**Interface:**
```typescript
interface MetricsCache {
  get(serviceId: string): CachedMetrics | null;
  set(serviceId: string, metrics: ServiceMetrics, ttl: number): void;
  clear(serviceId?: string): void;
  isExpired(serviceId: string): boolean;
}

interface CachedMetrics {
  data: ServiceMetrics;
  timestamp: number;
  ttl: number;
}
```

## Error Handling

### Error Handling Strategy

1. **Service Endpoint Unavailable:**
   - Return null from fetcher
   - Fallback to generic metrics
   - Show "Metrics Unavailable" message

2. **Network Timeout:**
   - 5-second timeout per service
   - Return cached metrics if available
   - Fallback to generic metrics

3. **Invalid Response:**
   - Log error
   - Return null from fetcher
   - Fallback to generic metrics

4. **Partial Failure:**
   - Return available metrics
   - Mark unavailable metrics as "N/A"
   - Show warning indicator

## Performance Optimization

### Optimization Strategies

1. **Parallel Fetching:**
   - Fetch metrics from multiple services in parallel
   - Use `Promise.all()` for concurrent requests

2. **Caching:**
   - Cache metrics with short TTL (3-5 seconds)
   - Reduce API calls by 80-90%

3. **Debouncing:**
   - Debounce rapid refresh requests
   - Prevent excessive API calls

4. **Lazy Loading:**
   - Only fetch metrics when modal is open
   - Cancel pending requests on modal close

5. **Request Cancellation:**
   - Cancel in-flight requests on unmount
   - Use AbortController for request cancellation

## Security Considerations

### Security Measures

1. **CORS:**
   - Services should allow CORS from dashboard origin
   - Or use admin-api as proxy

2. **Authentication:**
   - Use existing authentication if required
   - Pass auth tokens in requests

3. **Input Validation:**
   - Validate service IDs
   - Sanitize metric values before display

4. **Error Messages:**
   - Don't expose sensitive information in error messages
   - Log detailed errors server-side only

## Testing Strategy

### Unit Tests

- ServiceMetricsClient: Fetch, cache, error handling
- useServiceMetrics hook: State management, updates
- Metric components: Rendering, formatting
- Configuration: Metric definitions, formatters

### Integration Tests

- End-to-end metrics fetching
- Real-time updates
- Error handling and fallbacks
- Cache behavior

### E2E Tests

- Open service details modal
- Verify metrics display
- Test real-time updates
- Test error scenarios

## Deployment Considerations

### Deployment Steps

1. **Frontend:**
   - Build React app
   - Deploy to existing health-dashboard service
   - No backend changes required

2. **Service Endpoints:**
   - Ensure all services expose `/health` or `/metrics`
   - Add endpoints for services that don't have them (future work)

3. **Configuration:**
   - Update service metrics configuration
   - Test with each service

## Migration Plan

### Phase 1: Infrastructure
1. Create ServiceMetricsClient
2. Create useServiceMetrics hook
3. Create metric components
4. Create configuration system

### Phase 2: Core Services
1. Implement fetchers for core services
2. Add metrics configuration
3. Test with one service (websocket-ingestion)

### Phase 3: All Services
1. Implement fetchers for all services
2. Add metrics configuration for all services
3. Test and refine

### Phase 4: Polish
1. Optimize performance
2. Improve error handling
3. Add accessibility features
4. Write tests

## Open Questions

1. **Metrics Endpoint Standardization:** Should we create a standard `/metrics` endpoint format?
2. **Historical Metrics:** Should we show trends over time?
3. **Alerting:** Should metrics trigger alerts when thresholds exceeded?
4. **Export:** Should users be able to export metrics data?

---

**Document Status:** Technical Design - Ready for Implementation  
**Last Updated:** 2026-01-14
