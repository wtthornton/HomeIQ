# Admin API Service

## Overview

The Admin API Service is a FastAPI-based REST API that provides comprehensive administration, monitoring, and configuration management for the HomeIQ system.

**Port:** 8004 (previously 8003)
**Technology:** Python 3.11+, FastAPI 0.121, Pydantic 2.12
**Container:** `homeiq-admin-api`

## Features

### System Monitoring
- Health check endpoints for all services
- Real-time system metrics and statistics
- Performance monitoring and analytics
- Service status tracking with dependency health
- Uptime tracking and reporting

### Integration Management
- Configuration management for external services
- Read/write service configuration (.env files)
- Secure credential management with masked values
- Support for Home Assistant, Weather API, and InfluxDB configurations
- MQTT/Zigbee configuration endpoints

### Service Control
- Docker service status monitoring
- Service listing and health checks
- Restart capabilities (requires Docker socket access)
- Container management via Docker SDK

### Data Management
- InfluxDB query interface
- Data export capabilities
- Historical data analysis
- Real-time metrics collection

### Alert Management
- Real-time alert monitoring and management
- Automatic cleanup of stale alerts (timeout alerts older than 1 hour)
- Alert acknowledgment and resolution
- Critical alert filtering and prioritization
- Alert lifecycle management

### Devices & Entities
- Device and entity metadata queries
- Device discovery and management
- Entity state tracking

## API Endpoints

### Health & Monitoring

#### `GET /health`
Simple health check endpoint for Docker and monitoring
```bash
curl http://localhost:8004/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-15T12:00:00Z",
  "service": "admin-api",
  "uptime_seconds": 3600
}
```

#### `GET /api/health`
Simple health endpoint that always works
```bash
curl http://localhost:8004/api/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-15T12:00:00Z",
  "service": "admin-api"
}
```

#### `GET /api/v1/health`
Enhanced health endpoint with dependency information
```json
{
  "status": "healthy",
  "service": "admin-api",
  "timestamp": "2025-11-15T12:00:00Z",
  "uptime_seconds": 3600,
  "uptime_human": "1h 0m 0s",
  "uptime_percentage": 100.0,
  "dependencies": [
    {
      "name": "InfluxDB",
      "type": "database",
      "status": "healthy",
      "response_time_ms": 5.2,
      "last_check": "2025-11-15T12:00:00Z"
    },
    {
      "name": "WebSocket Ingestion",
      "type": "websocket",
      "status": "healthy",
      "response_time_ms": 12.1,
      "last_check": "2025-11-15T12:00:00Z"
    },
    {
      "name": "Enrichment Pipeline",
      "type": "service",
      "status": "healthy",
      "response_time_ms": 8.7,
      "last_check": "2025-11-15T12:00:00Z"
    }
  ],
  "metrics": {
    "uptime_human": "1h 0m 0s",
    "uptime_percentage": 100.0,
    "total_requests": 0,
    "error_rate": 0.0
  }
}
```

#### `GET /api/metrics/realtime`
Simple real-time metrics endpoint
```bash
curl http://localhost:8004/api/metrics/realtime
```

Response:
```json
{
  "success": true,
  "events_per_second": 0.0,
  "active_api_calls": 0,
  "active_sources": [],
  "timestamp": "2025-11-15T12:00:00Z"
}
```

### Integration Management

#### `GET /api/v1/integrations`
List all available service integrations
```bash
curl http://localhost:8004/api/v1/integrations
```

Response:
```json
{
  "integrations": [
    {
      "id": "websocket",
      "name": "Home Assistant WebSocket",
      "description": "Home Assistant connection configuration",
      "configured": true
    },
    {
      "id": "weather",
      "name": "Weather API",
      "description": "Weather data integration",
      "configured": true
    },
    {
      "id": "influxdb",
      "name": "InfluxDB",
      "description": "Time-series database configuration",
      "configured": true
    }
  ]
}
```

#### `GET /api/v1/integrations/{service}/config`
Get configuration for a specific service
```bash
curl http://localhost:8004/api/v1/integrations/websocket/config
```

Response:
```json
{
  "service": "websocket",
  "config": {
    "HA_URL": "ws://homeassistant.local:8123/api/websocket",
    "HA_TOKEN": "••••••••",
    "HA_VERIFY_SSL": "true",
    "HA_RECONNECT_DELAY": "5"
  },
  "masked_fields": ["HA_TOKEN"]
}
```

#### `PUT /api/v1/integrations/{service}/config`
Update service configuration
```bash
curl -X PUT http://localhost:8004/api/v1/integrations/websocket/config \
  -H "Content-Type: application/json" \
  -d '{
    "HA_URL": "ws://homeassistant.local:8123/api/websocket",
    "HA_TOKEN": "new-token-here",
    "HA_VERIFY_SSL": "true"
  }'
```

### Service Control

#### `GET /api/v1/services`
List all Docker services with status
```bash
curl http://localhost:8004/api/v1/services
```

Response:
```json
{
  "services": [
    {
      "name": "websocket-ingestion",
      "status": "running",
      "health": "healthy",
      "uptime": "2h 34m"
    },
    {
      "name": "data-api",
      "status": "running",
      "health": "healthy",
      "uptime": "2h 34m"
    }
  ]
}
```

#### `POST /api/v1/services/{service}/restart`
Restart a Docker service (requires Docker socket access)
```bash
curl -X POST http://localhost:8004/api/v1/services/websocket-ingestion/restart
```

### Alert Management (Epic 17.4)

#### `GET /api/v1/alerts/active`
Get all active alerts with automatic cleanup of stale alerts
```bash
curl http://localhost:8004/api/v1/alerts/active
```

**Features:**
- Automatically resolves timeout alerts older than 1 hour
- Filters by severity (optional): `?severity=critical`
- Returns only currently relevant alerts

**Response:**
```json
{
  "value": [
    {
      "id": "service_unhealthy_1234567890",
      "name": "service_unhealthy",
      "severity": "critical",
      "status": "active",
      "message": "Service health is critical: critical",
      "service": "admin-api",
      "metric": "health_status",
      "current_value": null,
      "threshold_value": null,
      "created_at": "2025-11-15T21:19:58.537970Z",
      "resolved_at": null,
      "acknowledged_at": null,
      "metadata": {
        "dependency": "WebSocket Ingestion",
        "response_time_ms": 2000.0,
        "message": "Timeout after 2.0s"
      }
    }
  ],
  "Count": 1
}
```

#### `POST /api/v1/alerts/{alert_id}/acknowledge`
Acknowledge an alert
```bash
curl -X POST http://localhost:8004/api/v1/alerts/service_unhealthy_1234567890/acknowledge
```

#### `POST /api/v1/alerts/{alert_id}/resolve`
Resolve an alert
```bash
curl -X POST http://localhost:8004/api/v1/alerts/service_unhealthy_1234567890/resolve
```

### Metrics Endpoints (Epic 17.3)

#### `GET /api/v1/metrics`
Get current system metrics
```bash
curl http://localhost:8004/api/v1/metrics
```

### Events Endpoints

#### `GET /api/v1/events`
Query historical events from InfluxDB
```bash
curl http://localhost:8004/api/v1/events
```

### Statistics Endpoints

#### `GET /api/v1/stats`
Get system statistics from InfluxDB
```bash
curl http://localhost:8004/api/v1/stats
```

### Configuration Endpoints

#### `GET /api/v1/config`
Get system configuration
```bash
curl http://localhost:8004/api/v1/config
```

### MQTT/Zigbee Configuration

#### MQTT configuration endpoints
MQTT and Zigbee configuration management endpoints available under `/api/v1/mqtt/*`

### Devices & Entities

#### Device and entity management endpoints
Device discovery and entity state tracking available under `/api/v1/devices/*`

## Configuration

### Environment Variables

```bash
# API Configuration
API_PORT=8004
API_HOST=0.0.0.0
API_TITLE=Home Assistant Ingestor Admin API
API_VERSION=1.0.0
API_DESCRIPTION=Admin API for Home Assistant Ingestor

# Security
API_KEY=your-api-key-here
ENABLE_AUTH=true

# CORS Settings
CORS_ORIGINS=*
CORS_METHODS=GET,POST,PUT,DELETE
CORS_HEADERS=*

# InfluxDB Connection
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your-token
INFLUXDB_ORG=homeiq
INFLUXDB_BUCKET=home_assistant_events

# Configuration Management
CONFIG_DIR=/app/infrastructure
CONFIG_FILE_PERMISSIONS=0600

# Logging
LOG_LEVEL=info
RELOAD=false
```

### Configuration Files

The service reads/writes configuration from:
- `infrastructure/.env.websocket` - Home Assistant configuration
- `infrastructure/.env.weather` - Weather API configuration
- `infrastructure/.env.influxdb` - InfluxDB configuration

## Architecture

### Components

```
admin-api/
├── src/
│   ├── main.py                    # Main application with lifespan management
│   ├── config_manager.py          # Configuration file I/O
│   ├── config_endpoints.py        # Configuration API endpoints
│   ├── health_endpoints.py        # Health check endpoints
│   ├── events_endpoints.py        # Events query endpoints
│   ├── docker_endpoints.py        # Docker management endpoints
│   ├── devices_endpoints.py       # Device & entity endpoints
│   ├── mqtt_config_endpoints.py   # MQTT/Zigbee configuration
│   └── metrics_endpoints.py       # Metrics endpoints (Epic 17.3)
│   └── alert_endpoints.py         # Alert management (Epic 17.4)
├── tests/                         # Unit tests
│   └── (tests being rebuilt)
├── Dockerfile                     # Production container
├── Dockerfile.dev                 # Development container
├── requirements.txt               # Python dependencies
├── requirements-prod.txt          # Production dependencies
└── pytest.ini                     # Test configuration
```

### Shared Dependencies

The service uses shared libraries from `/shared`:
- `logging_config.py` - Centralized logging with correlation IDs
- `correlation_middleware.py` - FastAPI correlation middleware
- `monitoring.py` - Monitoring services (logging, metrics, alerting)
- `auth.py` - Authentication management
- `endpoints.py` - Integration router factory

### Design Patterns

- **FastAPI Router Pattern** - Modular endpoint organization
- **Dependency Injection** - Configuration and client management
- **Repository Pattern** - Data access abstraction
- **Lifespan Management** - Proper startup/shutdown handling with async context managers
- **Middleware Pattern** - CORS, logging, and correlation ID middleware
- **Monitoring Services** - Centralized logging, metrics, and alerting

## Development

### Local Setup

```bash
# Navigate to service directory
cd services/admin-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally
python -m uvicorn src.main:app --reload --port 8004
```

### Running with Docker

```bash
# Build container
docker compose build admin-api

# Start service
docker compose up admin-api

# View logs
docker compose logs -f admin-api
```

### API Documentation

When running, interactive API documentation is available at:
- **Swagger UI:** http://localhost:8004/docs
- **ReDoc:** http://localhost:8004/redoc
- **OpenAPI JSON:** http://localhost:8004/openapi.json

**Note:** API docs are disabled when `ENABLE_AUTH=true` for security.

## Testing

### Run Unit Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src --cov-report=html tests/

# Run specific test file
pytest tests/test_health_endpoints.py

# Run async tests
pytest tests/ -v
```

**Note:** Automated test framework is being rebuilt as of November 2025. Use manual testing in the meantime.

### Manual Testing

```bash
# Test health endpoints
curl http://localhost:8004/health
curl http://localhost:8004/api/health
curl http://localhost:8004/api/v1/health

# Test integrations list
curl http://localhost:8004/api/v1/integrations

# Test configuration read
curl http://localhost:8004/api/v1/integrations/websocket/config

# Test metrics
curl http://localhost:8004/api/metrics/realtime

# Test active alerts
curl http://localhost:8004/api/v1/alerts/active
```

## Security

### Authentication
- API key authentication (configurable via `ENABLE_AUTH`)
- HTTP Bearer token support
- CORS configuration for frontend access
- Credential masking in API responses

### Configuration Security
- Sensitive values are masked in API responses (e.g., `HA_TOKEN` → `••••••••`)
- Configuration files set to 600 permissions
- No secrets logged or exposed in error messages
- Secure environment variable management

### Best Practices
- Use environment variables for secrets
- Enable HTTPS in production
- Implement rate limiting for public endpoints
- Regular security audits
- Enable authentication in production (`ENABLE_AUTH=true`)

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
docker compose logs admin-api
```

**Common issues:**
- InfluxDB not accessible → Service will log warning but continue
- Configuration files missing → Check `infrastructure/` directory
- Port 8004 already in use → Change `API_PORT` environment variable
- Shared modules not found → Ensure `/shared` directory is accessible

### Configuration Not Saving

**Check permissions:**
```bash
ls -la infrastructure/.env.*
```

**Should show:** `-rw-------` (600 permissions)

**Fix permissions:**
```bash
chmod 600 infrastructure/.env.*
```

### Service Restart Failing

**Limitation:** Service restart requires Docker socket access

**Workaround:** Use command line
```bash
docker compose restart websocket-ingestion
```

**Future:** Mount Docker socket in docker-compose.yml or use Docker API

### InfluxDB Connection Issues

**Symptoms:** Statistics endpoints return errors or fall back to direct service calls

**Solutions:**
1. Check InfluxDB is running: `curl http://localhost:8086/health`
2. Verify `INFLUXDB_TOKEN` is correct
3. Check network connectivity between containers

## Performance

### Performance Targets

| Endpoint Type | Target | Acceptable | Investigation |
|---------------|--------|------------|---------------|
| Health checks | <10ms | <50ms | >100ms |
| Metrics queries | <50ms | <100ms | >200ms |
| InfluxDB queries | <100ms | <200ms | >500ms |
| Configuration reads | <20ms | <50ms | >100ms |

### Resource Usage

- **Memory:** ~100-150MB baseline
- **CPU:** Minimal (<5% during normal operation)
- **Throughput:** 1000+ requests/minute
- **Concurrent Connections:** 100+

## Dependencies

### Core Dependencies

```
fastapi==0.121.2           # Web framework
uvicorn[standard]==0.38.0  # ASGI server
pydantic==2.12.4           # Data validation
```

### Authentication & Security

```
python-jose[cryptography]==3.5.0  # JWT tokens
passlib[bcrypt]==1.7.4            # Password hashing
python-multipart==0.0.20          # Form data parsing
```

### HTTP & Networking

```
aiohttp==3.13.2           # Async HTTP client
requests==2.32.5          # Sync HTTP client
```

### Database & Storage

```
influxdb-client==1.49.0   # InfluxDB 2.x client
```

### System & Monitoring

```
psutil==7.1.3             # System metrics
docker==6.1.3             # Docker SDK for Python
```

### Configuration & Environment

```
python-dotenv==1.2.1      # Environment variable management
```

### Development & Testing

```
pytest==8.3.3             # Testing framework
pytest-asyncio==0.23.0    # Async test support
httpx==0.27.2             # Async HTTP testing
black==23.11.0            # Code formatter
isort==5.12.0             # Import sorter
flake8==6.1.0             # Code linter
```

## Contributing

1. Follow Python PEP 8 style guidelines
2. Use Black for code formatting
3. Use isort for import sorting
4. Add type hints for all functions
5. Document all endpoints with docstrings
6. Update tests when adding functionality
7. Update this README when adding features

### Code Style

```python
"""Module docstring"""

from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)

@router.get("/api/v1/example", response_model=ExampleResponse)
async def example_endpoint(request: ExampleRequest) -> ExampleResponse:
    """
    Example endpoint with proper documentation

    Args:
        request: Example request payload

    Returns:
        ExampleResponse with processed data

    Raises:
        HTTPException: If processing fails
    """
    try:
        # Implementation
        pass
    except Exception as e:
        logger.error(f"Failed to process request: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

## Related Documentation

- [API Reference](../../docs/api/API_REFERENCE.md) - Complete API documentation
- [Architecture Overview](../../docs/architecture/) - System architecture
- [Database Schema](../../docs/architecture/database-schema.md) - Database structure
- [Deployment Guide](../../docs/DEPLOYMENT_GUIDE.md) - Deployment instructions
- [CLAUDE.md](../../CLAUDE.md) - AI assistant development guide

## Support

- **Issues:** File on GitHub at https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** Check `/docs` directory
- **API Docs:** http://localhost:8004/docs
- **Health Status:** http://localhost:8004/health

## Version History

### 2.1 (November 15, 2025)
- Updated port from 8003 to 8004
- Added comprehensive dependency documentation
- Enhanced health endpoint documentation
- Added metrics and alert endpoints
- Updated testing information
- Improved troubleshooting section

### 2.0 (October 11, 2025)
- Added integration management
- Added service control features
- Added alert management
- Enhanced monitoring capabilities

### 1.0 (Initial Release)
- Basic health checks
- InfluxDB query interface
- Statistics endpoints

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅
**Port:** 8004
