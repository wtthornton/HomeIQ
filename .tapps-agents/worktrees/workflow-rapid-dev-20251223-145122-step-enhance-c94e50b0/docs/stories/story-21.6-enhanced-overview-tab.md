# Story 21.6: Enhanced Overview Tab

**Epic:** Epic 21 - Dashboard API Integration Fix  
**Story ID:** 21.6  
**Created:** October 13, 2025  
**Status:** In Progress  
**Priority:** High  
**Estimated Effort:** 2-3 hours  

## Goal

Update the Overview tab with enhanced health monitoring capabilities by integrating Epic 17.2 enhanced health endpoints, displaying critical alerts, and providing quick actions for service management.

## Current State

- OverviewTab displays basic system health information
- EnhancedHealthStatus component exists and shows service dependencies
- Uses basic `/api/v1/health` endpoint
- No integration with alerts system
- No quick action buttons for service management

## User Story

**As a** system administrator  
**I want to** see comprehensive system health at a glance in the Overview tab  
**So that** I can quickly identify and respond to issues across all services

## Requirements

### Functional Requirements

1. **Enhanced Health Display**
   - Show all service dependencies with status
   - Display detailed metrics per service (uptime, response time, error rate)
   - Color-coded status indicators (green, yellow, red)
   - Last health check timestamp

2. **Critical Alerts Integration**
   - Display critical alerts prominently at top of Overview
   - Show alert count with severity breakdown
   - Link to full Alerts tab for details
   - Real-time alert updates

3. **Service Metrics**
   - Events per minute
   - API response times
   - Database connection status
   - InfluxDB query performance
   - WebSocket connection status

4. **Quick Actions** (Phase 2 - Optional)
   - Restart service button
   - View logs link
   - Service configuration link
   - Health check refresh

### Non-Functional Requirements

1. **Performance**
   - Load overview in < 500ms
   - Auto-refresh every 30 seconds
   - Responsive UI updates

2. **Usability**
   - Clear visual hierarchy
   - Intuitive status indicators
   - Accessible color schemes (not relying only on color)
   - Keyboard navigation support

3. **Reliability**
   - Graceful handling of service failures
   - Fallback to cached data if API unavailable
   - Clear error messages

## Design

### Component Structure

```
OverviewTab
├── Critical Alerts Banner (if any)
│   ├── Alert Count Badge
│   ├── Severity Breakdown
│   └── View All Alerts Link
├── System Health Summary Cards (4-col grid)
│   ├── Total Events (24h)
│   ├── Active Services
│   ├── System Uptime
│   └── Success Rate
├── EnhancedHealthStatus Component
│   ├── Service Health Cards
│   │   ├── Service Name & Status
│   │   ├── Uptime Percentage
│   │   ├── Response Time
│   │   ├── Dependency Status
│   │   └── Last Health Check
│   └── Dependency Graph (optional)
└── Key Metrics Section
    ├── Events Processing Rate Chart
    ├── API Response Time Trend
    └── Recent Activity Timeline
```

### Data Models

```typescript
// Enhanced health response
interface EnhancedHealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  services: {
    [serviceName: string]: ServiceHealth;
  };
  timestamp: string;
  overall: {
    uptime_seconds: number;
    events_processed_24h: number;
    active_services: number;
    success_rate: number;
  };
}

// Service health detail
interface ServiceHealth {
  status: 'up' | 'down' | 'degraded';
  uptime_seconds: number;
  response_time_ms: number;
  error_count: number;
  last_check: string;
  dependencies: {
    [depName: string]: DependencyStatus;
  };
}

// Dependency status
interface DependencyStatus {
  status: 'connected' | 'disconnected' | 'unknown';
  details?: string;
}
```

### API Endpoints

**GET /api/v1/health**
- Basic health check
- Returns: status, service, timestamp

**GET /api/v1/health/enhanced**
- Detailed health with all service information
- Returns: EnhancedHealthResponse with full metrics

**GET /api/v1/alerts?severity=critical**
- Get critical alerts for banner
- Returns: Array of critical alerts

**GET /api/v1/analytics?range=1h**
- Get metrics for overview charts
- Returns: Events rate, response times, etc.

## Tasks

### Phase 1: Core Enhancement
- [x] Create story documentation (BMAD)
- [ ] Review current OverviewTab and EnhancedHealthStatus
- [ ] Verify enhanced health endpoints exist
- [ ] Update OverviewTab to use enhanced health data
- [ ] Add critical alerts banner
- [ ] Update service health cards with detailed metrics
- [ ] Test auto-refresh functionality

### Phase 2: Additional Features (Optional)
- [ ] Add quick action buttons
- [ ] Add dependency graph visualization
- [ ] Add service restart capability
- [ ] Add logs viewer integration

### Testing
- [ ] Test enhanced health data loading
- [ ] Test critical alerts integration
- [ ] Test auto-refresh (30s interval)
- [ ] Test error handling (service down scenarios)
- [ ] Test responsive design
- [ ] Test dark mode
- [ ] Test performance with multiple services

## Acceptance Criteria

### Must Have
- [ ] Enhanced health section shows all service dependencies
- [ ] Status indicators accurately reflect service health
- [ ] Critical alerts displayed prominently at top
- [ ] Summary cards show correct metrics
- [ ] Metrics update every 30 seconds
- [ ] Loading states during data fetch
- [ ] Error handling with retry
- [ ] Responsive design for mobile/tablet/desktop

### Should Have
- [ ] Service-specific health details on hover/click
- [ ] Dependency status for each service
- [ ] Historical uptime display
- [ ] Performance metrics trends

### Nice to Have
- [ ] Quick actions (restart, view logs)
- [ ] Dependency graph visualization
- [ ] Service health history chart
- [ ] Export health report

## Technical Considerations

### State Management
- Use React hooks for local state
- useEffect for auto-refresh
- Custom hooks for health data fetching
- Context for sharing data with child components

### API Integration
- Combine data from multiple endpoints:
  - `/api/v1/health/enhanced` - Service health
  - `/api/v1/alerts?severity=critical` - Critical alerts
  - `/api/v1/analytics?range=1h` - Metrics
- Handle partial failures gracefully
- Cache last successful response

### Performance
- Memoize expensive calculations
- Debounce refresh if user navigating away
- Lazy load detailed metrics
- Optimize re-renders with React.memo

### Error Handling
- Display cached data if refresh fails
- Show warning banner for stale data
- Retry failed requests with exponential backoff
- Log errors to console for debugging

## Dependencies

### Internal
- admin-api service (enhanced health endpoint)
- data-api service (alerts, analytics)
- EnhancedHealthStatus component (existing)
- Alert types from Story 21.5

### External
- None (using existing React/TypeScript stack)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Enhanced health endpoint missing | High | Verify endpoint exists, implement if needed |
| Too much data causes performance issues | Medium | Paginate/filter service list, lazy load details |
| Auto-refresh causes excessive API calls | Medium | Implement smart refresh (only when tab active) |
| Multiple endpoint failures complicate error handling | Medium | Independent error boundaries per section |

## Timeline

- **Phase 1a (0.5-1 hour):** Review and planning
- **Phase 1b (1-1.5 hours):** Enhanced health integration
- **Phase 1c (0.5 hour):** Critical alerts integration
- **Phase 1d (0.5 hour):** Testing and refinement

**Total:** 2.5-3 hours

## Success Metrics

- Overview tab loads in < 500ms
- All service statuses display correctly
- Critical alerts visible immediately
- Auto-refresh works without UI flicker
- 0 critical bugs in production
- Positive user feedback on information density

## Related Stories

- **Story 21.0:** Deploy Data API Service (prerequisite)
- **Story 21.5:** Alerts Tab Implementation (provides alert integration)
- **Story 21.4:** Analytics Tab with Real Data (provides metrics API)
- **Epic 17.2:** Enhanced Health Monitoring (original health endpoints)

## References

- Epic 21 document: `docs/stories/epic-21-dashboard-api-integration-fix.md`
- EnhancedHealthStatus component: `services/health-dashboard/src/components/EnhancedHealthStatus.tsx`
- Admin API health endpoints: `services/admin-api/src/health_endpoints.py`
- Alert types: `services/health-dashboard/src/types/alerts.ts` (Story 21.5)

---

**Created by:** AI Assistant (BMAD Method)  
**Last Updated:** October 13, 2025

