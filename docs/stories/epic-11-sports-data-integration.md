# Epic 11: NFL & NHL Sports Data Integration - Brownfield Enhancement

**Status:** 🔄 IN PROGRESS (Critical Bug Fixes Required)  
**Created:** October 12, 2025  
**Hotfix Applied:** October 12, 2025 (nginx routing fix)  
**Bug Fixes Required:** October 19, 2025 (team persistence & HA integration)

---

## ⚠️ PRODUCTION HOTFIX APPLIED (Oct 12, 2025)

**Issue:** NHL data not accessible in production due to missing nginx routing  
**Fix:** Added `/api/sports/` proxy configuration to nginx.conf  
**Impact:** Critical feature now working - users can access NHL data  
**Architecture Change:** Simplified from dual sports services to single service (sports-data only)  

**Documentation:**
- Implementation: `implementation/sports-architecture-simplification-summary.md`
- Verification: `implementation/sports-architecture-simplification-verification-results.md`
- QA Gate: `docs/qa/gates/11.x-sports-architecture-simplification.yml`

**Status:** 🔄 IN PROGRESS - Critical Bug Fixes Required

## 🚨 CRITICAL BUGS FOUND (Oct 19, 2025)

**Issue 1: Team Persistence Broken**
- Team selections don't persist across service restarts
- POST endpoint only logs teams, doesn't save them
- GET endpoint reads from environment variables, not user data

**Issue 2: HA Automation Endpoints Broken**
- HA endpoints return "none" even for live games
- Cache key mismatch between main API and HA endpoints
- Event detector can't find games to monitor

**Issue 3: Event Detection Not Working**
- Event detector calls API with empty team lists
- No teams = No games monitored = No score change detection
- Webhook system exists but can't trigger events

**Impact**: Users cannot trigger HA automations when teams score

---

## Epic Goal

Enable users to monitor their favorite NFL and NHL teams with real-time game updates, statistics visualization, and smart alerting, integrated seamlessly into the existing HA Ingestor Dashboard with team-specific data fetching to optimize API usage.

## Epic Description

### Existing System Context

- **Current functionality:** HA Ingestor Dashboard monitors Home Assistant events, enriches with weather data, stores in InfluxDB
- **Technology stack:** React 18.2 + TypeScript, Python 3.11 + FastAPI, Docker, InfluxDB 2.7
- **Integration points:** Admin API (port 8004), Health Dashboard (port 3000), Enrichment Pipeline

### Enhancement Details

**What's being added:**
- New Sports Data Service (FastAPI) on port 8005
- Team selection interface in dashboard
- Live game monitoring cards with real-time updates
- Sports tab in dashboard with Recharts visualizations
- API integration with ESPN/NHL Official APIs
- User preferences storage for selected teams

**How it integrates:**
- New microservice follows existing Docker Compose pattern
- Dashboard adds new tab using existing UI patterns
- Uses existing Nginx proxy configuration
- Stores preferences in local storage (Phase 1) or InfluxDB (Phase 2)
- Real-time updates via polling (consistent with existing patterns)

**Success criteria:**
- Users can select 2-5 favorite teams
- Live games display with <15s update latency
- API usage stays under 100 calls/day (free tier)
- No performance degradation to existing features
- Mobile-responsive design matches existing UI

## Stories

### Story 11.1: Sports Data Backend Service
Create FastAPI service for sports data fetching with team-specific filtering, caching, and ESPN/NHL API integration.

**Key Tasks:**
- FastAPI service structure
- ESPN/NHL API clients
- Team-based filtering logic
- Redis/in-memory caching (15s TTL)
- Health check endpoint
- Docker container configuration

### Story 11.2: Team Selection UI & User Preferences
Implement 3-step setup wizard for team selection and preferences management interface.

**Key Tasks:**
- Setup wizard component (3 steps)
- Team grid selection UI
- Search/filter functionality
- Preferences storage (localStorage)
- Empty state handling
- Team management interface

### Story 11.3: Live Games Display & Real-Time Updates
Create live game cards with real-time score updates, animations, and game status indicators.

**Key Tasks:**
- LiveGameCard component with animations
- Real-time polling (30s intervals)
- Score change animations
- Game status indicators
- Sports tab layout
- Mobile-responsive design

### Story 11.4: Statistics Visualization with Recharts
Add Recharts-powered visualizations for game statistics, score timelines, and team comparisons.

**Key Tasks:**
- ScoreTimeline component (LineChart)
- StatsComparison component (BarChart)
- Team performance charts
- Responsive chart containers
- Data transformation for charts
- Interactive tooltips

### Story 11.5: Team Persistence Implementation ⚠️ CRITICAL BUG FIX
Implement actual database storage for team selections to fix persistence across service restarts.

**Key Tasks:**
- Add SQLite table for user team preferences
- Implement team selection storage in POST endpoint
- Update GET endpoint to read from database
- Add team persistence to event detector
- Test team selections across service restarts
- Add migration for existing team data

**Acceptance Criteria:**
- [ ] Team selections persist across Docker restarts
- [ ] POST `/api/v1/user/teams` actually saves to database
- [ ] GET `/api/v1/user/teams` reads from database
- [ ] Event detector uses persisted team selections
- [ ] No data loss on service restart

### Story 11.6: HA Automation Endpoint Cache Fix ⚠️ CRITICAL BUG FIX
Fix cache key mismatch between main API and HA automation endpoints.

**Key Tasks:**
- Standardize cache key format across all endpoints
- Update HA endpoints to use correct cache keys
- Add fallback cache key lookups
- Test HA endpoints with live games
- Ensure HA endpoints return correct game status

**Acceptance Criteria:**
- [ ] HA endpoints return "playing" for live games
- [ ] HA endpoints return "upcoming" for scheduled games
- [ ] Cache key format consistent across all endpoints
- [ ] HA automation endpoints respond in <50ms
- [ ] No cache key mismatches

### Story 11.7: Event Detector Team Integration ⚠️ CRITICAL BUG FIX
Connect event detector to user's selected teams for proper game monitoring.

**Key Tasks:**
- Update event detector to use user's selected teams
- Fix team list passing to sports API client
- Test event detection with live games
- Verify score change detection works
- Test webhook delivery on score changes

**Acceptance Criteria:**
- [ ] Event detector monitors user's selected teams
- [ ] Score changes detected within 15 seconds
- [ ] Webhooks fired on score changes
- [ ] Game start/end events detected
- [ ] Event detection works with multiple teams

## Compatibility Requirements

- [x] Existing APIs remain unchanged (new service on separate port)
- [x] Database schema changes are backward compatible (no schema changes)
- [x] UI changes follow existing patterns (Tailwind CSS, React hooks)
- [x] Performance impact is minimal (separate service, cached data)

## Risk Mitigation

**Primary Risk:** API rate limit exhaustion affecting other services

**Mitigation:** 
- Team selection limits data fetching
- Caching with appropriate TTL
- API usage monitoring endpoint
- Warning system when approaching limits

**Rollback Plan:** 
- Stop sports-data Docker container
- Hide Sports tab in UI (feature flag)
- No database changes to rollback
- Existing functionality unaffected

## Definition of Done

- [ ] All 7 stories completed with acceptance criteria met
- [ ] Team selections persist across service restarts
- [ ] HA automation endpoints return correct game status
- [ ] Event detector monitors user's selected teams
- [ ] Score change detection and webhook delivery working
- [ ] Existing dashboard functionality verified (no regressions)
- [ ] Sports service integrates via Docker Compose
- [ ] API usage monitoring in place
- [ ] E2E tests for sports features
- [ ] Mobile responsive on iOS and Android
- [ ] Dark mode support consistent with existing UI
- [ ] Documentation updated (API docs, user guide)

## Dependencies

- ESPN API key or NHL Official API access
- Recharts library (add to package.json)
- No architectural changes required

## Estimated Effort

- Story 11.1: ✅ COMPLETE (backend service)
- Story 11.2: ✅ COMPLETE (team selection UI) 
- Story 11.3: ✅ COMPLETE (live games display)
- Story 11.4: ⏳ PENDING (statistics visualization)
- Story 11.5: 🔄 CRITICAL (team persistence) - 1 day
- Story 11.6: 🔄 CRITICAL (HA endpoint cache fix) - 0.5 days
- Story 11.7: 🔄 CRITICAL (event detector integration) - 0.5 days

**Total Remaining:** ~2 days (critical bug fixes)

---

**Status:** Draft  
**Created:** October 12, 2025  
**Epic Owner:** Product Team  
**Development Lead:** TBD

