# Device Intelligence Service

**Centralized Device Discovery and Intelligence Processing for HomeIQ**

**Port:** 8028
**Technology:** Python 3.11+, FastAPI 0.121, SQLAlchemy 2.0, scikit-learn 1.4
**Container:** `homeiq-device-intelligence`
**Database:** SQLite (device_intelligence.db - 7 tables)

## Overview

The Device Intelligence Service provides comprehensive device discovery, capability analysis, and intelligent recommendations for Home Assistant devices. It powers **Epic AI-2 (Device Intelligence)** by maintaining a SQLite database of discovered devices, their capabilities, and usage patterns, enabling fast lookups and predictive analytics.

### Key Features

- **Universal Device Discovery** - 6,000+ Zigbee device models with full capability mapping
- **Capability Analysis** - Feature extraction and utilization tracking
- **Predictive Analytics** - ML-powered predictions for device behavior and failures
- **Recommendations Engine** - Intelligent suggestions for device optimization
- **Health Monitoring** - Track device health metrics and detect anomalies
- **Data Hygiene** - Automated cleanup and database maintenance
- **WebSocket Support** - Real-time device updates and notifications
- **Feature Suggestions** - LED notifications, power monitoring, unused capabilities

## Quick Start

### Prerequisites

- Python 3.11+
- SQLite 3.x
- Home Assistant API access

### Running Locally

```bash
cd services/device-intelligence-service

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start service
uvicorn src.main:app --reload --port 8028
```

### Running with Docker

```bash
# Build and start
docker compose up -d device-intelligence-service

# View logs
docker compose logs -f device-intelligence-service

# Check health
curl http://localhost:8028/health
```

## API Endpoints

### Health & Status

#### `GET /health`
Service health check
```bash
curl http://localhost:8028/health
```

#### `GET /api/health`
Enhanced health with database stats
```bash
curl http://localhost:8028/api/health
```

### Device Discovery (Epic AI-2)

#### `GET /api/devices`
List all discovered devices
```bash
curl http://localhost:8028/api/devices
```

#### `POST /api/devices/discover`
Trigger device discovery from Home Assistant
```bash
curl -X POST http://localhost:8028/api/devices/discover
```

#### `GET /api/devices/{device_id}`
Get specific device details with capabilities
```bash
curl http://localhost:8028/api/devices/abc123
```

#### `GET /api/devices/{device_id}/capabilities`
Get device capabilities and utilization
```bash
curl http://localhost:8028/api/devices/abc123/capabilities
```

### Predictions

#### `GET /api/predictions`
List all predictions
```bash
curl http://localhost:8028/api/predictions
```

#### `POST /api/predictions/generate`
Generate predictions for all devices
```bash
curl -X POST http://localhost:8028/api/predictions/generate
```

#### `GET /api/predictions/{device_id}`
Get predictions for specific device
```bash
curl http://localhost:8028/api/predictions/{device_id}
```

### Recommendations (Epic AI-2)

#### `GET /api/recommendations`
List all recommendations
```bash
curl http://localhost:8028/api/recommendations
```

#### `POST /api/recommendations/generate`
Generate recommendations for all devices
```bash
curl -X POST http://localhost:8028/api/recommendations/generate
```

### Database Management

#### `POST /api/database/cleanup`
Clean up old records
```bash
curl -X POST http://localhost:8028/api/database/cleanup
```

#### `POST /api/database/optimize`
Optimize database (VACUUM, ANALYZE)
```bash
curl -X POST http://localhost:8028/api/database/optimize
```

#### `GET /api/database/stats`
Get database statistics
```bash
curl http://localhost:8028/api/database/stats
```

### Data Hygiene

#### `POST /api/hygiene/run`
Run data hygiene tasks
```bash
curl -X POST http://localhost:8028/api/hygiene/run
```

#### `GET /api/hygiene/status`
Get hygiene task status
```bash
curl http://localhost:8028/api/hygiene/status
```

### WebSocket

#### `WS /ws`
Real-time device updates
```bash
wscat -c ws://localhost:8028/ws
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVICE_INTELLIGENCE_PORT` | `8028` | Service port |
| `DATABASE_PATH` | `/app/data/device_intelligence.db` | SQLite database path |
| `HA_URL` | `http://homeassistant:8123` | Home Assistant URL |
| `HA_TOKEN` | _required_ | Home Assistant access token (validated on startup) |
| `ALLOWED_ORIGINS` | `["http://localhost:3000", ...]` | JSON/CSV list of trusted CORS origins |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DISCOVERY_INTERVAL` | `3600` | Discovery interval (seconds) |
| `PREDICTION_INTERVAL` | `7200` | Prediction interval (seconds) |

> **Note:** The service now validates `HA_TOKEN` during startup and will exit early if it is missing, ensuring clearer diagnostics for single-home deployments.

### Example `.env`

```bash
DEVICE_INTELLIGENCE_PORT=8028
DATABASE_PATH=/app/data/device_intelligence.db
HA_URL=http://homeassistant:8123
HA_TOKEN=your-token-here
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:3001"]
LOG_LEVEL=INFO
DISCOVERY_INTERVAL=3600
PREDICTION_INTERVAL=7200
```

Set `ALLOWED_ORIGINS` to a JSON array (or comma-separated list) that matches the dashboards you trust (for example, the health dashboard at `http://localhost:3000`).

## Architecture

### Data Flow

```
┌──────────────────────────────┐
│ Home Assistant               │
│ Device & Entity Registry     │
└───────────┬──────────────────┘
            │
            │ Discovery (on demand / interval)
            ↓
┌──────────────────────────────┐
│ Device Intelligence Service  │
│ (Port 8028)                  │
│                              │
│ ┌────────────────────────┐  │
│ │ Capability Parser      │  │
│ │ 6,000+ Zigbee models   │  │
│ └────────────────────────┘  │
│                              │
│ ┌────────────────────────┐  │
│ │ Predictive Analytics   │  │
│ │ scikit-learn ML        │  │
│ └────────────────────────┘  │
└───────────┬──────────────────┘
            │
            ↓
┌──────────────────────────────┐
│ SQLite Database              │
│ device_intelligence.db       │
│ - devices (7 tables)         │
│ - capabilities               │
│ - predictions                │
│ - recommendations            │
└──────────────────────────────┘
            │
            ↓
┌──────────────────────────────┐
│ AI Automation Service        │
│ Uses capabilities for        │
│ feature suggestions          │
└──────────────────────────────┘
```

### Component Architecture

```
src/
├── main.py                    # FastAPI application
├── config.py                  # Pydantic settings
├── api/
│   ├── devices.py             # Device endpoints
│   ├── predictions.py         # Prediction endpoints
│   ├── recommendations.py     # Recommendation endpoints
│   └── database.py            # Database management
├── core/
│   ├── database.py            # SQLAlchemy setup
│   ├── models.py              # Database models (7 tables)
│   └── schemas.py             # Pydantic schemas
├── services/
│   ├── discovery.py           # Device discovery from HA
│   ├── capability_parser.py   # Capability extraction
│   ├── predictions.py         # ML predictions
│   ├── recommendations.py     # Recommendation engine
│   └── hygiene.py             # Data cleanup
└── ml/
    ├── models.py              # ML model definitions
    └── training.py            # Model training
```

## Database Schema

### 7 Tables

1. **devices** - Device registry
   - device_id (PK), friendly_name, manufacturer, model, area_id
   - last_seen, health_score, capabilities_json

2. **device_capabilities** - Capability metadata (Epic AI-2)
   - id (PK), device_id (FK), capability_name, capability_type
   - utilization_score, last_used, created_at

3. **feature_usage** - Feature utilization tracking
   - id (PK), device_id (FK), feature_name, usage_count
   - last_used, created_at

4. **predictions** - ML predictions
   - id (PK), device_id (FK), prediction_type, confidence
   - predicted_at, expires_at

5. **recommendations** - Intelligent suggestions
   - id (PK), device_id (FK), recommendation_type, priority
   - status (pending/accepted/rejected), created_at

6. **device_health** - Health tracking
   - id (PK), device_id (FK), health_score, last_check
   - issues_json, created_at

7. **discovery_runs** - Discovery job tracking
   - id (PK), started_at, completed_at, devices_found
   - status, errors_json

### Indexes

- `devices.area_id`, `devices.manufacturer`
- `device_capabilities.device_id`, `device_capabilities.capability_type`
- `predictions.device_id`, `predictions.expires_at`
- `recommendations.device_id`, `recommendations.status`

## Performance

### Performance Targets

| Operation | Target | Acceptable | Investigation |
|-----------|--------|------------|---------------|
| Device queries | <10ms | <50ms | >100ms |
| Discovery (full) | 1-2s | <5s | >10s |
| Predictions | 100-500ms | <1s | >2s |
| Recommendations | 200-800ms | <1.5s | >3s |

### Resource Usage

- **Memory:** ~200-400MB (with ML models loaded)
- **CPU:** <10% typical, <50% during discovery
- **Disk:** <50MB database (typical)

### Optimization

**SQLite Optimizations:**
```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-64000;  # 64MB cache
PRAGMA temp_store=MEMORY;
PRAGMA foreign_keys=ON;
```

## Development

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src --cov-report=html tests/

# Run specific test
pytest tests/test_discovery.py -v
```

### Manual Testing

```bash
# Health check
curl http://localhost:8028/health

# Discover devices
curl -X POST http://localhost:8028/api/devices/discover

# Get recommendations
curl http://localhost:8028/api/recommendations

# Database stats
curl http://localhost:8028/api/database/stats
```

## Monitoring

### Structured Logging

Logs include:
- Request/response timing
- Database query performance
- Discovery results and statistics
- Prediction accuracy metrics
- Health check status
- Error tracking with stack traces

### Metrics

- Devices discovered per run
- Predictions generated
- Recommendations created
- Database size and query times
- API response times

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
docker compose logs device-intelligence-service
```

**Common issues:**
- Database file permissions → Check `/app/data/` permissions
- Home Assistant unreachable → Verify `HA_URL` and `HA_TOKEN`
- Port 8028 in use → Change `DEVICE_INTELLIGENCE_PORT`
- Missing migrations → Run `alembic upgrade head`

### Discovery Not Working

**Check Home Assistant connection:**
```bash
curl -H "Authorization: Bearer $HA_TOKEN" http://homeassistant:8123/api/
```

**Manually trigger discovery:**
```bash
curl -X POST http://localhost:8028/api/devices/discover
```

### Database Locked

**Symptoms:**
- "database is locked" errors
- Slow queries

**Solutions:**
```bash
# Check WAL mode
sqlite3 data/device_intelligence.db "PRAGMA journal_mode;"

# Optimize database
curl -X POST http://localhost:8028/api/database/optimize
```

## Dependencies

### Core

```
fastapi==0.121.2           # Web framework
uvicorn[standard]==0.38.0  # ASGI server
pydantic==2.12.4           # Data validation
pydantic-settings==2.12.0  # Settings management
```

### Database

```
sqlalchemy==2.0.44         # ORM
aiosqlite==0.21.0          # Async SQLite
alembic==1.17.2            # Migrations
```

### HTTP & WebSocket

```
httpx==0.27.2              # HTTP client
aiohttp==3.13.2            # Async HTTP
websockets==12.0           # WebSocket server
paho-mqtt==1.6.1           # MQTT client
```

### Machine Learning

```
scikit-learn==1.4.2        # ML predictions
pandas==2.3.3              # Data analysis
numpy==2.3.4               # Numerical computing
joblib==1.4.2              # Model persistence
```

### Development

```
pytest==8.3.3              # Testing
pytest-asyncio==0.23.0     # Async tests
pytest-cov==5.0.0          # Coverage
black==23.11.0             # Code formatting
mypy==1.7.1                # Type checking
```

## Related Documentation

- [Epic AI-2: Device Intelligence](../../docs/stories/epic-ai2-device-intelligence.md)
- [AI Automation Service](../ai-automation-service/README.md)
- [Data API](../data-api/README.md)
- [API Reference](../../docs/api/API_REFERENCE.md)
- [CLAUDE.md](../../CLAUDE.md)

## Support

- **Issues:** https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** `/docs` directory
- **Health Check:** http://localhost:8028/health
- **API Docs:** http://localhost:8028/docs

## Version History

### 2.1 (November 15, 2025)
- Updated documentation to 2025 standards
- Corrected port from 8017 to 8028
- Enhanced dependency documentation
- Added comprehensive API endpoint documentation
- Improved troubleshooting section
- Added Epic AI-2 context

### 2.0 (September 2025)
- Added 6,000+ Zigbee device capability mapping
- Feature utilization tracking
- Enhanced recommendation engine

### 1.0 (Initial Release)
- Device discovery from Home Assistant
- Basic predictive analytics
- SQLite database storage

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅
**Port:** 8028
**Epic:** AI-2 (Device Intelligence)
