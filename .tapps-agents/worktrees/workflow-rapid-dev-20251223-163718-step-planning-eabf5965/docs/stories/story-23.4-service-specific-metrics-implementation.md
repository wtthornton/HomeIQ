# Story 23.4: Service-Specific Metrics Implementation

## Story Overview

**Story ID**: 23.4  
**Epic**: 23 - Enhanced Dependencies Tab Real-Time Metrics  
**Story Type**: Backend Implementation  
**Priority**: Medium  
**Estimated Effort**: 3 weeks  
**Assigned To**: Backend Team  

## User Story

**As a** system administrator  
**I want** each microservice to implement its own event rate tracking and metrics collection  
**So that** the consolidated metrics system can accurately report per-service performance data  

## Acceptance Criteria

### Primary Criteria
- [ ] All 15 services implement event rate tracking logic
- [ ] Each service calculates events per second and events per hour
- [ ] Services track total events processed since startup
- [ ] Uptime tracking is accurate and consistent
- [ ] Metrics are calculated over 1-minute rolling window

### Secondary Criteria
- [ ] Services handle zero-event periods gracefully
- [ ] Metrics calculation doesn't impact service performance
- [ ] Error handling prevents metrics collection failures
- [ ] Services log metrics collection errors appropriately
- [ ] Memory usage for metrics tracking is minimal

## Technical Requirements

### Core Services Implementation

#### WebSocket Ingestion Service
```python
# websocket-ingestion/src/event_rate_tracker.py
class EventRateTracker:
    def __init__(self):
        self.event_timestamps = deque(maxlen=3600)  # 1 hour of timestamps
        self.total_events = 0
        self.start_time = datetime.now()
        self.lock = threading.Lock()
    
    def record_event(self, event_data: dict):
        """Record an event for rate calculation"""
        with self.lock:
            self.event_timestamps.append(datetime.now())
            self.total_events += 1
    
    def get_events_per_second(self) -> float:
        """Get events per second over last minute"""
        with self.lock:
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)
            recent_events = sum(1 for ts in self.event_timestamps if ts >= minute_ago)
            return recent_events / 60.0
    
    def get_events_per_hour(self) -> float:
        """Get events per hour over last minute"""
        return self.get_events_per_second() * 3600
    
    def get_total_events(self) -> int:
        """Get total events processed"""
        return self.total_events
    
    def get_uptime_seconds(self) -> float:
        """Get service uptime in seconds"""
        return (datetime.now() - self.start_time).total_seconds()

# websocket-ingestion/src/main.py
event_tracker = EventRateTracker()

@app.get("/api/v1/event-rate")
async def get_event_rate():
    """Get current event processing rate"""
    try:
        return {
            "events_per_second": event_tracker.get_events_per_second(),
            "events_per_hour": event_tracker.get_events_per_hour(),
            "total_events": event_tracker.get_total_events(),
            "uptime_seconds": event_tracker.get_uptime_seconds(),
            "service": "websocket-ingestion",
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
            "service": "websocket-ingestion",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

#### Enrichment Pipeline Service
```python
# enrichment-pipeline/src/processing_metrics.py
class ProcessingMetrics:
    def __init__(self):
        self.processed_events = 0
        self.processing_times = deque(maxlen=1000)
        self.start_time = datetime.now()
        self.lock = threading.Lock()
    
    def record_processing(self, processing_time: float):
        """Record a processing event"""
        with self.lock:
            self.processed_events += 1
            self.processing_times.append(processing_time)
    
    def get_events_per_second(self) -> float:
        """Calculate events per second over last minute"""
        with self.lock:
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)
            # Use processing_times to estimate recent events
            recent_events = len([t for t in self.processing_times if t >= minute_ago])
            return recent_events / 60.0
    
    def get_events_per_hour(self) -> float:
        """Calculate events per hour"""
        return self.get_events_per_second() * 3600
    
    def get_total_events(self) -> int:
        """Get total events processed"""
        return self.processed_events
    
    def get_uptime_seconds(self) -> float:
        """Get service uptime"""
        return (datetime.now() - self.start_time).total_seconds()

# enrichment-pipeline/src/main.py
processing_metrics = ProcessingMetrics()

@app.get("/api/v1/event-rate")
async def get_event_rate():
    """Get current processing rate"""
    try:
        return {
            "events_per_second": processing_metrics.get_events_per_second(),
            "events_per_hour": processing_metrics.get_events_per_hour(),
            "total_events": processing_metrics.get_total_events(),
            "uptime_seconds": processing_metrics.get_uptime_seconds(),
            "service": "enrichment-pipeline",
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
            "service": "enrichment-pipeline",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

#### Data API Service
```python
# data-api/src/api_metrics.py
class APIMetrics:
    def __init__(self):
        self.request_timestamps = deque(maxlen=3600)
        self.total_requests = 0
        self.start_time = datetime.now()
        self.lock = threading.Lock()
    
    def record_request(self):
        """Record an API request"""
        with self.lock:
            self.request_timestamps.append(datetime.now())
            self.total_requests += 1
    
    def get_requests_per_second(self) -> float:
        """Get requests per second over last minute"""
        with self.lock:
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)
            recent_requests = sum(1 for ts in self.request_timestamps if ts >= minute_ago)
            return recent_requests / 60.0
    
    def get_requests_per_hour(self) -> float:
        """Get requests per hour"""
        return self.get_requests_per_second() * 3600
    
    def get_total_requests(self) -> int:
        """Get total requests processed"""
        return self.total_requests
    
    def get_uptime_seconds(self) -> float:
        """Get service uptime"""
        return (datetime.now() - self.start_time).total_seconds()

# data-api/src/main.py
api_metrics = APIMetrics()

# Add middleware to track requests
@app.middleware("http")
async def track_requests(request, call_next):
    api_metrics.record_request()
    response = await call_next(request)
    return response

@app.get("/api/v1/event-rate")
async def get_event_rate():
    """Get current API request rate"""
    try:
        return {
            "events_per_second": api_metrics.get_requests_per_second(),
            "events_per_hour": api_metrics.get_requests_per_hour(),
            "total_events": api_metrics.get_total_requests(),
            "uptime_seconds": api_metrics.get_uptime_seconds(),
            "service": "data-api",
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
            "service": "data-api",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

### Data Services Implementation

#### Sports Data Service
```python
# sports-data/src/sports_metrics.py
class SportsMetrics:
    def __init__(self):
        self.api_calls = 0
        self.data_fetches = 0
        self.start_time = datetime.now()
        self.lock = threading.Lock()
    
    def record_api_call(self):
        """Record an external API call"""
        with self.lock:
            self.api_calls += 1
    
    def record_data_fetch(self):
        """Record a data fetch operation"""
        with self.lock:
            self.data_fetches += 1
    
    def get_events_per_second(self) -> float:
        """Get API calls per second (sports data is periodic)"""
        with self.lock:
            uptime_minutes = (datetime.now() - self.start_time).total_seconds() / 60
            if uptime_minutes > 0:
                return (self.api_calls + self.data_fetches) / (uptime_minutes * 60)
            return 0.0
    
    def get_events_per_hour(self) -> float:
        """Get events per hour"""
        return self.get_events_per_second() * 3600
    
    def get_total_events(self) -> int:
        """Get total events"""
        return self.api_calls + self.data_fetches
    
    def get_uptime_seconds(self) -> float:
        """Get service uptime"""
        return (datetime.now() - self.start_time).total_seconds()
```

#### Weather API Service
```python
# weather-api/src/weather_metrics.py
class WeatherMetrics:
    def __init__(self):
        self.weather_requests = 0
        self.enrichment_calls = 0
        self.start_time = datetime.now()
        self.lock = threading.Lock()
    
    def record_weather_request(self):
        """Record a weather API request"""
        with self.lock:
            self.weather_requests += 1
    
    def record_enrichment_call(self):
        """Record a weather enrichment call"""
        with self.lock:
            self.enrichment_calls += 1
    
    def get_events_per_second(self) -> float:
        """Get weather requests per second"""
        with self.lock:
            uptime_minutes = (datetime.now() - self.start_time).total_seconds() / 60
            if uptime_minutes > 0:
                return (self.weather_requests + self.enrichment_calls) / (uptime_minutes * 60)
            return 0.0
    
    def get_events_per_hour(self) -> float:
        """Get events per hour"""
        return self.get_events_per_second() * 3600
    
    def get_total_events(self) -> int:
        """Get total events"""
        return self.weather_requests + self.enrichment_calls
    
    def get_uptime_seconds(self) -> float:
        """Get service uptime"""
        return (datetime.now() - self.start_time).total_seconds()
```

### AI Services Implementation

#### AI Automation Service
```python
# ai-automation-service/src/ai_metrics.py
class AIMetrics:
    def __init__(self):
        self.analysis_requests = 0
        self.pattern_detections = 0
        self.suggestions_generated = 0
        self.start_time = datetime.now()
        self.lock = threading.Lock()
    
    def record_analysis_request(self):
        """Record an analysis request"""
        with self.lock:
            self.analysis_requests += 1
    
    def record_pattern_detection(self):
        """Record a pattern detection"""
        with self.lock:
            self.pattern_detections += 1
    
    def record_suggestion_generation(self):
        """Record a suggestion generation"""
        with self.lock:
            self.suggestions_generated += 1
    
    def get_events_per_second(self) -> float:
        """Get AI operations per second"""
        with self.lock:
            uptime_minutes = (datetime.now() - self.start_time).total_seconds() / 60
            if uptime_minutes > 0:
                total_operations = self.analysis_requests + self.pattern_detections + self.suggestions_generated
                return total_operations / (uptime_minutes * 60)
            return 0.0
    
    def get_events_per_hour(self) -> float:
        """Get events per hour"""
        return self.get_events_per_second() * 3600
    
    def get_total_events(self) -> int:
        """Get total events"""
        return self.analysis_requests + self.pattern_detections + self.suggestions_generated
    
    def get_uptime_seconds(self) -> float:
        """Get service uptime"""
        return (datetime.now() - self.start_time).total_seconds()
```

## Testing Requirements

### Unit Tests
- [ ] Each service's metrics calculation is accurate
- [ ] Event recording works correctly
- [ ] Uptime calculation is precise
- [ ] Error handling prevents crashes

### Integration Tests
- [ ] All services respond to event-rate endpoint
- [ ] Metrics are consistent across service restarts
- [ ] Performance impact is minimal
- [ ] Memory usage remains stable

### Performance Tests
- [ ] Metrics collection doesn't impact service performance
- [ ] Memory usage for metrics tracking is <1MB per service
- [ ] Endpoint response time is <50ms

## Definition of Done

- [ ] All 15 services implement metrics tracking
- [ ] Event-rate endpoints return accurate data
- [ ] Performance impact is minimal
- [ ] Error handling is comprehensive
- [ ] Unit tests achieve 90% coverage
- [ ] Integration tests pass
- [ ] Performance tests meet criteria
- [ ] Code review is completed

## Dependencies

### Internal Dependencies
- **Story 23.1**: Standardized Event Rate Endpoints (must be complete)
- Existing service infrastructure
- Service-specific business logic

### External Dependencies
- None

## Risks and Mitigations

### High Risk
- **Performance Impact**: Metrics collection may slow services
  - *Mitigation*: Use efficient data structures and minimal locking

### Medium Risk
- **Memory Usage**: Metrics tracking may consume too much memory
  - *Mitigation*: Use bounded collections and periodic cleanup

### Low Risk
- **Data Accuracy**: Metrics may be inaccurate during high load
  - *Mitigation*: Use atomic operations and proper locking

## Success Metrics

- **Implementation Coverage**: 100% of services implement metrics
- **Performance Impact**: <5% overhead for metrics collection
- **Memory Usage**: <1MB per service for metrics tracking
- **Data Accuracy**: Metrics match actual service activity

## Notes

This story provides the foundation for accurate per-service metrics. Each service must implement appropriate metrics tracking based on its specific functionality and workload patterns.
