# Story 27.2: HA Integration Health Checker

## Story Overview
**Story ID**: STORY-27.2  
**Epic**: EPIC-27 (HA Ingestor Setup & Recommendation Service Foundation)  
**Priority**: High  
**Story Points**: 5  
**Sprint**: Sprint 1  

## User Story
**As a** HA Ingestor user  
**I want** automated health checks for my Home Assistant integrations  
**So that** I can identify which integrations are working properly and which need attention  

## Acceptance Criteria
- [ ] Check MQTT broker connectivity and configuration
- [ ] Verify Zigbee2MQTT addon status and configuration
- [ ] Validate device discovery functionality
- [ ] Check integration API endpoints
- [ ] Verify authentication tokens and permissions
- [ ] Display detailed status for each integration
- [ ] Provide specific error messages for failed checks

## Technical Requirements

### Backend Integration Checker (FastAPI)
- Create `IntegrationHealthChecker` service class with async methods
- Implement MQTT broker connectivity test using aiohttp/asyncio
- Add Zigbee2MQTT addon status verification via HA API
- Create device discovery validation (check device registry sync)
- Implement API endpoint health checks with timeout handling
- Add HA token authentication validation
- Create detailed error reporting with structured logging

### Health Check Patterns (Context7 Best Practices)
- Use FastAPI dependency injection for checker service
- Implement async context managers for MQTT connections
- Add proper exception handling with specific error types
- Use Pydantic models for health check results
- Implement retry logic with exponential backoff

### Database Storage (SQLAlchemy 2.0)
- Store integration health history in SQLite
- Use async_sessionmaker for database operations
- Create integration_health table with status and error fields
- Implement proper transaction management

## Context7 Best Practices Applied
✅ FastAPI async dependency injection pattern
✅ Proper async/await for all I/O operations
✅ Pydantic models for data validation
✅ SQLAlchemy async session management
✅ Structured error handling and logging

## Definition of Done
- [ ] Integration health checker service implemented
- [ ] MQTT connectivity tests working
- [ ] Zigbee2MQTT status checks functional
- [ ] Device discovery validation complete
- [ ] API health checks implemented
- [ ] Authentication validation working
- [ ] Error reporting detailed and actionable
- [ ] Unit tests written and passing
- [ ] Integration tests completed

## Dependencies
- Home Assistant API access
- MQTT broker configuration
- Zigbee2MQTT addon access

## Risks
- **Risk**: Integration-specific API limitations
  - **Mitigation**: Graceful degradation with manual check instructions
- **Risk**: False positive health checks
  - **Mitigation**: Multiple validation methods and user feedback loop
