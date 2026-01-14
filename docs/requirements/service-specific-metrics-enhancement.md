# Service-Specific Metrics Enhancement - Requirements & Planning

**Created:** 2026-01-14  
**Status:** Requirements & Planning Phase  
**Epic:** Service Management Dashboard Enhancement

## Executive Summary

Enhance the service details popup in the health dashboard to display service-specific metrics that provide actionable insights into both operational status (is it running?) and performance quality (how well is it running?). Currently, all services show identical generic metrics, which provides minimal value for monitoring and troubleshooting.

## Current State Analysis

### Current Implementation
- **Location:** `services/health-dashboard/src/components/ServiceDetailsModal.tsx`
- **Current Metrics:** All services display the same 4 generic fields:
  1. Service Name
  2. Status (running/stopped/error/degraded)
  3. Container Status
  4. Last Check (timestamp)

### Problem Statement
- **Generic metrics** provide no service-specific insights
- **No performance indicators** - can't tell if service is performing well
- **No operational metrics** - can't see what the service is actually doing
- **Limited troubleshooting value** - can't identify service-specific issues

### Existing Infrastructure
- Health endpoints exist for many services (websocket-ingestion, data-api, admin-api)
- Some services already expose detailed metrics (websocket-ingestion has connection stats, event rates)
- RAGDetailsModal provides a good example of service-specific metrics display
- Service definitions exist in `ServicesTab.tsx` with service metadata

## Requirements

### Functional Requirements

#### FR1: Service-Specific Metrics Display
**Priority:** High  
**Description:** Each service category must display unique, relevant metrics based on its function and purpose.

**Service Categories & Metrics:**

##### Core Services

**1. websocket-ingestion (Port 8001)**
- **Operational Metrics:**
  - WebSocket Connection Status (connected/disconnected)
  - Connection Attempts (total, successful, failed)
  - Last Connection Time
  - Current Connection State
- **Performance Metrics:**
  - Events Per Minute (current rate)
  - Total Events Received (lifetime)
  - Last Event Timestamp
  - Event Processing Status (subscribed/not subscribed)
- **Error Metrics:**
  - Error Rate (%)
  - Last Error Message
  - Circuit Breaker State (closed/open/half-open)
  - Failure Count
- **Resource Metrics:**
  - Memory Usage (MB)
  - CPU Usage (%)
  - InfluxDB Write Status (connected/disconnected)
  - Last Write Time
  - Write Errors (count)

**2. data-api (Port 8006)**
- **Operational Metrics:**
  - API Status (healthy/degraded/unhealthy)
  - Uptime (seconds, human-readable)
  - Version
- **Performance Metrics:**
  - Requests Per Minute
  - Average Response Time (ms)
  - P95/P99 Response Times (ms)
  - Total Requests (lifetime)
- **Query Metrics:**
  - Cache Hit Rate (%)
  - Cache Miss Rate (%)
  - Query Success Rate (%)
  - Average Query Time (ms)
- **Dependency Metrics:**
  - InfluxDB Connection Status
  - InfluxDB Response Time (ms)
  - WebSocket Ingestion Status
  - Dependency Health Summary

**3. admin-api (Port 8003)**
- **Operational Metrics:**
  - API Gateway Status
  - Uptime
  - Version
- **Performance Metrics:**
  - Requests Per Minute
  - Average Response Time (ms)
  - Total Requests
- **Service Health Aggregation:**
  - Services Monitored (count)
  - Healthy Services (count)
  - Unhealthy Services (count)
  - Health Check Success Rate (%)

**4. ai-automation-service (Port 8018)**
- **Operational Metrics:**
  - Service Status
  - Uptime
  - Model Status (loaded/not loaded)
- **AI Performance Metrics:**
  - Total Queries Processed
  - Average Processing Time (ms)
  - Direct Calls vs Orchestrated Calls
  - Model Usage Statistics
- **Cost Metrics:**
  - Total Cost (USD)
  - Cost Per Request (USD)
  - Token Usage (total)
- **Quality Metrics:**
  - NER Success Rate (%)
  - OpenAI Success Rate (%)
  - Pattern Fallback Rate (%)

**5. influxdb (Port 8086)**
- **Operational Metrics:**
  - Database Status (running/stopped)
  - Uptime
  - Version
- **Storage Metrics:**
  - Total Data Points
  - Storage Size (GB)
  - Retention Policy Status
  - Bucket Count
- **Performance Metrics:**
  - Write Operations Per Second
  - Query Operations Per Second
  - Average Write Latency (ms)
  - Average Query Latency (ms)
- **Health Metrics:**
  - Connection Pool Status
  - Active Connections
  - Error Rate (%)

##### External Data Services

**6. weather-api (Port 8009)**
- **Operational Metrics:**
  - Service Status
  - API Key Status (configured/missing)
  - Last Successful Fetch
  - Fetch Success Rate (%)
- **Performance Metrics:**
  - API Calls Today (count)
  - API Quota Usage (%)
  - Cache Hit Rate (%)
  - Average Response Time (ms)
- **Data Quality Metrics:**
  - Data Freshness (minutes since last update)
  - Cache Age (minutes)
  - Last Error Message
  - Failed Fetches (count)

**7. sports-api (Port 8005)**
- **Operational Metrics:**
  - Service Status
  - Home Assistant Connection Status
  - Last Successful Poll
  - Poll Success Rate (%)
- **Performance Metrics:**
  - Games Tracked (count)
  - Teams Monitored (count)
  - Update Frequency (minutes)
  - Average Poll Time (ms)
- **Data Quality Metrics:**
  - Last Score Update
  - Stale Data Count (games not updated in X hours)
  - Sensor Update Success Rate (%)

**8. carbon-intensity-service (Port 8010)**
- **Operational Metrics:**
  - Service Status
  - API Connection Status
  - Last Successful Fetch
  - Fetch Success Rate (%)
- **Performance Metrics:**
  - Current Carbon Intensity (gCO2/kWh)
  - Renewable Percentage (%)
  - Forecast Accuracy (%)
  - Data Points Written (count)
- **Data Quality Metrics:**
  - Data Freshness (minutes)
  - Last Error Message
  - API Quota Usage (%)

**9. electricity-pricing-service (Port 8011)**
- **Operational Metrics:**
  - Service Status
  - API Connection Status
  - Last Successful Fetch
  - Fetch Success Rate (%)
- **Performance Metrics:**
  - Current Price (currency/unit)
  - Cheapest Hours (list)
  - Price Update Frequency
  - Data Points Written (count)
- **Data Quality Metrics:**
  - Data Freshness (minutes)
  - Last Error Message
  - API Quota Usage (%)

**10. air-quality-service (Port 8012)**
- **Operational Metrics:**
  - Service Status
  - API Connection Status
  - Last Successful Fetch
  - Fetch Success Rate (%)
- **Performance Metrics:**
  - Current AQI (Air Quality Index)
  - PM2.5 Level (μg/m³)
  - PM10 Level (μg/m³)
  - Ozone Level (ppb)
  - Data Points Written (count)
- **Data Quality Metrics:**
  - Data Freshness (minutes)
  - Last Error Message
  - API Quota Usage (%)

**11. calendar-service (Port 8013)**
- **Operational Metrics:**
  - Service Status
  - Calendar Integration Status
  - Last Successful Sync
  - Sync Success Rate (%)
- **Performance Metrics:**
  - Events Processed (count)
  - Upcoming Events (count)
  - Sync Frequency (minutes)
  - Average Sync Time (ms)
- **Data Quality Metrics:**
  - Last Sync Time
  - Failed Syncs (count)
  - Calendar Sources (count)

**12. smart-meter-service (Port 8014)**
- **Operational Metrics:**
  - Service Status
  - Meter Connection Status
  - Last Successful Reading
  - Reading Success Rate (%)
- **Performance Metrics:**
  - Current Power (W)
  - Daily Energy (kWh)
  - Readings Per Hour
  - Data Points Written (count)
- **Data Quality Metrics:**
  - Last Reading Time
  - Failed Readings (count)
  - Meter Response Time (ms)

**13. blueprint-index (Port 8031)**
- **Operational Metrics:**
  - Service Status
  - Index Status (indexed/not indexed)
  - Last Index Update
  - Index Success Rate (%)
- **Performance Metrics:**
  - Total Blueprints Indexed (count)
  - Search Queries Per Minute
  - Average Search Time (ms)
  - Index Size (MB)
- **Data Quality Metrics:**
  - Index Freshness (minutes)
  - Search Success Rate (%)
  - Last Error Message

**14. rule-recommendation-ml (Port 8035)**
- **Operational Metrics:**
  - Service Status
  - Model Status (loaded/not loaded)
  - Last Model Update
  - Model Version
- **Performance Metrics:**
  - Recommendations Generated (count)
  - Average Processing Time (ms)
  - Model Accuracy (%)
  - Training Status
- **Data Quality Metrics:**
  - Recommendation Success Rate (%)
  - Last Error Message
  - Model Performance Score

#### FR2: Metrics Data Collection
**Priority:** High  
**Description:** System must collect service-specific metrics from available endpoints.

**Requirements:**
- Fetch metrics from service `/health` endpoints when available
- Fetch metrics from service `/metrics` endpoints when available
- Fallback to generic metrics when service-specific endpoints unavailable
- Cache metrics data to reduce API calls
- Handle service unavailability gracefully (show "unavailable" status)

#### FR3: Metrics Display Format
**Priority:** Medium  
**Description:** Metrics must be displayed in a clear, scannable format with visual indicators.

**Requirements:**
- Group metrics by category (Operational, Performance, Error, Resource, etc.)
- Use color coding for status indicators (green/yellow/red)
- Show units for all numeric values
- Display relative time for timestamps ("2 minutes ago")
- Show trend indicators when applicable (↑/↓)
- Use progress bars for percentage values
- Show warning/error states prominently

#### FR4: Real-Time Updates
**Priority:** Medium  
**Description:** Metrics should update in real-time when auto-refresh is enabled.

**Requirements:**
- Refresh metrics when modal is opened
- Respect auto-refresh setting from main dashboard
- Update metrics every 5-10 seconds when modal is open
- Show loading state during refresh
- Handle refresh errors gracefully

### Non-Functional Requirements

#### NFR1: Performance
- Modal should open within 500ms
- Metrics should load within 2 seconds
- No impact on main dashboard performance
- Efficient API call batching

#### NFR2: Reliability
- Graceful degradation when service endpoints unavailable
- Fallback to generic metrics when service-specific metrics unavailable
- Error handling for network failures
- Timeout handling (5 second timeout per service)

#### NFR3: Maintainability
- Service-specific metric definitions in configuration
- Easy to add new services
- Clear separation of concerns
- Reusable metric components

#### NFR4: User Experience
- Clear visual hierarchy
- Accessible (WCAG 2.1 AA)
- Responsive design (mobile-friendly)
- Keyboard navigation support

## User Stories

### Epic: Service-Specific Metrics Enhancement

#### Story 1: WebSocket Ingestion Service Metrics
**As a** system administrator  
**I want to** see detailed WebSocket ingestion metrics in the service details popup  
**So that** I can monitor event processing, connection health, and performance

**Acceptance Criteria:**
- [ ] Display WebSocket connection status (connected/disconnected)
- [ ] Show events per minute and total events received
- [ ] Display connection attempts and success/failure counts
- [ ] Show circuit breaker state and failure count
- [ ] Display memory and CPU usage
- [ ] Show InfluxDB write status and error count
- [ ] All metrics update in real-time when modal is open

**Story Points:** 5  
**Priority:** High  
**Dependencies:** None

---

#### Story 2: Data API Service Metrics
**As a** system administrator  
**I want to** see detailed data API metrics in the service details popup  
**So that** I can monitor query performance, cache efficiency, and API health

**Acceptance Criteria:**
- [ ] Display requests per minute and total requests
- [ ] Show average, P95, and P99 response times
- [ ] Display cache hit/miss rates
- [ ] Show query success rate
- [ ] Display dependency health (InfluxDB, WebSocket Ingestion)
- [ ] Show dependency response times
- [ ] All metrics update in real-time when modal is open

**Story Points:** 5  
**Priority:** High  
**Dependencies:** None

---

#### Story 3: External Data Services Metrics (Weather, Sports, Carbon, etc.)
**As a** system administrator  
**I want to** see detailed metrics for external data services  
**So that** I can monitor API usage, data freshness, and service health

**Acceptance Criteria:**
- [ ] Display API connection status and last successful fetch
- [ ] Show fetch success rate and failed fetch count
- [ ] Display API quota usage (when available)
- [ ] Show data freshness (time since last update)
- [ ] Display cache hit rate (when applicable)
- [ ] Show service-specific data metrics (AQI, carbon intensity, etc.)
- [ ] All metrics update in real-time when modal is open

**Story Points:** 8  
**Priority:** High  
**Dependencies:** None

---

#### Story 4: AI Automation Service Metrics
**As a** system administrator  
**I want to** see detailed AI automation service metrics  
**So that** I can monitor AI performance, costs, and model usage

**Acceptance Criteria:**
- [ ] Display total queries processed and average processing time
- [ ] Show direct vs orchestrated call counts
- [ ] Display model usage statistics (requests, tokens, cost per model)
- [ ] Show total cost and cost per request
- [ ] Display NER success rate and OpenAI success rate
- [ ] Show pattern fallback rate
- [ ] All metrics update in real-time when modal is open

**Story Points:** 5  
**Priority:** Medium  
**Dependencies:** None  
**Note:** AI stats already partially implemented - extend existing functionality

---

#### Story 5: Metrics Data Collection Infrastructure
**As a** developer  
**I want to** have a reusable infrastructure for fetching service-specific metrics  
**So that** I can easily add metrics for new services

**Acceptance Criteria:**
- [ ] Create service metrics API client with error handling
- [ ] Implement metrics caching to reduce API calls
- [ ] Create service-specific metric fetcher functions
- [ ] Implement fallback to generic metrics when service endpoints unavailable
- [ ] Add timeout handling (5 seconds per service)
- [ ] Create TypeScript types for service-specific metrics

**Story Points:** 8  
**Priority:** High  
**Dependencies:** None

---

#### Story 6: Metrics Display Components
**As a** developer  
**I want to** have reusable components for displaying different metric types  
**So that** I can consistently display metrics across all services

**Acceptance Criteria:**
- [ ] Create MetricCard component for individual metrics
- [ ] Create MetricGroup component for grouped metrics
- [ ] Create StatusBadge component for status indicators
- [ ] Create ProgressBar component for percentage values
- [ ] Create TrendIndicator component for trend arrows
- [ ] Create TimeAgo component for relative timestamps
- [ ] All components support dark mode
- [ ] All components are accessible (ARIA labels, keyboard navigation)

**Story Points:** 5  
**Priority:** Medium  
**Dependencies:** Story 5

---

#### Story 7: Service Metrics Configuration
**As a** developer  
**I want to** configure service-specific metrics in a centralized location  
**So that** I can easily add or modify metrics for services

**Acceptance Criteria:**
- [ ] Create service metrics configuration file
- [ ] Define metric schema for each service type
- [ ] Map service IDs to metric fetchers
- [ ] Define metric display groups (Operational, Performance, Error, etc.)
- [ ] Define metric status thresholds (good/warning/error)
- [ ] Support for custom metric formatters

**Story Points:** 5  
**Priority:** Medium  
**Dependencies:** Story 5

---

#### Story 8: Real-Time Metrics Updates
**As a** system administrator  
**I want to** see metrics update in real-time when the details modal is open  
**So that** I can monitor service health continuously

**Acceptance Criteria:**
- [ ] Metrics refresh automatically when modal is open
- [ ] Refresh interval configurable (default: 5-10 seconds)
- [ ] Respect auto-refresh setting from main dashboard
- [ ] Show loading indicator during refresh
- [ ] Handle refresh errors gracefully (show last known values)
- [ ] Pause refresh when modal is closed

**Story Points:** 3  
**Priority:** Medium  
**Dependencies:** Story 5, Story 6

---

#### Story 9: InfluxDB Service Metrics
**As a** system administrator  
**I want to** see detailed InfluxDB metrics in the service details popup  
**So that** I can monitor database performance and storage

**Acceptance Criteria:**
- [ ] Display database status and uptime
- [ ] Show total data points and storage size
- [ ] Display write/query operations per second
- [ ] Show average write/query latency
- [ ] Display connection pool status and active connections
- [ ] Show error rate
- [ ] All metrics update in real-time when modal is open

**Story Points:** 5  
**Priority:** Medium  
**Dependencies:** Story 5, Story 6

---

#### Story 10: Admin API Service Metrics
**As a** system administrator  
**I want to** see detailed admin API metrics in the service details popup  
**So that** I can monitor API gateway performance and aggregated service health

**Acceptance Criteria:**
- [ ] Display API gateway status and uptime
- [ ] Show requests per minute and total requests
- [ ] Display average response time
- [ ] Show services monitored count
- [ ] Display healthy/unhealthy service counts
- [ ] Show health check success rate
- [ ] All metrics update in real-time when modal is open

**Story Points:** 3  
**Priority:** Low  
**Dependencies:** Story 5, Story 6

---

## Implementation Plan

### Phase 1: Foundation (Stories 5, 6, 7)
**Duration:** 2-3 weeks  
**Goal:** Build infrastructure for service-specific metrics

**Tasks:**
1. Create service metrics API client
2. Implement metrics caching
3. Create reusable metric display components
4. Create service metrics configuration system
5. Define TypeScript types for all service metrics

**Deliverables:**
- Service metrics API client
- Metric display components library
- Service metrics configuration file
- TypeScript type definitions

---

### Phase 2: Core Services (Stories 1, 2, 9, 10)
**Duration:** 2-3 weeks  
**Goal:** Implement metrics for core services

**Tasks:**
1. Implement WebSocket Ingestion metrics
2. Implement Data API metrics
3. Implement InfluxDB metrics
4. Implement Admin API metrics
5. Test metrics display and real-time updates

**Deliverables:**
- Core services with service-specific metrics
- Real-time metrics updates
- Error handling and fallbacks

---

### Phase 3: External Services (Story 3)
**Duration:** 2-3 weeks  
**Goal:** Implement metrics for external data services

**Tasks:**
1. Implement Weather API metrics
2. Implement Sports API metrics
3. Implement Carbon Intensity metrics
4. Implement Electricity Pricing metrics
5. Implement Air Quality metrics
6. Implement Calendar Service metrics
7. Implement Smart Meter metrics

**Deliverables:**
- All external services with service-specific metrics
- Consistent metrics display across all services

---

### Phase 4: AI Services (Story 4)
**Duration:** 1-2 weeks  
**Goal:** Enhance AI automation service metrics

**Tasks:**
1. Extend existing AI stats display
2. Add missing metrics (model comparison, cost analysis)
3. Integrate with service details modal
4. Test metrics display

**Deliverables:**
- Enhanced AI automation service metrics
- Integration with service details modal

---

### Phase 5: Polish & Optimization (Story 8)
**Duration:** 1 week  
**Goal:** Optimize performance and user experience

**Tasks:**
1. Optimize metrics refresh performance
2. Add loading states and error handling
3. Improve accessibility
4. Add unit tests
5. Update documentation

**Deliverables:**
- Optimized metrics display
- Comprehensive error handling
- Accessibility improvements
- Test coverage
- Updated documentation

---

## Technical Architecture

### Component Structure
```
ServiceDetailsModal
├── ServiceHeader (existing)
├── ServiceMetrics (new)
│   ├── MetricGroup
│   │   ├── MetricCard
│   │   │   ├── StatusBadge
│   │   │   ├── ProgressBar
│   │   │   ├── TrendIndicator
│   │   │   └── TimeAgo
│   │   └── MetricCard (multiple)
│   └── MetricGroup (multiple)
└── ServiceFooter (existing)
```

### Data Flow
```
ServicesTab
  └──> ServiceDetailsModal
        └──> useServiceMetrics(serviceId)
              └──> ServiceMetricsClient
                    ├──> fetchServiceMetrics(serviceId)
                    │     └──> Service-specific fetcher
                    │           └──> API call to service /health or /metrics
                    └──> cache metrics
                          └──> return metrics data
```

### Service Metrics Configuration
```typescript
interface ServiceMetricsConfig {
  serviceId: string;
  fetcher: (serviceId: string) => Promise<ServiceMetrics>;
  groups: MetricGroup[];
  refreshInterval?: number;
}

interface MetricGroup {
  title: string;
  metrics: MetricDefinition[];
}

interface MetricDefinition {
  key: string;
  label: string;
  formatter?: (value: any) => string;
  statusThresholds?: {
    good: number;
    warning: number;
    error: number;
  };
  unit?: string;
}
```

## Dependencies

### External Dependencies
- None (using existing API endpoints)

### Internal Dependencies
- Service health endpoints (`/health`)
- Service metrics endpoints (`/metrics`) - when available
- Admin API service health aggregation
- Existing ServiceDetailsModal component

## Risks & Mitigations

### Risk 1: Service Endpoints Unavailable
**Impact:** High  
**Probability:** Medium  
**Mitigation:** 
- Implement fallback to generic metrics
- Show "unavailable" status clearly
- Cache last known values
- Add retry logic with exponential backoff

### Risk 2: Performance Impact from Frequent API Calls
**Impact:** Medium  
**Probability:** Medium  
**Mitigation:**
- Implement metrics caching
- Batch API calls when possible
- Use configurable refresh intervals
- Limit concurrent API calls

### Risk 3: Inconsistent Metrics Across Services
**Impact:** Medium  
**Probability:** High  
**Mitigation:**
- Create standardized metric configuration
- Define common metric types
- Use consistent naming conventions
- Document metric definitions

### Risk 4: Missing Metrics for Some Services
**Impact:** Low  
**Probability:** High  
**Mitigation:**
- Start with services that have health endpoints
- Gradually add metrics as endpoints become available
- Use generic metrics as fallback
- Document which services need metrics endpoints

## Success Criteria

### Functional Success
- ✅ All 14 services display service-specific metrics
- ✅ Metrics update in real-time when modal is open
- ✅ Metrics display correctly in both light and dark modes
- ✅ Graceful degradation when service endpoints unavailable

### Performance Success
- ✅ Modal opens within 500ms
- ✅ Metrics load within 2 seconds
- ✅ No performance impact on main dashboard
- ✅ Efficient API call batching

### User Experience Success
- ✅ Metrics are easy to understand at a glance
- ✅ Visual indicators clearly show status
- ✅ Accessible to users with disabilities
- ✅ Responsive design works on mobile devices

## Open Questions

1. **Metrics Endpoint Standardization:** Should we standardize `/metrics` endpoints across all services?
2. **Historical Metrics:** Should we show historical trends (e.g., "events/min over last hour")?
3. **Alerting Integration:** Should metrics trigger alerts when thresholds are exceeded?
4. **Export Functionality:** Should users be able to export metrics data?
5. **Metrics Retention:** How long should we cache metrics data?

## Next Steps

1. **Review & Approval:** Review this document with stakeholders
2. **Prioritization:** Prioritize user stories based on business value
3. **Sprint Planning:** Break down stories into tasks for sprint planning
4. **Technical Design:** Create detailed technical design for Phase 1
5. **Prototype:** Build prototype for one service (websocket-ingestion) to validate approach

---

**Document Status:** Draft - Awaiting Review  
**Last Updated:** 2026-01-14  
**Author:** AI Agent (via TappsCodingAgents)
