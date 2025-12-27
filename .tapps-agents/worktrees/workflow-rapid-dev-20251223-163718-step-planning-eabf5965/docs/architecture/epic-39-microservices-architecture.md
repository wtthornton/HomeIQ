# Epic 39: AI Automation Service Microservices Architecture

**Epic 39, Story 39.16: Documentation & Deployment Guide**  
**Last Updated:** January 2025  
**Status:** ✅ Current Production Architecture

## Overview

The AI Automation Service has been modularized into focused microservices for independent scaling, improved maintainability, and optimized performance.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI Automation Microservices                       │
│                    (Epic 39 Modularization)                         │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│ ai-training-service  │  │ ai-pattern-service   │  │ ai-query-service     │
│   Port 8017          │  │   Port 8016          │  │   Port 8018          │
│                      │  │                      │  │                      │
│ • Model Training     │  │ • Pattern Detection  │  │ • Query Processing   │
│ • Synthetic Data     │  │ • Synergy Detection  │  │ • Entity Extraction  │
│ • Training Runs      │  │ • Daily Analysis     │  │ • Clarification      │
│                      │  │ • Pattern Learning   │  │ • Suggestion Gen     │
└──────────┬───────────┘  └──────────┬───────────┘  └──────────┬───────────┘
           │                         │                         │
           │                         │                         │
┌──────────▼─────────────────────────▼─────────────────────────▼───────────┐
│                    ai-automation-service (Refactored)                    │
│                        Port 8021                                         │
│                                                                          │
│ • Suggestion Generation                                                 │
│ • YAML Generation                                                       │
│ • Automation Deployment                                                 │
└──────────────────────┬──────────────────────────────────────────────────┘
                       │
                       │
┌──────────────────────▼──────────────────────────────────────────────────┐
│                          Shared Infrastructure                          │
│                                                                          │
│ • Shared Database (SQLite) - devices, patterns, suggestions, etc.       │
│ • CorrelationCache (SQLite-backed, two-tier)                            │
│ • Database Connection Pool (shared across services)                     │
│ • Service-to-Service HTTP Client (retry, timeout, health checks)        │
└──────────────────────┬──────────────────────────────────────────────────┘
                       │
                       │
┌──────────────────────▼──────────────────────────────────────────────────┐
│                    External Dependencies                                │
│                                                                          │
│ • InfluxDB (Port 8086) - Time-series data                               │
│ • Data API (Port 8006) - Event and device queries                       │
│ • Home Assistant (192.168.1.86:8123) - Device control                   │
│ • OpenAI API - LLM interactions                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Service Details

### Training Service (Port 8017)

**Purpose:** Handle all AI model training and synthetic data generation.

**Responsibilities:**
- Synthetic data generation (weather, calendar, occupancy, etc.)
- Model training (soft prompts, GNN synergy detection, home type classifier)
- Training run management and tracking

**Key Endpoints:**
- `POST /api/v1/training/{training_type}` - Start training job
- `GET /api/v1/training/runs` - List training runs
- `GET /api/v1/training/runs/{run_id}` - Get training run status

**Database:**
- Training runs table (shared database)

**Dependencies:**
- Shared database
- Data API (for fetching training data)
- OpenAI API (for synthetic data generation)

### Pattern Service (Port 8016)

**Purpose:** Pattern detection, analysis, and learning.

**Responsibilities:**
- Pattern detection (time-of-day, co-occurrence, anomaly)
- Synergy detection (2-level, 3-level, 4-level chains)
- Daily analysis scheduler (runs at 3 AM)
- Pattern learning and RLHF
- Quality scoring

**Key Endpoints:**
- `GET /api/v1/patterns` - Get patterns
- `GET /api/v1/synergies` - Get synergy opportunities
- `POST /api/v1/analysis/run` - Trigger manual analysis

**Database:**
- Patterns table (shared database)
- Synergy opportunities table (shared database)

**Dependencies:**
- Shared database
- Data API (for fetching events)
- MQTT broker (for notifications)
- Scheduled jobs (APScheduler)

### Query Service (Port 8018)

**Purpose:** Low-latency natural language query processing.

**Responsibilities:**
- Query processing and entity extraction
- Clarification detection and question generation
- Suggestion generation
- Low-latency optimization (<500ms P95 target)

**Key Endpoints:**
- `POST /api/v1/query/` - Process natural language query
- `POST /api/v1/query/{query_id}/refine` - Refine query
- `GET /api/v1/query/{query_id}/suggestions` - Get suggestions

**Database:**
- AskAI queries table (shared database)
- Clarification sessions table (shared database)

**Dependencies:**
- Shared database
- Data API (for entity lookups)
- OpenAI API (for query processing)
- Pattern/Query services (for context)

### Automation Service (Refactored) (Port 8021)

**Purpose:** Suggestion generation, YAML generation, and deployment.

**Responsibilities:**
- Suggestion generation (from patterns/synergies)
- YAML generation and validation
- Automation deployment to Home Assistant
- Safety validation

**Key Endpoints:**
- `POST /api/v1/suggestions/generate` - Generate suggestions
- `POST /api/v1/suggestions/{id}/approve` - Approve suggestion
- `POST /api/v1/deployment/deploy` - Deploy automation

**Database:**
- Suggestions table (shared database)
- Automation versions table (for rollback)

**Dependencies:**
- Shared database
- Home Assistant API (for deployment)
- Query service (for query-based suggestions)
- Pattern service (for pattern-based suggestions)

## Shared Infrastructure

### Correlation Cache (`shared/correlation_cache.py`)

**Purpose:** Two-tier caching for correlation computations.

**Features:**
- In-memory LRU cache (fast lookups)
- SQLite-backed persistent cache
- Automatic TTL expiration
- Cache statistics tracking

**Usage:**
```python
from shared.correlation_cache import CorrelationCache

cache = CorrelationCache(cache_db_path="/app/data/correlation_cache.db")
correlation = cache.get(entity1_id, entity2_id, ttl_seconds=3600)
if correlation is None:
    correlation = compute_correlation(...)
    cache.set(entity1_id, entity2_id, correlation, ttl_seconds=3600)
```

### Database Connection Pool (`shared/database_pool.py`)

**Purpose:** Shared SQLAlchemy async engine with connection pooling.

**Features:**
- Singleton pattern (one engine per database URL)
- Connection pooling (pool_size=10, max_overflow=5)
- Automatic connection verification (pool_pre_ping)

**Usage:**
```python
from shared.database_pool import create_shared_db_engine

engine = await create_shared_db_engine(
    database_url="sqlite+aiosqlite:////app/data/shared.db",
    pool_size=10,
    max_overflow=5
)
```

### Service Client (`shared/service_client.py`)

**Purpose:** HTTP client for inter-service communication.

**Features:**
- Automatic retry with exponential backoff
- Request timeout handling
- Health check support
- Pre-configured service URLs

**Usage:**
```python
from shared.service_client import get_service_client

client = get_service_client("data-api")
data = await client.get("/api/v1/events")
```

**Pre-configured Services:**
- `data-api`: http://data-api:8006
- `ai-query-service`: http://ai-query-service:8018
- `ai-automation-service-new`: http://ai-automation-service-new:8021
- `ai-training-service`: http://ai-training-service:8017
- `ai-pattern-service`: http://ai-pattern-service:8016

## Data Flow

### Query Processing Flow

```
User Query
    ↓
ai-query-service (Port 8018)
  - Entity extraction
  - Clarification detection
  - Query context building
    ↓
  Query Pattern/Synergy Context
    ↓
ai-pattern-service (Port 8016)
  - Pattern matching
  - Synergy detection
    ↓
  Suggestions Generated
    ↓
ai-automation-service-new (Port 8021)
  - YAML generation
  - Safety validation
  - Deployment
```

### Daily Analysis Flow

```
APScheduler (3 AM Daily)
    ↓
ai-pattern-service (Port 8016)
  - Fetch events from Data API
  - Pattern detection
  - Synergy detection
  - Store patterns/synergies
    ↓
  MQTT Notification
    ↓
  Suggestions Available
```

### Training Flow

```
Training Request
    ↓
ai-training-service (Port 8017)
  - Generate synthetic data
  - Train model
  - Store training run
    ↓
  Model Saved
    ↓
  Available for Use
```

## Service Communication

### Inter-Service Communication Patterns

1. **HTTP/REST** (Primary)
   - Services communicate via HTTP REST APIs
   - Uses `shared/service_client.py` for reliability
   - Automatic retry and timeout handling

2. **Shared Database** (Secondary)
   - Services share SQLite database for common data
   - Patterns, synergies, suggestions, training runs
   - Connection pooling prevents exhaustion

3. **MQTT** (Event Notifications)
   - Pattern service publishes analysis completion
   - Services can subscribe for real-time updates

4. **Direct InfluxDB Access** (Data Queries)
   - Services query InfluxDB directly for time-series data
   - No intermediate service for data queries

## Performance Targets

### Query Service
- **Latency**: <500ms P95
- **Health Check**: <10ms
- **Cache Hit Rate**: >80%

### Pattern Service
- **Daily Analysis**: 2-4 minutes
- **Pattern Detection**: <100ms per pattern
- **Background Processing**: Non-blocking

### Training Service
- **Training Jobs**: Queue-based (can take hours)
- **Synthetic Data Generation**: Batch processing
- **API Response**: <1s for status checks

### Database
- **Query Latency**: <50ms P95
- **Connection Pool**: Max 20 connections per service
- **Cache Hit Rate**: >80% for correlations

## Deployment Configuration

### Docker Compose Services

```yaml
ai-training-service:
  ports:
    - "8017:8017"
  environment:
    - DATABASE_URL=sqlite+aiosqlite:////app/data/shared.db
    - DATA_API_URL=http://data-api:8006

ai-pattern-service:
  ports:
    - "8016:8016"
  environment:
    - DATABASE_URL=sqlite+aiosqlite:////app/data/shared.db
    - DATA_API_URL=http://data-api:8006
    - MQTT_BROKER=192.168.1.86

ai-query-service:
  ports:
    - "8018:8018"
  environment:
    - DATABASE_URL=sqlite+aiosqlite:////app/data/shared.db
    - DATA_API_URL=http://data-api:8006
    - OPENAI_API_KEY=${OPENAI_API_KEY}

ai-automation-service-new:
  ports:
    - "8021:8021"
  environment:
    - DATABASE_URL=sqlite+aiosqlite:////app/data/shared.db
    - HA_URL=http://192.168.1.86:8123
```

### Shared Volumes

- `ai_automation_data:/app/data` - Shared database and cache
- Shared network: `homeiq-network`

## Migration Status

### Completed Migrations
- ✅ Training service extracted (Stories 39.1-39.4)
- ✅ Pattern service extracted (Stories 39.5-39.8)
- ✅ Query service foundation (Story 39.9-39.10)
- ✅ Automation service foundation (Story 39.10)
- ✅ Shared infrastructure (Story 39.11)
- ✅ Router modularization (Story 39.13)
- ✅ Performance optimization utilities (Story 39.15)

### Remaining Work
- ⏳ Full query service endpoint migration
- ⏳ Full automation service endpoint migration
- ⏳ Service layer reorganization (Story 39.14)

## Benefits

### Scalability
- **Independent Scaling**: Each service can scale independently
- **Resource Optimization**: Services use only needed resources
- **Load Distribution**: Queries distributed across services

### Maintainability
- **Focused Services**: Each service has clear responsibility
- **Easier Testing**: Smaller codebases easier to test
- **Clear Boundaries**: Well-defined service interfaces

### Performance
- **Low Latency**: Query service optimized for speed
- **Background Processing**: Pattern service doesn't block queries
- **Caching**: Shared cache reduces redundant computation

## Related Documentation

- [Epic 31 Architecture Pattern](epic-31-architecture-pattern.md) - Current architecture (enrichment-pipeline deprecated)
- [Performance Optimization Guide](../../services/ai-automation-service/PERFORMANCE_OPTIMIZATION_GUIDE.md)
- [API Reference](../api/API_REFERENCE.md) - API endpoint documentation
- [Deployment Guide](../DEPLOYMENT_GUIDE.md) - Deployment instructions

