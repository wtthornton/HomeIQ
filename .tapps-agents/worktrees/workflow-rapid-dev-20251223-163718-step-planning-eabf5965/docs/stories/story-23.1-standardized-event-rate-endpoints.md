# Story 23.1: Standardized Event Rate Endpoints

## Story Overview

**Story ID**: 23.1  
**Epic**: 23 - Enhanced Dependencies Tab Real-Time Metrics  
**Story Type**: Technical Infrastructure  
**Priority**: High  
**Estimated Effort**: 2 weeks  
**Assigned To**: Backend Team  

## User Story

**As a** system administrator  
**I want** all microservices to expose standardized event rate endpoints  
**So that** the dashboard can collect real-time performance metrics from each service  

## Acceptance Criteria

### Primary Criteria
- [ ] All 15 microservices implement `/api/v1/event-rate` endpoint
- [ ] Endpoint returns consistent JSON structure across all services
- [ ] Response includes events_per_second, events_per_hour, total_events, uptime_seconds
- [ ] Endpoint responds within 200ms under normal load
- [ ] Error handling returns appropriate HTTP status codes

### Secondary Criteria
- [ ] Endpoint includes service identification in response
- [ ] Metrics are calculated over 1-minute rolling window
- [ ] Zero values are returned when no events are processed
- [ ] Endpoint is accessible without authentication
- [ ] Response includes timestamp of last metric calculation

## Technical Requirements

### API Specification
```json
GET /api/v1/event-rate
Response: {
  "events_per_second": 12.5,
  "events_per_hour": 45000,
  "total_events": 1250000,
  "uptime_seconds": 86400,
  "service": "websocket-ingestion",
  "timestamp": "2025-01-17T10:30:00Z",
  "window_minutes": 1
}
```

### Error Response
```json
{
  "events_per_second": 0,
  "events_per_hour": 0,
  "total_events": 0,
  "uptime_seconds": 0,
  "service": "service-name",
  "error": "Service temporarily unavailable",
  "timestamp": "2025-01-17T10:30:00Z"
}
```

## Implementation Details

### Services to Update
1. **websocket-ingestion** (Port 8001) - Core event processing
2. **enrichment-pipeline** (Port 8002) - Data normalization
3. **admin-api** (Port 8003) - System monitoring
4. **data-api** (Port 8006) - Feature data hub
5. **sports-data** (Port 8005) - Sports data processing
6. **weather-api** (Port 8009) - Weather enrichment
7. **carbon-intensity-service** (Port 8010) - Carbon data
8. **electricity-pricing-service** (Port 8011) - Pricing data
9. **air-quality-service** (Port 8012) - Air quality data
10. **calendar-service** (Port 8013) - Calendar integration
11. **smart-meter-service** (Port 8014) - Smart meter data
12. **log-aggregator** (Port 8015) - Log processing
13. **energy-correlator** (Port 8017) - Energy analysis
14. **ai-automation-service** (Port 8018) - AI processing
15. **data-retention** (Port 8080) - Data lifecycle

### Implementation Pattern
```python
# Template for all services
@app.get("/api/v1/event-rate")
async def get_event_rate():
    """Get current event processing rate"""
    try:
        # Service-specific rate calculation
        current_rate = get_current_processing_rate()
        total_events = get_total_events_processed()
        uptime = get_service_uptime()
        
        return {
            "events_per_second": current_rate,
            "events_per_hour": current_rate * 3600,
            "total_events": total_events,
            "uptime_seconds": uptime,
            "service": "service-name",
            "timestamp": datetime.now().isoformat(),
            "window_minutes": 1
        }
    except Exception as e:
        logger.error(f"Error getting event rate: {e}")
        return {
            "events_per_second": 0,
            "events_per_hour": 0,
            "total_events": 0,
            "uptime_seconds": 0,
            "service": "service-name",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

## Service-Specific Implementations

### WebSocket Ingestion Service
```python
def get_current_processing_rate():
    return event_rate_monitor.get_current_rate(window_minutes=1) / 60

def get_total_events_processed():
    return event_rate_monitor.total_events

def get_service_uptime():
    return (datetime.now() - event_rate_monitor.start_time).total_seconds()
```

### Enrichment Pipeline Service
```python
def get_current_processing_rate():
    return processing_stats.get_events_per_second()

def get_total_events_processed():
    return processing_stats.total_processed

def get_service_uptime():
    return processing_stats.uptime_seconds
```

### Data API Service
```python
def get_current_processing_rate():
    return api_request_counter.get_requests_per_second()

def get_total_events_processed():
    return api_request_counter.total_requests

def get_service_uptime():
    return api_request_counter.uptime_seconds
```

## Testing Requirements

### Unit Tests
- [ ] Endpoint returns correct JSON structure
- [ ] Error handling returns appropriate responses
- [ ] Rate calculations are mathematically correct
- [ ] Uptime calculations are accurate

### Integration Tests
- [ ] All 15 services respond to endpoint
- [ ] Response times are within 200ms
- [ ] Concurrent requests don't impact performance
- [ ] Error responses are properly formatted

### Performance Tests
- [ ] Endpoint handles 100 concurrent requests
- [ ] Response time remains under 200ms under load
- [ ] Memory usage doesn't increase with repeated calls

## Definition of Done

- [ ] All 15 services implement the endpoint
- [ ] Endpoint returns consistent JSON structure
- [ ] Response times meet performance requirements
- [ ] Error handling is comprehensive
- [ ] Unit tests achieve 90% coverage
- [ ] Integration tests pass for all services
- [ ] Performance tests meet criteria
- [ ] Documentation is updated
- [ ] Code review is completed

## Dependencies

### Internal Dependencies
- Existing service infrastructure
- Event processing logic in each service
- Logging and monitoring systems

### External Dependencies
- None

## Risks and Mitigations

### High Risk
- **Service Performance Impact**: Adding metrics collection may slow services
  - *Mitigation*: Use efficient rate calculation algorithms and caching

### Medium Risk
- **Inconsistent Implementation**: Different services may implement differently
  - *Mitigation*: Provide detailed implementation template and code review

### Low Risk
- **Endpoint Discovery**: Services may not be discoverable
  - *Mitigation*: Use service registry or hardcoded port mapping

## Success Metrics

- **Implementation Coverage**: 100% of services implement endpoint
- **Response Time**: <200ms average response time
- **Error Rate**: <1% failed requests
- **Consistency**: 100% of responses follow JSON schema

## Notes

This story provides the foundation for all real-time metrics collection. Each service must implement this endpoint before the consolidated metrics system can function properly.
