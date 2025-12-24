# Epic 39: Service Communication Documentation

**Epic 39, Story 39.16: Documentation & Deployment Guide**  
**Last Updated:** January 2025

## Overview

This document describes inter-service communication patterns for the Epic 39 microservices architecture.

## Communication Patterns

### 1. HTTP REST (Primary)

**Use Case:** Synchronous request/response communication between services.

**Implementation:**
- Uses `shared/service_client.py` for reliable HTTP communication
- Automatic retry with exponential backoff
- Request timeout handling
- Health check support

**Example:**
```python
from shared.service_client import get_service_client

# Query service calling Data API
data_api_client = get_service_client("data-api")
events = await data_api_client.get("/api/v1/events", params={"limit": 100})

# Query service calling Pattern service
pattern_client = get_service_client("ai-pattern-service")
patterns = await pattern_client.get("/api/v1/patterns", params={"device_id": "light.office"})
```

### 2. Shared Database (Secondary)

**Use Case:** Common data access across services.

**Shared Tables:**
- `patterns` - Pattern detection results
- `synergy_opportunities` - Synergy detection results
- `suggestions` - Automation suggestions
- `training_runs` - Model training runs
- `ask_ai_queries` - Query processing records

**Implementation:**
- SQLite database shared via Docker volume
- Connection pooling prevents exhaustion
- Each service uses `shared/database_pool.py`

**Example:**
```python
from shared.database_pool import create_shared_db_engine

engine = await create_shared_db_engine(
    database_url="sqlite+aiosqlite:////app/data/shared.db",
    pool_size=10,
    max_overflow=5
)
```

### 3. Direct InfluxDB Access (Data Queries)

**Use Case:** Time-series data queries.

**Pattern:**
- Services query InfluxDB directly (no intermediate service)
- No HTTP calls between services for time-series data
- Reduces latency and failure points

**Example:**
```python
from influxdb_client import InfluxDBClient

client = InfluxDBClient(url="http://influxdb:8086", token=token)
query_api = client.query_api()
results = query_api.query(query, org=org)
```

### 4. MQTT (Event Notifications)

**Use Case:** Real-time event notifications.

**Usage:**
- Pattern service publishes analysis completion events
- Services can subscribe for real-time updates
- Fire-and-forget pattern

**Example:**
```python
from ..clients.mqtt_client import MQTTNotificationClient

mqtt_client = MQTTNotificationClient(...)
await mqtt_client.publish("homeiq/analysis/complete", {"status": "success"})
```

## Service Communication Matrix

| From Service | To Service | Communication Method | Use Case |
|-------------|------------|---------------------|----------|
| Query Service | Data API | HTTP REST | Fetch entities/devices |
| Query Service | Pattern Service | HTTP REST | Get pattern context |
| Query Service | OpenAI | HTTP REST | LLM queries |
| Pattern Service | Data API | HTTP REST | Fetch events for analysis |
| Pattern Service | InfluxDB | Direct | Query time-series events |
| Pattern Service | MQTT | MQTT | Publish analysis events |
| Training Service | Data API | HTTP REST | Fetch training data |
| Training Service | OpenAI | HTTP REST | Synthetic data generation |
| Automation Service | Query Service | HTTP REST | Get query-based suggestions |
| Automation Service | Pattern Service | HTTP REST | Get pattern-based suggestions |
| Automation Service | Home Assistant | HTTP REST | Deploy automations |

## Service Dependencies

### Query Service Dependencies

**Direct Dependencies:**
- Data API - Entity and device lookups
- OpenAI API - Query processing
- Shared Database - Query and clarification storage

**Optional Dependencies:**
- Pattern Service - Pattern context (for enhanced suggestions)
- CorrelationCache - Entity correlation lookups

### Pattern Service Dependencies

**Direct Dependencies:**
- Data API - Event fetching
- Shared Database - Pattern/synergy storage
- MQTT Broker - Event notifications

**Optional Dependencies:**
- InfluxDB - Direct time-series queries (for efficiency)

### Training Service Dependencies

**Direct Dependencies:**
- Data API - Training data fetching
- OpenAI API - Synthetic data generation
- Shared Database - Training run storage

### Automation Service Dependencies

**Direct Dependencies:**
- Query Service - Query-based suggestions
- Pattern Service - Pattern-based suggestions
- Home Assistant - Automation deployment
- Shared Database - Suggestion storage

## Service URLs

### Internal (Docker Network)

All services use Docker service names for internal communication:

- `http://data-api:8006` - Data API
- `http://ai-query-service:8018` - Query Service
- `http://ai-pattern-service:8016` - Pattern Service
- `http://ai-training-service:8017` - Training Service
- `http://ai-automation-service-new:8021` - Automation Service (new)
- `http://influxdb:8086` - InfluxDB

### External (From Host)

Services exposed to host for external access:

- `http://localhost:8018` - Query Service
- `http://localhost:8016` - Pattern Service
- `http://localhost:8017` - Training Service
- `http://localhost:8021` - Automation Service (new)

## Error Handling

### Retry Logic

All HTTP requests use exponential backoff:
- **Max Retries**: 3
- **Initial Delay**: 1 second
- **Max Delay**: 10 seconds
- **Retry On**: Request errors, 5xx status codes

### Timeout Handling

- **Default Timeout**: 5 seconds
- **Configurable per service**: Set `timeout` parameter
- **Graceful Degradation**: Services continue if optional dependencies unavailable

### Health Checks

All services provide health check endpoints:
- `/health/health` - Basic health
- `/health/ready` - Readiness (database connectivity)
- `/health/live` - Liveness

**Example Health Check:**
```python
# Check if service is ready
client = get_service_client("ai-query-service")
is_ready = await client.health_check()
```

## Best Practices

### 1. Use Service Client

Always use `shared/service_client.py` for inter-service HTTP calls:
```python
# ✅ Good
client = get_service_client("data-api")
data = await client.get("/api/v1/events")

# ❌ Bad
response = await httpx.get("http://data-api:8006/api/v1/events")
```

### 2. Handle Failures Gracefully

Services should continue operating if optional dependencies fail:
```python
try:
    patterns = await pattern_client.get("/api/v1/patterns")
except Exception as e:
    logger.warning(f"Pattern service unavailable: {e}")
    patterns = []  # Continue without patterns
```

### 3. Use Shared Database for Common Data

Don't make HTTP calls for data that's in shared database:
```python
# ✅ Good - Direct database query
patterns = await db.execute(select(Pattern).where(...))

# ❌ Bad - HTTP call for shared data
patterns = await client.get("/api/v1/patterns")  # Unnecessary HTTP overhead
```

### 4. Batch Operations

Batch multiple requests when possible:
```python
# ✅ Good - Single batch request
entities = await data_api_client.get("/api/v1/entities", params={"ids": "id1,id2,id3"})

# ❌ Bad - Multiple requests
for id in ids:
    entity = await data_api_client.get(f"/api/v1/entities/{id}")
```

### 5. Cache Aggressively

Use shared cache for frequently accessed data:
```python
from shared.correlation_cache import CorrelationCache

cache = CorrelationCache(cache_db_path="/app/data/cache.db")
correlation = cache.get(entity1_id, entity2_id)
if correlation is None:
    correlation = compute_correlation(...)
    cache.set(entity1_id, entity2_id, correlation)
```

## Monitoring

### Service Health

Monitor all services:
```bash
for service in ai-query-service ai-pattern-service ai-training-service ai-automation-service-new; do
  curl http://localhost:$(get_service_port $service)/health/health
done
```

### Communication Metrics

Track inter-service communication:
- Request counts per service
- Error rates
- Latency percentiles
- Timeout occurrences

### Cache Performance

Monitor cache effectiveness:
- Hit rates per cache type
- Cache size and eviction rates
- Cache latency

## Related Documentation

- [Microservices Architecture](architecture/epic-39-microservices-architecture.md)
- [Deployment Guide](EPIC_39_DEPLOYMENT_GUIDE.md)
- [Shared Infrastructure](../shared/STORY_39_11_SHARED_INFRASTRUCTURE.md)

