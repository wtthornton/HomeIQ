# Epic 21: Dashboard API Integration Fix & Epic 12/13 Feature Completion

**Status:** 🚧 **READY FOR DEVELOPMENT**  
**Created:** 2025-10-13  
**Epic Owner:** Development Team  
**Priority:** HIGH - Critical for feature completeness

---

## 🎯 Epic Goal

Fully integrate the dashboard with the new data-api service structure (Epic 13) and connect to Epic 12 sports persistence features, fixing broken/missing API connections and completing feature implementation across all 12 dashboard tabs.

---

## 📋 Executive Summary

### Current State Analysis

**What's Working ✅**
- nginx routing correctly configured for data-api (port 8006) and admin-api (port 8003/8004)
- API client structure properly separated (`adminApi` vs `dataApi`)
- Devices tab correctly queries `data-api` endpoints
- Tab navigation and UI structure functional
- WebSocket infrastructure exists

**What's Broken or Missing ❌**
1. **WebSocket Connection Error**: Dashboard tries to connect to admin-api WebSocket, should use data-api `/api/v1/ws`
2. **Sports Tab**: Only shows setup wizard, missing:
   - Live games display with real-time polling
   - Historical games query from InfluxDB (Epic 12 Story 12.2)
   - Season statistics and team records
   - Game timeline visualization
3. **Events Tab**: Only shows WebSocket stream, missing:
   - Query to `/api/v1/events` for historical data
   - Event search functionality
   - Event stats display
4. **Analytics Tab**: Shows mock/placeholder data, missing:
   - Query to `/api/v1/analytics` endpoint
   - Real metrics from backend services
5. **Alerts Tab**: Placeholder only, missing:
   - Query to `/api/v1/alerts` endpoint
   - Alert management UI
6. **OverviewTab**: Missing integration with enhanced health endpoints

### Root Cause

The dashboard was built when all endpoints were on admin-api. Epic 13 separated the API into:
- **admin-api (8003/8004)**: System monitoring, health, Docker management
- **data-api (8006)**: Feature data hub (events, devices, sports, analytics, alerts)

Many dashboard components still reference old endpoints or have placeholder implementations. Epic 12 added sports persistence to InfluxDB, but the dashboard doesn't query these historical endpoints.

---

## 📊 Technical Context

### API Structure (Epic 13)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Dashboard (Port 3000)                         │
│                         nginx proxy                              │
└────────────┬────────────────────────────────┬────────────────────┘
             │                                │
             │ System Monitoring              │ Feature Data
             │                                │
             ▼                                ▼
┌────────────────────────────┐  ┌──────────────────────────────────┐
│   Admin API (8003/8004)   │  │     Data API (8006)              │
│                            │  │                                  │
│ - System health            │  │ - Events (8 endpoints)           │
│ - Docker management        │  │ - Devices & Entities (5)         │
│ - Service monitoring       │  │ - Sports data (9) [Epic 12]      │
│ - Configuration            │  │ - Analytics (4)                  │
│ - Admin WebSocket (/ws)    │  │ - Alerts (6)                     │
│                            │  │ - Integrations (2)               │
│                            │  │ - Data WebSocket (/api/v1/ws)    │
└────────────────────────────┘  └──────────────────────────────────┘
```

### Epic 12 Sports Persistence (IMPLEMENTED)

**Backend Services Ready:**
- ✅ InfluxDB persistence for all game data (2-year retention)
- ✅ Historical query endpoints in data-api:
  - `/api/v1/sports/games/history` - Historical games by team/season
  - `/api/v1/sports/games/timeline/{id}` - Score progression
  - `/api/v1/sports/schedule/{team}` - Season schedules
- ✅ HA automation endpoints:
  - `/api/v1/ha/game-status/{team}` - Real-time game status
  - `/api/v1/ha/game-context/{team}` - Rich context for automations

**Dashboard Implementation:** ⚠️ MISSING - Only setup wizard exists

---

## 🎯 Success Criteria

1. ✅ All 12 dashboard tabs functional with real data
2. ✅ WebSocket connection uses correct data-api endpoint
3. ✅ Sports tab displays live games + historical data from InfluxDB
4. ✅ Events tab queries historical events from data-api
5. ✅ Analytics tab shows real metrics from backend
6. ✅ Alerts tab displays and manages alerts via data-api
7. ✅ No console errors related to API calls
8. ✅ All API client methods properly use `dataApi` vs `adminApi`
9. ✅ Performance: Historical queries complete in <200ms
10. ✅ All existing functionality preserved (no regressions)

---

## 📖 Stories

### Story 21.0: Deploy Data API Service (PREREQUISITE)

**Goal:** Deploy the data-api service that was created in Epic 13 but never deployed to production

**Current Issue:**
```bash
# data-api service exists but is NOT RUNNING
$ docker ps --filter "name=data-api"
NAMES     STATUS    PORTS
# <empty - service not deployed>
```

**Root Cause:**
- Epic 13 created the data-api service (port 8006) to separate feature data from admin monitoring
- Service code exists: `services/data-api/` with all endpoints implemented
- Service configured in `docker-compose.yml`
- **Service was NEVER deployed/started**
- Dashboard and nginx expect data-api to be running, causing connection failures

**Verification Steps:**

**Step 1: Verify Service Configuration**
```bash
# Check docker-compose.yml
grep -A 20 "data-api:" docker-compose.yml

# Expected output:
#   data-api:
#     build:
#       context: .
#       dockerfile: services/data-api/Dockerfile
#     container_name: homeiq-data-api
#     ports:
#       - "8006:8006"
```

**Step 2: Check Service Code**
```bash
# Verify main.py exists
ls -la services/data-api/src/main.py

# Verify all endpoints exist
ls -la services/data-api/src/*_endpoints.py
# Expected files:
#   - events_endpoints.py (Epic 13 Story 13.2)
#   - devices_endpoints.py (Epic 13 Story 13.2)
#   - alert_endpoints.py (Epic 13 Story 13.3)
#   - metrics_endpoints.py (Epic 13 Story 13.3)
#   - integration_endpoints.py (Epic 13 Story 13.3)
#   - websocket_endpoints.py (Epic 13 Story 13.3)
#   - sports_endpoints.py (Epic 13 Story 13.4)
#   - ha_automation_endpoints.py (Epic 13 Story 13.4)
```

**Deployment Tasks:**

**Task 1: Build Data API Container**
```bash
# Build the data-api service
docker-compose build data-api

# Verify build success
docker images | grep data-api
```

**Task 2: Start Data API Service**
```bash
# Start data-api service
docker-compose up -d data-api

# Verify service is running
docker ps --filter "name=data-api"

# Expected output:
# homeiq-data-api   Up X seconds   0.0.0.0:8006->8006/tcp
```

**Task 3: Verify Health Endpoint**
```bash
# Test health endpoint
curl http://localhost:8006/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "data-api",
#   "version": "1.0.0",
#   "timestamp": "2025-10-13T...",
#   "influxdb": {
#     "status": "connected"
#   }
# }
```

**Task 4: Verify All Endpoint Routes**
```bash
# Test events endpoint
curl http://localhost:8006/api/v1/events?limit=1

# Test devices endpoint
curl http://localhost:8006/api/devices?limit=1

# Test sports endpoint
curl http://localhost:8006/api/v1/sports/games/live

# Test OpenAPI docs
curl http://localhost:8006/docs
# Should return FastAPI auto-generated docs page
```

**Task 5: Update Docker Compose Profiles (if needed)**
```yaml
# Ensure data-api is included in default/production profiles
# Check docker-compose.yml for:

data-api:
  profiles: ["default", "production"]  # Add if missing
  # ... rest of config
```

**Task 6: Verify nginx Routing**
```bash
# From dashboard container, verify nginx can reach data-api
docker exec homeiq-health-dashboard curl http://homeiq-data-api:8006/health

# Expected: Should return health status (not connection refused)
```

**Task 7: Integration Test from Dashboard**
```bash
# Test from browser/dashboard
# Open: http://localhost:3000
# Check browser console - should NOT see:
#   - "Failed to fetch" errors for /api/v1/events
#   - "net::ERR_CONNECTION_REFUSED" for port 8006
```

**Environment Variables Required:**
```bash
# Add to infrastructure/.env or docker-compose.yml environment:

# Data API Configuration
DATA_API_PORT=8006
DATA_API_HOST=0.0.0.0
ENABLE_AUTH=false  # Optional for data-api

# InfluxDB Connection (required for data queries)
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
INFLUXDB_ORG=homeiq
INFLUXDB_BUCKET=home_assistant_events

# CORS (for dashboard access)
CORS_ORIGINS=http://localhost:3000,http://localhost:8003
```

**Acceptance Criteria:**
- [ ] data-api container builds without errors
- [ ] data-api service starts and shows "Up" status
- [ ] Health endpoint responds at http://localhost:8006/health
- [ ] All 8 endpoint routers accessible (events, devices, sports, alerts, etc.)
- [ ] InfluxDB connection successful (shown in health status)
- [ ] nginx can route to data-api from dashboard container
- [ ] Browser console shows no connection errors to port 8006
- [ ] OpenAPI docs accessible at http://localhost:8006/docs
- [ ] Service logs show no startup errors

**Rollback Plan:**
If deployment causes issues:
```bash
# Stop data-api service
docker-compose stop data-api

# Dashboard will fall back to HTTP polling of admin-api
# (Graceful degradation - some features unavailable but system functional)
```

**Files to Verify/Modify:**
- `docker-compose.yml` - Ensure data-api service configured correctly
- `infrastructure/.env` - Add data-api environment variables
- `services/data-api/Dockerfile` - Verify build configuration
- `services/data-api/requirements.txt` - Verify dependencies

**Testing Checklist:**
```bash
# Post-deployment verification
□ docker ps shows data-api running
□ curl localhost:8006/health returns 200 OK
□ curl localhost:8006/api/v1/events returns data or empty array
□ curl localhost:8006/docs returns HTML (OpenAPI docs)
□ Dashboard loads without 502/503 errors
□ Browser DevTools Network tab shows successful requests to /api/v1/*
□ Admin-api still accessible at port 8003/8004
□ No port conflicts (8006 not in use by other services)
```

**⚠️ CRITICAL NOTE:**
This story MUST be completed before any other stories in Epic 21. Without the data-api service running, the dashboard cannot connect to feature data endpoints, and all subsequent stories will fail.

---

### Story 21.1: Fix WebSocket Connection to Data API

**Goal:** Update WebSocket service to connect to data-api `/api/v1/ws` for feature data streaming

**Current Issue:**
```typescript
// services/health-dashboard/src/services/websocket.ts
// Currently connects to /ws (admin-api)
// Should connect to /api/v1/ws (data-api) for events, sports, alerts
```

**Tasks:**
1. Update WebSocket connection URL in `websocket.ts`
2. Update message handling for data-api format
3. Update `useRealtimeMetrics` hook to handle new data structure
4. Test reconnection logic
5. Verify error handling for connection failures
6. Update EventStreamViewer to properly display streamed events

**Acceptance Criteria:**
- [ ] WebSocket connects to `/api/v1/ws` (data-api)
- [ ] Connection status indicator shows green on successful connection
- [ ] Real-time events stream correctly to EventsTab
- [ ] Reconnection works after network interruption
- [ ] Console shows no WebSocket errors during normal operation

**Files to Modify:**
- `services/health-dashboard/src/services/websocket.ts`
- `services/health-dashboard/src/hooks/useRealtimeMetrics.ts`
- `services/health-dashboard/src/components/EventStreamViewer.tsx`

---

### Story 21.2: Complete Sports Tab Implementation

**Goal:** Implement full sports data display with live games and historical queries (Epic 12 integration)

**Current State:** Setup wizard only (3-step team selection)

**New Implementation:**

```typescript
// After setup completion:
SportsTab
├── Team Selection Header (sticky)
│   └── Selected teams with quick filter
├── Live Games Section (if any games today)
│   ├── Query: dataApi.getLiveGames()
│   ├── Real-time polling (every 15 seconds during games)
│   └── Score updates with animations
├── Historical Data Section
│   ├── Season Statistics Card
│   │   ├── Query: dataApi.getSportsHistory(team, season)
│   │   └── Win/Loss record, standings
│   ├── Recent Games List
│   │   ├── Query: dataApi.getSportsHistory(team, { limit: 10 })
│   │   └── Click to view game timeline
│   └── Game Timeline Modal
│       ├── Query: dataApi.getGameTimeline(gameId)
│       └── Score progression chart (Recharts)
└── Schedule Section
    ├── Query: dataApi.getTeamSchedule(team)
    └── Upcoming games calendar view
```

**Tasks:**

**Phase 1: Setup Wizard Enhancement**
1. Add localStorage persistence for selected teams
2. Add "Edit Teams" button to post-setup view
3. Add validation for minimum 1 team selection

**Phase 2: Live Games Display**
1. Create `LiveGameCard` component
   - Display current score, quarter/period, time remaining
   - Team logos and colors
   - Status indicator (live, upcoming, final)
2. Implement polling logic (15-second interval during game times)
3. Add score change animations
4. Handle "No games today" state

**Phase 3: Historical Data Integration**
1. Create `TeamStatisticsCard` component
   - Query `/api/v1/sports/games/history` for season data
   - Display win/loss record, winning percentage
   - Show last 5 games results
2. Create `RecentGamesList` component
   - Table view of recent games
   - Final scores, dates, opponent
   - Click to view timeline
3. Create `GameTimelineModal` component
   - Query `/api/v1/sports/games/timeline/{id}`
   - Line chart showing score progression
   - Quarter-by-quarter breakdown

**Phase 4: Schedule View**
1. Create `TeamScheduleView` component
   - Query `/api/v1/sports/schedule/{team}`
   - Calendar-style view of season
   - Highlight past games (with results) vs future games

**Acceptance Criteria:**
- [ ] Setup wizard saves team selections to localStorage
- [ ] Live games display with real-time score updates
- [ ] Season statistics query InfluxDB via data-api
- [ ] Game timeline modal shows score progression chart
- [ ] Schedule view displays full season with results
- [ ] Polling stops when no games are live (performance)
- [ ] Error handling for API failures (graceful degradation)
- [ ] Responsive design for mobile devices

**API Endpoints Used:**
```typescript
// Live games (cache-first, 15s TTL)
dataApi.getLiveGames(teamIds, league)

// Historical queries (InfluxDB)
dataApi.getSportsHistory(team, { season, limit })
dataApi.getGameTimeline(gameId)
dataApi.getTeamSchedule(team)
```

**Files to Create/Modify:**
- `services/health-dashboard/src/components/sports/LiveGameCard.tsx` (NEW)
- `services/health-dashboard/src/components/sports/TeamStatisticsCard.tsx` (NEW)
- `services/health-dashboard/src/components/sports/RecentGamesList.tsx` (NEW)
- `services/health-dashboard/src/components/sports/GameTimelineModal.tsx` (NEW)
- `services/health-dashboard/src/components/sports/TeamScheduleView.tsx` (NEW)
- `services/health-dashboard/src/components/sports/SportsTab.tsx` (MODIFY)
- `services/health-dashboard/src/hooks/useSportsData.ts` (NEW)

---

### Story 21.3: Implement Events Tab Historical Queries

**Goal:** Add historical event querying to complement real-time WebSocket stream

**Current State:** Only shows WebSocket stream from EventStreamViewer

**New Implementation:**

```typescript
EventsTab
├── Filter Bar (existing)
│   ├── Service filter
│   ├── Severity filter
│   └── Search query
├── Time Range Selector (NEW)
│   └── Last 1h / 6h / 24h / 7d
├── Event Stream (existing WebSocket)
│   └── Real-time events (auto-scroll)
└── Historical Events Section (NEW)
    ├── Query: dataApi.getEvents({ filters })
    ├── Pagination (100 events per page)
    ├── Click to expand event details
    └── Event statistics summary
```

**Tasks:**
1. Add time range selector component
2. Implement `dataApi.getEvents()` call with filters
3. Create event statistics summary component
   - Query: `dataApi.getEventsStats(period)`
   - Display: Total events, event types breakdown, top entities
4. Add pagination controls
5. Merge historical + real-time events intelligently
6. Add export functionality (CSV/JSON)

**Acceptance Criteria:**
- [ ] Time range selector filters historical events
- [ ] Historical events load from `/api/v1/events`
- [ ] Event statistics display at top of tab
- [ ] Pagination works for large result sets
- [ ] Export to CSV/JSON functional
- [ ] Filters apply to both historical and real-time events

**API Endpoints:**
```typescript
dataApi.getEvents({
  limit: 100,
  offset: 0,
  entity_id?: string,
  event_type?: string,
  start_time?: string,
  end_time?: string
})

dataApi.getEventsStats(period: '1h' | '6h' | '24h' | '7d')
```

**Files to Modify:**
- `services/health-dashboard/src/components/tabs/EventsTab.tsx`
- `services/health-dashboard/src/hooks/useEvents.ts` (NEW)

---

### Story 21.4: Implement Analytics Tab with Real Data

**Goal:** Replace mock data with real analytics from data-api backend

**Current State:** Shows placeholder charts with mock data

**New Implementation:**

```typescript
AnalyticsTab
├── Summary Cards (update with real data)
│   ├── Total Events (from API)
│   ├── Success Rate (calculated)
│   ├── Avg Latency (from metrics)
│   └── System Uptime (from health)
├── Performance Charts (replace mock data)
│   ├── Events Processing Rate (time series)
│   ├── API Response Time (time series)
│   ├── Database Write Latency (time series)
│   └── Error Rate (time series)
└── Service-Specific Analytics
    ├── WebSocket Ingestion metrics
    ├── Enrichment Pipeline metrics
    └── Sports Data service metrics (if configured)
```

**Tasks:**
1. Create `/api/v1/analytics` endpoint in data-api (if missing)
   - Aggregate metrics from InfluxDB
   - Return time-series data for charts
2. Update AnalyticsTab to query real data
3. Implement data transformation for Recharts
4. Add loading states and error handling
5. Add time range selector (1h, 6h, 24h, 7d)
6. Add export functionality

**Acceptance Criteria:**
- [ ] All summary cards show real metrics
- [ ] Charts display actual time-series data
- [ ] Data updates every 30 seconds
- [ ] Time range selector changes chart data
- [ ] Loading states show during data fetch
- [ ] Error handling for API failures

**API Endpoints:**
```typescript
dataApi.getAnalytics({
  period: '1h' | '6h' | '24h' | '7d',
  metrics: string[] // ['events_rate', 'latency', 'error_rate']
})
```

**Files to Modify:**
- `services/health-dashboard/src/components/tabs/AnalyticsTab.tsx`
- `services/health-dashboard/src/hooks/useAnalytics.ts` (NEW)
- `services/data-api/src/analytics_endpoints.py` (backend - if missing)

---

### Story 21.5: Implement Alerts Tab

**Goal:** Create full alerts management interface using data-api alerts endpoints

**Current State:** Placeholder tab with no functionality

**New Implementation:**

```typescript
AlertsTab
├── Alert Summary Cards
│   ├── Active Alerts count
│   ├── Warning count
│   ├── Critical count
│   └── Last alert time
├── Alerts List
│   ├── Filter by severity (all, info, warning, error, critical)
│   ├── Filter by service
│   ├── Alert cards with:
│   │   ├── Severity indicator
│   │   ├── Service name
│   │   ├── Message and details
│   │   ├── Timestamp
│   │   └── Actions: Acknowledge, Resolve, Dismiss
│   └── Pagination
└── Alert Configuration (optional)
    ├── View alert rules
    └── Link to configuration tab
```

**Tasks:**
1. Create alert types and interfaces
2. Implement `dataApi.getAlerts()` hook
3. Create AlertCard component with actions
4. Implement alert actions:
   - Acknowledge: `dataApi.acknowledgeAlert(id)`
   - Resolve: `dataApi.resolveAlert(id)`
   - Dismiss: `dataApi.dismissAlert(id)`
5. Add real-time alert updates via WebSocket
6. Add alert history view (past 24h)
7. Add alert notification badge in header

**Acceptance Criteria:**
- [ ] Alerts load from `/api/v1/alerts`
- [ ] Severity filtering works correctly
- [ ] Alert actions (acknowledge, resolve) call API
- [ ] Real-time alerts appear via WebSocket
- [ ] Alert history shows resolved alerts
- [ ] Notification badge shows active alert count
- [ ] Responsive design for mobile

**API Endpoints:**
```typescript
dataApi.getAlerts({ severity?, service?, status? })
dataApi.acknowledgeAlert(alertId)
dataApi.resolveAlert(alertId)
dataApi.dismissAlert(alertId)
```

**Files to Create:**
- `services/health-dashboard/src/components/tabs/AlertsTab.tsx` (REPLACE PLACEHOLDER)
- `services/health-dashboard/src/components/alerts/AlertCard.tsx` (NEW)
- `services/health-dashboard/src/hooks/useAlerts.ts` (NEW)
- `services/health-dashboard/src/types/alerts.ts` (NEW)

---

### Story 21.6: Update OverviewTab with Enhanced Health

**Goal:** Integrate Epic 17.2 enhanced health monitoring endpoints

**Current State:** Uses basic health endpoint, has enhanced health section but may need updates

**Tasks:**
1. Verify `apiService.getEnhancedHealth()` uses correct endpoint
2. Update health status cards to show more detailed metrics
3. Add service-specific health indicators
4. Integrate with alerts system (show critical alerts)
5. Add quick actions (restart service, view logs)

**Acceptance Criteria:**
- [ ] Enhanced health section shows all service dependencies
- [ ] Status indicators accurately reflect service health
- [ ] Quick actions functional from overview
- [ ] Critical alerts displayed prominently
- [ ] Metrics update every 30 seconds

**Files to Modify:**
- `services/health-dashboard/src/components/tabs/OverviewTab.tsx`
- `services/health-dashboard/src/components/EnhancedHealthStatus.tsx`

---

## 🏗️ Implementation Strategy

### Phase 0: Deploy Data API Service (Story 21.0) ⚠️ CRITICAL PREREQUISITE
**Goal:** Get the Epic 13 data-api service deployed and running
**Duration:** 1-2 hours
**Priority:** MUST BE COMPLETED FIRST

1. Build and start data-api container
2. Verify all endpoints accessible
3. Test InfluxDB connectivity
4. Verify nginx routing
5. Confirm dashboard can reach service

**Blockers Resolved:**
- ✅ Dashboard will stop showing connection errors
- ✅ All feature endpoints become accessible
- ✅ WebSocket connection can be established

### Phase 1: Core API Fixes (Stories 21.1, 21.6)
**Goal:** Fix fundamental API connection issues
**Duration:** 2-3 days
**Prerequisites:** Phase 0 completed, data-api running

1. Fix WebSocket connection
2. Update OverviewTab health monitoring
3. Verify all API client methods
4. Test basic connectivity

### Phase 2: Feature Data Integration (Stories 21.3, 21.4, 21.5)
**Goal:** Connect feature tabs to data-api
**Duration:** 4-5 days

1. Implement Events tab historical queries
2. Implement Analytics tab real data
3. Implement Alerts tab functionality
4. Test each tab thoroughly

### Phase 3: Sports Integration (Story 21.2)
**Goal:** Complete Epic 12 sports features in dashboard
**Duration:** 5-7 days

1. Complete setup wizard enhancement
2. Implement live games display
3. Implement historical data queries
4. Implement game timeline visualization
5. Implement schedule view
6. End-to-end testing

### Phase 4: Testing & Polish
**Duration:** 2-3 days

1. Integration testing across all tabs
2. Performance testing (query times, WebSocket stability)
3. Error handling verification
4. Mobile responsiveness testing
5. Documentation updates

---

## 📈 Success Metrics

### Performance Targets
- Historical query response time: <200ms (p95)
- WebSocket message latency: <100ms
- Dashboard initial load: <2s
- Tab switching: <500ms

### Quality Targets
- Zero console errors during normal operation
- 100% of API calls use correct client (`dataApi` vs `adminApi`)
- All tabs functional with real data
- Graceful degradation when services unavailable

### User Experience Targets
- All 12 tabs operational
- Real-time data updates visible
- Sports historical data accessible
- Alerts manageable through UI

---

## 🔗 Dependencies

### Upstream Dependencies
- ✅ Epic 13: API separation completed (admin-api vs data-api CODE)
- ✅ Epic 12: Sports InfluxDB persistence completed
- ✅ nginx routing configured correctly
- ✅ API client structure created (adminApi, dataApi)
- ❌ **Epic 13 DEPLOYMENT - NOT COMPLETED** (Story 21.0 resolves)

### Backend Readiness - CODE vs DEPLOYMENT STATUS
- ❌ **data-api service NOT RUNNING** (Story 21.0 deploys it)
- ✅ Events endpoints implemented (CODE exists, needs deployment)
- ✅ Devices endpoints implemented (CODE exists, needs deployment)
- ✅ Sports endpoints implemented (CODE exists, needs deployment)
- ⚠️ Analytics endpoints - verify implementation (CODE exists)
- ⚠️ Alerts endpoints - verify implementation (CODE exists)

**CRITICAL DISCOVERY:**
The entire data-api service architecture was **built but never deployed**. Story 21.0 is the missing deployment step that unblocks everything else.

---

## 🚨 Risks & Mitigation

### Risk 1: Analytics/Alerts Endpoints Missing
**Impact:** Medium  
**Probability:** Medium  
**Mitigation:**
- Verify endpoint existence first (Story 21.4, 21.5)
- If missing, create minimal implementation in data-api
- Use mock data temporarily if backend not ready
- Document required backend changes

### Risk 2: Performance Issues with Historical Queries
**Impact:** Medium  
**Probability:** Low  
**Mitigation:**
- Implement caching in frontend (5-minute TTL)
- Add pagination for large result sets
- Monitor query performance in InfluxDB
- Optimize InfluxDB queries if needed

### Risk 3: WebSocket Connection Stability
**Impact:** High  
**Probability:** Low  
**Mitigation:**
- Implement robust reconnection logic
- Add connection health monitoring
- Fallback to HTTP polling if WebSocket fails
- Test with network interruptions

---

## 📝 Testing Strategy

### Unit Tests
- API client methods (adminApi, dataApi)
- Hook logic (useEvents, useSportsData, useAlerts)
- Component rendering with mock data

### Integration Tests
- API connectivity tests
- WebSocket connection and reconnection
- Data flow from API to UI
- Filter and search functionality

### E2E Tests (Playwright)
1. Dashboard loads successfully
2. All tabs accessible and functional
3. Sports setup wizard completion flow
4. Live games display and updates
5. Historical data queries and display
6. Alert management actions
7. WebSocket real-time updates

### Performance Tests
- Query response times
- Dashboard load time
- WebSocket message latency
- Memory usage over 1-hour session

---

## 📚 Documentation Updates Required

1. **API_DOCUMENTATION.md**: Verify all data-api endpoints documented
2. **USER_MANUAL.md**: Update with new Sports tab features
3. **TROUBLESHOOTING_GUIDE.md**: Add WebSocket connection troubleshooting
4. **Implementation Summary**: Create `EPIC_21_SUMMARY.md` on completion

---

## 🎯 Definition of Done

- [ ] All 6 stories completed and tested
- [ ] WebSocket connection functional and stable
- [ ] Sports tab displays live + historical data
- [ ] Events, Analytics, Alerts tabs functional with real data
- [ ] Zero console errors during normal operation
- [ ] All API calls use correct endpoints
- [ ] Performance targets met
- [ ] Documentation updated
- [ ] E2E tests passing
- [ ] Code reviewed and merged
- [ ] Deployment successful
- [ ] User acceptance testing completed

---

## 👥 Story Assignment Recommendations

- **Story 21.1** (WebSocket): Frontend developer with WebSocket experience
- **Story 21.2** (Sports): Full-stack developer (requires both API and UI work)
- **Story 21.3** (Events): Frontend developer
- **Story 21.4** (Analytics): Full-stack developer (may need backend endpoint creation)
- **Story 21.5** (Alerts): Full-stack developer (may need backend endpoint creation)
- **Story 21.6** (Overview): Frontend developer

---

**Epic Created:** 2025-10-13  
**Last Updated:** 2025-10-13  
**Next Review:** After Story 21.1 completion

