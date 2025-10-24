# Services Overview - Home Assistant Ingestor

## 📋 Complete Service Reference

This document provides a comprehensive overview of all services in the Home Assistant Ingestor system with complete data flows and integrations.

**Reference:** See [COMPLETE_DATA_FLOW_CALL_TREE.md](../implementation/analysis/COMPLETE_DATA_FLOW_CALL_TREE.md) for detailed call trees.

---

## 🎯 Core Data Processing Services

### 1. WebSocket Ingestion Service
**Port:** 8001 (external)  
**Technology:** Python 3.11, aiohttp  
**Purpose:** Home Assistant WebSocket client and primary data ingestion point

**Data Flow:**
```
Home Assistant (WebSocket)
    ↓ state_changed events
WebSocket Ingestion Service
    ├─ EventProcessor: Validate and extract data
    ├─ WeatherEnrichmentService: Add weather context
    ├─ DiscoveryService: Device/entity/area enrichment (Epic 23)
    ├─ BatchProcessor: Batch events (100/batch, 5s timeout)
    └─ HTTP POST → Enrichment Pipeline (Port 8002)
```

**Key Features:**
- Real-time WebSocket connection to Home Assistant
- Automatic authentication and reconnection (exponential backoff)
- Event subscription management (state_changed events)
- Device and entity discovery from HA registry
- High-volume processing (1000 events/sec, 10 workers)
- Weather enrichment (15-minute cache)
- Context tracking: context_id, parent_id, user_id (Epic 23.1)
- Spatial enrichment: device_id, area_id (Epic 23.2)
- Duration tracking: duration_in_state (Epic 23.3)
- Device metadata: manufacturer, model (Epic 23.5)
- Batch processing for efficiency

**Endpoints:**
- `GET /health` - Service health status
- `GET /ws` - WebSocket endpoint for real-time streaming

**Health Check:** `http://localhost:8001/health`

**README:** [services/websocket-ingestion/README.md](../services/websocket-ingestion/README.md)

---

### 2. Enrichment Pipeline Service
**Port:** 8002 (external)  
**Technology:** Python 3.11, FastAPI, InfluxDB Client  
**Purpose:** Data validation, normalization, and InfluxDB storage

**Data Flow:**
```
WebSocket Ingestion (HTTP POST /events)
    ↓ enriched event data
Enrichment Pipeline Service
    ├─ DataValidationEngine: Validate event structure
    ├─ DataNormalizer: Convert to standard format
    ├─ Generate InfluxDB Line Protocol
    └─ InfluxDB Write → home_assistant_events bucket
```

**Key Features:**
- Event validation and normalization
- InfluxDB Line Protocol conversion
- Quality metrics and alerting
- Non-blocking async writes
- Batch write optimization

**InfluxDB Schema:**
```
Measurement: state_changed
Tags: entity_id, domain, event_type, device_id, area_id, context_id
Fields: state, attributes, duration_in_state, weather_*, device_*
```

**Endpoints:**
- `POST /events` - Receive events from WebSocket service
- `POST /process-event` - Process single event
- `POST /process-events` - Batch event processing
- `GET /health` - Service health status
- `GET /status` - Service statistics

**Health Check:** `http://localhost:8002/health`

**README:** [services/enrichment-pipeline/README.md](../services/enrichment-pipeline/README.md)

---

### 3. Data Retention Service (Enhanced)
**Port:** 8080 (external)  
**Technology:** Python 3.11, FastAPI  
**Purpose:** Advanced data lifecycle management

**Key Features:**
- **Tiered Storage:** Hot/Warm/Cold retention with automatic downsampling
- **Materialized Views:** Pre-computed aggregations for fast queries
- **S3 Archival:** Automatic archival to Amazon S3/Glacier
- **Storage Analytics:** Comprehensive monitoring and optimization
- **Backup & Restore:** Automated backup with retention policies
- **Data Cleanup:** Intelligent data lifecycle management

**New Modules (October 2025):**
- `materialized_views.py` - Fast query performance
- `tiered_retention.py` - Hot/warm/cold storage management
- `s3_archival.py` - S3/Glacier integration
- `storage_analytics.py` - Storage monitoring and optimization
- `scheduler.py` - Automated task scheduling
- `retention_endpoints.py` - REST API endpoints

**Health Check:** `http://localhost:8080/health`

**API Documentation:** `http://localhost:8080/docs`

**README:** [services/data-retention/README.md](../services/data-retention/README.md)

---

### 4. Data API Service (Feature Data Hub)
**Port:** 8006 (external)  
**Technology:** Python 3.11, FastAPI, SQLAlchemy, InfluxDB Client  
**Purpose:** Feature data access for events, devices, sports, analytics

**Data Flow:**
```
Health Dashboard / External Clients
    ↓ HTTP GET requests
Data API Service
    ├─ Query InfluxDB (time-series data)
    │  ├─ Events, metrics, analytics
    │  └─ Sports scores and history
    ├─ Query SQLite (metadata - Epic 22)
    │  ├─ Devices and entities (<10ms queries)
    │  └─ Webhooks (sports service)
    └─ Return JSON responses
```

**Hybrid Database Architecture (Epic 22):**
- **InfluxDB**: Time-series data (events, metrics, sports)
- **SQLite**: Metadata (devices, entities) - 5-10x faster than InfluxDB

**Key Endpoints:**
- **Events**: `/api/v1/events/stats`, `/api/v1/events/search`, `/api/v1/events/automation-trace/{context_id}` (Epic 23.1)
- **Devices**: `/api/devices`, `/api/devices/{id}`, `/api/entities`
- **Sports**: `/api/v1/sports/games/history`, `/api/v1/sports/games/timeline/{id}`
- **Analytics**: `/api/v1/analytics/realtime`, `/api/v1/analytics/entity-activity`
- **Energy**: `/api/v1/energy/correlation`, `/api/v1/energy/recommendations`
- **HA Automation**: `/api/v1/ha/game-status/{team}`, `/api/v1/ha/webhooks/*`

**Epic 23 Advanced Features:**
- **Automation Tracing (23.1)**: Follow context.parent_id chains
- **Spatial Analytics (23.2)**: Area-based activity aggregation
- **Duration Analytics (23.3)**: Time-in-state pattern analysis
- **Device Reliability (23.5)**: Availability and event frequency tracking

**Health Check:** `http://localhost:8006/health`

**API Documentation:** `http://localhost:8006/docs`

**README:** [services/data-api/README.md](../services/data-api/README.md)

---

### 5. Admin API Service (System Monitoring)
**Port:** 8003 (external, mapped from internal 8004)  
**Technology:** Python 3.11, FastAPI  
**Purpose:** System administration, monitoring, and Docker management

**Data Flow:**
```
Health Dashboard / Admin Clients
    ↓ HTTP GET/POST requests
Admin API Service
    ├─ Health Checks (all services)
    ├─ Docker Management
    │  ├─ Container status
    │  ├─ Restart services
    │  └─ Scale services
    ├─ System Statistics
    │  └─ Query InfluxDB for metrics
    └─ Alert Management
```

**Key Endpoints:**
- **Health**: `/api/v1/health`, `/api/v1/health/services`, `/api/v1/health/dependencies`
- **Docker**: `/api/v1/docker/containers`, `/api/v1/docker/restart/{service}`
- **Statistics**: `/api/v1/stats`, `/api/v1/stats/timeseries`
- **Monitoring**: `/api/v1/monitoring/metrics`, `/api/v1/monitoring/logs`
- **Alerts**: `/api/v1/alerts`, `/api/v1/alerts/{id}`

**Key Features:**
- Centralized health monitoring
- Docker container management
- System metrics aggregation
- Alert management
- Log aggregation

**Health Check:** `http://localhost:8003/health`

**API Documentation:** `http://localhost:8003/docs` (when auth disabled)

**README:** [services/admin-api/README.md](../services/admin-api/README.md)

---

### 6. Health Dashboard
**Port:** 3000 (external)  
**Technology:** React 18.2, TypeScript, Vite, TailwindCSS, nginx  
**Purpose:** Web-based monitoring and administration interface

**Data Flow:**
```
Health Dashboard (React SPA)
    ├─ HTTP Polling (no WebSockets for simplicity)
    ├─ Data API (Port 8006)
    │  ├─ Events, devices, sports, analytics
    │  └─ Poll intervals: 5s (live), 15s (sports), 30s (general)
    ├─ Admin API (Port 8003)
    │  ├─ Health checks, Docker management
    │  └─ Poll interval: 10s
    └─ Sports Data (Port 8005)
       ├─ Live games, upcoming games
       └─ Poll interval: 15s (live), 5m (upcoming)
```

**12 Interactive Tabs:**
1. **Overview** - System health summary
2. **Services** - Service status and management
3. **Dependencies** - Service dependency graph
4. **Devices** - Device and entity browser (SQLite)
5. **Events** - Real-time event stream
6. **Logs** - Live log viewer
7. **Sports** - NFL/NHL game tracking
8. **Data Sources** - Integration status
9. **Energy** - Energy correlation
10. **Analytics** - Performance analytics
11. **Alerts** - Alert management
12. **Configuration** - Service configuration

**Key Features:**
- Real-time system monitoring via HTTP polling
- Service health visualization
- Device and entity browsing (Epic 22 SQLite)
- Sports game tracking (Epic 12)
- Event feed and filtering
- Configuration management
- Mobile-responsive design
- Dark/light theme support
- Interactive dependency graph

**Access:** `http://localhost:3000`

**README:** [services/health-dashboard/README.md](../services/health-dashboard/README.md)

---

### 6. InfluxDB
**Port:** 8086 (external)  
**Technology:** InfluxDB 2.7  
**Purpose:** Time-series database

**Key Features:**
- High-performance time-series storage
- Tiered storage with downsampling
- Web UI for data exploration
- Flux query language support

**Web UI:** `http://localhost:8086`

---

## 🌐 External Data Services

### 7. Carbon Intensity Service (NEW)
**Port:** 8010 (internal only)  
**Technology:** Python 3.11, FastAPI  
**Purpose:** Carbon intensity data integration

**Key Features:**
- Real-time carbon intensity data from National Grid
- Regional carbon metrics
- Renewable energy percentage
- Carbon footprint calculations

**Data Source:** National Grid ESO API

**README:** [services/carbon-intensity-service/README.md](../services/carbon-intensity-service/README.md)

---

### 8. Electricity Pricing Service (NEW)
**Port:** 8011 (internal only)  
**Technology:** Python 3.11, FastAPI  
**Purpose:** Real-time electricity pricing

**Key Features:**
- Multi-provider support (Octopus Energy, Agile, etc.)
- Time-of-use tariff information
- Peak/off-peak pricing
- Cost optimization data

**Supported Providers:**
- Octopus Energy
- Agile tariffs
- Dynamic pricing schemes

**README:** [services/electricity-pricing-service/README.md](../services/electricity-pricing-service/README.md)

---

### 9. Air Quality Service (NEW)
**Port:** 8012 (internal only)  
**Technology:** Python 3.11, FastAPI  
**Purpose:** Air quality monitoring

**Key Features:**
- Air quality index (AQI)
- Pollutant levels (PM2.5, PM10, NO2, O3, etc.)
- Health recommendations
- Government and OpenAQ data sources

**Data Sources:**
- OpenAQ
- Government air quality APIs

**README:** [services/air-quality-service/README.md](../services/air-quality-service/README.md)

---

### 10. Calendar Service
**Port:** 8013 (internal only)  
**Technology:** Python 3.12, aiohttp  
**Purpose:** Home Assistant calendar integration for occupancy prediction

**Data Flow:**
```
Home Assistant Calendar Entities
    ↓ REST API (every 15 min)
Calendar Service
    ├─ HA Client: Fetch events from multiple calendars
    ├─ Event Parser: Parse and detect WFH/home/away patterns
    ├─ Occupancy Predictor: Generate predictions with confidence scores
    └─ HTTP POST → InfluxDB (occupancy_prediction)
```

**Key Features:**
- Integrates with Home Assistant calendar entities (any HA-supported source)
- Supports unlimited calendars simultaneously
- Occupancy prediction based on calendar events
- Work-from-home (WFH) pattern detection
- Home/away location detection
- Dynamic confidence scoring
- Multi-calendar concurrent fetching
- Event-based automation triggers

**Supported Calendar Platforms** (via Home Assistant):
- Google Calendar
- iCloud (CalDAV)
- Office 365 / Outlook
- Nextcloud (CalDAV)
- Any CalDAV server
- Local HA calendars
- ICS file imports
- Todoist

**Configuration:**
- `HOME_ASSISTANT_URL` - HA instance URL
- `HOME_ASSISTANT_TOKEN` - Long-lived access token
- `CALENDAR_ENTITIES` - Comma-separated calendar entity IDs
- `CALENDAR_FETCH_INTERVAL` - Fetch interval in seconds (default: 900)

**InfluxDB Measurement:** `occupancy_prediction`

**Endpoints:**
- `GET /health` - Service health and calendar count

**Health Check:** `http://localhost:8013/health`

**README:** [services/calendar-service/README.md](../services/calendar-service/README.md)

---

### 11. Smart Meter Service (NEW)
**Port:** 8014 (internal only)  
**Technology:** Python 3.11, FastAPI  
**Purpose:** Smart meter data integration

**Key Features:**
- Real-time energy consumption data
- Multi-protocol support (SMETS2, P1, etc.)
- Cost calculations
- Usage analytics

**Supported Protocols:**
- SMETS2 (UK standard)
- P1 (Netherlands standard)
- Custom protocols

**README:** [services/smart-meter-service/README.md](../services/smart-meter-service/README.md)

---

### 12. Weather API Service
**Port:** Internal only  
**Technology:** Python 3.11, FastAPI  
**Purpose:** Weather data integration

**Key Features:**
- OpenWeatherMap API integration
- Location-based weather data
- Weather context for events
- Caching and rate limiting
- Integrated into websocket-ingestion service

**Data Source:** OpenWeatherMap

**README:** [services/weather-api/README.md](../services/weather-api/README.md)

---

### 13. Sports Data Service ⚡ (Epic 12)
**Port:** 8005 (external)  
**Technology:** Python 3.11, FastAPI, SQLite (webhooks Epic 22.3), InfluxDB  
**Purpose:** NFL & NHL sports data integration with webhook notifications

**Data Flow:**
```
ESPN API (Free)
    ↓ HTTP GET
Sports Data Service
    ├─ SportsAPIClient: Fetch live/upcoming games
    ├─ CacheService: Cache results
    │  ├─ Live games: 15s TTL
    │  └─ Upcoming: 5m TTL
    ├─ InfluxDBWriter: Store game scores (Story 12.1)
    │  └─ Measurements: nfl_games, nhl_games
    ├─ GameEventDetector: Detect events (Story 12.3)
    │  ├─ game_started
    │  ├─ score_changed
    │  └─ game_ended
    └─ WebhookManager: Trigger webhooks (SQLite Epic 22.3)
       ├─ Query webhooks from SQLite
       ├─ Filter by team/event
       ├─ POST with HMAC signature
       └─ Log delivery status
```

**Key Features:**
- **FREE ESPN API** (no API key required)
- Team-based filtering (user selects favorite teams)
- Live game status with real-time updates
- Upcoming games (next 24-48 hours)
- **Smart caching strategy:**
  - Live games: 15-second TTL
  - Upcoming games: 5-minute TTL
- **InfluxDB Persistence (Story 12.1):**
  - Historical game data
  - Score timelines
  - Team statistics
- **Circuit Breaker Pattern:**
  - Failure threshold: 3 consecutive failures
  - Timeout: 60 seconds
- **Webhook Notifications (Story 12.3):**
  - Register webhooks for game events
  - HMAC-SHA256 signature verification
  - Team-based filtering
  - SQLite storage (Epic 22.3)
  - Delivery logging
- **Home Assistant Integration:**
  - `/api/v1/ha/game-status/{team}` - Binary sensor friendly
  - `/api/v1/ha/game-context/{team}` - Rich context for automations
  - Webhook delivery to HA automations

**Endpoints:**
- `/api/v1/games/live?team_ids=sf,dal` - Live games
- `/api/v1/games/upcoming?hours=24&team_ids=sf` - Upcoming games
- `/api/v1/teams?league=NFL` - Available teams
- `/api/v1/games/history?team=Patriots&season=2025` - Historical queries (Story 12.2)
- `/api/v1/games/timeline/{game_id}` - Score progression (Story 12.2)
- `/api/v1/games/schedule/{team}?season=2025` - Team schedule (Story 12.2)
- `/api/v1/webhooks/register` - Register webhook (Story 12.3)
- `/api/v1/webhooks/list` - List webhooks (Story 12.3)
- `/api/v1/webhooks/{id}` - Delete webhook (Story 12.3)
- `/api/v1/ha/game-status/{team}` - HA sensor endpoint (Story 12.3)
- `/api/v1/ha/game-context/{team}` - HA automation context (Story 12.3)
- `/api/v1/user/teams` - Manage selected teams
- `/api/v1/metrics/api-usage` - Track API usage

**Epic 12.3 Webhook Events:**
- `game_started`: When game status changes to 'live'
- `score_changed`: When score changes during live game
- `game_ended`: When game status changes to 'finished'

**SQLite Schema (Epic 22.3):**
```sql
TABLE webhooks (
  webhook_id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  events TEXT NOT NULL,  -- JSON array
  secret_hash TEXT NOT NULL,  -- HMAC secret
  team TEXT,  -- Optional filter
  sport TEXT,
  active BOOLEAN DEFAULT 1
)

TABLE webhook_deliveries (
  id INTEGER PRIMARY KEY,
  webhook_id TEXT,
  event_type TEXT,
  status_code INTEGER,
  success BOOLEAN,
  delivered_at TIMESTAMP
)
```

**Health Check:** `http://localhost:8005/health`

**API Documentation:** `http://localhost:8005/docs`

**README:** [services/sports-data/README.md](../services/sports-data/README.md)

**Status:** ✅ Production Ready (Epic 12 Complete)

---

### 14. Log Aggregator Service
**Port:** 8015 (external)  
**Technology:** Python 3.11  
**Purpose:** Centralized log aggregation

**Key Features:**
- Collects logs from all Docker containers
- JSON log parsing and aggregation
- Real-time log streaming
- Log search and filtering

**Health Check:** `http://localhost:8015/health`

**README:** [services/log-aggregator/README.md](../services/log-aggregator/README.md)

---

### 15. HA Simulator Service
**Port:** N/A (test utility)  
**Technology:** Python 3.11  
**Purpose:** Test event generator

**Key Features:**
- Simulates Home Assistant events
- Configurable event generation
- Used for testing and development
- YAML-based configuration

**README:** [services/ha-simulator/README.md](../services/ha-simulator/README.md)

---

## 📊 Service Statistics

### Core Data Processing Services
- **Total:** 5 services
- **Ports:** 8001 (websocket), 8002 (enrichment), 8003 (admin), 8006 (data-api), 3000 (dashboard)
- **Technology:** Python/FastAPI, React/TypeScript
- **Container Size:** 40-80MB (Alpine-based)

### Data Services
- **Sports Data:** 8005 (Epic 12 complete with webhooks)
- **Data Retention:** 8080 (tiered storage, S3 archival)
- **Log Aggregator:** 8015

### External Integration Services
- **Total:** 7 services (all internal-only)
- **Services:** Weather, Carbon, Electricity, Air Quality, Calendar, Smart Meter, Energy Correlator, AI Automation
- **Ports:** 8010-8014, 8017-8018
- **Technology:** Python/FastAPI
- **Container Size:** 40-45MB (Alpine-based)

### Infrastructure
- **InfluxDB:** 8086 (time-series database)
- **SQLite:** Embedded (devices/entities in data-api, webhooks in sports-data)

### Overall System
- **Total Services:** 17 (16 microservices + InfluxDB)
- **Microservices:** 16 custom services
- **External Ports:** 9 (8001, 8002, 8003, 8005, 8006, 8015, 8080, 8086, 3000)
- **Internal Ports:** 8 (8010-8014, 8017-8018)
- **Total Container Size:** ~650MB (70% reduction with Alpine)
- **Architecture:** Event-driven microservices with hybrid database (InfluxDB + SQLite)

---

## 🔍 Service Dependencies and Data Flow

```
┌─────────────────┐
│ Home Assistant  │  (External System)
└────────┬────────┘
         │ WebSocket (auth token)
         ↓
┌─────────────────────────────────┐
│ WebSocket Ingestion (8001)      │  ← Entry Point
│ ├─ Event Processing             │
│ ├─ Weather Enrichment            │
│ ├─ Device/Entity Discovery       │
│ └─ Batch Processing              │
└────────┬────────────────────────┘
         │ HTTP POST /events
         ↓
┌─────────────────────────────────┐
│ Enrichment Pipeline (8002)       │
│ ├─ Data Validation               │
│ ├─ Data Normalization            │
│ └─ Quality Metrics               │
└────────┬────────────────────────┘
         │ InfluxDB Line Protocol
         ↓
┌─────────────────────────────────┐      ┌──────────────────┐
│ InfluxDB (8086)                  │◄─────┤ Data Retention   │
│ Bucket: home_assistant_events    │      │ (8080)           │
│ ├─ Events (time-series)          │      │ ├─ Downsampling  │
│ ├─ Sports scores                 │      │ ├─ Archival      │
│ └─ Analytics data                │      │ └─ S3/Glacier    │
└────────┬────────────────────────┘      └──────────────────┘
         │ Flux Queries
         ↓
┌─────────────────────────────────┐      ┌──────────────────┐
│ Data API (8006)                  │◄─────┤ SQLite           │
│ ├─ Event queries (InfluxDB)      │      │ (Embedded)       │
│ ├─ Device queries (SQLite)       │      │ ├─ Devices       │
│ ├─ Sports queries                │      │ └─ Entities      │
│ ├─ Analytics                     │      └──────────────────┘
│ └─ Energy correlation            │
└────────┬────────────────────────┘
         │
         │
┌─────────────────────────────────┐
│ Admin API (8003)                 │
│ ├─ Health monitoring             │
│ ├─ Docker management             │
│ └─ System statistics             │
└────────┬────────────────────────┘
         │
         ├─────────────────────────┐
         │                         │
         ↓                         ↓
┌─────────────────────────────────┐      ┌──────────────────┐
│ Health Dashboard (3000)          │      │ Sports Data      │
│ ├─ 12 Interactive Tabs           │◄─────┤ (8005)           │
│ ├─ HTTP Polling                  │      │ ├─ ESPN API      │
│ ├─ Real-time Charts              │      │ ├─ InfluxDB      │
│ └─ Device/Sports Management      │      │ ├─ Webhooks      │
└──────────────────────────────────┘      │ └─ HA Integration│
                                          └──────────────────┘

External Integration Services (Internal Only, 8010-8014, 8017-8018):
├─ Weather API (integrated in websocket-ingestion)
├─ Carbon Intensity (8010)
├─ Electricity Pricing (8011)
├─ Air Quality (8012)
├─ Calendar (8013)
├─ Smart Meter (8014)
├─ Energy Correlator (8017)
└─ AI Automation (8018)
```

---

## 🔌 Service Communication Matrix

| Source Service | Destination Service | Protocol | Port | Purpose | Frequency |
|----------------|---------------------|----------|------|---------|-----------|
| Home Assistant | websocket-ingestion | WebSocket | 8001 | Event streaming | Real-time |
| websocket-ingestion | enrichment-pipeline | HTTP POST | 8002 | Event forwarding | Batch (5s) |
| enrichment-pipeline | InfluxDB | HTTP | 8086 | Data storage | Batch writes |
| data-api | InfluxDB | HTTP | 8086 | Data queries | On-demand |
| data-api | SQLite | Direct | N/A | Metadata queries | On-demand |
| admin-api | All Services | HTTP GET | Various | Health checks | Every 10s |
| admin-api | InfluxDB | HTTP | 8086 | Statistics | On-demand |
| sports-data | ESPN API | HTTP GET | 443 | Sports data | 15s (live), 5m (upcoming) |
| sports-data | InfluxDB | HTTP | 8086 | Game scores | On score change |
| sports-data | Webhooks | HTTP POST | Various | Event notifications | On event |
| sports-data | SQLite | Direct | N/A | Webhook storage | On register/trigger |
| health-dashboard | data-api | HTTP GET | 8006 | Data fetching | 5-30s polling |
| health-dashboard | admin-api | HTTP GET | 8003 | Monitoring | 10s polling |
| health-dashboard | sports-data | HTTP GET | 8005 | Sports data | 15s (live), 5m (upcoming) |
| data-retention | InfluxDB | HTTP | 8086 | Data lifecycle | Scheduled |
| websocket-ingestion | Weather API | HTTP GET | 443 | Weather data | On event (15m cache) |

---

## 🎯 Complete Service Port Reference

| Service | Internal Port | External Port | Status | Purpose |
|---------|---------------|---------------|--------|---------|
| websocket-ingestion | 8001 | 8001 | ✅ Running | HA event ingestion |
| enrichment-pipeline | 8002 | 8002 | ✅ Running | Data processing |
| admin-api | 8004 | 8003 | ✅ Running | System monitoring (port mapped) |
| data-api | 8006 | 8006 | ✅ Running | Feature data hub |
| sports-data | 8005 | 8005 | ✅ Running | Sports data API |
| health-dashboard | 3000 | 3000 | ✅ Running | React frontend |
| data-retention | 8080 | 8080 | ✅ Running | Data lifecycle management |
| log-aggregator | 8015 | 8015 | ✅ Running | Centralized logging |
| carbon-intensity | 8010 | Internal | ✅ Running | Carbon data |
| electricity-pricing | 8011 | Internal | ✅ Running | Pricing data |
| air-quality | 8012 | Internal | ✅ Running | Air quality data |
| calendar-service | 8013 | Internal | ✅ Running | Calendar integration |
| smart-meter | 8014 | Internal | ✅ Running | Smart meter data |
| energy-correlator | 8017 | Internal | ✅ Running | Energy analysis |
| ai-automation | 8018 | Internal | ✅ Running | AI automation |
| InfluxDB | 8086 | 8086 | ✅ Running | Time-series database |

**Key:**
- ✅ Running - Service actively deployed
- Internal - Accessible only via Docker network
- Port Mapping - admin-api: external 8003 → internal 8004

---

## 🤖 Phase 1 AI Services (Containerized)

### AI Services Overview

The system now includes **5 containerized AI microservices** for advanced automation and analysis:

| Service | External Port | Internal Port | Status | Purpose |
|---------|---------------|---------------|--------|---------|
| openvino-service | 8022 | 8019 | ✅ Running | Embeddings, re-ranking, classification |
| ml-service | 8021 | 8020 | ✅ Running | K-Means clustering, anomaly detection |
| ner-service | 8019 | 8019 | ✅ Running | Named Entity Recognition (BERT) |
| openai-service | 8020 | 8020 | ✅ Running | GPT-4o-mini API client |
| ai-core-service | 8018 | 8018 | ✅ Running | AI orchestration and coordination |

### 1. OpenVINO Service
**Port:** 8022 (external) → 8019 (internal)  
**Technology:** Python 3.11, FastAPI, sentence-transformers, transformers  
**Purpose:** Optimized AI model inference for embeddings, re-ranking, and classification

**Models:**
- **all-MiniLM-L6-v2**: Text embeddings (384 dimensions)
- **bge-reranker-base**: Candidate re-ranking
- **flan-t5-small**: Pattern classification

**Endpoints:**
- `POST /embeddings` - Generate text embeddings
- `POST /rerank` - Re-rank candidates by relevance
- `POST /classify` - Classify patterns by category and priority
- `GET /health` - Service health status

### 2. ML Service
**Port:** 8021 (external) → 8020 (internal)  
**Technology:** Python 3.11, FastAPI, scikit-learn, pandas, numpy  
**Purpose:** Classical machine learning algorithms for data analysis

**Algorithms:**
- **K-Means Clustering**: Data clustering and pattern discovery
- **Isolation Forest**: Anomaly detection in time-series data

**Endpoints:**
- `POST /cluster` - Perform K-Means clustering
- `POST /anomaly_detect` - Detect anomalies using Isolation Forest
- `GET /health` - Service health status

### 3. NER Service
**Port:** 8019 (external) → 8019 (internal)  
**Technology:** Python 3.11, FastAPI, transformers, BERT  
**Purpose:** Named Entity Recognition for extracting entities from text

**Model:**
- **dslim/bert-base-NER**: BERT-based entity recognition

**Endpoints:**
- `POST /extract` - Extract entities from text
- `GET /health` - Service health status

### 4. OpenAI Service
**Port:** 8020 (external) → 8020 (internal)  
**Technology:** Python 3.11, FastAPI, OpenAI API client  
**Purpose:** GPT-4o-mini API client for advanced language processing

**Features:**
- **GPT-4o-mini Integration**: Cost-effective language model access
- **Configurable Parameters**: Temperature, max tokens, model selection
- **Error Handling**: Robust retry logic and error management

**Endpoints:**
- `POST /chat/completions` - Generate text completions
- `GET /health` - Service health status

### 5. AI Core Service
**Port:** 8018 (external) → 8018 (internal)  
**Technology:** Python 3.11, FastAPI, httpx  
**Purpose:** Orchestrator for complex AI workflows and multi-model coordination

**Features:**
- **Service Orchestration**: Coordinates calls to other AI services
- **Complex Analysis**: Multi-step AI workflows
- **Health Monitoring**: Monitors dependent AI services
- **Error Handling**: Graceful degradation when services are unavailable

**Endpoints:**
- `POST /orchestrate` - Execute complex AI analysis workflows
- `GET /health` - Service health status

### AI Services Integration

**Communication Pattern:**
```
AI Automation Service (Port 8017)
    ↓ HTTP API calls
AI Core Service (Port 8018)
    ├─ OpenVINO Service (Port 8019) - Embeddings, re-ranking
    ├─ ML Service (Port 8020) - Clustering, anomaly detection
    ├─ NER Service (Port 8019) - Entity extraction
    └─ OpenAI Service (Port 8020) - Language processing
```

**Health Monitoring:**
- All services include comprehensive health checks
- Docker Compose health checks use Python urllib
- Service dependencies with health-based startup conditions
- Circuit breaker pattern for fault tolerance

**Testing:**
- Comprehensive test suite for all AI services
- Integration tests for service communication
- Performance monitoring and metrics collection
- Context7 knowledge base integration for troubleshooting

---

## 🗄️ Database Architecture

### InfluxDB (Time-Series Data)
**Bucket:** `home_assistant_events`
- **Events**: Home Assistant state changes
- **Metrics**: System and application metrics
- **Sports**: Game scores and timelines
- **Analytics**: Aggregated analytics data

**Retention:**
- Default: 30 days
- Downsampled: 90 days (1h resolution)
- Archived: 1 year (1d resolution)

### SQLite (Relational Metadata)

**Data API Database:** `data/metadata.db`
- **Devices**: Home Assistant devices
- **Entities**: Home Assistant entities
- **Performance**: <10ms queries (5-10x faster than InfluxDB)

**Sports Data Database:** `data/webhooks.db` (Epic 22.3)
- **Webhooks**: Registered webhooks
- **Webhook Deliveries**: Delivery log and status
- **Performance**: <5ms queries

**Benefits:**
- Proper foreign key relationships
- ACID transactions
- Concurrent-safe (WAL mode)
- Optimized for relational queries

---

## 📚 Additional Documentation

- **[Complete Data Flow Call Tree](../implementation/analysis/COMPLETE_DATA_FLOW_CALL_TREE.md)** - Detailed call trees and data flows
- **[API Documentation](API_DOCUMENTATION.md)** - Complete API reference
- **[Docker Services Reference](DOCKER_COMPOSE_SERVICES_REFERENCE.md)** - Docker configuration details
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Production deployment
- **[Architecture Documentation](architecture.md)** - System architecture
- **[User Manual](USER_MANUAL.md)** - User guide and configuration
- **[Tech Stack](architecture/tech-stack.md)** - Technology choices and rationale
- **[Source Tree](architecture/source-tree.md)** - Project structure and file organization

---

## 🎯 Quick Links

**Health Checks:**
- Websocket Ingestion: http://localhost:8001/health
- Enrichment Pipeline: http://localhost:8002/health
- Admin API: http://localhost:8003/health
- Sports Data: http://localhost:8005/health
- Data API: http://localhost:8006/health
- Health Dashboard: http://localhost:3000
- InfluxDB: http://localhost:8086

**API Documentation:**
- Admin API: http://localhost:8003/docs
- Data API: http://localhost:8006/docs
- Sports Data: http://localhost:8005/docs
- Data Retention: http://localhost:8080/docs

---

**Last Updated:** 2025-10-16  
**Version:** 4.1 (Complete Data Flow Documentation)  
**Status:** Production Ready with Epic 12, 22, 23 Complete

