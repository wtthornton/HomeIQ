# API Reference - Complete Endpoint Documentation

**Last Updated:** February 2026 (Docker: activity-recognition, energy-forecasting)  
**API Version:** v4.9  
**Status:** ✅ Production Ready  
**Recent Updates:** Blueprint-First Architecture (January 2026) - Blueprint Index Service, Blueprint Opportunity Engine, Blueprint Deployer, Blueprint-enriched synergies; Epic AI-24 Device Mapping Library (January 2025), Device mapping API endpoints, Plugin-based device handlers, Epic AI-6 Blueprint-Enhanced Suggestion Intelligence (December 2025), Preference API endpoints, Pattern validation, Preference-aware ranking

> **📌 This is the SINGLE SOURCE OF TRUTH for all HA Ingestor API documentation.**  
> **Supersedes:** API_DOCUMENTATION.md, API_COMPREHENSIVE_REFERENCE.md, API_ENDPOINTS_REFERENCE.md

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Authentication](#authentication)
4. [Admin API](#admin-api) (Port 8004)
5. [Data API](#data-api) (Port 8006)
6. [Sports API Service](#sports-api-service) (Port 8005)
7. [AI Automation Services](#ai-automation-services-epic-39-modularization) (Ports 8016-8018, 8021)
8. [HA AI Agent Service](#ha-ai-agent-service) (Port 8030)
9. [Device Intelligence Service](#device-intelligence-service) (Port 8028)
10. [Blueprint Index Service](#blueprint-index-service) (Port 8031) - NEW
11. [AI Pattern Service](#ai-pattern-service) (Port 8020) - Blueprint Opportunities
12. [Statistics API](#statistics-api)
13. [Error Handling](#error-handling)
14. [Integration Examples](#integration-examples)

---

## Overview

### System Purpose

The HA Ingestor is an **API-first platform** designed for Home Automation data management and intelligent automation.

**Primary Consumers:**
- Home Assistant automations (webhook triggers, fast status APIs <50ms)
- External analytics platforms (historical queries, trends)
- Cloud integrations (mobile apps, voice assistants)
- Third-party systems (API access to all data sources)

**Deployment:** Single-tenant, self-hosted (one per home)

### Base URLs

| Service | Port | Base URL | Purpose |
|---------|------|----------|---------|
| **Admin API** | 8004 | `http://localhost:8004` | System monitoring, Docker management |
| **Data API** | 8006 | `http://localhost:8006` | Feature data (events, devices, sports, analytics) |
| **AI Automation** | 8024 | `http://localhost:8024` | Automation suggestions & conversational AI |
| **AI Pattern Service** | 8020/8034 | `http://localhost:8034` | Pattern detection, synergy analysis, blueprint opportunities |
| **Blueprint Index** | 8031 | `http://localhost:8031` | Blueprint indexing and search (NEW) |
| **HA AI Agent** | 8030 | `http://localhost:8030` | Tier 1 Context Injection for Home Assistant AI Agent [Epic AI-19] |
| **Dashboard** | 3000 | `http://localhost:3000` | Frontend (nginx proxy to APIs) |
| **AI Automation UI** | 3001 | `http://localhost:3001` | Conversational automation UI |
| **InfluxDB** | 8086 | `http://localhost:8086` | Time-series database |
| **Activity Recognition** | 8043 | `http://localhost:8043` | User activity detection from sensor patterns (Tier 6) |
| **Energy Forecasting** | 8042 | `http://localhost:8042` | 7-day energy consumption predictions (Tier 3) |

---

## Architecture

### Epic 13 API Separation (October 2025)

```
┌──────────────────────────────────────────────────────────────┐
│              Health Dashboard (Port 3000)                     │
│                      nginx proxy                              │
└──────────────────┬────────────────────────┬───────────────────┘
                   │                        │
      System Monitoring & Control  Feature Data Queries
                   │                        │
                   ▼                        ▼
┌─────────────────────────────┐  ┌──────────────────────────────┐
│   Admin API (8004)     │  │     Data API (8006)          │
│                             │  │                              │
│ • Health checks             │  │ • Events (8 endpoints)       │
│ • Docker management (5)     │  │ • Devices & Entities (5)     │
│ • Service monitoring (4)    │  │ • Sports data (9)            │
│ • Configuration (3)         │  │ • HA automation (4)          │
│ • Statistics (8)            │  │ • Analytics (4)              │
│ • WebSocket (/ws)           │  │ • Alerts (6)                 │
│                             │  │ • WebSocket (/api/v1/ws)     │
│ ~22 endpoints               │  │ ~40 endpoints                │
└─────────────────────────────┘  └──────────────────────────────┘
           │                                 │
           └────────────┬────────────────────┘
                        ▼
               ┌─────────────────┐
               │  InfluxDB 2.7   │
               │   Port 8086     │
               └─────────────────┘
```

### Epic 31 Event Flow Architecture (October 2025)

**Current Event Flow (Post-Epic 31):**
```
Home Assistant WebSocket (192.168.1.86:8123)
        ↓
websocket-ingestion (Port 8001)
  - Event validation (inline)
  - Inline normalization
  - Device/area lookups (Epic 23.2)
  - Duration calculation (Epic 23.3)
  - DIRECT InfluxDB writes
        ↓
InfluxDB (Port 8086)
  bucket: home_assistant_events
        ↓
data-api (Port 8006)
  - Query endpoint for events
        ↓
health-dashboard (Port 3000)
```

**Key Changes (Epic 31):**
- ❌ **Deprecated:** enrichment-pipeline service (Port 8002) - Removed to simplify architecture
- ✅ **Current:** Direct InfluxDB writes from websocket-ingestion (inline normalization)
- ✅ **External Services:** Standalone pattern - Fetch → Write to InfluxDB → Query via data-api
- ✅ **Benefits:** Reduced latency, fewer failure points, simplified architecture

**External Services Pattern (Epic 31):**
- `weather-api` (Port 8009) - Writes weather data directly to InfluxDB
- `sports-api` (Port 8005) - Writes sports scores directly to InfluxDB
- `carbon-intensity` (Port 8010) - Writes carbon data directly to InfluxDB
- All services query via data-api, no service-to-service HTTP dependencies

**See:** [Event Flow Architecture](../architecture/event-flow-architecture.md) for detailed event processing flow

---

## Authentication

### Local Network (Development)
```bash
# No authentication required for local access
curl http://localhost:8004/health
```

### Remote Access (Production)
```bash
# API Key Authentication
curl -H "X-API-Key: your-api-key" http://api.domain.com/health

# JWT Token Authentication
curl -H "Authorization: Bearer your-jwt-token" http://api.domain.com/health
```

### Configuration
Set `ENABLE_AUTH=false` in environment variables to disable authentication (development only).

---

## Admin API

**Base URL:** `http://localhost:8004`  
**Purpose:** System monitoring, health checks, Docker container management

### Health Endpoints

#### GET /health
Basic health status of admin-api service.

**Response:**
```json
{
  "status": "healthy",
  "service": "admin-api",
  "uptime": "0:05:23.123456",
  "timestamp": "2025-10-20T12:00:00Z"
}
```

#### GET /api/v1/health
Comprehensive health status of all system services.

**Response:**
```json
{
  "overall_status": "healthy",
  "admin_api_status": "healthy",
  "services": {
    "websocket_ingestion": {
      "status": "healthy",
      "connection": { "is_connected": true },
      "event_processing": { "events_per_minute": 16.28 }
    },
    "data_retention": { "status": "healthy" },
    "influxdb": { "status": "healthy" }
  },
  "timestamp": "2025-10-20T12:00:00Z"
}
```

#### GET /api/v1/health/services
Health status of individual services.

#### GET /api/v1/health/dependencies
Service dependency visualization data.

### Docker Management Endpoints

#### GET /api/v1/docker/containers
List all Docker containers with status.

```json
{
  "containers": [
    {
      "id": "abc123",
      "name": "homeiq-admin",
      "status": "running",
      "image": "homeiq-admin-api:latest"
    }
  ]
}
```

#### POST /api/v1/docker/containers/{container_name}/start
Start a stopped container.

#### POST /api/v1/docker/containers/{container_name}/stop
Stop a running container.

#### POST /api/v1/docker/containers/{container_name}/restart
Restart a container.

#### GET /api/v1/docker/containers/{container_name}/logs?tail=100
Retrieve container logs.

### Statistics Endpoints

See [Statistics API](#statistics-api) section for detailed documentation.

### Configuration Endpoints

#### GET /api/v1/integrations
List all configured integrations.

#### PUT /api/v1/integrations/{integration_name}
Update integration settings.

#### POST /api/v1/integrations/{integration_name}/test
Test integration connectivity.

### Training Endpoints *(October 2025 update)*

#### GET /api/v1/admin/training/runs
Return recent soft prompt training runs (most recent first).

**Response:**
```json
[
  {
    "id": 42,
    "status": "completed",
    "startedAt": "2025-10-24T14:12:06Z",
    "finishedAt": "2025-10-24T14:22:44Z",
    "datasetSize": 1860,
    "baseModel": "google/flan-t5-small",
    "outputDir": "data/ask_ai_soft_prompt/run_20251024_1412",
    "runIdentifier": "run_20251024_1412",
    "finalLoss": 0.9812,
    "errorMessage": null,
    "metadataPath": "data/ask_ai_soft_prompt/run_20251024_1412/training_run.json",
    "triggeredBy": "admin"
  }
]
```

#### POST /api/v1/admin/training/trigger → `202 Accepted`
Queue a new soft prompt fine-tuning job. Returns `409 Conflict` if another job is already running.

**Response:**
```json
{
  "id": 43,
  "status": "queued",
  "startedAt": "2025-10-24T15:01:11Z",
  "finishedAt": null,
  "datasetSize": null,
  "baseModel": null,
  "outputDir": "data/ask_ai_soft_prompt/run_20251024_1501",
  "runIdentifier": "run_20251024_1501",
  "finalLoss": null,
  "errorMessage": null,
  "metadataPath": null,
  "triggeredBy": "admin"
}
```

**Notes:**
- The training job executes asynchronously; clients can poll `GET /api/v1/admin/training/runs` for status updates.
- Artifacts (model weights, tokenizer, metadata) are written under `data/ask_ai_soft_prompt/<runIdentifier>` and symlinked to `latest/` when complete.

### WebSocket

#### WS /ws
Real-time system monitoring updates.

**Events:** System alerts, service status changes

---

## Data API

**Base URL:** `http://localhost:8006`  
**Purpose:** Feature data hub - events, devices, sports, analytics, alerts

### Health Check

#### GET /health
```json
{
  "status": "healthy",
  "service": "data-api",
  "uptime": "0:05:23.123456",
  "influxdb_connected": true
}
```

### Events Endpoints (8 total)

#### GET /api/v1/events
Retrieve recent Home Assistant events.

**Query Parameters:**
- `limit` (default: 100): Number of events
- `offset` (default: 0): Pagination offset
- `entity_id` (optional): Filter by entity
- `start_time` (optional): ISO 8601 start time
- `end_time` (optional): ISO 8601 end time

**Response:**
```json
{
  "events": [
    {
      "id": "event_123",
      "entity_id": "sensor.temperature",
      "state": "72.5",
      "timestamp": "2025-10-20T12:00:00Z",
      "attributes": { "unit": "°F" }
    }
  ],
  "total": 42156,
  "limit": 100,
  "offset": 0
}
```

#### GET /api/v1/events/{event_id}
Retrieve specific event details.

#### POST /api/v1/events/search
Advanced event search with filters.

#### GET /api/v1/events/stats
Event statistics and aggregations.

#### GET /api/v1/events/entity/{entity_id}
Get events for specific entity.

#### GET /api/v1/events/timeline
Timeline view of events.

#### GET /api/v1/events/count
Count events matching criteria.

#### GET /api/v1/events/export?format=csv
Export events in CSV/JSON format.

### Devices & Entities Endpoints

#### GET /api/devices
Get all discovered Home Assistant devices.

**Response:**
```json
{
  "devices": [
    {
      "device_id": "device_abc123",
      "name": "Living Room Light",
      "manufacturer": "Philips",
      "model": "Hue Bulb",
      "sw_version": "1.88.1",
      "area_id": "living_room",
      "integration": "hue",
      "config_entry_id": "entry_123",
      "via_device": null,
      "entity_count": 2,
      "timestamp": "2025-01-20T12:00:00Z"
    }
  ],
  "count": 42
}
```

#### GET /api/devices/{device_id}
Get specific device information.

**Response includes:** device_id, name, manufacturer, model, sw_version, area_id, integration, config_entry_id, via_device, entity_count, timestamp

#### GET /api/entities
Get all Home Assistant entities.

#### GET /api/entities/{entity_id}
Get specific entity information.

**Response includes:** entity_id, device_id, domain, platform, unique_id, area_id, disabled, config_entry_id, name, name_by_user, original_name, friendly_name, supported_features, capabilities, available_services, icon, device_class, unit_of_measurement, timestamp

#### GET /api/entities/{entity_id}/history
Get historical data for entity.

#### Relationship Query Endpoints (NEW)

#### GET /api/entities/by-device/{device_id}
Get all entities for a device.

**Response:**
```json
{
  "success": true,
  "device_id": "device_abc123",
  "entities": [
    {
      "entity_id": "light.living_room",
      "device_id": "device_abc123",
      "domain": "light",
      "platform": "hue",
      "related_entities": ["sensor.living_room_battery"],
      "config_entry_id": "entry_123",
      "capabilities": {"brightness": true, "color": true}
    }
  ],
  "count": 2
}
```

#### GET /api/entities/{entity_id}/siblings
Get sibling entities (entities from same device).

**Response:**
```json
{
  "success": true,
  "entity_id": "light.living_room",
  "siblings": [
    {
      "entity_id": "sensor.living_room_battery",
      "device_id": "device_abc123",
      "domain": "sensor"
    }
  ],
  "count": 1
}
```

#### GET /api/entities/{entity_id}/device
Get device for an entity.

**Response:**
```json
{
  "success": true,
  "entity_id": "light.living_room",
  "device": {
    "device_id": "device_abc123",
    "name": "Living Room Light",
    "manufacturer": "Philips",
    "model": "Hue Bulb",
    "sw_version": "1.88.1",
    "area_id": "living_room",
    "integration": "hue",
    "config_entry_id": "entry_123",
    "via_device": null
  }
}
```

#### GET /api/entities/by-area/{area_id}
Get all entities in an area.

**Response:**
```json
{
  "success": true,
  "area_id": "living_room",
  "entities": [
    {
      "entity_id": "light.living_room",
      "device_id": "device_abc123",
      "area_id": "living_room",
      "related_entities": []
    }
  ],
  "count": 10
}
```

#### GET /api/entities/by-config-entry/{config_entry_id}
Get entities by config entry ID.

**Response:**
```json
{
  "success": true,
  "config_entry_id": "entry_123",
  "entities": [
    {
      "entity_id": "light.living_room",
      "config_entry_id": "entry_123"
    }
  ],
  "count": 5
}
```

#### GET /api/devices/{device_id}/hierarchy
Get device hierarchy (via_device relationships).

**Response:**
```json
{
  "success": true,
  "device_id": "device_abc123",
  "device": {
    "device_id": "device_abc123",
    "name": "Living Room Light",
    "manufacturer": "Philips",
    "model": "Hue Bulb",
    "via_device": "parent_device_id",
    "config_entry_id": "entry_123"
  },
  "parent_device": {
    "device_id": "parent_device_id",
    "name": "Parent Device",
    "manufacturer": "Philips",
    "model": "Bridge"
  },
  "child_devices": []
}
```

### WebSocket

#### WS /api/v1/ws
Real-time data updates.

**Events:**
- `event` - New Home Assistant events
- `game_update` - Sports game status changes
- `alert` - New system alerts
- `metric_update` - Real-time metrics

---

### Device Database Endpoints (NEW - January 2025)

#### GET /api/devices/{device_id}/health
Get health report for a device.

**Response:**
```json
{
  "device_id": "device_abc123",
  "device_name": "Living Room Light",
  "timestamp": "2025-01-20T12:00:00Z",
  "overall_status": "healthy",
  "response_time_ms": 45.2,
  "battery_level": null,
  "last_seen": "2025-01-20T11:59:30Z",
  "power_consumption_w": 8.5,
  "power_anomaly": false,
  "issues": [],
  "maintenance_recommendations": []
}
```

#### GET /api/devices/health-summary
Get overall health summary for all devices.

**Response:**
```json
{
  "total_devices": 45,
  "healthy_devices": 42,
  "warning_devices": 2,
  "error_devices": 1,
  "timestamp": "2025-01-20T12:00:00Z"
}
```

#### GET /api/devices/maintenance-alerts
Get maintenance alerts for devices needing attention.

**Query Parameters:**
- `limit` (default: 50): Maximum number of alerts (1-200)

#### POST /api/devices/{device_id}/classify
Classify a device based on its entities.

#### GET /api/devices/{device_id}/setup-guide
Get setup guide for a device.

#### GET /api/devices/{device_id}/setup-issues
Get detected setup issues for a device.

#### POST /api/devices/{device_id}/setup-complete
Mark device setup as complete.

#### GET /api/devices/{device_id}/power-analysis
Get power consumption analysis for a device.

#### GET /api/devices/{device_id}/efficiency
Get efficiency report for a device.

#### GET /api/devices/power-anomalies
Get devices with power consumption anomalies.

#### POST /api/devices/{device_id}/discover-capabilities
Discover device capabilities from HA API.

#### GET /api/devices/recommendations
Get device recommendations.

**Query Parameters:**
- `device_type` (required): Device type (fridge, light, sensor, etc.)

#### GET /api/devices/compare
Compare devices side-by-side.

**Query Parameters:**
- `device_ids` (required): Comma-separated device IDs (minimum 2)

#### GET /api/devices/similar/{device_id}
Find similar devices.

**See:** [Device Database Enhancements Documentation](../DEVICE_DATABASE_ENHANCEMENTS.md) for detailed endpoint documentation.

---

## Sports API Service

**Base URL:** `http://localhost:8005`  
**Purpose:** Home Assistant Team Tracker integration with InfluxDB persistence  
**Architecture:** Standalone service (Epic 31 pattern - direct InfluxDB writes)  
**Note:** Not in docker-compose.yml by default - run separately if needed

### Overview

The Sports API Service integrates with Home Assistant's [Team Tracker](https://github.com/xyzroe/ha-teamtracker) integration to:
1. Poll Team Tracker sensors from HA REST API
2. Parse sensor states and attributes (PRE, IN, POST, BYE states)
3. Write normalized sports data directly to InfluxDB
4. Supports all leagues supported by Team Tracker (NFL, NHL, MLB, NBA, etc.)

### API Endpoints

#### GET /
Service information.

**Response:**
```json
{
  "service": "sports-api",
  "version": "1.0.0",
  "status": "running",
  "endpoints": ["/health", "/metrics", "/sports-data", "/stats"]
}
```

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "sports-api",
  "version": "1.0.0",
  "ha_connected": true,
  "influxdb_connected": true,
  "last_fetch": "2025-01-08T10:30:00Z"
}
```

#### GET /sports-data
Get current sports data from Team Tracker sensors.

**Response:**
```json
{
  "sensors": [
    {
      "entity_id": "sensor.team_tracker_nfl_patriots",
      "state": "IN",
      "sport": "nfl",
      "league": "NFL",
      "team_abbr": "NE",
      "team_name": "Patriots",
      "team_score": 21,
      "opponent_abbr": "KC",
      "opponent_name": "Chiefs",
      "opponent_score": 17,
      "quarter": 3,
      "clock": "10:32",
      "venue": "Gillette Stadium",
      "last_updated": "2025-01-08T10:30:00Z"
    }
  ],
  "count": 1,
  "last_update": "2025-01-08T10:30:00Z"
}
```

#### GET /stats
Service statistics.

**Response:**
```json
{
  "fetch_count": 150,
  "sensors_processed": 450,
  "influx_write_success": 148,
  "influx_write_failures": 2,
  "last_successful_fetch": "2025-01-08T10:30:00Z",
  "last_influx_write": "2025-01-08T10:30:00Z",
  "poll_interval_seconds": 60,
  "cached_sensors_count": 3
}
```

### Game States

| State | Description |
|-------|-------------|
| `PRE` | Pre-game (scheduled, not started) |
| `IN` | Game in progress |
| `POST` | Game completed |
| `BYE` | Team has bye week |
| `NOT_FOUND` | No game found |

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_PORT` | 8005 | Service port |
| `HA_HTTP_URL` | - | Home Assistant URL |
| `HA_TOKEN` | - | Home Assistant long-lived access token |
| `SPORTS_POLL_INTERVAL` | 60 | Polling interval in seconds |
| `INFLUXDB_URL` | http://influxdb:8086 | InfluxDB URL |
| `INFLUXDB_TOKEN` | - | InfluxDB auth token |
| `INFLUXDB_BUCKET` | home_assistant_events | InfluxDB bucket |

### Historical Data

Historical sports data is stored in InfluxDB and can be queried via data-api:

```bash
# Query via data-api
curl "http://localhost:8006/api/v1/sports/games?sport=nfl&limit=10"
```

---

## AI Automation Services (Epic 39 Modularization)

**Status:** ✅ Modularized (January 2025)

The AI Automation Service has been split into focused microservices for better scalability and maintainability:

- **ai-training-service** (Port 8017) - Model training and synthetic data generation
- **ai-pattern-service** (Port 8016) - Pattern detection and daily analysis
- **ai-query-service** (Port 8018) - Low-latency query processing
- **ai-automation-service-new** (Port 8021) - Suggestion generation and deployment

**Note:** The original monolithic `ai-automation-service` (Port 8018) still exists during migration.

**See:** [Epic 39 Microservices Architecture](../architecture/epic-39-microservices-architecture.md) for complete architecture details.

---

## AI Automation Service (Monolithic - Legacy)

**Base URL:** `http://localhost:8018`  
**Purpose:** AI-powered Home Assistant automation discovery and recommendation system  
**Version:** 2.0.0  
**Status:** ⚠️ Being Refactored (Epic 39)

### Overview

The AI Automation Service provides intelligent automation suggestions through multiple approaches:

- **Pattern Detection:** Analyzes historical usage to detect automation opportunities
- **Device Intelligence:** Discovers device capabilities and suggests unused features  
- **Natural Language:** Create automations from plain English descriptions
- **Conversational Refinement:** Refine suggestions through natural language interaction
- **Ask AI:** Natural language query interface for automation discovery

### Core Features

**Epic AI-1: Pattern Automation**
- Time-of-day patterns (consistent usage times)
- Device co-occurrence (frequently used together)
- Anomaly detection (repeated manual interventions)
- AI-generated automation suggestions

**Epic AI-2: Device Intelligence**
- Universal device capability discovery (6,000+ Zigbee models)
- Utilization analysis (how much of device features you use)
- Feature suggestions (LED notifications, power monitoring, etc.)
- Smart recommendations based on manufacturer specs

**Epic AI-3: N-Level Synergy Detection**
- Multi-hop device relationship discovery
- Device embedding generation for similarity matching
- Advanced synergy pattern detection

### Health & System Endpoints

#### GET /health
Service health check with device intelligence stats.

**Response:**
```json
{
  "status": "healthy",
  "service": "ai-automation-service",
  "version": "2.0.0",
  "timestamp": "2025-10-20T12:00:00Z",
  "device_intelligence": {
    "devices_discovered": 45,
    "devices_processed": 42,
    "devices_skipped": 3,
    "errors": 0
  }
}
```

#### GET /event-rate
Get standardized event rate metrics.

#### GET /stats
Get AI service call pattern statistics and telemetry.

**Response:**
```json
{
  "call_patterns": {
    "direct_calls": 145,
    "orchestrated_calls": 0
  },
  "performance": {
    "avg_direct_latency_ms": 125.45,
    "avg_orch_latency_ms": 0.0
  },
  "model_usage": {
    "total_queries": 145,
    "ner_success": 131,
    "openai_success": 12,
    "pattern_fallback": 2,
    "avg_processing_time": 0.125,
    "total_cost_usd": 0.0048
  }
}
```

**Note:** This endpoint provides real-time telemetry for the AI Automation Service, tracking direct vs orchestrated service calls, latency metrics, and model usage statistics. Accessible in the Health Dashboard Services tab by viewing AI Automation Service details.

### Analysis & Pattern Detection

#### GET /api/analysis/status
Current analysis status and pattern statistics.

**Response:**
```json
{
  "status": "ready",
  "patterns": {
    "total_patterns": 1227,
    "by_type": {
      "co_occurrence": 1217,
      "time_of_day": 10
    },
    "unique_devices": 1227,
    "avg_confidence": 0.987
  },
  "suggestions": {
    "pending_count": 0,
    "recent": []
  }
}
```

#### POST /api/analysis/analyze-and-suggest
Run complete analysis pipeline: Fetch events → Detect patterns → Generate suggestions.

**Request:**
```json
{
  "days": 30,
  "max_suggestions": 10,
  "min_confidence": 0.7,
  "time_of_day_enabled": true,
  "co_occurrence_enabled": true
}
```

**Response:**
```json
{
  "success": true,
  "analysis_id": "analysis-123",
  "patterns_detected": 15,
  "suggestions_generated": 8,
  "duration_seconds": 127.5,
  "openai_usage": {
    "total_tokens": 2847,
    "cost_usd": 0.0042
  }
}
```

#### POST /api/analysis/trigger
Manually trigger daily analysis job (for testing or on-demand execution).

#### GET /api/analysis/schedule
Get information about the analysis schedule.

### Pattern Detection Endpoints

#### POST /api/patterns/detect/time-of-day
Detect time-of-day patterns in device usage.

**Query Parameters:**
- `days` (default: 30): Number of days of history to analyze
- `min_occurrences` (default: 3): Minimum pattern occurrences

#### POST /api/patterns/detect/co-occurrence
Detect co-occurrence patterns between devices.

**Query Parameters:**
- `days` (default: 30): Number of days of history to analyze
- `window_minutes` (default: 5): Time window for co-occurrence

#### GET /api/patterns/list
List detected patterns with filtering.

**Query Parameters:**
- `pattern_type`: Filter by pattern type
- `device_id`: Filter by device ID
- `min_confidence`: Minimum confidence threshold

#### GET /api/patterns/stats
Get pattern detection statistics.

#### POST /api/patterns/incremental-update
Perform incremental pattern update using only recent events.

**Query Parameters:**
- `hours` (default: 1): Number of hours of new events to process (1-24)

**Response:**
```json
{
  "success": true,
  "message": "Incremental update complete: 1234 events processed",
  "data": {
    "patterns_updated": 45,
    "events_processed": 1234,
    "time_range": {
      "start": "2025-01-20T12:00:00Z",
      "end": "2025-01-20T13:00:00Z",
      "hours": 1
    },
    "performance": {
      "duration_seconds": 15.3,
      "events_per_second": 80
    },
    "note": "Incremental updates are enabled. Detectors now support incremental learning."
  }
}
```

**Note:** This endpoint processes only new events since the last update, making it 90% faster than full pattern detection. Ideal for near real-time pattern updates.

### Suggestion Management

#### POST /api/suggestions/generate
Generate automation suggestions from detected patterns using OpenAI.

**Query Parameters:**
- `pattern_type`: Generate suggestions for specific pattern type
- `min_confidence` (default: 0.7): Minimum pattern confidence
- `max_suggestions` (default: 10): Maximum suggestions to generate

#### GET /api/suggestions/list
List suggestions with status filtering.

**Query Parameters:**
- `status_filter`: Filter by status (draft, refining, yaml_generated, deployed, rejected)
- `limit` (default: 50): Maximum suggestions to return

#### GET /api/suggestions/usage-stats
Get OpenAI API usage statistics and cost estimates.

#### POST /api/suggestions/usage-stats/reset
Reset OpenAI API usage statistics (for monthly reset).

### Conversational Automation Flow

#### POST /api/v1/suggestions/generate
Generate description-only automation suggestion (no YAML yet).

**Request:**
```json
{
  "pattern_id": 123,
  "user_preferences": {
    "style": "simple",
    "include_conditions": true
  }
}
```

**Response:**
```json
{
  "suggestion_id": "suggestion-456",
  "status": "draft",
  "description_only": "Turn on kitchen light at 7 AM on weekdays",
  "conversation_history": [],
  "refinement_count": 0
}
```

#### POST /api/v1/suggestions/{suggestion_id}/refine
Refine suggestion based on user input.

**Request:**
```json
{
  "user_input": "Make it 6:30 AM instead and only on weekdays",
  "conversation_context": true
}
```

**Response:**
```json
{
  "suggestion_id": "suggestion-456",
  "status": "refining",
  "description_only": "Turn on kitchen light at 6:30 AM on weekdays",
  "conversation_history": [
    {
      "timestamp": "2025-10-20T12:00:00Z",
      "user_input": "Make it 6:30 AM instead and only on weekdays",
      "ai_response": "Updated timing to 6:30 AM and restricted to weekdays only."
    }
  ],
  "refinement_count": 1
}
```

#### POST /api/v1/suggestions/{suggestion_id}/approve
Approve suggestion and generate Home Assistant YAML.

**Request:**
```json
{
  "force_generate": false
}
```

**Response:**
```json
{
  "suggestion_id": "suggestion-456",
  "status": "yaml_generated",
  "automation_yaml": "alias: 'Kitchen Light Morning'\ntrigger:\n  - platform: time\n    at: '06:30:00'\ncondition:\n  - condition: time\n    weekday:\n      - mon\n      - tue\n      - wed\n      - thu\n      - fri\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.kitchen",
  "ready_to_deploy": true,
  "yaml_generated_at": "2025-10-20T12:05:00Z"
}
```

#### GET /api/v1/suggestions/devices/{device_id}/capabilities
Get device capabilities for suggestion generation.

#### GET /api/v1/suggestions/{suggestion_id}
Get detailed suggestion information.

### Natural Language Generation

#### POST /api/nl/generate
Generate automation from natural language request.

**Request:**
```json
{
  "request_text": "Turn on kitchen light at 7 AM on weekdays",
  "user_id": "default"
}
```

**Response:**
```json
{
  "success": true,
  "suggestion_id": "nl-suggestion-789",
  "automation": {
    "title": "Kitchen Light Morning Routine",
    "yaml": "alias: 'Kitchen Light Morning'...",
    "description": "Turns on kitchen light at 7 AM on weekdays"
  },
  "safety": {
    "score": 85,
    "warnings": [],
    "passed_checks": 6
  }
}
```

#### POST /api/nl/clarify/{suggestion_id}
Clarify automation request with additional context.

**Request:**
```json
{
  "clarification_text": "Only if someone is home"
}
```

#### GET /api/nl/examples
Get example natural language requests for user guidance.

#### GET /api/nl/stats
Get statistics about NL generation usage.

### Ask AI - Natural Language Query Interface

#### POST /api/v1/ask-ai/query
Process natural language query about Home Assistant devices and automations. **Enhanced with full device capability details (October 2025).**

**Request:**
```json
{
  "query_text": "What lights can I control in the kitchen?",
  "user_id": "default"
}
```

**Response:**
```json
{
  "query_id": "query-abc123",
  "status": "processed",
  "extracted_entities": [
    {
      "name": "Kitchen Main Light",
      "type": "device",
      "entity_id": "light.kitchen_main",
      "manufacturer": "Philips",
      "model": "Hue",
      "capabilities": [
        {
          "name": "brightness",
          "type": "numeric",
          "properties": {"min": 0, "max": 100, "unit": "%"},
          "supported": true
        }
      ],
      "health_score": 95
    }
  ],
  "suggestions": [
    {
      "suggestion_id": "suggestion-xyz789",
      "title": "Kitchen Light Control",
      "description": "Fade kitchen lights to 75% brightness when motion detected",
      "confidence": 0.92,
      "capabilities_used": ["brightness"]
    }
  ]
}
```

**Key Features (October 2025):**
- **Enhanced Capability Display:** Capabilities show types, ranges, and values
- **Precise Suggestions:** AI uses actual capability constraints in suggestions
- **Health-Aware:** Prioritizes devices with health_score > 80
- **Dynamic Examples:** Capability-specific examples based on detected devices

#### POST /api/v1/ask-ai/query/{query_id}/refine
Refine query results based on user feedback.

#### GET /api/v1/ask-ai/query/{query_id}/suggestions
Get all suggestions for a specific query.

#### POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/test
Test a suggestion from a query.

#### POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/approve
Approve specific suggestion from a query with optional device selection and custom entity mapping.

**Request Body:**
```json
{
  "selected_entity_ids": ["light.office_lamp", "light.kitchen_ceiling"],
  "custom_entity_mapping": {
    "Office Light": "light.office_desk_lamp",
    "Kitchen Light": "light.kitchen_main"
  }
}
```

**Parameters:**
- `selected_entity_ids` (optional): List of entity IDs to include in the automation. Filters which devices from the suggestion are used.
- `custom_entity_mapping` (optional): Map of friendly_name → entity_id overrides. Allows users to change which entity_id maps to a device name. All custom entity IDs are verified to exist in Home Assistant before applying.

**Response:**
```json
{
  "suggestion_id": "suggestion-xyz789",
  "status": "approved",
  "automation_id": "automation.office_lights_flash_1737123456_a1b2c3d4",
  "automation_yaml": "...",
  "ready_to_deploy": true
}
```

**Features:**
- **Device Selection**: Use `selected_entity_ids` to include/exclude specific devices
- **Custom Mapping**: Use `custom_entity_mapping` to override entity IDs for specific device names
- **Entity Validation**: All custom entity IDs are verified to exist in Home Assistant
- **Mapping Priority**: Custom mappings are applied after device selection filtering
- **Unique ID Generation**: Each approval creates a **new automation** with a unique ID. The automation ID is generated by appending a timestamp and UUID suffix to the base ID (e.g., `office_lights_flash_1737123456_a1b2c3d4`). This ensures that multiple approvals with similar names create separate automations rather than updating the same one.

#### GET /api/v1/ask-ai/entities/search
Search available Home Assistant entities for device mapping.

**Query Parameters:**
- `domain` (optional): Filter by domain (e.g., "light", "switch", "sensor")
- `search_term` (optional): Search term to match against entity_id or friendly_name
- `limit` (optional, default: 100): Maximum number of results to return (1-500)

**Response:**
```json
[
  {
    "entity_id": "light.office_desk_lamp",
    "friendly_name": "Office Desk Lamp",
    "domain": "light",
    "state": "on",
    "capabilities": ["brightness", "color_temp"],
    "device_id": "device-abc123",
    "area_id": "office"
  },
  {
    "entity_id": "light.office_ceiling",
    "friendly_name": "Office Ceiling Light",
    "domain": "light",
    "state": "off",
    "capabilities": ["brightness", "rgb_color"],
    "device_id": "device-xyz789",
    "area_id": "office"
  }
]
```

**Use Case:** 
Used by the frontend Device Mapping Modal to show alternative entities when users want to change which entity_id maps to a friendly_name in an automation suggestion. Entities are enriched with current state and capabilities from Home Assistant.

### System Settings API *(October 2025 update)*

**Base URL:** `/api/v1/settings` (AI Automation Service)

#### GET /api/v1/settings
Retrieve the persisted system configuration (schedule, confidence thresholds, budget limits, AI model toggles).

**Response:**
```json
{
  "scheduleEnabled": true,
  "scheduleTime": "03:00",
  "minConfidence": 70,
  "maxSuggestions": 10,
  "enabledCategories": {
    "energy": true,
    "comfort": true,
    "security": true,
    "convenience": true
  },
  "budgetLimit": 10.0,
  "notificationsEnabled": false,
  "notificationEmail": "",
  "softPromptEnabled": true,
  "softPromptModelDir": "data/ask_ai_soft_prompt",
  "softPromptConfidenceThreshold": 0.85,
  "guardrailEnabled": true,
  "guardrailModelName": "unitary/toxic-bert",
  "guardrailThreshold": 0.6
}
```

#### PUT /api/v1/settings
Update the system configuration. Validation is applied server-side (e.g., soft prompt directories must exist when enabled, thresholds must be between 0 and 1).

**Request:**
```json
{
  "scheduleEnabled": true,
  "scheduleTime": "04:30",
  "minConfidence": 75,
  "maxSuggestions": 8,
  "enabledCategories": {
    "energy": true,
    "comfort": true,
    "security": false,
    "convenience": true
  },
  "budgetLimit": 15,
  "notificationsEnabled": true,
  "notificationEmail": "alerts@example.com",
  "softPromptEnabled": true,
  "softPromptModelDir": "data/ask_ai_soft_prompt",
  "softPromptConfidenceThreshold": 0.9,
  "guardrailEnabled": true,
  "guardrailModelName": "unitary/toxic-bert",
  "guardrailThreshold": 0.55
}
```

**Response:** Updated configuration payload (same schema as GET).

**Validation Errors:** Returns `400 Bad Request` with a list of validation issues (e.g., missing directory, thresholds out of range).

### Preference API *(Epic AI-6, December 2025)*

**Base URL:** `/api/v1/preferences` (AI Automation Service)

User preference settings for customizing suggestion generation and ranking. Preferences control how suggestions are filtered, ranked, and limited in both the daily batch job (3 AM) and Ask AI queries.

**Epic AI-6 Features:**
- **Blueprint Opportunity Discovery:** Proactively finds automation opportunities from device inventory
- **Pattern Validation:** Validates detected patterns against community blueprints for confidence boosting
- **Preference-Based Ranking:** Customizable suggestion ranking with creativity levels and blueprint preferences
- **Unified Preference Application:** Single ranking service applies all preferences in optimal order

#### GET /api/v1/preferences

Get current user preferences for suggestion generation.

**Query Parameters:**
- `user_id` (optional, default: "default"): User ID

**Response:**
```json
{
  "max_suggestions": 10,
  "creativity_level": "balanced",
  "blueprint_preference": "medium"
}
```

**Field Descriptions:**
- `max_suggestions` (int, 5-50): Maximum number of suggestions to show (default: 10)
  - Controls the total number of suggestions returned in both batch job and Ask AI queries
  - Applied after all ranking and filtering is complete
- `creativity_level` (string): Creativity level - "conservative", "balanced", or "creative" (default: "balanced")
  - **Conservative:** Only high-confidence suggestions (confidence ≥ 0.85), no experimental features
  - **Balanced:** Standard confidence threshold (≥ 0.70), includes validated patterns
  - **Creative:** Lower confidence threshold (≥ 0.60), includes experimental and innovative suggestions
- `blueprint_preference` (string): Blueprint preference - "low", "medium", or "high" (default: "medium")
  - **Low:** Blueprint opportunities receive minimal weight boost (5%)
  - **Medium:** Standard blueprint weighting (15% boost for blueprint-validated patterns)
  - **High:** Strong blueprint preference (30% boost for blueprint-validated patterns)

**Example:**
```bash
curl "http://localhost:8024/api/v1/preferences?user_id=default"
```

#### PUT /api/v1/preferences

Update user preferences. Only provided fields are updated.

**Query Parameters:**
- `user_id` (optional, default: "default"): User ID

**Request:**
```json
{
  "max_suggestions": 15,
  "creativity_level": "creative",
  "blueprint_preference": "high"
}
```

**Response:** Updated preferences (same schema as GET)

**Validation:**
- `max_suggestions`: Must be between 5 and 50
- `creativity_level`: Must be "conservative", "balanced", or "creative"
- `blueprint_preference`: Must be "low", "medium", or "high"

**Validation Errors:** Returns `400 Bad Request` with validation error details.

**Example:**
```bash
curl -X PUT "http://localhost:8024/api/v1/preferences?user_id=default" \
  -H "Content-Type: application/json" \
  -d '{"max_suggestions": 15, "creativity_level": "creative", "blueprint_preference": "high"}'
```

**Notes:**
- Preferences are applied to both daily batch job (3 AM) and Ask AI query suggestions
- Changes take effect immediately for new suggestions
- If preferences are not set, default values are used
- Preferences are stored in `suggestion_preferences` table in SQLite
- See [User Guide: Preferences](../current/USER_GUIDE_PREFERENCES.md) for detailed explanations
- See [Epic AI-6 Documentation](../../docs/prd/epic-ai6-blueprint-enhanced-suggestion-intelligence.md) for architecture details

### Entity Alias Management (October 2025)

User-defined aliases allow personalized nicknames for devices (e.g., "sleepy light" → light.bedroom_1).

#### POST /api/v1/ask-ai/aliases
Create a new alias for an entity.

**Request:**
```json
{
  "entity_id": "light.bedroom_1",
  "alias": "sleepy light",
  "user_id": "user123"
}
```

**Response:**
```json
{
  "entity_id": "light.bedroom_1",
  "alias": "sleepy light",
  "user_id": "user123",
  "created_at": "2025-10-29T12:00:00Z",
  "updated_at": "2025-10-29T12:00:00Z"
}
```

#### DELETE /api/v1/ask-ai/aliases/{alias}
Delete an alias.

**Query Parameters:**
- `user_id` (optional, default: "anonymous"): User ID

**Example:**
```bash
DELETE /api/v1/ask-ai/aliases/sleepy%20light?user_id=user123
```

#### GET /api/v1/ask-ai/aliases
List all aliases for a user, grouped by entity_id.

**Query Parameters:**
- `user_id` (optional, default: "anonymous"): User ID

**Response:**
```json
{
  "light.bedroom_1": ["sleepy light", "bedroom main"],
  "light.living_room_1": ["living room lamp"]
```

---

### Home Type Categorization (November 2025)

The Home Type Categorization System uses ML-based classification (RandomForest) to categorize homes and enhance automation suggestions based on home characteristics.

#### GET /api/home-type/profile
Get current home type profile with comprehensive home characteristics.

**Query Parameters:**
- `home_id` (optional, default: "default"): Home identifier

**Response:**
```json
{
  "status": "success",
  "home_id": "default",
  "profile": {
    "device_composition": {
      "total_devices": 45,
      "by_domain": {
        "light": 12,
        "sensor": 18,
        "switch": 8,
        "climate": 4,
        "cover": 3
      }
    },
    "event_patterns": {
      "events_per_day": 1250,
      "peak_hours": [6, 7, 18, 19, 20],
      "most_active_domain": "light"
    },
    "spatial_layout": {
      "areas": 8,
      "rooms": 6,
      "devices_per_area": 5.6
    },
    "behavior_patterns": {
      "automation_count": 23,
      "manual_interventions": 45
    }
  }
}
```

#### GET /api/home-type/classify
Classify home type using pre-trained RandomForest model.

**Query Parameters:**
- `home_id` (optional, default: "default"): Home identifier

**Response:**
```json
{
  "status": "success",
  "home_id": "default",
  "classification": {
    "home_type": "smart_home_enthusiast",
    "confidence": 0.87,
    "method": "ml_model",
    "model_version": "1.0",
    "categories": {
      "security": 0.15,
      "climate": 0.20,
      "lighting": 0.35,
      "appliance": 0.15,
      "monitoring": 0.10,
      "general": 0.05
    }
  }
}
```

**Home Types:**
- `smart_home_enthusiast` - High device count, extensive automation
- `basic_automation` - Standard automation with common devices
- `security_focused` - Security devices and monitoring emphasis
- `energy_efficient` - Climate and energy monitoring focus
- `minimal` - Few devices, basic functionality

#### GET /api/home-type/model-info
Get model metadata and training information.

**Response:**
```json
{
  "status": "success",
  "model_info": {
    "is_loaded": true,
    "model_version": "1.0",
    "training_date": "2025-11-20",
    "class_names": [
      "smart_home_enthusiast",
      "basic_automation",
      "security_focused",
      "energy_efficient",
      "minimal"
    ],
    "feature_names": [
      "device_count",
      "automation_count",
      "events_per_day",
      "area_count",
      "climate_device_ratio",
      "security_device_ratio",
      ...
    ],
    "algorithm": "RandomForestClassifier",
    "training_samples": 120
  }
}
```

**Integration Notes:**
- Home type classification is automatically used in suggestion ranking (10% weight boost)
- Event categorization maps events to categories based on home type preferences
- Classification results are cached for 24 hours
- Graceful fallback to default home type if classification fails
}
```

### Deployment & Management

#### POST /api/deploy/{suggestion_id}
Deploy an approved suggestion to Home Assistant.

**Request:**
```json
{
  "force_deploy": false
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "automation_id": "automation-123",
    "safety_score": 85,
    "safety_warnings": [],
    "deployed_at": "2025-10-20T12:10:00Z"
  }
}
```

#### POST /api/deploy/batch
Deploy multiple approved suggestions at once.

#### GET /api/deploy/automations
List all automations currently in Home Assistant.

#### GET /api/deploy/automations/{automation_id}
Get status of a specific automation in Home Assistant.

#### POST /api/deploy/automations/{automation_id}/enable
Enable/turn on an automation in Home Assistant.

#### POST /api/deploy/automations/{automation_id}/disable
Disable/turn off an automation in Home Assistant.

#### POST /api/deploy/automations/{automation_id}/trigger
Manually trigger an automation in Home Assistant.

#### POST /api/deploy/{automation_id}/rollback
Rollback automation to previous version.

#### GET /api/deploy/{automation_id}/versions
Get version history for automation (last 3 versions).

#### GET /api/deploy/test-connection
Test connection to Home Assistant.

### Suggestion Management Operations

#### DELETE /api/suggestions/{suggestion_id}
Delete a suggestion.

#### POST /api/suggestions/batch/approve
Approve multiple suggestions at once.

#### POST /api/suggestions/batch/reject
Reject multiple suggestions at once.

### Synergy Detection (Epic AI-3, AI-4)

#### GET /api/synergies
List detected device synergies with priority-based ordering.

**Query Parameters:**
- `synergy_type`: Filter by synergy type (`device_pair`, `device_chain`, `weather_context`, `energy_context`, `event_context`)
- `min_confidence` (default: 0.7): Minimum confidence score
- `validated_by_patterns` (boolean): Filter by pattern validation status
- `synergy_depth` (int, optional): Filter by chain depth (2=pair, 3=3-chain, 4=4-chain) - **NEW (Epic AI-4)**
- `min_priority` (float): Minimum priority score (0.0-1.0)
- `order_by_priority` (boolean, default: true): Order results by priority score
- `limit` (int): Maximum number of results to return

**Chain Depth Filtering (Epic AI-4):**
- `synergy_depth=2`: Device pairs (A → B)
- `synergy_depth=3`: 3-device chains (A → B → C)
- `synergy_depth=4`: 4-device chains (A → B → C → D)
- Omit parameter to get all depths

**Priority Score Calculation:**
- 40% impact_score
- 25% confidence
- 25% pattern_support_score
- 10% validation bonus (if validated_by_patterns)
- Complexity adjustment: low=+0.10, medium=0, high=-0.10

**Synergy Types:**
- `device_pair`: Cross-device automation opportunities (2-device pairs)
- `device_chain`: Multi-device automation chains (3-level or 4-level chains) - **NEW (Epic AI-4)**
- `weather_context`: Weather-based automation suggestions
- `energy_context`: Energy cost optimization opportunities (NEW)
- `event_context`: Entertainment/event-based automations (NEW)

**Response Fields (Epic AI-4):**
- `synergy_depth`: Number of devices in chain (2, 3, or 4)
- `chain_devices`: JSON array of entity IDs in the automation chain
- `chain_path`: Human-readable chain path (e.g., "entity1 → entity2 → entity3 → entity4")

#### GET /api/synergies/stats
Get comprehensive synergy detection statistics including counts by type, complexity, depth, and detailed breakdowns. Returns ALL data from the database (data cleanup occurs on insert, not output).

**Response:**
```json
{
  "success": true,
  "data": {
    "total_synergies": 48934,
    "by_type": {
      "device_pair": 48713,
      "device_chain": 200,
      "scene_based": 16,
      "weather_context": 5
    },
    "by_complexity": {
      "low": 48734,
      "medium": 200
    },
    "by_depth": {
      "2": 48718,
      "3": 200,
      "10": 16
    },
    "by_type_and_depth": {
      "device_pair": {
        "2": {
          "count": 48713,
          "avg_impact": 0.715,
          "avg_confidence": 0.908,
          "min_impact": 0.5,
          "max_impact": 1.0
        }
      },
      "device_chain": {
        "3": {
          "count": 200,
          "avg_impact": 0.85,
          "avg_confidence": 0.9,
          "min_impact": 0.85,
          "max_impact": 0.85
        }
      }
    },
    "by_type_and_complexity": {
      "device_pair": {
        "low": {
          "count": 48713,
          "avg_impact": 0.715,
          "avg_confidence": 0.908
        }
      },
      "device_chain": {
        "medium": {
          "count": 200,
          "avg_impact": 0.85,
          "avg_confidence": 0.9
        }
      }
    },
    "avg_impact_score": 0.716,
    "avg_confidence": 0.908,
    "min_impact_score": 0.5,
    "max_impact_score": 1.0,
    "unique_areas": 0
  },
  "message": "Synergy statistics retrieved successfully"
}
```

**Response Fields:**
- `total_synergies`: Total count of all synergies (includes all data, no filtering)
- `by_type`: Count of synergies by type (device_pair, device_chain, scene_based, weather_context, etc.)
- `by_complexity`: Count of synergies by complexity level (low, medium, high)
- `by_depth`: Count of synergies by depth/level (2=pair, 3=chain, etc.)
- `by_type_and_depth`: Detailed breakdown by type and depth with counts, averages, min/max impact scores
- `by_type_and_complexity`: Detailed breakdown by type and complexity with counts and averages
- `avg_impact_score`: Average impact score across all synergies
- `avg_confidence`: Average confidence score across all synergies
- `min_impact_score`: Minimum impact score in dataset
- `max_impact_score`: Maximum impact score in dataset
- `unique_areas`: Count of unique areas

**Notes:**
- This endpoint (proxied as `/api/synergies/stats`) maps to `/api/v1/synergies/statistics` in the pattern service
- Must be defined before the parameterized `/{synergy_id}` route to ensure correct FastAPI route matching
- Returns ALL data from database - data filtering/cleanup occurs on insert, not output
- Uses SQL aggregate queries for efficient calculation across large datasets

#### GET /api/synergies/{synergy_id}
Get detailed synergy information including metadata, devices involved, and opportunity details.

### Data Access Endpoints

#### GET /api/data/health
Check Data API health status.

#### GET /api/data/events
Get events from Data API with filtering.

**Query Parameters:**
- `days` (default: 7): Number of days of history
- `entity_id`: Filter by entity ID

#### GET /api/data/devices
Get devices from Data API.

#### GET /api/data/entities
Get entities from Data API.

### Performance Metrics

- **Small datasets** (< 50k events): 1-2 minutes
- **Large datasets** (50k+ events): 2-3 minutes
- **API response times:** 50-5000ms depending on operation
- **OpenAI cost:** ~$0.50/year for daily analysis
- **Memory usage:** 200-400MB peak
- **Daily job duration:** 2-4 minutes typical

---

## HA AI Agent Service

**Base URL:** `http://ha-ai-agent-service:8030`  
**Status:** ✅ Complete (Epic AI-19)  
**Purpose:** Tier 1 Context Injection for Home Assistant AI Agent

### Overview

The HA AI Agent Service provides REST API endpoints for retrieving context and system prompts for a conversational Home Assistant AI agent. This service implements Tier 1 essential context that is always included in every conversation to enable efficient automation generation without excessive tool calls.

### Endpoints

#### GET /health

Check service health and readiness.

**Response:**
```json
{
  "status": "healthy",
  "service": "ha-ai-agent-service",
  "version": "1.0.0"
}
```

**Status Codes:**
- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service is not ready

---

#### GET /api/v1/context

Retrieve Tier 1 context formatted for OpenAI agent.

**Response:**
```json
{
  "context": "HOME ASSISTANT CONTEXT:\nENTITY INVENTORY:\n...",
  "token_count": 1450
}
```

**Response Fields:**
- `context` (string) - Formatted context string with all Tier 1 components
- `token_count` (integer) - Rough token estimate (word count)

**Context Sections:**
1. Entity Inventory Summary - Aggregated entity counts by domain and area (5 min cache TTL)
2. Areas/Rooms List - All areas from Home Assistant (10 min cache TTL)
3. Available Services Summary - Services by domain with common parameters (10 min cache TTL)
4. Device Capability Patterns - Capability examples from device intelligence (15 min cache TTL)
5. Helpers & Scenes Summary - Available helpers and scenes for reusable components (10 min cache TTL)

**Status Codes:**
- `200 OK` - Context retrieved successfully
- `503 Service Unavailable` - Service not ready
- `500 Internal Server Error` - Failed to build context

**Example:**
```bash
curl http://ha-ai-agent-service:8030/api/v1/context
```

---

#### GET /api/v1/system-prompt

Retrieve the base system prompt defining the agent's role and behavior.

**Response:**
```json
{
  "system_prompt": "You are a knowledgeable and helpful Home Assistant automation assistant...",
  "token_count": 850
}
```

**Response Fields:**
- `system_prompt` (string) - Base system prompt without context
- `token_count` (integer) - Rough token estimate

**Status Codes:**
- `200 OK` - System prompt retrieved successfully
- `503 Service Unavailable` - Service not ready

**Example:**
```bash
curl http://ha-ai-agent-service:8030/api/v1/system-prompt
```

---

#### GET /api/v1/complete-prompt

Retrieve the complete system prompt with Tier 1 context injected, ready for OpenAI API calls.

**Response:**
```json
{
  "system_prompt": "You are a knowledgeable and helpful Home Assistant automation assistant...\n\n---\n\nHOME ASSISTANT CONTEXT:\n...",
  "token_count": 2300
}
```

**Response Fields:**
- `system_prompt` (string) - Complete system prompt with context injected
- `token_count` (integer) - Rough token estimate

**Status Codes:**
- `200 OK` - Complete prompt retrieved successfully
- `503 Service Unavailable` - Service not ready
- `500 Internal Server Error` - Failed to build context

**Example:**
```bash
curl http://ha-ai-agent-service:8030/api/v1/complete-prompt
```

### Performance Requirements

- **Context Building (with cache)**: < 100ms ✅
- **Context Building (first call)**: < 500ms ✅
- **System Prompt Retrieval**: < 10ms ✅
- **Complete Prompt Building**: < 100ms ✅

### Caching

Context components are cached in SQLite database (`ha_ai_agent.db`) with TTL-based expiration:
- Entity summaries: 5 minutes
- Areas list: 10 minutes
- Services summary: 10 minutes
- Capability patterns: 15 minutes
- Helpers & scenes summary: 10 minutes

### Dependencies

The service depends on:
- **Home Assistant REST API** - For areas, services, and entity states
- **Data API Service** (Port 8006) - For entity queries
- **Device Intelligence Service** (Port 8028) - For device capability patterns

If dependencies are unavailable, the service will return context with unavailable sections marked.

### Example Usage

**Python Client:**
```python
import httpx

async with httpx.AsyncClient() as client:
    # Get complete prompt for OpenAI
    response = await client.get(
        "http://ha-ai-agent-service:8030/api/v1/complete-prompt"
    )
    data = response.json()
    complete_prompt = data["system_prompt"]
    # Use complete_prompt as system message in OpenAI API call
```

**cURL:**
```bash
# Get context only
curl http://ha-ai-agent-service:8030/api/v1/context

# Get system prompt only
curl http://ha-ai-agent-service:8030/api/v1/system-prompt

# Get complete prompt (recommended for OpenAI)
curl http://ha-ai-agent-service:8030/api/v1/complete-prompt
```

### Related Documentation

- Service README: `services/ha-ai-agent-service/README.md`
- API Documentation: `services/ha-ai-agent-service/docs/API_DOCUMENTATION.md`
- System Prompt: `services/ha-ai-agent-service/docs/SYSTEM_PROMPT.md`

---

## Device Intelligence Service

**Base URL:** `http://localhost:8028`  
**Purpose:** Device capability discovery, health monitoring, and device mapping library (Epic AI-24)

### Device Mapping Library API (Epic AI-24)

The Device Mapping Library provides a plugin-based architecture for device-specific intelligence.

#### GET /api/device-mappings/status

Get device mapping registry status.

**Response:**
```json
{
  "status": "operational",
  "handler_count": 2,
  "handlers": ["hue", "wled"],
  "cache_size": 15
}
```

#### POST /api/device-mappings/reload

Reload device mapping registry (clears cache and re-discovers handlers).

#### POST /api/device-mappings/{device_id}/type

Get device type for a specific device.

**Request Body:**
```json
{
  "device_id": "hue_room_office",
  "manufacturer": "Signify",
  "model": "Room",
  "name": "Office"
}
```

**Response:**
```json
{
  "device_id": "hue_room_office",
  "type": "group",
  "handler": "HueHandler",
  "handler_name": "hue"
}
```

#### POST /api/device-mappings/{device_id}/relationships

Get device relationships (e.g., segments to master, groups to members).

#### POST /api/device-mappings/{device_id}/context

Get enriched context for a device.

**See:** `services/device-intelligence-service/README.md` for complete API documentation
- Epic AI-19: `docs/prd/epic-ai19-ha-ai-agent-tier1-context-injection.md`

---

## Blueprint Index Service

**Base URL:** `http://localhost:8031`  
**Purpose:** Index and search community Home Assistant blueprints  
**Status:** ✅ Production (January 2026)

### Overview

The Blueprint Index Service crawls GitHub and Discourse to build a searchable index of 5,000+ community blueprints. It enables:
- Blueprint opportunity discovery based on user device inventory
- Pattern matching to community-validated blueprints
- Blueprint deployment via Home Assistant API

### Health Check

#### GET /health

Service health check.

**Response:**
```json
{
  "status": "healthy",
  "service": "blueprint-index",
  "indexed_blueprints": 5234,
  "last_update": "2026-01-07T03:00:00Z"
}
```

### Search Endpoints

#### GET /api/blueprints/search

Search blueprints by criteria.

**Query Parameters:**
- `query` (optional): Full-text search query
- `domains` (optional): Comma-separated required domains (e.g., "binary_sensor,light")
- `device_classes` (optional): Comma-separated required device classes (e.g., "motion")
- `use_case` (optional): Use case filter (energy, comfort, security, convenience)
- `min_quality_score` (optional, default: 0): Minimum quality score (0.0-1.0)
- `limit` (optional, default: 20): Maximum results

**Response:**
```json
{
  "blueprints": [
    {
      "id": "homeassistant/motion_light",
      "name": "Motion-activated Light",
      "description": "Turn on a light when motion is detected",
      "source_url": "https://github.com/home-assistant/core/tree/dev/homeassistant/components/automation/blueprints",
      "required_domains": ["binary_sensor", "light"],
      "required_device_classes": ["motion"],
      "use_case": "convenience",
      "quality_score": 0.95,
      "community_rating": 0.92,
      "stars": 245,
      "downloads": 12000
    }
  ],
  "count": 1,
  "total_available": 5234
}
```

#### GET /api/blueprints/{blueprint_id}

Get detailed blueprint information.

**Response:**
```json
{
  "id": "homeassistant/motion_light",
  "name": "Motion-activated Light",
  "description": "Turn on a light when motion is detected and turn it off after a delay",
  "source_url": "https://github.com/home-assistant/core/...",
  "required_domains": ["binary_sensor", "light"],
  "required_device_classes": ["motion"],
  "inputs": {
    "motion_entity": {
      "name": "Motion Sensor",
      "selector": {"entity": {"domain": "binary_sensor", "device_class": "motion"}}
    },
    "light_entity": {
      "name": "Light",
      "selector": {"entity": {"domain": "light"}}
    },
    "no_motion_wait": {
      "name": "Wait time",
      "default": 120,
      "selector": {"number": {"min": 0, "max": 3600, "unit_of_measurement": "seconds"}}
    }
  },
  "yaml_content": "blueprint:\n  name: Motion-activated Light\n  ...",
  "use_case": "convenience",
  "quality_score": 0.95,
  "community_rating": 0.92,
  "stars": 245,
  "downloads": 12000,
  "author": "home-assistant",
  "ha_min_version": "2021.3.0"
}
```

#### GET /api/blueprints/by-pattern

Find blueprints matching a trigger-action pattern.

**Query Parameters:**
- `trigger_domain` (required): Trigger domain (e.g., "binary_sensor")
- `action_domain` (required): Action domain (e.g., "light")
- `trigger_device_class` (optional): Trigger device class (e.g., "motion")
- `limit` (optional, default: 10): Maximum results

**Response:**
```json
{
  "blueprints": [...],
  "count": 5
}
```

### Indexing Endpoints

#### POST /api/blueprints/index/refresh

Trigger re-indexing of blueprints.

**Request:**
```json
{
  "job_type": "full"
}
```

**Response:**
```json
{
  "status": "started",
  "job_id": "index-20260107-1200",
  "estimated_duration_minutes": 30
}
```

#### GET /api/blueprints/status

Get indexing status.

**Response:**
```json
{
  "total_blueprints": 5234,
  "by_source": {
    "github": 4500,
    "discourse": 734
  },
  "last_update": "2026-01-07T03:00:00Z",
  "next_scheduled_update": "2026-01-08T03:00:00Z"
}
```

---

## AI Pattern Service

**Base URL:** `http://localhost:8020` (internal) / `http://localhost:8034` (external)  
**Purpose:** Pattern detection, synergy analysis, and blueprint opportunity discovery  
**Status:** ✅ Production (January 2026 - v1.3.0)

### Blueprint Opportunity Endpoints (NEW January 2026)

The Blueprint Opportunity Engine proactively discovers blueprint opportunities based on user device inventory.

#### GET /api/v1/blueprint-opportunities

List blueprint opportunities matching user devices.

**Query Parameters:**
- `min_fit_score` (optional, default: 0.5): Minimum fit score (0.0-1.0)
- `domain` (optional): Filter by blueprint domain
- `limit` (optional, default: 20): Maximum results

**Response:**
```json
{
  "success": true,
  "data": {
    "opportunities": [
      {
        "blueprint_id": "homeassistant/motion_light",
        "blueprint_name": "Motion-activated Light",
        "description": "Turn on a light when motion is detected",
        "fit_score": 0.92,
        "required_domains": ["binary_sensor", "light"],
        "required_device_classes": ["motion"],
        "matched_devices": [
          {
            "input_name": "motion_sensor",
            "required_domain": "binary_sensor",
            "required_device_class": "motion",
            "suggested_entity": "binary_sensor.kitchen_motion",
            "confidence": 0.95,
            "alternatives": ["binary_sensor.hallway_motion"]
          },
          {
            "input_name": "light_entity",
            "required_domain": "light",
            "suggested_entity": "light.kitchen_main",
            "confidence": 0.90,
            "alternatives": ["light.kitchen_ceiling"]
          }
        ],
        "community_stats": {
          "stars": 245,
          "downloads": 12000,
          "rating": 0.94
        }
      }
    ],
    "count": 15
  }
}
```

#### POST /api/v1/blueprint-opportunities/discover

Discover blueprint opportunities for a custom device inventory.

**Request:**
```json
{
  "devices": [
    {
      "entity_id": "binary_sensor.kitchen_motion",
      "domain": "binary_sensor",
      "device_class": "motion",
      "area_id": "kitchen"
    },
    {
      "entity_id": "light.kitchen_main",
      "domain": "light",
      "area_id": "kitchen"
    }
  ]
}
```

**Response:** Same as GET endpoint

#### GET /api/v1/blueprint-opportunities/{blueprint_id}

Get detailed blueprint opportunity by ID.

**Response:**
```json
{
  "success": true,
  "data": {
    "blueprint_id": "homeassistant/motion_light",
    "blueprint_name": "Motion-activated Light",
    "fit_score": 0.92,
    "matched_devices": [...],
    "blueprint_details": {
      "inputs": {...},
      "yaml_content": "...",
      "author": "home-assistant",
      "ha_min_version": "2021.3.0"
    }
  }
}
```

#### POST /api/v1/blueprint-opportunities/{blueprint_id}/preview

Preview a blueprint deployment with auto-filled inputs.

**Response:**
```json
{
  "success": true,
  "data": {
    "blueprint_id": "homeassistant/motion_light",
    "preview_yaml": "alias: Kitchen Motion Light\nuse_blueprint:\n  path: homeassistant/motion_light\n  input:\n    motion_entity: binary_sensor.kitchen_motion\n    light_entity: light.kitchen_main\n    no_motion_wait: 120",
    "autofilled_inputs": {
      "motion_entity": "binary_sensor.kitchen_motion",
      "light_entity": "light.kitchen_main",
      "no_motion_wait": 120
    },
    "missing_inputs": [],
    "warnings": []
  }
}
```

#### POST /api/v1/blueprint-opportunities/{blueprint_id}/deploy

Deploy a blueprint as a Home Assistant automation.

**Request:**
```json
{
  "inputs": {
    "motion_entity": "binary_sensor.kitchen_motion",
    "light_entity": "light.kitchen_main",
    "no_motion_wait": 180
  },
  "automation_alias": "Kitchen Motion Light"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "automation_id": "automation.kitchen_motion_light",
    "deployed_at": "2026-01-07T12:00:00Z",
    "blueprint_id": "homeassistant/motion_light"
  }
}
```

### Enhanced Synergy Endpoints

Synergies are now enriched with blueprint metadata.

#### GET /api/v1/synergies/list

List synergies with blueprint enrichment.

**Response:**
```json
{
  "success": true,
  "data": {
    "synergies": [
      {
        "id": 1,
        "synergy_id": "device_pair_abc123",
        "synergy_type": "device_pair",
        "devices": ["binary_sensor.kitchen_motion", "light.kitchen_main"],
        "impact_score": 0.85,
        "confidence": 0.92,
        "blueprint_id": "homeassistant/motion_light",
        "blueprint_name": "Motion-activated Light",
        "blueprint_fit_score": 0.92,
        "has_blueprint_match": true,
        "explanation": {...},
        "context_breakdown": {...}
      }
    ],
    "count": 48
  }
}
```

**Blueprint Fields:**
- `blueprint_id`: Matched blueprint ID (null if no match)
- `blueprint_name`: Matched blueprint name
- `blueprint_fit_score`: Fit score (0.0-1.0)
- `has_blueprint_match`: Boolean indicating if a blueprint matches

**See:** `services/ai-pattern-service/README.md` for complete API documentation

---

## Statistics API

**Base URL:** `http://localhost:8004`

### Core Endpoints

#### GET /api/v1/stats
Comprehensive system statistics.

**Query Parameters:**
- `period` (optional): `1h`, `24h`, `7d`, `30d` (default: `1h`)
- `service` (optional): Filter by service name

#### GET /api/v1/stats/services
Statistics for all services.

#### GET /api/v1/stats/metrics
Query specific metrics with filtering.

**Query Parameters:**
- `metric_name` (optional): Specific metric
- `service` (optional): Filter by service
- `limit` (optional): Max results (default: 100, max: 200)

#### GET /api/v1/stats/performance
Performance analytics with optimization recommendations.

#### GET /api/v1/stats/alerts
Active system alerts sorted by severity.

### Real-Time Metrics (Dashboard Optimized)

#### GET /api/v1/real-time-metrics
**NEW in Oct 2025** - Consolidated metrics endpoint optimized for dashboards.

**Key Benefits:**
- Single API call (replaces 6-10 individual calls)
- 5-10ms response time
- Consistent timestamps
- Graceful degradation

**Response:**
```json
{
  "events_per_hour": 45000,
  "api_calls_active": 5,
  "data_sources_active": ["influxdb", "websocket", "home-assistant"],
  "api_metrics": [
    {
      "service": "websocket-ingestion",
      "status": "active",
      "events_per_hour": 180.0,
      "uptime_seconds": 1196.3
    }
  ],
  "health_summary": {
    "healthy": 2,
    "unhealthy": 13,
    "total": 15,
    "health_percentage": 13.3
  },
  "timestamp": "2025-10-20T12:00:00Z"
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Description | Usage |
|------|-------------|-------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Endpoint not found |
| 408 | Request Timeout | Operation timed out |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 502 | Bad Gateway | Proxy error (nginx) |
| 503 | Service Unavailable | Service temporarily unavailable |

### Error Response Format

```json
{
  "success": false,
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "field": "parameter_name",
    "issue": "Specific issue description"
  },
  "request_id": "req-123"
}
```

### Rate Limiting

API endpoints are rate-limited to prevent abuse using a token bucket algorithm:

**Rate Limits by Client Type:**
- **External IPs**: 600 requests per minute, 10,000 per hour
- **Internal Docker Network** (172.x.x.x, 192.168.x.x, 10.x.x.x): 2,000 requests per minute
- **Health Endpoints** (`/health`, `/api/health`): **Exempt** from rate limiting (always allowed)

**Endpoint-Specific Limits:**
- **General endpoints**: Subject to IP-based limits above
- **AI refinement**: 1 per 5 seconds, max 10 per suggestion
- **Analysis endpoints**: Maximum 1 analysis per 5 minutes

**Rate Limit Headers:**
```
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 550
X-RateLimit-Reset: 1640995200
Retry-After: 60
```

**Rate Limit Response (429 Too Many Requests):**
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Limit: 600/min, 10000/hour"
}
```

---

## Integration Examples

### Home Assistant Automation

```yaml
automation:
  - alias: "49ers Score Alert"
    trigger:
      platform: webhook
      webhook_id: sports_score_change
      local_only: true
    condition:
      - condition: template
        value_template: "{{ trigger.json.team == 'sf' }}"
      - condition: template
        value_template: "{{ trigger.json.score_diff.home > 0 }}"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          effect: flash
          rgb_color: [170, 0, 0]
          flash: long
```

### External Analytics Dashboard

```python
import requests

API_BASE = "http://localhost:8006/api/v1"

# Get season statistics
response = requests.get(
    f"{API_BASE}/sports/teams/sf/stats",
    params={"season": 2025}
)
stats = response.json()
```

### Voice Assistant Integration

```javascript
// Alexa skill backend
const response = await axios.get(
    `http://localhost:8006/api/v1/ha/game-status/${team}`,
    { timeout: 500 }
);
```

### Dashboard Real-Time Updates

```typescript
// Single API call for all metrics
async function updateDashboard() {
  const response = await fetch('http://localhost:8004/api/v1/real-time-metrics');
  const metrics = await response.json();
  
  updateEventRate(metrics.events_per_hour);
  updateServiceHealth(metrics.health_summary);
  updateServiceList(metrics.api_metrics);
}

// Refresh every 5 seconds
setInterval(updateDashboard, 5000);
```

---

## Endpoint Summary

| API | Category | Count |
|-----|----------|-------|
| **Admin API** | Health & Monitoring | 4 |
| | Docker Management | 5 |
| | Configuration | 3 |
| | Statistics | 8 |
| | WebSocket | 1 |
| **Data API** | Events | 8 |
| | Devices & Entities | 5 |
| | Analytics | 4 |
| | Alerts | 6 |
| | Integrations | 2 |
| | WebSocket | 1 |
| **Sports Data** | Real-Time | 2 |
| | Historical | 3 |
| | HA Automation | 2 |
| | Webhooks | 3 |
| **AI Automation** | Analysis | 3 |
| | Conversational Flow | 4 |
| **Grand Total** | | **~65 endpoints** |

---

## Related Documentation

- **[Architecture Overview](../architecture/index.md)** - System architecture
- **[Source Tree](../architecture/source-tree.md)** - Service structure
- **[Deployment Guide](../DEPLOYMENT_GUIDE.md)** - Deployment instructions
- **[Epic 13 Story](../stories/epic-13-admin-api-service-separation.md)** - API separation details

---

**Document Version:** 4.9  
**Last Updated:** February 2026 (Docker: activity-recognition, energy-forecasting)  
**Status:** ✅ Production Ready  
**Maintained By:** HA Ingestor Team

