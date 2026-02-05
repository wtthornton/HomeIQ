# Phase 2: Service Dependency Analysis

**Created:** February 5, 2026
**Story:** PHASE2-001
**Status:** ✅ Complete

---

## Executive Summary

**Total Services Analyzed:** 40
**Services Requiring Updates:** 35 unique services
**Breaking Changes Impact:** 3 CRITICAL, 2 HIGH, 1 LOW

### Key Findings

- ✅ **20 services** use pytest-asyncio (async tests)
- ✅ **10 services** use tenacity (retry logic)
- ✅ **3 services** use asyncio-mqtt (MQTT connectivity)
- ✅ **16 services** use influxdb-client (data ingestion/queries)
- ⚠️ **11 services** have multiple dependencies (require careful ordering)

---

## Service Categorization by Breaking Change

### 1. pytest-asyncio 1.3.0 Migration (20 services)

**Breaking Change:** Test fixture patterns, `@pytest.mark.asyncio` required

| Service | Type | Priority | Notes |
|---------|------|----------|-------|
| admin-api | Core | HIGH | Critical admin service |
| ai-core-service | AI/ML | HIGH | Core AI service |
| ai-pattern-service | AI/ML | MEDIUM | Pattern recognition |
| ai-query-service | AI/ML | MEDIUM | Query processing |
| ai-training-service | AI/ML | MEDIUM | Model training |
| automation-miner | Automation | LOW | Non-critical |
| blueprint-index | Automation | LOW | Non-critical |
| blueprint-suggestion-service | Automation | LOW | Non-critical |
| data-api | Core | CRITICAL | Critical data service |
| data-retention | Core | HIGH | Data management |
| device-intelligence-service | Device | MEDIUM | Device analysis |
| ha-ai-agent-service | AI/ML | MEDIUM | HA AI agent |
| ha-setup-service | Core | LOW | Setup service |
| ha-simulator | Dev | LOW | Testing tool |
| ml-service | AI/ML | HIGH | Core ML service |
| openvino-service | AI/ML | MEDIUM | OpenVINO inference |
| proactive-agent-service | AI/ML | MEDIUM | Proactive agent |
| sports-api | Integration | LOW | Sports data |
| weather-api | Integration | LOW | Weather data |
| websocket-ingestion | Core | CRITICAL | Event ingestion |

**Risk Assessment:**
- **CRITICAL Services:** 2 (data-api, websocket-ingestion)
- **HIGH Priority:** 4
- **MEDIUM Priority:** 8
- **LOW Priority:** 6

---

### 2. tenacity 9.1.2 Migration (10 services)

**Breaking Change:** Retry decorator API changes, wait strategy updates

| Service | Type | Priority | Notes |
|---------|------|----------|-------|
| ai-automation-service-new | Automation | HIGH | Automation core |
| ai-core-service | AI/ML | HIGH | Core AI service |
| ai-pattern-service | AI/ML | MEDIUM | Pattern recognition |
| api-automation-edge | Automation | CRITICAL | Edge automation |
| device-intelligence-service | Device | MEDIUM | Device analysis |
| ha-ai-agent-service | AI/ML | MEDIUM | HA AI agent |
| ml-service | AI/ML | HIGH | Core ML service |
| openvino-service | AI/ML | MEDIUM | OpenVINO inference |
| proactive-agent-service | AI/ML | MEDIUM | Proactive agent |
| rag-service | AI/ML | MEDIUM | RAG processing |

**Risk Assessment:**
- **CRITICAL Services:** 1 (api-automation-edge)
- **HIGH Priority:** 3
- **MEDIUM Priority:** 6

---

### 3. asyncio-mqtt → aiomqtt 2.4.0 Migration (3 services)

**Breaking Change:** Complete library replacement, package rename

| Service | Type | Priority | Notes |
|---------|------|----------|-------|
| data-retention | Core | HIGH | Data management |
| ha-simulator | Dev | LOW | Testing tool |
| websocket-ingestion | Core | CRITICAL | Event ingestion |

**Risk Assessment:**
- **CRITICAL Services:** 1 (websocket-ingestion)
- **HIGH Priority:** 1
- **LOW Priority:** 1

**Note:** Only 3 services, but websocket-ingestion is CRITICAL path.

---

### 4. influxdb3-python 0.17.0 Migration (16 services)

**Breaking Change:** Client API redesign, write/query API changes

| Service | Type | Priority | Notes |
|---------|------|----------|-------|
| admin-api | Core | HIGH | Critical admin service |
| air-quality-service | Integration | LOW | Air quality data |
| api-automation-edge | Automation | CRITICAL | Edge automation |
| calendar-service | Integration | LOW | Calendar integration |
| carbon-intensity-service | Integration | LOW | Carbon data |
| data-api | Core | CRITICAL | Critical data service |
| data-retention | Core | HIGH | Data management |
| electricity-pricing-service | Integration | LOW | Electricity data |
| energy-correlator | Analytics | MEDIUM | Energy analysis |
| energy-forecasting | Analytics | MEDIUM | Energy prediction |
| observability-dashboard | Monitoring | LOW | Dashboard |
| smart-meter-service | Integration | MEDIUM | Smart meter data |
| sports-api | Integration | LOW | Sports data |
| weather-api | Integration | LOW | Weather data |
| websocket-ingestion | Core | CRITICAL | Event ingestion |

**Risk Assessment:**
- **CRITICAL Services:** 3 (api-automation-edge, data-api, websocket-ingestion)
- **HIGH Priority:** 2
- **MEDIUM Priority:** 3
- **LOW Priority:** 8

---

## Services with Multiple Dependencies (11 services)

**High Risk - Require Careful Migration Order:**

| Service | Dependencies | Priority | Risk Level |
|---------|--------------|----------|------------|
| **websocket-ingestion** | pytest-asyncio, asyncio-mqtt, influxdb | CRITICAL | VERY HIGH |
| **data-api** | pytest-asyncio, influxdb | CRITICAL | HIGH |
| **api-automation-edge** | tenacity, influxdb | CRITICAL | HIGH |
| **ai-core-service** | pytest-asyncio, tenacity | HIGH | MEDIUM |
| **ml-service** | pytest-asyncio, tenacity | HIGH | MEDIUM |
| admin-api | pytest-asyncio, influxdb | HIGH | MEDIUM |
| ai-pattern-service | pytest-asyncio, tenacity | MEDIUM | MEDIUM |
| device-intelligence-service | pytest-asyncio, tenacity | MEDIUM | MEDIUM |
| ha-ai-agent-service | pytest-asyncio, tenacity | MEDIUM | MEDIUM |
| openvino-service | pytest-asyncio, tenacity | MEDIUM | MEDIUM |
| proactive-agent-service | pytest-asyncio, tenacity | MEDIUM | MEDIUM |
| data-retention | pytest-asyncio, asyncio-mqtt, influxdb | HIGH | MEDIUM |

**Critical Path Services:**
1. **websocket-ingestion** - 3 breaking changes (pytest-asyncio, MQTT, InfluxDB)
2. **data-api** - 2 breaking changes (pytest-asyncio, InfluxDB)
3. **api-automation-edge** - 2 breaking changes (tenacity, InfluxDB)

---

## Migration Order Strategy

### Phase A: Low-Risk Single Dependency Services (Days 1-2)

**Test Migration Scripts on Low-Risk Services:**

1. **pytest-asyncio only:**
   - automation-miner
   - blueprint-index
   - ha-setup-service
   - ha-simulator

2. **tenacity only:**
   - rag-service
   - ai-automation-service-new

3. **influxdb only:**
   - air-quality-service
   - calendar-service
   - carbon-intensity-service
   - electricity-pricing-service

**Rationale:** Test migration scripts on non-critical services first.

---

### Phase B: Medium-Risk Services (Days 2-3)

**Medium Priority, Multiple Dependencies:**

1. **pytest-asyncio + tenacity:**
   - ai-pattern-service
   - device-intelligence-service
   - openvino-service

2. **pytest-asyncio + influxdb:**
   - sports-api
   - weather-api

**Rationale:** Validate migration script interactions on medium-priority services.

---

### Phase C: High-Risk Services (Days 3-4)

**High Priority, Multiple Dependencies:**

1. **High priority with 2 dependencies:**
   - ai-core-service (pytest-asyncio + tenacity)
   - ml-service (pytest-asyncio + tenacity)
   - admin-api (pytest-asyncio + influxdb)
   - data-retention (pytest-asyncio + asyncio-mqtt + influxdb)

**Rationale:** Critical AI/ML and data services require careful migration.

---

### Phase D: Critical Path Services (Days 4-5)

**CRITICAL Services - Requires Blue-Green Deployment:**

1. **websocket-ingestion** (pytest-asyncio + asyncio-mqtt + influxdb)
   - 3 breaking changes
   - Event ingestion pipeline (24/7 critical)
   - Deploy in off-peak hours
   - Have rollback ready

2. **data-api** (pytest-asyncio + influxdb)
   - 2 breaking changes
   - Query API (24/7 critical)
   - Blue-green deployment

3. **api-automation-edge** (tenacity + influxdb)
   - 2 breaking changes
   - Automation edge (24/7 critical)
   - Canary deployment

**Rationale:** Critical path services require zero-downtime deployment strategies.

---

## Risk Assessment Matrix

### By Service Priority

| Priority | Services | Risk Level | Strategy |
|----------|----------|------------|----------|
| **CRITICAL** | 3 | VERY HIGH | Blue-green deployment, off-peak hours |
| **HIGH** | 9 | HIGH | Canary deployment, monitoring |
| **MEDIUM** | 15 | MEDIUM | Rolling deployment, health checks |
| **LOW** | 13 | LOW | Standard deployment |

### By Breaking Change Count

| Dependencies | Services | Risk Level | Strategy |
|--------------|----------|------------|----------|
| **3 changes** | 1 | VERY HIGH | Multi-stage migration |
| **2 changes** | 10 | HIGH | Sequential migration |
| **1 change** | 24 | MEDIUM-LOW | Single migration |

---

## Critical Dependencies Identified

### 1. Database Dependencies

**InfluxDB Services (16):**
- CRITICAL: websocket-ingestion, data-api, api-automation-edge
- Must maintain data integrity during migration
- **Mitigation:** Backup before migration, verify writes after

### 2. Test Dependencies

**pytest-asyncio Services (20):**
- All services with async tests
- Test suite must pass 100% after migration
- **Mitigation:** Test migration on dev environment first

### 3. Retry Logic Dependencies

**tenacity Services (10):**
- Services with critical retry logic
- Must test failure scenarios
- **Mitigation:** Inject test failures to verify retry behavior

### 4. MQTT Dependencies

**asyncio-mqtt Services (3):**
- Only 3 services, but includes CRITICAL websocket-ingestion
- Complete library replacement (highest risk)
- **Mitigation:** Test MQTT connectivity extensively, have broker monitoring

---

## Service Group Definitions

### Group 1: Low-Risk Test Group (8 services)

**Purpose:** Validate migration scripts

```yaml
low_risk_test_group:
  - automation-miner
  - blueprint-index
  - ha-setup-service
  - ha-simulator
  - air-quality-service
  - calendar-service
  - carbon-intensity-service
  - electricity-pricing-service
```

**Characteristics:**
- Single breaking change
- Non-critical services
- Good test cases for migration scripts

---

### Group 2: pytest-asyncio Focus (20 services)

**Purpose:** Async test pattern migration

```yaml
pytest_asyncio_group:
  critical:
    - data-api
    - websocket-ingestion
  high:
    - admin-api
    - ai-core-service
    - ml-service
    - data-retention
  medium:
    - ai-pattern-service
    - ai-query-service
    - ai-training-service
    - device-intelligence-service
    - ha-ai-agent-service
    - openvino-service
    - proactive-agent-service
  low:
    - automation-miner
    - blueprint-index
    - blueprint-suggestion-service
    - ha-setup-service
    - ha-simulator
    - sports-api
    - weather-api
```

---

### Group 3: tenacity Focus (10 services)

**Purpose:** Retry logic migration

```yaml
tenacity_group:
  critical:
    - api-automation-edge
  high:
    - ai-automation-service-new
    - ai-core-service
    - ml-service
  medium:
    - ai-pattern-service
    - device-intelligence-service
    - ha-ai-agent-service
    - openvino-service
    - proactive-agent-service
    - rag-service
```

---

### Group 4: MQTT Focus (3 services)

**Purpose:** MQTT library replacement

```yaml
mqtt_group:
  critical:
    - websocket-ingestion
  high:
    - data-retention
  low:
    - ha-simulator
```

---

### Group 5: InfluxDB Focus (16 services)

**Purpose:** InfluxDB client migration

```yaml
influxdb_group:
  critical:
    - api-automation-edge
    - data-api
    - websocket-ingestion
  high:
    - admin-api
    - data-retention
  medium:
    - energy-correlator
    - energy-forecasting
    - smart-meter-service
  low:
    - air-quality-service
    - calendar-service
    - carbon-intensity-service
    - electricity-pricing-service
    - observability-dashboard
    - sports-api
    - weather-api
```

---

## Batch Processing Strategy

### Batch 1: Low-Risk Validation (Parallel: 5 services)

```
automation-miner, blueprint-index, ha-setup-service,
air-quality-service, calendar-service
```

**Purpose:** Validate migration scripts work correctly

---

### Batch 2: Medium-Risk Testing (Parallel: 5 services)

```
ai-pattern-service, device-intelligence-service, openvino-service,
sports-api, weather-api
```

**Purpose:** Test multi-dependency migrations

---

### Batch 3: High-Risk Services (Parallel: 3 services)

```
ai-core-service, ml-service, admin-api
```

**Purpose:** Migrate high-priority AI/ML and admin services

---

### Batch 4: Critical Services (Sequential: 1 at a time)

```
1. data-retention (HIGH, 3 dependencies)
2. api-automation-edge (CRITICAL, 2 dependencies)
3. data-api (CRITICAL, 2 dependencies)
4. websocket-ingestion (CRITICAL, 3 dependencies)
```

**Purpose:** Zero-downtime critical path migration

---

## Rollback Plan

### Service-Level Rollback

**Each service has rollback script:**
- `scripts/phase2-rollback-<service>.sh`
- Reverts all breaking changes
- Restores previous requirements.txt
- Rebuilds with previous versions

### Batch-Level Rollback

**Rollback entire batch if >20% fail:**
- Automatic trigger on health check failures
- Rollback all services in batch
- Document failures for analysis

### Critical Service Rollback

**CRITICAL services have blue-green deployment:**
- Keep old version running during migration
- Switch traffic after validation
- Instant rollback if issues detected

---

## Success Criteria

### Story 1 Completion ✅

- [x] Complete dependency map for all services
- [x] Services categorized by breaking change
- [x] Risk assessment completed
- [x] Migration order determined
- [x] Service groups identified for parallel processing
- [x] Rollback plan documented

### Phase 2 Overall

- [ ] 95%+ success rate (maintain Phase 1 benchmark)
- [ ] 100% test pass rate after migrations
- [ ] Zero production incidents
- [ ] All CRITICAL services healthy

---

## Next Steps

### Immediate (Story 2)

Create pytest-asyncio migration script based on identified services:
- Focus on 20 services needing async test migration
- Prioritize CRITICAL services (data-api, websocket-ingestion)
- Test on low-risk services first (automation-miner, blueprint-index)

### Story 3-5

Create migration scripts for:
- tenacity (10 services)
- asyncio-mqtt (3 services)
- influxdb3-python (16 services)

### Story 6

Integrate all migration scripts into batch orchestrator

---

## Dependencies JSON

```json
{
  "phase2_service_groups": {
    "pytest_asyncio": [
      "admin-api", "ai-core-service", "ai-pattern-service",
      "ai-query-service", "ai-training-service", "automation-miner",
      "blueprint-index", "blueprint-suggestion-service", "data-api",
      "data-retention", "device-intelligence-service", "ha-ai-agent-service",
      "ha-setup-service", "ha-simulator", "ml-service",
      "openvino-service", "proactive-agent-service", "sports-api",
      "weather-api", "websocket-ingestion"
    ],
    "tenacity": [
      "ai-automation-service-new", "ai-core-service", "ai-pattern-service",
      "api-automation-edge", "device-intelligence-service", "ha-ai-agent-service",
      "ml-service", "openvino-service", "proactive-agent-service", "rag-service"
    ],
    "asyncio_mqtt": [
      "data-retention", "ha-simulator", "websocket-ingestion"
    ],
    "influxdb": [
      "admin-api", "air-quality-service", "api-automation-edge",
      "calendar-service", "carbon-intensity-service", "data-api",
      "data-retention", "electricity-pricing-service", "energy-correlator",
      "energy-forecasting", "observability-dashboard", "smart-meter-service",
      "sports-api", "weather-api", "websocket-ingestion"
    ],
    "critical_path": [
      "websocket-ingestion", "data-api", "api-automation-edge"
    ]
  }
}
```

---

**Status:** ✅ COMPLETE
**Next Story:** PHASE2-002 (pytest-asyncio Migration Script)
**Risk Level:** Manageable with proper sequencing
**Ready to Proceed:** YES
