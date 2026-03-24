# Service Groups Architecture

**Last Updated:** March 23, 2026
**Status:** Active
**Epic Reference:** Domain Architecture Restructuring (Epics 1-5 Complete)
**Approach:** 9-domain structure (extended from Option C -- Criticality + Domain Hybrid)
**AI Classification:** See [AI/Agent Service Classification](ai-agent-classification.md) for tier labels (T1-T4) and [ADR: Single Agent Architecture](adr-single-agent-architecture.md)

---

## Overview

HomeIQ is organized into **9 independently deployable domain groups** under `domains/`. The nine-group layout split the former `automation-intelligence` domain into **automation-core**, **blueprints**, **energy-analytics**, and **pattern-analysis**.

**Counts:** There are **62** `services:` entries across the nine `domains/*/compose.yml` files. With **`--profile production`** (as used by `scripts/start-stack.sh` / `start-stack.ps1`), **~58 containers** run: exclude `development` (e.g. `ha-simulator`, one-shot `model-prep`) and `test` (`home-assistant-test`, `websocket-ingestion-test`). See [Deployment Quick Reference](../deployment/DEPLOYMENT_QUICK_REFERENCE.md).

| # | Domain | Services (production profile) | Compose definitions | Purpose | Deploy Cadence |
|---|--------|------------------------------|---------------------|---------|----------------|
| 1 | **core-platform** | 11 | 14 | Data backbone + observability stack | Low |
| 2 | **data-collectors** | 10 | 10 | External API fetchers + Zeek network pipeline | Medium |
| 3 | **ml-engine** | 8 | 9 | ML inference and training (`model-prep` = dev one-shot) | Frequent |
| 4 | **automation-core** | 8 | 8 | NL to YAML, validation, traces, device control | High |
| 5 | **blueprints** | 4 | 4 | Blueprint discovery and ML recommendations | Medium |
| 6 | **energy-analytics** | 3 | 3 | Energy intelligence, forecasting, proactive agent | Medium |
| 7 | **device-management** | 8 | 8 | Device lifecycle, health, activity recognition | Medium |
| 8 | **pattern-analysis** | 2 | 2 | Pattern detection, api-automation-edge | Low |
| 9 | **frontends** | 4 | 4 | Jaeger, observability UI, AI UI, voice-gateway | High |

**Note:** **health-dashboard** (:3000) is defined only under **core-platform**, not under `frontends/compose.yml`.

---

## Dependency Graph

```
                         ┌────────────────────────┐
                         │  1. core-platform (11) │
                         └──────────┬─────────────┘
                                    │
         ┌──────────────┬───────────┼──────────────┐
         │              │           │              │
         ▼              ▼           ▼              ▼
  2. data-        3. ml-engine  7. device-   8. pattern-
  collectors (10)   (8)        mgmt (8)     analysis (2)
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
   4. automation- 5. blue-  6. energy-
     core (8)     prints(4) analytics(3)
          │
          ▼
     9. frontends (4)
```

**Key property:** No circular dependencies. Every arrow points downward from core-platform. Domains 2, 3, 7, and 8 are siblings with no inter-dependency. Domains 4, 5, and 6 depend on domain 3 for ML inference. Domain 9 depends on domains 1 and 4.

---

## Group 1: core-platform (11 services with `--profile production`)

**Purpose:** The data backbone. If this is down, everything is down. Includes PostgreSQL metadata, the health dashboard, and the Prometheus/Grafana/Alertmanager stack. Deployed rarely, tested heavily, always-on high availability.

| Service | Port | Role |
|---------|------|------|
| influxdb | 8086 | Time-series database -- all sensor/event data |
| postgres | 5432 | PostgreSQL 17 -- metadata, schema-per-domain |
| data-api | 8006 | Central query hub -- every service reads through this |
| websocket-ingestion | 8001 | Primary HA event capture, direct InfluxDB writer |
| admin-api | 8004 | System control plane, health checks, config |
| health-dashboard | 3000 | Primary user UI (React/Vite) |
| data-retention | 8080 | Data lifecycle -- cleanup, compression, rotation |
| alertmanager | 9093 | Alert routing (Prometheus) |
| prometheus | 9090 | Metrics collection and alerting rules |
| grafana | 3002 | Dashboards (maps host 3002 → container 3000) |
| postgres-exporter | 9187 | PostgreSQL metrics for Prometheus |

**Also in compose (not production profile):** `ha-simulator` (`development`), `home-assistant-test` + `websocket-ingestion-test` (`test`).

**Compose file:** `domains/core-platform/compose.yml`
**Env file:** `domains/core-platform/compose.env.example`
**Depends on:** Nothing (root of dependency tree)
**Depended on by:** All other groups

**Volumes:**
- `influxdb_data` / `influxdb_config` -- InfluxDB persistent storage
- `postgres_data` -- PostgreSQL metadata database
- `prometheus_data` / `grafana_data` -- Monitoring stack
- `data_retention_backups` -- Retention / backup state

**Key environment variables:**
- `INFLUXDB_TOKEN`, `INFLUXDB_ORG`, `INFLUXDB_BUCKET`
- `HA_WS_URL`, `HA_TOKEN` (for websocket-ingestion)
- `DATABASE_URL` (PostgreSQL URL for data-api)
- `API_KEY` (Bearer auth for data-api)

**Deploy commands:**
```bash
# Start core platform only (includes monitoring stack)
docker compose -f domains/core-platform/compose.yml --profile production up -d

# Rebuild and start
docker compose -f domains/core-platform/compose.yml --profile production up -d --build

# View logs
docker compose -f domains/core-platform/compose.yml logs -f

# Health check
curl http://localhost:8086/health   # InfluxDB
curl http://localhost:8006/health   # data-api
curl http://localhost:8001/health   # websocket-ingestion
curl http://localhost:8004/health   # admin-api
curl http://localhost:3000          # health-dashboard
curl http://localhost:8080/health   # data-retention
curl http://localhost:9090/-/healthy  # prometheus
curl http://localhost:3002/api/health # grafana (host port)
```

---

## Group 2: data-collectors (10 services)

**Purpose:** Stateless data fetchers plus optional Zeek network visibility. Collectors poll external APIs (or HA) on a schedule and write to InfluxDB. **air-quality**, **carbon-intensity**, **electricity-pricing**, and **calendar** require Compose **`--profile production`** (enabled by `start-stack`).

| Service | Port | External Source |
|---------|------|-----------------|
| weather-api | 8009 | OpenWeatherMap |
| smart-meter | 8014 | Home Assistant power entities |
| sports-api | 8005 | ESPN / HA Team Tracker |
| air-quality | 8012 | OpenWeatherMap AQI |
| carbon-intensity | 8010 | WattTime |
| electricity-pricing | 8011 | Energy pricing provider (e.g. Awattar) |
| calendar | 8013 | HA calendar entities |
| log-aggregator | 8015 | Docker socket / service logs |
| zeek | (host network) | Packet capture / Zeek logs |
| zeek-network-service | 8048 | Zeek log parser → InfluxDB / data-api |

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
# Start all collectors (include profile-gated services)
docker compose -f domains/data-collectors/compose.yml --profile production up -d

# Start a single collector
docker compose -f domains/data-collectors/compose.yml --profile production up -d weather-api

# Restart a failing collector (no impact on others)
docker compose -f domains/data-collectors/compose.yml restart smart-meter

# Health checks
for port in 8009 8014 8005 8012 8010 8011 8013 8015; do
  echo "Port $port: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:$port/health)"
done
```

---

## Group 3: ml-engine (8 running + 1 dev one-shot)

**Purpose:** ML model inference, embedding generation, and training. Heaviest compute requirements (GPU/high memory). Changes driven by model updates, not feature work.

| Service | Port | Role |
|---------|------|------|
| ai-core-service | 8018 | ML orchestrator -- routes to inference backends |
| openvino-service | 8026 | Transformer embeddings, semantic search, reranking |
| ml-service | 8025 | Classical ML -- clustering, anomaly detection |
| ner-service | 8031 | BERT-based Named Entity Recognition |
| openai-service | 8020 | OpenAI API client wrapper |
| rag-service | 8027 | Retrieval-Augmented Generation + vector search |
| ai-training-service | 8033 | Soft prompt training, model fine-tuning |
| device-intelligence-service | 8028 | Device capability mapping (ML models) |
| model-prep | (one-shot) | HuggingFace model download/cache -- **`profiles: [development]`** only |

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
# Start ML engine (production runtime services)
docker compose -f domains/ml-engine/compose.yml --profile production up -d

# Pre-download models first (recommended on first deploy; development profile)
docker compose -f domains/ml-engine/compose.yml --profile development run --rm model-prep

# Rebuild after model library upgrade
docker compose -f domains/ml-engine/compose.yml --profile production up -d --build openvino-service ml-service

# Health checks
curl http://localhost:8018/health   # ai-core-service
curl http://localhost:8026/health   # openvino-service
curl http://localhost:8025/health   # ml-service
curl http://localhost:8028/health   # device-intelligence-service
```

---

## Domain 4: automation-core (8 services)

**Purpose:** Core automation engine -- NL to YAML pipeline, entity resolution, validation, and deployment. The most actively developed domain.

| Service | Port | Role |
|---------|------|------|
| ha-ai-agent-service | 8030 | HA AI agent -- context building, entity resolution, GUI automation path |
| ai-automation-service-new | 8036 | Core automation engine -- NL to YAML (CLI path) |
| ai-query-service | 8035 | Natural language query interface |
| automation-linter | 8016 | YAML validation and linting |
| yaml-validation-service | 8037 | Unified schema/entity/service validation |
| ai-code-executor | (internal) | Safe code execution sandbox |
| automation-trace-service | 8044 | HA automation trace + logbook ingestion |
| ha-device-control | 8046 | Direct HA device control (lights, switches, covers) |

**Compose file:** `domains/automation-core/compose.yml`
**Depends on:** Domain 1 (data-api), Domain 3 (ML inference via ai-core-service)
**Depended on by:** Domain 9 (frontends display automation results)

**Key features:**
- Agent Evaluation Framework: `@trace_session` wired on ha-ai-agent-service (chat), ai-automation-service-new (plan), ai-core-service (analyze/patterns)
- Deploy Pipeline: Hardware-aware template selection, LLM prompt improvements, smart placeholder handling, automation update flow
- Reusable Patterns: 8 RAG domains, 5 validation endpoints, 5 verifiers

**Deploy commands:**
```bash
docker compose -f domains/automation-core/compose.yml up -d
curl http://localhost:8030/health   # ha-ai-agent-service
curl http://localhost:8036/health   # ai-automation-service-new
```

---

## Domain 5: blueprints (4 services)

**Purpose:** Blueprint discovery, indexing, and ML-powered automation recommendations. Previously part of automation-intelligence, split for clearer ownership.

| Service | Port | Role |
|---------|------|------|
| blueprint-index | 8038 | Blueprint metadata indexing and search |
| blueprint-suggestion-service | 8039 | Automation suggestions based on user devices |
| rule-recommendation-ml | 8040 | ML-powered automation recommendations |
| automation-miner | 8029 | Community automation crawler (Discourse/GitHub) |

**Compose file:** `domains/blueprints/compose.yml`
**Depends on:** Domain 1 (data-api), Domain 3 (ML inference)
**Depended on by:** Domain 4 (automation-core queries blueprint suggestions)

**Deploy commands:**
```bash
docker compose -f domains/blueprints/compose.yml up -d
curl http://localhost:8038/health   # blueprint-index
curl http://localhost:8039/health   # blueprint-suggestion-service
```

---

## Domain 6: energy-analytics (3 services)

**Purpose:** Energy intelligence -- power causality analysis, consumption forecasting, and proactive context-aware recommendations. Previously part of automation-intelligence.

| Service | Port | Role |
|---------|------|------|
| energy-correlator | 8017 | Device-power causality analysis |
| energy-forecasting | 8042 | 7-day energy consumption predictions |
| proactive-agent-service | 8031 | Proactive recommendations and suggestions |

**Compose file:** `domains/energy-analytics/compose.yml`
**Depends on:** Domain 1 (data-api), Domain 3 (ML inference)

**Key features:**
- Proactive Agent has activity context integration (fetches from data-api, injects into LLM prompt)
- Agent Evaluation Framework: `@trace_session` wired on proactive-agent-service (suggestions)
- Weather + sports + energy + activity context assembled via `context_analysis_service.py`

**Deploy commands:**
```bash
docker compose -f domains/energy-analytics/compose.yml up -d
curl http://localhost:8017/health   # energy-correlator
curl http://localhost:8031/health   # proactive-agent-service
```

---

## Domain 7: device-management (8 services)

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
**Depends on:** Domain 1 (data-api), Domain 3 (device-intelligence-service for classification)
**Depended on by:** Domain 4 (automation uses device context)

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

## Domain 8: pattern-analysis (2 services)

**Purpose:** Behavioral pattern detection and synergy analysis. Previously part of automation-intelligence, split due to distinct domain focus.

| Service | Port | Role |
|---------|------|------|
| ai-pattern-service | 8034 | Pattern detection, synergy analysis, blueprint enrichment |
| api-automation-edge | 8041 | Edge computing for API-driven automations |

**Compose file:** `domains/pattern-analysis/compose.yml`
**Depends on:** Domain 1 (data-api)

**Key features:**
- Sibling entity filtering (`_build_sibling_index()` + `_are_sibling_entities()`)
- Pattern scoring and tuning feedback loop
- Post-execution verification via `TaskExecutionVerifier`

**Deploy commands:**
```bash
docker compose -f domains/pattern-analysis/compose.yml up -d
curl http://localhost:8034/health   # ai-pattern-service
curl http://localhost:8041/health   # api-automation-edge
```

---

## Domain 9: frontends (4 services in this compose file)

**Purpose:** Observability UI, AI automation UI, and voice gateway. **health-dashboard** (:3000) is **not** in this file — it is deployed from **core-platform** (`domains/core-platform/compose.yml`).

| Service | Port | Role |
|---------|------|------|
| jaeger | 16686 | Distributed tracing UI |
| observability-dashboard | 8501 | Monitoring dashboard (Streamlit) |
| ai-automation-ui | 3001 | AI automation web UI (React) |
| voice-gateway | 8047 | Voice input/output gateway (STT/TTS) |

**Compose file:** `domains/frontends/compose.yml`
**Depends on:** Domain 1 (admin-api, data-api), Domain 4 (automation endpoints)

**Deploy commands:**
```bash
docker compose -f domains/frontends/compose.yml up -d
curl http://localhost:3001          # ai-automation-ui
curl http://localhost:16686         # jaeger UI
```

---

## Cross-Domain Communication Patterns

### Allowed Communication

```
+-------------------+      +-------------------+      +-----------------+
|  Any Domain       | ---> |  core-platform    | ---> |  InfluxDB       |
|  (HTTP client)    |      |  (data-api:8006)  |      |  (direct write) |
+-------------------+      +-------------------+      +-----------------+

+-------------------+      +-------------------+
|  automation-core  | ---> |  ml-engine        |
|  blueprints       |      |  (ai-core:8018)   |
|  energy-analytics | ---> |                   |
+-------------------+      +-------------------+

+-------------------+      +-------------------+
|  frontends        | ---> |  automation-core  |
|  (ai-auto-ui)     |      |  (ha-ai-agent)    |
+-------------------+      +-------------------+
```

### Communication Rules

1. **All domains may call core-platform** (data-api for queries, InfluxDB for writes)
2. **automation-core, blueprints, energy-analytics call ml-engine** for AI inference via ai-core-service
3. **frontends call automation-core** for automation features
4. **data-collectors are independent** -- no service-to-service calls between collectors
5. **No circular dependencies** -- communication flows downward from core-platform

### Resilience at Group Boundaries

All cross-group HTTP calls use `libs/homeiq-resilience/CrossGroupClient` with circuit breakers, automatic retries with exponential backoff, Bearer auth, and OTel trace propagation. See [libs/homeiq-resilience/README.md](../../libs/homeiq-resilience/README.md) for full documentation.

**Resilience rollout status (February 2026):**

| Service | Domain | Cross-Domain Targets | Circuit Breakers |
|---------|--------|---------------------|-----------------|
| ha-ai-agent-service | D4 automation-core | data-api (D1), device-intelligence (D3) | `core-platform`, `ml-engine` |
| blueprint-suggestion-service | D5 blueprints | data-api (D1) | `core-platform` |
| ai-pattern-service | D8 pattern-analysis | data-api (D1) | `core-platform` |
| ai-automation-service-new | D4 automation-core | data-api (D1) | `core-platform` |
| proactive-agent-service | D6 energy-analytics | data-api (D1), weather-api (D2) | `core-platform`, `data-collectors` |
| device-health-monitor | D7 device-management | data-api (D1), device-intelligence (D3) | `core-platform`, `ml-engine` |

**Degradation behavior:**

| Caller Domain | Upstream Domain | Behavior When Upstream Down |
|--------------|----------------|----------------------------|
| automation-core / blueprints / energy-analytics | ml-engine | Rule-based fallback, cached embeddings |
| automation-core / energy-analytics | core-platform | Circuit opens after 5 failures; returns empty results (events=`[]`, entities=`[]`) |
| device-management | ml-engine | Skip ML classification, return `None` |
| device-management | core-platform | Circuit opens; returns empty entities/devices |
| frontends | automation-core | Show "AI features temporarily unavailable" |
| data-collectors | core-platform | **Fatal** -- buffer to disk, retry on recovery |

**Health endpoint format** (all cross-group callers):
```json
{
  "status": "healthy",
  "group": "automation-core",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "dependencies": {
    "data-api": { "status": "healthy", "latency_ms": 12 }
  }
}
```

**Alerting severity matrix** (documented in `libs/homeiq-resilience/README.md`):

| Domain | Severity | Response Time |
|--------|----------|--------------|
| core-platform | P1 (page) | Immediate |
| ml-engine | P2 (alert) | 5 min |
| automation-core | P2 (alert) | 5 min |
| energy-analytics | P2 (alert) | 5 min |
| blueprints | P3 (notify) | 10 min |
| pattern-analysis | P3 (notify) | 10 min |
| data-collectors | P3 (notify) | 15 min |
| device-management | P3 (notify) | 10 min |
| frontends | P3 (notify) | 10 min |

---

## Deployment Combinations

### Common deployment profiles:

**Prefer:** `./scripts/start-stack.sh` or `.\scripts\start-stack.ps1` (ordered domains + `--profile production`). See [Deployment Quick Reference](../deployment/DEPLOYMENT_QUICK_REFERENCE.md).

```bash
# Full stack (all groups) — same as start-stack, merged project name "homeiq"
docker compose --profile production up -d

# Core only (data pipeline + dashboard + monitoring)
docker compose -f domains/core-platform/compose.yml --profile production up -d

# Core + collectors (include profile-gated collectors)
docker compose -f domains/core-platform/compose.yml -f domains/data-collectors/compose.yml --profile production up -d

# Core + ML + automation (AI features without device management)
docker compose -f domains/core-platform/compose.yml -f domains/ml-engine/compose.yml -f domains/automation-core/compose.yml --profile production up -d

# Core + devices (device management without AI)
docker compose -f domains/core-platform/compose.yml -f domains/device-management/compose.yml --profile production up -d

# Core + all backends (everything except frontends)
docker compose -f domains/core-platform/compose.yml -f domains/data-collectors/compose.yml \
  -f domains/ml-engine/compose.yml -f domains/automation-core/compose.yml -f domains/device-management/compose.yml --profile production up -d
```

### Startup order (recommended):

```
1. core-platform      (must be first -- provides InfluxDB, PostgreSQL, data-api)
2. data-collectors    (can start in parallel with 3, 7, 8)
3. ml-engine          (can start in parallel with 2, 7, 8)
4. device-management  (can start in parallel with 2, 3)
5. pattern-analysis   (can start in parallel with 2, 3)
6. automation-core    (after ml-engine is healthy)
7. blueprints         (after ml-engine is healthy)
8. energy-analytics   (after ml-engine is healthy)
9. frontends          (after automation-core is healthy)
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
    compose.yml              # Domain 1: core-platform services
  data-collectors/
    compose.yml              # Domain 2: data-collectors services
  ml-engine/
    compose.yml              # Domain 3: ml-engine services
  automation-core/
    compose.yml              # Domain 4: automation-core services
  blueprints/
    compose.yml              # Domain 5: blueprint services
  energy-analytics/
    compose.yml              # Domain 6: energy-analytics services
  device-management/
    compose.yml              # Domain 7: device-management services
  pattern-analysis/
    compose.yml              # Domain 8: pattern-analysis services
  frontends/
    compose.yml              # Domain 9: frontend services

docker-compose.yml           # Root file -- includes all 9 domain compose files
docker-bake.hcl              # Parallel build groups
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
**Last Updated:** February 27, 2026
