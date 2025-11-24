# Data Flow Diagram Review and Corrections

**Date:** December 2025  
**Status:** Review Complete - Corrections Required

---

## Executive Summary

The current diagram contains **critical architectural inaccuracies** that reflect the **pre-Epic 31 architecture**. The diagram shows the deprecated `enrichment-pipeline` service and incorrect data flow directions. This document provides corrections based on the current Epic 31 architecture.

---

## ❌ Critical Issues Found

### 1. **Enrichment Pipeline is DEPRECATED**

**Diagram Shows:**
- `Enrichment Pipeline` as an active service
- Connection: `WebSocket Ingestion → Enrichment Pipeline → InfluxDB`

**Reality (Epic 31):**
- `enrichment-pipeline` service was **deprecated in Epic 31 (Story 31.4)**
- All normalization now happens **inline** within `websocket-ingestion`
- **Direct write path**: `websocket-ingestion → InfluxDB` (no intermediate service)

**Evidence:**
- `.cursor/rules/epic-31-architecture.mdc` - Explicitly states enrichment-pipeline is deprecated
- `services/websocket-ingestion/src/main.py:411-420` - Inline normalization code
- `docker-compose.yml` - No enrichment-pipeline service defined

**Action Required:**
- ❌ **Remove** `Enrichment Pipeline` node from diagram
- ✅ **Add direct connection** from `WebSocket Ingestion` to `InfluxDB`

---

### 2. **Incorrect Data Flow Direction**

**Diagram Shows:**
```
Home Assistant → WebSocket Ingestion → Enrichment Pipeline → InfluxDB
```

**Correct Flow (Epic 31):**
```
Home Assistant (192.168.1.86:8123)
    ↓ WebSocket
WebSocket Ingestion (Port 8001)
    - Event validation
    - Inline normalization
    - Device/area lookups
    - Duration calculation
    ↓ DIRECT WRITE
InfluxDB (Port 8086)
    bucket: home_assistant_events
```

**Action Required:**
- ✅ Update connection from `WebSocket Ingestion` to `InfluxDB` (remove enrichment-pipeline)
- ✅ Change connection type to "Primary Path" (green line)

---

### 3. **External Services Write Directly to InfluxDB**

**Diagram Shows:**
- `External Services` → `InfluxDB` (correct)
- `Sports Data` → `InfluxDB` (correct)
- `OpenWeather` → `WebSocket Ingestion` (❌ INCORRECT)

**Reality:**
- **ALL external services** write **directly** to InfluxDB
- They do **NOT** go through websocket-ingestion
- Services include:
  - `weather-api` (Port 8009) → InfluxDB (bucket: `weather_data`)
  - `carbon-intensity` (Port 8010) → InfluxDB
  - `electricity-pricing` (Port 8011) → InfluxDB
  - `air-quality` (Port 8012) → InfluxDB
  - `smart-meter` (Port 8014) → InfluxDB

**Evidence:**
- `services/weather-api/src/main.py:139-169` - Direct InfluxDB writes
- `services/carbon-intensity-service/src/main.py:352-380` - Direct InfluxDB writes
- `.cursor/rules/epic-31-architecture.mdc` - "External services write directly to InfluxDB"

**Action Required:**
- ❌ **Remove** connection from `OpenWeather` to `WebSocket Ingestion`
- ✅ **Add direct connection** from `OpenWeather` to `InfluxDB`
- ✅ Verify all external services show direct InfluxDB writes

---

### 4. **AI Automation Service Data Flow**

**Diagram Shows:**
- `AI Automation` → `OpenAI GPT-4o-mini` (correct)
- `Enrichment Pipeline` → `AI Automation` (❌ INCORRECT - enrichment-pipeline is deprecated)

**Reality:**
- `AI Automation Service` (Port 8024 external, 8018 internal) **reads** from InfluxDB
- It uses `data-api` (Port 8006) to query events, OR queries InfluxDB directly
- It uses `openai-service` (Port 8020) for GPT-4o-mini API calls
- It uses `ai-core-service` (Port 8018) for orchestration

**Evidence:**
- `services/ai-automation-service/src/clients/influxdb_client.py` - Direct InfluxDB queries
- `services/ai-automation-service/src/clients/data_api_client.py` - Data API queries
- `docker-compose.yml:863-922` - AI Automation Service configuration

**Action Required:**
- ❌ **Remove** connection from `Enrichment Pipeline` to `AI Automation`
- ✅ **Add connection** from `InfluxDB` to `AI Automation` (read path)
- ✅ **Add connection** from `Data API` to `AI Automation` (alternative read path)
- ✅ Verify `AI Automation` → `OpenAI GPT-4o-mini` connection is correct

---

### 5. **SQLite Database Usage**

**Diagram Shows:**
- `SQLite` connected from `WebSocket Ingestion` and `Enrichment Pipeline`

**Reality (Epic 22):**
- **SQLite** stores **metadata** (devices, entities, webhooks) - NOT time-series data
- **InfluxDB** stores **time-series data** (events, metrics, sensor readings)
- They store **different data types** from the **same source**
- `websocket-ingestion` writes to **both** (events → InfluxDB, device metadata → SQLite via data-api)
- `data-api` queries **both** databases

**Evidence:**
- `docs/SQLITE_DATA_FLOW_CLARIFICATION.md` - Explicit separation of concerns
- `services/data-api/src/events_endpoints.py` - Queries InfluxDB for events
- `services/data-api/src/devices_endpoints.py` - Queries SQLite for devices

**Action Required:**
- ✅ Verify SQLite connection shows metadata storage (not time-series)
- ✅ Show SQLite is queried by `data-api` (not directly by dashboard)
- ✅ Clarify that SQLite and InfluxDB store different data types

---

### 6. **Sports Data Service Status**

**Diagram Shows:**
- `ESPN API` → `Sports Data` → `InfluxDB`

**Reality:**
- `sports-data` service is **NOT** in `docker-compose.yml`
- If it exists, it should write directly to InfluxDB
- Template configuration exists: `infrastructure/env.sports.template`
- Story 12.1 documents InfluxDB persistence for sports data

**Action Required:**
- ⚠️ **Verify** if `sports-data` service is actually running
- ✅ If running, ensure it shows direct write to InfluxDB
- ✅ If not running, consider removing from diagram or marking as "optional"

---

### 7. **OpenVINO Models Connection**

**Diagram Shows:**
- `OpenAI GPT-4o-mini` → `OpenVINO Models`

**Reality:**
- `OpenVINO Service` (Port 8026 external, 8019 internal) is a **separate service**
- It provides embeddings, re-ranking, and classification models
- It is called by `ai-core-service`, not directly by OpenAI
- Models: `all-MiniLM-L6-v2`, `bge-reranker-base`, `flan-t5-small`

**Evidence:**
- `docker-compose.yml:758-785` - OpenVINO Service configuration
- `services/ai-automation-service/README.md` - Service architecture

**Action Required:**
- ✅ Verify `OpenVINO Models` connection shows it's called by `AI Core Service`
- ✅ Clarify that OpenVINO is a separate microservice, not a model dependency

---

### 8. **Admin API Connection**

**Diagram Shows:**
- `Admin API` connected from `SQLite` with "Enhancement Path" (orange line)

**Reality:**
- `admin-api` (Port 8003 external, 8004 internal) queries **both** InfluxDB and SQLite
- It provides system monitoring, health checks, and Docker management
- It does **NOT** write to databases (read-only for monitoring)

**Evidence:**
- `docker-compose.yml:116-180` - Admin API configuration
- `services/admin-api/src/events_endpoints.py:450-492` - InfluxDB queries

**Action Required:**
- ✅ Verify `Admin API` shows connections to both InfluxDB and SQLite (read paths)
- ✅ Clarify that Admin API is for monitoring, not data enhancement

---

## ✅ Correct Connections (Verify These)

1. **Home Assistant → WebSocket Ingestion**
   - ✅ WebSocket connection (red line in diagram - verify this is correct)
   - ✅ Port: 192.168.1.86:8123 → localhost:8001

2. **WebSocket Ingestion → InfluxDB**
   - ✅ Direct write (should be green "Primary Path")
   - ✅ Port: localhost:8001 → localhost:8086

3. **InfluxDB → Data API**
   - ✅ Query path (blue "WebSocket/Query" line)
   - ✅ Port: localhost:8086 → localhost:8006

4. **Data API → Dashboard**
   - ✅ REST API (blue line)
   - ✅ Port: localhost:8006 → localhost:3000

5. **External Services → InfluxDB**
   - ✅ Direct writes (black "External APIs" line)
   - ✅ Services: weather-api, carbon-intensity, electricity-pricing, air-quality, smart-meter

6. **AI Automation → OpenAI GPT-4o-mini**
   - ✅ API calls (red line)
   - ✅ Via `openai-service` (Port 8020)

---

## 📋 Recommended Diagram Updates

### Remove These Nodes/Connections:
1. ❌ **Remove** `Enrichment Pipeline` node entirely
2. ❌ **Remove** `Enrichment Pipeline → InfluxDB` connection
3. ❌ **Remove** `Enrichment Pipeline → AI Automation` connection
4. ❌ **Remove** `OpenWeather → WebSocket Ingestion` connection

### Add/Update These Connections:
1. ✅ **Add** direct `WebSocket Ingestion → InfluxDB` (green "Primary Path")
2. ✅ **Add** `OpenWeather → InfluxDB` (black "External APIs" line)
3. ✅ **Add** `InfluxDB → AI Automation` (read path, purple "AI Pattern Analysis")
4. ✅ **Add** `Data API → AI Automation` (alternative read path)
5. ✅ **Update** `SQLite` connections to show metadata storage only
6. ✅ **Update** `Admin API` to show read-only monitoring connections

### Verify These Services Exist:
1. ⚠️ **Verify** `Sports Data` service is actually running
2. ⚠️ **Verify** all external services are correctly labeled
3. ⚠️ **Verify** port numbers match `docker-compose.yml`

---

## 🎯 Corrected Architecture Flow

### Main Event Flow (Epic 31):
```
Home Assistant (192.168.1.86:8123)
    ↓ WebSocket
WebSocket Ingestion (Port 8001)
    - Inline normalization
    - Device/area lookups
    ↓ DIRECT WRITE
InfluxDB (Port 8086)
    bucket: home_assistant_events
    ↓ QUERY
Data API (Port 8006)
    ↓ REST API
Dashboard (Port 3000)
```

### External Services Flow:
```
External APIs (ESPN, OpenWeatherMap, etc.)
    ↓ HTTP
External Services (weather-api, sports-data, etc.)
    ↓ DIRECT WRITE
InfluxDB (Port 8086)
    ↓ QUERY
Data API (Port 8006)
    ↓ REST API
Dashboard (Port 3000)
```

### AI Automation Flow:
```
InfluxDB (Port 8086)
    ↓ QUERY (via data-api or direct)
AI Automation Service (Port 8024)
    ↓ API CALL
OpenAI Service (Port 8020) → GPT-4o-mini
    ↓ RESPONSE
AI Automation Service
    ↓ SUGGESTIONS
AI Automation UI (Port 3001)
```

### Database Architecture (Epic 22):
```
WebSocket Ingestion
    ├─→ InfluxDB (time-series events)
    └─→ SQLite (via data-api) (metadata: devices, entities)
    
Data API
    ├─→ Queries InfluxDB (events)
    └─→ Queries SQLite (devices, entities)
```

---

## 📊 Service Port Reference

| Service | External Port | Internal Port | Status |
|---------|--------------|---------------|--------|
| InfluxDB | 8086 | 8086 | ✅ Active |
| WebSocket Ingestion | 8001 | 8001 | ✅ Active |
| Data API | 8006 | 8006 | ✅ Active |
| Admin API | 8003 | 8004 | ✅ Active |
| Dashboard | 3000 | 80 | ✅ Active |
| Weather API | 8009 | 8009 | ✅ Active |
| Carbon Intensity | 8010 | 8010 | ✅ Active |
| Electricity Pricing | 8011 | 8011 | ✅ Active |
| Air Quality | 8012 | 8012 | ✅ Active |
| Smart Meter | 8014 | 8014 | ✅ Active |
| AI Automation | 8024 | 8018 | ✅ Active |
| OpenAI Service | 8020 | 8020 | ✅ Active |
| OpenVINO Service | 8026 | 8019 | ✅ Active |
| AI Core Service | 8018 | 8018 | ✅ Active |
| AI Automation UI | 3001 | 80 | ✅ Active |
| Sports Data | ❓ | ❓ | ⚠️ Not in docker-compose.yml |
| Enrichment Pipeline | ❌ | ❌ | ❌ DEPRECATED |

---

## ✅ Next Steps

1. **Update Diagram:**
   - Remove enrichment-pipeline node
   - Add direct websocket-ingestion → InfluxDB connection
   - Fix external services connections
   - Update AI Automation data flow

2. **Verify Services:**
   - Check if sports-data service exists and is running
   - Confirm all port numbers match docker-compose.yml
   - Verify all external services are correctly represented

3. **Test Diagram Accuracy:**
   - Compare with actual running services
   - Verify connection types match actual protocols
   - Ensure all active services are shown

---

## 📚 References

- `.cursor/rules/epic-31-architecture.mdc` - Current architecture rules
- `docker-compose.yml` - Active service definitions
- `docs/architecture.md` - Architecture documentation
- `docs/SQLITE_DATA_FLOW_CLARIFICATION.md` - Database separation
- `services/websocket-ingestion/src/main.py` - Inline normalization code

---

**Review Completed:** December 2025  
**Reviewed By:** AI Assistant  
**Status:** Corrections Required

