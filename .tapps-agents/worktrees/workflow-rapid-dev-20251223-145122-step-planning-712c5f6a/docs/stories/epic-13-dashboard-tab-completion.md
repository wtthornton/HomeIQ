# Epic 13: Dashboard Tab Completion - Brownfield Enhancement

## Epic Goal

Complete all placeholder dashboard tabs (Data Sources, Analytics, Alerts) with meaningful, functional content that provides real value to users monitoring their HA Ingestor system.

## Epic Description

### Existing System Context

- **Current functionality:** Dashboard has 7 tabs, 3 are empty placeholders (Data Sources, Analytics, Alerts)
- **Technology stack:** React 18.2 + TypeScript, Tailwind CSS, Admin API (FastAPI)
- **Integration points:** Admin API health endpoints, existing service monitoring, InfluxDB metrics

### Enhancement Details

**What's being added:**
- Data Sources tab with live external API status monitoring
- Analytics tab with system performance charts and trends
- Alerts tab with alert history, management, and configuration
- Real-time status indicators for all external services
- Simple CSS-based charts (no new dependencies)
- Alert acknowledgment and filtering system

**How it integrates:**
- Uses existing Admin API endpoints
- Extends existing service monitoring infrastructure
- Follows current dashboard UI patterns
- Integrates with existing dark mode and theming
- Uses existing polling mechanisms (30s intervals)

**Success criteria:**
- All tabs have meaningful, functional content
- No empty placeholder states remain
- Real-time updates for all tabs
- Mobile-responsive layouts
- Consistent with existing dashboard UX
- <1s load time for each tab

## Stories

### Story 13.1: Data Sources Status Dashboard
Create comprehensive external data sources monitoring panel showing real-time status, API usage, and cache performance.

**Key Tasks:**
- Create DataSourcesPanel component
- Add status cards for each external service:
  - Weather API (OpenWeatherMap)
  - Carbon Intensity API
  - Air Quality API
  - Electricity Pricing API
  - Calendar Service
  - Smart Meter Service
- Real-time status indicators (healthy, degraded, error)
- API call statistics display
- Cache hit rate monitoring
- Last updated timestamps
- Response time tracking
- Retry count indicators
- Configuration quick links

**Acceptance Criteria:**
- [ ] All 6 external services displayed
- [ ] Status updates every 30 seconds
- [ ] API usage stats accurate
- [ ] Cache metrics displayed
- [ ] Mobile responsive layout
- [ ] Dark mode support
- [ ] Quick access to configuration

**Estimated Effort:** 2-3 days

### Story 13.2: System Performance Analytics
Create analytics dashboard showing system performance trends, metrics charts, and summary statistics.

**Key Tasks:**
- Create AnalyticsPanel component
- Implement simple CSS-based mini charts
- Add time-series visualizations:
  - Events per minute (last hour)
  - API response time trends
  - Database write latency
  - Error rate over time
- Summary statistics cards
- Time range selector (1h, 6h, 24h, 7d)
- Performance metrics calculations
- Trend indicators (up/down arrows)
- Peak/average/min displays
- Export metrics data (CSV)

**Acceptance Criteria:**
- [ ] 4 time-series charts displayed
- [ ] Summary statistics accurate
- [ ] Time range selector working
- [ ] Charts responsive
- [ ] Data updates in real-time
- [ ] Dark mode support
- [ ] Performance optimized (<100ms render)

**Estimated Effort:** 2-3 days

### Story 13.3: Alert Management System
Create comprehensive alert management interface with history, filtering, acknowledgment, and configuration.

**Key Tasks:**
- Create AlertsPanel component
- Alert history table (last 24 hours)
- Alert severity levels (info, warning, error, critical)
- Filtering by severity and service
- Acknowledgment functionality
- Alert timeline visualization
- Alert count badges
- Recent alerts summary
- Alert configuration section:
  - Email notifications toggle
  - Threshold settings
  - Check interval configuration
- Alert detail modal
- Clear/dismiss alerts

**Acceptance Criteria:**
- [ ] Alert history displays correctly
- [ ] Filtering works for all criteria
- [ ] Acknowledgment persists
- [ ] Alert configuration functional
- [ ] Real-time alert updates
- [ ] Mobile responsive
- [ ] Dark mode support
- [ ] Performance optimized (virtual scrolling for large lists)

**Estimated Effort:** 2-3 days

## Compatibility Requirements

- [x] Existing APIs remain unchanged (new endpoints only)
- [x] Database schema changes are backward compatible (localStorage for client state)
- [x] UI changes follow existing patterns (Tailwind CSS, React hooks)
- [x] Performance impact is minimal (uses existing polling, no new heavy dependencies)

## Risk Mitigation

**Primary Risk:** Performance degradation with multiple charts and real-time updates

**Mitigation:**
- Use CSS-based charts (no Canvas/WebGL overhead)
- Implement conditional rendering (only update visible tab)
- Debounced updates (30s minimum)
- Virtual scrolling for large lists
- React.memo for expensive components
- Performance monitoring

**Rollback Plan:**
- Revert to placeholder content
- No database changes to rollback
- Feature flags for gradual rollout
- Existing functionality unaffected

## Definition of Done

- [x] All 3 stories completed with acceptance criteria met
- [x] All dashboard tabs have functional content
- [x] No empty placeholder states remain
- [x] Real-time updates working for all tabs
- [x] Mobile responsive verified on iOS and Android
- [x] Dark mode working correctly on all new components
- [x] Performance tested (load time, render time, memory)
- [x] E2E tests for all new tabs
- [x] Documentation updated (user guide, API docs)

## Dependencies

- Admin API health endpoints (existing)
- Service monitoring infrastructure (existing)
- No new npm packages required

## Estimated Effort

- Story 13.1: 2-3 days (Data Sources dashboard)
- Story 13.2: 2-3 days (Analytics dashboard)
- Story 13.3: 2-3 days (Alert management)

**Total:** ~6-9 days (1.5-2 weeks)

---

**Status:** Draft  
**Created:** October 12, 2025  
**Epic Owner:** Product Team  
**Development Lead:** TBD  
**Priority:** High (completes dashboard functionality)

