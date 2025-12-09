# AI Pattern Service

**Pattern detection, synergy analysis, and community patterns service for HomeIQ**

**Port:** 8020 (internal), exposed as 8034 (external)
**Technology:** Python 3.11+, FastAPI, SQLAlchemy
**Container:** homeiq-ai-pattern-service
**Database:** SQLite (ai_automation.db)
**Scale:** Optimized for ~50-100 devices (single-home)

## Overview

The AI Pattern Service is a microservice extracted from ai-automation-service (Epic 39, Story 39.5) for independent scaling and maintainability. It handles pattern detection, synergy analysis, and community pattern mining operations that run on a scheduled basis.

**Port Mapping Note:** This service runs on port 8020 internally within the Docker network, but is exposed as port 8034 externally for host access. When making requests from outside Docker, use port 8034. Internal services should use port 8020.

### Key Features

- **Scheduled Pattern Analysis** - Automated pattern detection running on configurable cron schedule (default: 3 AM daily)
- **Time-of-Day Pattern Detection** - Identifies recurring automation patterns based on time
- **Co-occurrence Pattern Detection** - Discovers devices that are frequently used together
- **Synergy Detection** - Multi-hop device relationship discovery with confidence scoring
- **Community Pattern Mining** - Integration with automation-miner service for community insights
- **MQTT Notifications** - Optional notifications for pattern detection events
- **Incremental Updates** - Enable/disable incremental pattern analysis
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
  "service": "ai-pattern-service",
  "version": "1.0.0",
  "status": "operational"
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `/app/data/ai_automation.db` | Path to SQLite database file |
| `DATABASE_URL` | `sqlite+aiosqlite:////app/data/ai_automation.db` | SQLAlchemy database URL |
| `DATABASE_POOL_SIZE` | `10` | Database connection pool size (max 20 per service) |
| `DATABASE_MAX_OVERFLOW` | `5` | Max overflow connections |
| `DATA_API_URL` | `http://data-api:8006` | Data API service URL |
| `SERVICE_PORT` | `8020` | Internal service port |
| `SERVICE_NAME` | `ai-pattern-service` | Service name for logging/tracing |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Allowed CORS origins |

#### Pattern Detection Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNERGY_MIN_CONFIDENCE` | `0.5` | Minimum confidence score for synergy detection |
| `SYNERGY_MIN_IMPACT_SCORE` | `0.3` | Minimum impact score for synergy detection |
| `TIME_OF_DAY_OCCURRENCE_OVERRIDES` | `{}` | Override occurrence thresholds (JSON dict) |
| `TIME_OF_DAY_CONFIDENCE_OVERRIDES` | `{}` | Override confidence thresholds (JSON dict) |
| `CO_OCCURRENCE_SUPPORT_OVERRIDES` | `{}` | Override support thresholds (JSON dict) |
| `CO_OCCURRENCE_CONFIDENCE_OVERRIDES` | `{}` | Override confidence thresholds (JSON dict) |

#### Scheduler Configuration (Story 39.6)

| Variable | Default | Description |
|----------|---------|-------------|
| `ANALYSIS_SCHEDULE` | `0 3 * * *` | Cron schedule for pattern analysis (default: 3 AM daily) |
| `ENABLE_INCREMENTAL` | `True` | Enable incremental pattern updates |

#### MQTT Configuration (Story 39.6)

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_BROKER` | `None` | MQTT broker hostname (e.g., `192.168.1.86`) |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MQTT_USERNAME` | `None` | MQTT username (optional) |
| `MQTT_PASSWORD` | `None` | MQTT password (optional) |

## Development

### Running Locally

```bash
cd services/ai-pattern-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8020
```

### Running with Docker

```bash
# Build and start service
docker compose up -d ai-pattern-service

# View logs
docker compose logs -f ai-pattern-service

# Test health endpoint (external port)
curl http://localhost:8034/health

# Test from inside Docker network (internal port)
docker exec homeiq-ai-automation-ui curl http://ai-pattern-service:8020/health
```

### Testing Endpoints

```bash
# Health check
curl http://localhost:8034/health

# Readiness check
curl http://localhost:8034/ready

# Liveness check
curl http://localhost:8034/live

# Service info
curl http://localhost:8034/
```

## Dependencies

### Service Dependencies

- **data-api** (Port 8006) - Historical data queries, device/entity metadata
- **SQLite Database** - Shared ai_automation.db for pattern storage
- **MQTT Broker** (Optional) - Pattern detection notifications (typically Home Assistant's MQTT at 192.168.1.86:1883)

### Python Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy` - Database ORM
- `aiosqlite` - Async SQLite driver
- `pydantic` - Configuration management
- `pydantic-settings` - Environment variable loading
- `shared` - HomeIQ shared libraries (logging, observability, error handling)

## Related Services

### Upstream Dependencies

- **data-api** - Provides historical event data for pattern analysis
- **automation-miner** - Community pattern corpus (optional)

### Downstream Consumers

- **ai-automation-service** - Uses detected patterns for automation generation
- **ai-automation-ui** - Displays pattern insights to users
- **health-dashboard** - Monitors pattern service health

## Architecture Notes

### Separation from AI Automation Service

This service was extracted from ai-automation-service in Epic 39, Story 39.5 to:
- Enable independent scaling of pattern detection workloads
- Isolate long-running batch operations from real-time query handling
- Improve maintainability and deployment flexibility
- Support nightly analysis without impacting interactive performance

### Scheduled Analysis

The service runs pattern analysis on a configurable cron schedule (default: 3 AM daily):
1. **Pattern Detection** - Time-of-day and co-occurrence patterns
2. **Synergy Analysis** - Multi-hop device relationships
3. **Community Patterns** - Integration with automation-miner
4. **MQTT Notifications** - Optional alerts for new patterns

### Database Sharing

This service shares the `ai_automation.db` SQLite database with ai-automation-service:
- **Pattern Storage** - Detected patterns, synergy relationships
- **Community Patterns** - Mined automation patterns
- **Configuration** - Pattern detection thresholds and overrides

## Monitoring

### Health Checks

- **Liveness:** `GET /live` - Service is running
- **Readiness:** `GET /ready` - Service is ready to accept traffic
- **Health:** `GET /health` - Database connectivity verified

### Logging

All logs follow structured logging format with correlation IDs:
```json
{
  "timestamp": "2025-12-09T10:30:00Z",
  "level": "INFO",
  "service": "ai-pattern-service",
  "correlation_id": "abc-123",
  "message": "Pattern analysis completed",
  "duration_ms": 1234
}
```

### Observability

- **OpenTelemetry Tracing** - Distributed tracing across services
- **Correlation IDs** - Request tracking across service boundaries
- **Metrics** - Service health, database performance, pattern detection stats

## Version History

- **v1.0.0** (December 2025) - Initial service extraction from ai-automation-service (Epic 39, Story 39.5)
  - Scheduled pattern analysis with cron support
  - MQTT notification integration
  - Incremental pattern updates
  - Observability and structured logging

---

**Last Updated:** December 09, 2025
**Version:** 1.0.0
**Status:** Production Ready ✅
**Port:** 8020 (internal) / 8034 (external)
