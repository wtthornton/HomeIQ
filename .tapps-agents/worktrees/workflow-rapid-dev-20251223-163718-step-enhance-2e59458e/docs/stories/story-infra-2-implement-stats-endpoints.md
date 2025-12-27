# Story INFRA-2: Implement Statistics Endpoints

**Epic:** Infrastructure Maintenance  
**Story ID:** INFRA-2  
**Priority:** Medium  
**Effort:** 3 Story Points  
**Status:** ✅ Complete  
**Dependencies:** INFRA-1 (completed)

## User Story

**As a** system administrator  
**I want** comprehensive statistics endpoints in the Admin API  
**So that** I can monitor system performance, track metrics, and identify issues across all services

## Problem Statement

The Admin API currently lacks dedicated statistics endpoints (`/stats`, `/stats/services`, `/stats/metrics`, etc.) that were removed during the INFRA-1 fix. These endpoints are needed to provide centralized access to system-wide metrics and performance data.

### Current State
- ✅ Admin API service is healthy and running
- ✅ Core endpoints working (`/health`, `/api/v1/services`, `/api/v1/alerts`)
- ❌ Statistics endpoints return 404 (not implemented)
- ❌ No centralized metrics aggregation

### Desired State
- Comprehensive `/stats` endpoint with system-wide metrics
- Service-specific statistics via `/stats/services`
- Time-series metrics via `/stats/metrics`
- Performance analytics via `/stats/performance`
- Real-time metrics dashboard endpoint

## Acceptance Criteria

### Must Have
- [ ] `GET /stats` - General statistics with configurable time period
  - Query params: `period` (1h, 24h, 7d, 30d), `service` (optional)
  - Returns: metrics, trends, alerts
  - Response time: < 500ms
- [ ] `GET /stats/services` - Statistics for all services
  - Returns: per-service metrics, health status, performance
  - Includes: websocket-ingestion, enrichment-pipeline, data-api, etc.
- [ ] `GET /stats/metrics` - Specific metrics with filtering
  - Query params: `metric_name`, `service`, `limit`
  - Returns: time-series metric data
  - Supports pagination
- [ ] `GET /stats/performance` - Performance statistics
  - Returns: throughput, latency, error rates
  - Includes recommendations for optimization
- [ ] `GET /stats/alerts` - Active alerts and warnings
  - Returns: prioritized list of system alerts
  - Includes severity levels

### Should Have
- [ ] Proper error handling for all endpoints
- [ ] Response caching for expensive queries
- [ ] OpenAPI/Swagger documentation
- [ ] Rate limiting to prevent abuse

### Nice to Have
- [ ] WebSocket endpoint for real-time metrics streaming
- [ ] Historical data comparison (week-over-week, etc.)
- [ ] Exportable metrics (CSV, JSON formats)

## Technical Details

### Architecture Decision
All statistics routes should be properly defined within the `_add_routes()` method of the `StatsEndpoints` class to avoid the indentation issues from INFRA-1.

### Data Sources
1. **InfluxDB** (primary) - Time-series metrics
2. **Service HTTP APIs** (fallback) - Direct service queries
3. **MQTT** (real-time) - Live event streams

### Response Models
```python
class StatisticsResponse(BaseModel):
    timestamp: datetime
    period: str
    metrics: Dict[str, Any]
    trends: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]
    source: str  # "influxdb" or "services-fallback"

class ServiceMetrics(BaseModel):
    service_name: str
    status: str
    uptime_seconds: float
    events_per_minute: float
    error_rate: float
    success_rate: float
    response_time_ms: float

class MetricData(BaseModel):
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str]
```

### Implementation Structure
```python
class StatsEndpoints:
    def __init__(self):
        self.router = APIRouter()
        self.influxdb_client = AdminAPIInfluxDBClient()
        self._add_routes()
    
    def _add_routes(self):
        """Add all statistics routes - ALL ROUTES MUST BE DEFINED HERE"""
        
        @self.router.get("/stats", response_model=StatisticsResponse)
        async def get_statistics(
            period: str = Query("1h"),
            service: Optional[str] = Query(None)
        ):
            # Implementation
            pass
        
        @self.router.get("/stats/services")
        async def get_services_stats():
            # Implementation
            pass
        
        # ... other routes here
```

## Implementation Plan

### Phase 1: Core Statistics Endpoint (1 hour)
1. Implement `get_statistics()` route handler
2. Add InfluxDB query logic for metrics aggregation
3. Implement service-level fallback
4. Add response caching (5-minute TTL)
5. Test with multiple time periods

### Phase 2: Service-Specific Stats (45 min)
1. Implement `get_services_stats()` route
2. Query all registered services
3. Aggregate metrics per service
4. Handle service timeouts gracefully
5. Test with healthy and unhealthy services

### Phase 3: Metrics & Performance (45 min)
1. Implement `get_metrics()` with filtering
2. Implement `get_performance_stats()`
3. Add pagination for large result sets
4. Generate performance recommendations
5. Test with various query combinations

### Phase 4: Alerts & Documentation (30 min)
1. Implement `get_alerts()` endpoint
2. Add alert prioritization logic
3. Generate OpenAPI documentation
4. Add request/response examples
5. Update API documentation

## Testing Strategy

### Unit Tests
```python
# tests/test_stats_endpoints.py
async def test_get_statistics_default_period():
    """Test statistics endpoint with default 1h period"""
    response = await client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "1h"
    assert "metrics" in data
    assert "trends" in data
    assert "alerts" in data

async def test_get_statistics_custom_period():
    """Test statistics with custom time period"""
    response = await client.get("/stats?period=24h")
    assert response.status_code == 200
    assert response.json()["period"] == "24h"

async def test_get_statistics_specific_service():
    """Test statistics filtered by service"""
    response = await client.get("/stats?service=websocket-ingestion")
    assert response.status_code == 200
    data = response.json()
    assert "websocket-ingestion" in str(data["metrics"])

async def test_get_services_stats():
    """Test all services statistics"""
    response = await client.get("/stats/services")
    assert response.status_code == 200
    data = response.json()
    assert "websocket-ingestion" in data
    assert "enrichment-pipeline" in data

async def test_get_metrics_with_filter():
    """Test metrics endpoint with filters"""
    response = await client.get(
        "/stats/metrics?metric_name=events_per_minute&service=websocket-ingestion&limit=100"
    )
    assert response.status_code == 200
    metrics = response.json()
    assert len(metrics) <= 100

async def test_get_performance_stats():
    """Test performance statistics"""
    response = await client.get("/stats/performance")
    assert response.status_code == 200
    data = response.json()
    assert "overall" in data
    assert "services" in data
    assert "recommendations" in data

async def test_stats_error_handling():
    """Test error handling for invalid requests"""
    response = await client.get("/stats?period=invalid")
    assert response.status_code == 400
    assert "detail" in response.json()
```

### Integration Tests
```bash
# Test with real services
curl -X GET "http://localhost:8003/stats?period=1h"
curl -X GET "http://localhost:8003/stats/services"
curl -X GET "http://localhost:8003/stats/metrics?limit=10"
curl -X GET "http://localhost:8003/stats/performance"
curl -X GET "http://localhost:8003/stats/alerts"

# Test error conditions
curl -X GET "http://localhost:8003/stats?period=invalid"  # Should return 400
curl -X GET "http://localhost:8003/stats?service=nonexistent"  # Should handle gracefully
```

### Performance Tests
```python
# Load test statistics endpoints
async def test_stats_performance():
    """Verify statistics endpoint responds within 500ms"""
    import time
    start = time.time()
    response = await client.get("/stats?period=24h")
    duration = time.time() - start
    assert duration < 0.5  # 500ms threshold
    assert response.status_code == 200
```

## API Documentation Examples

### GET /stats
```yaml
parameters:
  - name: period
    in: query
    schema:
      type: string
      enum: [1h, 24h, 7d, 30d]
      default: 1h
  - name: service
    in: query
    schema:
      type: string
    required: false

responses:
  200:
    description: Statistics retrieved successfully
    content:
      application/json:
        example:
          timestamp: "2025-10-18T18:00:00Z"
          period: "1h"
          metrics:
            total_events: 15234
            events_per_minute: 254
            error_rate: 0.02
            active_services: 12
          trends:
            - metric: "events_per_minute"
              values: [245, 250, 254, 260]
              timestamps: ["18:00", "18:15", "18:30", "18:45"]
          alerts:
            - level: "warning"
              service: "websocket-ingestion"
              message: "High memory usage: 85%"
          source: "influxdb"
```

## Dependencies

### Code Dependencies
- `aiohttp` - Async HTTP client for service queries
- `influxdb-client` - InfluxDB integration
- Existing `AdminAPIInfluxDBClient` class
- Existing service URL configuration

### Service Dependencies
- InfluxDB (must be healthy for primary data source)
- All monitored services (websocket, enrichment, data-api, etc.)

### Story Dependencies
- **INFRA-1** (completed) - Admin API must be healthy

## Risks and Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| InfluxDB unavailable | High | Low | Implement service-level fallback |
| Slow query performance | Medium | Medium | Add response caching, query optimization |
| Service timeout cascade | Medium | Low | Individual timeouts per service |
| High memory usage | Low | Low | Limit result set size, pagination |

## Success Metrics

- [ ] All 5 endpoints implemented and tested
- [ ] Response times < 500ms for cached queries
- [ ] Response times < 2s for uncached queries
- [ ] 100% test coverage for new code
- [ ] Zero errors in production for 24 hours
- [ ] Successful integration with Health Dashboard

## Documentation Updates

### Required
- [ ] OpenAPI/Swagger specification
- [ ] API endpoint documentation in README
- [ ] Response model documentation
- [ ] Example requests/responses

### Optional
- [ ] Architecture diagram showing data flow
- [ ] Performance tuning guide
- [ ] Troubleshooting guide

## Definition of Done

- [x] Story INFRA-1 completed (Admin API healthy)
- [ ] All 5 statistics endpoints implemented
- [ ] All routes properly scoped in `_add_routes()`
- [ ] Unit tests written and passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Performance tests passing (<500ms response)
- [ ] Error handling implemented
- [ ] Response caching implemented
- [ ] OpenAPI documentation generated
- [ ] Code review completed
- [ ] Deployed to development environment
- [ ] Smoke tests passing in dev
- [ ] Admin verified functionality
- [ ] Documentation updated

---

**Story Created:** 2025-10-18  
**Last Updated:** 2025-10-18  
**Estimated Completion:** 3-4 hours  
**Assigned To:** Development Team  

