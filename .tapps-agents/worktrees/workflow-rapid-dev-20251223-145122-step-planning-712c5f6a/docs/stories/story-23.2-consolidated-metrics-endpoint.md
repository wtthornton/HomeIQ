# Story 23.2: Consolidated Real-Time Metrics Endpoint

## Story Overview

**Story ID**: 23.2  
**Epic**: 23 - Enhanced Dependencies Tab Real-Time Metrics  
**Story Type**: Backend API  
**Priority**: High  
**Estimated Effort**: 1.5 weeks  
**Assigned To**: Backend Team  

## User Story

**As a** frontend developer  
**I want** a single API endpoint that provides consolidated real-time metrics from all services  
**So that** the dashboard can efficiently display system-wide and per-API performance data  

## Acceptance Criteria

### Primary Criteria
- [ ] Admin API provides `/api/v1/real-time-metrics` endpoint
- [ ] Endpoint aggregates metrics from all 15 services in parallel
- [ ] Response includes system-wide events/hour totals
- [ ] Response includes per-API metrics array with individual service data
- [ ] Response includes active/inactive API counts
- [ ] Endpoint responds within 500ms under normal load

### Secondary Criteria
- [ ] Parallel service calls use async/await for performance
- [ ] Error handling gracefully manages service unavailability
- [ ] Response includes timestamp and data freshness indicators
- [ ] Endpoint is accessible without authentication
- [ ] Response includes service type categorization

## Technical Requirements

### API Specification
```json
GET /api/v1/real-time-metrics
Response: {
  "events_per_hour": 162720,
  "active_apis": [
    {
      "service_name": "websocket-ingestion",
      "port": 8001,
      "service_type": "core",
      "status": "active",
      "events_per_hour": 91800,
      "total_events": 2500000,
      "uptime_seconds": 86400,
      "last_activity": "2025-01-17T10:30:00Z",
      "error_message": null
    },
    {
      "service_name": "enrichment-pipeline",
      "port": 8002,
      "service_type": "core",
      "status": "active",
      "events_per_hour": 70920,
      "total_events": 1800000,
      "uptime_seconds": 86400,
      "last_activity": "2025-01-17T10:30:00Z",
      "error_message": null
    }
  ],
  "inactive_apis": 3,
  "data_sources_active": ["weather", "carbon", "electricity"],
  "timestamp": "2025-01-17T10:30:00Z",
  "collection_time_ms": 245
}
```

### Error Response
```json
{
  "events_per_hour": 0,
  "active_apis": [],
  "inactive_apis": 15,
  "data_sources_active": [],
  "timestamp": "2025-01-17T10:30:00Z",
  "error": "Failed to collect metrics from services",
  "collection_time_ms": 5000
}
```

## Implementation Details

### Service Configuration
```python
# In admin-api stats_endpoints.py
API_SERVICES = {
    "websocket-ingestion": {"port": 8001, "type": "core"},
    "enrichment-pipeline": {"port": 8002, "type": "core"},
    "admin-api": {"port": 8003, "type": "core"},
    "data-api": {"port": 8006, "type": "core"},
    "sports-data": {"port": 8005, "type": "data"},
    "weather-api": {"port": 8007, "type": "data"},
    "carbon-intensity-service": {"port": 8010, "type": "data"},
    "electricity-pricing-service": {"port": 8011, "type": "data"},
    "air-quality-service": {"port": 8012, "type": "data"},
    "calendar-service": {"port": 8013, "type": "data"},
    "smart-meter-service": {"port": 8014, "type": "data"},
    "log-aggregator": {"port": 8015, "type": "core"},
    "energy-correlator": {"port": 8017, "type": "analysis"},
    "ai-automation-service": {"port": 8018, "type": "ai"},
    "data-retention": {"port": 8080, "type": "core"}
}
```

### Main Endpoint Implementation
```python
@self.router.get("/real-time-metrics", response_model=Dict[str, Any])
async def get_real_time_metrics():
    """Get comprehensive real-time metrics for all APIs"""
    start_time = time.time()
    
    try:
        # Collect metrics from all services in parallel
        api_metrics = await self._get_all_api_metrics()
        data_sources = await self._get_active_data_sources()
        
        # Calculate system-wide totals
        total_events_per_hour = sum(
            api["events_per_hour"] for api in api_metrics["active_apis"]
        )
        
        collection_time = int((time.time() - start_time) * 1000)
        
        return {
            "events_per_hour": total_events_per_hour,
            "active_apis": api_metrics["active_apis"],
            "inactive_apis": api_metrics["inactive_apis"],
            "data_sources_active": data_sources,
            "timestamp": datetime.now().isoformat(),
            "collection_time_ms": collection_time
        }
        
    except Exception as e:
        logger.error(f"Error getting real-time metrics: {e}")
        return {
            "events_per_hour": 0,
            "active_apis": [],
            "inactive_apis": len(API_SERVICES),
            "data_sources_active": [],
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "collection_time_ms": int((time.time() - start_time) * 1000)
        }
```

### Parallel Metrics Collection
```python
async def _get_all_api_metrics(self):
    """Get metrics for all APIs in parallel"""
    active_apis = []
    inactive_apis = 0
    
    # Create tasks for all services
    tasks = []
    for service_name, config in API_SERVICES.items():
        task = self._get_api_metrics(service_name, config["port"], config["type"])
        tasks.append(task)
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for i, result in enumerate(results):
        service_name = list(API_SERVICES.keys())[i]
        if isinstance(result, Exception):
            logger.warning(f"Failed to get metrics for {service_name}: {result}")
            inactive_apis += 1
        elif result["status"] == "active":
            active_apis.append(result)
        else:
            inactive_apis += 1
    
    return {
        "active_apis": active_apis,
        "inactive_apis": inactive_apis
    }
```

### Individual Service Metrics Collection
```python
async def _get_api_metrics(self, service_name: str, port: int, service_type: str):
    """Get metrics for a specific API"""
    try:
        # Get event rate metrics
        event_rate_data = await self._get_service_event_rate(port)
        
        # Get health status
        health_data = await self._get_service_health(port)
        
        # Calculate metrics
        events_per_second = event_rate_data.get("events_per_second", 0)
        events_per_hour = events_per_second * 3600
        total_events = event_rate_data.get("total_events", 0)
        uptime_seconds = event_rate_data.get("uptime_seconds", 0)
        
        # Determine status
        status = "active" if events_per_second > 0 or health_data.get("status") == "healthy" else "inactive"
        
        return {
            "service_name": service_name,
            "port": port,
            "service_type": service_type,
            "status": status,
            "events_per_second": events_per_second,
            "events_per_hour": events_per_hour,
            "total_events": total_events,
            "uptime_seconds": uptime_seconds,
            "last_activity": datetime.now().isoformat(),
            "error_message": None
        }
        
    except Exception as e:
        logger.warning(f"Error getting metrics for {service_name}: {e}")
        return {
            "service_name": service_name,
            "port": port,
            "service_type": service_type,
            "status": "error",
            "events_per_second": 0,
            "events_per_hour": 0,
            "total_events": 0,
            "uptime_seconds": 0,
            "last_activity": None,
            "error_message": str(e)
        }
```

### Service Communication
```python
async def _get_service_event_rate(self, port: int):
    """Get event rate from a specific service"""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
            async with session.get(f"http://localhost:{port}/api/v1/event-rate") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"HTTP {response.status}")
    except Exception as e:
        logger.warning(f"Failed to get event rate from port {port}: {e}")
        return {
            "events_per_second": 0,
            "events_per_hour": 0,
            "total_events": 0,
            "uptime_seconds": 0
        }

async def _get_service_health(self, port: int):
    """Get health status from a specific service"""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1)) as session:
            async with session.get(f"http://localhost:{port}/health") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"status": "unhealthy"}
    except Exception:
        return {"status": "unreachable"}
```

## Testing Requirements

### Unit Tests
- [ ] Endpoint returns correct JSON structure
- [ ] Parallel service calls execute correctly
- [ ] Error handling manages service unavailability
- [ ] System-wide totals are calculated correctly

### Integration Tests
- [ ] All services are queried in parallel
- [ ] Response time is under 500ms
- [ ] Error responses are properly formatted
- [ ] Data aggregation is accurate

### Performance Tests
- [ ] Endpoint handles 50 concurrent requests
- [ ] Response time remains under 500ms under load
- [ ] Memory usage doesn't increase with repeated calls

## Definition of Done

- [ ] Endpoint implemented and tested
- [ ] Parallel service calls work correctly
- [ ] Error handling is comprehensive
- [ ] Response time meets requirements
- [ ] Unit tests achieve 90% coverage
- [ ] Integration tests pass
- [ ] Performance tests meet criteria
- [ ] Documentation is updated
- [ ] Code review is completed

## Dependencies

### Internal Dependencies
- **Story 23.1**: Standardized Event Rate Endpoints (must be complete)
- Admin API service infrastructure
- Async HTTP client capabilities

### External Dependencies
- None

## Risks and Mitigations

### High Risk
- **Performance Impact**: Parallel calls to 15 services may be slow
  - *Mitigation*: Use connection pooling and 2-second timeouts

### Medium Risk
- **Service Unavailability**: Some services may be down
  - *Mitigation*: Graceful error handling with fallback values

### Low Risk
- **Data Inconsistency**: Services may return different data formats
  - *Mitigation*: Strict JSON schema validation and error handling

## Success Metrics

- **Response Time**: <500ms average response time
- **Service Coverage**: 100% of services queried
- **Error Rate**: <5% failed service calls
- **Data Accuracy**: 100% of active services identified correctly

## Notes

This endpoint is the central aggregation point for all real-time metrics. It must be highly performant and reliable as it will be called every 5 seconds by the frontend.
