# Epic 13: Admin API Service Separation - Brownfield Refactoring

**Status:** ✅ **COMPLETE**  
**Created:** 2025-10-13  
**Completed:** 2025-11-26  
**Epic Owner:** Architecture Team  
**Development Lead:** BMad Master Agent

---

## Epic Goal

Refactor the overloaded admin-api service into two specialized services: admin-api (system monitoring & control) and data-api (feature data hub), improving performance, reliability, and scalability while enabling future enhancements like sports data InfluxDB persistence and Home Assistant automation integration.

---

## Epic Description

### Existing System Context

**Current Functionality:**
- **Service**: admin-api (FastAPI) running on port 8003
- **Endpoints**: 60+ endpoints across 14 modules
- **Responsibilities**: 
  - System health monitoring (health checks, dependencies, service status)
  - Docker container management (start, stop, restart, logs)
  - System configuration management
  - HA event queries from InfluxDB
  - Device and entity browsing
  - Integration management
  - Alert management
  - Real-time WebSocket streaming
  - Metrics and analytics

**Technology Stack:**
- **Backend**: Python 3.11, FastAPI 0.104.1
- **Database**: InfluxDB 2.7 (queries for both system stats and feature data)
- **Deployment**: Docker Compose, nginx reverse proxy
- **Dashboard Integration**: All 12 tabs call admin-api on port 8003

**Integration Points:**
- Dashboard → nginx (port 3000) → admin-api (port 8003)
- Admin-api → InfluxDB (port 8086) for queries
- Admin-api → Docker socket for container management
- Admin-api → Other services for health checks

**Current Pain Points:**
1. **Overloaded Service**: 60+ endpoints with mixed concerns (system vs features)
2. **Performance Contention**: Heavy InfluxDB queries slow down health checks
3. **Single Point of Failure**: Both monitoring AND features unavailable if service fails
4. **Cannot Scale Independently**: Feature queries need more resources than health checks
5. **Maintenance Complexity**: 14 endpoint modules in single codebase

---

### Enhancement Details

**What's Being Changed:**

1. **Split admin-api into Two Services**
   - **admin-api** (port 8003, existing): System monitoring, Docker management, configuration
   - **data-api** (port 8006, NEW): Feature data, InfluxDB queries, HA automation integration

2. **Migrate ~40 Feature Endpoints to data-api**
   - Events endpoints (8) - HA event queries
   - Devices endpoints (5) - Device/entity browsing
   - Integration endpoints (7) - Integration management
   - Alert endpoints (5) - Alert system
   - Metrics endpoints (6) - Analytics queries
   - WebSocket endpoints (3) - Real-time streaming
   - Sports endpoints (NEW from Epic 12)
   - HA automation endpoints (NEW from Epic 12)

3. **Move Shared Code to shared/ Directory**
   - `auth.py` → `shared/auth.py` (reused by both)
   - `influxdb_client.py` → `shared/influxdb_query_client.py` (reused by both)
   - Authentication and authorization shared utilities

4. **Update Dashboard API Service Layer**
   - Create separate clients: `AdminApiClient` and `DataApiClient`
   - Update all dashboard components to use correct client
   - Abstract behind service layer (minimal component changes)

5. **Update Nginx Routing**
   - Path-based routing to admin-api vs data-api
   - Backward compatibility during migration
   - Clear URL structure for future maintainability

**How It Integrates:**

- **Infrastructure**: New data-api container added to docker-compose.yml
- **Database**: Both services query InfluxDB (admin-api: system metrics only, data-api: full access)
- **Authentication**: Shared auth module in `shared/auth.py`
- **Dashboard**: API service layer updated, component code mostly unchanged
- **Nginx**: Routing rules updated for path-based service selection
- **Service Discovery**: Both services registered in Docker Compose network

**Success Criteria:**

1. ✅ admin-api contains only system monitoring endpoints (~22)
2. ✅ data-api contains all feature endpoints (~45+)
3. ✅ Dashboard works with split architecture (all 12 tabs functional)
4. ✅ Health check response time improves by 50%+ (<50ms)
5. ✅ No regression in existing functionality
6. ✅ data-api can be scaled to 2-4 instances
7. ✅ Backward compatibility maintained during migration
8. ✅ Documentation updated (architecture, API docs)

---

## Stories

### Story 13.1: Create data-api Service Foundation

**Goal**: Create new data-api service with FastAPI foundation, Docker configuration, and basic health endpoint

**Key Tasks:**
- Create `services/data-api/` directory structure
- Setup FastAPI application with CORS middleware
- Create Dockerfile and Dockerfile.dev (follow admin-api pattern)
- Add to docker-compose.yml on port 8006
- Move shared code: `auth.py`, `influxdb_client.py` to `shared/`
- Update both services to import from `shared/`
- Create basic health endpoint: `GET /health`
- Setup logging with correlation middleware
- Unit tests for service initialization
- CI/CD pipeline integration (GitHub Actions)

**Acceptance Criteria:**
- [ ] data-api service builds successfully (Docker image)
- [ ] Service starts on port 8006
- [ ] Health endpoint responds: `GET http://localhost:8006/health`
- [ ] Shared code accessible from both admin-api and data-api
- [ ] No breaking changes to admin-api (still functional)
- [ ] Docker Compose starts all services including data-api
- [ ] Unit tests pass with >80% coverage
- [ ] Service logs showing structured logging

**Technical Notes:**
- Follow `services/admin-api/` structure exactly
- Use same FastAPI version (0.104.1)
- Reuse CORS configuration from admin-api
- InfluxDB client initialized (connection pooling)

---

### Story 13.2: Migrate Events & Devices Endpoints to data-api

**Goal**: Move events and devices endpoints from admin-api to data-api, update dashboard to use data-api

**Key Tasks:**
- Copy `events_endpoints.py` to data-api/src/
- Copy `devices_endpoints.py` to data-api/src/
- Update imports (use shared utilities)
- Register routers in data-api main.py
- Create InfluxDB query layer in data-api
- Add feature flag in admin-api: `DEPRECATED_ENDPOINTS_ENABLED=true`
- Update dashboard: `src/services/api.ts` to use data-api
- Create `DataApiClient` class
- Update dashboard components (Events tab, Devices tab)
- Update nginx: Route `/api/v1/events` → data-api
- Update nginx: Route `/api/v1/devices` → data-api
- Integration tests for both services
- Regression tests for dashboard tabs

**Acceptance Criteria:**
- [ ] Events endpoints functional in data-api
- [ ] Devices endpoints functional in data-api
- [ ] Dashboard Events tab works via data-api
- [ ] Dashboard Devices tab works via data-api
- [ ] admin-api endpoints return deprecation warnings (if feature flag enabled)
- [ ] Nginx correctly routes to data-api
- [ ] Response times: Events queries <200ms, Devices queries <100ms
- [ ] Integration tests pass for both services
- [ ] No regression in dashboard functionality

**Technical Notes:**
- Dashboard API service layer abstracts routing (components unchanged)
- Both services can run simultaneously during migration
- Feature flag allows gradual cutover

---

### Story 13.3: Migrate Remaining Feature Endpoints & WebSockets

**Goal**: Complete migration of all feature endpoints (alerts, metrics, integrations, WebSockets) to data-api

**Key Tasks:**
- Migrate `alert_endpoints.py` to data-api
- Migrate `metrics_endpoints.py` to data-api
- Migrate `integration_endpoints.py` to data-api
- Migrate `websocket_endpoints.py` to data-api
- Update dashboard components for all remaining tabs
- Update nginx routing for all feature endpoints
- Remove deprecated endpoints from admin-api (feature flag OFF)
- Clean up admin-api codebase (remove migrated modules)
- Update API documentation (OpenAPI/Swagger)
- Comprehensive regression testing (all 12 dashboard tabs)
- Performance testing (query load on data-api)
- Load testing (simulate multiple dashboard users)

**Acceptance Criteria:**
- [ ] All 11 feature-focused dashboard tabs use data-api (not admin-api)
- [ ] Only Health/System tabs use admin-api
- [ ] WebSocket connections work via data-api
- [ ] Alert system functional via data-api
- [ ] Integration management works via data-api
- [ ] admin-api contains only system monitoring endpoints
- [ ] admin-api codebase reduced by ~60% (cleaner, focused)
- [ ] All dashboard tabs functional (no regression)
- [ ] Performance targets met (admin-api <50ms, data-api <200ms)
- [ ] Load testing passes (4 concurrent dashboard users)

**Technical Notes:**
- WebSocket endpoint migration requires careful state management
- Alert delivery system may need refactoring
- Integration endpoints connect to service-controller (keep in admin-api or data-api?)

---

### Story 13.4: Sports Data & HA Automation Integration (Epic 12)

**Goal**: Integrate Epic 12 (sports InfluxDB + HA automation) into data-api, completing the feature hub

**Key Tasks:**
- Implement sports InfluxDB writer in sports-data service (Epic 12.1)
- Implement sports historical query endpoints in data-api (Epic 12.2)
- Implement HA automation endpoints in data-api (Epic 12.3)
- Add `/api/v1/sports/*` routes to data-api
- Add `/api/v1/ha/*` automation routes to data-api
- Create sports WebSocket stream in data-api
- Update dashboard Sports tab to use data-api
- Create HA automation examples (3+ YAML configs)
- E2E testing with Home Assistant test instance
- Documentation updates (API docs, HA integration guide)
- Performance benchmarking (query response times)

**Acceptance Criteria:**
- [ ] Sports historical queries functional via data-api
- [ ] HA automation endpoints respond <50ms
- [ ] Webhooks deliver within 30 seconds of events
- [ ] Dashboard Sports tab displays historical data
- [ ] Home Assistant automations working (3 examples tested)
- [ ] Sports WebSocket stream delivers updates
- [ ] API documentation complete (FastAPI /docs)
- [ ] HA integration guide published with YAML examples
- [ ] E2E tests pass with real HA instance

**Technical Notes:**
- Epic 12 and Epic 13 converge in this story
- data-api becomes the natural home for all feature APIs
- Sports data follows same pattern as events/devices

---

## Compatibility Requirements

- [x] **Existing admin-api Unchanged Initially**: Service continues running during migration
- [x] **Backward Compatibility**: Feature flags allow gradual cutover
- [x] **Dashboard Updates**: Service layer abstracts API changes from components
- [x] **Nginx Routing**: Path-based routing maintains URL structure
- [x] **No Data Migration**: InfluxDB data unchanged (only client changes)
- [x] **Docker Compose**: Both services run simultaneously during migration
- [x] **Environment Variables**: New vars with sensible defaults (backward compatible)
- [x] **Rollback Capability**: Can disable data-api and revert to admin-api

---

## Risk Mitigation

### Primary Risk: Dashboard Breakage During Migration

**Symptoms**: Tabs not loading, API errors, missing data

**Mitigation:**
- Phased rollout (one tab at a time)
- Feature flag in dashboard: `USE_DATA_API=false` (rollback switch)
- Dual routing in nginx (try data-api, fallback to admin-api)
- Comprehensive regression testing before each phase
- Monitoring dashboard error rates during migration

**Rollback**: Set `USE_DATA_API=false` → Dashboard reverts to admin-api → <5 minutes

---

### Secondary Risk: Nginx Configuration Errors

**Symptoms**: 502 Bad Gateway, routing to wrong service

**Mitigation:**
- Test nginx config before deployment: `nginx -t`
- Staged rollout (dev → staging → production)
- Keep old nginx.conf as backup
- Clear documentation of routing rules
- Health checks verify routing correctness

**Rollback**: Restore old nginx.conf → reload nginx → <2 minutes

---

### Tertiary Risk: InfluxDB Connection Pooling Issues

**Symptoms**: Connection exhaustion, slow queries, timeouts

**Mitigation:**
- Configure connection pools properly (max 10 connections per service)
- Monitor InfluxDB connection count
- Implement connection timeout (5 seconds)
- Circuit breaker pattern for InfluxDB failures
- Graceful degradation (return cached data if DB unavailable)

**Rollback**: Reduce data-api instances → <5 minutes

---

## Definition of Done

### Functional Requirements
- [x] admin-api contains only system monitoring endpoints (~22)
- [x] data-api contains all feature endpoints (~45+)
- [x] Dashboard functional with split architecture (all 12 tabs)
- [x] Home Assistant automations can query data-api
- [x] Sports data integrated (Epic 12)
- [x] Backward compatibility maintained

### Technical Requirements
- [x] Both services have >80% unit test coverage
- [x] Integration tests verify service communication
- [x] E2E tests cover dashboard with split APIs
- [x] Performance targets met (admin <50ms, data <200ms)
- [x] Load testing passes (4+ concurrent users)
- [x] Health checks functional for both services

### Quality Requirements
- [x] No regression in existing functionality
- [x] Response times meet SLA targets
- [x] Error handling graceful (fallback strategies)
- [x] Monitoring and alerting configured
- [x] Security boundaries clear (admin vs user auth)

### Documentation Requirements
- [x] Architecture documentation updated
- [x] API documentation current (FastAPI /docs for both)
- [x] Migration guide for users
- [x] Nginx routing documented
- [x] Troubleshooting guide updated
- [x] EXTERNAL_API_CALL_TREES.md updated

---

## Dependencies

**Infrastructure:**
- [x] InfluxDB 2.7 running (port 8086)
- [x] Docker Compose orchestration
- [x] Nginx reverse proxy
- [ ] Port 8006 available for data-api

**Code Dependencies:**
- [x] Existing admin-api codebase
- [x] FastAPI, aiohttp libraries
- [x] Shared utilities directory

**External Dependencies:**
- [x] Dashboard codebase (React/TypeScript)
- [ ] Home Assistant test instance (for E2E testing)

---

## Estimated Effort

**Story 13.1: data-api Foundation**
- Implementation: 2 days
- Testing: 1 day
- Total: 3 days

**Story 13.2: Events & Devices Migration**
- Implementation: 3 days
- Testing: 1 day
- Total: 4 days

**Story 13.3: Complete Endpoint Migration**
- Implementation: 3 days
- Testing: 2 days
- Total: 5 days

**Story 13.4: Sports & HA Integration**
- Implementation: 3 days
- Testing: 1 day
- Total: 4 days

**Epic Total:** 16 days (~3-4 weeks with buffer)

---

## Architecture Integration

### Service Comparison

| Aspect | admin-api | data-api |
|--------|-----------|----------|
| **Port** | 8003 | 8006 |
| **Endpoints** | ~22 | ~45+ |
| **Purpose** | System monitoring | Feature data access |
| **Users** | Ops team | Dashboard + HA |
| **InfluxDB** | Read-only system metrics | Full query access |
| **Scaling** | Single instance | 2-4 instances |
| **Performance SLA** | <50ms (p95) | <200ms (p95) |
| **Criticality** | HIGH (must always work) | MEDIUM (can degrade) |

### Nginx Routing Strategy

```nginx
# System monitoring (admin-api)
location /api/v1/health {
    proxy_pass http://admin-api:8003;
}
location /api/v1/monitoring {
    proxy_pass http://admin-api:8003;
}
location /api/docker/ {
    proxy_pass http://admin-api:8003;
}

# Feature data (data-api)
location /api/v1/events {
    proxy_pass http://data-api:8006;
}
location /api/v1/devices {
    proxy_pass http://data-api:8006;
}
location /api/v1/sports {
    proxy_pass http://data-api:8006;
}
location /api/v1/ha {
    proxy_pass http://data-api:8006;
}
location /api/v1/analytics {
    proxy_pass http://data-api:8006;
}
```

---

## Integration with Epic 12 (Sports InfluxDB)

**Epic 12 Dependencies on Epic 13**:

Epic 12 stories assume sports data and HA automation endpoints go into a service. With Epic 13, that service is **data-api**, not admin-api.

**Modified Epic 12 Implementation**:
- Story 12.1: Sports InfluxDB writer → sports-data service (unchanged)
- Story 12.2: Historical query endpoints → **data-api** (not admin-api)
- Story 12.3: HA automation endpoints → **data-api** (not admin-api)

**Benefits**:
- ✅ Natural separation: Sports features in feature service (data-api)
- ✅ admin-api stays clean (no sports endpoints)
- ✅ data-api becomes comprehensive feature hub
- ✅ HA automation endpoints logically grouped with other HA features

**Implementation Order**:
1. Complete Epic 13 Stories 1-3 (data-api exists and functional)
2. Implement Epic 12 (sports endpoints go into data-api)
3. Complete Epic 13 Story 4 (finalize integration)

---

## Validation Checklist

### Scope Validation
- [x] Epic requires 4 stories (appropriate for brownfield refactoring)
- [x] No new external dependencies (uses existing infrastructure)
- [x] Follows existing patterns (FastAPI, Docker, InfluxDB)
- [x] Integration complexity is manageable

### Risk Assessment
- [x] Risk to existing system is medium (requires careful migration)
- [x] Rollback plan is feasible (feature flags, nginx revert)
- [x] Testing approach comprehensive (unit, integration, E2E)
- [x] Phased approach minimizes risk

### Architectural Validation
- [x] Follows microservices best practices (separation of concerns)
- [x] Enables future enhancements (Epic 12, analytics, GraphQL)
- [x] Improves performance (query isolation)
- [x] Improves reliability (fault isolation)

---

## Story Manager Handoff

**For Story Manager:**

Please develop detailed user stories for this brownfield refactoring epic. Key considerations:

**Existing System Context:**
- Refactoring of existing admin-api service (Python 3.11 + FastAPI)
- Current architecture: Monolithic gateway (60+ endpoints)
- Running services: admin-api (8003), dashboard (3000), InfluxDB (8086)

**Integration Points:**
- New data-api service (port 8006)
- Shared utilities: `shared/auth.py`, `shared/influxdb_query_client.py`
- Dashboard API service layer: `services/health-dashboard/src/services/api.ts`
- Nginx reverse proxy: `services/health-dashboard/nginx.conf`
- Docker Compose: `docker-compose.yml`

**Existing Patterns to Follow:**
- FastAPI application structure (same as admin-api)
- InfluxDB query patterns (use AdminAPIInfluxDBClient as template)
- Docker container configuration (Alpine-based, multi-stage builds)
- Environment variable configuration (.env files)
- Health check endpoint structure

**Critical Compatibility Requirements:**
- ALL existing admin-api endpoints MUST continue working during migration
- Dashboard MUST work throughout migration (feature flags for gradual cutover)
- Nginx routing MUST support both services simultaneously
- InfluxDB queries MUST not degrade performance
- Each story must include comprehensive regression testing
- Rollback MUST be possible at any point (feature flags + nginx config)

**Development Sequence:**
1. Story 13.1: Foundation (data-api exists, can receive traffic)
2. Story 13.2: First migration (events + devices, prove the pattern)
3. Story 13.3: Complete migration (all feature endpoints moved)
4. Story 13.4: Enhancement (Epic 12 integration, new features)

**Epic 12 Integration**:
This epic creates the **data-api** service that will host Epic 12 (sports InfluxDB) endpoints. Epic 12 Stories 12.2 and 12.3 should implement endpoints in data-api (not admin-api).

The epic should maintain system integrity while properly separating system monitoring from feature data access.

---

## Related Epics

**Epic 12**: Sports Data InfluxDB Persistence & HA Automation Hub
- Depends on Epic 13 Story 13.1 (data-api exists)
- Stories 12.2 and 12.3 implement in data-api
- Can be executed in parallel with Epic 13

**Epic 14** (Future): GraphQL Federation
- Builds on Epic 13 (data-api)
- Adds GraphQL layer to data-api
- admin-api remains REST-only

---

## Phase Status

### ✅ Story 13.1: data-api Service Foundation - COMPLETE
- Created `services/data-api/` directory structure
- FastAPI application with health endpoint functional
- Docker configuration (Dockerfile, docker-compose.yml)
- Shared code moved to `shared/` directory (auth.py, influxdb_query_client.py)
- Service running on port 8006

### ✅ Story 13.2: Migrate Events & Devices Endpoints - COMPLETE
- Events endpoints migrated to data-api
- Devices endpoints migrated to data-api
- Dashboard API service updated with `DataApiClient` and `AdminApiClient`
- Dashboard Events and Devices tabs using data-api
- Nginx routing configured

### ✅ Story 13.3: Migrate Remaining Feature Endpoints - COMPLETE
- Alert endpoints migrated to data-api
- Metrics endpoints migrated to data-api
- Integration endpoints migrated to data-api
- admin-api cleaned up (migrated modules removed)
- All dashboard tabs functional with split architecture

### ✅ Story 13.4: Sports & HA Automation Integration - COMPLETE
- Story 13.4 was superseded and consolidated into Epic 12 Stories 12.2 and 12.3
- Sports endpoints integrated into data-api (Epic 12.2)
- HA automation endpoints integrated into data-api (Epic 12.3)
- Webhook event detector functional
- Sports InfluxDB writer integrated

## Completion Summary

**Epic Status:** ✅ **COMPLETE** - All Stories Implemented and Integrated

**Key Achievements:**
- ✅ admin-api refactored to contain only system monitoring endpoints (~22 endpoints)
- ✅ data-api created with all feature endpoints (~45+ endpoints)
- ✅ Dashboard fully migrated to use data-api for features
- ✅ Shared utilities moved to `shared/` directory
- ✅ Nginx routing configured for path-based service selection
- ✅ Sports data and HA automation integrated (Epic 12 convergence)
- ✅ No regression in existing functionality
- ✅ Performance targets met (admin-api <50ms, data-api <200ms)

**Service Architecture:**
- **admin-api** (port 8003): System monitoring, Docker management, configuration
- **data-api** (port 8006): Feature data hub (events, devices, alerts, metrics, integrations, sports, HA automation)

**Document Version:** 4.0  
**Last Updated:** 2025-11-26  
**Created by:** BMad Master Agent  
**Analysis Document:** [implementation/analysis/ADMIN_API_SEPARATION_ANALYSIS.md](../../implementation/analysis/ADMIN_API_SEPARATION_ANALYSIS.md)

