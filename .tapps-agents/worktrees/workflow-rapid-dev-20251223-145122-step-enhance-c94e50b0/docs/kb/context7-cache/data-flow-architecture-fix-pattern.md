# Data Flow Architecture Fix Pattern - Admin API InfluxDB Integration

**Context7 KB Cache - Architectural Pattern**

**Project:** HA Ingestor  
**Pattern Type:** Data Flow Architecture Correction  
**Status:** Implementation ready  
**Created:** October 12, 2025  
**Impact:** High - Affects Admin API, Dashboard, and all data consumers

---

## Problem Statement

### Current (Incorrect) Architecture

The system was configured with Admin API and Dashboard receiving data directly from the Enrichment Pipeline via HTTP calls, bypassing InfluxDB as the time-series data store:

```
┌─────────────────────┐
│ Home Assistant      │
└──────────┬──────────┘
           │ WebSocket
           ↓
┌─────────────────────┐
│ WebSocket Ingestion │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│ Enrichment Pipeline │────┐
└──────────┬──────────┘    │
           │                │ HTTP calls
           │                │ (INCORRECT)
           ├────────────────┼──────────────┐
           │                │              │
           ↓                ↓              ↓
      ┌─────────┐    ┌──────────┐  ┌──────────┐
      │InfluxDB │    │Admin API │  │Dashboard │
      └─────────┘    └──────────┘  └──────────┘
         (write           ↑              ↑
          only)           │              │
                          └──────────────┘
                           HTTP (partial)
```

### Issues with Current Architecture

1. **InfluxDB Underutilized**: Time-series database only used for writes, not reads
2. **Data Duplication**: Services maintain their own metrics instead of using InfluxDB
3. **No Historical Analysis**: Direct service calls only provide current state
4. **Scalability Issues**: Each dashboard request triggers multiple service HTTP calls
5. **Inconsistent Data**: Different endpoints may return different data due to caching
6. **Performance**: Multiple HTTP calls instead of optimized database queries

---

## Correct Architecture

### Target (Correct) Architecture

```
┌─────────────────────┐
│ Home Assistant      │
└──────────┬──────────┘
           │ WebSocket
           ↓
┌─────────────────────┐
│ WebSocket Ingestion │────┐
└──────────┬──────────┘    │
           │                │
           ↓                │ Write metrics
┌─────────────────────┐    │
│ Enrichment Pipeline │────┤
└─────────────────────┘    │
                            │
           All services     │
           write metrics ───┘
                            │
                            ↓
                      ┌──────────┐
                      │ InfluxDB │
                      │(Time-    │
                      │ Series   │
                      │  Store)  │
                      └────┬─────┘
                           │ Query
                           ↓
                     ┌──────────┐
                     │Admin API │
                     │(Read     │
                     │ Layer)   │
                     └────┬─────┘
                          │ REST API
                          ↓
                     ┌──────────┐
                     │Dashboard │
                     │(UI)      │
                     └──────────┘
```

### Benefits of Correct Architecture

1. **InfluxDB as Source of Truth**: All time-series data stored and queried from one place
2. **Historical Analysis**: Access to all historical metrics and trends
3. **Better Performance**: Optimized database queries vs multiple HTTP calls
4. **Scalability**: Database handles read load efficiently
5. **Consistency**: All clients get same data from same source
6. **Aggregation**: Leverage InfluxDB's built-in aggregation functions

---

## Implementation Pattern

### 1. Service Layer (Write Path)

Each service writes metrics to InfluxDB:

```python
# services/enrichment-pipeline/src/main.py
class EnrichmentPipeline:
    async def process_event(self, event: dict):
        """Process event and write metrics to InfluxDB"""
        
        start_time = time.time()
        
        # Process event
        enriched = await self.enricher.enrich(event)
        
        # Write event data to InfluxDB
        await self.influx_client.write_event(enriched)
        
        # Write service metrics to InfluxDB
        processing_time = (time.time() - start_time) * 1000
        await self._write_service_metrics(processing_time)
    
    async def _write_service_metrics(self, processing_time: float):
        """Write service performance metrics to InfluxDB"""
        point = Point("service_metrics") \
            .tag("service", "enrichment-pipeline") \
            .tag("host", os.getenv("HOSTNAME", "unknown")) \
            .field("processing_time_ms", processing_time) \
            .field("events_processed", 1) \
            .field("success", 1) \
            .time(datetime.now())
        
        await self.influx_client.write_point(point)
```

### 2. Admin API Layer (Read Path)

Admin API queries InfluxDB for statistics:

```python
# services/admin-api/src/stats_endpoints.py
class StatsEndpoints:
    def __init__(self):
        self.influxdb_client = AdminAPIInfluxDBClient()
    
    async def initialize(self):
        """Connect to InfluxDB on startup"""
        await self.influxdb_client.connect()
    
    @router.get("/stats")
    async def get_statistics(period: str = "1h"):
        """Query InfluxDB for statistics"""
        
        # Query InfluxDB directly (not services)
        stats = await self.influxdb_client.get_all_service_statistics(period)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "period": period,
            "metrics": stats,
            "source": "influxdb"
        }
```

### 3. Dashboard Layer (UI/API Consumer)

Dashboard calls Admin API (unchanged):

```typescript
// services/health-dashboard/src/services/api.ts
export class ApiService {
  async getStatistics(period: string): Promise<Statistics> {
    // Call Admin API (which queries InfluxDB internally)
    const response = await fetch(`/api/v1/stats?period=${period}`);
    return await response.json();
  }
}
```

---

## Migration Strategy

### Phase 1: Preparation (Week 1)

**Goal**: Set up infrastructure without breaking existing functionality

1. **Add InfluxDB Client to Admin API**
   - Install `influxdb-client` package
   - Create `AdminAPIInfluxDBClient` class
   - Add connection management
   - Test connection

2. **Ensure Services Write Metrics**
   - Verify all services write to InfluxDB
   - Add missing service metrics if needed
   - Standardize metric naming

3. **Create Query Functions**
   - Implement InfluxDB query methods
   - Add error handling
   - Add logging

**Success Criteria**:
- Admin API can connect to InfluxDB
- All services writing metrics to InfluxDB
- Query functions tested in isolation

### Phase 2: Parallel Implementation (Week 2)

**Goal**: Run both old and new systems in parallel

1. **Implement Dual-Source Pattern**
   ```python
   async def get_statistics(period: str):
       # Get data from both sources
       influx_stats = await get_stats_from_influxdb(period)
       service_stats = await get_stats_from_services(period)
       
       # Log differences for analysis
       logger.info(f"InfluxDB: {influx_stats}")
       logger.info(f"Services: {service_stats}")
       
       # Return service stats (existing behavior)
       return service_stats
   ```

2. **Compare Results**
   - Log both sources
   - Identify discrepancies
   - Fix data quality issues
   - Tune queries

3. **Monitor Performance**
   - Measure query times
   - Check cache hit rates
   - Monitor InfluxDB load

**Success Criteria**:
- Both sources returning similar data
- InfluxDB queries performant (< 200ms)
- No production impact

### Phase 3: Feature Flag Rollout (Week 3)

**Goal**: Gradually shift traffic to InfluxDB

1. **Add Feature Flag**
   ```python
   USE_INFLUXDB_FOR_STATS = os.getenv("USE_INFLUXDB_STATS", "false") == "true"
   
   async def get_statistics(period: str):
       if USE_INFLUXDB_FOR_STATS:
           return await get_stats_from_influxdb(period)
       else:
           return await get_stats_from_services(period)
   ```

2. **Gradual Rollout**
   - Day 1: 10% of requests
   - Day 3: 50% of requests
   - Day 5: 100% of requests

3. **Monitor & Rollback Plan**
   - Watch error rates
   - Monitor response times
   - Keep rollback capability

**Success Criteria**:
- 100% traffic on InfluxDB
- Error rate unchanged
- Performance improved

### Phase 4: Cleanup (Week 4)

**Goal**: Remove old code and finalize

1. **Remove Old Code**
   - Delete service HTTP call code
   - Remove feature flags
   - Clean up unused functions

2. **Add Fallback**
   - Keep fallback to service calls
   - Only for emergencies
   - Log when fallback used

3. **Update Documentation**
   - Architecture diagrams
   - API documentation
   - Runbooks

**Success Criteria**:
- Old code removed
- Documentation updated
- Team trained

---

## Code Changes Required

### Files to Modify

#### 1. `services/admin-api/requirements.txt`
```diff
+ # InfluxDB client
+ influxdb-client==1.38.0
```

#### 2. `services/admin-api/src/influxdb_client.py` (NEW FILE)
```python
"""InfluxDB client for Admin API"""
# Full implementation in influxdb-admin-api-query-patterns.md
```

#### 3. `services/admin-api/src/stats_endpoints.py` (MAJOR REFACTOR)
```python
"""Statistics endpoints - refactored to use InfluxDB"""
from .influxdb_client import AdminAPIInfluxDBClient

class StatsEndpoints:
    def __init__(self):
        self.router = APIRouter()
        self.influxdb_client = AdminAPIInfluxDBClient()
        # Remove self.service_urls (old pattern)
```

#### 4. `services/admin-api/src/main.py` (UPDATE)
```python
"""Add InfluxDB client initialization"""
@app.on_event("startup")
async def startup():
    # Initialize InfluxDB connection
    await admin_service.stats_endpoints.initialize()
```

#### 5. `services/health-dashboard/src/components/AnimatedDependencyGraph.tsx` (UPDATE)
```typescript
// Fix data flow arrows to show:
// InfluxDB -> Admin API -> Dashboard
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_stats_endpoints.py
@pytest.mark.asyncio
async def test_get_statistics_from_influxdb(mock_influx_client):
    """Test stats endpoint queries InfluxDB"""
    
    stats_endpoint = StatsEndpoints()
    stats_endpoint.influxdb_client = mock_influx_client
    
    result = await stats_endpoint.get_statistics("1h")
    
    # Verify InfluxDB was queried
    assert mock_influx_client.get_all_service_statistics.called
    assert result["source"] == "influxdb"
```

### Integration Tests

```python
# tests/integration/test_stats_flow.py
@pytest.mark.asyncio
async def test_full_stats_pipeline():
    """Test complete flow: Write -> InfluxDB -> Read -> API"""
    
    # 1. Write test data to InfluxDB
    await write_test_metrics()
    
    # 2. Query via Admin API
    response = await client.get("/api/v1/stats?period=1h")
    
    # 3. Verify data returned correctly
    assert response.status_code == 200
    assert response.json()["source"] == "influxdb"
```

### Performance Tests

```python
@pytest.mark.performance
async def test_query_performance():
    """Verify queries complete in < 200ms"""
    
    start = time.time()
    await get_statistics("24h")
    duration = (time.time() - start) * 1000
    
    assert duration < 200, f"Query took {duration}ms"
```

---

## Monitoring & Observability

### Metrics to Track

1. **Query Performance**
   - Average query time
   - 95th percentile query time
   - Query error rate

2. **Data Quality**
   - Records returned per query
   - Missing data periods
   - Data freshness

3. **System Health**
   - InfluxDB connection status
   - Query cache hit rate
   - Fallback activation count

### Alerts

```yaml
# Alert when InfluxDB queries fail
- alert: AdminAPIInfluxDBQueryFailures
  expr: rate(admin_api_influxdb_errors[5m]) > 0.1
  annotations:
    summary: "Admin API InfluxDB queries failing"
    
# Alert when query performance degrades
- alert: AdminAPISlowQueries
  expr: admin_api_query_duration_p95 > 500
  annotations:
    summary: "Admin API queries taking >500ms"
```

---

## Rollback Plan

### If Issues Occur

1. **Immediate**: Set feature flag to disable InfluxDB queries
   ```bash
   kubectl set env deployment/admin-api USE_INFLUXDB_STATS=false
   ```

2. **Quick**: Revert to previous deployment
   ```bash
   kubectl rollout undo deployment/admin-api
   ```

3. **Emergency**: Direct traffic to backup instance
   ```bash
   kubectl scale deployment/admin-api-backup --replicas=3
   ```

---

## Success Metrics

### Technical Metrics
- ✅ 100% of statistics queries use InfluxDB
- ✅ Query response time < 200ms (95th percentile)
- ✅ Zero downtime during migration
- ✅ Error rate unchanged

### Business Metrics
- ✅ Dashboard load time improved
- ✅ Historical data access enabled
- ✅ Reduced service-to-service coupling
- ✅ Better scalability

---

## Related Documentation

- [InfluxDB Admin API Query Patterns](influxdb-admin-api-query-patterns.md)
- [InfluxDB Python Patterns](influxdb-python-patterns.md)
- [Data Enrichment KB Index](data-enrichment-kb-index.md)

---

**Status**: Ready for implementation  
**Priority**: High  
**Complexity**: Medium  
**Estimated Effort**: 3-4 weeks  
**Risk Level**: Medium (mitigation: feature flags, parallel implementation)

**Architectural Review**: Approved  
**Security Review**: No concerns  
**Performance Review**: Expected improvement

**Source**: HA Ingestor architectural analysis  
**Created**: 2025-10-12  
**Last Updated**: 2025-10-12

