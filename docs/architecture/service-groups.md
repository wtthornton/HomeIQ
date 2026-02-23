# Service Groups Architecture

**Last Updated:** February 23, 2026
**Status:** Active
**Epic Reference:** Service Group Decomposition (Phase 5)
**Approach:** Option C -- Criticality + Domain Hybrid (6 groups)

---

## Overview

HomeIQ's 50+ microservices are organized into **6 independently deployable groups** based on deployment criticality and domain boundaries. This structure enables independent scaling, faster CI/CD, clearer ownership, and blast-radius isolation.

| Group | Name | Services | Purpose | Deploy Cadence |
|-------|------|----------|---------|----------------|
| 1 | **core-platform** | 6 | Data backbone -- if down, everything is down | Low |
| 2 | **data-collectors** | 8 | Stateless data fetchers from external APIs | Medium |
| 3 | **ml-engine** | 9 + model-prep | ML model inference, embeddings, training | Frequent |
| 4 | **automation-intelligence** | 16 | Automation generation, suggestion, validation | High |
| 5 | **device-management** | 8 | Device lifecycle, health, onboarding | Medium |
| 6 | **frontends** | 3 + infra | User-facing UIs and observability tooling | High |

---

## Dependency Graph

```
                    +------------------------------+
                    |   Group 1: core-platform     |
                    | (InfluxDB, data-api,         |
                    |  websocket, admin, dashboard, |
                    |  data-retention)              |
                    +---------------+--------------+
                                    |
          +-------------------------+-------------------------+
          |                         |                         |
          v                         v                         v
  +----------------+     +-------------------+     +-------------------+
  | Group 2:       |     | Group 3:          |     | Group 5:          |
  | data-          |     | ml-engine         |     | device-           |
  | collectors     |     | (ai-core,         |     | management        |
  | (weather,      |     |  openvino, ML,    |     | (health, setup,   |
  |  smart-meter,  |     |  NER, OpenAI,     |     |  classifier,      |
  |  sports, etc)  |     |  RAG, training)   |     |  activity)        |
  +----------------+     +---------+---------+     +-------------------+
                                   |
                                   v
                    +------------------------------+
                    | Group 4: automation-         |
                    | intelligence                 |
                    | (ha-ai-agent,                |
                    |  ai-automation,              |
                    |  patterns, blueprints,       |
                    |  energy, traces)             |
                    +---------------+--------------+
                                    |
                                    v
                    +------------------------------+
                    | Group 6: frontends           |
                    | (ai-automation-ui,           |
                    |  observability,              |
                    |  jaeger)                     |
                    +------------------------------+
```

**Key property:** No circular dependencies. Every arrow points downward from core-platform. Groups 2, 3, and 5 are siblings with no inter-dependency. Group 4 depends on Group 3 for ML inference. Group 6 depends on Groups 1 and 4.

---

## Group 1: core-platform (6 services)

**Purpose:** The data backbone. If this is down, everything is down. Deployed rarely, tested heavily, always-on high availability.

| Service | Port | Role |
|---------|------|------|
| influxdb | 8086 | Time-series database -- all sensor/event data |
| data-api | 8006 | Central query hub -- every service reads through this |
| websocket-ingestion | 8001 | Primary HA event capture, direct InfluxDB writer |
| admin-api | 8004 | System control plane, health checks, config |
| health-dashboard | 3000 | Primary user UI (React/Vite) |
| data-retention | 8080 | Data lifecycle -- cleanup, compression, rotation |

**Compose file:** `domains/core-platform/compose.yml`
**Env file:** `domains/core-platform/compose.env.example`
**Depends on:** Nothing (root of dependency tree)
**Depended on by:** All other groups

**Volumes:**
- `influxdb_data` -- InfluxDB persistent storage
- `data_api_sqlite` -- SQLite metadata database
- `data_retention_data` -- Retention state

**Key environment variables:**
- `INFLUXDB_TOKEN`, `INFLUXDB_ORG`, `INFLUXDB_BUCKET`
- `HA_WS_URL`, `HA_TOKEN` (for websocket-ingestion)
- `DATABASE_URL` (SQLite path for data-api)
- `API_KEY` (Bearer auth for data-api)

**Deploy commands:**
```bash
# Start core platform only
docker compose -f domains/core-platform/compose.yml up -d

# Rebuild and start
docker compose -f domains/core-platform/compose.yml up -d --build

# View logs
docker compose -f domains/core-platform/compose.yml logs -f

# Health check
curl http://localhost:8086/health   # InfluxDB
curl http://localhost:8006/health   # data-api
curl http://localhost:8001/health   # websocket-ingestion
curl http://localhost:8004/health   # admin-api
curl http://localhost:3000          # health-dashboard
curl http://localhost:8080/health   # data-retention
```

---

## Group 2: data-collectors (8 services)

**Purpose:** Stateless data fetchers. Each service polls an external API on a schedule and writes to InfluxDB. Independently restartable, no cross-dependencies.

| Service | Port | External Source |
|---------|------|-----------------|
| weather-api | 8009 | OpenWeatherMap |
| smart-meter-service | 8014 | Home Assistant power entities |
| sports-api | 8005 | ESPN / HA Team Tracker |
| air-quality-service | 8012 | OpenWeatherMap AQI |
| carbon-intensity-service | 8010 | WattTime |
| electricity-pricing-service | 8011 | Energy pricing provider |
| calendar-service | 8013 | HA calendar entities |
| log-aggregator | 8015 | Docker socket / service logs |

**Compose file:** `domains/data-collectors/compose.yml`
**Env file:** `domains/data-collectors/compose.env.example`
**Depends on:** Group 1 (influxdb write, data-api metadata)
**Depended on by:** Groups 3, 4 (indirect -- via InfluxDB data)

**Pattern:** Every service follows the same data flow:
```
Scheduled fetch --> transform --> InfluxDB write
```

**Key environment variables:**
- `OPENWEATHERMAP_API_KEY` (weather-api, air-quality)
- `WATTTIME_USERNAME`, `WATTTIME_PASSWORD` (carbon-intensity)
- `INFLUXDB_URL`, `INFLUXDB_TOKEN` (all services)

**Resource profile:** Lightweight, stateless, low memory (128-256MB each)

**Deploy commands:**
```bash
# Start all collectors
docker compose -f domains/data-collectors/compose.yml up -d

# Start a single collector
docker compose -f domains/data-collectors/compose.yml up -d weather-api

# Restart a failing collector (no impact on others)
docker compose -f domains/data-collectors/compose.yml restart smart-meter-service

# Health checks
for port in 8009 8014 8005 8012 8010 8011 8013 8015; do
  echo "Port $port: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:$port/health)"
done
```

---

## Group 3: ml-engine (9 services + model-prep)

**Purpose:** All ML model inference, embedding generation, and training. Heaviest compute requirements (GPU/high memory). Changes driven by model updates, not feature work.

| Service | Port | Role |
|---------|------|------|
| ai-core-service | 8018 | ML orchestrator -- routes to inference backends |
| openvino-service | 8026 | Transformer embeddings, semantic search, reranking |
| ml-service | 8025 | Classical ML -- clustering, anomaly detection |
| ner-service | (internal 8031) | BERT-based Named Entity Recognition |
| openai-service | 8020 | OpenAI API client wrapper (GPT-5.2-codex) |
| rag-service | 8027 | Retrieval-Augmented Generation + vector search |
| ai-training-service | 8033 | Soft prompt training, model fine-tuning |
| device-intelligence-service | 8028 | 6,000+ device capability mapping (ML models) |
| model-prep | (one-shot) | HuggingFace model download/cache |

**Compose file:** `domains/ml-engine/compose.yml`
**Env file:** `domains/ml-engine/compose.env.example`
**Depends on:** Group 1 (data-api for entity/device metadata)
**Depended on by:** Group 4 (automation calls ML for inference), Group 5 (device classification)

**Internal dependency chain:**
```
openvino-service (embeddings)
        |
ml-service (classical ML)
        |
ner-service (NER)            --> ai-core-service (orchestrator)
        |
openai-service (LLM)
```

**Volumes:**
- `ai_automation_models` -- Shared model cache (populated by model-prep)
- `ai_automation_data` -- Training data and fine-tuned models

**Key environment variables:**
- `OPENAI_API_KEY` (openai-service)
- `MODEL_CACHE_DIR` (model-prep, openvino-service)
- `INFLUXDB_URL`, `INFLUXDB_TOKEN` (device-intelligence)

**Resource profile:** GPU-capable, high memory (512MB-1.5GB per service), CPU-intensive

**Deploy commands:**
```bash
# Start ML engine
docker compose -f domains/ml-engine/compose.yml up -d

# Pre-download models first (recommended on first deploy)
docker compose -f domains/ml-engine/compose.yml run model-prep

# Rebuild after model library upgrade
docker compose -f domains/ml-engine/compose.yml up -d --build openvino-service ml-service

# Health checks
curl http://localhost:8018/health   # ai-core-service
curl http://localhost:8026/health   # openvino-service
curl http://localhost:8025/health   # ml-service
curl http://localhost:8028/health   # device-intelligence-service
```

---

## Group 4: automation-intelligence (16 services)

**Purpose:** Everything related to automation generation, suggestion, validation, and deployment. The feature-richest group -- most active development happens here.

| Service | Port | Role |
|---------|------|------|
| ha-ai-agent-service | 8030 | HA AI agent -- context building, entity resolution, GUI automation path |
| ai-automation-service-new | 8036 | Core automation engine -- NL to YAML (CLI path) |
| ai-query-service | 8035 | Natural language query interface |
| ai-pattern-service | 8034 | Pattern detection, synergy analysis |
| ai-code-executor | (internal) | Safe code execution sandbox |
| automation-miner | 8029 | Community automation crawler (Discourse/GitHub) |
| automation-linter | 8016 | YAML validation and linting |
| yaml-validation-service | 8037 | Unified schema/entity/service validation |
| blueprint-index | 8038 | Blueprint metadata indexing and search |
| blueprint-suggestion-service | 8039 | Automation suggestions based on user devices |
| rule-recommendation-ml | 8040 | ML-powered automation recommendations |
| api-automation-edge | 8041 | Edge computing for API-driven automations |
| proactive-agent-service | 8031 | Proactive recommendations and suggestions |
| energy-correlator | 8017 | Device-power causality analysis |
| energy-forecasting | 8042 | 7-day energy consumption predictions |
| automation-trace-service | 8044 | HA automation trace + logbook ingestion |

**Compose file:** `domains/automation-core/compose.yml`
**Env file:** `domains/automation-core/compose.env.example`
**Depends on:** Group 1 (data-api), Group 3 (ML inference via ai-core-service)
**Depended on by:** Group 6 (frontends display automation results)

**Internal dependency chain:**
```
ha-ai-agent-service
    +-> ai-automation-service-new --> yaml-validation-service
    +-> ai-query-service
    +-> ai-pattern-service
    +-> proactive-agent-service

blueprint-suggestion-service --> blueprint-index
                             --> ai-pattern-service
```

**Key environment variables:**
- `HA_URL`, `HA_TOKEN` (ha-ai-agent, proactive-agent)
- `DATA_API_URL`, `DATA_API_KEY` (all services)
- `OPENAI_API_KEY` (ha-ai-agent, ai-automation-service-new)

**Resource profile:** Medium, CPU-bound (256MB-512MB each)

**Deploy commands:**
```bash
# Start automation intelligence
docker compose -f domains/automation-core/compose.yml up -d

# Rebuild a specific service after code change
docker compose -f domains/automation-core/compose.yml up -d --build ai-pattern-service

# Health checks
curl http://localhost:8030/health   # ha-ai-agent-service
curl http://localhost:8036/health   # ai-automation-service-new
curl http://localhost:8034/health   # ai-pattern-service
curl http://localhost:8016/health   # automation-linter
```

---

## Group 5: device-management (8 services)

**Purpose:** Device lifecycle -- health monitoring, onboarding, classification, activity recognition. Medium churn, independent of automation features.

| Service | Port | Role |
|---------|------|------|
| device-health-monitor | 8019 | Device health tracking, battery monitoring |
| device-context-classifier | 8032 | Room/location inference |
| device-setup-assistant | 8021 | Guided device onboarding |
| device-database-client | 8022 | Device data access layer + caching |
| device-recommender | 8023 | Device upgrade suggestions |
| activity-recognition | 8043 | LSTM/ONNX user activity detection |
| activity-writer | 8045 | Periodic activity prediction pipeline |
| ha-setup-service | 8024 | HA health checks, integration monitoring |

**Compose file:** `domains/device-management/compose.yml`
**Env file:** `domains/device-management/compose.env.example`
**Depends on:** Group 1 (data-api), Group 3 (device-intelligence-service for classification)
**Depended on by:** Group 4 (automation uses device context)

**Key environment variables:**
- `HA_URL`, `HA_TOKEN` (ha-setup-service)
- `DATA_API_URL`, `DATA_API_KEY` (all services)

**Resource profile:** Low-medium (128-512MB each)

**Deploy commands:**
```bash
# Start device management
docker compose -f domains/device-management/compose.yml up -d

# Health checks
curl http://localhost:8019/health   # device-health-monitor
curl http://localhost:8024/health   # ha-setup-service
curl http://localhost:8043/health   # activity-recognition
```

---

## Group 6: frontends (3 services + infra)

**Purpose:** User-facing UIs and observability tooling. Fast iteration, independent build pipelines (Node/React vs Python).

| Service | Port | Role |
|---------|------|------|
| ai-automation-ui | 3001 | AI automation web UI (React) |
| observability-dashboard | 8501 | Monitoring dashboard (Streamlit) |
| jaeger | 16686 | Distributed tracing UI |

**Compose file:** `domains/frontends/compose.yml`
**Env file:** `domains/frontends/compose.env.example`
**Depends on:** Group 1 (admin-api, data-api), Group 4 (automation endpoints)

**Note:** `health-dashboard` is developed with frontends but deployed with core-platform (Group 1) for availability. It appears only in `domains/core-platform/compose.yml`.

**Key environment variables:**
- `API_BASE_URL` (frontend API target)
- `VITE_*` (Vite build-time variables)

**Resource profile:** Lightweight, CDN-friendly static assets

**Deploy commands:**
```bash
# Start frontends
docker compose -f domains/frontends/compose.yml up -d

# Health checks
curl http://localhost:3001          # ai-automation-ui
curl http://localhost:16686         # jaeger UI
curl http://localhost:8501/health   # observability-dashboard
```

---

## Cross-Group Communication Patterns

### Allowed Communication

```
+-------------------+      +-------------------+      +-----------------+
|  Any Group        | ---> |  core-platform    | ---> |  InfluxDB       |
|  (HTTP client)    |      |  (data-api:8006)  |      |  (direct write) |
+-------------------+      +-------------------+      +-----------------+

+-------------------+      +-------------------+
|  automation-      | ---> |  ml-engine        |
|  intelligence     |      |  (ai-core:8018)   |
+-------------------+      +-------------------+

+-------------------+      +-------------------+
|  frontends        | ---> |  automation-      |
|  (ai-auto-ui)     |      |  intelligence     |
+-------------------+      +-------------------+
```

### Communication Rules

1. **All groups may call core-platform** (data-api for queries, InfluxDB for writes)
2. **automation-intelligence calls ml-engine** for AI inference via ai-core-service
3. **frontends call automation-intelligence** for automation features
4. **data-collectors are independent** -- no service-to-service calls between collectors
5. **No circular dependencies** -- communication flows downward from core-platform

### Resilience at Group Boundaries

All cross-group HTTP calls use `libs/homeiq-resilience/CrossGroupClient` with circuit breakers, automatic retries with exponential backoff, Bearer auth, and OTel trace propagation. See [libs/homeiq-resilience/README.md](../../libs/homeiq-resilience/README.md) for full documentation.

**Resilience rollout status (February 2026):**

| Service | Group | Cross-Group Targets | Circuit Breakers |
|---------|-------|-------------------|-----------------|
| ha-ai-agent-service | G4 | data-api (G1), device-intelligence (G3) | `core-platform`, `ml-engine` |
| blueprint-suggestion-service | G4 | data-api (G1) | `core-platform` |
| ai-pattern-service | G4 | data-api (G1) | `core-platform` |
| ai-automation-service-new | G4 | data-api (G1) | `core-platform` |
| proactive-agent-service | G4 | data-api (G1), weather-api (G2) | `core-platform`, `data-collectors` |
| device-health-monitor | G5 | data-api (G1), device-intelligence (G3) | `core-platform`, `ml-engine` |

**Degradation behavior:**

| Caller Group | Upstream Group | Behavior When Upstream Down |
|-------------|----------------|----------------------------|
| automation-intelligence | ml-engine | Rule-based fallback, cached embeddings |
| automation-intelligence | core-platform | Circuit opens after 5 failures; returns empty results (events=`[]`, entities=`[]`) |
| device-management | ml-engine | Skip ML classification, return `None` |
| device-management | core-platform | Circuit opens; returns empty entities/devices |
| frontends | automation-intelligence | Show "AI features temporarily unavailable" |
| data-collectors | core-platform | **Fatal** -- buffer to disk, retry on recovery |

**Health endpoint format** (all cross-group callers):
```json
{
  "status": "healthy",
  "group": "automation-intelligence",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "dependencies": {
    "data-api": { "status": "healthy", "latency_ms": 12 }
  }
}
```

**Alerting severity matrix** (documented in `libs/homeiq-resilience/README.md`):

| Group | Severity | Response Time |
|-------|----------|--------------|
| core-platform | P1 (page) | Immediate |
| ml-engine | P2 (alert) | 5 min |
| automation-intelligence | P2 (alert) | 5 min |
| data-collectors | P3 (notify) | 15 min |
| device-management | P3 (notify) | 10 min |
| frontends | P3 (notify) | 10 min |

---

## Deployment Combinations

### Common deployment profiles:

```bash
# Full stack (all groups)
docker compose up -d

# Core only (minimal system -- data pipeline + dashboard)
docker compose -f domains/core-platform/compose.yml up -d

# Core + collectors (data pipeline with enrichment)
docker compose -f domains/core-platform/compose.yml -f domains/data-collectors/compose.yml up -d

# Core + ML + automation (AI features without device management)
docker compose -f domains/core-platform/compose.yml -f domains/ml-engine/compose.yml -f domains/automation-core/compose.yml up -d

# Core + devices (device management without AI)
docker compose -f domains/core-platform/compose.yml -f domains/device-management/compose.yml up -d

# Core + all backends (everything except frontends)
docker compose -f domains/core-platform/compose.yml -f domains/data-collectors/compose.yml \
  -f domains/ml-engine/compose.yml -f domains/automation-core/compose.yml -f domains/device-management/compose.yml up -d
```

### Startup order (recommended):

```
1. core-platform     (must be first -- provides InfluxDB, data-api)
2. data-collectors   (can start in parallel with groups 3, 5)
3. ml-engine         (can start in parallel with groups 2, 5)
4. device-management (can start in parallel with groups 2, 3)
5. automation-intelligence (after ml-engine is healthy)
6. frontends         (after automation-intelligence is healthy)
```

---

## Network Architecture

All groups share a single Docker network for inter-group communication:

```yaml
# Defined in domains/core-platform/compose.yml
networks:
  homeiq-network:
    name: homeiq-network

# Referenced in all other group compose files
networks:
  homeiq-network:
    external: true
```

This allows:
- Services in different groups to communicate via Docker DNS
- Groups to be started and stopped independently
- No impact on other groups when one group is restarted

---

## Compose File Structure

```
domains/
  core-platform/
    compose.yml              # Group 1: core-platform services
    compose.env.example      # Environment template for core
  data-collectors/
    compose.yml              # Group 2: data-collectors services
    compose.env.example      # Environment template for collectors
  ml-engine/
    compose.yml              # Group 3: ml-engine services
    compose.env.example      # Environment template for ML
  automation-core/
    compose.yml              # Group 4: automation-intelligence services
    compose.env.example      # Environment template for automation
  device-management/
    compose.yml              # Group 5: device-management services
    compose.env.example      # Environment template for devices
  frontends/
    compose.yml              # Group 6: frontend services
    compose.env.example      # Environment template for frontends

docker-compose.yml           # Root file -- includes all 6 group files
```

---

## Related Documentation

- [Services Ranked by Importance](./SERVICES_RANKED_BY_IMPORTANCE.md) -- Service tier classification with group assignments
- [Architecture Quick Reference](./README_ARCHITECTURE_QUICK_REF.md) -- Service patterns and port reference
- [Deployment Runbook](../deployment/DEPLOYMENT_RUNBOOK.md) -- Per-group deployment procedures
- [Event Flow Architecture](./event-flow-architecture.md) -- Data flow with group boundary annotations
- [Service Decomposition Plan](../planning/service-decomposition-plan.md) -- Full implementation plan

---

**Maintained by:** HomeIQ DevOps Team
**Last Updated:** February 23, 2026
