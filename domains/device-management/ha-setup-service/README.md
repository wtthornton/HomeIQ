# HA Setup & Recommendation Service

**Automated health monitoring, setup assistance, and performance optimization for Home Assistant**

**Port:** 8020 (internal), exposed as **8024** (host)
**Technology:** Python 3.11+, FastAPI, SQLAlchemy, AsyncIO
**Container:** homeiq-setup-service
**Init gateway:** `/api/v1/init/audit` (read-only) and `/api/v1/init/converge` (backup-gated) — see `docs/operations/init-gateway.md`
**Tests:** `.venv/bin/python -m pytest domains/device-management/ha-setup-service/tests -q` — run this tree **separately** from `libs/homeiq-ha` (both expose a `tests` package; a combined invocation fails collection on `tests.path_setup`)
**Database:** PostgreSQL (schema: `devices`)
**Scale:** Optimized for single Home Assistant instance

## Overview

The HA Setup & Recommendation Service provides comprehensive health monitoring, automated setup wizards, and performance optimization for Home Assistant environments integrated with HomeIQ. It continuously monitors the health of Home Assistant, its integrations, and HomeIQ services, providing actionable recommendations.

**Port Mapping Note:** This service runs on port 8020 internally within the Docker network and is exposed as port **8024** on the host. From outside Docker use 8024; internal services use 8020.

### Key Features

- **Environment Health Monitoring** - Real-time health score (0-100) with intelligent weighting and graceful degradation
- **Integration Health Checks** - Monitor HA authentication, device discovery, and HomeIQ services
- **Continuous Monitoring** - Background health monitoring with configurable intervals
- **Health Trends** - Track health score trends over time
- **Init Gateway** - Read-only `audit` and backup-gated `converge` over the HA init agent's recipes
- **Human-Decision Queue** - Surface `blocked_on_human` outcomes and accept answers
- **Performance Optimization** - Automated performance analysis and recommendations
- **Configuration Validation** - Detect and fix Home Assistant configuration issues (Epic 32)
- **Area Assignment Fixes** - Automatically fix missing or incorrect area assignments

**Health Scoring Algorithm (Updated December 2025):**
- **Graceful Degradation:** Health score no longer returns 0 when data is incomplete
  - HA Core "error/unknown" status scores 25 (instead of 0)
  - Empty integrations list scores 30 (instead of 0)
  - 0ms response time scores 80 (assumes good performance)
- **Weighted Components:**
  - HA Core: 35% weight
  - Integrations: 35% weight
  - Performance: 15% weight
  - Reliability: 15% weight
- **Result:** Health score provides meaningful feedback even with partial data, preventing false "0/100" scores

## API Endpoints

### Health Endpoints

```bash
GET /health
```
Simple health check for container orchestration.

**Response:**
```json
{
  "status": "healthy",
  "service": "ha-setup-service",
  "timestamp": "2025-12-09T10:30:00Z",
  "version": "1.0.0"
}
```

```bash
GET /api/health/environment
```
Comprehensive environment health status.

**Response:**
```json
{
  "health_score": 95,
  "ha_status": "healthy",
  "integrations": [
    {
      "integration_name": "Home Assistant",
      "integration_type": "core",
      "status": "healthy",
      "is_configured": true,
      "is_connected": true,
      "last_check": "2025-12-09T10:30:00Z"
    }
  ],
  "performance_metrics": {
    "cpu_usage": 15.5,
    "memory_usage": 42.3,
    "disk_usage": 35.7
  },
  "issues_detected": []
}
```

```bash
GET /api/health/trends?hours=24
```
Health trends over specified time period.

**Query Parameters:**
- `hours` (optional) - Number of hours to analyze (default: 24)

**Response:**
```json
{
  "average_score": 93.5,
  "min_score": 85,
  "max_score": 98,
  "trend": "stable",
  "data_points": 24
}
```

```bash
GET /api/health/integrations
```
Detailed integration health status.

**Response:**
```json
{
  "timestamp": "2025-12-09T10:30:00Z",
  "total_integrations": 5,
  "healthy_count": 4,
  "warning_count": 1,
  "error_count": 0,
  "not_configured_count": 0,
  "integrations": [
    {
      "integration_name": "Device Discovery",
      "integration_type": "discovery",
      "status": "healthy",
      "is_configured": true,
      "is_connected": true,
      "check_details": {
        "sync_status": "synced",
        "devices_discovered": 15
      }
    }
  ]
}
```

### Init Gateway Endpoints

The HA init agent (`libs/homeiq-ha/src/homeiq_ha/agent/`) is served here. This is
the only path in HomeIQ that writes to Home Assistant. Full semantics in
[docs/operations/init-gateway.md](../../../docs/operations/init-gateway.md).

```bash
GET /api/v1/init/audit
```
Runs every recipe's `check()` behind a read-only proxy that raises on any write.
Always safe. Returns one outcome row per recipe with `status`
(`satisfied` / `needs_apply` / `blocked_on_human` / `not_applicable`), `summary`,
`details`, and `human_action`.

```bash
POST /api/v1/init/converge   {"phase": N, "only": "<recipe>"}
```
Backup-gated plan -> apply -> verify. A backup is taken before every phase past
the gate; a `blocked_on_human` outcome halts later phases.

```bash
GET  /api/v1/init/queue?show_all=false
POST /api/v1/init/answers
```
The human-decision queue and its answer sink. `queue` returns `audit_blocked`
items carrying a `decision` payload (e.g. `type: "area_assignment"` listing the
devices needing an area); `answers` submits the resolutions.

```bash
POST /api/v1/init/pairing/permit
POST /api/v1/init/flows/{flow_id}/start
POST /api/v1/init/flows/{flow_id}/decision
POST /api/v1/init/hacs/start
```
Zigbee permit-join (ZHA), HA config-flow driving, and HACS bootstrap.

### Performance Optimization

```bash
GET /api/optimization/analyze
```
Run comprehensive performance analysis.

**Response:**
```json
{
  "bottlenecks": [
    {
      "component": "database",
      "severity": "moderate",
      "description": "High query latency detected",
      "recommendation": "Add database indexes"
    }
  ],
  "overall_score": 75
}
```

```bash
GET /api/optimization/recommendations
```
Get prioritized optimization recommendations.

**Response:**
```json
{
  "timestamp": "2025-12-09T10:30:00Z",
  "total_recommendations": 3,
  "recommendations": [
    {
      "priority": "high",
      "category": "performance",
      "title": "Optimize database queries",
      "description": "Add indexes to frequently queried tables",
      "impact": "Reduce query latency by 50%"
    }
  ]
}
```

### Configuration Validation (Epic 32)

```bash
GET /api/v1/validation/ha-config
```
Validate Home Assistant configuration and get suggestions.

**Query Parameters:**
- `category` (optional) - Filter by issue category (e.g., "missing_area_assignment")
- `min_confidence` (optional) - Minimum confidence score 0-100 (default: 0)

**Response:**
```json
{
  "issues": [
    {
      "category": "missing_area_assignment",
      "entity_id": "light.hue_office_back_left",
      "description": "Entity is not assigned to an area",
      "suggested_fix": {
        "area_id": "office",
        "confidence": 95
      }
    }
  ],
  "total_issues": 5,
  "timestamp": "2025-12-09T10:30:00Z"
}
```

```bash
POST /api/v1/validation/apply-fix
```
Apply single area assignment fix.

**Request:**
```json
{
  "entity_id": "light.hue_office_back_left",
  "area_id": "office"
}
```

**Response:**
```json
{
  "success": true,
  "entity_id": "light.hue_office_back_left",
  "area_id": "office",
  "message": "Area assignment updated successfully"
}
```

```bash
POST /api/v1/validation/apply-bulk-fixes
```
Apply multiple area assignment fixes in batch.

**Request:**
```json
{
  "fixes": [
    {
      "entity_id": "light.hue_office_back_left",
      "area_id": "office"
    },
    {
      "entity_id": "light.hue_bedroom_main",
      "area_id": "bedroom"
    }
  ]
}
```

**Response:**
```json
{
  "applied": 2,
  "failed": 0,
  "results": [
    {
      "entity_id": "light.hue_office_back_left",
      "success": true
    }
  ]
}
```

### Service Info

```bash
GET /
```
Root endpoint with service information and available endpoints.

## Configuration

### Environment Variables

#### Service Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | `ha-setup-service` | Service name for logging |
| `SERVICE_PORT` | `8020` | Internal service port |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

#### Home Assistant Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HA_URL` | `http://192.168.1.86:8123` | Home Assistant URL |
| `HA_TOKEN` | *From env* | HA long-lived access token (auto-loaded from infrastructure/.env.websocket) |
| `HOME_ASSISTANT_TOKEN` | *From env* | Alternative token variable name |

#### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg:////app/data/ha-setup.db` | PostgreSQL database URL (absolute path for Docker) |

#### API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_API_URL` | `http://homeiq-data-api:8006` | Data API URL |
| `ADMIN_API_URL` | `http://homeiq-admin-api:8004` | Admin API URL |

#### Health Check Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HEALTH_CHECK_INTERVAL` | `60` | Health check interval (seconds) |
| `INTEGRATION_CHECK_INTERVAL` | `300` | Integration check interval (seconds) |

#### Performance Monitoring

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_PERFORMANCE_MONITORING` | `True` | Enable performance monitoring |
| `PERFORMANCE_SAMPLE_INTERVAL` | `30` | Performance sampling interval (seconds) |

## Development

### Running Locally

```bash
cd domains/device-management/ha-setup-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set required environment variables
export HA_TOKEN="your-ha-long-lived-token"

uvicorn src.main:app --reload --port 8020
```

### Running with Docker

```bash
# Build and start service
docker compose up -d ha-setup-service

# View logs
docker compose logs -f ha-setup-service

# Test health endpoint (external port)
curl http://localhost:8024/health

# Test from inside Docker network (internal port)
docker exec homeiq-health-dashboard curl http://ha-setup-service:8020/health
```

### Testing Endpoints

```bash
# Health check
curl http://localhost:8024/health

# Environment health
curl http://localhost:8024/api/health/environment

# Integration health
curl http://localhost:8024/api/health/integrations

# Health trends (24 hours)
curl "http://localhost:8024/api/health/trends?hours=24"

# Init audit (read-only)
curl http://localhost:8024/api/v1/init/audit

# Configuration validation
curl http://localhost:8024/api/v1/validation/ha-config

# Performance analysis
curl http://localhost:8024/api/optimization/analyze
```

## Dependencies

### Service Dependencies

- **Home Assistant** - External instance for integration health monitoring
- **data-api** (Port 8006) - Historical data queries
- **admin-api** (Port 8003) - System control
- **PostgreSQL Database** - Health history and validation results

### Python Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy` - Database ORM with async support
- `asyncpg` - Async PostgreSQL driver
- `pydantic` - Configuration management and validation
- `pydantic-settings` - Environment variable loading
- `aiohttp` - Async HTTP client for HA API calls
- `shared` - HomeIQ shared libraries (logging, observability)

## Related Services

### Upstream Dependencies

- **Home Assistant** - Core integration being monitored
- **data-api** - Health metrics and historical data
- **admin-api** - System administration

### Downstream Consumers

- **health-dashboard** - Displays health monitoring UI
- **ai-automation-ui** - Shows integration status

## Architecture Notes

### Health Monitoring System

The service implements a comprehensive health monitoring system:
1. **Continuous Monitoring** - Background task runs at configurable intervals
2. **Health Score Calculation** - Weighted scoring based on component health
3. **Trend Analysis** - Track health over time to detect degradation
4. **Issue Detection** - Automatically detect and report issues
5. **Database Storage** - Store health history for analysis

### Integration Health Checks

Monitors these integrations:
- **Home Assistant Core** - API authentication and availability
- **Device Discovery** - Registry sync verification (HA device count vs ingestor count)
- **Data API** - HomeIQ service health
- **Admin API** - HomeIQ service health
- **HACS** - Custom-component store availability

Zigbee is **HA built-in ZHA**, checked by the init agent's `zigbee.*` recipes
(coordinator watchdog, mesh health) rather than by this hand-rolled check list.
HomeIQ runs no MQTT broker and no Zigbee2MQTT; see
[docs/operations/init-gateway.md](../../../docs/operations/init-gateway.md).

### Init Gateway

Recipe-driven convergence over Home Assistant:
- **Audit** - Every recipe's `check()` behind a write-raising read-only proxy
- **Converge** - Backup-gated plan -> apply -> verify, halting on `blocked_on_human`
- **Queue / Answers** - Surface human decisions (area assignment, pairing) and accept them
- **Zigbee (ZHA)** - Coordinator watchdog and mesh-health recipes, plus permit-join

### Configuration Validation (Epic 32)

Validates Home Assistant configuration:
- **Missing Area Assignments** - Detect entities without areas
- **Incorrect Area Assignments** - Suggest better area assignments
- **Bulk Fixes** - Apply multiple fixes in one operation
- **Confidence Scoring** - AI-based confidence for suggestions

## Monitoring

### Health Checks

- **Liveness:** `GET /health` - Service is running
- **Environment Health:** `GET /api/health/environment` - Complete system status
- **Integration Health:** `GET /api/health/integrations` - All integration statuses

### Logging

All logs follow structured logging format:
```json
{
  "timestamp": "2025-12-09T10:30:00Z",
  "level": "INFO",
  "service": "ha-setup-service",
  "event": "environment_health",
  "health_score": 95,
  "issues_detected": 0
}
```

### Database Schema

**Tables:**
- `health_checks` - Historical health check results
- `integration_health` - Integration health history
- `validation_results` - Configuration validation findings

## Security Notes

- **HA Token** - Automatically loaded from `infrastructure/.env.websocket`
- **CORS Configuration** - Allows localhost:3000 and localhost:3001
- **No Public Exposure** - Internal service, assumes trusted network
- **PostgreSQL Security** - Database file permissions restricted to service user

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
docker compose logs ha-setup-service
```

**Common issues:**
- Missing `HA_TOKEN` - Verify `infrastructure/.env.websocket`
- Database initialization failed - Check `/app/data` volume permissions
- Port 8024 in use - Change the host mapping in `domains/device-management/compose.yml`

### HA Authentication Failures

**Symptoms:**
- Integration health shows "error" status
- "Invalid authentication" errors in logs

**Solutions:**
```bash
# Verify HA token
curl -H "Authorization: Bearer $HA_TOKEN" http://192.168.1.86:8123/api/

# Check environment variable
docker exec homeiq-ha-setup-service env | grep HA_TOKEN

# Regenerate token in Home Assistant
# Profile → Long-Lived Access Tokens → Create Token
```

### Zigbee (ZHA) Issues

Zigbee is HA's built-in ZHA on an SMLIGHT SLZB-06p7. The init agent owns the
probes; there is no bridge service to restart here.

**Check coordinator and mesh health:**
```bash
curl -s http://localhost:8024/api/v1/init/audit \
  | python3 -c "import json,sys; [print(o) for o in json.load(sys.stdin)['outcomes']]" \
  | grep -i zigbee
```

A `blocked_on_human` row from `zigbee.coordinator_watchdog` carries a
`human_action` (typically a coordinator power-cycle). See
[docs/operations/init-gateway.md](../../../docs/operations/init-gateway.md).

## Version History

- **v1.0.0** (December 2025) - Initial production release
  - Environment health monitoring with 0-100 scoring
  - Integration health checks (HA, device discovery, HomeIQ services)
  - Continuous monitoring with configurable intervals
  - Health trend analysis
  - Init gateway: audit, converge, decision queue
  - Performance optimization engine
  - Configuration validation (Epic 32)
  - Area assignment fixes
  - Lifespan context manager pattern (Context7 best practices)

---

**Last Updated:** August 20, 2026
**Version:** 1.0.0
**Status:** Production Ready ✅
**Port:** 8020 (internal) / 8024 (external)
