# Data API Service

**Hybrid Database Query Interface for HomeIQ**

**Port:** 8006
**Technology:** Python 3.11+, FastAPI 0.121, SQLAlchemy 2.0, InfluxDB 2.x
**Container:** `homeiq-data-api`
**Database:** Hybrid (SQLite + InfluxDB)

## Overview

The Data API service is a specialized microservice that handles all feature-related data access, providing a unified interface to both SQLite metadata and InfluxDB time-series data. It delivers:

- **Hybrid Database Architecture** - SQLite for metadata (<10ms), InfluxDB for time-series
- **HA Event Queries** - Historical state changes from InfluxDB
- **Device & Entity Browsing** - Fast metadata queries from SQLite (Story 22.1-22.2)
- **Integration Management** - Device discovery and integration tracking
- **Sports Data** - Real-time and historical sports scores (Epic 12)
- **Home Assistant Automation** - Webhook endpoints for HA automations
- **Analytics & Metrics** - System-wide data analytics
- **Internal Bulk Upsert** - High-performance device/entity ingestion

### Database Architecture (Epic 22)

**SQLite (Metadata - Fast Queries)**:
- Devices table with indexes on area_id, manufacturer, integration
- Entities table with foreign key to devices
- Webhooks, preferences, and configuration
- Query performance: <10ms (vs ~50ms with InfluxDB)

**InfluxDB (Time-Series Data)**:
- HA state_changed events (365-day retention)
- Sports scores (NFL, NHL, NBA, MLB)
- Environmental data (air quality, carbon intensity)
- Smart meter power consumption
- All other time-series measurements

## Quick Start

### Prerequisites

- Python 3.11+
- InfluxDB 2.7+
- SQLite 3.x

### Running Locally

```bash
# Navigate to service directory
cd services/data-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start service
python -m uvicorn src.main:app --reload --port 8006
```

### Running with Docker

```bash
# Build container
docker compose build data-api

# Start service
docker compose up -d data-api

# View logs
docker compose logs -f data-api

# Check health
curl http://localhost:8006/health
```

### Docker Compose

```bash
# Start with all services
docker compose up data-api

# Or start entire stack
docker compose up
```

## API Endpoints

### Health & Status

#### `GET /health`
Service health check with dependency status
```bash
curl http://localhost:8006/health
```

Response:
```json
{
  "status": "healthy",
  "service": "data-api",
  "timestamp": "2025-11-15T12:00:00Z",
  "uptime_seconds": 3600,
  "dependencies": {
    "influxdb": "healthy",
    "sqlite": "healthy"
  },
  "performance": {
    "avg_query_time_ms": 8.5,
    "memory_mb": 150.2
  }
}
```

#### `GET /api/info`
API information and version
```bash
curl http://localhost:8006/api/info
```

### Events (Story 13.2)

#### `GET /api/v1/events`
Query HA events from InfluxDB
```bash
curl "http://localhost:8006/api/v1/events?entity_id=light.office&days=7"
```

Query parameters:
- `entity_id`: Filter by entity
- `days`: Days of history (default: 7)
- `start`: Start timestamp
- `end`: End timestamp
- `limit`: Maximum results (default: 1000)

#### `GET /api/v1/events/{id}`
Get specific event by ID
```bash
curl http://localhost:8006/api/v1/events/abc123
```

#### `POST /api/v1/events/search`
Search events with complex filters
```bash
curl -X POST http://localhost:8006/api/v1/events/search \
  -H "Content-Type: application/json" \
  -d '{
    "entity_ids": ["light.office", "light.bedroom"],
    "start_time": "2025-11-01T00:00:00Z",
    "end_time": "2025-11-15T23:59:59Z",
    "states": ["on", "off"],
    "limit": 500
  }'
```

#### `GET /api/v1/events/stats`
Event statistics and aggregations
```bash
curl http://localhost:8006/api/v1/events/stats?entity_id=light.office
```

### Devices & Entities (Story 13.2 + Epic 22)

#### `GET /api/devices`
List all devices from SQLite (<10ms)
```bash
curl http://localhost:8006/api/devices
```

Query parameters:
- `area_id`: Filter by area
- `manufacturer`: Filter by manufacturer
- `integration`: Filter by integration (e.g., "zigbee2mqtt")
- `limit`: Maximum results

Response:
```json
[
  {
    "id": "abc123",
    "name": "Office Light",
    "manufacturer": "IKEA",
    "model": "TRADFRI bulb E27 WS opal 980lm",
    "area_id": "office",
    "integration": "zigbee2mqtt",
    "entity_count": 3,
    "created_at": "2025-11-15T12:00:00Z"
  }
]
```

#### `GET /api/devices/{id}`
Get device details by ID
```bash
curl http://localhost:8006/api/devices/abc123
```

#### `GET /api/entities`
List all entities from SQLite (<10ms)
```bash
curl http://localhost:8006/api/entities
```

Query parameters:
- `device_id`: Filter by device
- `domain`: Filter by domain (light, switch, sensor, etc.)
- `area_id`: Filter by area
- `disabled`: Include disabled entities (default: false)

#### `GET /api/entities/{id}`
Get entity details by ID
```bash
curl http://localhost:8006/api/entities/light.office
```

#### `GET /api/integrations`
List integrations from InfluxDB
```bash
curl http://localhost:8006/api/integrations
```

### Internal Endpoints (October 2025)

**Purpose**: High-performance bulk upsert for websocket-ingestion service

#### `POST /internal/devices/bulk_upsert`
Bulk upsert devices (called by websocket-ingestion)
```bash
curl -X POST http://localhost:8006/internal/devices/bulk_upsert \
  -H "Content-Type: application/json" \
  -d '{
    "devices": [
      {
        "id": "abc123",
        "name": "Office Light",
        "manufacturer": "IKEA",
        "model": "TRADFRI bulb E27",
        "area_id": "office",
        "integration": "zigbee2mqtt"
      }
    ]
  }'
```

#### `POST /internal/entities/bulk_upsert`
Bulk upsert entities (called by websocket-ingestion)
```bash
curl -X POST http://localhost:8006/internal/entities/bulk_upsert \
  -H "Content-Type: application/json" \
  -d '{
    "entities": [
      {
        "entity_id": "light.office",
        "device_id": "abc123",
        "name": "Office Light",
        "domain": "light",
        "platform": "zigbee2mqtt",
        "area_id": "office"
      }
    ]
  }'
```

### Sports Data (Story 13.4 - Epic 12)

#### `GET /api/v1/sports/games/live`
Get live games across all sports
```bash
curl http://localhost:8006/api/v1/sports/games/live
```

#### `GET /api/v1/sports/games/history`
Get historical games
```bash
curl "http://localhost:8006/api/v1/sports/games/history?days=7&sport=nfl"
```

#### `GET /api/v1/sports/schedule/{team}`
Get team schedule
```bash
curl http://localhost:8006/api/v1/sports/schedule/seahawks
```

### Home Assistant Automation (Story 13.4 - Epic 12)

#### `GET /api/v1/ha/game-status/{team}`
Quick game status for HA automations (<50ms)
```bash
curl http://localhost:8006/api/v1/ha/game-status/seahawks
```

Response:
```json
{
  "is_playing": true,
  "score": "21-14",
  "quarter": "Q3",
  "time_remaining": "8:42"
}
```

#### `GET /api/v1/ha/game-context/{team}`
Rich game context for advanced automations
```bash
curl http://localhost:8006/api/v1/ha/game-context/seahawks
```

#### `POST /api/v1/ha/webhooks/register`
Register webhook for event notifications
```bash
curl -X POST http://localhost:8006/api/v1/ha/webhooks/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "game_started",
    "url": "http://homeassistant:8123/api/webhook/abc123",
    "events": ["game_start", "touchdown", "game_end"]
  }'
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATA_API_HOST` | Host address | `0.0.0.0` |
| `DATA_API_PORT` | Service port | `8006` |
| `INFLUXDB_URL` | InfluxDB URL | `http://influxdb:8086` |
| `INFLUXDB_TOKEN` | InfluxDB auth token | Required |
| `INFLUXDB_ORG` | InfluxDB organization | `homeiq` |
| `INFLUXDB_BUCKET` | InfluxDB bucket | `home_assistant_events` |
| `DATABASE_URL` | SQLite database URL | `sqlite+aiosqlite:///./data/metadata.db` |
| `SQLITE_TIMEOUT` | Connection timeout (seconds) | `30` |
| `SQLITE_CACHE_SIZE` | Cache size (KB, negative) | `-64000` (64MB) |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENABLE_AUTH` | Enable API authentication | `true` (invalid values default to `true`) |
| `API_KEY` | API key (if auth enabled) | - |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |

### Example `.env` File

```bash
# Data API Configuration
DATA_API_HOST=0.0.0.0
DATA_API_PORT=8006
# Supported values: true, false, 1, 0, yes, no, on, off
ENABLE_AUTH=false

# InfluxDB Configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your-token-here
INFLUXDB_ORG=homeiq
INFLUXDB_BUCKET=home_assistant_events

# SQLite Configuration (Story 22.1 - Epic 22)
DATABASE_URL=sqlite+aiosqlite:///./data/metadata.db
SQLITE_TIMEOUT=30
SQLITE_CACHE_SIZE=-64000  # 64MB cache

# Performance Tuning
SQLITE_JOURNAL_MODE=WAL  # Write-Ahead Logging
SQLITE_SYNCHRONOUS=NORMAL  # Fast writes
SQLITE_TEMP_STORE=MEMORY  # Fast temp tables

# Logging
LOG_LEVEL=INFO
```

## Architecture

### Service Separation

The HomeIQ system uses two API services:

**admin-api** (port 8004): System monitoring & control
- Health checks for all services
- Docker container management
- System configuration
- System-wide statistics
- Alert management

**data-api** (port 8006): Feature data hub ← THIS SERVICE
- HA event queries (InfluxDB)
- Device/entity browsing (SQLite)
- Sports data (InfluxDB)
- Analytics and metrics
- HA automation integration

### Data Flow (Epic 31 + Epic 22)

```
┌─────────────────────┐
│ Home Assistant      │
│ @ 192.168.1.86:8123 │
└──────────┬──────────┘
           │
           │ WebSocket Discovery (on connect)
           ↓
┌───────────────────────────┐
│ websocket-ingestion       │
│ (Port 8001)               │
│                           │
│ POST /internal/           │
│   devices/bulk_upsert     │
│   entities/bulk_upsert    │
└──────────┬────────────────┘
           │
           ↓
┌───────────────────────────┐
│ Data API (8006)           │
│                           │
│ ┌─────────┐ ┌──────────┐ │
│ │ SQLite  │ │ InfluxDB │ │
│ │Metadata │ │Time-Series│ │
│ │ <10ms   │ │ <100ms   │ │
│ └─────────┘ └──────────┘ │
└──────────┬────────────────┘
           │
           ↓
┌───────────────────────────┐
│ Dashboards & Consumers    │
│ - Health Dashboard (3000) │
│ - AI Automation UI (3001) │
│ - HA Automations          │
└───────────────────────────┘
```

### Database Access

**SQLite (Primary for Metadata - Epic 22)**:
- `devices` - Device registry (99 devices, <10ms queries)
  - Indexes: area_id, manufacturer, integration
  - Foreign keys: None (root table)
- `entities` - Entity registry (100+ entities, <10ms queries)
  - Foreign key: device_id → devices.id
  - Indexes: device_id, domain, area_id
- `webhooks` - Webhook registrations
- `preferences` - User preferences
- `integrations_meta` - Integration metadata

**InfluxDB (Time-Series Data)**:
- `home_assistant_events` - HA state changes (365-day retention)
- `nfl_scores`, `nhl_scores`, `nba_scores`, `mlb_scores` - Sports data
- `air_quality` - Air quality measurements
- `carbon_intensity` - Grid carbon intensity
- `electricity_pricing` - Dynamic pricing
- `smart_meter` - Power consumption
- `weather` - Weather data
- All other time-series measurements

### Component Architecture

```
data-api/
├── src/
│   ├── main.py                       # FastAPI application with lifespan
│   ├── config.py                     # Pydantic settings
│   ├── database/
│   │   ├── models.py                 # SQLAlchemy models
│   │   └── session.py                # Database session management
│   ├── events_endpoints.py           # Event queries (InfluxDB)
│   ├── devices_endpoints.py          # Device/entity queries (SQLite)
│   ├── internal_endpoints.py         # Bulk upsert endpoints
│   ├── sports_endpoints.py           # Sports data (Epic 12)
│   ├── ha_automation_endpoints.py    # HA automation webhooks
│   ├── influxdb_client.py            # InfluxDB query client
│   └── sqlite_client.py              # SQLite query client
├── alembic/                          # Database migrations
│   ├── versions/
│   └── env.py
├── tests/                            # Unit tests
├── Dockerfile                        # Production container
├── Dockerfile.dev                    # Development container
├── requirements.txt                  # Python dependencies
├── requirements-prod.txt             # Production dependencies
└── alembic.ini                       # Alembic configuration
```

## Performance

### Performance Targets

| Endpoint Type | Target | Acceptable | Investigation |
|---------------|--------|------------|---------------|
| Health checks | <20ms | <50ms | >100ms |
| Device queries (SQLite) | <10ms | <50ms | >100ms |
| Entity queries (SQLite) | <10ms | <50ms | >100ms |
| Event queries (InfluxDB) | <100ms | <200ms | >500ms |
| HA automation endpoints | <50ms | <100ms | >200ms |
| Sports data queries | <100ms | <200ms | >500ms |

### Resource Usage

- **Memory:** 256-512 MB typical
- **CPU:** 0.5-1.0 cores typical
- **Disk:** <100 MB (SQLite database)
- **InfluxDB Connections:** Pool of 10 connections

### Scaling

- Can scale horizontally (2-4 instances)
- InfluxDB connection pooling (max 10 connections)
- Query result caching (5-minute TTL)
- SQLite per-instance (no sharing required)

### Optimization

**SQLite Optimizations:**
```sql
PRAGMA journal_mode=WAL;       -- Write-Ahead Logging
PRAGMA synchronous=NORMAL;     -- Fast writes
PRAGMA cache_size=-64000;      -- 64MB cache
PRAGMA temp_store=MEMORY;      -- Fast temp tables
PRAGMA foreign_keys=ON;        -- Referential integrity
PRAGMA busy_timeout=30000;     -- 30s lock wait
```

**InfluxDB Optimizations:**
- Batch queries when possible
- Use specific time ranges
- Limit field selection
- Index-aware query planning

## Testing

### Run Unit Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_events_endpoints.py -v

# Run async tests
pytest tests/ -v
```

**Test Coverage:**
- Event query endpoints
- Device/entity CRUD operations
- Bulk upsert operations
- Sports data queries
- HA automation webhooks
- Health checks
- Database migrations

**Note:** Automated test framework is being rebuilt as of November 2025.

### Manual Testing

```bash
# Test health endpoint
curl http://localhost:8006/health

# Test device query
curl http://localhost:8006/api/devices

# Test event query
curl "http://localhost:8006/api/v1/events?entity_id=light.office&days=7"

# Test bulk upsert
curl -X POST http://localhost:8006/internal/devices/bulk_upsert \
  -H "Content-Type: application/json" \
  -d '{"devices": [{"id": "test", "name": "Test Device"}]}'
```

## Development

### Project Structure

```
services/data-api/
├── src/
│   ├── __init__.py
│   ├── main.py                       # FastAPI application
│   ├── config.py                     # Pydantic settings
│   ├── events_endpoints.py           # Event queries (Story 13.2)
│   ├── devices_endpoints.py          # Device browsing (Story 13.2)
│   ├── internal_endpoints.py         # Bulk upsert (October 2025)
│   ├── sports_endpoints.py           # Sports data (Story 13.4)
│   └── ha_automation_endpoints.py    # HA automation (Story 13.4)
├── tests/
│   ├── __init__.py
│   ├── test_main.py
│   ├── test_events.py
│   └── test_devices.py
├── alembic/                          # Database migrations
│   ├── versions/
│   │   └── 001_initial_schema.py
│   └── env.py
├── Dockerfile                        # Production image
├── Dockerfile.dev                    # Development image
├── requirements.txt                  # Dependencies
├── requirements-prod.txt             # Pinned production deps
└── README.md                         # This file
```

### Adding New Endpoints

Follow the FastAPI router pattern:

```python
# src/my_endpoints.py
from fastapi import APIRouter, Depends
from typing import List

router = APIRouter()

@router.get("/api/v1/my-endpoint", response_model=List[MyModel])
async def my_endpoint():
    """
    Get my data

    Returns:
        List of my data items
    """
    return {"data": "..."}

# src/main.py
from .my_endpoints import router as my_router
app.include_router(my_router, tags=["My Feature"])
```

### Database Migrations

```bash
# Create new migration
cd services/data-api
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history
```

## Security

### Authentication

Authentication is **optional** for data-api (default: disabled).

Enable with:
```bash
ENABLE_AUTH=true
API_KEY=your-secret-api-key
```

### API Key Usage

```bash
# With Bearer token
curl -H "Authorization: Bearer your-api-key" \
  http://localhost:8006/api/v1/events

# With X-API-Key header
curl -H "X-API-Key: your-api-key" \
  http://localhost:8006/api/v1/events
```

### Best Practices

- Use strong API keys (32+ characters)
- Rotate API keys periodically (90 days)
- Use environment variables for secrets
- Enable HTTPS in production
- Implement rate limiting for public endpoints
- Use CORS to restrict origins

## Troubleshooting

### Service Won't Start

**Check InfluxDB connection:**
```bash
curl http://localhost:8086/health
```

**Check SQLite database:**
```bash
ls -la data/metadata.db
# Should exist and be writable
```

**Check logs:**
```bash
docker compose logs data-api
```

**Common issues:**
- InfluxDB not accessible → Check `INFLUXDB_URL` and network
- SQLite database locked → Check file permissions
- Port 8006 already in use → Change `DATA_API_PORT`
- Missing migrations → Run `alembic upgrade head`

### Queries Are Slow

**Check InfluxDB performance:**
```bash
curl http://localhost:8006/health | jq '.performance.avg_query_time_ms'
```

**Enable query logging:**
```bash
LOG_LEVEL=DEBUG
```

**Optimize queries:**
- Use specific time ranges
- Limit result sets
- Add indexes to SQLite tables
- Use query result caching

### Dashboard Can't Connect

**Verify nginx routing:**
```bash
docker compose logs health-dashboard
```

**Test endpoint directly:**
```bash
curl http://localhost:8006/health
```

**Check CORS settings:**
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### SQLite Database Locked

**Symptoms:**
- "database is locked" errors
- Slow write operations
- Timeout errors

**Solutions:**
```bash
# Increase timeout
SQLITE_TIMEOUT=60

# Check WAL mode
sqlite3 data/metadata.db "PRAGMA journal_mode;"
# Should return: wal

# Reset database (DESTRUCTIVE)
rm data/metadata.db
alembic upgrade head
```

### InfluxDB Connection Pool Exhausted

**Symptoms:**
- "Connection pool exhausted" errors
- Slow query responses
- Timeout errors

**Solutions:**
- Increase connection pool size (if available)
- Add query result caching
- Reduce concurrent requests
- Scale horizontally (add instances)

## Dependencies

### Core Dependencies

```
fastapi==0.121.2            # Web framework
uvicorn[standard]==0.38.0   # ASGI server
python-multipart==0.0.20    # Form data parsing
pydantic==2.12.4            # Data validation
pydantic-settings==2.12.0   # Settings management
```

### HTTP Client

```
aiohttp==3.13.2             # Async HTTP client
```

### Database

```
influxdb-client==1.49.0     # InfluxDB 2.x client
sqlalchemy==2.0.44          # ORM
aiosqlite==0.21.0           # Async SQLite driver
alembic==1.17.2             # Database migrations
```

### Configuration & Utilities

```
python-dotenv==1.2.1        # Environment variables
python-jose[cryptography]==3.5.0  # JWT tokens
passlib[bcrypt]==1.7.4      # Password hashing
```

### Development & Testing

```
pytest==8.3.3               # Testing framework
pytest-asyncio==0.23.0      # Async test support
pytest-cov==4.1.0           # Coverage reporting
httpx==0.28.1               # FastAPI testing
```

## Related Documentation

- [Epic 13: Admin API Service Separation](../../docs/stories/epic-13-admin-api-service-separation.md)
- [Epic 22: SQLite Metadata Storage](../../docs/stories/epic-22-sqlite-metadata.md)
- [Admin API Separation Analysis](../../implementation/analysis/ADMIN_API_SEPARATION_ANALYSIS.md)
- [Architecture Overview](../../docs/architecture/)
- [Database Schema](../../docs/architecture/database-schema.md)
- [API Reference](../../docs/api/API_REFERENCE.md)
- [CLAUDE.md](../../CLAUDE.md) - AI assistant development guide

## Support

- **Issues:** File on GitHub at https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** Check `/docs` directory
- **Health Check:** http://localhost:8006/health
- **API Docs:** http://localhost:8006/docs

## Version History

### 2.1 (November 15, 2025)
- Updated documentation to 2025 standards
- Enhanced dependency documentation
- Added comprehensive API endpoint documentation
- Improved troubleshooting section
- Added database migration workflows
- Enhanced security best practices
- Updated admin-api port reference (8003 → 8004)

### 2.0 (October 2025)
- Added Epic 22 SQLite metadata storage
- Implemented internal bulk upsert endpoints
- Enhanced device/entity query performance (<10ms)
- Added comprehensive error handling

### 1.0 (October 2025)
- Epic 13 service separation
- Initial FastAPI implementation
- InfluxDB query interface
- Sports data endpoints (Epic 12)
- HA automation webhooks

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅
**Port:** 8006
**Architecture:** Hybrid Database (SQLite + InfluxDB)
