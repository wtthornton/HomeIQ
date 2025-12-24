# Story 27.1: Environment Health Dashboard Foundation

## Story Overview
**Story ID**: STORY-27.1  
**Epic**: EPIC-27 (HA Ingestor Setup & Recommendation Service Foundation)  
**Priority**: High  
**Story Points**: 8  
**Sprint**: Sprint 1  

## User Story
**As a** HA Ingestor user  
**I want** to see a comprehensive health dashboard showing my Home Assistant environment status  
**So that** I can quickly identify issues and understand my system's overall health  

## Acceptance Criteria
- [ ] Dashboard displays real-time health status of HA core
- [ ] Shows integration status (MQTT, Zigbee2MQTT, etc.)
- [ ] Displays device discovery status
- [ ] Shows performance metrics (response time, resource usage)
- [ ] Provides health score (0-100) with color coding
- [ ] Updates automatically every 30 seconds
- [ ] Responsive design works on mobile and desktop

## Technical Requirements

### Backend (FastAPI)
- Create `/api/health/environment` endpoint with response_model validation
- Implement lifespan context manager for health service initialization
- Use dependency injection for database session management
- Add proper async/await patterns for HA API calls
- Implement health scoring algorithm with configurable weights

### Frontend (React)
- Create `EnvironmentHealthCard` component with useState for state management
- Use useEffect hook for real-time updates (30-second polling)
- Implement Context API for sharing health status across components
- Create responsive TailwindCSS layout with color-coded health indicators
- Add error boundary for graceful error handling

### Database (SQLAlchemy 2.0)
- Use async_sessionmaker for async database access
- Implement context managers for proper session lifecycle
- Store health metrics in SQLite with proper transaction management
- Create health_metrics table with timestamp indexing

## Context7 Best Practices Applied
✅ FastAPI lifespan context manager pattern
✅ React useState/useEffect for real-time updates
✅ SQLAlchemy async session management
✅ Proper error handling with re-raise pattern
✅ Response model validation for API consistency

## Definition of Done
- [ ] Health dashboard component created and tested
- [ ] API endpoints return health status data
- [ ] Health scoring algorithm implemented
- [ ] Real-time updates working
- [ ] Responsive design verified
- [ ] Unit tests written and passing
- [ ] Integration tests completed
- [ ] Code reviewed and approved

## Dependencies
- HA Ingestor core services
- Home Assistant API access
- WebSocket infrastructure

## Risks
- **Risk**: HA API rate limiting
  - **Mitigation**: Implement caching and request throttling
- **Risk**: Performance impact on HA system
  - **Mitigation**: Lightweight health checks with configurable intervals
