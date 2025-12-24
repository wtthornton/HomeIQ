# HomeIQ Port Mapping Reference

**Last Updated:** December 09, 2025
**Version:** 1.0.0
**Purpose:** Comprehensive reference for all HomeIQ service port mappings

---

## Overview

HomeIQ uses Docker Compose to manage 24 active microservices on a single NUC deployment. Due to port conflicts where multiple services share the same internal port, Docker Compose maps external ports to internal container ports.

**Port Mapping Format:** `EXTERNAL:INTERNAL` (e.g., `8024:8018` means external port 8024 maps to internal port 8018)

**Why Port Mapping?**
- Multiple services use the same internal ports (8018, 8019, 8020)
- Docker resolves conflicts by exposing different external ports
- Services communicate internally using container names (not ports)
- External clients access services via mapped external ports

---

## Complete Service Port Reference

### Web Layer (Frontend Services)

| Service | External Port | Internal Port | Container Name | Access URL |
|---------|--------------|---------------|----------------|------------|
| **Health Dashboard** | 3000 | 80 | homeiq-health-dashboard | http://localhost:3000 |
| **AI Automation UI** | 3001 | 80 | homeiq-ai-automation-ui | http://localhost:3001 |

---

### Core API Layer

| Service | External Port | Internal Port | Container Name | Access URL |
|---------|--------------|---------------|----------------|------------|
| **WebSocket Ingestion** | 8001 | 8001 | homeiq-websocket | http://localhost:8001 |
| **Admin API** | 8003 | 8004 | homeiq-admin-api | http://localhost:8003 |
| **Data API** | 8006 | 8006 | homeiq-data-api | http://localhost:8006 |

---

### AI Services Layer

| Service | External Port | Internal Port | Port Conflict | Container Name | Access URL |
|---------|--------------|---------------|---------------|----------------|------------|
| **AI Core Service** | 8018 | 8018 | ✅ Original | homeiq-ai-core | http://localhost:8018 |
| **AI Automation Service** | 8024 | 8018 | ⚠️ Conflicts with AI Core | homeiq-ai-automation-service | http://localhost:8024 |
| **AI Query Service** | 8035 | 8018 | ⚠️ Conflicts with AI Core | homeiq-ai-query-service | http://localhost:8035 |
| **OpenVINO Service** | 8026 | 8019 | ⚠️ Conflicts with Device Intelligence | homeiq-openvino-service | http://localhost:8026 |
| **Device Intelligence** | 8028 | 8019 | ⚠️ Conflicts with OpenVINO | homeiq-device-intelligence | http://localhost:8028 |
| **Automation Miner** | 8029 | 8019 | ⚠️ Conflicts with OpenVINO | homeiq-automation-miner | http://localhost:8029 |
| **OpenAI Service** | 8020 | 8020 | ✅ Original | homeiq-openai-service | http://localhost:8020 |
| **ML Service** | 8025 | 8020 | ⚠️ Conflicts with OpenAI | homeiq-ml-service | http://localhost:8025 |
| **HA Setup Service** | 8027 | 8020 | ⚠️ Conflicts with OpenAI | homeiq-ha-setup-service | http://localhost:8027 |
| **AI Pattern Service** | 8034 | 8020 | ⚠️ Conflicts with OpenAI | homeiq-ai-pattern-service | http://localhost:8034 |
| **NER Service** | 8031 (exposed) | 8031 | ✅ Internal only | homeiq-ner-service | Internal only |
| **Proactive Agent** | 8031 (exposed) | 8031 | ✅ Internal only | homeiq-proactive-agent | Internal only |

---

### Data Enrichment Layer (Epic 31: Direct InfluxDB Writes)

| Service | External Port | Internal Port | Container Name | Access URL |
|---------|--------------|---------------|----------------|------------|
| **Weather API** | 8009 | 8009 | homeiq-weather-api | http://localhost:8009 |
| **Carbon Intensity** | 8010 | 8010 | homeiq-carbon-intensity | http://localhost:8010 |
| **Electricity Pricing** | 8011 | 8011 | homeiq-electricity-pricing | http://localhost:8011 |
| **Air Quality** | 8012 | 8012 | homeiq-air-quality | http://localhost:8012 |
| **Calendar Service** | 8013 | 8013 | homeiq-calendar | ⏸️ Currently disabled |
| **Smart Meter** | 8014 | 8014 | homeiq-smart-meter | http://localhost:8014 |

---

### Processing & Infrastructure Layer

| Service | External Port | Internal Port | Container Name | Access URL |
|---------|--------------|---------------|----------------|------------|
| **Log Aggregator** | 8015 | 8015 | homeiq-log-aggregator | http://localhost:8015 |
| **Energy Correlator** | 8017 | 8017 | homeiq-energy-correlator | http://localhost:8017 |
| **Data Retention** | 8080 | 8080 | homeiq-data-retention | http://localhost:8080 |

---

### Infrastructure Services (Not HomeIQ)

| Service | Port | Container Name | Access URL |
|---------|------|----------------|------------|
| **InfluxDB** | 8086 | homeiq-influxdb | http://localhost:8086 |
| **Home Assistant** | 8123 | N/A (external) | http://192.168.1.86:8123 |
| **MQTT Broker** | 1883 | N/A (external) | mqtt://192.168.1.86:1883 |

---

## Port Conflict Resolution

### Internal Port 8018 Conflicts

**Services sharing port 8018:**
1. AI Core Service: `8018:8018` ✅ Original
2. AI Automation Service: `8024:8018` ⚠️ Remapped
3. AI Query Service: `8035:8018` ⚠️ Remapped

**Resolution:**
- AI Core Service keeps original port 8018
- AI Automation Service exposed as 8024 externally
- AI Query Service exposed as 8035 externally

### Internal Port 8019 Conflicts

**Services sharing port 8019:**
1. OpenVINO Service: `8026:8019` ⚠️ Remapped
2. Device Intelligence: `8028:8019` ⚠️ Remapped
3. Automation Miner: `8029:8019` ⚠️ Remapped

**Resolution:**
- All three services remapped to different external ports
- Services communicate internally via container names

### Internal Port 8020 Conflicts

**Services sharing port 8020:**
1. OpenAI Service: `8020:8020` ✅ Original
2. ML Service: `8025:8020` ⚠️ Remapped
3. HA Setup Service: `8027:8020` ⚠️ Remapped
4. AI Pattern Service: `8034:8020` ⚠️ Remapped

**Resolution:**
- OpenAI Service keeps original port 8020
- Other services exposed on different external ports

---

## Port Range Allocation

### Reserved Ranges

- **3000-3999:** Frontend services (React UIs)
- **8001-8099:** Backend services (APIs, processors, AI)
- **8000s:** Core APIs (websocket, admin, data)
- **8010s:** Enrichment services (weather, carbon, etc.)
- **8020s-8030s:** AI services (ML, OpenVINO, automation)

### Available Ports (for future services)

- 8002 (available)
- 8005 (available)
- 8007-8008 (available)
- 8016 (available)
- 8021-8023 (available)
- 8030 (available)
- 8032-8033 (available)
- 8036+ (available)

---

## Service-to-Service Communication

**Internal Docker Network:** `homeiq-network`

Services communicate using **container names**, not ports:
```python
# Good: Use container name (DNS resolution within Docker network)
DATA_API_URL = "http://data-api:8006"
AI_CORE_URL = "http://ai-core-service:8018"

# Bad: Use localhost (doesn't work inside containers)
DATA_API_URL = "http://localhost:8006"  # ❌ Won't work
```

**Example:** AI Automation Service calls Device Intelligence:
```python
# Inside ai-automation-service container
import httpx
response = await httpx.get("http://device-intelligence-service:8019/api/devices")
# Uses internal port 8019, not external port 8028
```

---

## Local Development Port Usage

When developing locally **without Docker**, use the **internal port**:

```bash
# ML Service local development
cd services/ml-service
uvicorn src.main:app --reload --port 8020  # Internal port

# Access locally
curl http://localhost:8020/health

# In Docker production
curl http://localhost:8025/health  # External port
```

**General Rule:**
- **Local development:** Use internal port
- **Docker production:** Use external port
- **Service-to-service:** Use container name + internal port

---

## docker-compose.yml Port Mapping Examples

### Simple Port Mapping (No Conflict)

```yaml
websocket-ingestion:
  ports:
    - "8001:8001"  # external:internal
  # Both ports are the same (no conflict)
```

### Port Conflict Resolution

```yaml
ai-automation-service:
  ports:
    - "8024:8018"  # external:internal
  # External 8024 maps to internal 8018
  # Resolves conflict with ai-core-service (8018:8018)
```

### Exposed But Not Published (Internal Only)

```yaml
ner-service:
  expose:
    - "8031"  # Accessible within Docker network only
  # No external port mapping
  # Only accessible by other containers
```

---

## Troubleshooting

### Issue: "Connection refused" when accessing service

**Cause:** Using wrong port (internal vs external)

**Solution:**
```bash
# If accessing from host machine, use external port
curl http://localhost:8025/health  # ✅ ML Service external

# If accessing from another container, use container name + internal port
curl http://ml-service:8020/health  # ✅ ML Service internal
```

### Issue: "Port already in use" when starting Docker Compose

**Cause:** External port conflict with another service on host

**Solution:**
1. Check what's using the port: `sudo lsof -i :8024`
2. Stop conflicting service or change port in docker-compose.yml
3. Restart: `docker compose up -d`

### Issue: Service can't reach another service

**Cause:** Using localhost instead of container name

**Solution:**
```python
# Wrong (doesn't work in Docker)
url = "http://localhost:8020/health"

# Right (works in Docker)
url = "http://ml-service:8020/health"
```

---

## Quick Reference Table (Alphabetical)

| Service | External → Internal | Container Name |
|---------|---------------------|----------------|
| Admin API | 8003 → 8004 | homeiq-admin-api |
| AI Automation Service | 8024 → 8018 | homeiq-ai-automation-service |
| AI Automation UI | 3001 → 80 | homeiq-ai-automation-ui |
| AI Core Service | 8018 → 8018 | homeiq-ai-core |
| AI Pattern Service | 8034 → 8020 | homeiq-ai-pattern-service |
| AI Query Service | 8035 → 8018 | homeiq-ai-query-service |
| Air Quality | 8012 → 8012 | homeiq-air-quality |
| Automation Miner | 8029 → 8019 | homeiq-automation-miner |
| Calendar Service | 8013 → 8013 (disabled) | homeiq-calendar |
| Carbon Intensity | 8010 → 8010 | homeiq-carbon-intensity |
| Data API | 8006 → 8006 | homeiq-data-api |
| Data Retention | 8080 → 8080 | homeiq-data-retention |
| Device Intelligence | 8028 → 8019 | homeiq-device-intelligence |
| Electricity Pricing | 8011 → 8011 | homeiq-electricity-pricing |
| Energy Correlator | 8017 → 8017 | homeiq-energy-correlator |
| HA Setup Service | 8027 → 8020 | homeiq-ha-setup-service |
| Health Dashboard | 3000 → 80 | homeiq-health-dashboard |
| InfluxDB | 8086 → 8086 | homeiq-influxdb |
| Log Aggregator | 8015 → 8015 | homeiq-log-aggregator |
| ML Service | 8025 → 8020 | homeiq-ml-service |
| NER Service | Exposed 8031 (internal) | homeiq-ner-service |
| OpenAI Service | 8020 → 8020 | homeiq-openai-service |
| OpenVINO Service | 8026 → 8019 | homeiq-openvino-service |
| Proactive Agent | Exposed 8031 (internal) | homeiq-proactive-agent |
| Smart Meter | 8014 → 8014 | homeiq-smart-meter |
| Weather API | 8009 → 8009 | homeiq-weather-api |
| WebSocket Ingestion | 8001 → 8001 | homeiq-websocket |

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Comprehensive guide for AI assistants
- [API_REFERENCE.md](api/API_REFERENCE.md) - All 65 API endpoints
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Production deployment instructions
- [docker-compose.yml](../docker-compose.yml) - Service definitions with port mappings

---

## Version History

### v1.0.0 (December 09, 2025)
- Initial port mapping reference document
- Documented all 24+ active services
- Identified and documented port conflicts
- Added troubleshooting guide
- Created quick reference table

---

**Document Metadata:**
- **Created:** December 09, 2025
- **Last Updated:** December 09, 2025
- **Version:** 1.0.0
- **Maintainer:** HomeIQ Development Team
- **Review Schedule:** Update when services are added/removed or ports change
