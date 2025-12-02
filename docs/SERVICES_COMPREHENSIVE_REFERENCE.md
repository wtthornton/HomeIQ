# HomeIQ Services - Comprehensive Reference

**Last Updated:** November 4, 2025
**Total Services:** 26 microservices (24 active + 2 infrastructure)
**Review Status:** ✅ Verified against actual implementation

---

## Quick Reference Table

| # | Service | External Port | Internal Port | Status | Category |
|---|---------|--------------|---------------|--------|----------|
| 1 | influxdb | 8086 | 8086 | ✅ Active | Database |
| 2 | data-api | 8006 | 8006 | ✅ Active | Core API |
| 3 | admin-api | 8003 | 8004 | ✅ Active | Core API |
| 4 | websocket-ingestion | 8001 | 8001 | ✅ Active | Core API |
| 5 | health-dashboard | 3000 | 80 | ✅ Active | Frontend |
| 6 | ai-automation-ui | 3001 | 80 | ✅ Active | Frontend |
| 7 | ai-automation-service | 8024 | 8018 | ✅ Active | AI/ML |
| 8 | ai-core-service | 8018 | 8018 | ✅ Active | AI/ML |
| 9 | openvino-service | 8026 | 8019 | ✅ Active | AI/ML |
| 10 | ml-service | 8025 | 8020 | ✅ Active | AI/ML |
| 11 | ner-service | 8019 | 8019 | ✅ Active | AI/ML |
| 12 | openai-service | 8020 | 8020 | ✅ Active | AI/ML |
| 13 | device-intelligence-service | 8028 | 8019 | ✅ Active | AI/ML |
| 14 | automation-miner | 8029 | 8019 | ✅ Active | AI/ML |
| 15 | weather-api | 8009 | 8009 | ✅ Active | Enrichment |
| 16 | air-quality-service | 8012 | 8012 | ✅ Active | Enrichment |
| 17 | carbon-intensity-service | 8010 | 8010 | ✅ Active | Enrichment |
| 18 | electricity-pricing-service | 8011 | 8011 | ✅ Active | Enrichment |
| 19 | smart-meter-service | 8014 | 8014 | ✅ Active | Enrichment |
| 20 | calendar-service | 8013 | 8013 | ✅ Active | Enrichment |
| 21 | data-retention | 8080 | 8080 | ✅ Active | Processing |
| 22 | energy-correlator | 8017 | 8017 | ✅ Active | Processing |
| 23 | log-aggregator | 8015 | 8015 | ✅ Active | Processing |
| 24 | ha-setup-service | 8027 | 8020 | ✅ Active | Processing |
| 25 | ha-simulator | 8123 | 8123 | 🔧 Dev Only | Development |
| 26 | mosquitto | 1883, 9001 | 1883, 9001 | ✅ Active | Infrastructure |
| — | enrichment-pipeline | 8002 | — | ❌ DEPRECATED | — |

---

## 1. Core Services

### 1.1 InfluxDB
**Port:** 8086
**Technology:** InfluxDB 2.7
**Purpose:** Time-series database for event storage

**Responsibilities:**
- Store Home Assistant state change events
- Store metrics and telemetry data
- Store enrichment data (weather, energy, sports)
- Provide time-series query capabilities

**Key Features:**
- 365-day retention policy (home_assistant_events bucket)
- ~150 flattened attribute fields for fast queries
- Batch writes (1000 points per batch)
- Automatic retention and downsampling

**Performance:**
- Write throughput: 1000+ events/second
- Query latency: 50-200ms (depending on time range)
- Storage: ~1GB per month (typical home)

**Health Check:** `/health`
**Configuration:**
```bash
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_ORG=homeiq
INFLUXDB_BUCKET=home_assistant_events
INFLUXDB_TOKEN=<generated>
```

---

### 1.2 Data API
**Port:** 8006 (External & Internal)
**Technology:** Python 3.11 + FastAPI + SQLite + InfluxDB
**Purpose:** Feature data hub for events, devices, sports, analytics

**Responsibilities:**
- Query historical HA events from InfluxDB
- Device/entity metadata queries from SQLite
- Sports data integration (NFL/NHL scores)
- Home Assistant automation webhook endpoints
- Alert management
- Analytics queries
- Energy correlation data

**Key Components:**
```
src/
├── main.py                          # FastAPI app initialization
├── events_endpoints.py              # Event queries (Story 13.2)
├── devices_endpoints.py             # Device/entity browsing (SQLite)
├── sports_endpoints.py              # Sports data (NFL, NHL)
├── ha_automation_endpoints.py       # HA webhook integration
├── alert_endpoints.py               # Alert management
├── analytics_endpoints.py           # Analytics queries
├── energy_endpoints.py              # Energy correlation
├── metrics_endpoints.py             # Performance metrics
├── integration_endpoints.py         # Integration management
├── database.py                      # SQLite setup & migrations
└── alerting_service.py             # Alert processing
```

**Database Architecture:**
- SQLite (metadata.db): devices, entities tables with indexes
- InfluxDB: home_assistant_events, nfl_scores, nhl_scores

**Key Endpoints:**
```
GET  /health                    # Service health
GET  /api/v1/events             # Query HA events
GET  /api/devices               # List devices (SQLite)
GET  /api/entities              # List entities (SQLite)
POST /internal/devices/bulk_upsert     # Device sync
POST /internal/entities/bulk_upsert    # Entity sync
GET  /api/v1/sports/games/live  # Live sports data
POST /api/v1/ha/webhooks/register      # HA webhook registration
```

**Performance:**
- Device queries: <10ms (SQLite indexes)
- Event queries: 50-200ms (InfluxDB time-series)
- Query caching: 5-minute TTL

---

### 1.3 Admin API
**Port:** 8003 (External) → 8004 (Internal)
**Technology:** Python 3.11 + FastAPI
**Purpose:** System monitoring, health checks, Docker management

**Responsibilities:**
- System health monitoring
- Docker container management
- Service configuration management (read/write .env files)
- InfluxDB query interface
- Alert management with auto-cleanup

**Key Endpoints:**
```
GET  /health                          # Service health
GET  /api/v1/health                   # Comprehensive system health
GET  /api/v1/integrations             # List service integrations
GET  /api/v1/integrations/{service}/config   # Get config
PUT  /api/v1/integrations/{service}/config   # Update config
GET  /api/v1/services                 # List services with status
POST /api/v1/services/{service}/restart      # Restart service
GET  /api/v1/alerts/active            # Get active alerts
POST /api/v1/alerts/{id}/acknowledge  # Acknowledge alert
```

**Configuration Management:**
- Reads/writes from `infrastructure/.env.*` files
- Masks sensitive fields (tokens, passwords)
- File permissions: chmod 600 (secure)
- Manages: HA, Weather API, InfluxDB credentials

**Docker Management:**
- Container start/stop/restart
- Container health status
- Resource usage monitoring
- Log access

---

### 1.4 WebSocket Ingestion
**Port:** 8001
**Technology:** Python 3.11 + aiohttp + WebSocket
**Purpose:** Real-time Home Assistant WebSocket connection

**Responsibilities:**
- Real-time WebSocket connection to Home Assistant
- Event normalization and processing
- Device/entity discovery (stores to SQLite via data-api)
- Direct InfluxDB writes (Epic 31 architecture)
- Network resilience with infinite retry

**Network Resilience Features:**
```python
# Infinite retry configuration
WEBSOCKET_MAX_RETRIES=-1           # -1 = infinite, or specific number
WEBSOCKET_MAX_RETRY_DELAY=300      # 5 minutes max backoff

# Exponential backoff: 1s → 2s → 4s → ... → 300s (capped)
Attempt 1/∞ in 1.0s
Attempt 2/∞ in 2.0s
Attempt 10/∞ in 300.0s
... continues forever ...
```

**High-Volume Processing:**
```python
# Batch processing configuration
BATCH_SIZE=100                      # Max events per batch
BATCH_TIMEOUT=5.0                   # Max seconds to wait
MAX_WORKERS=10                      # Concurrent workers
PROCESSING_RATE_LIMIT=1000         # Max events/second
MAX_MEMORY_MB=1024                  # Memory ceiling
```

**Event Processing Pipeline:**
1. Connect to HA WebSocket with infinite retry
2. Subscribe to `state_changed` events
3. Normalize events (extract state, attributes, timing)
4. Batch processing (100 events or 5s timeout)
5. Direct write to InfluxDB (Epic 31 architecture)
6. Device/entity discovery on connect → POST to data-api

**Device Discovery Process:**
```
HA Connection ──> Device Registry Discovery
                  ├── Query: config/device_registry/list
                  ├── Query: config/entity_registry/list
                  └── POST /internal/bulk_upsert to data-api
                      └── Stores to SQLite
```

**Circuit Breaker Integration:**
- Uses `enhanced_ha_connection_manager.py`
- States: CLOSED → OPEN → HALF_OPEN
- Automatic fallback: Primary HA → Nabu Casa → Local HA
- Configurable fail_max, reset_timeout, success_threshold

---

## 2. Frontend Services

### 2.1 Health Dashboard
**Port:** 3000 (External) → 80 (Internal, nginx)
**Technology:** React 18.2 + TypeScript + Vite + Tailwind CSS
**Purpose:** System monitoring & management UI

**Components:** 40+ React components organized by feature
**Tabs:** 13 specialized tabs
1. Overview - System health summary
2. Services - Service management & health
3. Data Sources - Integration status
4. Analytics - Performance analytics
5. Alerts - Active alert monitoring
6. Configuration - Service config management
7. Dependencies - Service dependency graph
8. Logs - Log viewing
9. Metrics - Real-time metrics
10. Sports - Sports data dashboard
11. Energy - Energy correlation
12. Devices - Device browser
13. Settings - UI preferences

**State Management:**
- Hooks-based architecture (no Redux/global state)
- 11 custom hooks for data fetching
- Local useState for UI state
- Singleton pattern for API clients

**API Clients:**
- **AdminApiClient** (port 8003) - System monitoring & control
- **DataApiClient** (port 8006) - Device/Entity/Event data
- **AIAutomationApiClient** (port 8018) - AI-powered features

**Key Features:**
- Real-time metrics with 30-second polling
- Dark/light theme support
- Mobile-responsive design
- Masked credential display
- Service restart capability
- Interactive dependency graph visualization

**Performance Optimizations:**
- `useMemo` for derived state
- `useCallback` for memoized functions
- `React.memo` for expensive components
- Code splitting with vendor chunk
- Conditional rendering

**Nginx Configuration:**
- Dynamic DNS resolution (`resolver 127.0.0.11`)
- Route proxying to data-api and admin-api
- WebSocket upgrade support
- Gzip compression
- Cache headers for static assets
- Security headers (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)

---

### 2.2 AI Automation UI
**Port:** 3001 (External) → 80 (Internal, nginx)
**Technology:** React 18 + TypeScript + Zustand + Framer Motion + Tailwind
**Purpose:** Conversational automation interface

**Pages:**
- Dashboard (root): Suggestion feed with status tabs
- Patterns: Detected usage patterns
- Synergies: Cross-automation opportunities
- Deployed: Active Home Assistant automations
- Discovery: Device exploration
- Settings: UI preferences

**Suggestion States:**
```
draft → refining → yaml_generated → deployed
  ↓                      ↓
rejected            rejected
```

**Conversational Interface:**
1. View draft suggestions (description only, no YAML)
2. Refine with natural language input
3. Approve to generate YAML with safety validation
4. Deploy to Home Assistant via MQTT
5. Monitor deployment status

**Features:**
- Natural language automation refinement
- Device validation and entity mapping
- Entity alias management
- YAML generation with safety checks
- Deployment status tracking
- Real-time MQTT notifications

---

## 3. AI/ML Services

### 3.1 AI Automation Service
**Port:** 8024 (External) → 8018 (Internal)
**Technology:** Python 3.11 + FastAPI + OpenAI + SQLite
**Purpose:** Pattern detection, AI-powered suggestions, conversational flow

**Responsibilities:**
- Pattern detection from historical events
- AI-powered automation suggestions
- Natural language generation (OpenAI GPT-4o-mini)
- Device intelligence & capability discovery
- Conversational suggestion refinement
- N-level synergy detection
- Entity alias management

**Unified Daily Batch Job (3 AM):**
```
Phase 1: Device Capability Update (Epic AI-2)
├─ Query Zigbee2MQTT device database (6,000+ models)
├─ Update device capabilities in SQLite
└─ Calculate feature utilization

Phase 2: Fetch Historical Events
├─ Query InfluxDB (last 30 days)
├─ Fetch from data-api
└─ Load event stream

Phase 3: Pattern Detection (Epic AI-1)
├─ Time-of-day patterns
├─ Device co-occurrence patterns
├─ Anomaly detection (repeated manual interventions)
└─ Store patterns in SQLite

Phase 4: Feature Analysis (Epic AI-2)
├─ Analyze device capability usage
├─ Identify unused features
└─ Score recommendations

Phase 5: Description-Only Generation (Story AI1.24)
├─ OpenAI GPT-4o-mini (description only, NO YAML)
├─ Human-readable automation descriptions
├─ Save as status='draft'
└─ YAML generated only after user approval

Phase 6: Publish MQTT Notification
└─ Notify frontend of new suggestions
```

**Conversational Refinement Flow (Story AI1.23-24):**
```
1. Generate description-only suggestion
   ├─ No YAML yet (automation_yaml=NULL)
   └─ Status='draft'

2. User clicks "Refine"
   └─ POST /api/v1/suggestions/{id}/refine
   ├─ User provides natural language (e.g., "make it 6:30am instead")
   ├─ OpenAI refines description
   └─ Status='refining'

3. User clicks "Approve"
   └─ POST /api/v1/suggestions/{id}/approve
   ├─ OpenAI generates YAML code
   ├─ Safety validation (6-rule engine)
   ├─ Status='yaml_generated'
   └─ Saves automation_yaml to DB

4. User clicks "Deploy"
   └─ POST /api/deploy/{id}
   ├─ Sends to Home Assistant via MQTT
   └─ Status='deployed'
```

**Key Algorithms:**

1. **Entity Resolution (Story AI1.21)**
   - Multi-signal matching: 35% embeddings + 30% exact + 15% fuzzy + 15% numbered + 5% location
   - Fuzzy string matching (rapidfuzz library)
   - Enhanced blocking (domain/location filtering)
   - User-defined aliases

2. **Safety Validation (6-Rule Engine)**
   - Entity ID validation
   - Device type compatibility
   - Service existence verification
   - Attribute/state validation
   - Trigger-condition-action consistency
   - Resource limits (execution time, complexity)

**Database Schema (11 tables in ai_automation.db):**
- `suggestions` - AI-generated automation suggestions
- `patterns` - Detected usage patterns
- `device_capabilities` - Zigbee2MQTT capabilities (6,000+ models)
- `device_feature_usage` - Feature utilization tracking
- `synergy_opportunities` - Multi-device automations
- `device_embeddings` - 1024-dim embeddings for similarity [Epic 47]
- `ask_ai_queries` - NL query history
- `entity_aliases` - User-defined entity mappings
- `reverse_engineering_metrics` - AI refinement analytics
- `automation_versions` - Rollback history (last 3 versions)
- `user_feedback` - Feedback tracking

**OpenAI Integration:**
- Model: GPT-4o-mini (cost-effective)
- Phase 5: Description generation (~$0.001-0.005 per run)
- Annual cost: ~$0.50-2.50
- Token usage tracked and reported

---

### 3.2 AI Core Service
**Port:** 8018
**Technology:** Python 3.11 + FastAPI
**Purpose:** AI orchestration and coordination

**Responsibilities:**
- Multi-model orchestration
- Service coordination
- Model routing and load balancing
- Caching and optimization

---

### 3.3 OpenVINO Service
**Port:** 8026 (External) → 8019 (Internal)
**Technology:** Python 3.11 + OpenVINO + FastAPI
**Purpose:** Optimized embeddings, re-ranking, classification

**Models:**
- BAAI/bge-large-en-v1.5 (1024-dim embeddings) [Epic 47]
- bge-reranker-base (re-ranking)
- flan-t5-small (classification)

**Use Cases:**
- Entity similarity search
- Semantic search for device capabilities
- Document re-ranking
- Text classification

---

### 3.4 ML Service
**Port:** 8025 (External) → 8020 (Internal)
**Technology:** Python 3.11 + scikit-learn + FastAPI
**Purpose:** Classical ML algorithms

**Algorithms:**
- K-Means clustering (time-of-day patterns)
- Anomaly detection
- Co-occurrence mining
- Feature analysis

---

### 3.5 NER Service
**Port:** 8031
**Technology:** Python 3.11 + Transformers + FastAPI
**Purpose:** Named Entity Recognition

**Model:** dslim/bert-base-NER
**Use Cases:**
- Entity extraction from natural language
- Device name recognition
- Automation intent parsing

---

### 3.6 OpenAI Service
**Port:** 8020
**Technology:** Python 3.11 + OpenAI Python SDK + FastAPI
**Purpose:** GPT-4o-mini API wrapper

**Responsibilities:**
- Natural language generation
- Automation description creation
- Conversational refinement
- YAML code generation
- Error correction and validation

---

### 3.7 Device Intelligence Service
**Port:** 8028 (External) → 8019 (Internal)
**Technology:** Python 3.11 + FastAPI + MQTT + SQLite
**Purpose:** Device capability discovery

**Database (device_intelligence.db - 7 tables):**
- `devices` - Device registry with health scores
- `device_capabilities` - Capability definitions
- `device_relationships` - Parent/child/sibling relationships
- `device_health_metrics` - Health tracking
- `device_entities` - Entity mappings
- `discovery_sessions` - Discovery job tracking
- `cache_stats` - Performance metrics

**Features:**
- MQTT-based device discovery
- Zigbee2MQTT integration
- Capability parsing and storage
- Relationship management
- Health monitoring

---

### 3.8 Automation Miner
**Port:** 8029 (External) → 8019 (Internal)
**Technology:** Python 3.11 + FastAPI + SQLite + Web Scraping
**Purpose:** Community automation mining

**Database (automation_miner.db):**
- `community_automations` - 6,000+ community automations corpus
- `miner_state` - Crawler state management

**Data Sources:**
- Discourse forums
- GitHub repositories
- Community Hacks

**Features:**
- Web scraping and crawling
- Automation parsing and normalization
- Quality scoring
- Pattern extraction

---

## 4. Data Enrichment Services

### 4.1 Weather API
**Port:** 8009
**Technology:** Python 3.11 + FastAPI + OpenWeatherMap API
**Purpose:** Weather data integration

**Features:**
- Current weather conditions
- 5-day forecasts
- 15-minute refresh intervals
- 15-minute TTL caching with fallback
- InfluxDB storage (weather_data measurement)

**Metrics:**
- Temperature, humidity, pressure
- Wind speed/direction
- Weather description
- Precipitation

---

### 4.2 Air Quality Service
**Port:** 8012
**Technology:** Python 3.11 + FastAPI + AirNow API
**Purpose:** Air quality monitoring

**Metrics:**
- PM2.5, PM10
- Ozone (O3)
- AQI (Air Quality Index)

**Features:**
- Hourly refresh
- 1-hour TTL caching
- InfluxDB storage (air_quality measurement)
- Health-based automations (close windows, HVAC adjustments)

---

### 4.3 Carbon Intensity Service
**Port:** 8010
**Technology:** Python 3.11 + FastAPI + WattTime API
**Purpose:** Grid carbon intensity data

**Metrics:**
- Carbon intensity (gCO2/kWh)
- Renewable percentage
- Grid region

**Features:**
- 15-minute refresh
- InfluxDB storage (carbon_intensity measurement)
- Use case: Schedule energy-intensive tasks during clean energy periods

---

### 4.4 Electricity Pricing Service
**Port:** 8011
**Technology:** Python 3.11 + FastAPI + Awattar API
**Purpose:** Real-time electricity pricing

**Features:**
- Hourly electricity prices (Germany/Austria)
- 24-hour forecasts
- Hourly refresh
- InfluxDB storage (electricity_pricing measurement)
- Use case: Schedule EV charging/water heating during cheap hours

---

### 4.5 Smart Meter Service
**Port:** 8014
**Technology:** Python 3.11 + FastAPI + Home Assistant Sensors
**Purpose:** Power consumption tracking

**Adapters:**
- Home Assistant sensors
- Emporia Vue
- Sense
- Shelly EM

**Metrics:**
- Whole-home power (W)
- Daily energy (kWh)
- Circuit-level breakdown

**Features:**
- 5-minute refresh
- InfluxDB storage (smart_meter + smart_meter_circuit measurements)
- Phantom load detection
- High consumption alerting

---

### 4.6 Calendar Service
**Port:** 8013
**Technology:** Python 3.11 + FastAPI + Home Assistant Calendar Integration
**Purpose:** Calendar-based presence prediction

**Platforms:**
- Google Calendar
- iCloud Calendar
- CalDAV
- Office 365
- Nextcloud
- Local Calendar

**Features:**
- 15-minute refresh
- Work-from-home (WFH) detection
- Home location detection
- Away status prediction
- InfluxDB storage (occupancy_prediction measurement)
- Use case: Predictive automations (prepare home before arrival)

---

## 5. Processing & Infrastructure Services

### 5.1 Data Retention
**Port:** 8080
**Technology:** Python 3.11 + FastAPI
**Purpose:** Data lifecycle and backup management

**Features:**
- Automatic data archival
- Compression after 24 hours
- Backup creation (24-hour intervals)
- Retention policy enforcement (365 days)
- S3-ready backup format

**Configuration:**
```bash
CLEANUP_INTERVAL_HOURS=24
BACKUP_INTERVAL_HOURS=24
BACKUP_DIR=/backups
RETENTION_POLICY_DAYS=365
```

---

### 5.2 Energy Correlator
**Port:** 8017
**Technology:** Python 3.11 + FastAPI + InfluxDB
**Purpose:** Energy pattern correlation analysis

**Features:**
- Device energy correlation
- Usage pattern detection
- Cost analysis
- Optimization recommendations

---

### 5.3 Log Aggregator
**Port:** 8015
**Technology:** Python 3.11 + FastAPI
**Purpose:** Centralized logging

**Features:**
- Log collection from all services
- Structured JSON parsing
- Correlation ID tracking
- Log rotation (168 hours / 7 days default)
- Log level filtering

---

### 5.4 HA Setup Service
**Port:** 8027 (External) → 8020 (Internal)
**Technology:** Python 3.11 + FastAPI + SQLite
**Purpose:** Home Assistant health monitoring & setup recommendations

**Database (ha_setup_data):**
- Environment health tracking
- Integration status
- Setup recommendations

**Features:**
- HA connectivity testing
- Integration verification
- Health scoring
- Setup guidance

---

### 5.5 HA Simulator
**Port:** 8123
**Technology:** Python 3.11 + FastAPI
**Purpose:** Development WebSocket simulator

**Status:** 🔧 Development only
**Features:**
- Mock Home Assistant WebSocket API
- Event simulation
- Device registry simulation
- Testing without real HA instance

---

### 5.6 Mosquitto
**Ports:** 1883 (MQTT), 9001 (MQTT over WebSocket)
**Technology:** Eclipse Mosquitto
**Purpose:** MQTT broker for event-driven notifications

**Features:**
- Event-driven notifications
- AI automation deployment notifications
- Real-time update propagation
- WebSocket support for frontend

---

### 5.7 Enrichment Pipeline (DEPRECATED)
**Port:** 8002
**Status:** ❌ DEPRECATED (Epic 31)
**Reason:** Services now write directly to InfluxDB

**Migration:** All enrichment services (weather, carbon, air quality, etc.) now write directly to InfluxDB instead of going through the enrichment pipeline.

---

## 6. Service Dependencies

### Dependency Map

```
influxdb (base)
├── websocket-ingestion
├── data-api
├── admin-api
├── data-retention
├── weather-api
├── carbon-intensity-service
├── electricity-pricing-service
├── air-quality-service
├── smart-meter-service
├── calendar-service
├── energy-correlator
└── ai-automation-service
    ├── ai-core-service
    ├── openvino-service
    ├── ml-service
    ├── ner-service
    ├── openai-service
    ├── device-intelligence-service
    └── automation-miner

health-dashboard
├── admin-api
├── data-api
└── ai-automation-service (optional)

ai-automation-ui
└── ai-automation-service

log-aggregator
└── (all services)

ha-setup-service
└── data-api
```

---

## 7. Shared Libraries

All services share common libraries from `/shared/`:

**Core Modules (11 modules, 3,947 lines):**
1. `ha_connection_manager.py` (537 lines) - HA connection with fallback
2. `enhanced_ha_connection_manager.py` (443 lines) - Circuit breaker pattern
3. `logging_config.py` (259 lines) - Structured JSON logging
4. `correlation_middleware.py` (225 lines) - Request tracking
5. `metrics_collector.py` (318 lines) - In-memory metrics
6. `metrics_api.py` (383 lines) - InfluxDB query API
7. `alert_manager.py` (351 lines) - Threshold-based alerting
8. `auth.py` (230 lines) - API authentication
9. `influxdb_query_client.py` (407 lines) - InfluxDB client
10. `system_metrics.py` (466 lines) - System resource metrics
11. `log_validator.py` (328 lines) - Log validation

**Types Package:**
- `types/health.py` (217 lines) - Standardized health check types

---

## 8. Docker Compose Profiles

| Profile | Services | Use Case |
|---------|----------|----------|
| `docker-compose.yml` | 26 services | Full production deployment |
| `docker-compose.prod.yml` | 8 core services | Production-optimized |
| `docker-compose.dev.yml` | 9 services | Development with hot-reload |
| `docker-compose.complete.yml` | Core services | Complete simplified setup |
| `docker-compose.simple.yml` | 2 services | Ultra-minimal (InfluxDB + WebSocket) |

---

## 9. Health Check Endpoints

All services expose `/health` endpoints:

```bash
# Core Services
curl http://localhost:8086/health  # InfluxDB
curl http://localhost:8001/health  # WebSocket Ingestion
curl http://localhost:8003/health  # Admin API
curl http://localhost:8006/health  # Data API

# AI Services
curl http://localhost:8024/health  # AI Automation Service
curl http://localhost:8018/health  # AI Core Service
curl http://localhost:8026/health  # OpenVINO Service
curl http://localhost:8025/health  # ML Service
curl http://localhost:8031/health  # NER Service
curl http://localhost:8020/health  # OpenAI Service
curl http://localhost:8028/health  # Device Intelligence Service
curl http://localhost:8029/health  # Automation Miner

# Enrichment Services
curl http://localhost:8009/health  # Weather API
curl http://localhost:8010/health  # Carbon Intensity
curl http://localhost:8011/health  # Electricity Pricing
curl http://localhost:8012/health  # Air Quality
curl http://localhost:8013/health  # Calendar Service
curl http://localhost:8014/health  # Smart Meter

# Processing Services
curl http://localhost:8080/health  # Data Retention
curl http://localhost:8017/health  # Energy Correlator
curl http://localhost:8015/health  # Log Aggregator
curl http://localhost:8027/health  # HA Setup Service

# Frontend Services
curl http://localhost:3000/       # Health Dashboard
curl http://localhost:3001/       # AI Automation UI
```

---

## 10. Performance Characteristics

### Response Time Targets

| Service | Target | Actual | Status |
|---------|--------|--------|--------|
| Health checks | <10ms | <5ms | ✅ Exceeded |
| Data API (SQLite) | <10ms | <8ms | ✅ Met |
| Data API (InfluxDB) | <100ms | 45-120ms | ✅ Met |
| WebSocket Ingestion | <100ms | <50ms | ✅ Exceeded |
| AI Automation (query) | <200ms | <150ms | ✅ Met |
| AI Automation (daily job) | <10 min | 2-4 min | ✅ Exceeded |
| Dashboard load | <2s | ~1.5s | ✅ Met |

---

## 11. Service Interdependencies

### HTTP Service Dependencies

| Service | Depends On | Type |
|---------|-----------|------|
| data-api | InfluxDB, SQLite | Database |
| admin-api | InfluxDB, Docker daemon | Database, Infrastructure |
| websocket-ingestion | Home Assistant, InfluxDB, data-api | External, Database, API |
| ai-automation-service | InfluxDB, data-api, OpenAI, MQTT | Database, API, External, Messaging |
| health-dashboard | admin-api, data-api | API |
| ai-automation-ui | ai-automation-service | API |
| All enrichment services | InfluxDB, External APIs | Database, External |

### Database Dependencies

**SQLite Shared by:**
- data-api (metadata.db)
- ai-automation-service (ai_automation.db)
- automation-miner (automation_miner.db)
- device-intelligence-service (device_intelligence.db)
- ha-setup-service (ha_setup_data)

**InfluxDB Shared by:**
- All services (write measurements)
- data-api, ai-automation-service, admin-api (query)
- health-dashboard (visualize)

---

## 12. Deployment Recommendations

### Minimum Requirements
- **CPU:** 2 cores
- **RAM:** 4GB
- **Storage:** 10GB
- **Network:** Stable connection to Home Assistant

### Recommended (Development)
- **CPU:** 4 cores
- **RAM:** 8GB
- **Storage:** 20GB

### Recommended (Production)
- **CPU:** 4-6 cores
- **RAM:** 6-8GB
- **Storage:** 50GB

---

**Document Version:** 1.0.0
**Last Reviewed:** November 4, 2025
**Maintained By:** HomeIQ Development Team
**Related Documents:**
- [CODE_REVIEW_COMPREHENSIVE_FINDINGS.md](CODE_REVIEW_COMPREHENSIVE_FINDINGS.md)
- [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md)
- [architecture/database-schema.md](architecture/database-schema.md)
