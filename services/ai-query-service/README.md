# AI Query Service

**Low-latency natural language query service for HomeIQ automation**

**Port:** 8018 (internal), exposed as 8035 (external)
**Technology:** Python 3.11+, FastAPI, SQLAlchemy
**Container:** homeiq-ai-query-service
**Database:** SQLite (ai_automation.db)
**Scale:** Optimized for ~50-100 devices (single-home)

## Overview

The AI Query Service is a microservice extracted from ai-automation-service (Epic 39, Story 39.9) for independent scaling and low-latency query processing. It handles natural language automation queries with a target P95 latency of <500ms.

**Port Mapping Note:** This service runs on port 8018 internally within the Docker network, but is exposed as port 8035 externally for host access. When making requests from outside Docker, use port 8035. Internal services should use port 8018.

### Key Features

- **Natural Language Processing** - Process user queries in natural language
- **Entity Extraction** - Identify devices, rooms, and actions from queries using UnifiedExtractionPipeline
- **Clarification Detection** - Detect ambiguous queries and request clarification
- **Suggestion Generation** - Generate automation suggestions based on query intent
- **Query Refinement** - Allow users to refine and improve suggestions
- **Low-Latency Design** - Target P95 latency <500ms for interactive use
- **Query Caching** - 5-minute TTL cache for repeated queries
- **Parallel Extraction** - Enable parallel entity extraction for faster processing
- **Observability** - OpenTelemetry tracing, correlation middleware, structured logging

## API Endpoints

### Health Endpoints

```bash
GET /health
```
Health check with database connectivity verification.

**Response:**
```json
{
  "status": "ok",
  "database": "connected"
}
```

```bash
GET /ready
```
Kubernetes readiness probe endpoint.

**Response:**
```json
{
  "status": "ready"
}
```

```bash
GET /live
```
Kubernetes liveness probe endpoint.

**Response:**
```json
{
  "status": "live"
}
```

### Service Info

```bash
GET /
```
Root endpoint with service information.

**Response:**
```json
{
  "service": "ai-query-service",
  "version": "1.0.0",
  "status": "operational"
}
```

### Query Endpoints

```bash
POST /api/v1/query
```
Process natural language query and generate automation suggestions.

**Request:**
```json
{
  "query": "Turn on the living room lights when I get home",
  "user_id": "user123",
  "context": {
    "location": "home",
    "time": "evening"
  }
}
```

**Response:**
```json
{
  "query_id": "query-abc123",
  "status": "completed",
  "message": "Query processed successfully",
  "suggestions": [
    {
      "automation_id": "auto-1",
      "description": "Turn on living room lights on arrival",
      "confidence": 0.95
    }
  ],
  "entities": [
    {
      "type": "device",
      "value": "living room lights",
      "entity_id": "light.living_room"
    }
  ]
}
```

```bash
GET /api/v1/query/{query_id}/suggestions
```
Get all suggestions for a specific query.

**Response:**
```json
{
  "query_id": "query-abc123",
  "suggestions": [],
  "total_count": 0,
  "status": "completed"
}
```

```bash
POST /api/v1/query/{query_id}/refine
```
Refine query results based on user feedback.

**Request:**
```json
{
  "feedback": "Add sunset condition",
  "selected_entities": ["light.living_room"]
}
```

**Response:**
```json
{
  "query_id": "query-abc123",
  "status": "refined",
  "message": "Query refined successfully"
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `/app/data/ai_automation.db` | Path to SQLite database file |
| `DATABASE_URL` | `sqlite+aiosqlite:////app/data/ai_automation.db` | SQLAlchemy database URL |
| `DATABASE_POOL_SIZE` | `10` | Database connection pool size (optimized for query service) |
| `DATABASE_MAX_OVERFLOW` | `5` | Max overflow connections |
| `DATA_API_URL` | `http://data-api:8006` | Data API service URL |
| `DEVICE_INTELLIGENCE_URL` | `http://device-intelligence-service:8023` | Device intelligence service URL |
| `SERVICE_PORT` | `8018` | Internal service port |
| `SERVICE_NAME` | `ai-query-service` | Service name for logging/tracing |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

#### Home Assistant Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HA_URL` | `None` | Home Assistant URL (e.g., `http://192.168.1.86:8123`) |
| `HA_TOKEN` | `None` | Home Assistant long-lived access token |

#### OpenAI Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | `None` | OpenAI API key for GPT-4o-mini |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |
| `OPENAI_TIMEOUT` | `30.0` | Timeout for OpenAI API calls (seconds) |

#### Performance Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `QUERY_TIMEOUT` | `5.0` | Max time for query processing (seconds) |
| `MAX_QUERY_LENGTH` | `500` | Max characters in query |
| `ENABLE_CACHING` | `True` | Enable query result caching |
| `CACHE_TTL` | `300` | Cache TTL in seconds (5 minutes) |
| `ENABLE_PARALLEL_EXTRACTION` | `True` | Enable parallel entity extraction |
| `EXTRACTION_TIMEOUT` | `2.0` | Timeout for entity extraction (seconds) |

#### Clarification Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `CLARIFICATION_ENABLED` | `True` | Enable clarification detection |
| `CLARIFICATION_CONFIDENCE_THRESHOLD` | `0.7` | Confidence threshold for clarification |
| `MAX_CLARIFICATION_QUESTIONS` | `3` | Max clarification questions per query |

## Development

### Running Locally

```bash
cd services/ai-query-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8018
```

### Running with Docker

```bash
# Build and start service
docker compose up -d ai-query-service

# View logs
docker compose logs -f ai-query-service

# Test health endpoint (external port)
curl http://localhost:8035/health

# Test from inside Docker network (internal port)
docker exec homeiq-ai-automation-ui curl http://ai-query-service:8018/health
```

### Testing Endpoints

```bash
# Health check
curl http://localhost:8035/health

# Process a query
curl -X POST http://localhost:8035/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Turn on the living room lights at sunset",
    "user_id": "test-user"
  }'

# Get query suggestions
curl http://localhost:8035/api/v1/query/query-abc123/suggestions
```

## Dependencies

### Service Dependencies

- **data-api** (Port 8006) - Historical data queries, device/entity metadata
- **device-intelligence-service** (Port 8023) - Device capability information
- **Home Assistant** - External instance for entity data and area information
- **OpenAI API** - GPT-4o-mini for natural language processing
- **SQLite Database** - Shared ai_automation.db for query history and suggestions

### Python Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy` - Database ORM
- `aiosqlite` - Async SQLite driver
- `pydantic` - Configuration management
- `pydantic-settings` - Environment variable loading
- `openai` - OpenAI API client
- `shared` - HomeIQ shared libraries (logging, observability, error handling)

## Related Services

### Upstream Dependencies

- **data-api** - Provides historical event data and device metadata
- **device-intelligence-service** - Device capability discovery
- **Home Assistant** - Entity registry and area information

### Downstream Consumers

- **ai-automation-ui** - Primary consumer for Ask AI tab
- **health-dashboard** - Monitors query service health and performance

## Architecture Notes

### Separation from AI Automation Service

This service was extracted from ai-automation-service in Epic 39, Story 39.9 to:
- Enable independent scaling of query workloads
- Optimize for low-latency interactive queries (<500ms P95)
- Separate real-time query handling from batch pattern detection
- Improve maintainability and deployment flexibility

### Performance Optimization

The service is optimized for low-latency query processing:
1. **Query Timeout** - Hard 5-second timeout prevents hanging requests
2. **Parallel Extraction** - Entity extraction runs in parallel when enabled
3. **Result Caching** - 5-minute TTL cache for repeated queries
4. **Connection Pooling** - Optimized database pool for query workload
5. **Extraction Timeout** - 2-second timeout for entity extraction

### Database Sharing

This service shares the `ai_automation.db` SQLite database with ai-automation-service:
- **Query History** - Stores processed queries for analytics
- **Suggestion Cache** - Cached automation suggestions
- **User Preferences** - Clarification preferences and feedback

## Monitoring

### Health Checks

- **Liveness:** `GET /live` - Service is running
- **Readiness:** `GET /ready` - Service is ready to accept traffic
- **Health:** `GET /health` - Database connectivity verified

### Performance Targets

| Metric | Target | Acceptable | Investigation |
|--------|--------|------------|---------------|
| Query Processing | <500ms | <1s | >2s |
| Entity Extraction | <2s | <3s | >5s |
| Suggestion Generation | <3s | <5s | >10s |

### Logging

All logs follow structured logging format with correlation IDs:
```json
{
  "timestamp": "2025-12-09T10:30:00Z",
  "level": "INFO",
  "service": "ai-query-service",
  "correlation_id": "abc-123",
  "message": "Query processed",
  "duration_ms": 450,
  "query_id": "query-abc123"
}
```

### Observability

- **OpenTelemetry Tracing** - Distributed tracing across services
- **Correlation IDs** - Request tracking across service boundaries
- **Metrics** - Query latency, cache hit rate, extraction performance

## Security Notes

- **TODO (Story 39.10):** Authentication middleware needs to be added before production deployment
- **TODO (Story 39.10):** Rate limiting middleware needs to be added before production deployment
- **CORS:** Currently allows specific origins (localhost:3000, localhost:3001, container networks)
- **Input Validation:** Max query length enforced (500 characters)
- **Timeouts:** All operations have configurable timeouts to prevent resource exhaustion

## Version History

- **v1.0.0** (December 2025) - Initial service extraction from ai-automation-service (Epic 39, Story 39.9)
  - Foundation implementation with query endpoint
  - Low-latency query processing (<500ms target)
  - Query caching and parallel extraction
  - Observability and structured logging
  - **Note:** Full implementation will be completed in Story 39.10

---

**Last Updated:** December 09, 2025
**Version:** 1.0.0
**Status:** Development (Foundation Ready, Full Implementation in Story 39.10) 🚧
**Port:** 8018 (internal) / 8035 (external)
