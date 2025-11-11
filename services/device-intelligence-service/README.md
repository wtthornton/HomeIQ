# Device Intelligence Service

**Port:** 8017
**Purpose:** Centralized device discovery and intelligence processing
**Status:** Production Ready

## Overview

The Device Intelligence Service provides comprehensive device discovery, predictive analytics, and intelligent recommendations for Home Assistant devices. It maintains a SQLite database of discovered devices and their metadata, enabling fast lookups and pattern recognition.

## Key Features

- **Device Discovery**: Automatic discovery and metadata collection from Home Assistant
- **Predictive Analytics**: ML-powered predictions for device behavior and failures
- **Recommendations Engine**: Intelligent suggestions for device optimization
- **Health Monitoring**: Track device health metrics and detect anomalies
- **Data Hygiene**: Automated cleanup and database maintenance
- **WebSocket Support**: Real-time device updates and notifications

## Database

Uses SQLite for device metadata storage:
- **Location**: `/app/data/device_intelligence.db`
- **Schema**: Devices, entities, predictions, recommendations
- **Performance**: <10ms metadata queries

## API Endpoints

### Health & Status
```
GET /health
GET /api/health
```

### Device Discovery
```
GET /api/devices
POST /api/devices/discover
GET /api/devices/{device_id}
```

### Predictions
```
GET /api/predictions
POST /api/predictions/generate
GET /api/predictions/{device_id}
```

### Recommendations
```
GET /api/recommendations
POST /api/recommendations/generate
```

### Database Management
```
POST /api/database/cleanup
POST /api/database/optimize
GET /api/database/stats
```

### Data Hygiene
```
POST /api/hygiene/run
GET /api/hygiene/status
```

### WebSocket
```
WS /ws
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVICE_INTELLIGENCE_PORT` | `8017` | Service port |
| `DATABASE_PATH` | `/app/data/device_intelligence.db` | SQLite database path |
| `HA_URL` | `http://homeassistant:8123` | Home Assistant URL |
| `LOG_LEVEL` | `INFO` | Logging level |

## Architecture

```
┌──────────────────────────┐
│ Device Intelligence Svc  │
│      (Port 8017)         │
└───────────┬──────────────┘
            │
     ┌──────┴──────┐
     │             │
     ▼             ▼
┌─────────┐   ┌──────────────┐
│ SQLite  │   │ Home         │
│ Device  │   │ Assistant    │
│ Database│   │ API          │
└─────────┘   └──────────────┘
```

## Data Flow

1. **Discovery Phase**: Poll Home Assistant for devices/entities
2. **Storage**: Store metadata in SQLite database
3. **Analysis**: Run predictive analytics on device patterns
4. **Recommendations**: Generate intelligent suggestions
5. **Hygiene**: Periodic cleanup and optimization

## Development

### Running Locally
```bash
cd services/device-intelligence-service
docker-compose up --build
```

### Database Migrations
```bash
# Database is initialized automatically on startup
# Manual initialization (if needed):
docker exec device-intelligence-service python -c "from src.core.database import initialize_database; import asyncio; asyncio.run(initialize_database())"
```

### Testing
```bash
# Health check
curl http://localhost:8017/health

# Discover devices
curl -X POST http://localhost:8017/api/devices/discover

# Get recommendations
curl http://localhost:8017/api/recommendations
```

## Dependencies

- FastAPI (web framework)
- SQLAlchemy (ORM)
- aiosqlite (async SQLite)
- scikit-learn (ML predictions)
- pydantic (data validation)

## Database Schema

### Devices Table
- `device_id` (PK): Unique device identifier
- `friendly_name`: User-facing name
- `manufacturer`: Device manufacturer
- `model`: Device model
- `area_id`: Location/room
- `last_seen`: Last activity timestamp
- `health_score`: Computed health metric (0-100)

### Predictions Table
- `id` (PK): Prediction identifier
- `device_id` (FK): Associated device
- `prediction_type`: Type of prediction
- `confidence`: Confidence score (0-1)
- `predicted_at`: Timestamp
- `expires_at`: Expiration timestamp

### Recommendations Table
- `id` (PK): Recommendation identifier
- `device_id` (FK): Associated device
- `recommendation_type`: Type of recommendation
- `priority`: Priority level (low/medium/high)
- `status`: Status (pending/accepted/rejected)
- `created_at`: Timestamp

## Performance

- **Device Queries**: <10ms (SQLite)
- **Discovery**: 1-2s (full scan)
- **Predictions**: 100-500ms
- **Recommendations**: 200-800ms

## Monitoring

Logs structured JSON with:
- Request/response timing
- Database query performance
- Discovery results
- Prediction accuracy
- Health check status

## Related Services

- [Admin API](../admin-api/README.md) - System monitoring
- [Data API](../data-api/README.md) - Historical data queries
- [AI Automation Service](../ai-automation-service/README.md) - Automation suggestions
