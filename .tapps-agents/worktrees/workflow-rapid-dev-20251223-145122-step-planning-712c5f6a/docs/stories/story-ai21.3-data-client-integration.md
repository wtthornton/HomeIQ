# Story AI21.3: Data Client Integration

**Epic:** Epic-AI-21 - Proactive Conversational Agent Service  
**Story ID:** AI21.3  
**Priority:** Critical  
**Estimated Effort:** 6-8 hours  
**Dependencies:** Story AI21.1 (Service Foundation)

---

## User Story

**As a** developer,  
**I want** clients for external data sources,  
**so that** I can fetch weather, sports, and energy data.

---

## Acceptance Criteria

1. WeatherAPIClient (connects to weather-api:8009)
2. SportsDataClient (connects to sports-data:8005)
3. CarbonIntensityClient (connects to carbon-intensity:8010)
4. DataAPIClient (connects to data-api:8006)
5. Async HTTP clients (httpx 0.27+)
6. Retry logic with exponential backoff
7. Error handling and graceful degradation
8. Unit tests for all clients

---

## Tasks Breakdown

1. **Create clients directory structure** (15 min)
2. **Implement WeatherAPIClient** (1.5 hours)
3. **Implement SportsDataClient** (1.5 hours)
4. **Implement CarbonIntensityClient** (1 hour)
5. **Implement DataAPIClient** (1.5 hours)
6. **Add retry logic and error handling** (1 hour)
7. **Write unit tests** (1.5 hours)

**Total:** 6-8 hours

---

## Definition of Done

- [ ] All four clients implemented
- [ ] Async HTTP clients using httpx
- [ ] Retry logic with exponential backoff
- [ ] Error handling and graceful degradation
- [ ] Unit tests >90% coverage
- [ ] Code reviewed and approved

---

**Story Status:** In Progress  
**Assigned To:** Dev Agent  
**Created:** 2025-01-XX  
**Updated:** 2025-01-XX

