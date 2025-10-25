# Architecture Overview: HomeIQ

**Last Updated:** 2025-10-25
**Version:** 3.0.0 (Phase 1 AI Containerization)

---

## System Architecture

HomeIQ is an enterprise-grade intelligence layer for Home Assistant with AI-powered automation, pattern detection, advanced analytics, and distributed AI services.

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Home Assistant                            │
│  (WebSocket API, Device Registry, MQTT Broker)              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ├──── WebSocket Events ────┐
                 ├──── Device Registry ─────┤
                 └──── Zigbee2MQTT ─────────┤
                                            │
┌────────────────────────────────────────────────────────────┐
│                  HA-Ingestor Platform                       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Ingestion Layer                                      │ │
│  │  - WebSocket Ingestion Service                        │ │
│  │  - Event Normalization & Enrichment                   │ │
│  └──────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Storage Layer (Hybrid Architecture)                  │ │
│  │  - InfluxDB (time-series events)                      │ │
│  │  - SQLite (metadata: devices, entities, patterns)     │ │
│  └──────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  API Layer                                            │ │
│  │  - Data API (historical queries)                      │ │
│  │  - Admin API (system management)                      │ │
│  │  - AI Automation API (suggestions)                    │ │
│  └──────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  AI Intelligence Layer (NEW in v2.0)                  │ │
│  │  - Pattern Detection (Epic AI-1)                      │ │
│  │  - Device Intelligence (Epic AI-2)                    │ │
│  │  - Unified Daily Batch Job (3 AM)                     │ │
│  └──────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Enrichment Layer                                     │ │
│  │  - Weather API, Carbon Intensity, Air Quality         │ │
│  │  - Electricity Pricing, Calendar, Smart Meter         │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│                  Client Applications                        │
│  - Health Dashboard (React/TypeScript)                     │
│  - Home Assistant Automations (webhooks)                   │
│  - External Analytics Platforms (APIs)                     │
│  - Mobile Apps & Voice Assistants                          │
└────────────────────────────────────────────────────────────┘
```

---

## AI Intelligence Layer (v2.0)

### Unified Daily Batch Job

**Schedule:** 3 AM daily  
**Duration:** 7-15 minutes  
**Resource:** 200-400MB peak memory

```
┌──────────────────────────────────────────────────────────┐
│ Unified Daily AI Analysis (3 AM)                         │
│                                                           │
│ Phase 1: Device Capability Update (Epic AI-2)            │
│   - Query Zigbee2MQTT for device capabilities            │
│   - Update device_capabilities table                     │
│   Duration: 1-3 min                                      │
│                                                           │
│ Phase 2: Fetch Events (SHARED)                           │
│   - Query InfluxDB (last 30 days)                        │
│   - Used by BOTH pattern detection and feature analysis  │
│   Duration: 1-2 min                                      │
│                                                           │
│ Phase 3: Pattern Detection (Epic AI-1)                   │
│   - Time-of-day clustering (KMeans)                      │
│   - Co-occurrence detection                              │
│   - Anomaly detection                                    │
│   Duration: 2-3 min                                      │
│                                                           │
│ Phase 4: Feature Analysis (Epic AI-2)                    │
│   - Match devices to capabilities                        │
│   - Calculate utilization scores                         │
│   - Identify unused features                             │
│   Duration: 1-2 min                                      │
│                                                           │
│ Phase 5: Combined Suggestions (AI-1 + AI-2)              │
│   - Generate pattern suggestions (OpenAI)                │
│   - Generate feature suggestions (OpenAI)                │
│   - Unified ranking (top 10)                             │
│   Duration: 2-4 min                                      │
│                                                           │
│ Phase 6: Publish & Store                                 │
│   - Store suggestions in SQLite                          │
│   - Publish MQTT notification                            │
│   Duration: <1 min                                       │
└──────────────────────────────────────────────────────────┘
```

### Epic AI-1: Pattern Automation

**Purpose:** Analyze usage patterns to suggest time-based automations

**Components:**
- `TimeOfDayPatternDetector` - Finds consistent usage times
- `CoOccurrencePatternDetector` - Identifies devices used together
- `AnomalyDetector` - Spots repeated manual interventions

**Example Suggestions:**
- "Turn on bedroom light at 10:30 PM" (consistent daily pattern)
- "Turn on kitchen light when coffee maker starts" (co-occurrence)
- "Turn on porch light at 10 PM" (late arrival anomaly)

### Epic AI-2: Device Intelligence

**Purpose:** Discover device capabilities and suggest unused features

**Components:**
- `CapabilityParser` - Parses Zigbee2MQTT device definitions
- `FeatureAnalyzer` - Calculates utilization scores
- `FeatureSuggestionGenerator` - LLM-powered feature recommendations

**Example Suggestions:**
- "Enable LED notifications on your Inovelli switch"
- "Configure power monitoring on your smart plug"
- "Try double-tap actions on your dimmer"

**Supported Devices:** 6,000+ Zigbee device models from 100+ manufacturers

---

## Data Flow

### Event Ingestion

```
Home Assistant Event
  ↓
WebSocket Ingestion Service
  ↓
Event Normalization
  ↓
Enrichment Pipeline
  ├─→ Weather Data
  ├─→ Carbon Intensity
  ├─→ Electricity Pricing
  └─→ Other Sources
  ↓
Parallel Storage
  ├─→ InfluxDB (time-series)
  └─→ SQLite (metadata)
```

### AI Analysis Flow

```
Daily Trigger (3 AM)
  ↓
Device Capability Update
  ├─→ Query HA Device Registry
  ├─→ Query Zigbee2MQTT Bridge
  └─→ Update Capability Database
  ↓
Historical Data Fetch
  └─→ InfluxDB (last 30 days)
  ↓
Parallel Analysis
  ├─→ Pattern Detection (AI-1)
  │   ├─→ Time-of-day clustering
  │   ├─→ Co-occurrence mining
  │   └─→ Anomaly detection
  └─→ Feature Analysis (AI-2)
      ├─→ Device matching
      ├─→ Utilization calculation
      └─→ Opportunity identification
  ↓
Combined Suggestion Generation
  ├─→ OpenAI LLM (pattern suggestions)
  ├─→ OpenAI LLM (feature suggestions)
  └─→ Unified ranking
  ↓
Storage & Notification
  ├─→ SQLite (suggestions table)
  └─→ MQTT Notification
```

---

## Technology Stack

### Core Infrastructure
- **Docker Compose** - Service orchestration
- **Python 3.11+** - Backend services
- **TypeScript/React** - Frontend dashboard

### Data Storage
- **InfluxDB 2.x** - Time-series event storage
- **SQLite 3.45+** - Metadata storage (devices, patterns, suggestions)

### AI/ML Stack
- **scikit-learn 1.3+** - Pattern detection (KMeans, clustering)
- **pandas** - Data processing
- **OpenAI GPT-4o-mini** - LLM-powered suggestions

### APIs & Integration
- **FastAPI** - RESTful APIs
- **WebSocket** - Real-time event ingestion
- **MQTT** - Event-driven notifications
- **Zigbee2MQTT** - Device capability discovery

---

## Deployment Architecture

### Docker Services

```
services:
  - influxdb (time-series database)
  - data-api (historical queries)
  - admin-api (system management)
  - websocket-ingestion (event capture)
  - ai-automation-service (pattern + device intelligence)
  - health-dashboard (monitoring UI)
  - enrichment services:
    - weather-api
    - carbon-intensity-service
    - electricity-pricing-service
    - air-quality-service
    - calendar-service
    - smart-meter-service
```

### Resource Requirements

| Service | Memory | CPU | Storage |
|---------|--------|-----|---------|
| InfluxDB | 512MB | 0.5 | 5-10GB |
| AI Automation | 400MB peak | 0.3 | 100MB |
| WebSocket | 256MB | 0.2 | Minimal |
| Data API | 256MB | 0.2 | Minimal |
| Dashboard | 128MB | 0.1 | Minimal |
| Others | ~1GB total | 0.5 | Minimal |
| **Total** | **~2.5GB** | **1.8** | **5-10GB** |

---

## Architectural Decisions

### Hybrid Database (InfluxDB + SQLite)

**Rationale:**
- InfluxDB excels at time-series event storage and queries
- SQLite excels at metadata queries (devices, entities, patterns)
- Combination provides 5-10x faster queries vs InfluxDB-only

**Trade-offs:**
- Increased complexity (2 databases)
- Data consistency requirements
- Worth it for query performance gains

### Unified Daily Batch (Real-time → Batch)

**Rationale:**
- Device capabilities change monthly, not secondly
- Suggestions are batched daily anyway (3 AM → 7 AM)
- 99% resource reduction (2.5 hrs vs 730 hrs/month)

**Trade-offs:**
- Device discovery delayed by hours (vs immediate)
- Same user experience (suggestions at 7 AM regardless)
- Massive resource savings justify delay

### Single-Tenant Design

**Rationale:**
- Simplified architecture
- Lower resource usage
- Easier maintenance
- No multi-tenancy complexity

**Trade-offs:**
- Not suitable for SaaS
- Each home needs own deployment
- Acceptable for target use case

---

## Performance Characteristics

### Event Ingestion
- **Throughput:** 100-1000 events/sec
- **Latency:** <100ms end-to-end
- **Storage:** ~1GB per month (typical home)

### Query Performance
- **Device metadata:** <10ms (SQLite)
- **Historical events:** 50-200ms (InfluxDB)
- **Pattern detection:** 2-3 minutes (30-day analysis)

### AI Analysis
- **Daily batch:** 7-15 minutes
- **Suggestions generated:** 8-10 per day
- **OpenAI cost:** ~$0.003 per run (~$0.10/month)

---

## Security Architecture

### Authentication
- **Home Assistant:** Long-lived access token
- **APIs:** Internal network only (no public exposure)
- **Dashboard:** Network-level security

### Data Protection
- **No PII storage:** Device IDs and entity IDs only
- **Local deployment:** All data stays on user's network
- **No external dependencies:** Except OpenAI (anonymized data)

### Network Security
- **Docker network isolation**
- **No ports exposed publicly**
- **TLS for external APIs** (OpenAI, weather, etc.)

---

## Scalability

### Current Limits
- **Devices:** Tested up to 1,000 devices
- **Events:** 100K+ per month
- **Storage:** 5-10GB InfluxDB (6-month retention)

### Scaling Strategies
- **Horizontal:** Not applicable (single-tenant)
- **Vertical:** Add CPU/memory for larger homes
- **Data retention:** Adjust InfluxDB retention policies

---

## Monitoring & Observability

### Health Metrics
- Service health status
- WebSocket connection state
- Event ingestion rate
- Database performance
- AI analysis job status

### Alerting
- Service failures
- WebSocket disconnections
- Database errors
- AI job failures

### Logging
- Structured JSON logging
- Correlation IDs for request tracing
- Log aggregation (ELK stack support)

---

## Documentation

### Architecture Docs
- This document (overview)
- `docs/architecture-device-intelligence.md` (Epic AI-2 details)
- `docs/DOCKER_STRUCTURE_GUIDE.md` (Docker architecture)

### Implementation Docs
- `implementation/REALTIME_VS_BATCH_ANALYSIS.md` (Batch decision)
- `implementation/EPIC_AI1_VS_AI2_SUMMARY.md` (Epic comparison)
- `implementation/DATA_INTEGRATION_ANALYSIS.md` (Data flow)

### API Docs
- OpenAPI/Swagger at `/docs` (each service)
- `docs/prd.md` (API specifications)

---

**Last Updated:** 2025-10-16  
**Version:** 2.0.0  
**Status:** Production Ready ✅

