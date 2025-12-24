# Epic 10: Sports API Integration

**Status:** ⚠️ ARCHIVED - Superseded by Epic 11  
**Priority:** ~~High~~ Reference Only  
**Epic Owner:** Sarah (Product Owner)  
**Technical Lead:** Winston (Architect)  
**Created:** October 11, 2025  
**Archived:** October 12, 2025

---

## ⚠️ ARCHIVE NOTICE

**This epic has been superseded by Epic 11 (NFL & NHL Sports Data Integration).**

**Why archived:**
- Epic 11 implemented a simpler solution using free ESPN API
- Frontend was built for Epic 11 architecture (sports-data service)
- API-SPORTS.io requires paid API key ($0-50/month)
- Current user requirements met by Epic 11 implementation

**Status of Implementation:**
- ✅ All stories completed (10.1-10.7)
- ✅ sports-api service fully functional
- ✅ Comprehensive test coverage (90%+)
- ⚠️ Service commented out in docker-compose.yml
- 📁 Code preserved in `services/sports-api/`

**To restore this service:**
1. Uncomment sports-api in docker-compose.yml
2. Add API_SPORTS_KEY to environment
3. Update frontend to use sports-api endpoints (8-10 hours)
4. Deploy and test

**See:** `docs/stories/epic-11-sports-data-integration.md` for active implementation.

---

## Epic Overview

Integrate API-SPORTS (NFL, NCAA, and NHL) into the Home Assistant Ingestor ecosystem to provide real-time sports data enrichment for Home Assistant events. This enables users to create automations based on live game data, scores, standings, and player statistics.

### Business Value

- **User Automation**: Enable sports-based Home Assistant automations (e.g., "Turn on TV when my team plays")
- **Real-Time Data**: Live scores updated every ~15 seconds during games
- **Multi-Sport Support**: NFL, NHL, and future NCAA coverage
- **Historical Analysis**: Store and query historical sports data for trends and analytics

### Technical Context

This epic implements a new microservice following established patterns from weather-api and enrichment-pipeline services. The architecture leverages:

- **aiohttp** for async HTTP client with connection pooling (Context7 KB best practices)
- **InfluxDB** for time-series sports data storage with optimized schema
- **Rate limiting** with token bucket algorithm to manage API quotas
- **Intelligent caching** to minimize API calls and maximize free tier usage

**Architecture Document:** `docs/architecture/sports-api-integration.md`

---

## Epic Goals

1. ✅ **Service Foundation**: Create sports-api microservice with proper structure
2. ✅ **API Integration**: Implement NFL and NHL API clients with shared authentication
3. ✅ **Data Storage**: Design and implement optimized InfluxDB schema for sports data
4. ✅ **Performance**: Implement rate limiting, caching, and batch writing
5. ✅ **Integration**: Connect with enrichment pipeline for event enrichment
6. ✅ **Monitoring**: Add health checks, metrics, and observability
7. ✅ **Quality**: Comprehensive testing (unit, integration, E2E)

---

## Stories

### 10.1 - Sports API Service Foundation
**Priority:** Critical  
**Story Points:** 8  
**Dependencies:** None

Create the foundational sports-api service structure, base API client, configuration management, and Docker deployment.

**Key Deliverables:**
- Service directory structure
- Base API client with aiohttp
- Configuration management (environment variables)
- Docker Compose integration
- Health check endpoint

---

### 10.2 - NFL Client Implementation
**Priority:** High  
**Story Points:** 13  
**Dependencies:** 10.1

Implement NFL-specific API client with endpoints for scores, standings, fixtures, players, and injuries.

**Key Deliverables:**
- NFL API client class
- Pydantic data models (NFLScore, NFLStanding, etc.)
- API endpoint methods (scores, standings, fixtures, injuries)
- Unit tests for NFL client
- Integration tests with mock API

---

### 10.3 - NHL Client Implementation
**Priority:** High  
**Story Points:** 8  
**Dependencies:** 10.1

Implement NHL-specific API client with endpoints for scores, standings, and fixtures.

**Key Deliverables:**
- NHL API client class
- Pydantic data models (NHLScore, NHLStanding)
- API endpoint methods (scores, standings, fixtures)
- Unit tests for NHL client
- Code reuse from NFL client

---

### 10.4 - InfluxDB Schema and Writer
**Priority:** Critical  
**Story Points:** 13  
**Dependencies:** 10.2, 10.3

Design and implement optimized InfluxDB schema for sports data with high-performance batch writer.

**Key Deliverables:**
- InfluxDB schema design (measurements, tags, fields)
- SportsInfluxDBWriter class with batch writing
- Retention policies configuration
- Write methods for all data types
- Query patterns and examples
- Unit tests for writer

---

### 10.5 - Rate Limiting and Caching
**Priority:** High  
**Story Points:** 8  
**Dependencies:** 10.1

Implement token bucket rate limiter and intelligent TTL-based caching to optimize API usage.

**Key Deliverables:**
- RateLimiter class with token bucket algorithm
- CacheManager with TTL support
- Circuit breaker pattern for API failures
- Cache hit/miss tracking
- Unit tests for rate limiter and cache

---

### 10.6 - Service Endpoints and Integration
**Priority:** High  
**Story Points:** 13  
**Dependencies:** 10.2, 10.3, 10.4, 10.5

Create HTTP endpoints for sports data access and integrate with enrichment pipeline.

**Key Deliverables:**
- REST API endpoints for NFL and NHL data
- Enrichment pipeline integration
- Admin API configuration endpoints
- Service endpoints class
- Integration tests

---

### 10.7 - Testing and Deployment
**Priority:** High  
**Story Points:** 8  
**Dependencies:** 10.6

Comprehensive testing suite and production deployment preparation.

**Key Deliverables:**
- Unit test coverage (90%+)
- Integration test suite
- E2E tests with Playwright
- Production Docker configuration
- Deployment documentation
- Monitoring and alerting setup

---

## Acceptance Criteria (Epic Level)

1. ✅ Sports API service deployed and running in Docker Compose
2. ✅ NFL and NHL live scores accessible via REST API
3. ✅ Sports data stored in InfluxDB with optimized schema
4. ✅ Rate limiting prevents API quota exhaustion
5. ✅ Cache hit rate > 60% for frequent queries
6. ✅ Health check endpoint returns service status
7. ✅ Unit test coverage > 90%
8. ✅ Integration tests pass for all API clients
9. ✅ Service integrates with enrichment pipeline
10. ✅ Documentation complete (architecture, API, deployment)

---

## Technical Constraints

1. **API Rate Limits**: Free tier typically 100-500 requests/day
2. **Update Cadence**: Live scores update every ~15 seconds
3. **Data Retention**: 2 years for events, 5 years for standings
4. **Response Time**: < 500ms for cached data, < 2s for API calls
5. **Availability**: 99% uptime excluding API-SPORTS outages

---

## Dependencies

### External Dependencies
- **API-SPORTS**: API key and service availability
- **InfluxDB**: Database running and configured
- **Docker**: Container orchestration

### Internal Dependencies
- **Shared Logging**: `shared/logging_config.py`
- **Enrichment Pipeline**: Integration point
- **Admin API**: Configuration management

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| API rate limit exhaustion | High | Medium | Intelligent caching, token bucket limiter |
| API-SPORTS service outage | Medium | Low | Circuit breaker, serve stale cache |
| InfluxDB write performance | Medium | Low | Batch writing, connection pooling |
| Schema design requires changes | Medium | Low | Versioned schema, migration support |
| Free tier insufficient | Low | Medium | Monitor usage, upgrade plan if needed |

---

## Definition of Done

- [ ] All 7 stories completed and marked Done
- [ ] All acceptance criteria met
- [ ] Code reviewed and merged to main
- [ ] Unit tests passing with >90% coverage
- [ ] Integration tests passing
- [ ] Service deployed to development environment
- [ ] Service deployed to production environment
- [ ] Documentation complete and published
- [ ] Architecture document updated with implementation notes
- [ ] QA validation passed
- [ ] Product Owner sign-off received

---

## Related Documents

- **Architecture**: `docs/architecture/sports-api-integration.md`
- **Summary**: `docs/SPORTS_API_ARCHITECTURE_SUMMARY.md`
- **Tech Stack**: `docs/architecture/tech-stack.md`
- **Source Tree**: `docs/architecture/source-tree.md`
- **Context7 KB**: `docs/kb/context7-cache/aiohttp-client-patterns.md`
- **Context7 KB**: `docs/kb/context7-cache/influxdb-python-patterns.md`

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-11 | 1.0 | Epic created from architecture document | Sarah (PO) |

---

## Notes

- Architecture designed by Winston (Architect) using Context7 KB for best practices
- Follows existing patterns from weather-api and enrichment-pipeline services
- Phase 1 uses in-memory caching; Phase 2 will add Redis
- NCAA support deferred to Phase 2 (future epic)
- Consider MLB, NBA, MLS in Phase 3 based on user demand

