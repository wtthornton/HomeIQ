# Service-Specific Metrics Enhancement - Summary

**Created:** 2026-01-14  
**Status:** Requirements & Planning Complete - Ready for Implementation  
**Epic:** Service Management Dashboard Enhancement

## Quick Overview

Enhance the service details popup to show **service-specific metrics** instead of generic ones. Currently all services show the same 4 fields (Service Name, Status, Container Status, Last Check). Each service should display unique, relevant metrics based on its function.

## Current Problem

- ❌ All services show identical generic metrics
- ❌ No performance indicators
- ❌ No operational insights
- ❌ Limited troubleshooting value

## Solution

- ✅ Service-specific metrics for each of 14 services
- ✅ Real-time metrics updates
- ✅ Visual indicators (status badges, progress bars, trends)
- ✅ Graceful fallback to generic metrics when unavailable

## Services & Key Metrics

### Core Services
1. **websocket-ingestion** - Events/min, connection status, error rates, InfluxDB writes
2. **data-api** - Requests/min, response times, cache hit rate, dependency health
3. **admin-api** - API gateway stats, aggregated service health
4. **ai-automation-service** - Query counts, model usage, costs, success rates
5. **influxdb** - Write/query ops, storage size, connection pool

### External Data Services
6. **weather-api** - API calls, cache hit rate, data freshness, quota usage
7. **sports-api** - Games tracked, update frequency, poll success rate
8. **carbon-intensity-service** - Current intensity, renewable %, data freshness
9. **electricity-pricing-service** - Current price, cheapest hours, data freshness
10. **air-quality-service** - AQI, PM levels, data freshness
11. **calendar-service** - Events processed, sync status, sync frequency
12. **smart-meter-service** - Current power, daily energy, reading success rate
13. **blueprint-index** - Blueprints indexed, search performance
14. **rule-recommendation-ml** - Recommendations generated, model accuracy

## User Stories (10 Stories)

### Phase 1: Foundation (Stories 5, 6, 7)
- **Story 5:** Metrics Data Collection Infrastructure (8 points)
- **Story 6:** Metrics Display Components (5 points)
- **Story 7:** Service Metrics Configuration (5 points)

### Phase 2: Core Services (Stories 1, 2, 9, 10)
- **Story 1:** WebSocket Ingestion Metrics (5 points)
- **Story 2:** Data API Metrics (5 points)
- **Story 9:** InfluxDB Metrics (5 points)
- **Story 10:** Admin API Metrics (3 points)

### Phase 3: External Services (Story 3)
- **Story 3:** External Data Services Metrics (8 points)

### Phase 4: AI Services (Story 4)
- **Story 4:** AI Automation Service Metrics (5 points)

### Phase 5: Polish (Story 8)
- **Story 8:** Real-Time Metrics Updates (3 points)

**Total Story Points:** 52 points  
**Estimated Duration:** 8-11 weeks

## Implementation Phases

1. **Phase 1:** Build infrastructure (2-3 weeks)
2. **Phase 2:** Core services metrics (2-3 weeks)
3. **Phase 3:** External services metrics (2-3 weeks)
4. **Phase 4:** AI services metrics (1-2 weeks)
5. **Phase 5:** Polish & optimization (1 week)

## Key Files

- **Requirements:** `docs/requirements/service-specific-metrics-enhancement.md`
- **Current Modal:** `services/health-dashboard/src/components/ServiceDetailsModal.tsx`
- **Service Definitions:** `services/health-dashboard/src/components/ServicesTab.tsx`
- **Example (RAG):** `services/health-dashboard/src/components/RAGDetailsModal.tsx`

## Next Steps

1. ✅ Requirements & Planning Complete
2. ⏭️ Review & Approval
3. ⏭️ Sprint Planning
4. ⏭️ Technical Design (Phase 1)
5. ⏭️ Prototype (websocket-ingestion)

---

**See full requirements:** `docs/requirements/service-specific-metrics-enhancement.md`
