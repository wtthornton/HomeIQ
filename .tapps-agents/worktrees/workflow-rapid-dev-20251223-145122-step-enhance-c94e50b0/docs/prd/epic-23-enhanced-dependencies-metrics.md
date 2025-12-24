# Epic 23: Enhanced Dependencies Tab Real-Time Metrics

## Epic Overview

**Epic ID**: 23  
**Epic Name**: Enhanced Dependencies Tab Real-Time Metrics  
**Epic Type**: Feature Enhancement  
**Priority**: High  
**Estimated Effort**: 8-10 weeks  
**Target Completion**: Q1 2025  

## Business Context

The HA Ingestor Dashboard's Dependencies tab currently shows static metrics (0 events/sec, 0 active APIs) that don't reflect the actual system state. This creates a poor user experience and limits operational visibility into the real-time performance of the microservices architecture.

## Problem Statement

**Current State**: The Dependencies tab displays hardcoded zero values for:
- Events per second
- Active API count
- Data source activity

**Business Impact**: 
- Poor operational visibility
- Inability to monitor system performance
- Reduced confidence in system reliability
- Limited troubleshooting capabilities

**User Pain Points**:
- Dashboard shows misleading "0" values when system is actually processing events
- No visibility into individual API performance
- Cannot identify which services are active vs inactive
- Missing granular metrics for capacity planning

## Solution Overview

Transform the Dependencies tab into a comprehensive real-time monitoring dashboard that provides:

1. **System-Wide Metrics**: Overall events/sec and events/hour across all services
2. **Per-API Metrics**: Individual performance metrics for each active API
3. **Service Status Tracking**: Active vs inactive API counts with detailed breakdown
4. **Real-Time Updates**: Polling-based metrics refresh every 5 seconds
5. **Enhanced UI**: Tabular display of per-API metrics with status indicators

## Success Criteria

### Primary Success Criteria
- [ ] Dependencies tab shows real-time events/sec and events/hour (not hardcoded zeros)
- [ ] Per-API metrics table displays individual service performance
- [ ] Active/inactive API counts accurately reflect system state
- [ ] Metrics update every 5 seconds via polling
- [ ] All 15 microservices expose event rate endpoints

### Secondary Success Criteria
- [ ] UI performance remains smooth with 5-second polling
- [ ] Error handling gracefully manages service unavailability
- [ ] Metrics are accurate within 5-second refresh window
- [ ] Dashboard loads within 2 seconds
- [ ] Zero WebSocket dependencies in UI layer

## Technical Approach

### Architecture Pattern
- **Polling-Based**: HTTP polling every 5 seconds (no WebSockets in UI)
- **Consolidated API**: Single `/real-time-metrics` endpoint aggregates all data
- **Service-Level Endpoints**: Each service exposes `/api/v1/event-rate` endpoint
- **Parallel Collection**: Admin API fetches metrics from all services concurrently

### Technology Stack
- **Frontend**: React hooks with polling (useRealTimeMetrics)
- **Backend**: FastAPI endpoints with async/await
- **Data Flow**: Service → Admin API → Frontend (polling)
- **Error Handling**: Graceful degradation with fallback values

## Dependencies

### Internal Dependencies
- **Epic 13**: Admin API service (must be operational)
- **Epic 17**: Health monitoring infrastructure
- **All Service Epics**: Each microservice needs event rate endpoint

### External Dependencies
- None

## Risks and Mitigations

### High Risk
- **Service Performance Impact**: 5-second polling across 15 services
  - *Mitigation*: Implement connection pooling and timeout handling
- **Data Accuracy**: Metrics may be slightly stale due to polling
  - *Mitigation*: Accept 5-second delay as acceptable for dashboard use

### Medium Risk
- **UI Performance**: Frequent updates may impact rendering
  - *Mitigation*: Implement efficient React state management and memoization
- **Service Availability**: Some services may be temporarily unavailable
  - *Mitigation*: Graceful error handling with fallback to "inactive" status

### Low Risk
- **Network Latency**: Polling requests may be slow
  - *Mitigation*: Implement request timeouts and parallel fetching

## Acceptance Criteria

### Epic-Level Acceptance
1. **Functional**: Dependencies tab displays real-time metrics for all active APIs
2. **Performance**: Metrics update every 5 seconds without UI lag
3. **Reliability**: System gracefully handles service unavailability
4. **Usability**: Clear visual indicators for active/inactive services
5. **Maintainability**: Clean separation between polling logic and UI components

### Quality Gates
- [ ] All 15 services implement event rate endpoints
- [ ] Admin API consolidates metrics successfully
- [ ] Frontend polling works without memory leaks
- [ ] Error handling covers all failure scenarios
- [ ] Performance testing shows <2s load time

## Business Value

### Immediate Value
- **Operational Visibility**: Real-time view of system performance
- **Issue Detection**: Quick identification of inactive services
- **Capacity Planning**: Per-API metrics for scaling decisions

### Long-term Value
- **System Reliability**: Proactive monitoring prevents outages
- **Performance Optimization**: Data-driven service improvements
- **User Confidence**: Accurate metrics build trust in system

## Out of Scope

- WebSocket-based real-time updates
- Historical metrics storage and trending
- Alerting based on metrics thresholds
- Custom dashboard configuration
- Metrics export functionality

## Success Metrics

### Technical Metrics
- **API Response Time**: <500ms for consolidated metrics endpoint
- **UI Update Frequency**: 5-second polling without performance degradation
- **Service Coverage**: 100% of services expose event rate endpoints
- **Error Rate**: <1% failed metric collection attempts

### Business Metrics
- **User Satisfaction**: Dashboard provides accurate system view
- **Operational Efficiency**: Faster issue identification and resolution
- **System Reliability**: Improved monitoring leads to better uptime

## Epic Completion Criteria

The epic is complete when:
1. All 15 microservices expose standardized event rate endpoints
2. Admin API provides consolidated real-time metrics endpoint
3. Dependencies tab displays accurate per-API metrics
4. UI updates every 5 seconds via polling
5. Error handling covers all service unavailability scenarios
6. Performance meets specified criteria
7. All acceptance criteria are validated
8. Documentation is updated

## Next Steps

1. **Story Breakdown**: Create detailed stories for each component
2. **Technical Design**: Finalize API specifications and data models
3. **Implementation Planning**: Assign stories to development sprints
4. **Testing Strategy**: Define testing approach for real-time metrics
5. **Deployment Planning**: Plan rollout strategy for new endpoints
