# HomeIQ Compose Files

**Last Updated:** February 22, 2026

This directory contains the per-group Docker Compose files for HomeIQ's 6-group service architecture.

---

## Quick Start

```bash
# Start everything (full stack)
cd /path/to/HomeIQ
docker compose up -d

# Start core only (minimal system)
docker compose -f compose/core.yml up -d

# Start core + collectors (data pipeline with enrichment)
docker compose -f compose/core.yml -f compose/collectors.yml up -d

# Start core + ML + automation (AI features)
docker compose -f compose/core.yml -f compose/ml.yml -f compose/automation.yml up -d
```

---

## File Structure

```
compose/
  core.yml                 # Group 1: core-platform (6 services)
  core.env.example         # Environment template for core
  collectors.yml           # Group 2: data-collectors (8 services)
  collectors.env.example   # Environment template for collectors
  ml.yml                   # Group 3: ml-engine (9+1 services)
  ml.env.example           # Environment template for ML
  automation.yml           # Group 4: automation-intelligence (16 services)
  automation.env.example   # Environment template for automation
  devices.yml              # Group 5: device-management (8 services)
  devices.env.example      # Environment template for devices
  frontends.yml            # Group 6: frontends (3 + infra)
  frontends.env.example    # Environment template for frontends
  test.yml                 # Test profile (ha-simulator, etc.)
```

---

## Groups at a Glance

| # | Group | Compose File | Services | Must Start After |
|---|-------|-------------|----------|------------------|
| 1 | **core-platform** | `core.yml` | influxdb, data-api, websocket-ingestion, admin-api, health-dashboard, data-retention | -- (start first) |
| 2 | **data-collectors** | `collectors.yml` | weather-api, smart-meter, sports-api, air-quality, carbon-intensity, electricity-pricing, calendar, log-aggregator | core-platform |
| 3 | **ml-engine** | `ml.yml` | ai-core-service, openvino, ml-service, ner-service, openai-service, rag-service, ai-training, device-intelligence, model-prep | core-platform |
| 4 | **automation-intelligence** | `automation.yml` | ha-ai-agent, ai-automation, ai-query, ai-pattern, ai-code-executor, automation-miner, automation-linter, yaml-validation, blueprint-index, blueprint-suggestion, rule-recommendation-ml, api-automation-edge, proactive-agent, energy-correlator, energy-forecasting, automation-trace | core-platform, ml-engine |
| 5 | **device-management** | `devices.yml` | device-health-monitor, device-context-classifier, device-setup-assistant, device-database-client, device-recommender, activity-recognition, activity-writer, ha-setup-service | core-platform |
| 6 | **frontends** | `frontends.yml` | ai-automation-ui, observability-dashboard, jaeger | core-platform, automation-intelligence |

---

## Environment Setup

Each group has a `.env.example` template. Copy and configure before starting:

```bash
# Copy environment templates
cp compose/core.env.example compose/core.env
cp compose/collectors.env.example compose/collectors.env
cp compose/ml.env.example compose/ml.env
cp compose/automation.env.example compose/automation.env
cp compose/devices.env.example compose/devices.env
cp compose/frontends.env.example compose/frontends.env

# Edit each .env file with your settings
# At minimum, configure:
#   core.env        - INFLUXDB_TOKEN, HA_WS_URL, HA_TOKEN, API_KEY
#   collectors.env  - OPENWEATHERMAP_API_KEY, WATTTIME credentials
#   ml.env          - OPENAI_API_KEY
#   automation.env  - HA_URL, HA_TOKEN, DATA_API_KEY
```

**IMPORTANT:** The `.env` files contain secrets and must NOT be committed to Git.

---

## Network Architecture

All groups share a single Docker network (`homeiq-network`):

- `core.yml` defines the network
- All other group files reference it as `external: true`
- Services can communicate across groups via Docker DNS (e.g., `http://data-api:8006`)
- Groups can be started/stopped independently without affecting the shared network

---

## Common Operations

```bash
# View logs for a specific group
docker compose -f compose/ml.yml logs -f

# Rebuild a single service within a group
docker compose -f compose/automation.yml up -d --build ai-pattern-service

# Stop a group without affecting others
docker compose -f compose/collectors.yml down

# Force recreate containers (for config changes)
docker compose -f compose/devices.yml up -d --force-recreate

# View running services across all groups
docker compose ps
```

---

## Documentation

- [Service Groups Architecture](../docs/architecture/service-groups.md) -- Canonical reference with full details
- [Deployment Runbook](../docs/deployment/DEPLOYMENT_RUNBOOK.md) -- Per-group deployment and rollback procedures
- [Services Ranked by Importance](../services/SERVICES_RANKED_BY_IMPORTANCE.md) -- Service tier classification
- [Service Decomposition Plan](../docs/planning/service-decomposition-plan.md) -- Full implementation plan
