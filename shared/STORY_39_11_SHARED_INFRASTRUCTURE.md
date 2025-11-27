# Story 39.11: Shared Infrastructure Setup - Documentation

## Overview

This document describes the shared infrastructure components set up for Epic 39 microservices.

## Components

### 1. Shared Correlation Cache

**Location:** `shared/correlation_cache.py`

**Features:**
- SQLite-backed persistent cache
- In-memory LRU cache for fast lookups
- Two-tier caching (memory + SQLite)
- Automatic cache invalidation
- Thread-safe for async usage

**Usage:**
```python
from shared.correlation_cache import get_correlation_cache

cache = get_correlation_cache(
    cache_db_path="/app/data/correlation_cache.db",
    max_memory_size=1000
)

# Get cached correlation
correlation = cache.get("entity1", "entity2", ttl_seconds=3600)

# Set cached correlation
cache.set("entity1", "entity2", correlation_value, ttl_seconds=3600)

# Get statistics
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate_percent']}%")
```

**Configuration:**
- Cache DB path: `/app/data/correlation_cache.db` (shared volume)
- Default TTL: 1 hour (3600 seconds)
- Max memory size: 1000 entries
- Target hit rate: >80%

### 2. Shared Database Connection Pool

**Location:** `shared/database_pool.py`

**Features:**
- Singleton pattern (one engine per database URL)
- Connection pooling optimization
- Async SQLAlchemy support
- Pool statistics

**Usage:**
```python
from shared.database_pool import create_shared_session_maker

AsyncSessionLocal = create_shared_session_maker(
    database_url="sqlite+aiosqlite:////app/data/ai_automation.db",
    pool_size=10,
    max_overflow=5
)

async with AsyncSessionLocal() as session:
    # Use session
    result = await session.execute(select(Model))
```

**Configuration:**
- Pool size: 10 per service (max 20 total)
- Max overflow: 5 per service
- Pool pre-ping: Enabled (verify connections)

### 3. Service-to-Service HTTP Client

**Location:** `shared/service_client.py`

**Features:**
- Automatic retry with exponential backoff
- Request timeout handling
- Health check support
- Singleton pattern for client reuse

**Usage:**
```python
from shared.service_client import get_service_client

# Get client for data-api
client = get_service_client(
    "data-api",
    base_url="http://data-api:8006"
)

# Make GET request
data = await client.get("/api/v1/events")

# Make POST request
result = await client.post("/api/v1/query", json={"query": "..."})

# Health check
health = await client.health_check()
```

**Pre-configured Services:**
- `data-api`: http://data-api:8006
- `ai-query-service`: http://ai-query-service:8018
- `ai-automation-service`: http://ai-automation-service:8021
- `ai-training-service`: http://ai-training-service:8015
- `ai-pattern-service`: http://ai-pattern-service:8016

## Shared Infrastructure Configuration

### Docker Compose Setup

All services share:
- Database volume: `ai_automation_data:/app/data`
- Cache volume: `ai_automation_data:/app/data` (shared cache DB)
- Network: `homeiq-network`

### Environment Variables

```bash
# Shared database
DATABASE_URL=sqlite+aiosqlite:////app/data/ai_automation.db
DATABASE_PATH=/app/data/ai_automation.db

# Cache
CORRELATION_CACHE_DB=/app/data/correlation_cache.db

# Service URLs (for inter-service communication)
DATA_API_URL=http://data-api:8006
AI_QUERY_SERVICE_URL=http://ai-query-service:8018
AI_AUTOMATION_SERVICE_URL=http://ai-automation-service:8021
AI_TRAINING_SERVICE_URL=http://ai-training-service:8015
AI_PATTERN_SERVICE_URL=http://ai-pattern-service:8016
```

## Performance Targets

### Cache Performance
- Hit rate: >80%
- Memory cache lookup: <1ms
- SQLite cache lookup: <5ms

### Database Connection Pool
- Connection acquisition: <10ms
- Pool exhaustion: Should not happen (max 20 connections)
- Connection recovery: Automatic (pool_pre_ping)

### Service Communication
- Request timeout: 5 seconds (configurable)
- Retry attempts: 3 (with exponential backoff)
- Health check: <100ms

## Migration Notes

Services can now use shared infrastructure:

1. **Replace local cache** with `shared.correlation_cache`
2. **Replace local DB pool** with `shared.database_pool`
3. **Use service clients** for inter-service calls

## Next Steps

1. Migrate services to use shared correlation cache
2. Optimize connection pooling based on usage
3. Monitor cache hit rates and adjust TTLs
4. Add service discovery if needed

