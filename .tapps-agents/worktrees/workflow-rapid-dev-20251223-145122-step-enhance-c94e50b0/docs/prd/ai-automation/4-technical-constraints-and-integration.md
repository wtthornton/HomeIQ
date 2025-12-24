# 4. Technical Constraints and Integration

### 4.1 Existing Technology Stack (Must Use)

**Backend Stack:**
- Python 3.11
- FastAPI 0.104.1
- Docker + Docker Compose 2.20+
- InfluxDB 2.7 (via Data API)
- SQLite 3.45+

**Frontend Stack:**
- React 18.2.0
- TypeScript 5.2.2
- TailwindCSS 3.4.0
- Vite 5.0.8
- Heroicons 2.2.0

**Infrastructure:**
- Mosquitto MQTT 2.0 (NEW)
- Docker Volumes
- Python logging

---

### 4.2 Phase 1 MVP Technology Stack (NEW)

**Machine Learning:**

```python
scikit-learn==1.3.2
  - KMeans (clustering)
  - DBSCAN (density-based clustering)
  - Isolation Forest (anomaly detection)

pandas==2.1.4
  - Data manipulation
  - Feature engineering

numpy==1.26.2
  - Numerical operations
```

**LLM Integration:**

```python
openai==1.12.0
  - GPT-4o-mini API client
  - Structured outputs (Pydantic)

langchain==0.1.0 (Optional - may defer to Phase 2)
  - Prompt management
  - Chain orchestration
```

**MQTT Communication:**

```python
paho-mqtt==1.6.1
  - MQTT client
  - Pub/sub patterns
```

**Database & Storage:**

```python
aiosqlite==0.19.0
  - Async SQLite
  - Pattern storage
```

**Scheduling:**

```python
apscheduler==3.10.4
  - Cron-style scheduling
  - Daily batch jobs
```

---

### 4.3 Integration Approach

#### Data API Integration (Read-Only):

```python
# Query existing Data API for historical data
async def fetch_historical_events():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://data-api:8006/api/events",
            params={
                "start": "-30d",
                "group_by": "device_id"
            }
        )
        return response.json()
```

**No Direct InfluxDB Access:**
- ✅ Use Data API as abstraction layer
- ❌ Do NOT query InfluxDB directly

#### Home Assistant API Integration:

```python
# Read existing automations
GET http://ha:8123/api/config/automation/config

# Deploy new automation
POST http://ha:8123/api/config/automation/config
{
  "alias": "AI Suggested: Morning Lights",
  "trigger": [...],
  "action": [...]
}

# Remove automation
DELETE http://ha:8123/api/config/automation/config/{automation_id}
```

#### MQTT Integration:

```bash
# Topic structure
ha-ai/events/*          # AI publishes
ha-ai/commands/*        # AI sends commands
ha-ai/responses/*       # HA responds
homeassistant/status    # HA status
```

---

### 4.4 Code Organization

```
services/ai-automation-service/
├── src/
│   ├── main.py                      # FastAPI entry point
│   ├── config.py                    # Configuration
│   ├── pattern_analyzer/            # Pattern detection
│   │   ├── time_of_day.py
│   │   ├── co_occurrence.py
│   │   └── anomaly_detector.py
│   ├── llm/                         # LLM integration
│   │   ├── openai_client.py
│   │   └── prompt_templates.py
│   ├── mqtt/                        # MQTT communication
│   │   ├── client.py
│   │   └── topics.py
│   ├── database/                    # Database layer
│   │   ├── models.py
│   │   └── crud.py
│   ├── api/                         # FastAPI endpoints
│   │   ├── suggestions.py
│   │   ├── patterns.py
│   │   └── deployment.py
│   └── scheduler/                   # Batch scheduling
│       └── daily_analysis.py
├── tests/
├── Dockerfile
├── requirements.txt
└── README.md
```

---

### 4.5 Deployment Configuration

**Docker Compose Integration:**

```yaml
services:
  # NEW: MQTT Broker
  mosquitto:
    image: eclipse-mosquitto:2.0-alpine
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./infrastructure/mqtt/mosquitto.conf:/mosquitto/config/mosquitto.conf
    networks:
      - ha-network
  
  # NEW: AI Automation Service
  ai-automation-service:
    build: ./services/ai-automation-service
    ports:
      - "8011:8011"
    environment:
      - DATA_API_URL=http://data-api:8006
      - HA_URL=http://home-assistant:8123
      - HA_TOKEN=${HA_TOKEN}
      - MQTT_BROKER=mosquitto
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANALYSIS_SCHEDULE=0 3 * * *
    depends_on:
      - data-api
      - mosquitto
      - home-assistant
    volumes:
      - ai_data:/app/data
    networks:
      - ha-network
  
  # NEW: AI Frontend
  ai-automation-frontend:
    build: ./services/ai-automation-frontend
    ports:
      - "3002:80"
    environment:
      - AI_API_URL=http://localhost:8011
    depends_on:
      - ai-automation-service
    networks:
      - ha-network
```

---

### 4.6 Performance Constraints

**Memory Limits:**
- Peak (analysis): 1GB
- Idle: 200MB
- Total system: Must fit within NUC 8-16GB RAM

**Processing Time:**
- Daily analysis: 10 minutes target, 15 minutes max
- API response: 500ms target
- LLM generation: 30 seconds per suggestion (async)

**Storage:**
- Code + dependencies: 500MB
- Pattern database: 100MB
- Logs: 50MB (rotating)
- Total: <1GB

---

### 4.7 Security Constraints

**Network Security:**
- ✅ MQTT on internal network only
- ✅ All services within Docker network
- ✅ No public endpoints except frontend

**API Security:**
- ✅ Home Assistant token authentication
- ✅ CORS restricted to localhost
- ✅ Rate limiting on API endpoints

**Data Security:**
- ✅ No raw event data sent to LLM (only anonymized patterns)
- ✅ HA tokens stored securely (environment variables)
- ✅ OpenAI API key in environment (not code)

---
