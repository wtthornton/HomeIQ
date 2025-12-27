# BMAD Implementation Tasks - Detailed Breakdown

## Phase 1: Service Communication Infrastructure

### Task 1.1: HTTP Client Implementation
**BMAD ID**: `BMAD-001`
**Priority**: Critical
**Estimated Effort**: 2 days

#### Acceptance Criteria
- [ ] Standardized HTTP client with retry logic
- [ ] Exponential backoff implementation
- [ ] Circuit breaker pattern
- [ ] Structured logging for all calls
- [ ] Timeout and error handling

#### Implementation Details
```python
# shared/http_client.py
class ServiceHTTPClient:
    def __init__(self, service_name: str, base_url: str):
        self.service_name = service_name
        self.base_url = base_url
        self.session = aiohttp.ClientSession()
        self.retry_config = RetryConfig()
        self.circuit_breaker = CircuitBreaker()
    
    async def post(self, endpoint: str, data: dict) -> dict:
        """POST request with retry logic and circuit breaker"""
        pass
    
    async def get(self, endpoint: str) -> dict:
        """GET request with retry logic and circuit breaker"""
        pass
```

#### Test Cases
- [ ] Test retry logic with failed requests
- [ ] Test circuit breaker activation
- [ ] Test timeout handling
- [ ] Test logging output

### Task 1.2: Service Discovery
**BMAD ID**: `BMAD-002`
**Priority**: High
**Estimated Effort**: 1 day

#### Acceptance Criteria
- [ ] Service registry implementation
- [ ] Health check integration
- [ ] Service availability tracking
- [ ] Dynamic service discovery

#### Implementation Details
```python
# shared/service_discovery.py
class ServiceRegistry:
    def __init__(self):
        self.services = {}
        self.health_checker = HealthChecker()
    
    async def register_service(self, name: str, url: str):
        """Register a service with health checking"""
        pass
    
    async def get_service_url(self, name: str) -> str:
        """Get healthy service URL"""
        pass
    
    async def check_all_services(self) -> dict:
        """Check health of all registered services"""
        pass
```

### Task 1.3: Message Queue Implementation
**BMAD ID**: `BMAD-003`
**Priority**: Medium
**Estimated Effort**: 2 days

#### Acceptance Criteria
- [ ] Async message queue
- [ ] Dead letter queue for failed messages
- [ ] Message ordering preservation
- [ ] Performance monitoring

## Phase 2: WebSocket Ingestion Refactoring

### Task 2.1: Remove Internal Processing
**BMAD ID**: `BMAD-004`
**Priority**: Critical
**Estimated Effort**: 3 days

#### Current Code to Remove
```python
# services/websocket-ingestion/src/main.py
# REMOVE: Lines 312-332 (weather enrichment)
if self.weather_enrichment:
    processed_event = await self.weather_enrichment.enrich_event(processed_event)

# REMOVE: Lines 323-332 (batch processing)
if self.batch_processor:
    await self.batch_processor.add_event(processed_event)

# REMOVE: Lines 369-400 (InfluxDB writing)
await self.influxdb_writer.write_batch(batch)
```

#### New Implementation
```python
# services/websocket-ingestion/src/event_forwarder.py
class EventForwarder:
    def __init__(self, enrichment_url: str):
        self.enrichment_url = enrichment_url
        self.http_client = ServiceHTTPClient("enrichment-pipeline", enrichment_url)
    
    async def forward_event(self, event_data: dict) -> bool:
        """Forward event to enrichment pipeline"""
        try:
            response = await self.http_client.post("/api/v1/events", event_data)
            return response.get("success", False)
        except Exception as e:
            logger.error(f"Failed to forward event: {e}")
            return False
```

#### Acceptance Criteria
- [ ] Remove all internal processing logic
- [ ] Implement event forwarding
- [ ] Maintain connection stability
- [ ] Add comprehensive logging

### Task 2.2: Event Validation
**BMAD ID**: `BMAD-005`
**Priority**: High
**Estimated Effort**: 1 day

#### Implementation Details
```python
# services/websocket-ingestion/src/event_validator.py
class EventValidator:
    def validate(self, event_data: dict) -> dict:
        """Validate and normalize event data"""
        required_fields = ["event_type", "time_fired", "data"]
        
        for field in required_fields:
            if field not in event_data:
                raise ValidationError(f"Missing required field: {field}")
        
        return {
            "event_id": str(uuid.uuid4()),
            "timestamp": event_data.get("time_fired"),
            "source": "websocket-ingestion",
            "data": event_data
        }
```

### Task 2.3: HTTP Endpoints
**BMAD ID**: `BMAD-006`
**Priority**: Medium
**Estimated Effort**: 2 days

#### New Endpoints
```python
# services/websocket-ingestion/src/api_server.py
@router.post("/api/v1/events/forward")
async def forward_event(event_data: dict):
    """Manual event forwarding endpoint"""
    pass

@router.get("/api/v1/events/stats")
async def get_event_stats():
    """Get event forwarding statistics"""
    pass

@router.get("/api/v1/health")
async def health_check():
    """Enhanced health check with forwarding status"""
    pass
```

## Phase 3: Enrichment Pipeline Enhancement

### Task 3.1: HTTP Server Implementation
**BMAD ID**: `BMAD-007`
**Priority**: Critical
**Estimated Effort**: 3 days

#### Implementation Details
```python
# services/enrichment-pipeline/src/api_server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Enrichment Pipeline API")

class EventRequest(BaseModel):
    event_id: str
    timestamp: str
    source: str
    data: dict

@app.post("/api/v1/events")
async def receive_event(event: EventRequest):
    """Receive and process events from websocket service"""
    try:
        processed_event = await event_processor.process(event.data)
        await storage_client.store_event(processed_event)
        return {"success": True, "event_id": event.event_id}
    except Exception as e:
        logger.error(f"Event processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### Acceptance Criteria
- [ ] HTTP server with async request handling
- [ ] Event validation and processing
- [ ] Error handling and logging
- [ ] Performance monitoring

### Task 3.2: Enhanced Event Processing
**BMAD ID**: `BMAD-008`
**Priority**: High
**Estimated Effort**: 4 days

#### Implementation Details
```python
# services/enrichment-pipeline/src/enhanced_processor.py
class EnhancedEventProcessor:
    def __init__(self):
        self.weather_service = WeatherService()
        self.validator = EventValidator()
        self.normalizer = DataNormalizer()
    
    async def process(self, event_data: dict) -> dict:
        """Enhanced event processing pipeline"""
        # 1. Validate event
        validated_event = self.validator.validate(event_data)
        
        # 2. Enrich with weather data
        enriched_event = await self.weather_service.enrich(validated_event)
        
        # 3. Normalize data
        normalized_event = self.normalizer.normalize(enriched_event)
        
        # 4. Add processing metadata
        normalized_event["processing_metadata"] = {
            "processed_at": datetime.utcnow().isoformat(),
            "processor_version": "1.0.0",
            "processing_time_ms": processing_time
        }
        
        return normalized_event
```

### Task 3.3: Weather Integration
**BMAD ID**: `BMAD-009`
**Priority**: Medium
**Estimated Effort**: 2 days

#### Implementation Details
```python
# services/enrichment-pipeline/src/weather_service.py
class WeatherService:
    def __init__(self):
        self.cache = WeatherCache()
        self.api_client = OpenWeatherMapClient()
    
    async def enrich(self, event_data: dict) -> dict:
        """Enrich event with weather data"""
        location = self._determine_location(event_data)
        
        # Check cache first
        weather_data = await self.cache.get(location)
        if not weather_data:
            weather_data = await self.api_client.get_current_weather(location)
            await self.cache.set(location, weather_data, ttl=900)  # 15 minutes
        
        enriched_event = event_data.copy()
        enriched_event["weather"] = weather_data
        return enriched_event
```

## Phase 4: Data Storage Service

### Task 4.1: Storage Service Implementation
**BMAD ID**: `BMAD-010`
**Priority**: Critical
**Estimated Effort**: 4 days

#### Implementation Details
```python
# services/data-storage/src/storage_service.py
class DataStorageService:
    def __init__(self):
        self.influxdb_client = InfluxDBClient()
        self.batch_writer = BatchWriter()
    
    async def store_event(self, event_data: dict) -> bool:
        """Store event in InfluxDB with batching"""
        try:
            await self.batch_writer.add_event(event_data)
            return True
        except Exception as e:
            logger.error(f"Failed to store event: {e}")
            return False
    
    async def query_events(self, query_params: dict) -> list:
        """Query events from InfluxDB"""
        try:
            return await self.influxdb_client.query(query_params)
        except Exception as e:
            logger.error(f"Failed to query events: {e}")
            return []
```

#### API Endpoints
```python
# services/data-storage/src/api_server.py
@app.post("/api/v1/events")
async def store_event(event: dict):
    """Store event from enrichment pipeline"""
    success = await storage_service.store_event(event)
    return {"success": success}

@app.get("/api/v1/events")
async def query_events(
    start_time: str,
    end_time: str,
    entity_id: Optional[str] = None,
    limit: int = 100
):
    """Query events for admin API"""
    events = await storage_service.query_events({
        "start_time": start_time,
        "end_time": end_time,
        "entity_id": entity_id,
        "limit": limit
    })
    return {"events": events}
```

### Task 4.2: Database Optimization
**BMAD ID**: `BMAD-011`
**Priority**: High
**Estimated Effort**: 3 days

#### Implementation Details
```python
# services/data-storage/src/influxdb_optimizer.py
class InfluxDBOptimizer:
    def __init__(self):
        self.batch_size = 1000
        self.batch_timeout = 5.0
        self.write_queue = asyncio.Queue()
    
    async def optimize_schema(self):
        """Optimize InfluxDB schema for Home Assistant events"""
        # Create optimized measurement structure
        # Set up proper tags and fields
        # Configure retention policies
        pass
    
    async def batch_write(self, events: list):
        """Optimized batch writing to InfluxDB"""
        # Group events by measurement
        # Optimize point structure
        # Use batch write API
        pass
```

## Phase 5: Integration and Testing

### Task 5.1: End-to-End Integration
**BMAD ID**: `BMAD-012`
**Priority**: Critical
**Estimated Effort**: 3 days

#### Integration Test Suite
```python
# tests/integration/test_end_to_end.py
class TestEndToEndIntegration:
    async def test_complete_data_flow(self):
        """Test complete data flow from HA to storage"""
        # 1. Simulate HA event
        ha_event = self.create_sample_event()
        
        # 2. Send to websocket service
        ws_response = await self.websocket_client.forward_event(ha_event)
        assert ws_response["success"] == True
        
        # 3. Verify enrichment processing
        enrich_response = await self.enrichment_client.get_metrics()
        assert enrich_response["events_processed"] > 0
        
        # 4. Verify storage
        stored_events = await self.storage_client.query_events({
            "start_time": "1h ago",
            "limit": 1
        })
        assert len(stored_events) > 0
        
        # 5. Verify admin API
        admin_response = await self.admin_client.get_recent_events()
        assert len(admin_response["events"]) > 0
```

### Task 5.2: Performance Testing
**BMAD ID**: `BMAD-013`
**Priority**: High
**Estimated Effort**: 2 days

#### Performance Test Suite
```python
# tests/performance/test_throughput.py
class TestPerformance:
    async def test_event_throughput(self):
        """Test system can handle expected event volume"""
        # Send 1000 events in 1 minute (baseline: 17/min)
        events = self.generate_events(1000)
        
        start_time = time.time()
        for event in events:
            await self.websocket_client.forward_event(event)
        end_time = time.time()
        
        # Verify all events processed within time limit
        processing_time = end_time - start_time
        assert processing_time < 60  # Should complete in under 1 minute
        
        # Verify no events lost
        total_processed = await self.get_total_processed_events()
        assert total_processed >= 1000
```

### Task 5.3: Migration Implementation
**BMAD ID**: `BMAD-014`
**Priority**: Critical
**Estimated Effort**: 2 days

#### Migration Script
```python
# scripts/migrate_architecture.py
class ArchitectureMigration:
    async def migrate(self):
        """Execute zero-downtime migration"""
        # 1. Deploy new services
        await self.deploy_new_services()
        
        # 2. Start parallel processing
        await self.start_parallel_processing()
        
        # 3. Validate data consistency
        await self.validate_data_consistency()
        
        # 4. Switch traffic to new services
        await self.switch_traffic()
        
        # 5. Remove old services
        await self.remove_old_services()
    
    async def rollback(self):
        """Rollback to previous architecture if needed"""
        # Stop new services
        # Restart old services
        # Validate system health
        pass
```

## Service Communication Patterns

### HTTP API Standards

#### Request/Response Format
```python
# Standard request format
{
    "event_id": "uuid-v4",
    "timestamp": "2025-01-06T14:30:00Z",
    "source": "websocket-ingestion",
    "correlation_id": "req_12345",
    "data": {
        "event_type": "state_changed",
        "entity_id": "sensor.temperature",
        "state": "22.5",
        "attributes": {...}
    }
}

# Standard response format
{
    "success": true,
    "event_id": "uuid-v4",
    "processed_at": "2025-01-06T14:30:01Z",
    "processing_time_ms": 45,
    "correlation_id": "req_12345",
    "metadata": {
        "service": "enrichment-pipeline",
        "version": "1.0.0",
        "processing_steps": ["validation", "enrichment", "normalization"]
    }
}
```

#### Error Handling
```python
# Standard error format
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid event format",
        "details": {
            "field": "entity_id",
            "issue": "Missing required field",
            "expected": "string"
        }
    },
    "timestamp": "2025-01-06T14:30:00Z",
    "correlation_id": "req_12345"
}
```

### Service Discovery Configuration
```python
# shared/service_config.py
SERVICES = {
    "websocket-ingestion": {
        "url": "http://localhost:8001",
        "health_endpoint": "/api/v1/health",
        "timeout": 5.0,
        "retry_attempts": 3
    },
    "enrichment-pipeline": {
        "url": "http://localhost:8002",
        "health_endpoint": "/api/v1/health",
        "timeout": 10.0,
        "retry_attempts": 3
    },
    "data-storage": {
        "url": "http://localhost:8004",
        "health_endpoint": "/api/v1/health",
        "timeout": 5.0,
        "retry_attempts": 3
    }
}
```

## Success Criteria

### Performance Metrics
- [ ] **Event Processing**: 17+ events/minute (baseline requirement)
- [ ] **Latency**: <100ms end-to-end processing time
- [ ] **Throughput**: Support 10,000+ events/day
- [ ] **Reliability**: 99.9% event delivery success rate

### Quality Metrics
- [ ] **Code Coverage**: >90% for all new services
- [ ] **Test Coverage**: 100% critical paths covered
- [ ] **Error Rate**: <0.1% processing errors
- [ ] **Documentation**: Complete API documentation

### Operational Metrics
- [ ] **Service Health**: All services report healthy status
- [ ] **Data Consistency**: 100% data integrity validation
- [ ] **Monitoring**: Real-time metrics and alerting
- [ ] **Recovery**: <5 minute recovery time from failures

This detailed task breakdown provides the implementation roadmap for transforming the current monolithic architecture into a proper microservices architecture following BMAD methodology principles.
