# HomeIQ Services Ranked by Importance

**Last Updated:** February 24, 2026
**Purpose:** Comprehensive ranking of all services by criticality to system operation

---

## Overview

HomeIQ consists of **50 microservices** organized into a layered architecture. This document ranks services by their importance to system operation, helping teams prioritize monitoring, deployment, and incident response.

---

## Service Groups (Deployment Architecture)

Services are organized into **9 independently deployable domain groups** based on deployment criticality and domain boundaries. For the canonical reference, see [Service Groups Architecture](./service-groups.md).

| # | Domain | Count | Services | Compose File |
|---|--------|-------|----------|--------------|
| 1 | **core-platform** | 6 | influxdb, data-api, websocket-ingestion, admin-api, health-dashboard, data-retention | `domains/core-platform/compose.yml` |
| 2 | **data-collectors** | 8 | weather-api, smart-meter, sports-api, air-quality, carbon-intensity, electricity-pricing, calendar, log-aggregator | `domains/data-collectors/compose.yml` |
| 3 | **ml-engine** | 10 | openvino-service, ml-service, ner-service, openai-service, rag-service, ai-core-service, ai-training-service, device-intelligence-service, nlp-fine-tuning, model-prep | `domains/ml-engine/compose.yml` |
| 4 | **automation-core** | 7 | ha-ai-agent, ai-automation-service-new, ai-query, automation-linter, yaml-validation, ai-code-executor, automation-trace | `domains/automation-core/compose.yml` |
| 5 | **blueprints** | 4 | blueprint-index, blueprint-suggestion, rule-recommendation-ml, automation-miner | `domains/blueprints/compose.yml` |
| 6 | **energy-analytics** | 3 | energy-correlator, energy-forecasting, proactive-agent | `domains/energy-analytics/compose.yml` |
| 7 | **device-management** | 8 | device-health-monitor, device-context-classifier, device-setup-assistant, device-database-client, device-recommender, activity-recognition, activity-writer, ha-setup-service | `domains/device-management/compose.yml` |
| 8 | **pattern-analysis** | 2 | ai-pattern-service, api-automation-edge | `domains/pattern-analysis/compose.yml` |
| 9 | **frontends** | 4 | ai-automation-ui, observability-dashboard, health-dashboard, jaeger | `domains/frontends/compose.yml` |

**Dependency flow:** core-platform --> (data-collectors | ml-engine | device-management | pattern-analysis) --> (automation-core | blueprints | energy-analytics) --> frontends

---

## Tier Classification

| Tier | Classification | Count | Availability Target |
|------|---------------|-------|---------------------|
| 🔴 Tier 1 | Mission-Critical | 5 | 99.9%+ |
| 🟠 Tier 2 | Essential Data Integration | 5 | 99.5%+ |
| 🟡 Tier 3 | AI/ML Core | 5 | 99%+ |
| 🟢 Tier 4 | Enhanced Data Sources | 6 | 95%+ |
| 🔵 Tier 5 | AI Automation Features | 8 | 90%+ |
| ⚪ Tier 6 | Device Management | 6 | 90%+ |
| ⚪ Tier 7 | Specialized/Development | 11 | Best effort |

---

## 🔴 TIER 1: MISSION-CRITICAL

**System cannot function without these services.**

| Rank | Service | Port | Role | Dependencies |
|------|---------|------|------|--------------|
| **1** | **websocket-ingestion** | 8001 | Primary data pipeline - captures ALL Home Assistant events | InfluxDB, data-api |
| **2** | **data-api** | 8006 | Central query hub - ALL services query through this | InfluxDB, SQLite |
| **3** | **InfluxDB** | 8086 | Time-series database - stores ALL event/sensor data | None |
| **4** | **admin-api** | 8004 | System control plane - health, config, service mgmt | All services |
| **5** | **health-dashboard** | 3000 | Primary user interface - visibility and configuration | admin-api, data-api |

### Impact if Down

- **websocket-ingestion**: Complete data flow stops - no events captured
- **data-api**: All queries fail - dashboards blank, analytics broken
- **InfluxDB**: No data storage - everything fails
- **admin-api**: No system monitoring or configuration
- **health-dashboard**: Users cannot see or control the system

### Data Flow (Critical Path)

```
Home Assistant (192.168.1.86:8123)
         │
         ▼
┌─────────────────────┐
│ websocket-ingestion │ ◄── Port 8001
│  (Event Capture)    │
└─────────┬───────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌────────┐  ┌─────────┐
│InfluxDB│  │ data-api│ ◄── Port 8006
│ :8086  │  │ (SQLite)│
└────┬───┘  └────┬────┘
     │           │
     └─────┬─────┘
           ▼
   ┌───────────────┐
   │health-dashboard│ ◄── Port 3000
   │   (React UI)   │
   └───────────────┘
```

---

## 🟠 TIER 2: ESSENTIAL DATA INTEGRATION

**Core features depend on these services.**

| Rank | Service | Port | Role | Dependencies |
|------|---------|------|------|--------------|
| **6** | **data-retention** | 8080 | Data lifecycle management - prevents bloat/data loss | InfluxDB, SQLite |
| **7** | **ha-setup-service** | 8024 | HA health monitoring, integration checks, setup wizards | HA, MQTT, Zigbee2MQTT |
| **8** | **weather-api** | 8009 | Weather data for automations | InfluxDB |
| **9** | **smart-meter-service** | 8014 | Real-time power monitoring | InfluxDB |
| **10** | **energy-correlator** | 8017 | Device power consumption causality | InfluxDB |

### Impact if Down

- **data-retention**: Database grows unbounded, potential disk full
- **ha-setup-service**: Cannot diagnose HA integration issues
- **weather-api**: Weather-based automations fail
- **smart-meter-service**: Energy analytics unavailable
- **energy-correlator**: Cannot correlate device actions to power usage

---

## 🟡 TIER 3: AI/ML CORE

**Intelligence features depend on these services.**

| Rank | Service | Port | Role | Dependencies |
|------|---------|------|------|--------------|
| **11** | **ai-core-service** | 8018 | Orchestrates all AI/ML services | openvino, ml-service |
| **12** | **device-intelligence-service** | 8028 | 6,000+ device capability mapping | SQLite, scikit-learn |
| **13** | **openvino-service** | 8026 | Transformer embeddings, semantic search | PyTorch |
| **14** | **ml-service** | 8025 | Clustering, anomaly detection | scikit-learn |
| **15** | **energy-forecasting** | 8042 | 7-day energy consumption predictions | InfluxDB |

### Impact if Down

- **ai-core-service**: All AI features unavailable
- **device-intelligence-service**: No device capability insights
- **openvino-service**: No semantic search or embeddings
- **ml-service**: No anomaly detection or clustering
- **energy-forecasting**: No energy predictions

### AI Service Architecture

```
┌─────────────────────────────────────────┐
│           ai-core-service               │
│         (Orchestrator :8018)            │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
┌────────┐  ┌─────────┐  ┌─────────────┐
│openvino│  │ml-service│  │   Other     │
│ :8026  │  │  :8025   │  │  AI Svc     │
└────────┘  └──────────┘  └─────────────┘
```

---

## 🟢 TIER 4: ENHANCED DATA SOURCES

**Enriches system with additional data.**

| Rank | Service | Port | Role | Update Frequency |
|------|---------|------|------|------------------|
| **16** | **air-quality-service** | 8012 | AQI for HVAC automations | Hourly |
| **17** | **sports-api** | 8005 | Team Tracker integration | Real-time |
| **18** | **carbon-intensity-service** | 8010 | Grid carbon data | Periodic |
| **19** | **electricity-pricing-service** | 8011 | Dynamic pricing | Periodic |
| **20** | **calendar-service** | 8013 | HA calendar events | Real-time |
| **21** | **log-aggregator** | 8015 | Centralized logging | Continuous |

### Impact if Down

- Specific automation triggers unavailable
- Debugging capabilities reduced (log-aggregator)
- System continues to function normally

---

## 🔵 TIER 5: AI AUTOMATION FEATURES

**Smart suggestion and automation features.**

| Rank | Service | Port | Role |
|------|---------|------|------|
| **22** | **automation-miner** | 8029 | Crawls community automations |
| **23** | **blueprint-suggestion-service** | 8039 | Suggests automations based on devices |
| **24** | **ha-ai-agent-service** | 8030 | HA AI agent integration |
| **25** | **ai-automation-service-new** | 8036 | Intelligent automation engine |
| **26** | **proactive-agent-service** | 8031 | Proactive recommendations |
| **27** | **rag-service** | 8027 | RAG for semantic search |
| **28** | **ai-query-service** | 8035 | Natural language queries |
| **29** | **ai-pattern-service** | 8034 | Pattern detection |

### Impact if Down

- No intelligent suggestions
- Core system continues to work
- Users can still manually create automations

---

## ⚪ TIER 6: DEVICE MANAGEMENT

**Supporting device-related features.**

| Rank | Service | Role |
|------|---------|------|
| **30** | **device-health-monitor** | Device health tracking and battery monitoring |
| **31** | **device-context-classifier** | Room/location inference |
| **32** | **device-recommender** | Device recommendations and upgrades |
| **33** | **device-setup-assistant** | Guided device onboarding |
| **34** | **device-database-client** | Device data access layer |
| **35** | **activity-recognition** | User activity detection from patterns |

---

## ⚪ TIER 7: SPECIALIZED/DEVELOPMENT

**Optional and development services.**

| Rank | Service | Port | Purpose |
|------|---------|------|---------|
| **36** | **automation-linter** | 8016 | YAML validation and fixes |
| **37** | **yaml-validation-service** | - | Config validation |
| **38** | **observability-dashboard** | - | Advanced monitoring UI |
| **39** | **blueprint-index** | - | Blueprint metadata |
| **40** | **ai-automation-ui** | 3001 | AI automation web UI |
| **41** | **model-prep** | - | ML model preparation |
| **42** | **nlp-fine-tuning** | - | NLP model fine-tuning |
| **43** | **rule-recommendation-ml** | - | ML rule suggestions |
| **44** | **ai-code-executor** | - | Safe code execution sandbox |
| **45** | **api-automation-edge** | - | Edge computing |
| **46** | **ha-simulator** | - | Development/testing only |

---

## Service Dependency Map

```
                        ┌─────────────────────────────────────┐
                        │     TIER 1: MISSION CRITICAL        │
                        │  websocket-ingestion → data-api     │
                        │      InfluxDB │ admin-api           │
                        │         health-dashboard            │
                        └──────────────┬──────────────────────┘
                                       │
                ┌──────────────────────┴───────────────────────┐
                │          TIER 2: ESSENTIAL                   │
                │ data-retention │ ha-setup │ weather-api      │
                │ smart-meter │ energy-correlator              │
                └──────────────────────┬───────────────────────┘
                                       │
           ┌───────────────────────────┴───────────────────────────┐
           │              TIER 3: AI/ML CORE                       │
           │   ai-core │ device-intelligence │ openvino │ ml      │
           │                  energy-forecasting                   │
           └───────────────────────────┬───────────────────────────┘
                                       │
      ┌────────────────────────────────┴────────────────────────────────┐
      │                    TIER 4-7: ENHANCED/OPTIONAL                  │
      │  air-quality │ sports │ carbon │ automation-miner │ etc.        │
      └─────────────────────────────────────────────────────────────────┘
```

---

## Operational Guidelines

### Deployment Priority

1. Always deploy Tier 1 services first
2. Tier 2 services should be deployed alongside Tier 1
3. AI/ML services (Tier 3) can be deployed after core is stable
4. Remaining tiers are optional based on feature needs

### Monitoring Priority

| Tier | Alert Severity | Response Time |
|------|----------------|---------------|
| Tier 1 | Critical | Immediate |
| Tier 2 | High | < 15 minutes |
| Tier 3 | Medium | < 1 hour |
| Tier 4-7 | Low | Best effort |

### Group-Level Alerting (Resilience)

Services that make cross-group HTTP calls use `libs/homeiq-resilience` circuit breakers and expose structured `/health` endpoints with a `group` field. Use this for differentiated alerting:

| Domain | Severity | Response Time | Rationale |
|--------|----------|---------------|-----------|
| core-platform (D1) | P1 (page) | Immediate | All services depend on data-api |
| ml-engine (D3) | P2 (alert) | 5 min | AI features degrade but basic function continues |
| automation-core (D4) | P2 (alert) | 5 min | Automation suggestions stop but HA control works |
| data-collectors (D2) | P3 (notify) | 15 min | Weather/energy data stale but not blocking |
| blueprints (D5) | P3 (notify) | 15 min | Blueprint suggestions stop but automations work |
| energy-analytics (D6) | P3 (notify) | 10 min | Energy forecasting delayed but system works |
| device-management (D7) | P3 (notify) | 10 min | Health monitoring delayed but devices work |
| pattern-analysis (D8) | P3 (notify) | 10 min | Pattern detection delayed but core functions work |
| frontends (D9) | P3 (notify) | 10 min | Dashboard unavailable but backend functional |

### Cross-Group Resilience

Services calling across group boundaries use `CrossGroupClient` with circuit breakers for graceful degradation. When a target group is down, services return empty/cached results instead of crashing.

**Services with resilience rollout complete:**
- ha-ai-agent-service (D4 → D1, D3)
- blueprint-suggestion-service (D5 → D1)
- ai-pattern-service (D8 → D1)
- ai-automation-service-new (D4 → D1)
- proactive-agent-service (D6 → D1, D2)
- device-health-monitor (D7 → D1, D3)

For details, see [`libs/homeiq-resilience/README.md`](../../libs/homeiq-resilience/README.md).

### Restart Order (After Outage)

1. InfluxDB
2. data-api
3. websocket-ingestion
4. admin-api
5. health-dashboard
6. Remaining services by tier

---

## Port Reference (Quick Lookup)

| Port | Service | Tier |
|------|---------|------|
| 3000 | health-dashboard | 1 |
| 3001 | ai-automation-ui | 7 |
| 8001 | websocket-ingestion | 1 |
| 8004 | admin-api | 1 |
| 8005 | sports-api | 4 |
| 8006 | data-api | 1 |
| 8009 | weather-api | 2 |
| 8010 | carbon-intensity-service | 4 |
| 8011 | electricity-pricing-service | 4 |
| 8012 | air-quality-service | 4 |
| 8013 | calendar-service | 4 |
| 8014 | smart-meter-service | 2 |
| 8015 | log-aggregator | 4 |
| 8017 | energy-correlator | 2 |
| 8018 | ai-core-service | 3 |
| 8016 | automation-linter | 7 |
| 8025 | ml-service | 3 |
| 8026 | openvino-service | 3 |
| 8024 | ha-setup-service | 2 |
| 8028 | device-intelligence-service | 3 |
| 8029 | automation-miner | 5 |
| 8037 | yaml-validation-service | 5 |
| 8042 | energy-forecasting | 3 |
| 8043 | activity-recognition | 6 |
| 8080 | data-retention | 2 |
| 8086 | InfluxDB | 1 |

### Docker deployment (host ports)

In `docker-compose.yml`, some services use a different **host** port to avoid conflicts (internal container port in parentheses):

| Host port | Service | Container port | Note |
|-----------|---------|----------------|------|
| 8042 | energy-forecasting | 8037 | 8037 used by yaml-validation-service |
| 8043 | activity-recognition | 8036 | 8036 used by ai-automation-service-new |
| 8125 | ha-simulator | 8123 | Profile `development` only |

**Optional / profile services:**

- **ha-simulator** (8125) and **model-prep** (one-shot): start with `docker compose --profile development up -d` or by service name.

---

## Related Documentation

- [Service Groups Architecture](./service-groups.md) - Canonical reference for the 9-domain deployment structure
- [Architecture Quick Reference](./README_ARCHITECTURE_QUICK_REF.md)
- [Tech Stack](./tech-stack.md)
- [Source Tree](./source-tree.md)
- [Master Call Tree Index](../../implementation/analysis/MASTER_CALL_TREE_INDEX.md)

---

**Maintained by:** HomeIQ DevOps Team
**Last Updated:** February 24, 2026
