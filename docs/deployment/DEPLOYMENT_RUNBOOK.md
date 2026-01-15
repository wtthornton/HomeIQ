# HomeIQ Deployment Runbook

**Last Updated:** December 29, 2025  
**Status:** Active  
**Version:** 2.1

---

## Overview

This runbook provides step-by-step instructions for deploying HomeIQ to production, including pre-deployment checks, deployment procedures, and post-deployment verification.

**Note:** This runbook covers both automated (GitHub Actions) and manual deployment procedures. For automated deployments, see [Deployment Pipeline Documentation](./DEPLOYMENT_PIPELINE.md).

---

## HomeIQ Features and Services

### System Overview

HomeIQ is an AI-powered Home Assistant intelligence platform that captures, enriches, and stores Home Assistant events with multi-source data enrichment, providing real-time monitoring, advanced analytics, conversational AI automation, and production-ready deployment capabilities.

**Deployment Model:** Single NUC deployment - all 30+ microservices run on one machine, connecting to Home Assistant on the local network (typically `192.168.1.86:8123`).

### Core Features

#### 🤖 AI-Powered Automation
- **Conversational Automation Creation** - Create automations via natural language, no YAML required
- **Smart Pattern Detection** - AI discovers automation opportunities from usage patterns
- **Synergy Detection** - Multi-type synergy detection (device pairs, weather, energy, events)
- **Device Validation** - Intelligent device compatibility checking
- **Smart Recommendations** - Context-aware automation suggestions with priority scoring
- **Self-Healing YAML** - Automatic entity ID correction during refinement
- **Device-Specific Templates** - Pre-built automation templates for common device types

#### 📊 Data Management & Analytics
- **Real-time Event Capture** - Direct WebSocket connection to Home Assistant
- **Hybrid Database Architecture** - InfluxDB (time-series) + SQLite (metadata) for 5-10x faster queries
- **Multi-Source Data Enrichment** - Weather, energy pricing, air quality, sports, carbon intensity
- **Advanced Analytics** - Deep insights with spatial and temporal analysis
- **Data Export** - Multiple formats (CSV, JSON, PDF, Excel)
- **Data Retention** - Automated cleanup, compression, and backup

#### 🎨 User Interfaces
- **Health Dashboard** - Real-time system health monitoring (Port 3000)
- **AI Automation UI** - Interactive conversational interface (Port 3001)
- **Mobile Support** - Responsive design with touch gestures
- **Interactive Dependency Visualization** - Visual service dependency graphs

#### 🔌 Integrations & Enrichment
- **Weather Integration** - OpenWeatherMap API with caching
- **Energy Pricing** - Awattar API for electricity pricing
- **Carbon Intensity** - WattTime API for grid carbon intensity
- **Air Quality** - AirNow API for air quality data
- **Sports Data** - ESPN API for sports scores and schedules
- **Calendar Integration** - Home Assistant calendar entities
- **Smart Meter Integration** - SMETS2/P1 protocol support

#### 🚀 Deployment & Operations
- **Interactive Deployment Wizard** - Guided setup in 30-60 minutes
- **Connection Validator** - Pre-deployment testing and validation
- **Containerized Services** - Docker Compose deployment
- **Health Monitoring** - Comprehensive health checks and metrics
- **Log Aggregation** - Centralized logging across all services
- **OpenTelemetry Tracing** - Distributed tracing with Jaeger

---

### Services Deployed

HomeIQ deploys **38 microservices** (plus InfluxDB and Jaeger infrastructure) organized into the following categories:

#### 🗄️ Infrastructure Services

**1. InfluxDB (Port 8086)**
- **Purpose:** Time-series database for event storage
- **Why Deployed:** Primary data store for all Home Assistant events and time-series metrics
- **Features:**
  - High-performance time-series storage
  - Automatic data retention policies
  - Query API for historical data
  - Bucket: `home_assistant_events` (production), `home_assistant_events_test` (test)

**2. Jaeger (Ports 16686, 4317, 4318)**
- **Purpose:** Distributed tracing system
- **Why Deployed:** OpenTelemetry tracing for debugging and performance monitoring
- **Features:**
  - OTLP gRPC and HTTP receivers
  - Trace visualization UI
  - Service dependency mapping

#### 🔄 Core Data Services

**3. websocket-ingestion (Port 8001)**
- **Purpose:** Home Assistant WebSocket client and primary data ingestion
- **Why Deployed:** Captures all Home Assistant state changes in real-time
- **Features:**
  - Real-time WebSocket connection to Home Assistant
  - Automatic reconnection with exponential backoff
  - Event validation and normalization
  - Inline weather enrichment (15-minute cache)
  - Device/entity/area lookups (Epic 23.2)
  - Duration calculation (Epic 23.3)
  - Direct InfluxDB writes (Epic 31 - no enrichment-pipeline)
  - Batch processing (100 events/batch, 5s timeout)
- **Dependencies:** data-api (for device lookups), influxdb

**4. data-api (Port 8006)**
- **Purpose:** Unified query API for historical data
- **Why Deployed:** Single API endpoint for all data queries (events, devices, entities, sports)
- **Features:**
  - InfluxDB query interface
  - SQLite metadata queries (devices, entities, webhooks)
  - Sports data queries (from InfluxDB)
  - CORS support for frontend
  - Authentication support
- **Dependencies:** influxdb

**5. admin-api (Port 8004)**
- **Purpose:** System administration and control API
- **Why Deployed:** Administrative functions, Docker management, system configuration
- **Features:**
  - Docker container management
  - Service health monitoring
  - System configuration management
  - Integration management (MQTT, etc.)
  - JWT authentication
- **Dependencies:** influxdb, websocket-ingestion, data-api

#### 🎨 Frontend Services

**6. health-dashboard (Port 3000)**
- **Purpose:** System health monitoring dashboard
- **Why Deployed:** Real-time visualization of system health, service status, and metrics
- **Features:**
  - Service health monitoring
  - Real-time metrics display
  - Dependency visualization
  - Event statistics
  - Integration status
- **Dependencies:** admin-api

**7. ai-automation-ui (Port 3001)**
- **Purpose:** Conversational AI automation interface
- **Why Deployed:** User-facing interface for creating automations via natural language
- **Features:**
  - Conversational chat interface
  - Automation creation and editing
  - Synergy visualization
  - Device selection and mapping
  - Settings and configuration
- **Dependencies:** ai-core-service, ai-automation-service-new

#### 🤖 AI/ML Services

**8. ai-automation-service-new (Port 8036 → 8025)**
- **Purpose:** Main automation service orchestrator
- **Why Deployed:** Coordinates automation creation, validation, and execution
- **Features:**
  - Automation orchestration
  - YAML generation and validation
  - Integration with query, pattern, and validation services
- **Dependencies:** data-api, yaml-validation-service, ai-query-service, ai-pattern-service

**9. ai-core-service (Port 8018)**
- **Purpose:** AI orchestrator for ML services
- **Why Deployed:** Coordinates multiple AI/ML services (OpenVINO, ML, NER, OpenAI)
- **Features:**
  - Service orchestration
  - Request routing
  - Fallback handling
- **Dependencies:** openvino-service, ml-service, ner-service, openai-service

**10. openvino-service (Port 8026 → 8019)**
- **Purpose:** Optimized model inference (OpenVINO INT8)
- **Why Deployed:** High-performance embeddings and NER using optimized models
- **Features:**
  - Text embeddings (3 models)
  - Named Entity Recognition
  - OpenVINO INT8 optimization (1.5-2x speedup)
- **Resource Requirements:** 1.5GB memory, 2 CPUs

**11. ml-service (Port 8025 → 8020)**
- **Purpose:** Classical machine learning algorithms
- **Why Deployed:** Clustering, classification, and pattern analysis
- **Features:**
  - scikit-learn algorithms
  - Pattern clustering
  - Statistical analysis
- **Resource Requirements:** 512MB memory, 2 CPUs

**12. ner-service (Port 8031, internal)**
- **Purpose:** Named Entity Recognition model service
- **Why Deployed:** Entity extraction from natural language
- **Features:**
  - BERT-based NER model (dslim/bert-base-NER)
  - Entity extraction for automation creation
- **Resource Requirements:** 1GB memory, 2 CPUs

**13. openai-service (Port 8020)**
- **Purpose:** OpenAI API client service
- **Why Deployed:** Lightweight wrapper for OpenAI API calls
- **Features:**
  - OpenAI API integration
  - Request management
  - Error handling
- **Resource Requirements:** 256MB memory, 1 CPU

**14. ai-query-service (Port 8035 → 8018)**
- **Purpose:** Natural language query processing
- **Why Deployed:** Converts natural language queries to data API calls
- **Features:**
  - Query understanding
  - Device intelligence integration
  - Response caching
- **Dependencies:** data-api, device-intelligence-service

**15. ai-pattern-service (Port 8034 → 8020)**
- **Purpose:** Pattern detection and synergy analysis
- **Why Deployed:** Discovers automation opportunities from usage patterns
- **Features:**
  - Multi-type synergy detection
  - Pattern mining
  - Synergy statistics API
- **Dependencies:** data-api

**16. ai-training-service (Port 8033 → 8022)**
- **Purpose:** AI model training service
- **Why Deployed:** Trains soft prompts and fine-tunes models
- **Features:**
  - Soft prompt training
  - Model fine-tuning
  - Training job management
- **Dependencies:** ai_automation_data volume (shared database)

**17. device-intelligence-service (Port 8028 → 8019)**
- **Purpose:** Device capability intelligence
- **Why Deployed:** Provides device metadata, capabilities, and recommendations
- **Features:**
  - Device capability analysis
  - ML-based failure prediction
  - Graph Neural Networks for device relationships
  - Device recommendations
- **Dependencies:** influxdb

**18. automation-miner (Port 8029 → 8019)**
- **Purpose:** Community automation mining
- **Why Deployed:** Discovers and indexes automations from Home Assistant community
- **Features:**
  - Discourse forum crawling
  - GitHub automation discovery
  - Weekly refresh (Epic AI-4)
  - Automation corpus indexing
- **Resource Requirements:** 512MB memory, 1 CPU

**19. ha-ai-agent-service (Port 8030)**
- **Purpose:** Home Assistant AI agent
- **Why Deployed:** Conversational interface for Home Assistant control
- **Features:**
  - Natural language Home Assistant control
  - Device intelligence integration
  - Context-aware responses
- **Dependencies:** data-api, device-intelligence-service

**20. proactive-agent-service (Port 8031)**
- **Purpose:** Proactive automation suggestions
- **Why Deployed:** Suggests automations based on context (weather, sports, energy)
- **Features:**
  - Scheduled suggestions (default: 3 AM)
  - Context-aware recommendations
  - Weather, sports, and energy integration
- **Dependencies:** ha-ai-agent-service, data-api

**21. ai-code-executor (Port 8030, internal)**
- **Purpose:** Safe code execution for AI-generated code
- **Why Deployed:** Executes AI-generated Python code in sandboxed environment
- **Features:**
  - Sandboxed execution
  - Resource limits (memory, CPU)
  - Timeout protection
- **Dependencies:** data-api, ai-automation-service-new

#### 🌐 Data Enrichment Services

**22. weather-api (Port 8009)**
- **Purpose:** Weather data service
- **Why Deployed:** Provides weather context for events and automations
- **Features:**
  - OpenWeatherMap API integration
  - 15-minute cache
  - Location-based weather data
  - Direct InfluxDB writes (bucket: `weather_data`)
- **Dependencies:** influxdb
- **Profile:** production (excluded from test profile)

**23. carbon-intensity-service (Port 8010)**
- **Purpose:** Grid carbon intensity data
- **Why Deployed:** Provides carbon intensity for energy optimization
- **Features:**
  - WattTime API integration
  - Auto-refresh token management
  - Grid region configuration (default: CAISO_NORTH)
  - Direct InfluxDB writes
- **Dependencies:** influxdb
- **Profile:** production (excluded from test profile)

**24. electricity-pricing-service (Port 8011)**
- **Purpose:** Electricity pricing data
- **Why Deployed:** Provides real-time and forecasted electricity prices
- **Features:**
  - Awattar API integration
  - Pricing forecasts
  - Direct InfluxDB writes
- **Dependencies:** influxdb
- **Profile:** production (excluded from test profile)

**25. air-quality-service (Port 8012)**
- **Purpose:** Air quality data service
- **Why Deployed:** Provides air quality context for health-related automations
- **Features:**
  - AirNow API integration
  - Location-based AQI data
  - Direct InfluxDB writes
- **Dependencies:** influxdb
- **Profile:** production (excluded from test profile)

**26. calendar-service (Port 8013)**
- **Purpose:** Calendar event integration
- **Why Deployed:** Provides calendar events for event-based automation triggers
- **Features:**
  - Home Assistant calendar entity integration
  - Event fetching (default: 900s interval)
  - Direct InfluxDB writes
- **Dependencies:** influxdb
- **Profile:** production (excluded from test profile)

**27. smart-meter-service (Port 8014)**
- **Purpose:** Smart meter data integration
- **Why Deployed:** Provides real-time energy consumption data
- **Features:**
  - SMETS2/P1 protocol support
  - Home Assistant meter entity integration
  - Direct InfluxDB writes
- **Dependencies:** influxdb

#### ⚙️ Processing Services

**28. data-retention (Port 8080)**
- **Purpose:** Data lifecycle management
- **Why Deployed:** Automated cleanup, compression, and backup of time-series data
- **Features:**
  - Automated data cleanup (24h interval)
  - Data compression
  - Backup management
  - Monitoring and reporting
- **Dependencies:** influxdb

**29. energy-correlator (Port 8017)**
- **Purpose:** Energy correlation analysis
- **Why Deployed:** Correlates device events with energy consumption
- **Features:**
  - Device-energy correlation
  - Lookback analysis (default: 5 minutes)
  - Processing interval (default: 60s)
- **Dependencies:** influxdb, smart-meter-service

**30. log-aggregator (Port 8015)**
- **Purpose:** Centralized log aggregation
- **Why Deployed:** Collects and aggregates logs from all services
- **Features:**
  - Docker log collection
  - Log aggregation and search
  - Health endpoint for log service status
- **Dependencies:** Docker socket access

**31. ha-setup-service (Port 8027 → 8020)**
- **Purpose:** Home Assistant setup and monitoring
- **Why Deployed:** Monitors Home Assistant health and integration status
- **Features:**
  - HA health monitoring
  - Integration status checking
  - Performance monitoring
  - Environment health scoring
- **Dependencies:** data-api, admin-api

**32. yaml-validation-service (Port 8037)**
- **Purpose:** YAML validation and normalization
- **Why Deployed:** Validates and normalizes Home Assistant YAML configurations
- **Features:**
  - YAML syntax validation
  - Entity validation
  - Normalization
  - Validation levels (moderate, strict)
- **Dependencies:** data-api

#### 🔧 Device Services

**33. device-health-monitor (Port 8019)**
- **Purpose:** Device health monitoring
- **Why Deployed:** Monitors device health and status
- **Features:**
  - Device health tracking
  - Status monitoring
  - Health alerts

**34. device-context-classifier (Port 8032 → 8020)**
- **Purpose:** Device context classification
- **Why Deployed:** Classifies device context and usage patterns
- **Features:**
  - Context classification
  - Usage pattern analysis

**35. device-setup-assistant (Port 8021)**
- **Purpose:** Device setup assistance
- **Why Deployed:** Guides users through device setup
- **Features:**
  - Setup guidance
  - Configuration assistance

**36. device-database-client (Port 8022)**
- **Purpose:** Device database client
- **Why Deployed:** Provides device database API client functionality
- **Features:**
  - Device database access
  - Caching

**37. device-recommender (Port 8023)**
- **Purpose:** Device recommendations
- **Why Deployed:** Recommends devices based on usage patterns
- **Features:**
  - Device recommendations
  - Compatibility checking

#### 🧪 Test Services (Optional)

**38. home-assistant-test (Port 8124 → 8123)**
- **Purpose:** Test Home Assistant instance
- **Why Deployed:** Provides isolated test environment for development
- **Profile:** test (excluded from production)

**39. websocket-ingestion-test (Port 8002 → 8001)**
- **Purpose:** Test WebSocket ingestion service
- **Why Deployed:** Tests WebSocket ingestion with test Home Assistant
- **Profile:** test (excluded from production)

---

### Service Dependencies

**Critical Path:**
```
influxdb → data-api → websocket-ingestion → admin-api → health-dashboard
```

**AI Services Chain:**
```
openvino-service, ml-service, ner-service, openai-service
    ↓
ai-core-service
    ↓
ai-automation-service-new → ai-query-service, ai-pattern-service, yaml-validation-service
```

**Enrichment Services:**
```
weather-api, carbon-intensity-service, electricity-pricing-service, 
air-quality-service, calendar-service, smart-meter-service
    ↓
influxdb (direct writes)
```

---

### Resource Requirements

**Total System Resources (NUC):**
- **Memory:** ~8-10GB (all services)
- **CPU:** 4-8 cores recommended
- **Disk:** 50GB+ for data storage
- **Network:** Local network access to Home Assistant

**Service Resource Allocation:**
- **High Memory:** influxdb (512MB), openvino-service (1.5GB), ner-service (1GB)
- **High CPU:** ai-core-service (2 CPUs), openvino-service (2 CPUs), ml-service (2 CPUs)
- **Low Resource:** Most enrichment services (192MB, 0.5 CPU)

---

## Pre-Deployment Checklist

### 1. Environment Preparation

- [ ] Verify Docker and Docker Compose are installed
- [ ] Check available disk space (minimum 10GB free)
- [ ] Verify network connectivity
- [ ] Confirm all required environment variables are set

### 2. Configuration Verification

- [ ] Review `docker-compose.yml` configuration
- [ ] Verify environment files (`.env`, `infrastructure/env.production`)
- [ ] Check API keys and tokens are set (not default values)
- [ ] Verify Home Assistant URL and token
- [ ] Confirm InfluxDB credentials

### 3. Security Checks

- [ ] Run security audit: `python -m pytest services/*/tests/test_*security*.py -v`
- [ ] Verify no hardcoded credentials
- [ ] Check authentication is enabled on protected endpoints
- [ ] Review recent security fixes

### 4. Code Quality

- [ ] Run unit tests: `python scripts/simple-unit-tests.py`
- [ ] Check test coverage (target: >80% for critical services)
- [ ] Review and fix any critical linter errors
- [ ] Verify no critical bugs in issue tracker

---

## Deployment Methods

### Automated Deployment (Recommended)

**Use GitHub Actions workflow for automated deployments:**

1. **Push to main branch** or **create a tag** (`v*`)
2. **Quality gates run automatically:**
   - Tests must pass
   - Security scans must pass (no CRITICAL/HIGH vulnerabilities)
   - Code quality scores meet thresholds
   - Docker Compose config validation
3. **If gates pass, deployment starts automatically**
4. **Post-deployment validation runs:**
   - Health checks for all services
   - Database connectivity verification
   - Service dependency checks
5. **Notifications sent** (Slack, email, webhook)

**Manual Trigger:**
- Go to GitHub Actions → "Deploy to Production" → "Run workflow"

**See:** [Deployment Pipeline Documentation](./DEPLOYMENT_PIPELINE.md) for complete pipeline details.

### Manual Deployment

**Use this method for local deployments or when automation is unavailable:**

#### Step 1: Pre-Deployment Validation

```bash
# Run pre-deployment validation
python scripts/deployment/validate-deployment.py --pre-deployment
```

**Checks:**
- Docker Compose configuration
- Environment variables
- Service dependencies
- Resource limits

#### Step 2: Build Docker Images

```bash
# Build all services
docker compose build --parallel

# Or build specific service
docker compose build <service-name>
```

**Expected Time:** 5-15 minutes  
**Verification:** Check for build errors

#### Step 3: Start Services

```bash
# Start all services
docker compose up -d

# Or start specific service
docker compose up -d <service-name>
```

**Expected Time:** <1 minute  
**Verification:** Check container status

```bash
docker compose ps
```

**Important for Route Order Fixes:**
If you've modified FastAPI route definitions (e.g., `synergy_router.py`), use full container restart to ensure route registration order is correct:

```bash
# Full restart (recommended for route changes)
docker compose down <service-name>
docker compose up -d <service-name>

# Or for all services
docker compose down
docker compose up -d
```

**Note:** Using `docker compose restart` may not apply route order changes correctly. Use `down/up` for route modifications.

#### Step 4: Post-Deployment Validation

```bash
# Run post-deployment validation
python scripts/deployment/validate-deployment.py --post-deployment
```

**Checks:**
- Service connectivity
- Database connectivity
- Inter-service communication

#### Step 5: Verify Service Health

```bash
# Comprehensive health check (recommended)
bash scripts/deployment/health-check.sh

# Or use existing health check script
./scripts/check-service-health.sh

# Or check individual services
curl http://localhost:8001/health  # websocket-ingestion
curl http://localhost:8006/health  # data-api
curl http://localhost:8004/health  # admin-api
```

**Expected Result:** All critical services return HTTP 200

#### Step 6: Track Deployment

```bash
# Track deployment in database
python scripts/deployment/track-deployment.py \
  --deployment-id "deploy-$(date +%Y%m%d-%H%M%S)" \
  --status success \
  --commit $(git rev-parse HEAD) \
  --branch $(git branch --show-current)
```

---

## Post-Deployment Verification

### 1. Service Health Check

```bash
# Comprehensive health check (recommended)
bash scripts/deployment/health-check.sh

# JSON output for automation
bash scripts/deployment/health-check.sh --json > health-report.json

# Check critical services only
bash scripts/deployment/health-check.sh --critical-only

# Or use existing health check script
./scripts/check-service-health.sh --json > health-report.json
```

**Success Criteria:**
- All critical services healthy (HTTP 200)
- Response times < 500ms
- No connection errors
- All containers running

### 2. Functional Verification

**Test Event Ingestion:**
```bash
# Check websocket connection
curl http://localhost:8001/health

# Verify events in InfluxDB
curl "http://localhost:8006/api/v1/events?limit=5"
```

**Test Data API:**
```bash
# Test events endpoint
curl "http://localhost:8006/api/v1/events?limit=10"

# Test stats endpoint
curl "http://localhost:8006/api/v1/events/stats?period=1h"
```

**Test Dashboard:**
```bash
# Open dashboard in browser
open http://localhost:3000

# Verify dashboard loads and shows data
```

**Test Synergies API:**
```bash
# Test direct pattern service endpoint
curl http://localhost:8034/api/v1/synergies/stats

# Test via automation service proxy
curl http://localhost:8025/api/synergies/stats

# Test via frontend proxy (through nginx)
curl http://localhost:3001/api/synergies/stats

# Verify route order (should show /stats before /{synergy_id})
docker exec ai-pattern-service python3 -c "from src.main import app; from fastapi.routing import APIRoute; routes = [(r.path, r.endpoint.__name__ if hasattr(r, 'endpoint') else 'N/A') for r in app.routes if isinstance(r, APIRoute) and 'synerg' in r.path.lower()]; [print(f'{i+1}. {p:45} {h}') for i, (p, h) in enumerate(routes)]"
```

**Expected Results:**
- All endpoints return 200 OK with JSON statistics data
- Route order shows `/stats` before `/{synergy_id}`
- Frontend Synergies page loads without errors

### 3. Monitoring Setup

**Check Logs:**
```bash
# View service logs
docker-compose logs -f <service-name>

# Check for errors
docker-compose logs | grep -i error
```

**Monitor Health:**
```bash
# Set up periodic health checks (cron job)
*/5 * * * * /path/to/scripts/check-service-health.sh --json >> /var/log/homeiq-health.log
```

---

## Rollback Procedure

### Automatic Rollback

**Triggered automatically when:**
- Health checks fail after deployment
- Post-deployment validation fails

**Process:**
1. Health check failures detected
2. Rollback script automatically executes
3. Previous deployment images restored
4. Services restarted with previous configuration
5. Rollback verified
6. Rollback tracked and team notified

**No manual intervention required** - rollback happens automatically.

### Manual Rollback

**Use when automatic rollback fails or for manual deployments:**

#### Option 1: Rollback to Previous Deployment

```bash
# Rollback to previous successful deployment
bash scripts/deployment/rollback.sh --previous
```

#### Option 2: Rollback to Specific Deployment ID

```bash
# Rollback to specific deployment
bash scripts/deployment/rollback.sh --deployment-id <deployment-id>
```

#### Option 3: Rollback to Specific Tag

```bash
# Rollback to specific tag
bash scripts/deployment/rollback.sh --tag <tag>
```

#### Option 4: Manual Git Rollback

```bash
# Stop services
docker compose down

# Restore previous version
git checkout <previous-commit>

# Rebuild and restart
docker compose build
docker compose up -d

# Verify rollback
bash scripts/deployment/health-check.sh
```

### If Service Degrades

1. **Identify Failing Service:**
   ```bash
   bash scripts/deployment/health-check.sh
   docker compose ps
   ```

2. **Check Logs:**
   ```bash
   docker compose logs <service-name>
   ```

3. **Restart Service:**
   ```bash
   docker compose restart <service-name>
   ```

4. **If Persistent, Rollback:**
   - Use automated rollback script (recommended)
   - Or follow manual rollback procedure above

---

## Troubleshooting

### Service Won't Start

**Check:**
- Docker daemon running: `docker ps`
- Port conflicts: `netstat -an | grep <port>`
- Environment variables: `docker-compose config`
- Logs: `docker-compose logs <service-name>`

### Service Unhealthy

**Check:**
- Health endpoint: `curl http://localhost:<port>/health`
- Dependencies: Verify required services are running
- Configuration: Check environment variables
- Logs: Review service logs for errors

### Synergies API 404 Errors

**Problem:** `/api/synergies/stats` returns 404 Not Found

**Root Cause:** FastAPI route matching order - parameterized route matches before specific route

**Solution:**
1. Verify route order: `/stats` must be registered before `/{synergy_id}`
2. Use full container restart: `docker-compose down ai-pattern-service && docker-compose up -d ai-pattern-service`
3. Check route registration order in container:
   ```bash
   docker exec ai-pattern-service python3 -c "from src.main import app; from fastapi.routing import APIRoute; routes = [(r.path, r.endpoint.__name__) for r in app.routes if isinstance(r, APIRoute) and 'synerg' in r.path.lower()]; [print(f'{i+1}. {p}') for i, (p, _) in enumerate(routes)]"
   ```
4. Verify `/stats` appears before `/{synergy_id}` in route list

**Prevention:**
- Always define specific routes before parameterized routes in FastAPI
- Use full container restart (`down/up`) after route changes, not just `restart`
- Test route order after deployment

**See:** `implementation/SYNERGIES_API_FIX_COMPLETE.md` for complete fix details

### Nginx Proxy Issues (Dashboard)

**Common Issues:**

1. **502 Bad Gateway or Connection Closed**
   - **Cause:** Nginx proxy_pass configuration issue or service not running
   - **Check:** `docker logs homeiq-dashboard | grep -i error`
   - **Solution:** Verify service names and ports match docker-compose.yml

2. **"host not found in upstream" Error**
   - **Cause:** Nginx tries to resolve hostname at startup, but service isn't running
   - **Solution:** Use variable-based proxy_pass with resolver for optional services:
   ```nginx
   location /service-name/ {
       set $service "http://service-name:port";
       proxy_pass $service/;
       # Resolver already configured at server level
   }
   ```

3. **Proxy Returns Wrong Endpoint (Root Instead of Target)**
   - **Cause:** Variable-based proxy_pass not forwarding path correctly
   - **Solution:** Use direct proxy_pass for always-running services, or use upstream blocks:
   ```nginx
   # For always-running services
   location /api/integrations {
       proxy_pass http://data_api/api/integrations;
   }
   
   # For optional services (with resolver)
   location /weather/ {
       set $weather_service "http://weather-api:8009";
       proxy_pass $weather_service/;
   }
   ```

**Nginx Configuration Best Practices:**
- **Always-running services:** Use direct `proxy_pass` or upstream blocks
- **Optional services:** Use variable-based `proxy_pass` with resolver (allows nginx to start even if service isn't running)
- **Service name changes:** Update both docker-compose.yml and nginx.conf (e.g., `ai-automation-service` → `ai-automation-service-new`)
- **Port changes:** Verify internal ports match (e.g., `ai-automation-service-new` uses port 8025 internally, not 8018)

**Verification:**
```bash
# Test proxy endpoints
curl http://localhost:3000/setup-service/api/health/environment
curl http://localhost:3000/api/integrations
curl http://localhost:3000/log-aggregator/health
curl http://localhost:3000/ai-automation/health

# Check nginx config syntax
docker exec homeiq-dashboard nginx -t

# View nginx logs
docker logs homeiq-dashboard --tail 50
```

### Authentication Issues (401 Unauthorized)

**Dashboard Endpoints Requiring Public Access:**
- `/api/v1/config/integrations/mqtt` (GET/PUT) - MQTT configuration for dashboard
- `/api/v1/real-time-metrics` - Real-time metrics for dashboard display

**If Dashboard Shows "Authentication Required":**
1. Check admin-api service is running: `curl http://localhost:8004/health`
2. Verify endpoints are registered as public (no `dependencies=secure_dependency`)
3. Check frontend API calls include proper headers
4. Review `services/admin-api/src/main.py` router configuration

### Health Score Showing 0/100

**Cause:** Health scoring algorithm returns 0 when data is incomplete

**Fixed (December 2025):**
- HA Core "error/unknown" now scores 25 instead of 0
- Empty integrations list scores 30 instead of 0
- 0ms response time scores 80 instead of causing issues

**Verification:**
```bash
curl http://localhost:8027/api/health/environment
# Should return health_score > 0 even with partial data
```

### High Error Rate

**Check:**
- Service logs for error patterns
- Resource usage: `docker stats`
- Network connectivity
- Database connectivity (InfluxDB)

### Performance Issues

**Check:**
- Resource usage: `docker stats`
- Response times: `./scripts/check-service-health.sh`
- Database query performance
- Network latency

---

## Maintenance

### Regular Tasks

**Daily:**
- Review health check reports
- Monitor error logs
- Check service uptime

**Weekly:**
- Review service logs for issues
- Check disk space usage
- Verify backup procedures

**Monthly:**
- Review and update dependencies
- Check security updates
- Review performance metrics

### Updates

**Procedure:**
1. Review changelog
2. Test in staging environment
3. Backup current deployment
4. Deploy updates
5. Verify health
6. Monitor for issues

---

## Emergency Contacts

- **On-Call Engineer:** [Contact Info]
- **DevOps Team:** [Contact Info]
- **Security Team:** [Contact Info]

---

## Deployment Tracking

### View Deployment History

```bash
# List recent deployments
python scripts/deployment/track-deployment.py --list

# Show deployment metrics
python scripts/deployment/track-deployment.py --metrics
```

### Metrics Available

- Total deployments
- Success/failure rates
- Average deployment duration
- Rollback frequency
- Mean time to recovery (MTTR)
- Recent deployments (7 days)

## Notifications

### Automated Notifications

Deployments automatically send notifications to:
- **Slack** (if `SLACK_WEBHOOK_URL` configured)
- **Email** (if configured, for failures only)
- **Custom Webhook** (if `DEPLOYMENT_WEBHOOK_URL` configured)
- **GitHub Actions** (workflow summary)

### Manual Notifications

For manual deployments, notifications can be sent via:

```bash
# Send notification via workflow
gh workflow run deployment-notify.yml \
  -f deployment-id="deploy-$(date +%Y%m%d-%H%M%S)" \
  -f status="success" \
  -f commit=$(git rev-parse HEAD) \
  -f branch=$(git branch --show-current)
```

## References

- [Deployment Pipeline Documentation](./DEPLOYMENT_PIPELINE.md) - Complete pipeline architecture
- [Nginx Proxy Configuration Guide](./NGINX_PROXY_CONFIGURATION.md) - Detailed nginx proxy patterns and troubleshooting
- [Synergies API Deployment Notes](./SYNERGIES_API_DEPLOYMENT_NOTES.md) - Critical deployment notes for synergies API route fixes
- [Test Strategy](../testing/TEST_STRATEGY.md)
- [Security Audit](../security/SECURITY_AUDIT_REPORT.md)
- [Production Readiness Components](../architecture/production-readiness-components.md)
- [Troubleshooting Guide](../TROUBLESHOOTING_GUIDE.md)

---

**Maintainer:** DevOps Team  
**Review Frequency:** Quarterly  
**Last Review:** December 27, 2025

